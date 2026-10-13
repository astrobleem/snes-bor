import subprocess
import unittest
import numpy as np

from m4_cgram_dma_windows import compile_rom, expected_frame, palette_color, fixed_color_for_row


class FixedColorComponentTests(unittest.TestCase):
    def test_legacy_rom_and_expected_pixels_remain_identical(self):
        previous = subprocess.check_output(['git', 'show', '0ed0d89:tools/verify/m4_cgram_dma_windows.py']).decode()
        namespace = {'__name__': 'retained_component'}
        exec(previous, namespace)
        self.assertEqual(compile_rom(81), namespace['compile_rom'](81))
        np.testing.assert_array_equal(expected_frame(), namespace['expected_frame']())

    def test_fixed_color_boot_and_four_shared_math_modes(self):
        color = 3 | (7 << 5) | (11 << 10)
        rom = compile_rom(81, fixed_color=color)
        self.assertIn(bytes.fromhex('a9 10 8d 30 21 a9 23 8d 32 21 a9 47 8d 32 21 a9 8b 8d 32 21'), rom[0x8000:0x8600])
        self.assertEqual([rom[0x1a400+y] for y in (80, 84, 88, 92)], [0x10, 0x50, 0x90, 0xd0])
        frame = expected_frame(fixed_color=color)
        for y in (80, 84, 88, 92):
            c = palette_color(y)
            values = []
            for shift, fixed in zip((0, 5, 10), (3, 7, 11)):
                channel = c >> shift & 31
                value = max(0, channel-fixed) if y % 16 >= 8 else channel+fixed
                values.append(value//2 if y % 8 >= 4 else value)
            self.assertEqual(frame[y, 128], sum(min(31, v) << s for s, v in zip((0, 5, 10), values)))
            self.assertEqual(frame[y, 96], c)  # ordinary OBJ bypasses math
            self.assertEqual(frame[y, 0], 0)  # main backdrop stays black; green BG is on the subscreen
        for color in (-1, 32768, True):
            with self.assertRaisesRegex(ValueError, 'FIXED_COLOR_DOMAIN'):
                compile_rom(81, fixed_color=color)

    def test_dynamic_fixed_color_table_cursor_and_channel_ownership(self):
        color = 3 | (7 << 5) | (11 << 10)
        rom = compile_rom(71, fixed_color=color, dynamic_fixed_color=True)
        for y in range(224):
            data = rom[0x1a700+3*y:0x1a703+3*y]
            word = sum((v & 31) << s for s, v in zip((0, 5, 10), data))
            self.assertEqual(word, fixed_color_for_row(color, y, True))
            self.assertEqual([v & 0xe0 for v in data], [0x20, 0x40, 0x80])
        self.assertIn(bytes.fromhex('a9 00 a7 8f 42 43 00'), rom[0x8800:0x8900])
        self.assertIn(bytes.fromhex('a9 de 8f 0b 42 00'), rom[0x8600:0x8800])
        for options in (dict(fixed_color=None), dict(fixed_color=color, general_windows=True),
                        dict(fixed_color=color, three_ranges=True)):
            with self.assertRaisesRegex(ValueError, 'CHANNEL_OWNERSHIP'):
                compile_rom(71, dynamic_fixed_color=True, **options)


if __name__ == '__main__':
    unittest.main()
