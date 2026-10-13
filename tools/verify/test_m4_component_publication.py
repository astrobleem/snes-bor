from pathlib import Path
import tempfile
import unittest

import numpy as np
from m4_component_production_sequence import validate_sequence_aliases,verify


class ComponentPublicationTests(unittest.TestCase):
    def test_later_map_cannot_enable_offsets_through_priority_or_flip(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder)
            for plane in ('high','low'):
                good=np.arange(1024,dtype='<u2')
                (root/f'00-{plane}.map').write_bytes(good.tobytes())
                for bit in (0x2000,0x4000):
                    bad=good.copy();bad[63]|=bit
                    (root/f'01-{plane}.map').write_bytes(bad.tobytes())
                    validate_sequence_aliases(root,1,plane)
                    with self.assertRaisesRegex(ValueError,'ENABLE_BITS:1'):
                        validate_sequence_aliases(root,2,plane)

    def test_retained_rom_mismatch_rejects_before_media_or_emulator_mutation(self):
        with tempfile.TemporaryDirectory()as folder:
            rom=Path(folder)/'retained.sfc';rom.write_bytes(b'original')
            with self.assertRaisesRegex(ValueError,'RETAINED_ROM_IDENTITY'):
                verify(b'changed',{}, {}, [], [],rom,{},Path(folder),existing_rom=rom)
            self.assertEqual(rom.read_bytes(),b'original')
            self.assertFalse((Path(folder)/'proof.sfc').exists())


if __name__=='__main__':unittest.main()
