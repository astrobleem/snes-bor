import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from compiler import Source
from component_source_assets import derive
from m4_bg_components_native import compile_rom
from m4_online_component_evidence import costs,decode_vram
from source_bg_feasibility import decode,rgb555


class ImmutableSourceAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name)
        cls.source=Source('Masters of the Universe [v.3.0 Build 4086].pak')
        cls.authority=derive(cls.source,'DATA/LEVELS/GUILE2.TXT',cls.folder)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_no_position_or_complete_actor_canvases(self):
        self.assertEqual(self.authority['complete_actor_contexts'],0)
        self.assertEqual(self.authority['stage']['scene']['actors'],[])
        self.assertEqual({f['role'] for f in self.authority['frames']},{'select','idle','walk'})

    def test_original_source_dimensions_and_indexed_art_survive(self):
        palette=self.authority['palette_identity']
        for f in self.authority['frames']:
            indices,_,digest=decode(self.source,f['path'],palette['rgb8'])
            self.assertEqual(list(indices.shape[::-1]),f['dimensions'])
            self.assertEqual(digest,f['source_sha256'])
            self.assertEqual(indices.tobytes(),(self.folder/(f['role']+'.indices')).read_bytes())
        self.assertEqual(next(f for f in self.authority['frames'] if f['role']=='walk')['dimensions'],[310,220])

    def test_source_palette_remains_exact_after_component_lookup(self):
        colors=json.loads((self.folder/'initial.json').read_text())
        lut=np.fromfile(self.folder/'actor-palette.bin',dtype='<u2')
        palette=self.authority['palette_identity']
        for f in self.authority['frames']:
            indices,rgb,_=decode(self.source,f['path'],palette['rgb8'])
            used=np.unique(indices[indices!=0]);words=lut[used]
            reconstructed=np.array([colors[(int(w)&255)-4]+((int(w)>>8&1)<<5)+((int(w)>>9&1)<<10) for w in words])
            self.assertTrue(np.array_equal(reconstructed,np.array(palette['rgb555'])[used]))

    def test_independent_planar_decoder_recovers_exact_backdrop(self):
        report=json.loads((self.folder/'report.json').read_text())
        rom,_,_=compile_rom(report,self.folder,cache_assets=self.folder,offset_alias=True)
        vram=bytearray(65536)
        for name,at in (('high.chr',0),('low.chr',0xc000),('0-high.map',0xf000),('0-low.map',0xf800)):
            data=(self.folder/name).read_bytes();vram[at:at+len(data)]=data
        expected=np.fromfile(self.folder/'expected.rgb555',dtype='<u2').reshape(224,256)
        self.assertTrue(np.array_equal(decode_vram(vram,rom[0x29000:0x29200]),expected))


class PublicationTraceTests(unittest.TestCase):
    def events(self,complete=True):
        phases=['OnlinePublish','OnlineBlank','OnlineTile','OnlineEncode','OnlineTransfer','DMA:80:24:0']
        if complete:phases+=['OnlineDmaDone1']
        phases+=['OnlineComplete','INIDISP:15']
        return [dict(phase=p,clock=100*i,field=0,line=0) for i,p in enumerate(phases)]

    def test_costs_require_actual_dma_completion_before_visible_epoch(self):
        result=costs(self.events());self.assertEqual(result['worst']['dma_bytes'],80)
        self.assertEqual(result['worst']['composition_clocks'],200)
        with self.assertRaisesRegex(ValueError,'BEFORE_DMA'):costs(self.events(False))

    def test_rejection_cannot_follow_a_partial_transfer(self):
        events=self.events()[:6]+[dict(phase='OnlineReject',clock=600)]
        with self.assertRaisesRegex(ValueError,'REJECTION_AFTER_MUTATION'):costs(events)

    def test_same_clock_completion_is_independent_of_callback_registration_order(self):
        events=self.events();events[6]['clock']=events[7]['clock']
        events[6],events[7]=events[7],events[6]
        self.assertEqual(costs(events)['worst']['dma_transfers'],1)


if __name__=='__main__':unittest.main()
