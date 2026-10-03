"""Targeted S6 reference tests; no emulator, runtime edits, or ModelIR changes."""
import unittest
from fractions import Fraction as F
from pathlib import Path

import source_actor_numeric as n


class SourceActorNumericTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_dir = Path(__file__).resolve().parents[2] / 'out/bor_compile_s6'
        n.verify_rng_sources(cls.source_dir)
        cls.instructions = n.rng_instructions((cls.source_dir / 'RAND32.ASM').read_text())

    def test_pinned_source(self):
        path = Path(__file__).resolve().parents[2] / 'out/bor_compile_s6/BOR.C'
        self.assertEqual(n.verify_source(path), n.PINNED_BOR_SHA256)

    def test_rng_golden_call_sequence(self):
        expected = [
            (2317836195, 390629927, 927), (754553504, 68103417, 417),
            (951082585, 889796784, 784), (1907194398, 2981851565, 565),
            (1397117695, 453071686, 686), (3530897612, 1559876213, 213),
            (218072853, 3398372607, 607), (858987050, 4075434803, 803)]
        seed = n.INITIAL_SEED
        for after, word, residue in expected:
            d = n.randf_decision(seed, 3)
            self.assertEqual((d.seed_after, d.returned_word, d.residue), (after, word, residue))
            self.assertEqual(d.nominal_value, F(3 * residue, 1000))
            seed = d.seed_after

    def test_pinned_header_and_instruction_shape(self):
        self.assertEqual(n.verify_rng_sources(self.source_dir), n.PINNED_RNG_SHA256)
        header = (self.source_dir / 'RAND32.H').read_text()
        self.assertIn('extern unsigned int __near rand32(void);', header)
        self.assertIn('#pragma aux rand32 modify[eax edx] value[eax];', header)
        self.assertIn('#pragma aux srand32 parm[eax];', header)
        self.assertEqual([' '.join(i) for i in self.instructions], [
            'mov eax seed', 'mov edx 1103515245', 'mul edx', 'shl edx 16',
            'add eax 12345', 'adc edx 0ffffh', 'mov seed eax', 'shr eax 16',
            'and edx 0ffff0000h', 'or eax edx', 'ret'])
        asm = (self.source_dir / 'RAND32.ASM').read_text().lower()
        self.assertRegex(asm, r'seed\s+dd\s+1234567890')
        setter = asm.split('srand32_ proc near')[1].split('srand32_ endp')[0]
        self.assertEqual(setter.split(), ['mov', 'seed,', 'eax', 'ret'])

    def test_actual_x86_steps_match_recurrence_including_carry(self):
        # Invert the odd multiplier mod2^32 to force all low-add overflow edges.
        inverse = pow(1103515245, -1, 2**32)
        edges = [0, 1, 65535, 65536, 0xFFFFFFFF, n.INITIAL_SEED]
        edges += [(low * inverse) & 0xFFFFFFFF for low in
                  (0xFFFFFFFF - 12345, 0xFFFFFFFF - 12344, 0xFFFFFFFF)]
        for seed in edges:
            self.assertEqual(n.random32_x86(seed, self.instructions), n.random32_step(seed))
        seed = n.INITIAL_SEED
        for _ in range(8192):
            expected = n.random32_step(seed)
            self.assertEqual(n.random32_x86(seed, self.instructions), expected)
            seed = expected[0]
        for carry in (0, 1):
            low_product = 0xFFFFFFFF - 12345 + carry
            seed = (low_product * inverse) & 0xFFFFFFFF
            _, trace = n.random32_x86(seed, self.instructions, with_trace=True)
            self.assertEqual(trace[4]['carry'], carry)
            # shifted EDX low16 starts zero; ADC ffff propagates only if CF=1.
            self.assertEqual(trace[5]['edx'] & 65535, 65535 if carry == 0 else 0)

    def test_bor_has_global_consumers_but_no_reseed_path(self):
        calls = n.audit_bor_rng_calls((self.source_dir / 'BOR.C').read_text())
        self.assertEqual(calls['rand32'], (705, 3814, 4054, 4066, 4094, 4108, 4230, 4272, 4279))
        for name in ('srand32', 'srand', 'randomize'):
            self.assertEqual(calls[name], ())
        self.assertFalse(calls['direct_seed_identifier'])

    def test_limb_carries_and_unsigned_remainder(self):
        # Exhaustive low16 with both extreme high halves, plus seeded trace.
        for high in (0, 65535):
            for low in range(65536):
                seed = (high << 16) | low
                self.assertEqual(n.random32_limbs(seed), n.random32_step(seed))
        seed = n.INITIAL_SEED
        for _ in range(4096):
            seed, word = n.random32_step(seed)
            self.assertEqual(n.unsigned_mod1000(word), word % 1000)
        self.assertEqual(n.unsigned_mod1000(0xFFFFFFFF), 295)

    def test_no_call_for_max_zero_and_global_call_order(self):
        d = n.randf_decision(n.INITIAL_SEED, 0)
        self.assertFalse(d.consumed)
        self.assertEqual(d.seed_before, d.seed_after)
        a = n.randf_decision(d.seed_after, 3)
        b = n.randf_decision(a.seed_after, 3)
        self.assertEqual((a.residue, b.residue), (927, 417))
        self.assertNotEqual(a.returned_word, a.seed_after)

    def test_modulo_bias_not_uniform_resampling(self):
        quotient, remainder = divmod(2**32, 1000)
        self.assertEqual((quotient, remainder), (4294967, 296))

    def test_rng_input_domain(self):
        for value in (-1, 2**32):
            for function in (n.random32_step, n.random32_limbs, n.unsigned_mod1000):
                with self.assertRaises(ValueError):
                    function(value)

    def test_fixedpoint_1000_covers_nominal_speed_domain(self):
        for residue in range(1000):
            velocity = n.drift_velocity(F(9, 10), residue, 20)
            self.assertEqual(velocity * 1000, 900 + 3 * residue)
        exact_2560 = [r for r in range(1000)
                      if (n.drift_velocity(F(9, 10), r, 20) * 2560).denominator == 1]
        self.assertEqual(exact_2560, list(range(0, 1000, 25)))

    def test_old_byte_random_approximation_is_observable(self):
        # Samples are not interchangeable RNG sequences. Compare one nominal
        # r=1 against nearest byte-domain sample k=0 (3*k/256).
        source, adapted = F(20), F(20)
        for _ in range(31):
            source += F(903, 1000)
            adapted += F(9, 10)
        self.assertEqual((n.pixel(source), n.pixel(adapted)), (47, 47))
        source += F(903, 1000)
        adapted += F(9, 10)
        # Retain a direct exact boundary witness at tick333 too.
        self.assertEqual((n.pixel(F(20) + 333 * F(903, 1000)),
                          n.pixel(F(20) + 333 * F(9, 10))), (320, 319))

    def test_fractional_difference_can_be_unobservable_in_short_window(self):
        a, b = F(1001, 100), F(1002, 100)
        self.assertNotEqual(a, b)
        self.assertEqual(n.pixel(a), n.pixel(b))
        self.assertEqual(n.drift_step(a, 0)[1], n.drift_step(b, 0)[1])
        self.assertEqual(n.INTERNAL, 'IMPLEMENTATION_DETAIL_NOT_OBSERVABLE')

    def test_bounds_before_motion_and_independent_authored_sign(self):
        self.assertEqual(n.drift_step(400, 1), (F(401), True))
        self.assertEqual(n.drift_step(401, 1), (F(401), False))
        self.assertEqual(n.drift_step(-80, -1), (F(-81), True))
        self.assertEqual(n.drift_step(-81, -1), (F(-81), False))
        self.assertGreater(n.drift_velocity(1, 0, 159), 0)
        self.assertLess(n.drift_velocity(1, 0, 160), 0)

    def test_exact_binary_unit_speed_control_domain(self):
        # Ordinary speed1 control, no random additive velocity/biker override.
        for velocity in (F(1), F(-1), F(1, 2)):
            self.assertTrue(n.certify_exact_translation(20, velocity, 10000, (-80, 400)))
        self.assertFalse(n.certify_exact_translation(20, F(9, 10), 1))
        self.assertFalse(n.certify_exact_translation(2**24, 1, 1))

    def test_conditional_float_position_counterexample_retained(self):
        w = n.conditional_drift_witness(20, '0.9', 0, 20)
        self.assertEqual((w['tick'], w['rational_pixel'], w['stored_pixel']), (10, 29, 28))
        self.assertEqual(w['stored_x'], '7602175/262144')
        self.assertEqual(w['classification'], n.VISIBLE)
        # Positive positions: floor vs truncation cannot erase this witness.
        self.assertEqual(n.pixel(F(w['stored_x']), 'floor'), 28)

    def test_counterexample_residue_is_reachable_from_specified_seed(self):
        seed = n.INITIAL_SEED
        for _ in range(118):
            before = seed
            seed, word = n.random32_step(seed)
        self.assertEqual((before, seed, word, word % 1000),
                         (2514399119, 3236463132, 2730017000, 0))

    def test_rational_enclosure_distinguishes_ambiguity_from_witness(self):
        result = n.translation_observation_enclosure(20, F(9, 10), F(1, 1000000), 10)
        self.assertEqual(result['certified_prefix_steps'], 9)
        self.assertEqual(result['ambiguous_tick'], 10)
        self.assertFalse(result['counterexample'])

    def test_conditional_gravity_branch_counterexample_retained(self):
        w = n.conditional_gravity_witness()
        self.assertEqual((w['tick'], w['rational_velocity'], w['stored_velocity']),
                         (70, '-6', '-12582905/2097152'))
        self.assertGreater(F(w['stored_velocity']), -6)

    def test_integer_only_oracle_round_ties_even(self):
        q = n.round_binary32_normal
        self.assertEqual(q(F(1) + F(1, 2**24)), 1)
        self.assertEqual(q(F(1) + F(3, 2**24)), F(1) + F(1, 2**22))
        self.assertEqual(q(F(-3, 2)), F(-3, 2))

    def test_cadence_catchup_pause_cap_and_equality(self):
        ticks = n.source_tick_batch(0, 10)
        self.assertEqual(n.think_due_times(ticks, 0), ((0, 2, 4, 6, 8), 10))
        self.assertEqual(n.source_tick_batch(10, 9, paused=True), ())
        self.assertEqual(len(n.source_tick_batch(10, 101)), 100)
        self.assertEqual(n.think_due_times((1, 3, 5), 0), ((), 0))

    def test_integer_clock_partition_and_source_batch_partition(self):
        intervals = [357368, 357364] * 1000
        ticks, remainder = n.rational_clock_frames(intervals, 21477270)
        self.assertEqual((sum(ticks), remainder), divmod(sum(intervals) * 200, 21477270))
        self.assertEqual(n.source_tick_batch(0, 4) + n.source_tick_batch(4, 6),
                         n.source_tick_batch(0, 10))
        # Source cap is per update() call, so arbitrary batching is NOT invariant.
        self.assertNotEqual(n.source_tick_batch(0, 150),
                            n.source_tick_batch(0, 75) + n.source_tick_batch(75, 75))


if __name__ == '__main__':
    unittest.main()
