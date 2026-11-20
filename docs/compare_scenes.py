#!/usr/bin/env python3
"""Reopen shortlisted owner turns side by side in a private, source-verified file."""
import argparse
import json
import os
from pathlib import Path

from read_context import read_window


class MixedOwners(ValueError):
    pass


def compare(indexes, ids, budget):
    if len(set(ids)) != len(ids):
        raise ValueError("each selected ID should only appear once")
    wanted = set(ids)
    found = {}
    for index in indexes:
        with index.open(encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                key = row["id"]
                if key in wanted:
                    if key in found:
                        raise ValueError("ambiguous message ID: use one original index for this selection")
                    found[key] = index, row
    if wanted != found.keys():
        raise ValueError("some selected IDs do not belong to the supplied indexes")
    codex_groups = {row.get("owner_group", "unknown") for _, row in found.values() if row.get("client") == "codex"}
    if len(codex_groups) > 1:
        raise MixedOwners("这些消息来自不同的账号分区。请用同一个已核实的本人分区重新选句。")

    scenes = []
    conversations = set()
    for key in ids:
        index, row = found[key]
        window = read_window(index, Path(row["source"]), key, budget)
        family = row.get("conversation_id") or row["session_id"]
        conversations.add((row.get("client"), family))
        # A pasted document can be followed by the owner's actual request at the very end.
        scene = {"id": key, "conversation_id": family, "session_id": row["session_id"],
                 "date": window["target_date"], "user_text": row["text"], "messages": window["messages"]}
        for field in ("owner_group", "evidence_level", "input_method"):
            if field in window or field in row:
                scene[field] = window.get(field, row.get(field))
        if len(row.get("parts", [])) > 1:
            scene["parts"] = row["parts"]
        if "assistant_context_available" in window:
            scene["assistant_context_available"] = window["assistant_context_available"]
        scenes.append(scene)
    return {"conversations": len(conversations),
            "owner_groups": sorted({scene.get("owner_group", "unknown") for scene in scenes}),
            "scenes": scenes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, action="append", help="private user-turn index; repeat for another source")
    parser.add_argument("--ids", required=True, nargs="+", help="user message IDs in the desired comparison order")
    parser.add_argument("--max-chars", type=int, default=1200, help="characters per surrounding turn; user_text keeps the full verified anchor")
    parser.add_argument("--output", type=Path, required=True, help="new private JSON file")
    args = parser.parse_args()
    try:
        data = compare(args.index, args.ids, args.max_chars)
        with open(args.output, "x", encoding="utf-8", opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
            try:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            except OSError:
                args.output.unlink(missing_ok=True)
                raise
    except MixedOwners as exc:
        parser.exit(1, f"{exc}\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Cannot compare the original turns ({type(exc).__name__}). Check the index, IDs and source files.\n")


if __name__ == "__main__":
    main()
