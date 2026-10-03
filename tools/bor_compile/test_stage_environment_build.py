"""Focused pre-assembly integration tests; the BG encoder is replaced by a fixture.

Generated artifacts live only in temporary directories. No native/ROM/MSU
build, emulator, audio generation, or shared asset regeneration runs here.
"""
import copy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from compiler import ROOT
sys.path.insert(0,str(ROOT))
import build_rom
import stage_water as water
import stage_frontpanel_bg2 as full


class StageEnvironmentBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = copy.deepcopy(build_rom.STAGE_CONFIGS)
        cls.roster = copy.deepcopy(build_rom.ROSTER_CONFIGS)
        cls.sources, cls.normal = water.normal_stage_inputs(cls.configs)
        cls.accepted = {ir.source_path:json.loads((Path(cls.configs[i]['bg'])/'manifest.json').read_text())
                        for i,ir in cls.normal.items()}

    def fixture_encoder(self, index, level, row):
        manifest = copy.deepcopy(self.accepted[row.source_path])
        manifest.update(level_entry=row.source_path,unique_tiles=1,stage_water=asdict(row))
        blobs = dict(zip(('tiles.bin','tilemap.bin','palette.bin'),
                         (bytes(32), b'\0\0\1'*(manifest['width_tiles']*28), bytes(256))))
        manifest.update({n.split('.')[0]+'_bytes':len(b) for n,b in blobs.items()})
        return manifest,blobs

    def prepare(self, temp):
        def clean_encoder(index,level,row,source_path):
            manifest,blobs = self.fixture_encoder(index,level,row)
            manifest.update(frontpanel=None,normal_frontpanel_removed=True)
            return manifest,blobs
        with patch.object(full,'encode_clean_background',side_effect=clean_encoder):
            return build_rom.prepare_stage_environment_assets(
                self.configs,self.roster,output_root=Path(temp)/'media',
                generated_dir=Path(temp)/'generated',bor_c=ROOT/'out/bor_compile_s6/BOR.C')

    def test_source_selection_and_shared_ir_cache(self):
        with patch.object(water,'stage',wraps=water.stage) as parser:
            sources,normal = water.normal_stage_inputs(self.configs)
        self.assertEqual(parser.call_count,14)
        self.assertEqual(list(normal),list(range(22,36)))
        self.assertEqual(len(sources),len({str(Path(c['pak']).resolve()) for c in self.configs}))
        # A claimed Normal set cannot activate an Easy path (or vice versa).
        bad = copy.deepcopy(self.configs)
        bad[0]['source_set_id'] = 1
        with self.assertRaisesRegex(ValueError,'MEMBERSHIP'):
            water.normal_stage_inputs(bad)

    def test_materialization_tables_bounds_hud_and_repeat_cache(self):
        before = copy.deepcopy(self.configs)
        originals = {Path(c[layer])/name for c in self.configs for layer in ('bg','frontpanel') if c.get(layer)
                     for name in ('manifest.json','tiles.bin','tilemap.bin','palette.bin')}
        hashes = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(water,'encode_background',side_effect=self.fixture_encoder) as encoder, \
                patch.object(build_rom,'assemble',side_effect=AssertionError('native build forbidden')):
            result = self.prepare(temp)
            self.assertEqual(encoder.call_count,4)
            changed = [i for i,(old,new) in enumerate(zip(before,result)) if old != new]
            self.assertEqual(changed,[22,26,27,28,29,30,33,34,35])
            for i in changed:
                fields = ['bg']+(['frontpanel'] if i in (22,27,28,30,33,34,35) else [])
                expected = dict(before[i],**{field:result[i][field] for field in fields})
                self.assertEqual(result[i],expected)
                for field in fields:
                    self.assertNotEqual(result[i][field],before[i][field])
            generated = Path(temp)/'generated'
            fp_table,fp_rows = full.motion_tables(result,self.normal)
            self.assertEqual((generated/'stage_frontpanel_tables.pasm').read_text(),fp_table)
            self.assertEqual(len(fp_rows),7)
            self.assertTrue(all(r['rows'] == 28 and r['working_set']['34'] <= 256 for r in fp_rows))
            from stage_bounds import emit_pasm,from_ir
            from generate_hud_names import render,family_sources
            bounds = [from_ir(self.normal[i]) if i in self.normal else None for i in range(len(result))]
            self.assertEqual((generated/'stage_bounds_tables.pasm').read_text(),emit_pasm(bounds,bank=15))
            hud_text,hud_rows = render(self.roster,family_sources(self.configs))
            self.assertEqual((generated/'hud_opponent_names.pasm').read_text(),hud_text)
            self.assertEqual(len(hud_rows),len(self.roster))
            table = (generated/'stage_water_tables.pasm').read_text()
            rows = [water.bind(self.sources[str(Path(self.configs[i]['pak']).resolve())],ir,i)
                    for i,ir in self.normal.items()]
            self.assertEqual(table,water.emit_tables(rows))
            # Easy and foreign slots are zero in all three runtime maps.
            mode_section = table.split('StageWater_ModeMap:\n')[1].split('StageWater_RockMap:')[0]
            import re
            modes = list(map(int,re.findall(r'\d+',mode_section)))
            self.assertEqual(modes[:22],[0]*22)
            self.assertEqual(modes[26:30],[15,0,0,2])
            mtimes = {n:p.stat().st_mtime_ns for n,p in
                      ((name,generated/name) for name in ('stage_water_tables.pasm','stage_bounds_tables.pasm','hud_opponent_names.pasm'))}
            result2 = self.prepare(temp)
            self.assertEqual(encoder.call_count,4)
            self.assertEqual(result,result2)
            self.assertTrue(all((generated/n).stat().st_mtime_ns == t for n,t in mtimes.items()))
            report = json.loads((generated/'stage_environment_materialization.json').read_text())
            self.assertTrue(all(r['reused'] for r in report['water_media']))
            self.assertEqual(report['frontpanel_wram']['status'],'PASS')
            self.assertEqual(report['frontpanel_wram']['block_start'],0x7EE020)
            self.assertEqual(report['frontpanel_wram']['dma_bank'],0x7E)
        self.assertEqual(self.configs,before)
        self.assertEqual({p:hashlib.sha256(p.read_bytes()).hexdigest() for p in originals},hashes)

    def test_corrupt_cache_rejected_preserved_and_repaired(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(water,'encode_background',side_effect=self.fixture_encoder) as encoder:
            first = self.prepare(temp)
            bad = Path(first[26]['bg'])/'tiles.bin'
            bad.write_bytes(b'corrupt fixture')
            second = self.prepare(temp)
            self.assertEqual(encoder.call_count,5)
            self.assertNotEqual(first[26]['bg'],second[26]['bg'])
            self.assertEqual(bad.read_bytes(),b'corrupt fixture')
            self.assertEqual((Path(second[26]['bg'])/'tiles.bin').read_bytes(),bytes(32))

    def test_bad_media_never_publishes_tables_or_mutates_bindings(self):
        def bad_encoder(index,level,row):
            manifest,blobs = self.fixture_encoder(index,level,row)
            blobs['tilemap.bin'] = b'\xff\xff\1'*(manifest['width_tiles']*28)
            return manifest,blobs
        before = copy.deepcopy(self.configs)
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(water,'encode_background',side_effect=bad_encoder):
            with self.assertRaisesRegex(ValueError,'TILE_REFERENCE'):
                self.prepare(temp)
            self.assertFalse((Path(temp)/'generated').exists())
        self.assertEqual(self.configs,before)

    def test_changed_source_metadata_changes_generation(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(water,'encode_background',side_effect=self.fixture_encoder) as encoder:
            first,_,_ = water.materialize_normal(self.configs,self.sources,self.normal,
                                                ROOT/'out/bor_compile_s6/BOR.C',temp)
            altered = copy.deepcopy(self.normal)
            altered[29].environment['water'][-1]['mode'] = 15
            second,rows,_ = water.materialize_normal(self.configs,self.sources,altered,
                                                     ROOT/'out/bor_compile_s6/BOR.C',temp)
            self.assertEqual(encoder.call_count,5)
            self.assertNotEqual(first[29]['bg'],second[29]['bg'])
            self.assertEqual(next(r.amplitude for r in rows if r.physical == 29),15)

    def test_boot_init_precedes_first_bg_load_and_nmi_enable(self):
        main = (ROOT/'src/main.pasm').read_text()
        boot = main.split('scpu_boot:\n',1)[1].split('scpu_main_loop:\n',1)[0]
        entry = 'StageFp_BG2ColdInit' if 'jsl StageFp_BG2ColdInit' in boot else 'StageWater_ColdInit'
        self.assertEqual(main.count('jsl '+entry),1)
        self.assertLess(boot.index('jsl '+entry),boot.index('jsr Bg_LoadScene'))
        self.assertLess(boot.index('jsl '+entry),boot.index('jsr Core_Nmi_Init'))
        fp_code = (ROOT/'src/core/stage_frontpanel_bg2.pasm').read_text()
        chain = fp_code.split('StageFp_BG2ColdInit:')[1].split('StageFp_BG2SceneReset:')[0]
        self.assertLess(chain.index('jsl StageWater_ColdInit'),chain.index('jsl StageFp_Init'))
        self.assertLess(chain.index('jsl StageFp_Init'),chain.index('jml StageFp_BG2Init'))
        assembly = (ROOT/'src/core/stage_water.pasm').read_text()
        wrapper = assembly.split('StageWater_ColdInit:\n')[1].split('StageWater_Init:')[0]
        self.assertLess(wrapper.index('jsl Tad_StreamInit'),wrapper.index('jml StageWater_Init'))
        cold_clear = assembly.split('StageWater_Reset__clear:\n')[1].split('StageWater_Begin:')[0]
        self.assertNotIn('Nmi_',cold_clear)
        self.assertIn('jmp StageWater_Reset__clear',assembly.split('StageWater_Reset:')[0])

    def test_water_tile_domain_minimum_maximum_and_overflow(self):
        limit = water.runtime_tile_id_limit()
        self.assertEqual(limit,16384)
        row = water.WaterMetadata(26,'fixture.txt',amplitude=2,background_height=80)
        accepted = dict(width_tiles=32,content_width_tiles=32)
        for count in (0,1,1922,1435,676,6419,limit,limit+1,65535,65536):
            with self.subTest(count=count):
                blobs = {'tiles.bin':bytes(count*32),
                         'tilemap.bin':max(0,count-1).to_bytes(2,'little')+b'\1',
                         'palette.bin':bytes(256)}
                blobs['tilemap.bin'] *= 32*28
                manifest = dict(accepted,stage_water=asdict(row),streaming=True,
                                height_tiles=28,level_entry=row.source_path,unique_tiles=count)
                manifest.update({n.split('.')[0]+'_bytes':len(b) for n,b in blobs.items()})
                if 1 <= count <= limit:
                    water._validate_media(manifest,blobs,row,accepted)
                else:
                    error = 'TILE2SLOT_CAPACITY' if count <= 65535 and count > limit else 'WATER_MEDIA_CAPACITY'
                    with self.assertRaisesRegex(ValueError,error):
                        water._validate_media(manifest,blobs,row,accepted)

    def test_runtime_tile_domain_is_source_derived_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'stream_cache.pasm'
            for literal,expected in (('73',73),('$4000',16384),('0x4000',16384)):
                source.write_text('STREAM_MAX_TILE_IDS = '+literal+' ; allocation\n')
                self.assertEqual(water.runtime_tile_id_limit(source),expected)
            for definition in ('', 'STREAM_MAX_TILE_IDS = 0',
                               'STREAM_MAX_TILE_IDS = 65536',
                               'STREAM_MAX_TILE_IDS = 8192*2',
                               'STREAM_MAX_TILE_IDS = 12\nSTREAM_MAX_TILE_IDS = 24'):
                source.write_text(definition)
                with self.assertRaisesRegex(ValueError,'RUNTIME_TILE_DOMAIN_UNBOUND'):
                    water.runtime_tile_id_limit(source)

    def test_runtime_limit_rechecked_for_hash_valid_cached_water(self):
        def two_tiles(index,level,row):
            manifest,blobs = self.fixture_encoder(index,level,row)
            manifest.update(unique_tiles=2,tiles_bytes=64)
            blobs['tiles.bin'] = bytes(64)
            return manifest,blobs
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(water,'encode_background',side_effect=two_tiles) as encoder:
            # Admit two-tile fixtures, then shrink only the runtime allocation.
            self.prepare(temp)
            with patch.object(water,'runtime_tile_id_limit',return_value=1), \
                    self.assertRaisesRegex(ValueError,'TILE2SLOT_CAPACITY'):
                self.prepare(temp)
            # Cache admission rejected the old bytes; fresh output is rejected too.
            self.assertEqual(encoder.call_count,5)


if __name__ == '__main__':
    unittest.main()
