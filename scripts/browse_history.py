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


def browse(index, terms, page, limit):
    if page < 1 or not 1 <= limit <= 100:
        raise ValueError("invalid page or limit")
    pattern = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE) if terms else None
    months = defaultdict(lambda: defaultdict(list))
    with index.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            message = row["text"]
            if not message:  # Attachment-only turns count in the calendar but supply no quote.
                continue
            match = pattern.search(message) if pattern else None
            if pattern and not match:
                continue
            start = max(0, match.start() - 52) if match else 0
            excerpt = message[start:start + 160]
            months[row["date"][:7]][row["session_id"]].append({
                "id": row["id"], "session_id": row["session_id"], "date": row["date"],
                "source": row["source"], "excerpt": excerpt,
                "clipped": start > 0 or len(excerpt) < len(message),
            })
    # Within a long conversation, sample both the initial question and later reactions.
    def spread(rows):
        if len(rows) < 4:
            return rows
        third = len(rows) // 3
        return interleave((rows[:third], rows[third:2 * third], reversed(rows[2 * third:])))

    # One dominant project or a dense month should not fill every page.
    stream = interleave(interleave(spread(rows) for rows in threads.values())
                        for _, threads in sorted(months.items()))
    total = sum(len(rows) for threads in months.values() for rows in threads.values())
    offset = (page - 1) * limit
    rows = list(islice(stream, offset, min(total, offset + limit))) if offset < total else []
    return {"matched_messages": total, "page": page,
            "next_page": page + 1 if offset + len(rows) < total else None, "entries": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, help="private index from collect_history.py")
    parser.add_argument("--term", action="append", default=[], help="match any supplied literal")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--output", type=Path, required=True, help="new private JSON file")
    args = parser.parse_args()
    try:
        result = browse(args.index, [t for t in args.term if t.strip()], args.page, args.limit)
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
