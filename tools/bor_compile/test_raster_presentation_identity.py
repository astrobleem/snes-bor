import hashlib
import json
import unittest
from raster_presentation_identity import refresh_presentation_identity
from raster_bank_residency import optimize,restrict_interval
from test_raster_slot_greedy import source_schedule


class PresentationIdentityTests(unittest.TestCase):
    def test_cache_materialization_drops_parent_packet_admission(self):
        from raster_word_cache_repair import compile_cache_rows
        from raster_slot_greedy import demand
        source=source_schedule()
        source.update(prepared_dma_packets=[{'parent':True}],physical_slot_layout={'parent':True},
            optimistic_bank_order={'parent':True},compiled_transfer_descriptor_sha256='old',native_presentation_proven=True)
        required,_,_=demand(source)
        rows={y:{b:set(cs)for b,cs in enumerate(row)}for y,row in enumerate(required)}
        result=compile_cache_rows(source,rows,0,2,100,{},'cache')
        self.assertNotIn('prepared_dma_packets',result)
        for key in ('physical_slot_layout','optimistic_bank_order','compiled_transfer_descriptor_sha256'):
            self.assertNotIn(key,result)
            self.assertEqual(result['input_'+key],source[key])
        self.assertFalse(result['native_presentation_proven'])

    def test_cache_recompile_rebinds_source_presentation_hash(self):
        source=source_schedule()
        source.update(source_rgb555_sha256='source',selected_modes={'0':'add'},
            compiled_color_window_descriptors={'0':{}},compiled_presentation_sha256='old')
        result=optimize(source,2,0,None,5,solver_backend='highs')
        payload=dict(schedule_sha256=result['compiled_schedule_sha256'],
            selected_modes=result['selected_modes'],
            compiled_color_window_descriptors=result['compiled_color_window_descriptors'],
            source_rgb555_sha256=result['source_rgb555_sha256'])
        self.assertEqual(result['compiled_presentation_sha256'],hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())
        self.assertEqual(result['input_compiled_presentation_sha256'],'old')
        self.assertNotIn('compiled_presentation_sha256',restrict_interval(source,7,8))

    def test_incomplete_binding_drops_old_current_digest(self):
        frame=dict(compiled_presentation_sha256='old',compiled_schedule_sha256='new')
        refresh_presentation_identity(frame)
        self.assertNotIn('compiled_presentation_sha256',frame)
        self.assertEqual(frame['input_compiled_presentation_sha256'],'old')


if __name__=='__main__':unittest.main()
