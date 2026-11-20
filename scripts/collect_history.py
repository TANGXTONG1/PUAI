#!/usr/bin/env python3
"""Index one authorized history locally. Stdout contains counts only; JSONL contains private text."""
import argparse
from collections import Counter, defaultdict
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


def date_in_zone(value, zone):
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
        return dt.astimezone(zone).date().isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def local_id(session, line, parts):
    # Legacy Codex logs have no native message IDs. Verify both the locator and exact text.
    text = json.dumps([session, line, parts], ensure_ascii=False, separators=(",", ":"))
    return "local-" + hashlib.sha256(text.encode()).hexdigest()


def codex_rows(path, stats):
    from read_context import visible_message

    by_family = {"response_item": [], "event_msg": []}
    with path.open("rb") as fin:
        header = json.loads(next(fin, b"{}"))
        meta = header.get("payload") or {}
        sid = meta.get("session_id") or meta.get("id")
        if header.get("type") != "session_meta" or not sid:
            stats["unrecognized_sources"] += 1
            return
        if meta.get("thread_source") not in (None, "user") or isinstance(meta.get("source"), dict):
            return
        for line, raw in enumerate(fin, 2):
            # Most bytes in a rollout are tool output. Do not decode it into working memory.
            if b'"user"' not in raw and b'"user_message"' not in raw:
                continue
            try:
                record = json.loads(raw)
            except (ValueError, UnicodeError):
                stats["unreadable_records"] += 1
                continue
            family = record.get("type")
            if family not in by_family:
                continue
            message = visible_message(record, family)
            if not message or message[0] != "user" or not message[1]:
                continue
            _, parts, mid = message
            if meta.get("forked_from_id") and not mid:
                # A legacy fork gives its inherited turns fresh locators with no original IDs.
                stats["unverifiable_fork_turns"] += 1
                continue
            row = {"session_id": sid, "line": line, "id": mid or local_id(sid, line, parts),
                   "timestamp": record.get("timestamp"), "text": "\n".join(parts)}
            by_family[family].append(row)
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
            if isinstance(content, str):
                parts = [content]
            elif isinstance(content, list):
                if role == "user" and any(isinstance(p, dict) and p.get("type") == "tool_result" for p in content):
                    continue
                parts = [p["text"] for p in content if isinstance(p, dict) and p.get("type") == "text"
                         and isinstance(p.get("text"), str)]
            else:
                continue
            parts = [p for p in parts if p.strip() and
                     (role != "user" or not p.lstrip().startswith(INJECTED + CLAUDE_WRAPPERS))]
            if parts:
                visible_ancestor[uid] = uid
                message = {"role": role, "session_id": row["sessionId"], "id": uid, "line": line,
                           "timestamp": row.get("timestamp"), "text": "\n".join(parts)}
                if "parentUuid" in row:
                    message["parent_id"] = parent
                yield message


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
        for name in ([member] if member else members):
            with archive.open(name) as fin:
                data = json.load(fin)
            if not isinstance(data, list):
                raise ValueError("unrecognized conversation export")
            yield from ((obj, name) for obj in data)


def chatgpt_messages(thread, member, stats):
    sid = thread.get("conversation_id") or thread.get("id")
    mapping = thread.get("mapping") or {}
    if not sid or not mapping:
        stats["unrecognized_threads"] += 1
        return
    node = thread.get("current_node")
    if not node:
        leaves = [k for k, v in mapping.items() if not v.get("children")]
        if len(leaves) == 1:
            node = leaves[0]
    # Only the selected branch belongs to the displayed conversation, including regenerated replies.
    chain, visited = [], set()
    while node:
        if node in visited or node not in mapping:
            chain = []
            break
        chain.append(node)
        visited.add(node)
        node = mapping[node].get("parent")
    if not chain:
        stats["unrecognized_threads"] += 1
        return
    for ordinal, key in enumerate(reversed(chain), 1):
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
                   "ordinal": ordinal, "timestamp": msg.get("create_time"), "text": "\n".join(parts)}
            if member:
                row["member"] = member
            yield row


def shared_messages(client, path, stats, target=None):
    if client == "claude":
        yield from claude_messages(path, stats)
    elif client == "chatgpt":
        for thread, member in chatgpt_threads(path, (target or {}).get("member")):
            if not target or (thread.get("conversation_id") or thread.get("id")) == target["session_id"]:
                yield from chatgpt_messages(thread, member, stats)


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
        raise ValueError("original message not found on the active branch")
    messages = []
    for row in prior + [anchor] + following:
        rendered = pack_message(row["role"], [row["text"]] if row["text"] else [], row.get("line", row.get("ordinal")),
                                budget, row["id"], row["timestamp"])
        if "node" in row:
            rendered["node"] = row["node"]
            rendered["ordinal"] = rendered.pop("line")
        messages.append(rendered)
    return {"target_id": target["id"], "session_id": target["session_id"], "messages": messages}


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
    return sorted(p for p in (root/"projects").glob("*/*.jsonl") if not p.name.startswith("agent-"))


def codex_source_order(path):
    # Archived parent sessions may contain the original date/locator for IDs replayed in forks.
    try:
        with path.open("rb") as stream:
            meta = json.loads(next(stream, b"{}")).get("payload") or {}
        return bool(meta.get("forked_from_id")), str(meta.get("timestamp", "")), str(path)
    except (OSError, ValueError, AttributeError):
        return True, "", str(path)


def readable_records(client, path, stats):
    try:
        if client == "codex":
            yield from codex_rows(path, stats)
        else:
            yield from shared_messages(client, path, stats)
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
    if client == "codex":
        paths = sorted(paths, key=codex_source_order)
    for path in paths:
        path = path.absolute()
        error_keys = ("unreadable_records", "unreadable_sources", "unverifiable_fork_turns")
        before = sum(stats[k] for k in error_keys)
        for row in readable_records(client, path, stats):
            if row.pop("role", "user") != "user" or row["id"] in seen:
                continue
            day = date_in_zone(row["timestamp"], zone)
            if not day:
                unplaced[row["id"]].add(row["session_id"])
                continue
            seen.add(row["id"])
            if int(day[:4]) != year:
                continue
            sessions.add(row["session_id"])
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
    return {"client": client, "year": year, "source_files_considered": len(paths),
            "user_turns_before_editorial_filter": sum(months.values()),
            "threads": len(sessions), "days": len(daily), "months": dict(sorted(months.items())),
            "daily_before_editorial_filter": dict(sorted(daily.items())), "index_sha256": checksum.hexdigest(),
            "first": min(daily, default=None), "last": max(daily, default=None), "skipped": dict(stats),
            "incomplete_scope_digests": sorted(incomplete)}


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
    mode.add_argument("--calendar-from", type=Path, help="complete private index for the publication calendar")
    mode.add_argument("--host-ledger", type=Path, help="private per-thread role, ID and date metadata from host tools")
    parser.add_argument("--inventory", type=Path, help="saved collection summary matching that index")
    parser.add_argument("--exclude-ids", type=Path, help="reviewed JSON array of ineligible message IDs")
    parser.add_argument("--year", type=int)
    parser.add_argument("--timezone", help="IANA timezone, default: OS local")
    parser.add_argument("--root", type=Path, help="override the selected local client's config root")
    parser.add_argument("--export", type=Path, help="explicitly provided ChatGPT JSON, ZIP, or export directory")
    parser.add_argument("--output", type=Path, help="new private JSONL file (never overwritten)")
    args = parser.parse_args()
    try:
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
        if not (args.year and args.output) or args.inventory or args.exclude_ids:
            parser.error("--client requires --year and --output; calendar options belong to --calendar-from")
        zone = ZoneInfo(args.timezone) if args.timezone else None
        paths = source_files(args.client, args.root, args.export)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                result = collect(args.client, paths, args.year, zone, out)
        except BaseException:
            args.output.unlink(missing_ok=True)
            raise
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, "Could not collect authorized history: " + type(exc).__name__ + ".\n")


if __name__ == "__main__":
    main()
