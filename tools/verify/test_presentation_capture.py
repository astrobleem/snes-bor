"""Offline capture tests: no emulator imports or session construction."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from capture_presentation_state import capture_presentation


class CaptureTests(unittest.TestCase):
    def test_read_only_capture_and_local_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'external.png'
            source.write_bytes(b'fixture-copy-bytes-not-a-runtime-screenshot')
            calls = []
            class Session:
                def get_state(self):
                    calls.append('state'); return {'frame': 7, 'paused': True}
                def get_ppu_state(self):
                    calls.append('ppu'); return {'bgMode': 1}
                def read_memory(self, memory, address, size):
                    calls.append((memory,address,size))
                    self_test.assertGreaterEqual(size, 32)
                    if memory == 'snesMemory':
                        self_test.assertGreaterEqual(address, 0x7E0000)
                    return [0]*size
                def take_screenshot(self):
                    calls.append('shot'); return {'path': str(source)}
            self_test = self
            result = capture_presentation(Session(), {'Nmi_ScreenMode':0x7E500F, 'StageFp_Ready':0x7FB78D,
                                            'Screen_PosY':0x7E1604, 'ROM_CONSTANT':0x108000}, root/'captures', '5A')
            report = json.loads(Path(result['path']).read_text())
            self.assertEqual(report['errors'], {})
            self.assertIn('StageFp_Ready', report['named_wram'])
            self.assertNotIn('ROM_CONSTANT', report['named_wram'])
            self.assertEqual(report['screenshot_copy']['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(report['visual_acceptance'], 'NOT_ASSERTED')
            self.assertEqual(calls.count('ppu'), 2)
            self.assertEqual(calls.count('state'), 2)
            with self.assertRaises(FileExistsError):
                capture_presentation(Session(), {}, root/'captures', '5A')

    def test_unavailable_ppu_is_explicit_not_fake_success(self):
        with tempfile.TemporaryDirectory() as directory:
            class Session:
                def get_state(self): return {'frame':1}
                def get_ppu_state(self): raise RuntimeError('unavailable')
                def take_screenshot(self): raise RuntimeError('unavailable')
            result = capture_presentation(Session(), {}, directory, 'missing', video_memory=False)
            self.assertIn('actual_ppu_before', result['errors'])
            self.assertIn('screenshot', result['errors'])


if __name__ == '__main__':
    unittest.main()
