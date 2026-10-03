import struct
import unittest
import game_s8_static_bg as bg


class StaticBgTests(unittest.TestCase):
    def test_packed_and_capture_regions(self):
        blob=bytearray(4096);blob[:8]=b'BORMSU1\0';blob[10]=1
        struct.pack_into('<I',blob,12,32)
        struct.pack_into('<BxHBB2xH2xIIIIIIH2x',blob,32,0,32,32,1,1,128,384,2432,2464,0,0,0)
        blob[2432:2464]=bytes(range(32))
        media=bg.packed_static(bytes(blob),0)
        vram=bytearray(65536);vram[:32]=media['tiles']
        vram[0xC000:0xC800]=media['tilemap'];vram[0xA000:0xA010]=media['hud']
        s=dict(Font_PaletteData=0x8000,Font_TilesData=0x8008,FONT_TILE_BYTES=16,FONT_TILES_VRAM_WORD=0x5900)
        result=bg.oracle(bytes(vram),bytes(512),media,bytes(24),s)
        self.assertTrue(all(r['equal'] for r in result.values()))
        vram[7]^=1
        self.assertEqual(bg.oracle(bytes(vram),bytes(512),media,bytes(24),s)['tiles']['first_offsets'],[7])
        blob[32]=1
        with self.assertRaises(ValueError):bg.packed_static(bytes(blob),0)

    def test_font_conflict_reported_not_ignored(self):
        media=dict(tiles=bytes(32),tilemap=bytes(2048),hud=bytes(16),palette=bytes(256))
        s=dict(Font_PaletteData=0x8000,Font_TilesData=0x8008,FONT_TILE_BYTES=16,FONT_TILES_VRAM_WORD=0x5900)
        rom=bytes.fromhex('00000000ff7f0000')+bytes(16)
        result=bg.oracle(bytes(65536),bytes(512),media,rom,s)
        self.assertTrue(result['packed_palette_1_127']['equal'])
        self.assertFalse(result['required_font_palette_4_7']['equal'])


if __name__=='__main__':unittest.main()
