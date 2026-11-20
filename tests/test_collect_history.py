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

    def test_fork_replay_cannot_move_an_original_turn_to_another_year(self):
        self.write("sessions/2026/05/10/rollout-child.jsonl", [meta("fork", forked_from_id="original"),
                   codex_turn("user","PRIVATE OLD","old","2026-05-10T00:00:00Z"),codex_turn("user","PRIVATE NEW","new","2026-05-10T00:00:00Z")])
        self.write("archived_sessions/rollout-parent.jsonl", [meta("original"),
                   codex_turn("user","PRIVATE OLD","old","2025-05-10T00:00:00Z")])
        summary, rows = self.collect("codex", "--root", self.root)
        self.assertEqual([r["id"] for r in rows],["new"])
        self.assertEqual(summary["user_turns_before_editorial_filter"],1)

    def test_chatgpt_active_branch_zipped_shards_and_sources(self):
        def node(role,text,parent,children,mid,**more):
            return {"parent":parent, "children":children,
                    "message":{"id":mid,"author":{"role":role},"create_time":1767227400,
                               "content":{"content_type":"text","parts":[text]},**more}}
        scope={"conversation_id":"one","current_node":"q2","mapping":{
            "r":{"parent":None,"children":["q"],"message":None},
            "q":node("user","PRIVATE January","r",["old","new"],"uid"),
            "old":node("user","PRIVATE alternate","q",[],"dropped"),
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
        self.assertEqual([r["id"] for r in rows],["uid","last","other"])
        self.assertEqual(summary["threads"],2)
        self.assertEqual(self.window(rows[0]),[("user",["PRIVATE January"]),("assistant",["PRIVATE published reply"]),("user",["PRIVATE next"])])

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
