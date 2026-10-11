import copy,hashlib,struct,tempfile,unittest
from pathlib import Path
import numpy as np
from m4_isolated_raster_obj_native import compile_rom
from raster_slot_greedy import demand
from raster_physical_relabel import point_partition
from raster_obj_math_cover import apply_math
from test_raster_slot_greedy import source_schedule


class AuthoredRasterCompileTests(unittest.TestCase):
    def fixture(self):
        source=source_schedule();source.update(color_math='subscreen-additive',main_screen_obj_disabled=True,metadata={})
        before=copy.deepcopy(source['trace'][-1]['resident_before'])
        for e in source['trace'][-1]['updates']:before[e['bank']][e['slot']-1]=e['color']
        for y in range(len(source['trace']),224):source['trace'].append(dict(scanline=y,resident_before=copy.deepcopy(before),updates=[]))
        state=[0]*128;packets=[]
        for row in source['trace']:
            for e in row['updates']:state[16*e['bank']+e['slot']]=e['color']
            span,ranges=point_partition([16*e['bank']+e['slot']for e in row['updates']]if row['scanline']else[])
            packets.append(dict(scanline=row['scanline'],prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=b''.join(state[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in ranges]))
        source.update(prepared_dma_packets=packets,physical_slot_layout=dict(status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN'))
        background=np.full((224,256),7<<5,dtype=np.uint16);expected=background.copy()
        for p,image in zip(source['pieces'],demand(source)[2]):
            for ly,lx in zip(*np.where(image>=0)):
                y,x=p['y']+int(ly),p['x']+int(lx);expected[y,x]=apply_math(int(image[ly,lx]),int(background[y,x]),'add')
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        base=bytearray(4*1024*1024);struct.pack_into('<H',base,0x7ffc,0x8000)
        return bytes(base),source,dict(background=background,expected=expected,metadata={})

    def test_authored_assets_and_routing_are_bound_without_bank_zero_growth(self):
        base,source,context=self.fixture()
        with tempfile.TemporaryDirectory()as folder:
            raw,expected,palette,oam,sy,report=compile_rom(base,None,{},source,Path(folder),sa1_mapping=True,foreground_wai=True,prepare_next_line=True,authored_context=context)
            asm=(Path(folder)/'fixture.pasm').read_text()
        np.testing.assert_array_equal(expected,context['expected'])
        self.assertEqual(raw[32768:39*32768],base[32768:39*32768])
        self.assertTrue(report['authored_source_context_bound'])
        self.assertEqual(report['obj_operand_screen'],'subscreen')
        self.assertEqual(report['background_asset_rom_banks'],[107,109])
        self.assertIn('lda #$10\n sta $212D',asm)
        self.assertIn('lda #$01\n sta $2131',asm)
        self.assertFalse(report['concurrent_actor_layer_routing_proven'])
        self.assertEqual(len(oam),544)

    def test_wrong_alpha_context_and_unleased_nmi_reject(self):
        base,source,context=self.fixture()
        with tempfile.TemporaryDirectory()as folder:
            bad=copy.deepcopy(context);bad['expected'][0,0]^=1
            with self.assertRaisesRegex(ValueError,'COMPLETE_ALPHA_PIXEL_IDENTITY'):
                compile_rom(base,None,{},source,Path(folder),authored_context=bad)
            with self.assertRaisesRegex(ValueError,'NMI_VRAM_LEASE_NOT_IMPLEMENTED'):
                compile_rom(base,None,{},source,Path(folder),sa1_mapping=True,production_nmi_services=True,authored_context=context)


if __name__=='__main__':unittest.main()
