"""Focused source-pixel, shared-resource and overwrite-lease controls."""
import io
import unittest
from PIL import Image
from compiler import ROOT,Source
from model_ir import parse_model
from source_actor_raster import compile_animation
from source_frame_transport import compile_frames,retained_working_set
from source_instance_transport import emit_jobs
from test_source_actor_raster import decode_tile


class InstanceTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        model=parse_model(cls.source,'data/chars/kula/kula.txt','Kula','instance-test','historical-bor')
        cls.manifest=compile_animation(cls.source,model,'attack1',color_adapter='SNES_RGB555_TRUNCATE')['manifest']
        cls.plan=compile_frames(cls.source,cls.manifest,group_future=True)

    def test_every_source_pixel_survives_static_placement(self):
        image=bytearray(self.plan['vram_byte_range'][1]-self.plan['vram_byte_range'][0])
        for f in self.plan['frames']:
            for w in f['writes']:
                at=w['destination']-0x8000
                self.assertGreaterEqual(at,0);self.assertLessEqual(at+len(w['payload']),len(image))
                image[at:at+len(w['payload'])]=w['payload']
            source=Image.open(io.BytesIO(self.source.read(f['source']['source_path'])))
            canvas=bytearray(source.width*source.height);ox,oy=f['source']['offset']
            for c in f['chunks']:
                cx,cy=c['right_xy'];cx+=ox;cy+=oy
                for ty in range(4):
                    for tx in range(2):
                        at=(c['tile']+ty*16+tx)*32;tile=decode_tile(image[at:at+32])
                        for y in range(8):
                            for x in range(8):
                                xx,yy=cx+tx*8+x,cy+ty*8+y
                                if 0<=xx<source.width and 0<=yy<source.height:
                                    canvas[yy*source.width+xx]=self.manifest['source_palette_indices'][tile[y*8+x]]
            self.assertEqual(bytes(canvas),source.tobytes())

    def test_repeated_instances_do_not_duplicate_graphics(self):
        for i in range(5):
            one=retained_working_set(self.plan,[i],[i+1])
            two=retained_working_set(self.plan,[i,i],[i+1,i+1])
            self.assertEqual(one,two)
            self.assertEqual(one['status'],'FITS_STATIC_LAYOUT')
            self.assertFalse(one['hardware_ready'])

    def test_staggered_retained_three_frame_layout_conflict_is_explicit(self):
        result=retained_working_set(self.plan,[3,4],[4,5])
        self.assertEqual((result['bytes'],result['available_bytes']),(9216,16384))
        self.assertEqual(result['status'],'STATIC_LAYOUT_CONFLICT')
        self.assertTrue(result['layout_conflicts'])

    def test_disappearance_does_not_retire_unconsumed_partner_packet(self):
        retained=retained_working_set(self.plan,[3,4],[5])
        self.assertEqual(retained['bytes'],9216)
        self.assertEqual(retained['status'],'STATIC_LAYOUT_CONFLICT')
        self.assertTrue(retained['layout_conflicts'])
        retired=retained_working_set(self.plan,[],[5])
        self.assertEqual(retired['status'],'FITS_STATIC_LAYOUT')

    def test_lease_never_overwrites_a_retained_older_frame(self):
        footprints=[]
        for f in self.plan['frames']:
            footprints.append({(c['tile']+row*16)*32+byte for c in f['chunks']
                               for row in range(4) for byte in range(64)})
            for w in f['writes']:
                written=set(range(w['destination']-0x8000,w['destination']-0x8000+len(w['payload'])))
                for old in range(w['consumed_frame_at_least'],f['index']):
                    self.assertFalse(written&footprints[old])

    def test_generated_jobs_retain_hardware_fence_and_budget(self):
        jobs=[dict(frame=2,lease=1,target=0x8000,source=0x8000,size=512)]
        text=emit_jobs(jobs)
        self.assertIn('DmaQueue+4,x',text)
        self.assertIn('DmaQueue+5,x',text)
        self.assertIn('adc.l $7F8F2A',text)
        self.assertIn('cmp #$0B00',text)
        self.assertIn('jsl Core_Dma_Enqueue_Long',text)
        for name in ('Kula','Joe','Crab','Lobster','Ramon','Time'):
            self.assertNotIn(name,text)

    def test_compiler_never_claims_hardware_readiness(self):
        self.assertFalse(self.plan['native_fences_connected'])
        self.assertFalse(self.plan['deadline_certified'])
        self.assertTrue(all(not f['ready'] for f in self.plan['frames']))

    def test_job_state_and_physical_resource_bounds_fail_closed(self):
        job=dict(frame=2,lease=1,target=0x8000,source=0x8000,size=512)
        with self.assertRaisesRegex(ValueError,'STATE_CAPACITY'):emit_jobs([job]*97)
        with self.assertRaisesRegex(ValueError,'FENCE_IDENTITY'):emit_jobs([job,job])
        # The reviewed Normal transport now owns $8000..$BFFF. The old
        # $9F00 boundary is a valid second-page transfer, not an ABI fault.
        emit_jobs([dict(job,target=0x9F00)])
        for change in (dict(target=0xBF00),dict(source=0xFF00),dict(size=2272),dict(lease=3)):
            with self.assertRaisesRegex(ValueError,'RESOURCE_ABI'):emit_jobs([dict(job,**change)])


if __name__=='__main__':unittest.main()
