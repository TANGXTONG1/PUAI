"""Use synthetic messages to exercise private recall on the installable CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "browse_history.py"


class BrowseTest(unittest.TestCase):
    def test_diverse_pages_and_memory_search_reopen_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            def add(session, date, message):
                rows.append(dict(id=str(len(rows)), source="private-log", session_id=session,
                                 text=message, date=date))
            for i in range(50):
                add("large", "2026-02-01", "请看下一页" + str(i))
            add("small", "2026-02-04", "PRIVATE " + "说明" * 110 + "一朵西兰花换四小时安静。")
            add("autumn", "2026-11-21", "PRIVATE Give the broccoli a day off.")
            index = root / "private.jsonl"
            index.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))

            def read(name, *args):
                output = root / name
                command = [sys.executable, str(SCRIPT), "--index", str(index), "--output", str(output), *args]
                result = subprocess.run(command, capture_output=True, check=True)
                self.assertEqual(result.stdout, b"")
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                return json.loads(output.read_text())

            first = read("first", "--limit", "3")
            self.assertEqual({r["session_id"] for r in first["entries"]}, {"small","large","autumn"})
            self.assertEqual((first["matched_messages"], first["next_page"]), (52, 2))
            second = read("second", "--page", "2", "--limit", "3")
            self.assertTrue({r["id"] for r in first["entries"]}.isdisjoint(r["id"] for r in second["entries"]))
            self.assertIn("49", [r["id"] for r in second["entries"]])
            hits = read("hits", "--term", "西兰花", "--term", "BROCCOLI")
            self.assertEqual(hits["matched_messages"], 2)
            self.assertIsNone(hits["next_page"])
            for row in hits["entries"]:
                original = rows[int(row["id"])]
                self.assertEqual((row["date"], row["source"]), (original["date"], original["source"]))
                self.assertIn(row["excerpt"], original["text"])
                self.assertEqual(row["clipped"], row["session_id"] == "small")
            self.assertIn("西兰花", hits["entries"][0]["excerpt"])
            self.assertEqual(read("no-hit", "--term", "花椰树")["entries"], [])
            with self.assertRaises(subprocess.CalledProcessError):
                read("hits", "--term", "PRIVATE")
