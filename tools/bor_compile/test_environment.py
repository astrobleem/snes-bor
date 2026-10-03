import unittest
import json
import tempfile
import re
import subprocess
import sys
from pathlib import Path

from compiler import ROOT, Source, stage, model_catalog
from environment_semantics import altitude_binding, display_name, exit_clamp, historical_map, hole_predicate, lower_map_queue
from stage_environment_abi import encode_map, decode_map, encode_palettes


class SourceEnvironmentTests(unittest.TestCase):
    def test_map_roundtrip_and_legacy_bytes(self):
        for kind in range(256):
            for facing in (0, 1):
                for selection in range(256):
                    a, b = encode_map(facing, kind, selection)
                    self.assertEqual(decode_map(a, b), (facing, selection))
                    self.assertEqual(b & ~0x18, kind & ~0x18)
                    if selection < 4:
                        self.assertEqual((a, b), (facing, (kind & ~0x18) | (selection << 3)))

    def test_all_palettes_emitted_without_truncation(self):
        palettes = [[i] * 16 for i in range(5)]
        data = encode_palettes(palettes)
        self.assertEqual(len(data), 160)
        self.assertEqual(data[-32:], b'\x04\x00' * 16)
        with self.assertRaises(ValueError):
            encode_palettes([[0] * 16] * 256)

    def test_real_extra_map_lowering_keeps_all_records_and_source_ir(self):
        source = Source(ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak')
        models = model_catalog(source)
        ir = stage(source, 'DATA/EXTRA.TXT')
        authored = [q.map for q in ir.queue]
        roster = {name: i for i, name in enumerate(sorted(models))}
        entities = {name: m['entity'] for name, m in models.items()}
        count, blob = lower_map_queue(ir, roster, entities, dialect='historical-bor')
        self.assertEqual((count, len(blob)), (184, 1840))
        self.assertEqual([q.map for q in ir.queue], authored)
        for i, q in enumerate(ir.queue):
            if q.kind == 'spawn':
                expected = historical_map(q.map, 7)
                self.assertEqual(decode_map(blob[i*10+5], blob[i*10+6])[1], expected)
        self.assertEqual(len(models['lobster']['entity']['remaps']), 5)
        self.assertEqual(sum(q.character and q.character.casefold() == 'lobster' for q in ir.queue if q.kind == 'spawn'), 27)
        self.assertEqual(sum(q.character and q.character.casefold() == 'crab' for q in ir.queue if q.kind == 'spawn'),50)
        self.assertEqual([sum(q.kind==kind for q in ir.queue) for kind in ('spawn','wait','group')],[166,7,11])

    def test_colourmap_unsigned_domain_and_absent_pointer(self):
        self.assertEqual([historical_map(i, 7) for i in range(9)], [0,1,2,3,4,5,6,7,0])
        self.assertEqual(historical_map(-1, 7), 0)
        self.assertEqual(historical_map(3, 2), 0)

    def test_alias_does_not_resolve_a_model(self):
        self.assertEqual(display_name('Eiji', 'Someone'), 'Someone')
        self.assertEqual(display_name('Eiji', ''), 'Eiji')
        self.assertEqual(display_name('Eiji', 'a' * 21), 'a' * 20)

    def test_signed_fixed_base_is_not_a_throw(self):
        for value in (49, -5):
            b = altitude_binding(value, 'steamer')
            self.assertEqual((b.authored, b.initial, b.base), (value, value, value))
            self.assertEqual(b.ownership, 'fixed_base')

    def test_spawn_altitude_override_order(self):
        self.assertIsNone(altitude_binding(49, 'enemy', authored_x=115).initial)
        self.assertEqual(altitude_binding(49, 'enemy', authored_x=0).initial, 49)
        self.assertEqual(altitude_binding(49, 'enemy', 'biker', authored_x=115).initial, 49)
        self.assertEqual(altitude_binding(-5, 'player', time=1).initial, 300)
        self.assertIsNone(altitude_binding(0, 'enemy', scroll='down', world_x=100).initial)

    def test_exit_geometry_depends_on_depth(self):
        self.assertEqual(exit_clamp(1000, 232, 1000, True), 970)
        self.assertEqual(exit_clamp(1000, 200, 1000, True), 938)
        self.assertEqual(hole_predicate(970, 200, 1000, [], True), 2)
        self.assertEqual(hole_predicate(111, 195, 1000, [100], False), 1)
        self.assertEqual(hole_predicate(111, 194, 1000, [100], False), 0)

    def test_driver_binding_uses_source_spawn_not_equal_coordinates(self):
        from analyze import validate_environment
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'stage.txt').write_text('spawn A\ncoords 10 20 49\nat 0\nspawn B\ncoords 10 20 49\nat 1')
            ir=stage(Source(root),'stage.txt')
            r=validate_environment(ir,{'a':{'ir':{'stats':{'type':'steamer'}}},
                                       'b':{'ir':{'stats':{'type':'enemy'}}}})
            self.assertEqual(len(r['bindings']),1)
            self.assertEqual(len(r['diagnostics']),1)

    def test_hole_resource_limit_is_not_silent_omission(self):
        from analyze import validate_environment
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'stage.txt').write_text('hole 100\nhole 200\nhole 300')
            ir=stage(Source(root),'stage.txt')
            self.assertEqual(len(ir.environment['hole']),3)
            self.assertTrue(any('HOLE_CAPACITY_EXCEEDED' in d['reason'] for d in validate_environment(ir)['diagnostics']))

    def test_golden_selector_only_changes(self):
        from compiler import baseline, compile_project, key
        from environment_semantics import extend_legacy_queue_maps
        source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        ref='c474617ee150b28b5b23677d89a9010b087dfa78'
        _,queues=compile_project(source,ref)
        cfg,git=baseline(ref)
        legacy={s['spawn']:queues[key(s['source_level'])] for s in cfg['STAGE_CONFIGS'] if s['family']=='bor-original'}
        for path,data in legacy.items(): self.assertEqual(data,git(path))
        changed=0
        for s in cfg['STAGE_CONFIGS']:
            if s['family']!='bor-original': continue
            ir=stage(source,s['source_level']);before=legacy[s['spawn']]
            after=extend_legacy_queue_maps(ir,before)
            self.assertEqual(after,(ROOT/s['spawn']).read_bytes())
            self.assertEqual(len(before),len(after))
            changed+=before!=after
            prefix=len(ir.environment.get('hole',[]))
            for i,q in enumerate(ir.queue,prefix):
                a,b=before[i*10:(i+1)*10],after[i*10:(i+1)*10]
                self.assertEqual(a[:5]+a[7:],b[:5]+b[7:])
                self.assertEqual(a[5]&1,b[5]&1)
                self.assertEqual(a[6]&~0x18,b[6]&~0x18)
                if 0<=q.map<=3: self.assertEqual(a,b)
        self.assertEqual((len(legacy),changed),(24,6))

    def test_real_lobster_all_five_palettes(self):
        from pack_msu_roster import pack_character_blob
        with tempfile.TemporaryDirectory() as folder:
            prefix=Path(folder)/'actor'
            subprocess.run([sys.executable,str(ROOT/'tools/bor_converter/convert_character.py'),
                str(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak'),
                r'DATA\CHARS\LOBSTER\LOBSTER.TXT',str(prefix)],check=True,capture_output=True)
            manifest=json.loads(Path(str(prefix)+'_moveset.json').read_text())
            palettes=encode_palettes(manifest['remap_palettes'])
            self.assertEqual(len(palettes),5*32)
            old,_=pack_character_blob(str(prefix),extended_maps=False)
            new,_=pack_character_blob(str(prefix),extended_maps=True)
            self.assertEqual(len(new)-len(old),2*32)
            self.assertIn(palettes,new)

    def test_parallel_metadata_does_not_touch_queue_or_following_state(self):
        stride=int(re.search(r'(?m)^CHAR_ZP_LEN\s*=\s*(\d+)',(ROOT/'src/main.pasm').read_text())[1])
        self.assertEqual(stride,133)
        self.assertLessEqual(0x7E550F+6*stride,0x7E5830)
        self.assertLessEqual(0x7E5834,0x7E5893)
        abi=json.loads((ROOT/'src/generated/queue_abi.json').read_text())
        self.assertEqual((abi['record_size'],abi['capacity'],abi['buffer_base']),(10,92,0x7F9200))

    def test_assembled_long_table_fields_keep_their_bank(self):
        symbols={name:(int(bank,16)<<16)|int(offset,16) for bank,offset,name in
                 re.findall(r'(?m)^([0-9A-F]{2}):([0-9A-F]{4}) (\w+)$',(ROOT/'src/main.sym').read_text())}
        rom=(ROOT/'distribution/bor.sfc').read_bytes()
        def pc(addr): return (addr>>16)*0x8000+(addr&0x7fff)
        for routine,table,fields,end in (
            ('StageEnv_ApplySpawnBase','StageEnv_BaseRecords',(0,1,2,4),'StageEnv_ApplySpawnAlias'),
            ('StageEnv_ApplySpawnAlias','StageEnv_AliasRecords',(0,1,2),'StageEnv_CaptureChildBase')):
            code=rom[pc(symbols[routine]):pc(symbols[end])]
            for field in fields:
                target=symbols[table]+field
                self.assertIn(b'\xbf'+target.to_bytes(3,'little'),code,(routine,field))

    def test_generated_alias_and_base_tables_reproduce(self):
        import build_rom
        from generate_environment import generate
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'environment.pasm'
            result=generate(build_rom.STAGE_CONFIGS,output)
            self.assertEqual(output.read_bytes(),(ROOT/'src/generated/stage_environment_bases.pasm').read_bytes())
            self.assertEqual((len(result['bases']),len(result['aliases']),len(result['names'])),(5,155,89))
            self.assertEqual(result['table_bytes'],1496)
            self.assertEqual({r['source_altitude'] for r in result['bases']},{49,-5})
            self.assertTrue(all(result['names'][r['alias_id']-1]==r['display_name'] for r in result['aliases']))
            self.assertEqual(result['aliases'][0]['source_model'],'Shermie')
            self.assertEqual(result['aliases'][0]['display_name'],'Prissy')


if __name__ == '__main__':
    unittest.main()
