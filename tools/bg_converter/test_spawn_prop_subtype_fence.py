import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bg_converter"))

import build_spawn_table as builder  # noqa: E402
from spawn_parse import SpawnEvent  # noqa: E402


class PropSubtypeFenceTests(unittest.TestCase):
    def test_money_prop_and_steamer_have_distinct_runtime_tags(self):
        chair = SpawnEvent("chair", 10)
        chair.item = "money"
        steamer = SpawnEvent("steamer", 20)
        count, packed = builder.convert_events(
            [chair, steamer],
            {"chair": "obstacle", "steamer": "steamer"},
            entity_lookup={
                "money": {"name": "money", "score": 1000},
                "steamer": {"name": "steamer"},
            },
        )
        self.assertEqual(count, 2)
        records = [packed[offset:offset + 10] for offset in (0, 10)]
        self.assertEqual(records[0][6] & 7, builder.RECORD_KIND_PROP)
        self.assertEqual((records[0][6] >> 5) & 7, builder.PICKUP_TYPE_MONEY)
        self.assertEqual(records[1][6] & 7, builder.RECORD_KIND_PROP)
        self.assertEqual((records[1][6] >> 5) & 7, builder.PICKUP_TYPE_STEAMER)

    def test_runtime_dispatch_uses_kind_before_overlapping_subtype_bits(self):
        source = (ROOT / "src" / "core" / "spawn.pasm").read_text(encoding="utf-8")
        self.assertIn("SPAWN_PICKUP_STEAMER = 7", source)
        for slot in (1, 2, 3):
            dispatch = source.split(f"Spawn_Play__slot{slot}_prop_fields:", 1)[0]
            dispatch = dispatch.rsplit(f"Spawn_Play__slot{slot}_not_prop:", 1)[-1]
            self.assertIn("lda.l Spawn_ScratchPickupType", dispatch)
            self.assertIn("cmp #SPAWN_PICKUP_STEAMER", dispatch)
        shared = source.split("Spawn_Play__slot45_non_prop:", 1)[0]
        shared = shared.rsplit("    lda.l Spawn_ScratchKind\n    cmp #SPAWN_KIND_PROP", 1)[-1]
        self.assertIn("Spawn_ScratchPickupType", shared)
        self.assertIn("jml Spawn_Play__slot45_prop", shared)
        non_prop = source.split("Spawn_Play__slot45_non_prop:", 1)[1].split(
            "Spawn_Play__slot45_steam:", 1
        )[0]
        self.assertIn("Spawn_ScratchSubtype", non_prop)


    def test_reused_slot45_clears_timer_prop_y_sentinel(self):
        source = (ROOT / "src" / "core" / "spawn.pasm").read_text(encoding="utf-8")
        slot45 = source.split("Spawn_Play__slot45:", 1)[1].split(
            "Spawn_Play__slot45_non_prop:", 1
        )[0]
        y_store = slot45.index("sta CHAR_POS_Y")
        y_clear = slot45.index("stz CHAR_POS_Y+1")
        kind_dispatch = slot45.index("lda.l Spawn_ScratchKind")
        self.assertLess(y_store, y_clear)
        self.assertLess(y_clear, kind_dispatch)


if __name__ == "__main__":
    unittest.main()
