"""Offline tests. Native assembly/PPU/master-clock verification is required."""
import random
import unittest
from direct_pair_dma import (DirectDMAContractError, emit_direct_pair_asm,
                             packet, transform)


def fixture():
    return ['OnlineBlank:', 'WarmRestore:', ' jsr WarmStage',
            'OnlineTransfer:', ' jsr WarmStage', 'OnlineComplete:',
            '.org $D000', 'WarmStage:', 'WarmFlush:', 'OnlineDmaDone5:',
            'OnlineDmaDone6:', 'OnlineDmaDone7:',
            '.org $E000', '.org $E200', '.org $F000']


class DirectPairTests(unittest.TestCase):
    def test_fail_closed_transform(self):
        src = fixture()
        result = transform(src)
        self.assertEqual(src, fixture())
        self.assertEqual(result.count(' jsr WarmDirectPair'), 2)
        self.assertEqual(result.count(' jsr WarmStage'), 0)
        self.assertLess(result.index('WarmDirectPair:'), result.index('.org $E000'))
        self.assertIn('OnlineDmaDone8:', result)
        self.assertIn('OnlineDmaDone9:', result)
        for bad in ('WarmStage:', 'OnlineBlank:', 'OnlineDmaDone5:', '.org $E200'):
            with self.subTest(bad=bad):
                broken=fixture();broken.remove(bad)
                with self.assertRaises(DirectDMAContractError):transform(broken)
        with self.assertRaises(DirectDMAContractError):transform(result)
        other=fixture();other.append(' jsr WarmStage')
        with self.assertRaises(DirectDMAContractError):transform(other)

    def test_emission_preserves_published_lease_abi(self):
        asm = emit_direct_pair_asm()
        self.assertEqual(asm[:4], ['.org $D400','WarmDirectPair:','.a16','.i16'])
        self.assertEqual(asm.count(' sta.l $002116'), 2)
        self.assertEqual(asm.count(' sta.l $004375'), 2)
        self.assertEqual(asm.count(' sta.l $00420B'), 2)
        self.assertEqual(asm.count(' sta.l $004370'), 2)
        self.assertEqual(asm.count(' sta.l $004371'), 2)
        self.assertEqual(asm.count(' sta.l $004372'), 2)
        self.assertEqual(asm.count(' sta.l $004373'), 2)
        self.assertEqual(asm.count(' sta.l $004374'), 2)
        self.assertEqual(asm.count(' asl a'), 8)
        self.assertTrue(asm[-4:]==[' rep #$20','.a16',' rts'] or asm[-3:]==[' rep #$20','.a16',' rts'])
        self.assertFalse(any('mvn' in s.lower() for s in asm))
        self.assertFalse(any('$004200' in s or '$002100' in s for s in asm))

    def test_exact_original_staged_payload_semantics(self):
        # StageCopy(scratch) -> DMA and DirectDMA(scratch) must deliver the
        # same HIGH/LOW bytes to every leased physical slot, even after reuse.
        r=random.Random(0xB0A)
        old=bytearray(65536);new=bytearray(65536)
        for i in range(2000):
            slot = r.randrange(768)
            hi=r.randbytes(64);lo=r.randbytes(16)
            stage_hi=bytes(hi);stage_lo=bytes(lo)
            for address,data in packet(slot,stage_hi,stage_lo):
                old[address:address+len(data)]=data
            for address,data in packet(slot,hi,lo):
                new[address:address+len(data)]=data
            self.assertEqual(new,old, f'packet={i}, slot={slot}')

    def test_boundary_slots_and_domains(self):
        self.assertEqual(packet(0,bytes(64),bytes(16))[0][0],0)
        self.assertEqual(packet(767,bytes(64),bytes(16))[0][0],49088)
        self.assertEqual(packet(767,bytes(64),bytes(16))[1][0],61424)
        for slot in (-1,768,999):
            with self.assertRaises(ValueError):packet(slot,bytes(64),bytes(16))
        with self.assertRaises(ValueError):packet(0,bytes(80),bytes(16))

    def test_noop_has_no_transfer_and_blank_lease_is_prerequisite(self):
        src=fixture();dest=transform(src)
        self.assertEqual(src.count(' jsr WarmDirectPair'),0)
        self.assertTrue(dest.index('OnlineBlank:') < dest.index(' jsr WarmDirectPair'))
        self.assertNotIn('OnlineNoop:',dest)  # fixture is limited; no opt-in noop mutation
        self.assertFalse(any(s.startswith(' jsr WarmDirectPair') for s in emit_direct_pair_asm()))


if __name__=='__main__':unittest.main()
