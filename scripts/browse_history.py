#!/usr/bin/env python3
"""Browse an authorized PUAI user-message index locally, across months and threads."""

import argparse
from collections import defaultdict, deque
from itertools import islice
import json
import os
from pathlib import Path
import re


def interleave(groups):
    """Take one entry per nonempty group before revisiting a group."""
    active = deque(map(iter, groups))
    while active:
        group = active.popleft()
        entry = next(group, None)
        if entry is not None:
            yield entry
            active.append(group)


def spread(rows, phase):
    # Rotate the first sample across first/middle/last turns of different conversations.
    # Revisit each third in turn so subsequent pages still contain every message.
    if len(rows) < 3:
        return iter(rows if not phase % 2 else reversed(rows))
    third = len(rows) // 3
    regions = [rows[:third], rows[third:2 * third], reversed(rows[2 * third:])]
    return interleave(regions[phase:] + regions[:phase])


def calendar_order(groups):
    """Balance the months represented by the next entry of each independent conversation."""
    while groups:
        months = defaultdict(list)
        for stream in groups:
            item = next(stream, None)
            if item is not None:
                months[item["date"][:7]].append((item, stream))
        groups = []
        for item, stream in interleave(months[m] for m in sorted(months)):
            yield item
            groups.append(stream)


def full_page(threads, page, limit, page_chars):
    """Page by source characters as well as rows. Offsets are Python Unicode code points."""
    current, used, count, entries = 1, 0, 0, []
    total_chars = sum(len(row["text"]) for rows in threads.values() for row in rows)
    for rows in threads.values():
        for row in rows:
            text = row["text"]
            start = 0
            while start < len(text):
                if count >= limit or used >= page_chars:
                    current, used, count = current + 1, 0, 0
                end = min(start + (page_chars - used), len(text))
                if page == current:
                    entries.append({**row, "text": text[start:end], "char_start": start,
                                    "char_end": end, "message_chars": len(text)})
                used += end - start
                count += 1
                start = end
    pages = current if total_chars else 0
    return {"matched_characters": total_chars, "pages": pages, "page_char_limit": page_chars,
            "next_page": page + 1 if page < pages else None, "entries": entries}


def browse(index, terms, page, limit, overview=False, exclude_sessions=(), *,
           full_text=False, page_chars=6000, months=(), sessions=()):
    if page < 1 or not 1 <= limit <= 100:
        raise ValueError("invalid page or limit")
    if (overview and full_text) or not 1 <= page_chars <= 65536:
        raise ValueError("invalid full-text page settings")
    pattern = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE) if terms else None
    threads = defaultdict(list)
    excluded, included = set(exclude_sessions), set(sessions)
    with index.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            session = row["session_id"]
            family = row.get("conversation_id", session)
            if session in exclude_sessions:
                excluded.add(family)
            if session in sessions:
                included.add(family)
            if months and row["date"][:7] not in months:
                continue
            message = row["text"]
            if not message:  # Uncaptioned uploads count in the calendar but supply no quote.
                continue
            match = pattern.search(message) if pattern else None
            if pattern and not match:
                continue
            entry = {key: row[key] for key in ("id", "session_id", "date", "source")}
            entry["conversation_id"] = family
            for field in ("owner_group", "evidence_level", "input_method"):
                if field in row:
                    entry[field] = row[field]
            if full_text:
                entry["text"] = message
                if row.get("parts") and len(row["parts"]) > 1:
                    # The input-history reader joins disjoint typed spans with newlines.
                    # Reopening the source preserves the boundaries for verbatim publication.
                    entry["disjoint_parts"] = True
            else:
                start = max(0, match.start() - 52) if match else 0
                entry["excerpt"] = message[start:start + 160]
                entry["clipped"] = start > 0 or len(entry["excerpt"]) < len(message)
            threads[family].append(entry)
    for family in list(threads):
        if family in excluded or (included and family not in included):
            del threads[family]
    months = set()
    groups = []
    # An unfiltered first pass should surface exchanges with a middle and an ending.
    # Each conversation still gets a turn; literal memory searches also keep one-off hits.
    candidates = threads.items() if terms else sorted(threads.items(), key=lambda pair: len(pair[1]) < 3)
    for phase, (family, rows) in enumerate(candidates):
        # Stable within-day input order keeps source order for a thread's follow-up turns.
        rows.sort(key=lambda row: row["date"])
        months.update(row["date"][:7] for row in rows)
        if full_text:
            continue
        if overview:
            sample_indices = sorted({0, len(rows) // 2, len(rows)-1})
            card = {"conversation_id": family, "first": rows[0]["date"], "last": rows[-1]["date"],
                    "matched_messages": len(rows), "samples": [rows[i] for i in sample_indices]}
            input_only = sum(row.get("evidence_level") == "input_history" for row in rows)
            if input_only:
                card["input_history_messages"] = input_only
            groups.append(iter([{"date": rows[len(rows)//2]["date"], "card": card}]))
        else:
            groups.append(spread(rows, (phase + 1) % 3))
    total = sum(len(rows) for rows in threads.values())
    summary = {"matched_messages": total, "matched_threads": len(threads), "matched_months": len(months), "page": page}
    if full_text:
        return {**summary, **full_page(threads, page, limit, page_chars)}
    count = len(threads) if overview else total
    offset = (page - 1) * limit
    entries = list(islice(calendar_order(groups), offset, offset + limit)) if offset < count else []
    return {**summary, "next_page": page + 1 if offset + len(entries) < count else None,
            "entries": [item["card"] for item in entries] if overview else entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, help="private index from collect_history.py")
    parser.add_argument("--term", action="append", default=[], help="match any supplied literal")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--overview", action="store_true", help="one card per conversation family, with up to three source locators")
    mode.add_argument("--full-text", action="store_true", help="read every matching user message, including continuations")
    parser.add_argument("--page-chars", type=int, help="maximum source characters on a full-text page (default 6000)")
    parser.add_argument("--month", action="append", default=[], help="select a calendar month YYYY-MM; repeat for a range")
    parser.add_argument("--session", action="append", default=[], help="select a conversation family or a member session")
    parser.add_argument("--exclude-session", action="append", default=[], help="skip a reviewed session and its known fork family")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--output", type=Path, required=True, help="new private JSON file")
    args = parser.parse_args()
    if args.page_chars is not None and not args.full_text:
        parser.error("--page-chars requires --full-text")
    if any(not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", month) for month in args.month):
        parser.error("--month must be YYYY-MM")
    try:
        result = browse(args.index, [t for t in args.term if t.strip()], args.page, args.limit, args.overview,
                        args.exclude_session, full_text=args.full_text, page_chars=args.page_chars if args.page_chars is not None else 6000,
                        months=args.month, sessions=args.session)
        # Private source paths and snippets belong in the requested file, not in stdout.
        with open(args.output, "x", encoding="utf-8", opener=private_file) as stream:
            try:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            except OSError:
                args.output.unlink(missing_ok=True)
                raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Could not browse private index ({type(error).__name__}).\n")


def private_file(path, flags):
    return os.open(path, flags, 0o600)


if __name__ == "__main__":
    main()
