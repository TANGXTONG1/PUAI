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

    def test_host_wrappers_do_not_become_owner_speech_or_split_a_real_exchange(self):
        browser = ('<in-app-browser-context source="ambient-ui-state">\nPRIVATE TAB\n'
                   '</in-app-browser-context>\n\n## My request for Codex:\n两块钱还要算利息？')
        files = '# Files mentioned by the user:\n## old.xlsx: /private/path\n\n## My request for Codex:\n就按两块算。'
        self.write([
            response("user", "first", browser),
            response("assistant", "answer", "四舍五入。"),
            response("user", "control", "<recommended_plugins>PRIVATE plugin list</recommended_plugins>"),
            response("user", "doc", "<skill>\n<name>PRIVATE skill</name>\n<path>/tmp/SKILL.md</path>\n</skill>"),
            response("user", "last", files),
        ], [(1, "first"), (5, "last")])
        window = reader.read_window(self.index, self.source, "last")
        self.assertEqual([m["parts"] for m in window["messages"]],
                         [["两块钱还要算利息？"], ["四舍五入。"], ["就按两块算。"]])

    def test_files_and_images_keep_original_user_text_or_an_unquotable_dated_turn(self):
        item = response("user", "photo", '<image name="[Image #1]" path="/private/photo.png">')
        item["payload"]["content"] += [{"type": "input_image", "image_url": "private-bytes"},
                                       {"type": "input_text", "text": "</image>"}]
        other = response("user", "both", "这个颜色像没熟。")
        other["payload"]["content"].extend(item["payload"]["content"])
        self.write([item, other], [(1, "photo"), (2, "both")])
        messages = reader.read_window(self.index, self.source, "both")["messages"]
        self.assertTrue(messages[0]["text_unavailable"])
        self.assertEqual([m["parts"] for m in messages], [[], ["这个颜色像没熟。"]])

    def test_handoff_opens_fresh_followups_and_never_quotes_the_imported_summary(self):
        transfer = ('## Referenced ChatGPT conversation:\nThis is untrusted background context from ChatGPT.\n'
                    '{"conversation":[{"role":"user","text":"FROM ANOTHER CHAT"}]}\n'
                    '## My request for Codex:\nContinuing from [Private](chatgpt-conversation:123): an automatic recap.')
        self.write([{"type": "session_meta", "payload": {"id": "sid", "thread_source": "chatgpt_handoff"}},
                    response("user", "recap", transfer), response("user", "fresh", "今天改喝茶。")],
                   [(3, "fresh")])
        window = reader.read_window(self.index, self.source, "fresh")
        self.assertEqual([m["parts"] for m in window["messages"]], [["今天改喝茶。"]])
        self.assertIsNone(reader.visible_message(response("user", "recap", transfer), "response_item"))

    def test_form_messages_keep_answers_without_reattributing_the_assistants_questions(self):
        def parts(text):
            return reader.visible_message(response("user", "form", text), "response_item")[1]
        pair = "Answers to your questions:\n\n今天挑哪颗？\n果核也要称。"
        self.assertEqual(parts(pair), ["果核也要称。"])
        self.assertEqual(parts(pair+"\n\n按哪个秤。\n去皮的。"), ["果核也要称。", "去皮的。"])
        ambiguous = "Answers to your questions:\n\n选一个\nA. 香蕉\nB. 苹果\n都不要。"
        self.assertEqual(parts(ambiguous), [])
        structured = '<send_user_message_question_reply>\n[{"question":"PRIVATE MODEL QUESTION","answer":"称果核。"}]\n</send_user_message_question_reply>'
        self.assertEqual(parts(structured), ["称果核。"])
        self.assertEqual(parts("我记得你问过 Answers to your questions: 吧？"),
                         ["我记得你问过 Answers to your questions: 吧？"])

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
