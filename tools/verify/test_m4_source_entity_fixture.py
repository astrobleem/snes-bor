import unittest
from pathlib import Path
from m4_source_entity_fixture import fixture_base
from _harness import pasm_constant_in


class FixtureOwnershipTests(unittest.TestCase):
    def test_complete_frontpanel_stamp_arena_includes_slot_256(self):
        root=Path(__file__).resolve().parents[2]
        cache=root/'src/core/stream_cache_fp.pasm'
        start=pasm_constant_in(str(cache),'StreamCacheFp_SlotStamp')
        count=pasm_constant_in(str(cache),'STREAM_FP_CACHE_SLOTS')
        base=fixture_base(root,160)
        self.assertEqual(count,257)
        self.assertGreaterEqual(base,start+count)
        self.assertGreater(base,0x7fb900)
        self.assertEqual(base%32,0)
        with self.assertRaisesRegex(ValueError,'WRAM_CAPACITY'):fixture_base(root,8192)


if __name__=='__main__':unittest.main()
