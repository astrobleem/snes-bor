"""Offline tests of the native adapter's guard editing and trace certificates.
These do not execute Poppy, Mesen or the user's retained native fixtures.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/bor_compile'))
import m4_home_borrow_bitmap_native as native
from home_borrow_bitmap import membership_reference


class NativeAdapterOfflineTests(unittest.TestCase):
    def test_retained_nonblank_bootstrap_marker_is_required_once(self):
        marker='-- NONBLANK_OBSERVER_BEGIN'
        self.assertEqual(native.bootstrap_script('bootstrap\n'+marker+'\nold observer'), 'bootstrap\n')
        for broken in ('-- ONLINE_OBSERVER_BEGIN', marker+'\n'+marker):
            with self.assertRaises(ValueError):native.bootstrap_script(broken)
        retained=ROOT/'out/byor-motu-home-borrow-success-v5/native/callback_owner.lua'
        if retained.exists():
            self.assertNotIn(marker,native.bootstrap_script(retained.read_text()))

    def test_guard_authorization_is_narrow_and_keeps_sa1_guard(self):
        sy=dict(NbBegin=0x39A000,NbCodeEnd=0x39A618,
                BhBitmapLeaseBegin=0x39B600,BhBitmapBuilt=0x39B6A0)
        def line(cpu):
            return (f"if '{cpu}'~='snes' or pc<{sy['NbBegin']} or pc>={sy['NbCodeEnd']} "
                    f"then nbLog('FAULT','QUEUE_OWNER:{cpu}|'..a)")
        original=line('snes')+'\n'+line('sa1')+'\n'
        altered=native.authorize_empty_queue_builder(original,sy)
        self.assertIn(line('sa1'),altered)
        for literal in ('bbLive','(a&0x7ff)>=0x500','(a&0x7ff)<0x598',
                        'nbWord(0x42d600)==1','nbWord(0x42d660)==0',
                        'nbWord(0x42d608)==0','nbWord(0x42d60a)==0','nbWord(0x42d70c)==0'):
            self.assertIn(literal,altered)
        self.assertIn("nbLog('FAULT','QUEUE_OWNER:snes|'..a)",altered)
        with self.assertRaises(ValueError):native.authorize_empty_queue_builder(altered,sy)
        with self.assertRaises(ValueError):native.authorize_empty_queue_builder(original+original,sy)

    def test_native_evidence_rejects_wrong_bits_changed_maps_and_unreleased_lease(self):
        cm=[0]*1024;pm=[0xFFFF]*1024
        def hexwords(words):return b''.join(w.to_bytes(2,'little') for w in words).hex()
        chex,phex,rhex=hexwords(cm),hexwords(pm),hexwords([0]*768)
        bits=b''.join(membership_reference(cm,pm)).hex()
        def line(kind,time,*data):return 'NB_'+kind+'|'+str(time)+'|0|0|'+'|'.join(map(str,data))+'\n'
        begin=line('BITMAP_BEGIN',100,3,chex,phex,rhex)
        built=line('BITMAP_BUILT',200,3,1024,bits)
        end=line('BITMAP_END',300,3,41,chex,phex,rhex)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'native').mkdir();log=root/'native/mesen.log'
            log.write_text(begin+built+end)
            result=native.bitmap_evidence(root)
            self.assertEqual(result['plans'][0]['build_clocks'],100)
            self.assertEqual(result['plans'][0]['lookup_calls'],41)
            for broken in (begin+built,begin+line('BITMAP_BUILT',200,3,1024,'00'*152)+end,
                           begin+built+line('BITMAP_END',300,3,41,phex,phex,rhex),
                           begin+line('BITMAP_BUILT',200,3,1023,bits)+end):
                log.write_text(broken)
                with self.assertRaises(ValueError):native.bitmap_evidence(root)

    def test_native_faults_and_lua_errors_are_never_filtered(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'native').mkdir();log=root/'native/mesen.log'
            for text in ('NB_FAULT|100|0|0|QUEUE_OWNER:snes|123\n',
                         'callback_owner.lua:42: runtime error\n'):
                log.write_text(text)
                with self.assertRaises(ValueError):native.bitmap_evidence(root)

    def test_native_observer_emission_does_not_change_legacy_script_elsewhere(self):
        sy=dict(NbBegin=0x39A000,NbCodeEnd=0x39A618,
            BhBitmapLeaseBegin=0x39B600,BhBitmapBuilt=0x39B6A0,
            BhBitmapMapLoop=0x39B620,BhEligible=0x39B450,
            BhPrepareOK=0x39B440,BhPrepareBad=0x39B430,
            NbPreloadPair=0x39A400,NbAbort=0x39A380,SpReadyBoundary=0x39B000)
        script=(f"if 'snes'~='snes' or pc<{sy['NbBegin']} or pc>={sy['NbCodeEnd']} then nbLog('FAULT','QUEUE_OWNER:snes|'..a) end\n"
                f"if 'sa1'~='snes' or pc<{sy['NbBegin']} or pc>={sy['NbCodeEnd']} then nbLog('FAULT','QUEUE_OWNER:sa1|'..a) end\n")
        fake=SimpleNamespace(observe=lambda path,contract:path.write_text(script))
        with tempfile.TemporaryDirectory() as d,patch.object(native,'_saved',fake):
            path=Path(d)/'callback_owner.lua'
            native.observer(path,{'native_symbols':sy})
            text=path.read_text()
            self.assertIn(script.splitlines()[1],text)
            self.assertIn('BITMAP_FROZEN_MAP_OR_REF_WRITE',text)
            self.assertIn('BITMAP_REPEATED_MAP_READ',text)
            self.assertIn('BITMAP_LEASE_NOT_RELEASED',text)
            self.assertEqual(text.count('local bbLive='),1)

if __name__=='__main__':unittest.main()
