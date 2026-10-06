import struct
import unittest
import numpy as np
from source_screen_palette import derive,projection_tables


class ScreenPalette(unittest.TestCase):
    def test_all_channel_pairs_retain_full_rgb555(self):
        tables=np.frombuffer(projection_tables(),dtype=np.uint8).reshape(4,65536).astype(np.uint16)
        actual=tables[0]|tables[1]|((tables[2]|tables[3])<<8)
        i=np.arange(65536,dtype=np.uint32)
        channel=(255-((255-(i&255))*(255-(i>>8))//255))>>3
        self.assertTrue(np.array_equal(actual,channel|(channel<<5)|(channel<<10)))
        self.assertFalse(np.any(actual&0x8000))

    def test_bindings_keep_constants_and_native_cache_identity(self):
        # SCREEN(0, destination) preserves destination, including low G/B bits.
        record=struct.pack('<3H',0x8000,0xc000,0xe000)+bytes(10)
        full=(128>>3)|((192>>3)<<5)|((224>>3)<<10)
        high=full&0xfbdf
        initial=[high,0x1234]+[None]*234
        report=dict(low_component_palette=[0,32,1024,1056],span=2,
                    trace=[dict(scanline=0,updates=[]),dict(scanline=1,updates=[dict(slot=2,color=high)])],
                    contiguous_bursts=[dict(start_slot=1),dict(start_slot=1)])
        pairs,bindings,cache,metadata=derive(record*3,report,initial)
        self.assertEqual(pairs,record[:6])
        self.assertEqual(cache,struct.pack('<H',full))
        actual=[]
        for value,native in struct.iter_unpack('<HH',bindings):
            actual.append((struct.unpack_from('<H',cache,value)[0]&0xfbdf) if native else value)
        self.assertEqual(actual[:6],[0,32,1024,1056,high,0x1234])
        self.assertEqual(actual[256:],[high,0x1234,high,high])
        self.assertEqual(metadata['unique_rgb8_pairs'],1)
        self.assertEqual(metadata['source_pixels'],3)
        with self.assertRaisesRegex(ValueError,'RECORD_ALIGNMENT'):derive(record[:-1],report,initial)
        with self.assertRaisesRegex(ValueError,'ROW_COUNT'):derive(record,{**report,'trace':[]},initial)
        with self.assertRaisesRegex(ValueError,'BURST_RANGE'):
            derive(record,{**report,'span':237},initial)


if __name__=='__main__':unittest.main()
