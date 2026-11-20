#!/usr/bin/env python3
"""Open one indexed Codex rollout around a selected user message. Output contains private text.

Both the local JSONL index (id, source, 1-based line, optional session_id) and its
authorized rollout must be supplied. Use a verified user index, preferably with all user
messages. An unindexed ordinary user turn is an opaque boundary. This is a reader for
response_item.message and event_msg.user_message / agent_message, not an account search.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys


INJECTED = ("[System Error]", "<environment_context>", "<INSTRUCTIONS>", "# AGENTS.md",
            "<subagent_notification>", "<permissions instructions>", "<paseo-system",
            "<turn_aborted>", "Message Type: ", "The user approved the plan. Implement it now.")


def read_index(index, source, message_id):
    locators = {}
    target = None
    with index.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            raw_path = row.get("source")
            if not isinstance(raw_path, str) or not raw_path or Path(raw_path) != source:
                continue
            number = row["line"]
            if type(number) is not int or number < 1 or not isinstance(row.get("id"), str):
                raise ValueError("invalid locator in the requested source")
            if number in locators:
                raise ValueError("ambiguous source line in index")
            locators[number] = row["id"]
            if row["id"] == message_id:
                if target:
                    raise ValueError("ambiguous target in index")
                target = row
    if target is None:
        raise ValueError("message ID and explicit source do not match the index")
    return target, locators


def visible_message(record, family):
    if record.get("type") != family or record.get("replayed") or record.get("is_replay"):
        return None
    payload = record.get("payload", {})
    if payload.get("replayed") or payload.get("is_replay") or payload.get("recipient") not in (None, "all"):
        return None
    kind = payload.get("type")
    if family == "response_item" and kind == "message":
        role = payload.get("role")
        parts = [p["text"] for p in payload.get("content", [])
                 if isinstance(p, dict) and p.get("type") in ("input_text", "output_text", "text")
                 and isinstance(p.get("text"), str) and p["text"]]
    elif family == "event_msg" and kind in ("user_message", "agent_message"):
        role = "user" if kind == "user_message" else "assistant"
        parts = [payload["message"]] if isinstance(payload.get("message"), str) and payload["message"] else []
    else:
        return None
    if role not in ("user", "assistant"):
        return None
    if role == "assistant" and (not parts or payload.get("phase") not in (None, "final", "final_answer")
                                or payload.get("channel") not in (None, "final", "assistant")
                                or payload.get("hidden") or payload.get("is_hidden_from_user")):
        return None
    if role == "user" and parts:
        parts = [part for part in parts if not part.lstrip().startswith(INJECTED)]
        if not parts:
            return None
    message_id = payload.get("id") or payload.get("message_id")
    return role, parts, message_id


def pack_message(role, parts, number, budget, message_id, timestamp):
    result = {"role": role, "line": number, "parts": []}
    if message_id:
        result["id"] = message_id
    if isinstance(timestamp, str):
        result["record_timestamp"] = timestamp
    for part in parts:
        if len(part) <= budget:
            result["parts"].append(part)
            budget -= len(part)
        elif budget:
            result["parts"].append({"prefix": part[:budget], "omitted_characters": len(part) - budget})
            budget = 0
        else:
            result["parts"].append({"omitted_characters": len(part)})
    if not parts:
        result["text_unavailable"] = True
    return result


def read_window(index, source, message_id, budget=4000):
    if budget < 1:
        raise ValueError("max-chars must be positive")
    target, locators = read_index(index, source, message_id)
    anchor = target["line"]
    with source.open(encoding="utf-8") as stream:
        anchor_record = next((json.loads(row) for i, row in enumerate(stream, 1) if i == anchor), {})
    family = anchor_record.get("type")
    candidate = visible_message(anchor_record, family)
    if not candidate or candidate[0] != "user" or not candidate[2] or candidate[2] != message_id:
        raise ValueError("source line no longer matches the indexed user message ID")

    window = []
    omitted = Counter()
    seen_ids = set()
    before = after = "end_of_record"
    found = False
    with source.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            raw = json.loads(line)
            if raw.get("type") == "session_meta":
                meta = raw.get("payload", {})
                session_id = meta.get("session_id") or meta.get("id")
                if session_id and target.get("session_id") and session_id != target["session_id"]:
                    raise ValueError("session identity does not match locator")
                agent_source = isinstance(meta.get("source"), dict) and "subagent" in meta["source"]
                if meta.get("thread_source") not in (None, "user") or agent_source:
                    raise ValueError("source is not an ordinary user session")
            message = visible_message(raw, family)
            if message is None:
                continue
            role, parts, mid = message
            if mid and mid in seen_ids:
                if number == anchor:
                    raise ValueError("anchor is a replayed message ID")
                continue
            if mid:
                seen_ids.add(mid)
            if role == "user":
                indexed = mid is not None and locators.get(number) == mid
                boundary = "indexed_user" if indexed else "unverified_user"
                if number < anchor:
                    before = boundary
                    window = []
                    omitted.clear()
                    if indexed:
                        window.append(pack_message(role, parts, number, budget, mid, raw.get("timestamp")))
                elif number == anchor:
                    if not indexed:
                        raise ValueError("target changed while reading")
                    window.append(pack_message(role, parts, number, budget, mid, raw.get("timestamp")))
                    found = True
                else:
                    after = boundary
                    if indexed:
                        window.append(pack_message(role, parts, number, budget, mid, raw.get("timestamp")))
                    break
            elif found or before == "indexed_user":
                # At most three visible answers per interval, retaining first and latest.
                # The omission count prevents interpreting clipped sets as all replies.
                previous = [i for i, msg in enumerate(window) if msg["role"] == "assistant"
                            and (msg["line"] > anchor) == found]
                if len(previous) >= 3:
                    del window[previous[1]]
                    omitted["after_target" if found else "before_target"] += 1
                window.append(pack_message(role, parts, number, budget, mid, raw.get("timestamp")))
    if not found:
        raise ValueError("target disappeared while reading")
    return {"target_line": anchor, "before": before, "after": after,
            "omitted_assistant_answers": dict(omitted), "messages": window}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True, help="exact approved source path used in the index")
    parser.add_argument("--id", required=True)
    parser.add_argument("--output", type=Path, required=True, help="new private JSON file")
    parser.add_argument("--max-chars", type=int, default=4000, help="text budget per message, truncation is marked")
    args = parser.parse_args()
    try:
        data = read_window(args.index, args.source, args.id, args.max_chars)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        except BaseException:
            args.output.unlink(missing_ok=True)
            raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Parsing errors can contain fragments of the original JSON. Keep the CLI free of raw logs.
        explanation = str(error) if type(error) is ValueError else type(error).__name__
        parser.exit(1, f"Could not produce a verified private window ({explanation}).\n")


if __name__ == "__main__":
    main()
