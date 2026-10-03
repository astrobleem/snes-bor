"""Scene cold-init source guards and harness predicate tests; NOT native proof.

Prefill checks model the source-guarded byte stores, not a 65816 execution.
No ROM build, emulator session, or production artifact writes.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


def code(path):
    return '\n'.join(line.split(';', 1)[0].strip()
                     for line in (ROOT / path).read_text().splitlines())


class SceneInitTests(unittest.TestCase):
    def test_byte_clear_and_prefilled_guard_model(self):
        body = code('src/core/scene_video.pasm').split('SceneVideo_Init:', 1)[1].split('SceneVideo_Request:', 1)[0]
        instructions = [line for line in body.splitlines() if line and not line.startswith('.')]
        self.assertEqual(instructions, [
            'php', 'rep #$30', 'pha', 'phx', 'sep #$20', 'lda #0', 'ldx #0',
            'SceneVideo_Init__clear:', 'sta.l SceneVideo_TestRequest,x', 'inx',
            'cpx #(SceneVideo_MsuDmaProbe-SceneVideo_TestRequest+1)',
            'bcc SceneVideo_Init__clear', 'sta.l SceneVideo_PlayState',
            'sta.l SceneVideo_SequenceActive', 'sta.l SceneVideo_SkipPending',
            'rep #$30', 'plx', 'pla', 'plp', 'rtl'])
        declarations = code('src/main.pasm')
        def address(name):
            return int(re.search(rf'^{name}\s*=\s*\$([0-9A-Fa-f]+)', declarations, re.M)[1], 16)
        first, last = map(address, ('SceneVideo_TestRequest', 'SceneVideo_MsuDmaProbe'))
        self.assertEqual((first, last), (0x7E9A60, 0x7E9A9A))
        extra = {address('SceneVideo_' + n) for n in ('PlayState', 'SequenceActive', 'SkipPending')}
        targets = set(range(first, last + 1)) | extra
        for poison in (29, 0xA5, 0xFF):
            ram = bytearray([poison]) * 0x20000
            for target in targets:
                ram[target - 0x7E0000] = 0
            self.assertTrue(all(ram[a - 0x7E0000] == 0 for a in targets))
            changed = {i + 0x7E0000 for i, value in enumerate(ram) if value != poison}
            self.assertEqual(changed, targets)

    def test_cold_hook_and_public_request(self):
        water = code('src/core/stage_water.pasm')
        self.assertRegex(water, r'StageWater_ColdInit:\s+jsl Tad_StreamInit\s+jsl SceneVideo_Init\s+jml StageWater_Init')
        self.assertIn('jsl StageFp_BG2ColdInit', code('src/main.pasm'))
        foreground = code('src/core/stage_frontpanel_bg2.pasm')
        self.assertRegex(foreground, r'StageFp_BG2ColdInit:\s+jsl StageWater_ColdInit\s+jsl StageFp_Init\s+jml StageFp_BG2Init')
        scene = code('src/core/scene_video.pasm')
        request = scene.split('SceneVideo_Request:', 1)[1].split('SceneVideo_ResolveSequence:', 1)[0]
        self.assertRegex(request, r'lda #0\s+sta\.l SceneVideo_MsuDmaProbe')
        self.assertLess(request.index('sta.l SceneVideo_MsuDmaProbe'), request.index('sta.l SceneVideo_TestRequest'))
        # Raw diagnostic seam remains available; public request resets it.
        self.assertRegex(scene, r'lda\.l SceneVideo_MsuDmaProbe\s+bne SceneVideo_FrameTestHandler__scheduler')


class SceneInputWordTests(unittest.TestCase):
    def setUp(self):
        scene = code('src/core/scene_video.pasm')
        self.body = scene.split('SceneVideo_LatchInputEdge:', 1)[1].split('SceneVideo_LoadFrame__aborted:', 1)[0]
        symbols = (ROOT / 'src/main.sym').read_text()
        self.addresses = {
            name: int(re.search(rf'^\w+:([0-9A-Fa-f]+) {name}$', symbols, re.M)[1], 16)
            for name in ('Input_trigger', 'Input_old', 'Input2_trigger', 'Input2_old')}

    def test_full_word_consumers_and_telemetry(self):
        self.assertRegex(self.body, r'^\s*rep #\$31\s+\.a16\s+\.i16')
        self.assertRegex(self.body, r'lda\.l Input_trigger\s+ora\.l Input2_trigger\s+beq SceneVideo_LatchInputEdge__none')
        self.assertNotRegex(self.body, r'(?:lda|ora)\.l Input2?_trigger\s*\+')
        for prefix, target in [('Input', 'SceneVideo_InputTriggerAtSkip'),
                               ('Input2', 'SceneVideo_Input2TriggerAtSkip')]:
            self.assertRegex(self.body, rf'lda\.l {prefix}_trigger\s+sta\.l {target}')
            self.assertEqual(self.addresses[prefix + '_old'], self.addresses[prefix + '_trigger'] + 2)

    def test_neighbor_poison_never_creates_edge_model(self):
        # Evaluate the guarded full-word loads, not an emulator/native claim.
        for player in ('Input', 'Input2'):
            trigger = self.addresses[player + '_trigger'] - 0x7E0000
            old = self.addresses[player + '_old'] - 0x7E0000
            for poison in range(256):
                ram = bytearray(0x420)
                ram[old] = poison
                def word(offset):
                    return int.from_bytes(ram[offset:offset + 2], 'little')
                actual = word(self.addresses['Input_trigger'] - 0x7E0000) | word(self.addresses['Input2_trigger'] - 0x7E0000)
                self.assertEqual(actual, 0, (player, poison))
                if poison == 0x80:
                    self.assertEqual(word(trigger + 1), 0x8000,
                                     'old overlapping-word implementation reproduces held-A false edge')
                # Real edges in either byte of either player's word survive.
                for edge in (0x0080, 0x8000, 0x0010, 0x1000):
                    ram[trigger:trigger + 2] = edge.to_bytes(2, 'little')
                    self.assertEqual(word(trigger), edge)
                    ram[trigger:trigger + 2] = b'\0\0'


if __name__ == '__main__':
    unittest.main()
