"""Exercise public CLI entry points with synthetic, private multi-thread history."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
WHEN = "2025-12-31T17:30:00Z"  # 2026 in Shanghai


def codex_turn(role, text, mid=None, timestamp=WHEN, **extra):
    return {"timestamp": timestamp, "type": "response_item",
            "payload": {"type": "message", "role": role, "id": mid, **extra,
                        "content": [{"type": "text", "text": text}]}}


def meta(sid, **extra):
    return {"type": "session_meta", "payload": {"id": sid, **extra}}


class CollectionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index = self.root/"index.jsonl"

    def write(self, name, records):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(x)+"\n" for x in records))
        return path

    def collect(self, client, *args):
        run = subprocess.run([sys.executable, str(SCRIPTS/"collect_history.py"), "--client", client,
                              "--output", str(self.index), "--timezone", "Asia/Shanghai", "--year", "2026",
                              *map(str, args)], check=True, capture_output=True)
        self.assertNotIn(b"PRIVATE", run.stdout+run.stderr)
        self.assertEqual(self.index.stat().st_mode & 0o777, 0o600)
        return json.loads(run.stdout), [json.loads(x) for x in self.index.read_text().splitlines()]

    def window(self, row):
        path = self.root/(row["id"]+"-window")
        subprocess.run([sys.executable, str(SCRIPTS/"read_context.py"), "--index", str(self.index),
                        "--source", row["source"], "--id", row["id"], "--output", str(path)],
                       check=True, capture_output=True)
        return [(r["role"], r["parts"]) for r in json.loads(path.read_text())["messages"]]

    def test_codex_broad_search_privacy_legacy_and_repeats(self):
        self.write("sessions/2025/12/31/rollout-1.jsonl", [
            meta("a"), codex_turn("user","PRIVATE A"), codex_turn("assistant","PRIVATE reply"),
            codex_turn("user","PRIVATE A","repeat"),  # intentionally sent twice
            {"type":"event_msg","timestamp":WHEN,"payload":{"type":"user_message","message":"PRIVATE A"}},
            codex_turn("user","<environment_context>private", "sys"),
            codex_turn("user","PRIVATE replay", "r", is_replay=True)])
        self.write("archived_sessions/rollout-2.jsonl", [meta("b"),codex_turn("user","PRIVATE B","b","2026-09-23T00:00:00Z")])
        self.write("archived_sessions/rollout-sub.jsonl", [meta("sub",thread_source="subagent"),codex_turn("user","PRIVATE child","sub")])
        self.write("archived_sessions/rollout-fork.jsonl",[meta("fork",forked_from_id="a"),
                   codex_turn("user","PRIVATE A","repeat"),codex_turn("user","PRIVATE inherited")])
        self.write("random/rollout-3.jsonl", [meta("other"),codex_turn("user","PRIVATE out of scope","x")])
        summary, rows = self.collect("codex", "--root", self.root)
        self.assertEqual((summary["days"],summary["threads"],summary["months"]), (2,2,{"2026-01":2,"2026-09":1}))
        self.assertCountEqual([r["text"] for r in rows],["PRIVATE A","PRIVATE A","PRIVATE B"])
        legacy = next(row for row in rows if row["id"].startswith("local-"))
        self.assertEqual(self.window(legacy),[("user",["PRIVATE A"]),("assistant",["PRIVATE reply"]),("user",["PRIVATE A"])])
        with self.assertRaises(subprocess.CalledProcessError):
            self.collect("codex", "--root", self.root)

    def test_calendar_uses_full_inventory_then_removes_report_messages(self):
        self.write("archived_sessions/rollout-one.jsonl", [
            meta("one"), codex_turn("user", "PRIVATE question", "a"),
            codex_turn("user", "PRIVATE followup", "b"),
            codex_turn("user", "PRIVATE report command", "control"),
            codex_turn("user", "PRIVATE another day", "c", "2026-01-02T14:00:00Z"),
        ])
        self.write("archived_sessions/rollout-incomplete.jsonl", [
            meta("incomplete"), codex_turn("user", "PRIVATE observed", "obs", "2026-01-08T00:00:00Z"),
            codex_turn("user", "PRIVATE undated", "unknown", None),
        ])
        summary, rows = self.collect("codex", "--root", self.root)
        self.assertEqual(summary["daily_before_editorial_filter"], {"2026-01-01": 3, "2026-01-02": 1, "2026-01-08": 1})
        self.assertEqual(summary["skipped"]["undated_turns"], 1)
        inventory = self.root / "inventory.json"
        inventory.write_text(json.dumps(summary))
        exclusions = self.root / "exclude.json"
        exclusions.write_text(json.dumps(["control"]))
        command = [sys.executable, str(SCRIPTS / "collect_history.py"), "--calendar-from", str(self.index),
                   "--inventory", str(inventory), "--exclude-ids", str(exclusions)]
        result = subprocess.run(command, check=True, capture_output=True)
        self.assertNotIn(b"PRIVATE", result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["days"], "01-01:2:?,01-02:1:?")
        self.assertEqual(json.loads(result.stdout)["dates"], "01-08")
        exclusions.write_text('["not-in-this-index"]')
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        exclusions.write_text("[]")
        self.index.write_text(json.dumps(rows[0]) + "\n")
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_chatgpt_window_keeps_the_local_date_and_original_numeric_timestamp(self):
        epoch = 1767202200  # 2025-12-31 UTC, 2026-01-01 in Shanghai
        def node(mid, parent, ts):
            return {"parent": parent, "children": [], "message": {"id": mid, "author": {"role": "user"},
                    "create_time": ts, "content": {"content_type": "text", "parts": ["PRIVATE dialog"]}}}
        export = self.root / "conversations.json"
        export.write_text(json.dumps([{"id": "thread", "current_node": "b", "update_time": epoch + 86400,
              "mapping": {"a": node("a", None, None), "b": node("b", "a", epoch)}}]))
        summary, rows = self.collect("chatgpt", "--export", export)
        self.assertEqual(summary["skipped"]["undated_turns"], 1)
        self.assertEqual([r["id"] for r in rows], ["b"])
        self.window(rows[0])
        window = json.loads((self.root / "b-window").read_text())
        self.assertEqual(window["target_date"], "2026-01-01")
        self.assertEqual(window["messages"][-1]["record_timestamp"], epoch)
        self.assertNotIn("record_timestamp", window["messages"][0])

    def test_host_calendar_splits_complete_sessions_from_search_hits(self):
        epoch = 1767202200
        def user(mid, **when):
            return {"id": mid, "role": "user", **when}
        ledger = [{"id": "history-page-1", "complete": True, "messages": [
            user("a", timestamp=epoch), user("b", timestamp=(epoch + 1000) * 1000),
            user("c", date="2026-01-02"), {"id": "reply", "role": "assistant", "date": "2026-01-02"}]},
            {"id": "history-page-2", "complete": True, "messages": [
                user("d", timestamp="2026-01-03T01:30:00+09:00"), user("a", timestamp=epoch),
                user("old", date="2025-01-01")]},
            {"id": "search-only", "complete": False, "messages": [
                user("e", date="2026-01-04"), user("f", date="2026-01-04"),
                user("x", date="2026-01-05"), user("d", date="2026-01-03")]},
            {"id": "time-missing", "complete": True, "messages": [
                user("unknown"), user("late", date="2026-01-07")]}]
        path = self.root / "native.json"
        path.write_text(json.dumps(ledger))
        command = [sys.executable, str(SCRIPTS/"collect_history.py"), "--host-ledger", str(path),
                   "--year", "2026", "--timezone", "Asia/Shanghai"]
        def aggregate():
            return json.loads(subprocess.run(command, check=True, capture_output=True).stdout)
        result = aggregate()
        self.assertEqual(result["days"], "01-01:2:?,01-02:1:?,01-03:1:?")
        self.assertEqual(result["dates"], "01-04,01-05,01-07")
        self.assertEqual(result["missing_message_dates"], 1)
        path.write_text(json.dumps([ledger[2]]))
        self.assertEqual(aggregate()["days"], "")
        self.assertEqual(aggregate()["dates"], "01-03,01-04,01-05")
        ledger[2]["messages"].append(user("d", date="2026-03-03"))
        path.write_text(json.dumps(ledger))
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_chatgpt_frequency_includes_media_only_days_across_threads(self):
        epoch = 1767202200  # Shanghai Jan 1, before midnight in UTC
        def node(mid, parent, timestamp, parts, role="user", **metadata):
            return {"parent": parent, "message": {"id": mid, "author": {"role": role},
                    "metadata": metadata, "create_time": timestamp,
                    "content": {"content_type": "multimodal_text", "parts": parts}}}

        photo = {"content_type": "image_asset_pointer", "asset_pointer": "PRIVATE-photo"}
        first = {"id": "one", "current_node": "reply", "mapping": {
            "q": node("q", None, epoch, ["PRIVATE text"]),
            "p": node("p", "q", epoch + 86400, ["", photo]),
            "reply": node("reply", "p", epoch + 86401, ["PRIVATE reply"], role="assistant")}}
        second = {"id": "two", "current_node": "empty", "mapping": {
            "b": node("b", None, epoch, ["PRIVATE more"]),
            "f": node("f", "b", epoch + 172800, [""], attachments=[{"id": "PRIVATE-file"}]),
            "hidden": node("hidden", "f", epoch + 259200, [photo], is_hidden=True),
            "empty": node("empty", "hidden", epoch + 259200, [""])}}
        export = self.root / "history.zip"
        with ZipFile(export, "w") as archive:
            archive.writestr("conversations-1.json", json.dumps([first]))
            archive.writestr("conversations-2.json", json.dumps([first, second]))
        inventory, rows = self.collect("chatgpt", "--export", export)
        expected = {"2026-01-01": 2, "2026-01-02": 1, "2026-01-03": 1}
        self.assertEqual(inventory["daily_before_editorial_filter"], expected)
        self.assertEqual((inventory["threads"], inventory["days"]), (2, 3))
        self.assertEqual([r["id"] for r in rows if not r["text"]], ["p", "f"])
        self.assertNotIn("PRIVATE-photo", self.index.read_text())
        self.assertEqual(self.window(rows[0]), [("user", ["PRIVATE text"]), ("user", [])])
        inv, exclusions = self.root / "inventory.json", self.root / "exclude.json"
        inv.write_text(json.dumps(inventory))
        exclusions.write_text("[]")
        run = subprocess.run([sys.executable, str(SCRIPTS/"collect_history.py"), "--calendar-from",
                              str(self.index), "--inventory", str(inv), "--exclude-ids", str(exclusions)],
                             check=True, capture_output=True)
        self.assertEqual(json.loads(run.stdout)["days"], "01-01:2:?,01-02:1:?,01-03:1:?")

    def test_multigeneration_fork_replayed_with_fresh_ids_and_times(self):
        def context(turn):
            return {"type": "turn_context", "payload": {"turn_id": turn}}
        def start(turn, epoch):
            return {"type": "event_msg", "payload": {"type": "task_started", "turn_id": turn, "started_at": epoch}}
        root = [meta("root"), context("original"),
                codex_turn("user","PRIVATE same", "a1"), codex_turn("user","PRIVATE same", "a2")]
        self.write("archived_sessions/rollout-original.jsonl", root)
        self.write("archived_sessions/rollout-fork.jsonl", [
            meta("first", forked_from_id="root", timestamp="2026-01-05T00:00:00Z"), context("original"),
            codex_turn("user","PRIVATE same","reissued1", "2026-01-05T00:00:00Z"),
            codex_turn("user","PRIVATE same","reissued2", "2026-01-05T00:00:00Z"),
            start("new", 1768179600), context("new"), codex_turn("user","PRIVATE same", None, "2026-01-12T00:00:00Z")])
        self.write("archived_sessions/rollout-earlier-name.jsonl", [
            meta("grandchild", forked_from_id="first", timestamp="2026-02-01T00:00:00Z"), context("original"),
            codex_turn("user","PRIVATE same", "reissued3","2026-02-01T00:00:00Z"),
            codex_turn("user","PRIVATE same", "reissued4","2026-02-01T00:00:00Z"), context("new"),
            codex_turn("user","PRIVATE same", "reissued5","2026-02-01T00:00:00Z"),
            context("followup"),codex_turn("user","PRIVATE same","genuinely-new","2026-02-02T00:00:00Z")])
        self.write("archived_sessions/rollout-other.jsonl", [
            meta("unrelated"), context("original"), codex_turn("user","PRIVATE same","other")])
        summary, rows = self.collect("codex", "--root", self.root)
        self.assertEqual(summary["user_turns_before_editorial_filter"], 5)
        self.assertEqual(summary["conversation_families"], 2)
        self.assertEqual(summary["skipped"]["inherited_fork_copies"], 5)
        self.assertCountEqual([row["date"] for row in rows], ["2026-01-01"]*3 + ["2026-01-12","2026-02-02"])
        self.assertTrue(all(row["conversation_id"] == "root" for row in rows if row["session_id"] in {"first","grandchild"}))
        newest = next(row for row in rows if row["id"] == "genuinely-new")
        self.assertEqual(self.window(newest)[-1], ("user", ["PRIVATE same"]))

    def test_fork_replay_cannot_move_an_original_turn_to_another_year(self):
        self.write("sessions/2026/05/10/rollout-child.jsonl", [meta("fork", forked_from_id="original"),
                   codex_turn("user","PRIVATE OLD","old","2026-05-10T00:00:00Z"),codex_turn("user","PRIVATE NEW","new","2026-05-10T00:00:00Z")])
        self.write("archived_sessions/rollout-parent.jsonl", [meta("original"),
                   codex_turn("user","PRIVATE OLD","old","2025-05-10T00:00:00Z")])
        summary, rows = self.collect("codex", "--root", self.root)
        self.assertEqual([r["id"] for r in rows],["new"])
        self.assertEqual(summary["user_turns_before_editorial_filter"],1)

    def test_chatgpt_keeps_unique_owner_inputs_across_branches_and_zipped_shards(self):
        def node(role,text,parent,children,mid,**more):
            return {"parent":parent, "children":children,
                    "message":{"id":mid,"author":{"role":role},"create_time":1767227400,
                               "content":{"content_type":"text","parts":[text]},**more}}
        scope={"conversation_id":"one","current_node":"q2","mapping":{
            "r":{"parent":None,"children":["q"],"message":None},
            "q":node("user","PRIVATE January","r",["old","new"],"uid"),
            "old":node("user","PRIVATE alternate","q",["old-a"],"sibling"),
            "old-a":node("assistant","PRIVATE on original branch","old",[],"sibling-answer"),
            "new":node("assistant","PRIVATE published reply","q",["q2"],"aid"),
            "q2":node("user","PRIVATE next","new",[],"last")}}
        additional={"conversation_id":"two","current_node":"q","mapping":{
            "q":node("user","PRIVATE second thread",None,[],"other")}}
        zipped=self.root/"export.zip"
        with ZipFile(zipped, "w") as archive:
            archive.writestr("export/conversations-000.json",json.dumps([scope]))
            archive.writestr("export/conversations-001.json",json.dumps([scope,additional]))
            archive.writestr("shared_conversations.json",json.dumps(["unrelated"]))
        summary, rows=self.collect("chatgpt","--export",zipped)
        self.assertCountEqual([r["id"] for r in rows],["uid","sibling","last","other"])
        self.assertEqual(summary["threads"],2)
        by = {r["id"]:r for r in rows}
        self.assertEqual(self.window(by["uid"]),[("user",["PRIVATE January"]),("assistant",["PRIVATE published reply"]),("user",["PRIVATE next"])])
        self.assertEqual(self.window(by["sibling"]),[("user",["PRIVATE January"]),("user",["PRIVATE alternate"]),
                                                     ("assistant",["PRIVATE on original branch"])])

    def test_missing_active_selection_and_broken_graph_preserve_authored_dates_without_crossing_branches(self):
        def node(mid, parent, day):
            return {"parent":parent, "message":{"id":mid, "author":{"role":"user"},
                    "create_time":f"2026-03-{day:02d}T09:00:00Z", "content":{"content_type":"text","parts":[mid]}}}
        good = {"r":node("first",None,1), "l":node("left","r",2),"a":node("right","r",3)}
        bad = {"x":node("orphan","missing",4), "y":node("cycle","y",5)}
        f=self.root/"conversations.json"; f.write_text(json.dumps([{"id":"complete","mapping":good},
                                                                 {"id":"gaps","mapping":bad}]))
        inventory, rows=self.collect("chatgpt","--export",f)
        by={r["id"]:r for r in rows}
        self.assertEqual(set(by),{"first","left","right","orphan","cycle"})
        self.assertEqual(self.window(by["first"]),[("user",["first"])])
        self.assertEqual(self.window(by["left"]),[("user",["first"]),("user",["left"])])
        self.assertEqual(self.window(by["cycle"]),[("user",["cycle"])])
        self.assertEqual(self.window(by["orphan"]),[("user",["orphan"])])
        inv,ex=self.root/"inventory",self.root/"exclude"; inv.write_text(json.dumps(inventory));ex.write_text("[]")
        ledger=json.loads(subprocess.check_output([sys.executable,str(SCRIPTS/"collect_history.py"),"--calendar-from",str(self.index),
                                                  "--inventory",str(inv),"--exclude-ids",str(ex)]))
        self.assertEqual((ledger["dated_user_messages"],ledger["dates"]),(3,"03-04,03-05"))

    def test_separate_chatgpt_export_folders_in_one_archive_cannot_become_one_person(self):
        combined=self.root/"combined.zip"
        with ZipFile(combined,"w") as archive:
            for account in ("a","b"):
                message={"id":account, "author":{"role":"user"}, "create_time":1767227400,
                         "content":{"content_type":"text","parts":["普通周末提问"]}}
                source=[{"id":account,"current_node":"m","mapping":{"m":{"parent":None,"message":message}}}]
                archive.writestr(f"{account}/conversations.json",json.dumps(source))
        proc = subprocess.run([sys.executable,str(SCRIPTS/"collect_history.py"),"--client","chatgpt",
                               "--year","2026","--export",str(combined),"--output",str(self.index)],
                              capture_output=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertIn("分别",proc.stderr.decode())
        self.assertFalse(self.index.exists())

    def test_claude_input_history_recovers_original_inputs_without_inventing_assistant_or_frequencies(self):
        def history(sid, when, text):
            return {"sessionId": sid, "timestamp": when, "display": text, "pastedContents": {"1": {"content": "PRIVATE pasted material"}}}
        when = 1772409600000  # 2026-03-02 UTC
        item = {"type": "user", "sessionId": "A", "uuid": "native", "timestamp": when,
                "message": {"role": "user", "content": "先把果核称了。"}}
        self.write("projects/work/A.jsonl", [item])
        first = history("B", when + 86400000, "还给果核发工资？")
        self.write("history.jsonl", [history("A", when, "先把果核称了。"), first, first,
                   history("B", when+86400001, "[Image #1] 这两个怎么都在打卡？"),
                   history("B", when+86400002, "[Pasted text #1 +12 lines]"),
                   history("B", when+86400003, "/clear"), history("B", when+86400004, "!pwd")])
        summary, rows = self.collect("claude", "--root", self.root)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["id"], "native")
        self.assertEqual(summary["input_history_messages"], 3)
        self.assertEqual([r.get("evidence_level") for r in rows], [None, "input_history", "input_history", "input_history"])
        self.assertEqual(rows[3]["text"], "")
        self.assertEqual(rows[3]["input_method"], "attachment_or_paste")
        self.assertEqual(self.window(rows[3]), [("user", [])])
        self.assertEqual(rows[2]["text"], "这两个怎么都在打卡？")
        self.assertNotIn("PRIVATE", self.index.read_text())
        self.window(rows[1])
        w = json.loads((self.root/(rows[1]["id"]+"-window")).read_text())
        self.assertEqual([q["parts"] for q in w["messages"]], [["还给果核发工资？"]])
        self.assertEqual(w["evidence_level"], "input_history")
        self.assertFalse(w["assistant_context_available"])
        inv, ex = self.root/"inventory", self.root/"excluded"
        inv.write_text(json.dumps(summary)); ex.write_text("[]")
        result = subprocess.run([sys.executable,str(SCRIPTS/"collect_history.py"),"--calendar-from",str(self.index),
            "--inventory",str(inv),"--exclude-ids",str(ex)], capture_output=True, check=True)
        calendar = json.loads(result.stdout)
        self.assertEqual((calendar["dated_user_messages"], calendar["days"], calendar["dates"]), (1, "03-02:1:?", "03-03"))

    def test_claude_original_media_only_and_input_journal_copy_are_one_turn(self):
        when = 1772409600000
        self.write("projects/work/photo.jsonl", [{"type":"user","sessionId":"photo","uuid":"upload","timestamp":when,
            "message":{"role":"user","content":[{"type":"image","source":{"type":"base64","data":"PRIVATE"}}]}}])
        self.write("history.jsonl", [{"sessionId":"photo","timestamp":when,"display":"[Image #1]"}])
        summary, rows = self.collect("claude","--root",self.root)
        self.assertEqual([(r["id"], r["text"]) for r in rows], [("upload","")])
        self.assertNotIn("PRIVATE", self.index.read_text())
        self.assertEqual(summary["input_history_messages"], 0)
        self.assertEqual(self.window(rows[0]), [("user", [])])

    def test_owner_partitions_do_not_merge_other_accounts_or_guess_legacy_ownership(self):
        for sid, owner in [("same-a", "private-user-a"), ("same-b", "private-user-a"),
                           ("other", "private-user-b"), ("old", None)]:
            where = {"creator_user_id": owner} if owner else {}
            self.write(f"sessions/2026/01/01/rollout-{sid}.jsonl",
                       [meta(sid, **where), codex_turn("user", "同一句话", sid, timestamp=WHEN)])
        summary, rows = self.collect("codex", "--root", self.root)
        by = {r["session_id"]: r["owner_group"] for r in rows}
        self.assertEqual(by["same-a"], by["same-b"])
        self.assertNotEqual(by["other"], by["same-a"])
        self.assertEqual(by["old"], "unknown")
        self.assertEqual(summary["owner_groups"][by["same-a"]], {"messages": 2, "threads": 2})
        self.assertNotIn("private-user", json.dumps(summary) + self.index.read_text())
        inv = self.root / "inventory"; inv.write_text(json.dumps(summary))
        def subset(flag, value, name):
            path = self.root/name
            cmd = [sys.executable, str(SCRIPTS/"collect_history.py"), "--scope-index", str(self.index),
                   "--inventory", str(inv), flag, value, "--output", str(path)]
            return subprocess.run(cmd, capture_output=True), path
        a, scoped = subset("--owner-session", "same-b", "just-a")
        self.assertEqual(a.returncode, 0, a.stderr)
        filtered = json.loads(a.stdout)
        self.assertEqual((filtered["threads"], filtered["days"]), (2, 1))
        self.assertEqual({r["owner_group"] for r in map(json.loads, scoped.read_text().splitlines())}, {by["same-a"]})
        inv2 = self.root/"scoped-inventory"; inv2.write_text(a.stdout.decode())
        exclusions = self.root/"excluded"; exclusions.write_text("[]")
        calendar = subprocess.run([sys.executable,str(SCRIPTS/"collect_history.py"), "--calendar-from",str(scoped),
              "--inventory",str(inv2),"--exclude-ids",str(exclusions)], capture_output=True, check=True)
        self.assertEqual(json.loads(calendar.stdout)["dated_user_messages"], 2)
        b, old = subset("--owner-group", "unknown", "just-old")
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual(json.loads(old.read_text())["session_id"], "old")
        bad, omitted = subset("--owner-session", "old", "no-guess")
        self.assertNotEqual(bad.returncode, 0)
        self.assertFalse(omitted.exists())

        self.index.write_text(self.index.read_text()+'\n')
        bad, omitted = subset("--owner-group", by["same-a"], "altered")
        self.assertNotEqual(bad.returncode, 0)
        self.assertFalse(omitted.exists())

    def test_matching_one_native_claude_turn_keeps_additional_same_word_submissions_and_dates(self):
        now = 1772409600000
        word = "还在算？"
        self.write("projects/work/A.jsonl", [{"type": "user", "sessionId": "A", "uuid": "native",
                        "timestamp": "2026-03-02T00:00:00+00:00", "message": {"role":"user","content":word}}])
        stamps = [now+350, now+9000, now+300000, now+35*86400000]
        self.write("history.jsonl", [{"sessionId": "A", "timestamp": t, "display": word} for t in stamps])
        summary, rows = self.collect("claude", "--root", self.root)
        extra = [r for r in rows if r.get("evidence_level") == "input_history"]
        self.assertEqual([r["timestamp"] for r in extra], stamps[1:])
        self.assertEqual(set(r["date"] for r in extra), {"2026-03-02", "2026-04-06"})
        self.assertEqual(summary["input_history_messages"], 3)

    def test_claude_collect_only_human_main_transcript(self):
        def item(role,mid,content,**flags):
            return {"type":role,"message":{"role":role,"content":content},"sessionId":"one","uuid":mid,"timestamp":WHEN,**flags}
        records=[item("user","uid", "PRIVATE one"),item("assistant","a",[{"type":"thinking","thinking":"private thought"},
                 {"type":"text","text":"PRIVATE answer"}]),item("user","t",[{"type":"tool_result","content":"private output"}]),
                 item("user","u2", "PRIVATE two"),item("user","m","PRIVATE metadata",isMeta=True),
                 item("user","injected","<local-command-stdout>private")]
        self.write("projects/my-project/one.jsonl", records)
        self.write("projects/my-project/one/subagents/agent.jsonl",[item("user","sub","PRIVATE sub")])
        summary, rows=self.collect("claude","--root",self.root)
        self.assertEqual((summary["threads"],[r["id"] for r in rows]),(1,["uid","u2"]))
        self.assertEqual(self.window(rows[0]),[("user",["PRIVATE one"]),("assistant",["PRIVATE answer"]),("user",["PRIVATE two"])])


    def test_claude_rewind_does_not_attribute_a_sibling_reply_to_user(self):
        def record(role, mid, parent, content):
            return {"type":role,"uuid":mid,"parentUuid":parent,"sessionId":"one","timestamp":WHEN,
                    "message":{"role":role,"content":content}}
        self.write("projects/proj/one.jsonl", [record("user","q",None,"start"),
                   record("assistant","right","q","right response"),
                   record("assistant","sibling","q","wrong response"),
                   record("user","tool","right",[{"type":"tool_result","content":"hidden"}]),
                   record("user","anchor","tool","follow-up")])
        _, rows = self.collect("claude","--root", self.root)
        self.assertEqual(self.window(rows[-1]),[("user",["start"]),("assistant",["right response"]),("user",["follow-up"])])


if __name__ == "__main__":
    unittest.main()
