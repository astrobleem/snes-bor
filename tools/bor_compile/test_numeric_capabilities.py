"""Focused capability boundary and durable evidence tests; no runtime edits."""
import hashlib
from pathlib import Path
import unittest

import numeric_capabilities as n


class NumericCapabilitiesTests(unittest.TestCase):
    def exact(self, op, *domains, **kwargs):
        return n.classify_exact(op, domains, scope=kwargs.get('scope', n.EXACT_SCOPE),
                                assumptions=kwargs.get('assumptions', n.ASSUMPTIONS)).status

    def test_every_retained_tuple_and_changed_input(self):
        for vector in n.load_vectors()['vectors']:
            inputs = vector['input']
            with self.subTest(vector=vector['id']):
                self.assertEqual(n.classify_probe(vector['id'], [inputs], scope=n.NT_SCOPE).status,
                                 n.HISTORICAL_FAMILY_PROVEN)
                for key in inputs:
                    changed = dict(inputs)
                    changed[key] = 'unproven'
                    self.assertEqual(n.classify_probe(vector['id'], [inputs, changed],
                                                     scope=n.NT_SCOPE).status, n.NUMERIC_BLOCKED)

    def test_no_spot_to_domain_or_target_promotion(self):
        v = n.load_vectors()['vectors'][0]
        for domain in ([], {}, [dict(v['input'], updates=[1, 70])],
                       [dict(v['input'], updates=70.0)], [dict(v['input'], extra=0)], [{}]):
            self.assertEqual(n.classify_probe(v['id'], domain, scope=n.NT_SCOPE).status,
                             n.NUMERIC_BLOCKED)
        for scope in ('dos', 'historical_2004', n.EXACT_SCOPE):
            self.assertEqual(n.classify_probe(v['id'], [v['input']], scope=scope).status,
                             n.NUMERIC_BLOCKED)
        self.assertEqual(n.classify_probe('runtime_cast', [{'value': '1.9'}],
                                         scope=n.NT_SCOPE).status, n.NUMERIC_BLOCKED)

    def test_boolean_does_not_match_random_word(self):
        v = n.load_vectors()['vectors'][1]
        self.assertEqual(n.classify_probe(v['id'], [dict(v['input'], random_word=False)],
                                         scope=n.NT_SCOPE).status, n.NUMERIC_BLOCKED)

    def test_analytic_whole_domains_and_closed_boundaries(self):
        d = n.DyadicDomain
        for q in (0, 1, 8, 16):
            for op in ('add', 'subtract', 'compare'):
                self.assertEqual(self.exact(op, d(-(1 << 23), 1 << 23, q),
                                           d(-(1 << 23), 1 << 23, q)), n.OBSERVATIONALLY_EQUIVALENT)
            self.assertEqual(self.exact('add', d(1 << 24, 1 << 24, q), d(0, 0, q)),
                             n.OBSERVATIONALLY_EQUIVALENT)
            self.assertEqual(self.exact('add', d(0, 1 << 24, q), d(0, 1, q)), n.NUMERIC_BLOCKED)
            self.assertEqual(self.exact('subtract', d(-(1 << 24), 0, q), d(0, 1, q)),
                             n.NUMERIC_BLOCKED)

    def test_analytic_rejections(self):
        d = n.DyadicDomain
        for op in ('multiply', 'divide', 'gravity', 'walk', 'randf', 'runtime_cast'):
            self.assertEqual(self.exact(op, d(0, 1), d(0, 1)), n.NUMERIC_BLOCKED)
        self.assertEqual(self.exact('add', d(0, 1)), n.NUMERIC_BLOCKED)
        self.assertEqual(self.exact('add', d(0, 1), d(0, 1, 1)), n.NUMERIC_BLOCKED)
        self.assertEqual(self.exact('compare', d(0, (1 << 24) + 1), d(0, 0)), n.NUMERIC_BLOCKED)
        self.assertEqual(self.exact('compare', d(0, 1), d(0, 1), scope=n.NT_SCOPE), n.NUMERIC_BLOCKED)
        for missing in n.ASSUMPTIONS:
            self.assertEqual(self.exact('add', d(0, 1), d(0, 1),
                                        assumptions=n.ASSUMPTIONS - {missing}), n.NUMERIC_BLOCKED)

    def test_integer_cast_and_invalid_domains(self):
        self.assertEqual(self.exact('integer_identity_cast', n.DyadicDomain(-(1 << 24), 1 << 24)),
                         n.OBSERVATIONALLY_EQUIVALENT)
        self.assertEqual(self.exact('integer_identity_cast', n.DyadicDomain(0, 1, 1)), n.NUMERIC_BLOCKED)
        for args in ((True, 1), (0.0, 1), (2, 1), (0, 1, -1), (0, 1, 17)):
            with self.assertRaises(ValueError):
                n.DyadicDomain(*args)

    def test_durable_sources_and_output_vectors(self):
        fixture = n.load_vectors()
        self.assertEqual(fixture['executable_audit'].keys(), fixture['runs'].keys())
        for artifact in fixture['executable_audit'].values():
            self.assertEqual((artifact['pe_signature'], artifact['machine'], artifact['subsystem']),
                             (0x4550, 0x14c, 3))
        hashes = {
            'watcom_fp_probe.c': '4363fd1a6834a82a9515c2b2c562ad2bc0e78b47e98462a34ecb3ee66b8e431f',
            'watcom_fp_source_cases.c': '9a98e43d6e1f04a52d1d01e9f36027dfbe33c6c37230099b03a07adfbd504492',
            'watcom_fp_values.c': '45518069020c6045fe48f592822552af078b3d86b4b5eaa7d90125005a1258a9',
        }
        for name, digest in hashes.items():
            self.assertEqual(hashlib.sha256(fixture['sources'][name].encode()).hexdigest(), digest)
        source_runs = [lines for name, lines in fixture['runs'].items() if name.startswith('watcom_source_')]
        values_runs = [lines for name, lines in fixture['runs'].items() if name.startswith('watcom_values_')]
        self.assertEqual(len(source_runs), 6)
        self.assertEqual(len(values_runs), 4)
        self.assertTrue(all(lines == source_runs[0] for lines in source_runs))
        self.assertTrue(all(lines == values_runs[0] for lines in values_runs))
        v = {v['id']: v['output'] for v in fixture['vectors']}
        g, w, i, c = (v[k] for k in ('gravity70', 'anything_walk10', 'inair_inline', 'constant_casts'))
        self.assertEqual(source_runs[0], [
            f"gravity a={g['a_bits']} v={g['v_bits']} branch={g['branch']}",
            f"anything_walk x={w['x_bits']} pixel={w['pixel']} xdir={w['xdir_bits']}",
            f"inair a={i['a_bits']} result={i['result']}",
            f"casts +1.9={c['positive']} -1.9={c['negative']}"])
        self.assertIn(f"randf(40,r=118)= {v['randf40']['bits']}", values_runs[0])
        self.assertIn('(int)1.9,(int)-1.9', fixture['sources']['watcom_fp_values.c'])

    def test_retained_source_audit_when_available(self):
        root = Path(__file__).resolve().parents[2] / 'out/bor_compile_s6'
        if not (root / 'BOR.C').exists():
            self.skipTest('optional retained source absent; durable fixture tests still run')
        fixture = n.load_vectors()
        self.assertEqual(hashlib.sha256((root / 'BOR.C').read_bytes()).hexdigest(), fixture['bor_sha256'])
        for name, source in fixture['sources'].items():
            self.assertEqual((root / name).read_text(), source)


if __name__ == '__main__':
    unittest.main()
