import struct
import unittest
from source_entity_abi import PROPERTIES, record, view, get_property


class EntityViewTests(unittest.TestCase):
    def item(self, token=0x6abcde):
        return record(token, {name: (-65536 if kind == 2 else 7) for name, kind in PROPERTIES})

    def test_types_aliases_and_stale_handle(self):
        item = self.item()
        self.assertEqual(struct.unpack('<BBHI', get_property([item], 0x6abcde, 'X')), (2, 0, 0, 0xffff0000))
        self.assertEqual(get_property([item], 0x6abcde, 'animationID'), get_property([item], 0x6abcde, 'animnum'))
        self.assertEqual(get_property([item], None, 'unknown'), bytes(8))
        dead = record(0x6abcde, {name: 0 for name, _ in PROPERTIES}, alive=False)
        with self.assertRaisesRegex(ValueError, 'STALE'): get_property([dead], 0x6abcde, 'x')
        with self.assertRaisesRegex(ValueError, 'STALE'): get_property([item], 99, 'x')

    def test_view_rejects_spill_duplicate_tokens_and_malformed_variant(self):
        item = self.item()
        descriptor, payload = view(0x7fb900, [item])
        self.assertEqual(len(descriptor), 8)
        self.assertEqual(payload, item)
        with self.assertRaisesRegex(ValueError, 'BANK_SPILL'): view(0x7fffc0, [item])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'): view(0x7fb900, [item, item])
        malformed = bytearray(item); malformed[8] = 1
        with self.assertRaisesRegex(ValueError, 'VARIANT_INVALID'): view(0x7fb900, [bytes(malformed)])


if __name__ == '__main__': unittest.main()
