import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "read_context.py"
spec = importlib.util.spec_from_file_location("read_context", SCRIPT)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def response(role, mid, text, **more):
    return {"type": "response_item", "payload": {"type": "message", "role": role, "id": mid,
            "content": [{"type": "output_text" if role == "assistant" else "input_text", "text": text}], **more}}


class ContextWindowTest(unittest.TestCase):
    def setUp(self):
        private = tempfile.TemporaryDirectory()
        self.addCleanup(private.cleanup)
        self.directory = Path(private.name)
        self.source = self.directory / "session.jsonl"
        self.index = self.directory / "index.jsonl"

    def write(self, records, locators):
        self.source.write_text("".join(json.dumps(v) + "\n" for v in records))
        self.index.write_text("".join(json.dumps({"id": mid, "source": str(self.source),
                                                   "line": number, "session_id": "sid"}) + "\n"
                                      for number, mid in locators))

    def test_reopen_surrounding_exchange_and_exclude_other_channels(self):
        self.write([
            {"type": "session_meta", "payload": {"id": "sid", "thread_source": "user"}},
            response("user", "prior", "提问"),
            response("assistant", "progress", "private progress", phase="commentary"),
            response("assistant", "first", "四项", phase="final_answer"),
            response("user", "anchor", "第四个呢"),
            {"type": "response_item", "payload": {"type": "function_call_output", "output": "private"}},
            response("user", "wrapper", "[System Error] contains private text"),
            {"type": "event_msg", "payload": {"type": "agent_message", "message": "镜像"}},
            response("assistant", "f", "清单只有三项", phase="final_answer"),
            response("assistant", "f", "清单只有三项", phase="final_answer"),
            response("user", "next", "好"),
            response("assistant", "later", "private later text"),
        ], [(2, "prior"), (5, "anchor"), (7, "wrapper"), (11, "next")])
        result = reader.read_window(self.index, self.source, "anchor")
        self.assertEqual([(v["role"], v["parts"]) for v in result["messages"]],
                         [("user", ["提问"]), ("assistant", ["四项"]), ("user", ["第四个呢"]),
                          ("assistant", ["清单只有三项"]), ("user", ["好"])])

    def test_closed_source_and_verified_id(self):
        self.write([response("assistant", "anchor", "wrong role")], [(1, "anchor")])
        with self.assertRaisesRegex(ValueError, "does not match|no longer matches"):
            reader.read_window(self.index, self.source, "anchor")
        alt = self.directory / "other.jsonl"
        with self.assertRaisesRegex(ValueError, "explicit source"):
            reader.read_window(self.index, alt, "anchor")
        self.write([response("user", "else", "same text")], [(1, "anchor")])
        with self.assertRaisesRegex(ValueError, "ID"):
            reader.read_window(self.index, self.source, "anchor")
        self.write([response("user", "anchor", "original"), response("user", "anchor", "replay")], [(2, "anchor")])
        with self.assertRaisesRegex(ValueError, "replayed"):
            reader.read_window(self.index, self.source, "anchor")

    def test_system_text_and_subagent_or_wrong_session_cannot_be_anchors(self):
        self.write([response("user", "anchor", "<paseo-system>private")], [(1, "anchor")])
        with self.assertRaisesRegex(ValueError, "indexed user"):
            reader.read_window(self.index, self.source, "anchor")
        for metadata in ({"id": "other"}, {"id": "sid", "thread_source": "agent"}):
            self.write([{"type": "session_meta", "payload": metadata},
                        response("user", "anchor", "user")], [(2, "anchor")])
            with self.assertRaisesRegex(ValueError, "session"):
                reader.read_window(self.index, self.source, "anchor")

    def test_uncertain_neighbors_limit_window_and_mark_omissions(self):
        self.write([response("user", "candidate", "查")]+
                   [response("assistant", str(i), "abcdefg") for i in range(6)]+
                   [response("user", "other", "private"), response("assistant", "later", "private")],
                   [(1, "candidate")])
        result = reader.read_window(self.index, self.source, "candidate", 4)
        self.assertEqual(result["omitted_assistant_answers"], {"after_target": 3})
        self.assertEqual(result["after"], "unverified_user")
        self.assertEqual([m["line"] for m in result["messages"]], [1, 2, 6, 7])
        self.assertEqual(result["messages"][1]["parts"], [{"prefix": "abcd", "omitted_characters": 3}])
        self.assertNotIn("private", json.dumps(result))

    def test_event_only_file_and_private_cli_output(self):
        def event(kind, mid, text):
            return {"type": "event_msg", "payload": {"type": kind, "id": mid, "message": text}}
        self.write([event("user_message", "anchor", "secret"), event("agent_message", "f", "secret2")], [(1, "anchor")])
        path = self.directory / "window.json"
        command = [sys.executable, str(SCRIPT), "--source", str(self.source), "--index", str(self.index),
                   "--id", "anchor", "--output", str(path)]
        run = subprocess.run(command, capture_output=True, check=True)
        self.assertEqual(run.stdout + run.stderr, b"")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(path.read_text())["messages"][-1]["parts"], ["secret2"])
        second = subprocess.run(command, capture_output=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertNotIn(b"secret", second.stderr)


if __name__ == "__main__":
    unittest.main()
