"""Catalog size is compiler-owned; runtime IDs retain their u8 ABI."""
import sys
import json
import tempfile
import unittest
from pathlib import Path
from compiler import ROOT

sys.path.insert(0, str(ROOT / 'tools/bor_converter'))
import pack_msu_roster as pack
from verify_msu_roster import parse_record, make_synthetic_char
from gen_pasm_animset import load_manifest


class ProductionRosterLayoutTests(unittest.TestCase):
    def test_header_tracks_actual_linked_count(self):
        for count in (1, 45, 47, 255):
            self.assertEqual(pack.roster_header_size(count), 16 + count * 50)
        for count in (0, 256, -1):
            with self.assertRaises(ValueError):
                pack.roster_header_size(count)

    def test_default_delay_and_47_runtime_records(self):
        with tempfile.TemporaryDirectory(prefix='s8_roster_layout_') as directory:
            prefix = make_synthetic_char(directory, 'actor', idle_frames=1)
            names = ('idle', 'walk', 'attack')
            Path(prefix + '_moveset.json').write_text(json.dumps(dict(
                entity='fixture', roles={name:i for i,name in enumerate(names)},
                animations=[dict(ordinal=i, name=name, dir=prefix+'_'+name)
                            for i,name in enumerate(names)])))
            path = Path(prefix + '_idle') / 'manifest.json'
            manifest = json.loads(path.read_text())
            manifest['frames'][0]['delay'] = None
            path.write_text(json.dumps(manifest))
            self.assertEqual(load_manifest(path.parent), (1, 0))
            payload, sidecar = pack.pack_roster(
                [prefix] * 47, playable_count=1, extended_maps=True)
        self.assertEqual(payload[9], 47)
        self.assertEqual(sidecar['header_size'], 2366)
        cursor = sidecar['header_size']
        for slot, info in enumerate(sidecar['characters']):
            record = parse_record(payload, slot)
            self.assertEqual(record['data_offset'], cursor)
            self.assertEqual(info['data_offset'], cursor)
            self.assertEqual(record['idle_delay'], 0)
            cursor += info['blob_size']
        self.assertEqual(cursor, len(payload))


if __name__ == '__main__':
    unittest.main()
