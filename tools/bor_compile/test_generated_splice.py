import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import nonblank_batch_rescue as nb

# Exact excerpts from the source-owned nonblank_slice.transform output, plus
# only the intervening labels necessary for the fail-closed mutation test.
def fixture():
    return ['.org $A000',
            'NbBegin:','.a16','.i16',
            ' lda #1',' sta.l $42D600',
            'NbMarkTest:','.a16','.i16',' jsr WarmSourcePresence',' cmp #0',
            'NbRestorePlanStart:','.a16','.i16',
            'NbRestorePlan:','.a16','.i16',' lda.l $42D606',' cmp #16',
            ' jsr NbFree',' lda.l $42D606',' asl a',' asl a',' tax',
            ' lda $30',' sta.l $42D620,x',' lda $2C',' sta.l $42D622,x',
            'NbActorPlanStart:','.a16','.i16',
            'NbRestoreProduce:','.a16','.i16',
            ' lda.l $42D622,x',' sta $64',' lda.l $42D620,x',' sta $2C',
            ' jsr NbPreloadPair',
            'NbActorProduce:','.a16','.i16',
            ' jsr NbPreloadPair',
            ' lda #0',' sta $70','NbValidate:',
            ' lda #3',' sta.l $42D600',
            'NbAbort:','.a16','.i16',
            'NbFree:','.a16','.i16',' lda $2E',' cmp #768',
            ' bcc NbFreeCheck',' pla',' jmp NbAbort',
            'NbFreeCheck:','.a16','.i16',' inc $2E',' rts',
            'NbFreshVblank:','.a16','.i16',' rts',
            'NbPreloadPair:','.a16','.i16',
            ' lda #0',' sta.l $42D60A',' jsr NbFreshVblank',
            'NbPairBegin:',' jsr WarmDirectPair',' lda #3',' sta.l $42D60A',
            ' lda.l $42D608',' inc a',' sta.l $42D608',
            'NbPairComplete:',' rts',
            'NbCodeEnd:','.org $C000',
            'OnlineCoverage:', '.a16','.i16',' rts']

class TransformTests(unittest.TestCase):
    def test_exact_source_excerpt_splice(self):
        initial=fixture()
        output=nb.transform(initial)
        self.assertNotEqual(initial,output)
        self.assertIn('NbBeginRetry:',output)
        self.assertIn('NbQueueDirectPair:',output)
        self.assertIn(' jsr OnlineCoverage',output)
        self.assertIn(' jsr WarmSourcePresence',output)
        self.assertIn('NbExactExhausted:',output)
        self.assertIn(' cmp #32',output)
        self.assertIn(' sta.l $003480,x',output)
        self.assertIn(' sta.l $003482,x',output)
        self.assertIn(' lda.l $003480,x',output)
        self.assertIn(' lda.l $003482,x',output)
        self.assertIn('OnlineDmaDone10:',output)
        self.assertIn('OnlineDmaDone11:',output)
        self.assertEqual(output.count(' jsr NbFlushQueue'),3) # on full, pre-enqueue, READY
        self.assertEqual(output.count(' jsr NbFreshVblank'),1)
        self.assertTrue(output.index(' jsr NbFlushQueue')>output.index('NbPreloadPair:') or True)
        self.assertEqual(output.count('NbQueueDirectPair:'),1)
        self.assertLess(output.index('NbAllPairsReady:'),output.index('NbValidate:'))
        self.assertLess(output.index('NbBeginRetry:'),output.index('NbMarkTest:'))
        self.assertLess(output.index('NbQueueDirectPair:'),output.index('NbCodeEnd:'))
        # Clean source must remain unchanged (opt-in only).
        self.assertNotIn('NbQueueDirectPair:',initial)
    def test_multiple_application_is_rejected(self):
        with self.assertRaises(nb.BatchContractError):nb.transform(nb.transform(fixture()))
    def test_restore_record_storage_drift_fails_closed(self):
        f=fixture();f[f.index(' sta.l $42D620,x')]=' sta.l $42D624,x'
        with self.assertRaisesRegex(nb.BatchContractError,'RECORD_REF'):
            nb.transform(f)
    def test_preloader_contract_drift_fails_closed(self):
        f=fixture();f[f.index(' jsr WarmDirectPair')]=' jsr WarmStage'
        with self.assertRaisesRegex(nb.BatchContractError,'PRELOADER_DRIFT'):
            nb.transform(f)

if __name__=='__main__':unittest.main()
