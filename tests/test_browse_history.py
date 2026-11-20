"""Use synthetic messages to exercise private recall on the installable CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "browse_history.py"


class BrowseTest(unittest.TestCase):
    def test_rank_and_overview_cover_unique_families_and_all_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index"
            records = []
            for month in range(1, 7):
                for session in ["shared", "fork", f"small-{month}"]:
                    for turn in range(6):
                        records.append(dict(id=str(len(records)), session_id=session, date=f"2026-{month:02}-02",
                                            conversation_id="shared" if session == "fork" else session,
                                            source="fixture", text=f"原话 {turn}"))
            index.write_text("".join(json.dumps(row)+"\n" for row in records))
            def fetch(page=1, *args):
                out = Path(tmp)/"out.json"
                subprocess.run([sys.executable, str(SCRIPT), "--index", str(index), "--limit", "7",
                                "--page", str(page), "--output", str(out), *args], check=True)
                data = json.loads(out.read_text())
                out.unlink()
                return data
            data = fetch()
            self.assertEqual((data["matched_threads"], data["matched_months"]), (7,6))
            first = data["entries"]
            self.assertEqual(len({e["conversation_id"] for e in first}),7)
            self.assertGreater(len({e["excerpt"] for e in first}),1)
            ids = [e["id"] for e in first]
            while data["next_page"]:
                data = fetch(data["next_page"])
                ids.extend(e["id"] for e in data["entries"])
            self.assertCountEqual(ids,[r["id"] for r in records])
            overview = fetch(1, "--overview")
            self.assertIsNone(overview["next_page"])
            cards = overview["entries"]
            self.assertEqual(sum(c["matched_messages"] for c in cards),len(records))
            shared = next(c for c in cards if c["conversation_id"] == "shared")
            self.assertEqual((shared["first"],shared["last"],shared["matched_messages"]),
                             ("2026-01-02","2026-06-02",72))
            for c in cards:
                self.assertEqual(len(c["samples"]),3)
                for sample in c["samples"]:
                    src=records[int(sample["id"])]
                    self.assertEqual((src["session_id"],src["text"]), (sample["session_id"],sample["excerpt"]))
            excluded = fetch(1, "--overview", "--exclude-session", "fork", "--term", "原话")
            self.assertEqual(excluded["matched_threads"],6)
            self.assertNotIn("shared",[c["conversation_id"] for c in excluded["entries"]])

    def test_full_pages_reconstruct_long_tail_without_losing_role_or_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, per_page = Path(tmp), 37
            rows = [
                dict(id="head", session_id="one", date="2026-07-01", text="交办" * 103+"\n我想算的是核。"),
                dict(id="tail", session_id="fork", conversation_id="one", date="2026-09-04",
                     text="🙂可以\n但先看看果核", evidence_level="input_history", owner_group="one-owner",
                     input_method="question_form", parts=["🙂可以", "但先看看果核"]),
                dict(id="other", session_id="two", date="2026-09-15", text="不在选定会话内"),
                dict(id="othermonth", session_id="one", date="2026-10-01", text="这个月也有一次。"),
                dict(id="pic", session_id="one", date="2026-07-05", text=""),
            ]
            for r in rows:
                r["source"]="fixture"
            index=root/"index"
            index.write_text("".join(json.dumps(r)+"\n" for r in rows))
            wanted={r["id"]:r["text"] for r in rows[:2]}
            read={}; page=1
            while page:
                out=root/f"page-{page}"
                cmd=[sys.executable,str(SCRIPT),"--index",str(index),"--output",str(out),"--full-text",
                     "--limit","2","--month","2026-07","--month","2026-09","--session","fork",
                     "--page-chars",str(per_page),"--page",str(page)]
                run=subprocess.run(cmd, capture_output=True, check=True)
                self.assertFalse(run.stdout+run.stderr)
                self.assertEqual(out.stat().st_mode & 0o777,0o600)
                result=json.loads(out.read_text())
                self.assertEqual(result["matched_characters"],sum(map(len,wanted.values())))
                self.assertLessEqual(sum(len(e["text"]) for e in result["entries"]),per_page)
                self.assertLessEqual(len(result["entries"]),2)
                self.assertEqual((result["matched_threads"],result["matched_messages"]),(1,2))
                for e in result["entries"]:
                    mid=e["id"]; prev=read.get(mid,"")
                    self.assertEqual(e["char_start"],len(prev))
                    read[mid]=prev+e["text"]
                    self.assertEqual(e["char_end"],len(read[mid]))
                    self.assertEqual(e["message_chars"],len(wanted[mid]))
                    if mid=="tail":
                        self.assertTrue(e["disjoint_parts"])
                        self.assertEqual(e["evidence_level"],"input_history")
                        self.assertEqual((e["owner_group"], e["input_method"]), ("one-owner", "question_form"))
                if result["next_page"] is None:
                    self.assertEqual(result["pages"],page)
                page=result["next_page"]
            self.assertEqual(read,wanted)

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
