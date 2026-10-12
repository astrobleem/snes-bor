import hashlib,unittest
import numpy as np
from raster_frame_bank_compile import compile_witness
from raster_frame_bank_geometry import search
from raster_math_windows import compile_sparse_mask
from test_raster_mask_rectangle_cover import fixture


def source_fixture():
    source=fixture();bg=np.zeros((224,256),dtype=np.uint16);bg[5,32]=1
    from raster_obj_compact import unpack
    for mask in source['piece_pixel_masks']:
        image=unpack(mask);image[6,7]=0;flat=image.flatten();mask['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
    expected=bg.copy();expected[5,32]=34
    source.update(color_math='additive',scanline_math_controls_source_bound=True,selected_modes={'5':'add'},
        compiled_color_window_descriptors={'5':compile_sparse_mask({x:1 for x in range(256)})},
        source_rgb555_sha256=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest())
    rectangles=[dict(x=8,y=0,width=8,height=8),dict(x=32,y=0,width=8,height=8)]
    witness=search(rectangles,{(5,12):{0:[0]},(5,32):{4:[33]}},time_limit=3)
    witness.update(source_rgb555_sha256=source['source_rgb555_sha256'],scanline_interval=[5,6])
    return source,witness,bg,expected


class FrameBankCompileTests(unittest.TestCase):
    def test_changed_windows_preserve_exact_source_output_or_fail(self):
        from raster_math_windows import evaluate
        source,witness,bg,expected=source_fixture()
        witness.update(compiled_color_window_descriptors={'5':compile_sparse_mask({x:0 for x in range(256)})},hardware_two_color_windows_replayed=True)
        witness['pixels'][1]['color']=34
        r=compile_witness(source,witness,bg,expected)
        self.assertFalse(evaluate(r['compiled_color_window_descriptors']['5'],32))
        self.assertTrue(r['restricted_pixel_identity_verified'])
        witness['pixels'][1]['color']=33
        with self.assertRaisesRegex(ValueError,'SOURCE_OUTPUT_REPLAY'):compile_witness(source,witness,bg,expected)

    def test_shared_mode_change_requires_exact_source_output(self):
        source,witness,bg,expected=source_fixture()
        witness.update(selected_modes={'5':'half-add'},shared_row_mode_word_compatibility_replayed=True)
        witness['pixels'][1]['color']=67
        result=compile_witness(source,witness,bg,expected)
        self.assertEqual(result['selected_modes']['5'],'half-add')
        self.assertEqual(result['source_exact_shared_row_math_mode_changes'],1)
        original=compile_witness(source,source_fixture()[1],bg,expected)
        self.assertNotEqual(result['compiled_presentation_sha256'],original['compiled_presentation_sha256'])
        self.assertFalse(result['native_presentation_proven'])
        witness['selected_modes']['5']='subtract'
        with self.assertRaisesRegex(ValueError,'SOURCE_OUTPUT_REPLAY'):compile_witness(source,witness,bg,expected)

    def test_unused_wrapped_piece_padding_cannot_hide_reserved_sprite_overflow(self):
        source,witness,bg,expected=source_fixture()
        witness['pieces'].append(dict(x=0,y=250,width=8,height=8,bank=0))
        witness['geometry_reservation']=dict(oam_entries=0,sprites_per_line=[0]*224,tile_slivers_per_line=[0]*224)
        witness['geometry_reservation']['sprites_per_line'][0]=32
        with self.assertRaisesRegex(ValueError,'RESERVED_HARDWARE_OVERFLOW'):
            compile_witness(source,witness,bg,expected)

    def test_partial_source_exact_compile_preserves_opaque_zero_and_scope(self):
        source,witness,bg,expected=source_fixture()
        result=compile_witness(source,witness,bg,expected)
        from raster_slot_greedy import demand
        required,_,_=demand(result,allow_restricted=True)
        self.assertEqual(required[5][0],{0});self.assertEqual(required[5][4],{33})
        self.assertFalse(result['compiled_pixel_identity_verified'])
        self.assertFalse(result['complete_source_frame_pixel_identity_proven'])
        self.assertEqual(result['source_output_pixels_replayed'],256)
        self.assertFalse(result['physical_transfer_and_native_timing_admitted'])

    def test_opaque_black_cannot_be_dropped_as_background_equal(self):
        source,witness,bg,expected=source_fixture();witness['pixels']=witness['pixels'][1:]
        with self.assertRaisesRegex(ValueError,'OPAQUE_OWNERSHIP'):compile_witness(source,witness,bg,expected)

    def test_joint_cache_initializes_in_vblank_and_rejects_missing_opaque_word(self):
        source,witness,bg,expected=source_fixture()
        resident={b:[]for b in range(8)};resident[0]=[0];resident[4]=[33]
        witness['joint_cache_trace']=[dict(scanline=5,resident_colors=resident)]
        result=compile_witness(source,witness,bg,expected)
        self.assertTrue(result['supplied_joint_cache_residency_compiled'])
        self.assertEqual(result['trace'][0]['colors_written'],2)
        self.assertEqual(result['peak_scheduled_writes'],0)
        witness['scanline_interval']=[0,224]
        full=compile_witness(source,witness,bg,expected)
        self.assertTrue(full['compiled_pixel_identity_verified'])
        self.assertEqual(full['trace'][0]['colors_written'],2)
        resident[0]=[]
        with self.assertRaisesRegex(ValueError,'CACHE_PIXEL_IDENTITY'):compile_witness(source,witness,bg,expected)

    def test_concurrent_geometry_reservation_survives_compilation(self):
        source,witness,bg,expected=source_fixture()
        witness['geometry_reservation']=dict(oam_entries=126,sprites_per_line=[30]*224,tile_slivers_per_line=[32]*224)
        result=compile_witness(source,witness,bg,expected)
        self.assertEqual(result['combined_reserved_geometry'],dict(oam_entries=128,peak_sprites=32,peak_tile_slivers=34))
        self.assertFalse(result['reservation_palette_and_layer_demand_included'])
        witness['geometry_reservation']['tile_slivers_per_line'][7]=33
        with self.assertRaisesRegex(ValueError,'RESERVED_HARDWARE_OVERFLOW'):compile_witness(source,witness,bg,expected)

    def test_full_source_identity_and_bad_math_word_fail_explicitly(self):
        source,witness,bg,expected=source_fixture();witness['scanline_interval']=[0,224]
        result=compile_witness(source,witness,bg,expected)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        witness['pixels'][1]['color']=32
        with self.assertRaisesRegex(ValueError,'SOURCE_OUTPUT_REPLAY'):compile_witness(source,witness,bg,expected)
        expected[0,0]=1
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH'):compile_witness(source,witness,bg,expected)


if __name__=='__main__':unittest.main()
