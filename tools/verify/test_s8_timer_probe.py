"""Offline probe plumbing tests only; never native runtime evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from game_s8_timer_probe import gates, parse, prepare, artifact_paths


class ProbeTests(unittest.TestCase):
    def test_retirement_wait_observes_host_completion_not_pending_zero_alone(self):
        from game_s8_timer_driver import await_native_retirement
        states = iter([dict(pending=3, hp=4, roster=46, kind=0),
                       dict(pending=0, hp=4, roster=46, kind=0),
                       dict(pending=0, hp=0, roster=46, kind=0)])
        ticks = []
        self.assertTrue(await_native_retirement(lambda: next(states), lambda: ticks.append(1),
                         lambda label, ok: self.assertTrue(ok, label)))
        self.assertEqual(len(ticks), 2)

    def test_retirement_wait_cannot_accept_stuck_live_actor(self):
        from game_s8_timer_driver import await_native_retirement
        def require(label, ok):
            if not ok:
                raise AssertionError(label)
        with self.assertRaisesRegex(AssertionError, 'callback completes'):
            await_native_retirement(lambda: dict(pending=0, hp=4, roster=46, kind=0),
                                    lambda: None, require)

    def test_native04_exact_retirement_was_already_successful(self):
        root = Path(__file__).resolve().parents[2] / 'out/s8_timer_native_04'
        if not (root/'mesen.log').exists():
            self.skipTest('preserved native04 evidence not present')
        checks = gates(json.loads((root/'spec.json').read_text()), parse((root/'mesen.log').read_text()))
        self.assertTrue(checks['retire_exactly_600_ticks'])
        self.assertTrue(checks['retirement_clears_actual_actor'])
        self.assertTrue(checks['no_pending_oam_submission'])
        self.assertFalse(checks['post_retire_slot_reused_natively'])

    def test_reuse_fixture_avoids_legacy_art_retention_records(self):
        from game_s8_timer_driver import pressure_record
        # Trigger80 explicit, trigger0 legacy0, trigger0 explicit30.
        rows = [bytes(10), bytes(10), bytes(10),
                bytes([80,0,0,0,0,0,0x45,0,0,30]), bytes(10),
                bytes([0,0,0,0,0,0,0x45,0,0,30])]
        spec = dict(queue=b''.join(rows).hex(), time_indices=[2], spawn_indices=[3,4,5])
        self.assertEqual(pressure_record(spec), 5)
        rows[5] = bytes([0,0,0,0,0,0,0x45,0,0,0])
        spec['queue'] = b''.join(rows).hex()
        self.assertEqual(pressure_record(spec), 5)  # real Ralf0 is not unbound

    def test_reuse_gate_requires_authored_source_record_and_roster(self):
        import inspect
        code = inspect.getsource(gates).split("checks['post_retire_slot_reused_natively']", 1)[1].split("checks['retirement_clears_actual_actor']", 1)[0]
        self.assertIn("e['spawn'] == ordinary['index']", code)
        self.assertIn("e['spawn_roster'] == ordinary['expected_roster']", code)
        self.assertIn("== ordinary['expected_roster'] for f in frames", code)
        self.assertNotIn('!= 46', code)

    def test_native03_pending_render_and_pressure_are_proven_not_full_pass(self):
        root = Path(__file__).resolve().parents[2] / 'out/s8_timer_native_03'
        if not (root/'mesen.log').exists():
            self.skipTest('preserved native03 evidence not present')
        checks = gates(json.loads((root/'spec.json').read_text()), parse((root/'mesen.log').read_text()))
        self.assertTrue(checks['no_pending_oam_submission'])
        self.assertTrue(checks['native_admission_under_reservation_pressure'])
        self.assertTrue(checks['retire_exactly_600_ticks'])
        self.assertFalse(checks['post_retire_slot_reused_natively'])
        self.assertFalse(checks['timeout_damage_sound_reset'])

    def test_native02_reanalysis_keeps_real_failures(self):
        root = Path(__file__).resolve().parents[2] / 'out/s8_timer_native_02'
        if not (root/'mesen.log').exists():
            self.skipTest('preserved native02 evidence not present')
        checks = gates(json.loads((root/'spec.json').read_text()), parse((root/'mesen.log').read_text()))
        self.assertTrue(checks['neutral_overlap_cannot_auto_collect'])
        self.assertFalse(checks['no_pending_oam_submission'])
        self.assertFalse(checks['native_admission_under_reservation_pressure'])

    def test_native_normal_prompt_sequence(self):
        from game_s8_timer_driver import select_normal
        m = SimpleNamespace(BTN_START=1, BTN_RIGHT=2)
        startup = SimpleNamespace(STATE=10, DIFFICULTY=11, SELECTED=12,
                                  CHAR_STEP=13, CHARSELECT=2, PLAYING=0)
        state = {10: 1, 11: 0, 12: 0, 13: 0}
        buttons = []
        def tick(button=None):
            buttons.append(button)
            if button == 1:
                if state[10] == 1:
                    state.update({10: 2, 11: 1})
                elif state[11] == 1:
                    self.assertEqual(state[12], 1)
                    state.update({11: 3, 13: 3})
                else:
                    state[10] = 0
            elif button == 2:
                self.assertEqual((state[10], state[11]), (2, 1))
                state[12] = 1
        def wait(predicate, limit, label):
            self.assertTrue(predicate(), label)
        select_normal(m, startup, lambda address, size=1: state[address], tick, wait,
                      lambda label, condition: self.assertTrue(condition, label))
        self.assertEqual(buttons, [1, 2, None, 1, None, 1])
        self.assertEqual(state[10], 0)

    def test_empty_log_cannot_pass_any_gate(self):
        checks = gates(dict(queue='', playing=3, paused=4, stride=133), [])
        self.assertGreaterEqual(len(checks), 10)
        self.assertFalse(any(checks.values()), checks)

    def test_native_log_prefix_and_payload(self):
        rows = parse('Mesen: S8T|collect|81|24|left=40000|rx=2|queue=2e06|vram=4124\n')
        self.assertEqual(rows, [dict(event='collect', tick=81, frame=24,
                                    left=40000, rx=2, queue='2e06', vram='4124')])

    def test_nonlinked_build_rejected_before_artifact_access(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'build.json'
            path.write_text(json.dumps(dict(status='ASSEMBLY_ONLY')))
            with self.assertRaisesRegex(ValueError, 'LINKED'):
                prepare(path)

    def test_truncated_native_record_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            parse('S8T|collect|broken|1|left=40000')

    def test_candidate_rom_and_msu_with_explicit_symbol_path(self):
        with patch.dict('os.environ', {'BOR_TEST_ROM': str(Path('candidate/bor.sfc').resolve())}):
            paths = artifact_paths({'paths': {'src/main.sym': 'candidate/main.sym'}})
        self.assertEqual(Path(paths['distribution/bor.sfc']).name, 'bor.sfc')
        self.assertEqual(Path(paths['distribution/bor.msu']).suffix, '.msu')
        self.assertEqual(Path(paths['src/main.sym']).name, 'main.sym')
        self.assertIn('candidate', paths['src/main.sym'])

    def test_native_driver_refuses_unlinked_before_session_or_output(self):
        from game_s8_timer_driver import run_native
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / 'build.json'
            manifest.write_text('{"status":"ASSEMBLY_ONLY"}')
            with self.assertRaisesRegex(ValueError, 'LINKED'):
                run_native(SimpleNamespace(linked=manifest, output=root/'run'))
            self.assertFalse((root/'run').exists())


if __name__ == '__main__':
    unittest.main()
