import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from m4_live_ground_component_native import check_motion


class MotionIdentityTests(unittest.TestCase):
    def samples(self,root,dx=32768,token=0x414000,controller=0x100):
        result=[]
        for epoch in (0,1):
            raw=bytearray(146)
            struct.pack_into('<I',raw,0,0x414000 if epoch==0 else token)
            struct.pack_into('<i',raw,52,80*65536+dx*epoch)
            struct.pack_into('<i',raw,60,220*65536)
            struct.pack_into('<3i',raw,112,65536,65536,0)
            struct.pack_into('<H',raw,144,epoch)
            path=root/f'{epoch}.bin';path.write_bytes(raw)
            result.append(dict(snapshot=str(path),sha256=hashlib.sha256(raw).hexdigest(),
                               label='birth' if epoch==0 else 'right',raw_controller=controller))
        return result

    def test_exact_controller_delta_keeps_source_token(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(check_motion(self.samples(Path(d)))[0]['exact'])

    def test_motion_cannot_pass_from_a_different_actor_or_pad(self):
        with tempfile.TemporaryDirectory() as d:
            for kwargs in (dict(token=0x414050),dict(controller=0),dict(dx=65536)):
                with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                    check_motion(self.samples(Path(d),**kwargs))

    def test_changed_snapshot_cannot_reuse_receipt_hash(self):
        with tempfile.TemporaryDirectory() as d:
            samples=self.samples(Path(d));Path(samples[1]['snapshot']).write_bytes(bytes(146))
            with self.assertRaisesRegex(ValueError,'IDENTITY'):check_motion(samples)


if __name__=='__main__':unittest.main()
