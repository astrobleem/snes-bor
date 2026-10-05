import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from compiler import Source
from source_profile import document, discover
from dialect_4086 import stage_queue, animation_frames


def rows(text):
    return [dict(directive=t.split()[0], values=t.split()[1:], line=i)
            for i, t in enumerate(text.splitlines(), 1) if t.strip()]


class Dialect4086Tests(unittest.TestCase):
    def test_at_commits_zero_entry_and_reset_replaces_pending(self):
        q = stage_queue(rows('spawn A\nwait\nat 3\nat 4\ngroup 0 0\nat 5\n'))
        self.assertEqual([r['kind'] for r in q['records']], ['wait', 'noop', 'group'])
        self.assertEqual(q['records'][2]['group_min'], 100)
        self.assertEqual(q['records'][2]['group_max'], 1)
        self.assertEqual(q['replaced_before_commit'][0]['kind'], 'spawn')
        self.assertFalse(q['runtime_lowered'])

    def test_delay_inherits_across_animation_but_geometry_resets(self):
        a, b = animation_frames(rows('anim idle\ndelay 6\noffset 9 10\nbbox 1 2 3 4\n'
            'sound a.wav\nframe a.gif\n@cmd spawn01 "Fx" 18 93 0\nframe b.gif\n'
            'anim walk\nframe c.gif\n'))
        self.assertEqual(a['events'][0]['frame_index'], 1)
        self.assertEqual(a['events'][0]['start_tick'], 12)
        self.assertIsNotNone(a['frames'][0]['sound'])
        self.assertIsNone(a['frames'][1]['sound'])
        self.assertEqual(b['frames'][0]['delay_ticks'], 12)
        self.assertEqual(b['frames'][0]['offset'], [0, 0])
        self.assertEqual(b['frames'][0]['bbox'], [0, 0, 0, 0])

    def test_modifiers_on_zero_base_and_music_physical_lookahead(self):
        q = stage_queue(rows('coords 5 6 7\nat 8\nmusic a.bor\nat 9\n'))
        self.assertEqual([r['kind'] for r in q['records']], ['zero_base_with_modifiers', 'music'])
        q = stage_queue(rows('music a.bor\n\nat 9\n'))
        self.assertEqual(q['records'][0]['kind'], 'noop')

    def test_supplied_demo_empty_entry_and_weapon_event(self):
        source = Source(Path(__file__).resolve().parents[2] / 'Masters of the Universe [v.3.0 Build 4086].pak')
        docs = {k: document(source, name) for k, (name, _) in source.index.items() if k.endswith('.txt')}
        structure = discover(source, docs)
        queues = [stage_queue(docs[e['source_path'].replace('\\', '/').lower()]['directives'])
                  for e in structure['sets'][0]['entries'] if e['kind'] == 'STAGE']
        self.assertEqual(sum(q['authored_records'] for q in queues), 35)
        self.assertEqual(sum(q['source_spawns'] for q in queues), 22)
        self.assertEqual(sum(q['zero_initialized_records'] for q in queues), 1)
        model = next(m for m in structure['models'] if m['name'] == 'He_ManB')
        animations = animation_frames(docs[model['source_path'].replace('\\', '/').lower()]['directives'])
        breath = next(a for a in animations if a['role'] == 'freespecial4')
        event = next(e for e in breath['events'] if e['function'] == 'spawn01')
        self.assertEqual(event['start_tick'], 48)
        self.assertEqual(event['arguments'], ['"HBreath"', '18', '93', '0'])
        self.assertEqual(breath['duration_ticks'], 312)


if __name__ == '__main__':
    unittest.main()
