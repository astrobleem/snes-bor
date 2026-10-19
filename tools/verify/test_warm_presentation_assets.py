"""Offline guard tests for ROM scatter, palette append, and WRAM lease bounds."""
import struct
import unittest

import numpy as np

from source_warm_frame_assets import encode_image, decode_image
from source_warm_presentation_assets import (
    META_BANK, CODE_BANK, RENDER_BANK, LEASE_BEGIN, LEASE_END,
    layout, palette_extension, scatter_images,
)


ROM_BYTES = 4 * 1024 * 1024
ROM_BANK_BYTES = 32768


def image_blob(width=4, height=3):
    rows = np.fromfunction(lambda y, x: (x + y) % 3 + 1,
                           (height, width), dtype=int).astype(np.uint8)
    return encode_image(rows)


class ScatterTests(unittest.TestCase):
    def test_uses_only_empty_unreserved_slots_and_preserves_other_rom_bytes(self):
        baseline = bytearray(ROM_BYTES)
        baseline[17] = 0x5A
        baseline[ROM_BANK_BYTES + 7] = 0xA5
        blobs = [image_blob(), image_blob(7, 2)]

        addresses, writes = scatter_images(bytes(baseline), blobs)

        self.assertEqual(len(addresses), len(blobs))
        self.assertEqual(len(writes), len(blobs))
        candidate = bytearray(baseline)
        written = set()
        for write in writes:
            offset, data = write['offset'], write['data']
            self.assertTrue(offset >= 2 * ROM_BANK_BYTES)
            self.assertTrue(offset // ROM_BANK_BYTES not in
                            (META_BANK, CODE_BANK, RENDER_BANK))
            self.assertFalse(any(baseline[offset:offset + len(data)]))
            self.assertEqual(addresses[write['image']], 0xC00000 + offset)
            self.assertEqual(decode_image(data).shape,
                             decode_image(blobs[write['image']]).shape)
            self.assertEqual(candidate[offset:offset + len(data)],
                             baseline[offset:offset + len(data)])
            candidate[offset:offset + len(data)] = data
            written.update(range(offset, offset + len(data)))
        changed = {i for i, (a, b) in enumerate(zip(baseline, candidate)) if a != b}
        self.assertTrue(changed <= written)
        self.assertEqual(candidate[17], 0x5A)
        self.assertEqual(candidate[ROM_BANK_BYTES + 7], 0xA5)

    def test_skips_reserved_empty_slots_and_nonempty_slots(self):
        baseline = bytearray([1]) * ROM_BYTES
        for bank in (META_BANK, CODE_BANK, RENDER_BANK, 47):
            baseline[bank * ROM_BANK_BYTES:(bank + 1) * ROM_BANK_BYTES] = bytes(ROM_BANK_BYTES)

        addresses, writes = scatter_images(bytes(baseline), [image_blob()])
        offset = addresses[0] - 0xC00000
        self.assertEqual(offset // ROM_BANK_BYTES, 47)
        self.assertEqual(writes[0]['offset'], offset)

    def test_images_do_not_cross_32k_slots_even_when_near_slot_capacity(self):
        alternating = np.tile(np.array([0, 1], dtype=np.uint8), (80, 100))
        blob = encode_image(alternating)
        self.assertLess(len(blob), ROM_BANK_BYTES)
        self.assertGreater(len(blob), ROM_BANK_BYTES // 2)

        addresses, writes = scatter_images(bytes(ROM_BYTES), [blob, blob])
        self.assertEqual(len(set(a // ROM_BANK_BYTES for a in addresses)), 2)
        for address, write in zip(addresses, writes):
            start = address - 0xC00000
            self.assertEqual(start // ROM_BANK_BYTES,
                             (start + len(write['data']) - 1) // ROM_BANK_BYTES)
            self.assertTrue(np.array_equal(decode_image(write['data']), alternating))

    def test_invalid_blob_and_capacity_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'WARM_IMAGE_TRUNCATED_HEADER'):
            scatter_images(bytes(ROM_BYTES), [b'bad'])
        with self.assertRaisesRegex(ValueError, 'WARM_SCATTER_CAPACITY'):
            scatter_images(bytes(ROM_BYTES), [image_blob()], reserved_banks=range(128))

    def test_rom_extent_and_individual_image_limit(self):
        with self.assertRaisesRegex(ValueError, 'WARM_ROM_EXTENT'):
            scatter_images(bytes(ROM_BYTES - 1), [image_blob()])
        with self.assertRaisesRegex(ValueError, 'WARM_SCATTER_IMAGE_EXTENT'):
            scatter_images(bytes(ROM_BYTES), [bytes(ROM_BANK_BYTES)])


class PaletteTests(unittest.TestCase):
    def test_append_preserves_old_slots_and_reconstructs_all_rgb555_bits(self):
        bases = [0x0000, 0x001F, 0x7BDF, 0x1234]
        bases = [c & ~0x420 for c in bases]
        old = [None] * 236
        for slot, color in enumerate(bases):
            old[slot] = color
        source = [0] * 256
        used = []
        for base in bases:
            for low_bits in (0, 0x20, 0x400, 0x420):
                index = len(used) + 1
                source[index] = base | low_bits
                used.append(index)

        colors, lut_bytes, changes = palette_extension(old, source, used)

        self.assertEqual(len(lut_bytes), 512)
        self.assertEqual(len(colors), 236)
        self.assertEqual(colors[:len(bases)], old[:len(bases)])
        self.assertTrue(all(colors[i] == old[i] for i in range(236) if old[i] is not None))
        self.assertEqual([row['slot'] for row in changes],
                         list(range(len(bases), len(bases) + len(changes))))
        lut = struct.unpack('<256H', lut_bytes)
        for index in used:
            draw = lut[index]
            slot = (draw & 0xFF) - 4
            reconstructed = (colors[slot] + ((draw >> 8) & 1) * 0x20 +
                             ((draw >> 9) & 1) * 0x400)
            self.assertEqual(reconstructed, source[index])

    def test_palette_domains_and_capacity_reject(self):
        with self.assertRaisesRegex(ValueError, 'WARM_PALETTE_EXTENT'):
            palette_extension([], [0] * 256, set())
        with self.assertRaisesRegex(ValueError, 'WARM_SOURCE_INDEX'):
            palette_extension([None] * 236, [0] * 256, {0})
        with self.assertRaisesRegex(ValueError, 'WARM_SOURCE_INDEX'):
            palette_extension([None] * 236, [0] * 256, {256})
        full = list(range(236))
        source = [0] * 256
        source[1] = 0x7FFF
        with self.assertRaisesRegex(ValueError, 'WARM_PALETTE_CAPACITY'):
            palette_extension(full, source, {1})


class MemoryLeaseTests(unittest.TestCase):
    def test_retired_video_workspace_is_bounded_nonoverlapping_and_not_production_lease(self):
        plan = layout()
        self.assertEqual((plan['begin'], plan['end']), (LEASE_BEGIN, LEASE_END))
        self.assertEqual(plan['begin'], 0x7E8340)
        self.assertEqual(plan['end'], 0x7E9A60)
        ranges = sorted((r['begin'], r['end'], r['name']) for r in plan['ranges'])
        self.assertTrue(all(plan['begin'] <= a < b <= plan['end'] for a, b, _ in ranges))
        self.assertTrue(all(b0 <= a1 for (_, b0, _), (a1, _, _) in zip(ranges, ranges[1:])))
        self.assertEqual(next(r for r in plan['ranges'] if r['name'] == 'row_cache')['end'],
                         0x7E9400)
        self.assertFalse(plan['production_lease'])
        # Explicitly verify disjointness from live audio, source actor RAM, and
        # the foreign-state arena rather than treating them as unowned gaps.
        candidates = [(a, b) for a, b, _ in ranges]
        protected = [(0x7E8100, 0x7E8340), (0x7E0A00, 0x7E1600),
                     (0x7FA000, 0x7FB900)]
        for a, b in candidates:
            for c, d in protected:
                self.assertTrue(b <= c or a >= d)


if __name__ == '__main__':
    unittest.main()
