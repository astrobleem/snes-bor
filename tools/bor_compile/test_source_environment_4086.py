from pathlib import Path
import struct
import unittest
from compiler import Source
from source_environment_4086 import derive, descriptor, wall_requirement, READY


class SourceEnvironment(unittest.TestCase):
    def test_source_stages_have_no_walls(self):
        r = derive(Source(Path(__file__).resolve().parents[2] / 'Masters of the Universe [v.3.0 Build 4086].pak'))
        self.assertEqual([s['source_path'].replace('\\','/').lower() for s in r['stages']],
                         ['data/levels/guile2.txt', 'data/levels/holes.txt'])
        self.assertTrue(all(s['admitted'] and s['wall_count'] == 0 for s in r['stages']))
        self.assertEqual([struct.unpack('<HHH', descriptor(s)) for s in r['stages']], [(READY,0,1),(READY,0,2)])

    def test_walls_are_retained_and_not_admitted(self):
        row = dict(directive='wall', values=['100','160','0','0','40','40','24'], line=9)
        r = wall_requirement([row]); r['stage_id'] = 1
        self.assertEqual(r['walls'],[row]); self.assertFalse(r['admitted'])
        self.assertEqual(r['diagnostics'],['CHECKWALL_NONEMPTY_GEOMETRY_UNBOUND'])
        with self.assertRaisesRegex(ValueError,'NONEMPTY'): descriptor(r)


if __name__ == '__main__': unittest.main()
