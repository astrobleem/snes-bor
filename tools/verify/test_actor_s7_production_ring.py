"""Production relay must run beyond the bounded fixture without ring aliasing."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from actor_s5_entity_fixture import symbols
from actor_s7_persistent_worker import _scpu_relay, _worker_gate


class ProductionTickRing(unittest.TestCase):
    def test_fixture_remains_bounded_but_production_wraps(self):
        fixture = _worker_gate(production_runtime=False)
        production = _worker_gate(production_runtime=True)
        self.assertIn('cmp #512', fixture)
        self.assertIn('cmp #307', _scpu_relay(
            symbols(ROOT / 'src/main.sym'),
            {'S6Host_RemoveHandle': 0x123456,
             'S7_QueueHitSfxLong': 0x123460,
             'S6Bridge_Project': 0x123470},
            production_input=False))
        self.assertNotIn('cmp #512', production)
        self.assertNotIn('cmp #307', production)
        self.assertIn('and #$01FF', production)

    def test_production_relay_rejects_full_ring_and_wraps_head(self):
        relay = _scpu_relay(
            symbols(ROOT / 'src/main.sym'),
            {'S6Host_RemoveHandle': 0x123456,
             'S7_QueueHitSfxLong': 0x123460,
             'S6Bridge_Project': 0x123470},
            production_input=True)
        self.assertNotIn('cmp #307', relay)
        self.assertIn('cmp.l $412004', relay)
        self.assertIn('beq Relay_Failed', relay)
        self.assertGreaterEqual(relay.count('and #$01FF'), 2)


if __name__ == '__main__':
    unittest.main()
