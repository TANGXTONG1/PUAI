"""A shortlist must reopen the original speaker in each independent chat."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/compare_scenes.py'
sys.path.insert(0, str(SCRIPT.parent))
from collect_history import codex_owner_group


class CompareScenes(unittest.TestCase):
    def test_pairs_verified_lines_and_keeps_events_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            rows = []
            author = 'fixture-author'
            group = codex_owner_group({'creator_user_id': author})
            for sid, owner, answer in [('alpha', '香菜归我否决。', '要不要辣椒？'), ('beta', '盘子有了主席。', '我来洗。')]:
                src = work / (sid + '.jsonl')
                records = [{'type': 'session_meta', 'payload': {'id': sid, 'creator_user_id': author}}]
                for role, text in [('user','Answers to your questions:\n\n怎么选？\n'+owner), ('assistant',answer)]:
                    records.append({'type':'response_item', 'timestamp':'2026-02-03T06:00:00Z', 'payload':{'type':'message', 'role':role, 'id':sid+role,
                                    'content':[{'type':'text','text':text}]}})
                src.write_text(''.join(json.dumps(r)+'\n' for r in records))
                rows.append({'id':sid+'user', 'client':'codex','session_id':sid,'source':str(src),'line':2,
                             'timestamp':'2026-02-03T06:00:00Z','date':'2026-02-03','text':owner,
                             'owner_group': group, 'input_method':'question_form'})
            index, out = work/'index', work/'checked'
            def save(rows):
                index.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            save(rows)
            def run(*ids):
                return subprocess.run([sys.executable, str(SCRIPT), '--index', str(index), '--ids', *ids, '--output', str(out)], capture_output=True)
            result = run('betauser','alphauser')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b'')
            checked = json.loads(out.read_text())
            self.assertEqual(checked['conversations'], 2)
            self.assertEqual(checked['owner_groups'], [group])
            self.assertEqual(checked['scenes'][0]['input_method'], 'question_form')
            self.assertEqual([r['id'] for r in checked['scenes']], ['betauser','alphauser'])
            self.assertEqual(checked['scenes'][0]['user_text'], '盘子有了主席。')
            self.assertEqual(checked['scenes'][0]['messages'][-1]['role'], 'assistant')
            self.assertEqual(out.stat().st_mode & 0o777, 0o600)
            out.unlink()
            first_source = Path(rows[0]['source'])
            original = first_source.read_text()
            for other_author in ('different-person', None):
                altered = [json.loads(line) for line in original.splitlines()]
                altered[0]['payload']['creator_user_id'] = other_author
                first_source.write_text(''.join(json.dumps(item)+'\n' for item in altered))
                rows[0]['owner_group'] = codex_owner_group(altered[0]['payload'])
                save(rows)
                self.assertNotEqual(run('betauser', 'alphauser').returncode, 0)
                self.assertFalse(out.exists())
            first_source.write_text(original)
            rows[0]['owner_group'] = group
            save(rows)
            limited = subprocess.run([sys.executable, str(SCRIPT), '--index', str(index), '--ids', 'betauser',
                                      '--max-chars','2','--output',str(out)], capture_output=True)
            self.assertEqual(limited.returncode, 0)
            self.assertEqual(json.loads(out.read_text())['scenes'][0]['user_text'], '盘子有了主席。')
            out.unlink()
            rows[1]['conversation_id']='alpha'
            save(rows)
            self.assertEqual(run('betauser','alphauser').returncode,0)
            self.assertEqual(json.loads(out.read_text())['conversations'],1)
            out.unlink()
            rows[0]['text']='这不是原话。'
            save(rows)
            self.assertNotEqual(run('betauser','alphauser').returncode,0)
            self.assertFalse(out.exists())
            self.assertNotEqual(run('betauser','missing').returncode,0)
            self.assertFalse(out.exists())
