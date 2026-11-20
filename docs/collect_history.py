#!/usr/bin/env python3
"""Index one authorized history locally. Stdout contains counts only; JSONL contains private text."""
import argparse
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile
from zoneinfo import ZoneInfo

EXPORT_NAME = re.compile(r"conversations(?:[-_]\d+)?\.json\Z", re.I)
CLAUDE_WRAPPERS = ("<local-command-", "<command-name>", "<command-message>", "<system-reminder>",
                   "[Request interrupted by user", "<ide_opened_file>", "<ide_selection>")
HIDDEN = ("is_visually_hidden_from_conversation", "is_user_system_message", "is_meta", "is_hidden")


def parse_timestamp(value):
    try:
        if isinstance(value, str) and re.fullmatch(r"\d{10}(?:\.\d+)?|\d{13}", value):
            value = float(value)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return None
        else:
            if type(value) not in (float, int):
                return None
            if abs(value) >= 100_000_000_000:  # Millisecond Unix timestamps in chat history.
                value /= 1000
            dt = datetime.fromtimestamp(value, timezone.utc)
        return dt
    except (ValueError, OverflowError, OSError):
        return None


def date_in_zone(value, zone):
    dt = parse_timestamp(value)
    return dt.astimezone(zone).date().isoformat() if dt is not None else None


def local_id(session, line, parts):
    # Legacy Codex logs have no native message IDs. Verify both the locator and exact text.
    text = json.dumps([session, line, parts], ensure_ascii=False, separators=(",", ":"))
    return "local-" + hashlib.sha256(text.encode()).hexdigest()


def codex_owner_group(meta):
    creator = meta.get("creator_user_id")
    if not isinstance(creator, str) or not creator.strip():
        return "unknown"
    return "owner-" + hashlib.sha256(("puai/codex/creator/" + creator).encode()).hexdigest()[:20]


def codex_rows(path, stats, origins=None, family=None):
    from read_context import is_form_record, is_user_session, visible_message

    by_family = {"response_item": [], "event_msg": []}
    with path.open("rb") as fin:
        header = json.loads(next(fin, b"{}"))
        meta = header.get("payload") or {}
        sid = meta.get("session_id") or meta.get("id")
        if header.get("type") != "session_meta" or not sid:
            stats["unrecognized_sources"] += 1
            return
        if not is_user_session(meta):
            return
        owner = codex_owner_group(meta)
        fork = bool(meta.get("forked_from_id"))
        fork_epoch = None
        if fork and isinstance(meta.get("timestamp"), str):
            try:
                fork_epoch = datetime.fromisoformat(meta["timestamp"].replace("Z", "+00:00")).timestamp()
            except ValueError:
                pass
        turn, started = None, None
        occurrences = Counter()
        for line, raw in enumerate(fin, 2):
            # Most bytes in a rollout are tool output. Do not decode it into working memory.
            if not any(token in raw for token in (b'"user"', b'"user_message"', b'"task_started"', b'"turn_context"')):
                continue
            try:
                record = json.loads(raw)
            except (ValueError, UnicodeError):
                stats["unreadable_records"] += 1
                continue
            kind, payload = record.get("type"), record.get("payload") or {}
            if kind == "event_msg" and payload.get("type") == "task_started" or kind == "turn_context":
                if turn != payload.get("turn_id"):
                    turn, started = payload.get("turn_id"), None
                    occurrences.clear()
                if kind == "event_msg":
                    started = payload.get("started_at")
                continue
            if kind not in by_family:
                continue
            message = visible_message(record, kind)
            if not message or message[0] != "user":
                continue
            _, parts, mid = message
            # Forked rollouts may reissue both message IDs *and* recorder timestamps.
            # The original turn context survives. Distinguish deliberate repetitions within it.
            if turn and origins is not None:
                digest = hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).digest()
                occurrences[kind, digest] += 1
                key = (family or sid, turn, digest, occurrences[kind, digest])
                origin = origins.setdefault(key, sid)
                if fork and origin != sid:
                    stats["inherited_fork_copies"] += 1
                    continue
            temporal_origin = fork_epoch is not None and type(started) in (int, float)
            if fork and temporal_origin and started < int(fork_epoch):
                # A copied turn without its original source cannot establish the date here.
                stats["unverifiable_fork_turns"] += 1
                continue
            if fork and not mid and not (temporal_origin and started > fork_epoch):
                stats["unverifiable_fork_turns"] += 1
                continue
            row = {"session_id": sid, "owner_group": owner, "line": line, "id": mid or local_id(sid, line, parts),
                   "timestamp": record.get("timestamp"), "text": "\n".join(parts)}
            if is_form_record(payload):
                row["input_method"] = "question_form"
            if family and family != sid:
                row["conversation_id"] = family
            by_family[kind].append(row)
    # Codex can record the same turn twice under different event families/IDs.
    primary = by_family["response_item"]
    yield from primary
    copies = Counter(row["text"] for row in primary)
    for row in by_family["event_msg"]:
        if copies[row["text"]]:
            copies[row["text"]] -= 1
        else:
            yield row


def claude_messages(path, stats):
    from read_context import INJECTED

    visible_ancestor = {}
    with path.open("rb") as fin:
        for line, raw in enumerate(fin, 1):
            try:
                row = json.loads(raw)
            except (ValueError, UnicodeError):
                stats["unreadable_records"] += 1
                continue
            uid = row.get("uuid")
            parent = visible_ancestor.get(row.get("parentUuid"), row.get("parentUuid"))
            if uid:
                visible_ancestor[uid] = parent
            role = row.get("type")
            msg = row.get("message") or {}
            if (role not in ("user", "assistant") or msg.get("role") != role or not row.get("uuid")
                    or not row.get("sessionId") or row.get("isSidechain") or row.get("isMeta")
                    or row.get("isCompactSummary") or row.get("isVisibleInTranscriptOnly")):
                continue
            content = msg.get("content")
            has_upload = False
            if isinstance(content, str):
                parts = [content]
            elif isinstance(content, list):
                if role == "user" and any(isinstance(p, dict) and p.get("type") == "tool_result" for p in content):
                    continue
                has_upload = role == "user" and any(isinstance(p, dict) and p.get("type") in ("image", "document")
                                                   and (p.get("source") or p.get("file_id")) for p in content)
                parts = [p["text"] for p in content if isinstance(p, dict) and p.get("type") == "text"
                         and isinstance(p.get("text"), str)]
            else:
                continue
            parts = [p for p in parts if p.strip() and
                     (role != "user" or not p.lstrip().startswith(INJECTED + CLAUDE_WRAPPERS))]
            if parts or has_upload:
                visible_ancestor[uid] = uid
                message = {"role": role, "session_id": row["sessionId"], "id": uid, "line": line,
                           "timestamp": row.get("timestamp"), "text": "\n".join(parts)}
                if "parentUuid" in row:
                    message["parent_id"] = parent
                yield message


PASTE_MARKER = re.compile(r"\[(?:Pasted text #\d+(?: \+\d+ lines?)?|Image #\d+)\]", re.I)


def claude_input_history(path, stats):
    """The CLI's submission history has original input, but no assistant or complete thread."""
    from read_context import INJECTED
    with path.open("rb") as stream:
        for line, raw in enumerate(stream, 1):
            try:
                record = json.loads(raw)
            except (ValueError, UnicodeError):
                stats["unreadable_records"] += 1
                continue
            if not isinstance(record, dict):
                continue
            sid, stamp, display = (record.get(k) for k in ("sessionId", "timestamp", "display"))
            if not isinstance(sid, str) or not sid or type(stamp) not in (int, float) or not isinstance(display, str):
                continue
            text = display.strip()
            if (not text or re.match(r"^/[\w:-]+(?:\s|$)|^!", text)
                    or text.startswith(INJECTED + CLAUDE_WRAPPERS)):
                continue
            # Pasted content and images may be documents, code or someone else's words.
            # Only the user's typed pieces are recoverable verbatim as separate spans.
            parts = [part.strip() for part in PASTE_MARKER.split(text) if part.strip()]
            uid = hashlib.sha256(json.dumps([sid, stamp, display], ensure_ascii=False).encode()).hexdigest()
            row = {"role": "user", "session_id": sid, "line": line, "id": "input-" + uid,
                   "timestamp": stamp, "text": "\n".join(parts), "evidence_level": "input_history"}
            if len(parts) > 1:
                row["parts"] = parts
            if not parts:
                row["input_method"] = "attachment_or_paste"
            yield row


class MultipleExportsError(ValueError):
    """A composite ZIP does not identify which account's export is intended."""


def chatgpt_threads(path, member=None):
    if path.suffix.lower() != ".zip":
        with path.open(encoding="utf-8-sig") as fin:
            data = json.load(fin)
        if not isinstance(data, list):
            raise ValueError("unrecognized conversation export")
        yield from ((obj, None) for obj in data)
        return
    with ZipFile(path) as archive:
        members = [k for k in archive.namelist() if EXPORT_NAME.fullmatch(Path(k).name)]
        if not members or (member and member not in members):
            raise ValueError("conversation file missing from export")
        if len({Path(k).parent for k in members}) > 1:
            raise MultipleExportsError("压缩包里有多个聊天导出目录。请分别使用各自的导出文件。")
        for name in ([member] if member else members):
            with archive.open(name) as fin:
                data = json.load(fin)
            if not isinstance(data, list):
                raise ValueError("unrecognized conversation export")
            yield from ((obj, name) for obj in data)


def chatgpt_graph(mapping, current):
    """Index parent links once. Depths certify which nodes lead to a real root."""
    children = defaultdict(list)
    incomplete = False
    for key, node in mapping.items():
        if not isinstance(node, dict) or "parent" not in node or not isinstance(node["parent"], (str, type(None))):
            incomplete = True
            continue
        children[node["parent"]].append(key)
        for child in node.get("children") or []:
            if not isinstance(child, str) or not isinstance(mapping.get(child), dict) or mapping[child].get("parent") != key:
                incomplete = True
    roots = children[None]
    pending = deque((key, 1) for key in roots)
    depths = {}
    while pending:
        key, depth = pending.popleft()
        depths[key] = depth
        pending.extend((child, depth+1) for child in children[key])
    active_next = {}
    has_current = isinstance(current, str) and current in depths
    if has_current:
        key = current
        while mapping[key]["parent"] is not None:
            parent = mapping[key]["parent"]
            active_next[parent] = key
            key = parent
    incomplete |= len(roots) != 1 or len(depths) != len(mapping) or bool(current and not has_current)
    return children, depths, active_next, incomplete


def chatgpt_branch(mapping, anchor, children, active_next, incomplete):
    if anchor not in mapping:
        return
    if incomplete:
        # A broken link can hide a sibling or a speaker. Only the anchor is verified.
        yield anchor
        return
    ancestors, key = [], anchor
    while key is not None:
        ancestors.append(key)
        key = mapping[key]["parent"]
    yield from reversed(ancestors)
    key = anchor
    while children[key]:
        if key in active_next:
            key = active_next[key]
        elif len(children[key]) == 1:
            key = children[key][0]
        else:
            break  # No selected branch here. Multiple alternative answers cannot be attributed.
        yield key


def chatgpt_messages(thread, member, stats, target=None):
    sid = thread.get("conversation_id") or thread.get("id")
    mapping = thread.get("mapping") or {}
    if not sid or not isinstance(mapping, dict) or not mapping:
        stats["unrecognized_threads"] += 1
        return
    children, depths, active_next, incomplete = chatgpt_graph(mapping, thread.get("current_node"))
    if incomplete:
        stats["incomplete_branch_threads"] += 1
    keys = (chatgpt_branch(mapping, target["node"], children, active_next, incomplete)
            if target else mapping)
    for key in keys:
        if not isinstance(mapping[key], dict):
            continue
        msg = mapping[key].get("message") or {}
        role = (msg.get("author") or {}).get("role")
        metadata = msg.get("metadata") or {}
        content = msg.get("content") or {}
        if (role not in ("user", "assistant") or msg.get("recipient") not in (None, "all")
                or msg.get("channel") not in (None, "final") or any(metadata.get(k) for k in HIDDEN)
                or content.get("content_type") not in ("text", "multimodal_text")):
            continue
        raw_parts = content.get("parts") or []
        parts = [p for p in raw_parts if isinstance(p, str) and p.strip()]
        # A sent screenshot or file is a user turn even when no caption can be quoted.
        has_upload = role == "user" and (
            any(isinstance(p, dict) and p.get("content_type") in ("image_asset_pointer", "audio_asset_pointer",
                "video_asset_pointer") and p.get("asset_pointer") for p in raw_parts)
            or any(isinstance(a, dict) and a.get("id") for a in (metadata.get("attachments") or [])))
        if parts or has_upload:
            row = {"role": role, "session_id": sid, "id": msg.get("id") or key, "node": key,
                   "timestamp": msg.get("create_time"), "text": "\n".join(parts)}
            if key in depths:
                row["ordinal"] = depths[key]
            if incomplete:
                row["incomplete_thread"] = True
            if member:
                row["member"] = member
            yield row


def shared_messages(client, path, stats, target=None):
    if client == "claude":
        if path.name == "history.jsonl" and path.parent.parent.name != "projects":
            yield from claude_input_history(path, stats)
        else:
            yield from claude_messages(path, stats)
    elif client == "chatgpt":
        for thread, member in chatgpt_threads(path, (target or {}).get("member")):
            if not target or (thread.get("conversation_id") or thread.get("id")) == target["session_id"]:
                yield from chatgpt_messages(thread, member, stats, target)


def claude_branch(target, rows):
    # A resumed transcript can have siblings. Respect the actual parent pointer and stop
    # at an ambiguous follow-up; tool-only rows have already been collapsed into their parent.
    visible, children = {}, defaultdict(list)
    for row in rows:
        if row["session_id"] == target["session_id"] and row["id"] not in visible:
            visible[row["id"]] = row
            children[row.get("parent_id")].append(row)
    current = visible.get(target["id"])
    if not current:
        return
    before = []
    while len(before) < 4:
        current = visible.get(current.get("parent_id"))
        if not current:
            break
        before.append(current)
        if current["role"] == "user":
            break
    yield from reversed(before)
    current = visible[target["id"]]
    yield current
    for _ in range(4):
        next_rows = children.get(current["id"], [])
        if len(next_rows) != 1:
            break
        current = next_rows[0]
        yield current
        if current["role"] == "user":
            break


def read_shared_window(target, source, budget):
    from read_context import pack_message

    prior, following, anchor = [], [], None
    seen = set()
    rows = shared_messages(target["client"], source, Counter(), target)
    if target["client"] == "claude" and "parent_id" in target:
        rows = claude_branch(target, rows)
    for row in rows:
        if row["session_id"] != target["session_id"] or row["id"] in seen:
            continue
        seen.add(row["id"])
        if row["id"] == target["id"]:
            if (row["role"] != "user" or row["text"] != target["text"] or row["timestamp"] != target["timestamp"] or
                    row.get("node") != target.get("node") or row.get("line") != target.get("line")):
                raise ValueError("original message no longer matches index")
            if row.get("evidence_level") == "input_history":
                message = pack_message("user", row.get("parts", [row["text"]] if row["text"] else []), row["line"], budget,
                                       row["id"], row["timestamp"])
                return {"target_id": row["id"], "session_id": row["session_id"], "messages": [message],
                        "evidence_level": "input_history", "assistant_context_available": False}
            anchor = row
        elif anchor:
            following.append(row)
            if row["role"] == "user" or len(following) == 4:
                break
        else:
            if row["role"] == "user":
                prior = []
            prior = (prior + [row])[-4:]
    if not anchor:
        raise ValueError("original message not found at its indexed location")
    messages = []
    for row in prior + [anchor] + following:
        rendered = pack_message(row["role"], [row["text"]] if row["text"] else [], row.get("line", row.get("ordinal")),
                                budget, row["id"], row["timestamp"])
        if "node" in row:
            rendered["node"] = row["node"]
            ordinal = rendered.pop("line")
            if ordinal is not None:
                rendered["ordinal"] = ordinal
        messages.append(rendered)
    result = {"target_id": target["id"], "session_id": target["session_id"], "messages": messages}
    if anchor.get("incomplete_thread"):
        result.update(incomplete_thread=True, assistant_context_available=False)
    return result


def source_files(client, root, export):
    if client == "chatgpt":
        if not export or root:
            raise ValueError("chatgpt needs one explicitly supplied --export file or directory")
        if export.is_file():
            return [export]
        if export.is_dir():
            return sorted(p for p in export.iterdir() if p.is_file() and EXPORT_NAME.fullmatch(p.name))
        raise ValueError("export not found")
    if export:
        raise ValueError("--export applies to chatgpt")
    if client == "codex":
        root = root or Path(os.environ.get("CODEX_HOME") or Path.home()/".codex")
        return sorted((root/"sessions").glob("*/*/*/rollout-*.jsonl")) + sorted((root/"archived_sessions").glob("rollout-*.jsonl"))
    root = root or Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home()/".claude")
    transcripts = sorted(p for p in (root/"projects").glob("*/*.jsonl") if not p.name.startswith("agent-"))
    history = root/"history.jsonl"
    return transcripts + ([history] if history.is_file() else [])


def codex_sources(paths):
    """Visit parents before descendants, even when an archived parent sorts last."""
    parents, sources = {}, []
    for path in paths:
        try:
            with path.open("rb") as stream:
                meta = json.loads(next(stream, b"{}")).get("payload") or {}
            sid = meta.get("session_id") or meta.get("id")
            if sid and meta.get("forked_from_id"):
                parents[sid] = meta["forked_from_id"]
        except (OSError, ValueError, AttributeError):
            sid = None
        sources.append((path, sid))
    ordered = []
    for path, sid in sources:
        root, visited = sid, set()
        while root in parents and root not in visited:
            visited.add(root)
            root = parents[root]
        ordered.append((len(visited), path, root))
    return [(path, root) for _, path, root in sorted(ordered)]


def readable_records(client, path, stats, origins=None, family=None):
    try:
        if client == "codex":
            yield from codex_rows(path, stats, origins, family)
        else:
            yield from shared_messages(client, path, stats)
    except MultipleExportsError:
        raise
    except (OSError, ValueError, BadZipFile, TypeError, AttributeError, KeyError):
        stats["unreadable_sources"] += 1


def coverage_key(kind, value):
    return hashlib.sha256(f"{kind}/{value}".encode("utf-8")).hexdigest()


def collect(client, paths, year, zone, out):
    daily, months, sessions, seen = Counter(), Counter(), set(), set()
    unplaced = defaultdict(set)
    incomplete = set()
    checksum = hashlib.sha256()
    stats = Counter()
    origins, independent = {}, set()
    transcript_inputs, input_history_days = defaultdict(list), set()
    input_history_messages = 0
    owner_messages, owner_threads = Counter(), defaultdict(set)
    sources = codex_sources(paths) if client == "codex" else [(path, None) for path in paths]
    for path, family in sources:
        path = path.absolute()
        error_keys = ("unreadable_records", "unreadable_sources", "unverifiable_fork_turns")
        before = sum(stats[k] for k in error_keys)
        for row in readable_records(client, path, stats, origins, family):
            if row.get("incomplete_thread"):
                incomplete.add(coverage_key("thread", row["session_id"]))
            if row.pop("role", "user") != "user" or row["id"] in seen:
                continue
            day = date_in_zone(row["timestamp"], zone)
            if not day:
                unplaced[row["id"]].add(row["session_id"])
                continue
            seen.add(row["id"])
            if int(day[:4]) != year:
                continue
            if client == "claude":
                # The two stores can stamp a submission slightly apart. Pair only
                # one near-simultaneous identical input on the same local day.
                key = (row["session_id"], day, row["text"].strip())
                timestamp = parse_timestamp(row["timestamp"]).timestamp()
                if row.get("evidence_level") == "input_history":
                    times = transcript_inputs.get(key)
                    if times:
                        nearest = min(range(len(times)), key=lambda i: abs(times[i]-timestamp))
                        if abs(times[nearest]-timestamp) <= 60:
                            times.pop(nearest)
                            continue
                    input_history_messages += 1
                    input_history_days.add(day)
                    incomplete.add(coverage_key("source", path))
                else:
                    transcript_inputs[key].append(timestamp)
            sessions.add(row["session_id"])
            if "owner_group" in row:
                owner_messages[row["owner_group"]] += 1
                owner_threads[row["owner_group"]].add(row["session_id"])
            independent.add(row.get("conversation_id", row["session_id"]))
            daily[day] += 1
            months[day[:7]] += 1
            row.update(client=client, date=day, source=str(path))
            line = json.dumps(row, ensure_ascii=False) + "\n"
            checksum.update(line.encode("utf-8"))
            out.write(line)
        if sum(stats[k] for k in error_keys) > before:
            incomplete.add(coverage_key("source", path))
    for mid in unplaced.keys() - seen:
        stats["undated_turns"] += 1
        incomplete.update(coverage_key("thread", sid) for sid in unplaced[mid])
    owners = {key: {"messages": n, "threads": len(owner_threads[key])} for key, n in sorted(owner_messages.items())}
    return {"client": client, "year": year, "source_files_considered": len(paths), "owner_groups": owners,
            "user_turns_before_editorial_filter": sum(months.values()),
            "input_history_messages": input_history_messages, "input_history_active_dates": len(input_history_days),
            "threads": len(sessions), "conversation_families": len(independent), "days": len(daily), "months": dict(sorted(months.items())),
            "daily_before_editorial_filter": dict(sorted(daily.items())), "index_sha256": checksum.hexdigest(),
            "first": min(daily, default=None), "last": max(daily, default=None), "skipped": dict(stats),
            "incomplete_scope_digests": sorted(incomplete)}


class OwnerScopeError(ValueError):
    """Safe, fixed user-facing errors for filtering a private local index."""


def scope_owner_index(index, inventory_path, group, session, out):
    """Partition an existing reviewed-source inventory. Keep its original locators and exclusions."""
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory.get("client") != "codex" or not inventory.get("owner_groups"):
        raise OwnerScopeError("请用当前版本重新盘点 Codex 本地记录。")
    if session:
        with index.open(encoding="utf-8") as stream:
            groups = {row.get("owner_group") for row in map(json.loads, stream) if row["session_id"] == session}
        if len(groups) != 1 or groups & {None, "unknown"}:
            raise OwnerScopeError("这个会话缺少唯一可核的账号标识。可按盘点中的分区分别查看。")
        group = groups.pop()
    if group not in inventory["owner_groups"]:
        raise OwnerScopeError("选择的账号分区不在这份盘点中。")
    parent_digest, digest = hashlib.sha256(), hashlib.sha256()
    daily, months = Counter(), Counter()
    sessions, families, sources = set(), set(), set()
    with index.open(encoding="utf-8") as stream:
        for line in stream:
            data = line.encode("utf-8")
            parent_digest.update(data)
            row = json.loads(line)
            if row["owner_group"] != group:
                continue
            out.write(line)
            digest.update(data)
            daily[row["date"]] += 1
            months[row["date"][:7]] += 1
            sessions.add(row["session_id"])
            families.add(row.get("conversation_id", row["session_id"]))
            sources.add(row["source"])
    if parent_digest.hexdigest() != inventory["index_sha256"]:
        raise OwnerScopeError("索引已改变，请使用与盘点配套的原索引。")
    relevant = {coverage_key("source", p) for p in sources} | {coverage_key("thread", s) for s in sessions}
    count = sum(daily.values())
    return {"client": "codex", "year": inventory["year"], "owner_group": group,
            "owner_groups": {group: {"messages": count, "threads": len(sessions)}},
            "source_files_considered": len(sources), "threads": len(sessions), "conversation_families": len(families),
            "user_turns_before_editorial_filter": count, "days": len(daily), "months": dict(sorted(months.items())),
            "daily_before_editorial_filter": dict(sorted(daily.items())), "first": min(daily, default=None),
            "last": max(daily, default=None), "index_sha256": digest.hexdigest(), "parent_index_sha256": inventory["index_sha256"],
            "incomplete_scope_digests": sorted(relevant.intersection(inventory["incomplete_scope_digests"])),
            "parent_skipped": inventory.get("skipped", {})}


def reviewed_calendar(index, inventory_path, exclusions_path):
    """Count the inventoried source once, excluding identified report controls or other ineligible turns."""
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    excluded = json.loads(exclusions_path.read_text(encoding="utf-8"))
    if (not isinstance(inventory, dict) or not isinstance(excluded, list) or
            any(not isinstance(mid, str) or not mid for mid in excluded)):
        raise ValueError("invalid inventory or exclusions")
    remaining = set(excluded)
    checksum = hashlib.sha256()
    daily = Counter()
    observed = set()
    incomplete = set(inventory.get("incomplete_scope_digests", []))
    # Legacy inventories identified missing dates but did not locate the affected threads.
    legacy_gap = "incomplete_scope_digests" not in inventory and any(
        inventory.get("skipped", {}).get(key) for key in ("undated_turns", "unreadable_records", "unreadable_sources",
                                                         "unverifiable_fork_turns"))
    with index.open(encoding="utf-8") as stream:
        for line in stream:
            checksum.update(line.encode("utf-8"))
            row = json.loads(line)
            if row["id"] in remaining:
                remaining.remove(row["id"])
            elif legacy_gap or (incomplete and (coverage_key("source", row["source"]) in incomplete or
                                                coverage_key("thread", row["session_id"]) in incomplete)):
                observed.add(row["date"])
            else:
                daily[row["date"]] += 1
    if checksum.hexdigest() != inventory.get("index_sha256") or remaining:
        raise ValueError("use the original full inventory and exclusion IDs belonging to it")
    dates = ",".join(f"{day[5:]}:{count}:?" for day, count in sorted(daily.items()))
    return {"year": inventory["year"], "active_days": len(daily),
            "dated_user_messages": sum(daily.values()), "days": dates,
            "dates": ",".join(day[5:] for day in sorted(observed))}


def host_calendar(path, year, zone):
    """Aggregate the host's private projection of eligible messages without reading their text."""
    threads = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(threads, list):
        raise ValueError("expected array of threads")
    members, complete, dates = {}, set(), {}
    for thread in threads:
        sid = thread["id"]
        if (not isinstance(sid, str) or not sid or sid in members or
                not isinstance(thread["messages"], list) or type(thread["complete"]) is not bool):
            raise ValueError("merge each thread's pages before marking coverage")
        members[sid] = set()
        if thread["complete"]:
            complete.add(sid)
        for row in thread["messages"]:
            if row["role"] != "user":
                continue
            mid = row["id"]
            if not isinstance(mid, str) or not mid:
                raise ValueError("a verifiable message ID is required")
            members[sid].add(mid)
            day = date_in_zone(row.get("timestamp"), zone)
            if row.get("date"):
                local = date.fromisoformat(row["date"]).isoformat()
                if day and day != local:
                    raise ValueError("source timestamp disagrees with the specified local date")
                day = local
            if day:
                if mid in dates and dates[mid] != day:
                    raise ValueError("conflicting dates on repeated message ID")
                dates[mid] = day
    # A missing timestamp in a complete thread can fall on any day. Retain its verified
    # dates as observations until the source's message metadata resolves the gap.
    counted_ids = set()
    for sid in complete:
        if members[sid].issubset(dates):
            counted_ids.update(members[sid])
    daily, observed = Counter(), set()
    for mid, day in dates.items():
        if int(day[:4]) == year:
            if mid in counted_ids:
                daily[day] += 1
            else:
                observed.add(day)
    missing = set().union(*members.values()).difference(dates)
    return {"year": year, "timezone": str(zone), "dated_user_messages": sum(daily.values()),
            "days": ",".join(f"{day[5:]}:{n}:?" for day, n in sorted(daily.items())),
            "dates": ",".join(day[5:] for day in sorted(observed)),
            "missing_message_dates": len(missing)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--client", choices=("codex", "claude", "chatgpt"))
    mode.add_argument("--scope-index", type=Path, help="private Codex index to partition for one known metadata group")
    mode.add_argument("--calendar-from", type=Path, help="complete private index for the publication calendar")
    mode.add_argument("--host-ledger", type=Path, help="private per-thread role, ID and date metadata from host tools")
    parser.add_argument("--inventory", type=Path, help="saved collection summary matching that index")
    parser.add_argument("--exclude-ids", type=Path, help="reviewed JSON array of ineligible message IDs")
    parser.add_argument("--year", type=int)
    parser.add_argument("--timezone", help="IANA timezone, default: OS local")
    parser.add_argument("--root", type=Path, help="override the selected local client's config root")
    parser.add_argument("--export", type=Path, help="explicitly provided ChatGPT JSON, ZIP, or export directory")
    parser.add_argument("--output", type=Path, help="new private JSONL file (never overwritten)")
    selectors = parser.add_mutually_exclusive_group()
    selectors.add_argument("--owner-group", help="group from the private inventory, or unknown for separate review")
    selectors.add_argument("--owner-session", help="match the recorded creator of this existing user session")
    args = parser.parse_args()
    try:
        if bool(args.scope_index) != bool(args.owner_group or args.owner_session):
            parser.error("--scope-index requires one of --owner-group or --owner-session")
        if args.host_ledger:
            if (not args.year or not args.timezone or args.inventory or args.exclude_ids
                    or args.export or args.output or args.root):
                parser.error("--host-ledger requires --year and --timezone only")
            print(json.dumps(host_calendar(args.host_ledger, args.year, ZoneInfo(args.timezone))))
            return
        if args.calendar_from:
            if not (args.inventory and args.exclude_ids):
                parser.error("--calendar-from requires --inventory and --exclude-ids")
            if args.year or args.output or args.root or args.export or args.timezone:
                parser.error("--calendar-from uses the dates and scope of its inventory")
            print(json.dumps(reviewed_calendar(args.calendar_from, args.inventory, args.exclude_ids)))
            return
        if args.scope_index:
            if not (args.inventory and args.output) or args.year or args.root or args.export or args.timezone or args.exclude_ids:
                parser.error("--scope-index requires its --inventory, an owner selector and a new --output")
        else:
            if not (args.year and args.output) or args.inventory or args.exclude_ids:
                parser.error("--client requires --year and --output; calendar options belong to --calendar-from")
            zone = ZoneInfo(args.timezone) if args.timezone else None
            paths = source_files(args.client, args.root, args.export)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                if args.scope_index:
                    result = scope_owner_index(args.scope_index, args.inventory, args.owner_group, args.owner_session, out)
                else:
                    result = collect(args.client, paths, args.year, zone, out)
        except BaseException:
            args.output.unlink(missing_ok=True)
            raise
        print(json.dumps(result, ensure_ascii=False))
    except (OwnerScopeError, MultipleExportsError) as exc:
        parser.exit(1, str(exc) + "\n")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, "Could not collect authorized history: " + type(exc).__name__ + ".\n")


if __name__ == "__main__":
    main()
