import contextlib
import io
import unittest
from audit_all import run_one_seed_set


class BankScopeTests(unittest.TestCase):
    def test_other_bank_payload_cannot_manufacture_bank_zero_violation(self):
        data=bytearray(0x10010)
        data[:5]=bytes.fromhex('22 00 80 01 60') # bank-0 JSL $018000; RTS
        # Flat indexing of $018000 incorrectly lands here, rather than at
        # LoROM offset $8000. Such a walk invents a bank-0 JSL to $0046F1.
        data[0x10000:0x10005]=bytes.fromhex('22 f1 46 00 60')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            ok,decoded=run_one_seed_set('scope',[0x8000],data,[(0x8000,['entry'])],
                [0x8000],{0x8000:['entry']})
        self.assertTrue(ok)
        self.assertEqual(decoded,{0x8000,0x8004})
        self.assertIn('1 cross-bank JSL/JML edges skipped',output.getvalue())

    def test_real_bank_zero_bad_call_still_fails(self):
        data=bytes.fromhex('20 03 80 60')
        with contextlib.redirect_stdout(io.StringIO()):
            ok,decoded=run_one_seed_set('bad',[0x8000],data,[(0x8000,['entry'])],
                [0x8000],{0x8000:['entry']})
        self.assertFalse(ok) # target is an instruction, but not an owned label


if __name__=='__main__':unittest.main()
