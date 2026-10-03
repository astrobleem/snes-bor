"""Synthetic report-contract regressions; no native or media proof."""
from copy import deepcopy
from pathlib import Path
import unittest
import tempfile
import json
from unittest.mock import patch

import game_s8_acceptance as acceptance


class AcceptanceTests(unittest.TestCase):
    def fixture(self, mode='skip'):
        entries = [['stage', 22 + i, f'DATA/NORMAL/{i}.TXT'] for i in range(16)]
        entries[13], entries[15] = ['scene', 1, 'RUGAL'], ['scene', 2, 'ENDING']
        contract = dict(entries=entries, flags=[int(i in (2, 3, 6, 8, 10, 14)) for i in range(16)])
        contract['completion_flags'] = ([1] * 15 + [0]) if mode == 'easy' else contract['flags'][:]
        contract['completion_policy'] = 'accepted-easy-s7' if mode == 'easy' else 'source-next'
        rom = Path('synthetic-candidate/bor.sfc').resolve()
        artifacts = {str(rom): 'a' * 64}
        campaign = 0 if mode == 'easy' else 3
        def state(i):
            terminal = i == 16
            kind, value, _ = entries[min(i, 15)]
            return dict(state=1 if terminal else 0 if kind == 'stage' else 7,
                        ordinal=min(i, 15), stage=value, campaign=campaign,
                        times=5 if terminal else 4, complete=0)
        rows = []
        for i, (kind, value, name) in enumerate(entries[:3 if mode == 'easy' else 16]):
            row = dict(ordinal=i, kind=kind, source=name, physical_or_scene=value,
                       next_after=bool(contract['flags'][i]), start=state(i), end=state(i + 1),
                       completion_expected=bool(contract['completion_flags'][i]),
                       saw_showcomplete=bool(contract['completion_flags'][i]), skip_sent=mode != 'natural')
            if kind == 'scene':
                row['scene'] = dict(presented=(126 if name == 'RUGAL' else 1997) if mode == 'natural' else 1,
                                    completion=int(mode == 'natural'), skip=int(mode == 'skip'),
                                    transitions=4 if name == 'ENDING' and mode == 'natural' else 0,
                                    late=0, retries=0)
            rows.append(row)
        report = dict(mode=mode, verdict='PASS', checks=[[n, True] for n in acceptance.required_checks(mode, contract)],
                      expected_entries=deepcopy(entries), next_flags=contract['flags'][:], route=rows,
                      completion_flags=contract['completion_flags'][:], completion_policy=contract['completion_policy'],
                      rom_path=str(rom), msu_path=str(rom.with_suffix('.msu')), artifacts=artifacts.copy(),
                      times_before=4, times_after=4 if mode == 'easy' else 5, final=deepcopy(rows[-1]['end']))
        return report, contract, artifacts, rom

    def test_exact_three_contracts(self):
        for mode in ('skip', 'natural', 'easy'):
            r, c, a, p = self.fixture(mode)
            self.assertEqual(acceptance.validate(r, mode, c, a, p)['status'], 'PASS')

    def test_title_dwell_allows_live_telemetry_but_not_credit_drift(self):
        r, c, a, p = self.fixture('natural')
        r['route'][-1]['end']['presentation_gate'] = {
            'nmi_frame_counter': 100, 'dma_queue': {'current_slot': 7}}
        r['final'] = deepcopy(r['route'][-1]['end'])
        r['final']['presentation_gate']['nmi_frame_counter'] += 180
        r['final']['presentation_gate']['dma_queue']['current_slot'] = 2
        self.assertEqual(acceptance.validate(r, 'natural', c, a, p)['status'], 'PASS')
        r['final']['times'] += 1
        self.assertEqual(acceptance.validate(r, 'natural', c, a, p)['status'], 'REJECTED')

    def test_pass_label_cannot_hide_missing_or_false_gates(self):
        for mutation in ('missing', 'false', 'duplicate', 'error'):
            r, c, a, p = self.fixture()
            if mutation == 'missing':
                r['checks'].pop()
            elif mutation == 'false':
                r['checks'][0][1] = False
            elif mutation == 'duplicate':
                r['checks'].append(r['checks'][0])
            else:
                r['error'] = 'prior failure'
            self.assertEqual(acceptance.validate(r, 'skip', c, a, p)['status'], 'REJECTED')

    def test_artifact_source_route_credit_and_counter_tampering(self):
        mutations = [lambda r: r['artifacts'].clear(),
                     lambda r: r['expected_entries'].reverse(),
                     lambda r: r['next_flags'].__setitem__(14, 0),
                     lambda r: r['route'].pop(),
                     lambda r: r['route'][14]['end'].__setitem__('times', 5),
                     lambda r: r['route'][13]['scene'].__setitem__('skip', 2),
                     lambda r: r['route'][13]['scene'].__setitem__('late', 1),
                     lambda r: r.__setitem__('times_after', 6)]
        for mutate in mutations:
            r, c, a, p = self.fixture()
            mutate(r)
            self.assertEqual(acceptance.validate(r, 'skip', c, a, p)['status'], 'REJECTED')

    def test_natural_requires_1997_frames_four_transitions(self):
        for field, value in [('presented', 1996), ('transitions', 3), ('skip', 1)]:
            r, c, a, p = self.fixture('natural')
            r['route'][15]['scene'][field] = value
            self.assertEqual(acceptance.validate(r, 'natural', c, a, p)['status'], 'REJECTED')

    def test_fake_immediate_skip_override_rejected(self):
        r, c, a, p = self.fixture()
        r['route'][15].update(skip_sent=False, immediate_skip_fences={'PASS': True})
        self.assertEqual(acceptance.validate(r, 'skip', c, a, p)['status'], 'REJECTED')

    def test_missing_reports_never_certify_release(self):
        _, c, _, p = self.fixture()
        with patch.object(acceptance, 'contracts', return_value={m: c for m in ('skip', 'natural', 'easy')}), \
                patch.object(acceptance, 'digest', return_value='a' * 64):
            result = acceptance.aggregate({}, p)
        self.assertEqual(result['route_evidence'], 'INCOMPLETE_OR_REJECTED')
        self.assertEqual(result['release_verdict'], 'BLOCKED_PENDING_EVIDENCE')
        self.assertTrue(all(result['per_feature'][name]['status'] == 'PENDING_NATIVE_EVIDENCE'
                            for name in acceptance.PENDING))
        self.assertEqual(len(result['entry_inventory']), 16)
        self.assertEqual(sum(e['kind'] == 'stage' for e in result['entry_inventory']), 14)
        self.assertEqual(result['per_feature']['all_source_spawn_integration']['status'], 'MISSING')
        self.assertEqual(result['native_route_and_admission_evidence'], 'MISSING_OR_REJECTED')

    def test_feature_generic_pass_is_not_native_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'receipt.json'
            artifacts = {str((Path(folder) / 'bor.sfc').resolve()): 'a' * 64}
            path.write_text(json.dumps(dict(verdict='PASS', artifacts=artifacts, checks=[['anything', True]])))
            self.assertEqual(acceptance.inspect_feature(path, artifacts)['status'], 'UNBOUND_FEATURE_SCHEMA')
            path.write_text(json.dumps(dict(verdict='FAIL', artifacts=artifacts, checks=[['anything', False]])))
            self.assertEqual(acceptance.inspect_feature(path, artifacts)['status'], 'REJECTED')

    def test_traversal_report_owned_plan_cannot_certify_itself(self):
        expected = [dict(stage=22, index=0, spawn=True)]
        r = dict(spawn_traversal=dict(status='PASS', expected=[], completed=[]))
        self.assertEqual(acceptance.validate_traversal(r, expected)['status'], 'REJECTED')

    def test_full_traversal_binding_and_identity_tamper(self):
        # Synthetic native-shaped rows exercise validation, not native proof.
        acceptance.contracts()
        import build_rom as build
        entries = build.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']
        expected = acceptance.campaign_bridge().traversal_plan(build, entries)
        def admitted_mode(row):
            source_type = row.get('source_type')
            if source_type == 'item':
                return 3
            if source_type == 'steamer':
                return 5
            if source_type == 'obstacle':
                pickup_tag = (bytes.fromhex(row['record'])[6] >> 5) & 7
                return 5 if pickup_tag == 7 else 3
            if source_type in (None, 'None'):
                return 3
            return 2

        completed = [dict(row, campaign=3, exists=1, hp=64,
                          mode=admitted_mode(row), idle_frames=2, load_result=1,
                          boss=int(row['boss'] or 0), offset=192, object_num=i)
                      for i, row in enumerate(expected)]
        checks = [['all 614 source spawn identities and every control record observed', True]]
        checks += [[f'entry {i} every packed record consumed natively', True]
                   for i, e in enumerate(entries) if e[0] == 'stage']
        r = dict(expected_entries=entries, checks=checks, spawn_traversal=dict(
            status='PASS', expected=expected, completed=completed))
        self.assertEqual(acceptance.validate_traversal(r, expected)['status'], 'PASS')
        next(row for row in completed if row['spawn'])['roster'] = 255
        self.assertEqual(acceptance.validate_traversal(r, expected)['status'], 'REJECTED')

    def test_malformed_receipt_rejected(self):
        _, c, a, p = self.fixture()
        for receipt in (None, [], {'mode': 'skip', 'verdict': 'PASS'}):
            self.assertEqual(acceptance.validate(receipt, 'skip', c, a, p)['status'], 'REJECTED')


if __name__ == '__main__':
    unittest.main()
