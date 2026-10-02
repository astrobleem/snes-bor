import copy
import unittest

from compiler import ROOT, Source
from model_ir import parse_model
from source_actor_raster import compile_animation, encode_tile, exact_cgram


def decode_tile(raw):
    return bytes(sum(((raw[(p//2)*16+y*2+p%2] >> (7-x)) & 1) << p
                     for p in range(4)) for y in range(8) for x in range(8))


class SourceRasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        cls.model = parse_model(cls.source, 'data/chars/kula/kula.txt', 'Kula',
                                'raster-test', 'historical-bor')

    def test_tile_roundtrip(self):
        original = bytes(i % 16 for i in range(64))
        self.assertEqual(decode_tile(encode_tile(original)), original)
        with self.assertRaisesRegex(ValueError, 'TILE_4BPP_INPUT'):
            encode_tile(bytes([16])*64)

    def test_lossless_source_canvas_and_obj_scatter(self):
        import io
        from PIL import Image
        result = compile_animation(self.source, self.model, 'attack1')
        manifest = result['manifest']
        self.assertEqual([len(f['chunks']) for f in manifest['frames']], [12,17,20,19,19,18])
        self.assertEqual(manifest['unique_chunks'], 87)
        self.assertEqual(manifest['preload_bytes'], 22272)
        self.assertFalse(manifest['preload_fits'])
        for frame in manifest['frames']:
            w, h = frame['dimensions']
            self.assertEqual([w,h], [98,104])
            reconstructed = bytearray(w*h)
            vram = bytearray(8192)
            for write in frame['writes']:
                start = write['vram_word_offset']*2
                offset = write['packet_offset']
                size=write['size']
                self.assertLessEqual(start+size, 8192)
                vram[start:start+size] = result['packets'][offset:offset+size]
            for chunk in frame['chunks']:
                cx, cy = chunk['canvas_xy']
                ox, oy = frame['offset']
                self.assertEqual(chunk['right_xy'], [cx-ox,cy-oy])
                self.assertEqual(chunk['left_xy'], [ox-cx-15,cy-oy])
                for ty in range(4):
                    for tx in range(2):
                        offset = (chunk['tile']+ty*16+tx)*32
                        tile = decode_tile(vram[offset:offset+32])
                        for y in range(8):
                            for x in range(8):
                                px, py = cx+tx*8+x, cy+ty*8+y
                                if px < w and py < h:
                                    reconstructed[py*w+px] = manifest['source_palette_indices'][tile[y*8+x]]
            with Image.open(io.BytesIO(self.source.read(frame['source_path']))) as image:
                self.assertEqual(bytes(reconstructed), image.tobytes())

    def test_exact_color_refuses_rounding(self):
        self.assertEqual(exact_cgram([(1,(255,0,0))])[:4], b'\0\0\x1f\0')
        with self.assertRaisesRegex(ValueError, 'COLOR_PRECISION'):
            exact_cgram([(29,(79,96,112))])
        result = compile_animation(self.source, self.model, 'attack1')
        self.assertIsNone(result['cgram'])
        self.assertEqual(result['manifest']['color_encoding']['status'], 'BLOCK')

    def test_deterministic_no_second_ir_or_mutation(self):
        before = copy.deepcopy(self.model)
        a = compile_animation(self.source, self.model, 'attack1')
        self.assertEqual(a, compile_animation(self.source, self.model, 'attack1'))
        self.assertEqual(self.model, before)

    def test_unknown_dialect_role_and_changed_asset_fail_closed(self):
        model = copy.deepcopy(self.model)
        model.dialect = 'unknown'
        with self.assertRaisesRegex(ValueError, 'RASTER_DIALECT'):
            compile_animation(self.source, model, 'attack1')
        with self.assertRaisesRegex(ValueError, 'RASTER_ROLE'):
            compile_animation(self.source, self.model, 'missing')
        model.dialect = 'historical-bor'
        next(a for a in model.animations if a.role == 'attack1').frames[0].asset_sha256 = 'bad'
        with self.assertRaisesRegex(ValueError, 'ASSET_HASH'):
            compile_animation(self.source, model, 'attack1')


if __name__ == '__main__':
    unittest.main()
