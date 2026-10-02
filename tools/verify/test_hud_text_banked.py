"""Focused S7 text relocation equivalence/ABI checks; no emulator or build."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASELINE = 'c8cbd71'


def lines(text):
    return [line.split(';', 1)[0].strip() for line in text.splitlines()
            if line.split(';', 1)[0].strip()]


def body(text, label, terminal):
    return text[text.index(label + ':'):text.index(terminal, text.index(label + ':')) + len(terminal)]


class HudTextBankedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / 'src/main.pasm').read_text()
        cls.text = (ROOT / 'src/core/hud_text_banked.pasm').read_text()

    def test_s7_body_equivalent_except_explicit_long_call_abi(self):
        old = subprocess.check_output(['git', 'show', f'{BASELINE}:src/main.pasm'],
                                      cwd=ROOT).decode('utf-8')
        old_lines = lines(old)
        start = old_lines.index('Hud_Play__text:')
        end = old_lines.index('Hud_Play__text_done:', start) + 3
        current = lines(self.text)
        self.assertEqual(current.count('jsl Core_Text_DrawLabeledNumber_Long'), 3)
        self.assertEqual(current.count('rtl'), 2)
        normalized = [line.replace('Hud_Play__text_banked', 'Hud_Play__text')
                      .replace('jsl Core_Text_DrawLabeledNumber_Long',
                               'jsr Core_Text_DrawLabeledNumber')
                      for line in current]
        normalized = ['rts' if line == 'rtl' else line for line in normalized]
        self.assertEqual(normalized, old_lines[start:end])

    def test_trampolines_preserve_carry_and_balanced_return_abi(self):
        self.assertEqual(lines(body(self.main, 'Hud_Play__text', '    rts')),
                         ['Hud_Play__text:', 'jsl Hud_Play__text_banked', 'rts'])
        self.assertEqual(lines(body(self.main, 'Core_Text_DrawLabeledNumber_Long', '    rtl')),
                         ['Core_Text_DrawLabeledNumber_Long:',
                          'jsr Core_Text_DrawLabeledNumber', 'rtl'])
        self.assertEqual(lines(self.text)[-6:], ['Hud_Play__text_banked_marked:',
                         'sec', 'rtl', 'Hud_Play__text_banked_done:', 'clc', 'rtl'])
        play = lines(body(self.main, 'Hud_Play', '    rts'))
        self.assertEqual(play[play.index('jsr Hud_Play__text') + 1], 'jsl Hud_Play__2p')
        p2 = lines((ROOT / 'src/core/hud_2p.pasm').read_text())
        self.assertLess(p2.index('bcs Hud_Play__2p_bar_only'), p2.index('jsr Hud_Play__2p_text'))

    def test_linked_bank_and_emitted_trampoline_bytes(self):
        # Read the existing production assembly only; never regenerate it here.
        sym = {name: int(bank + address, 16) for bank, address, name in
               re.findall(r'^([\dA-Fa-f]{2}):([\dA-Fa-f]{4,6}) (\S+)$',
                          (ROOT / 'src/main.sym').read_text(), re.M)}
        rom = (ROOT / 'src/main.bin').read_bytes()
        for caller, target, opcode, ret in [
                ('Hud_Play__text', 'Hud_Play__text_banked', 0x22, 0x60),
                ('Core_Text_DrawLabeledNumber_Long', 'Core_Text_DrawLabeledNumber', 0x20, 0x6B)]:
            self.assertEqual(sym[caller] >> 16, 0)
            address = sym[caller]
            offset = (address >> 16) * 0x8000 + (address & 0x7fff)
            operand = sym[target].to_bytes(3, 'little')[:3 if opcode == 0x22 else 2]
            expected = bytes([opcode]) + operand + bytes([ret])
            self.assertEqual(rom[offset:offset + len(expected)], expected)
        self.assertEqual(sym['Hud_Play__text_banked'] >> 16, 5)
        self.assertEqual(sym['Core_Text_DrawLabeledNumber'] >> 16, 0)


if __name__ == '__main__':
    unittest.main()
