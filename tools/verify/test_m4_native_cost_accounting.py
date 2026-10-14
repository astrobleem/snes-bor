import json
from pathlib import Path
import unittest
from m4_native_cost_accounting import account
from m4_native_cost_attribution import plan,ROM_SHA
import hashlib


def event(kind,name,t,ret=0,value=0):return dict(kind=kind,name=name,clock=t,ret=ret,value=value)


class CostAccountingTests(unittest.TestCase):
    def fixture(self):
        cost=dict(start=0,complete=100,production_clocks=100,publication_clocks=120,composition_clocks=0,dma_clocks=10,composition_intervals=[])
        events=[event('S','OnlinePublish',0),event('E','WarmStage',10,1000),event('B','StageMVN',15,1001,80),
                event('E','NMI',20,1002),event('P','1002',25),event('P','1001',30),event('E','WarmFlush',35,1003),
                event('D','DMA',40,16),event('d','DMA',50),event('P','1003',55),event('P','1000',60),
                event('S','OnlineComplete',100),event('S','Release',120)]
        return events,[cost]

    def test_nested_flush_dma_interrupt_and_inline_copy_are_not_double_counted(self):
        es,cs=self.fixture();r=account(es,cs)[0]
        self.assertEqual(r['routines']['WarmStage']['exclusive_active_clocks'],25)
        self.assertEqual(r['routines']['WarmStage']['inclusive_elapsed_clocks'],50)
        self.assertEqual(r['routines']['WarmStage']['inclusive_active_clocks'],35)
        self.assertEqual(r['routines']['WarmFlush']['exclusive_active_clocks'],10)
        self.assertEqual(r['inline_blocks']['StageMVN']['inclusive_active_clocks'],10)
        self.assertEqual(r['routines']['WarmStage']['inclusive_dma_bytes'],16)
        self.assertEqual(r['routines']['WarmStage']['own_dma_bytes'],0)
        self.assertEqual(r['routines']['WarmFlush']['own_dma_bytes'],16)
        self.assertEqual(r['attributed']['DMA'],10)
        self.assertEqual(r['attributed']['NMI'],5)
        self.assertEqual(sum(r['attributed'].values()),100)
        self.assertEqual(r['reconciliation_residual_clocks'],0)

    def test_missing_nmi_return_fails_closed_instead_of_fabricating_attribution(self):
        es,cs=self.fixture();es=[e for e in es if not(e['kind']=='P' and e['name']=='1002')]
        with self.assertRaisesRegex(ValueError,'OPEN_CALL'):account(es,cs)

    def test_wrong_production_boundary_fails_reconciliation(self):
        es,cs=self.fixture();cs[0]['production_clocks']+=1
        with self.assertRaisesRegex(ValueError,'PRODUCTION_RECONCILIATION'):account(es,cs)

    def test_retained_rom_and_resolved_call_sites_are_immutable(self):
        root=Path('out/byor-motu-cost-profile-v3');contract=json.loads((root/'contract.json').read_text())
        p=plan(root,contract)
        self.assertEqual(hashlib.sha256((root/'native/bor.sfc').read_bytes()).hexdigest(),ROM_SHA)
        self.assertGreater(len(p['calls']),10)
        script=(root/'native/callback_owner.lua').read_text().split('-- NATIVE_COST_OBSERVER_BEGIN')[1]
        self.assertNotIn('emu.write',script)
        self.assertIn('profCheckNmi',script)

    def test_real_epochs_reconcile_with_no_open_calls_and_exact_tile_counts(self):
        report=json.loads(Path('out/byor-motu-cost-profile-v3/cost-attribution.json').read_text())
        self.assertEqual(len(report['epochs']),18)
        for e in report['epochs']:
            self.assertEqual(e['reconciliation_residual_clocks'],0)
            self.assertEqual(sum(e['attributed'].values()),e['production_clocks'])
            if e['measured_costs'].get('render_noop'):self.assertFalse(e['routines'])


if __name__=='__main__':unittest.main()
