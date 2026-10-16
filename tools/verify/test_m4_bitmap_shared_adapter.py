"""Offline adapter boundary/error tests. Native Poppy/Mesen is separate."""
import unittest, tempfile
from pathlib import Path
from unittest.mock import patch
import m4_bitmap_shared_native as adapter
from home_bitmap_shared_cells import transform
from home_borrow_bitmap import _routines


def dump(words):
    return b''.join(int(x).to_bytes(2,'little') for x in words).hex()

class AdapterTests(unittest.TestCase):
    def test_accepted_receipt_fingerprints_use_handoff_scope(self):
        entries=[dict(path=f'file-{i}',sha256='0'*64) for i in range(29)]
        self.assertIs(adapter.inherited_fingerprints({'handoff':{
            'inherited_dirty_files_preserved':entries}}),entries)
        with self.assertRaises(KeyError):
            adapter.inherited_fingerprints({'inherited_dirty_files_preserved':entries})
        with self.assertRaisesRegex(ValueError,'29 inherited'):
            adapter.inherited_fingerprints({'handoff':{'inherited_dirty_files_preserved':entries[:-1]}})

    def test_bootstrap_marker_contract_is_retained(self):
        import m4_restore_single_pass_native as prior
        source='-- boot\n-- NONBLANK_OBSERVER_BEGIN\n-- old observers\n'
        self.assertEqual(prior.bootstrap_prefix(source),'-- boot\n')
        for x in ('-- ONLINE_OBSERVER_BEGIN\n','-- NONBLANK_OBSERVER_BEGIN\n-- NONBLANK_OBSERVER_BEGIN'):
            with self.assertRaises(ValueError):prior.bootstrap_prefix(x)

    def test_exact_source_contract_is_single_splice(self):
        source=['NbRestorePlan:','RpResolveRestore:','BhEligible:',*_routines(),
                'BhCodeEnd:','.org $C000']
        self.assertEqual(transform(source).count('BhBitmapSharedHit:'),1)
        self.assertEqual(transform(source).count('BhBitmapDifferent:'),1)

    def test_independent_native_trace_counts_and_timing(self):
        committed=[i%596 for i in range(1024)]
        pending=committed.copy()
        for k in range(135):pending[k]=0xFFFF
        pending[400]=pending[400]|0x4000
        expectedfast=sum(h<596 and h==p for h,p in zip(committed,pending))
        expectedslow=sum(h<596 and h!=p for h,p in zip(committed,pending))
        log=(f'NB_BITMAP_BEGIN|100|12|0|3|{dump(committed)}|{dump(pending)}|{dump([0]*768)}\n'
             'NB_BC_START|100|12|0|3\n'
             f'NB_BC_DONE|912|12|0|3|{expectedfast}|{expectedslow}|1024\n')
        with tempfile.TemporaryDirectory() as dir:
            native=Path(dir)/'native';native.mkdir();p=native/'mesen.log'
            p.write_text(log)
            rows=adapter.shared_evidence(Path(dir))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['bitmap_build_clocks'],812)
            self.assertEqual(rows[0]['shared_fast_cells'],expectedfast)
            self.assertEqual(rows[0]['different_home_cells'],expectedslow)
            for injected in ('NB_FAULT|900|12|0|INJECTED\n','callback_owner.lua:22: bad\n'):
                p.write_text(log+injected)
                with self.assertRaises(ValueError):adapter.shared_evidence(Path(dir))
            p.write_text(log.replace(f'|{expectedfast}|{expectedslow}|1024',f'|{expectedfast-1}|{expectedslow}|1024'))
            with self.assertRaisesRegex(ValueError,'COUNTS'):adapter.shared_evidence(Path(dir))

    def test_does_not_invent_native_timings(self):
        with tempfile.TemporaryDirectory() as dir:
            native=Path(dir)/'native';native.mkdir();(native/'mesen.log').write_text('')
            self.assertEqual(adapter.shared_evidence(Path(dir)),[])
            (native/'mesen.log').write_text('NB_BC_START|100|12|0|3\n')
            with self.assertRaisesRegex(ValueError,'MISSING'):adapter.shared_evidence(Path(dir))

if __name__=='__main__':unittest.main()
