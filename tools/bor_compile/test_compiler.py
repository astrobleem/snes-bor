"""Focused S0 tests; no emulator, build or production writes."""
import json
import tempfile
import unittest
from pathlib import Path
from compiler import (ROOT, Source, StageIR, QueueIR, EntryIR, SetIR, assign_ids,
                      compile_project, key, legacy_events, lower, partial_set,
                      presentation, project, scene, stage)
from PIL import Image
import io

PAK = ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak'
BASE = '0ef9a82bbd754aa979359df43d23821e48724ad8'
SHA = 'e7fe744af2928939f926a1c9121f6ac9e7f1d378533b95366e4afefd6bfe90af'


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def source(self, files):
        for name, content in files.items():
            p = self.root/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content if isinstance(content,bytes) else content.encode())
        return Source(self.root)
    def test_paths(self):
        s=self.source({'DATA/Foo.TXT':'value'})
        self.assertEqual(s.read(r'data\FOO.txt'),b'value')
        self.assertEqual(s.resolve('data/foo.txt'),'DATA/Foo.TXT')
        with self.assertRaises(ValueError): key('../escape')
    def test_ambiguous_path(self):
        self.assertEqual(key('./Data//FOO'),key(r'DATA\foo'))
    def test_sets_and_next(self):
        s=self.source({'DATA/LEVELS.TXT':'set Other\nfile data/a.txt\nnext\nscene data/s.txt\nset Secret\nifcomplete 2\nfile data/a.txt', 'data/a.txt':'', 'data/s.txt':''})
        p=project(s)
        self.assertEqual([s.name for s in p.sets],['Other','Secret'])
        self.assertTrue(p.sets[0].entries[0].next_after)
        self.assertFalse(p.sets[0].entries[1].next_after)
        self.assertEqual(p.sets[1].ifcomplete,2)
    def test_unknown_progression(self):
        s=self.source({'DATA/LEVELS.TXT':'set X\nteleport 1'})
        with self.assertRaises(ValueError): project(s)
    def test_stage_modifiers_preserved(self):
        s=self.source({'a.txt':'spawn Hero\ncoords 10 20 -5\nalias Bob\nmap 6\nhealth 400\n2pitem Meat\nboss 1\nat 50\nendhole 1'})
        ir=stage(s,'a.txt'); q=ir.queue[0]
        self.assertEqual((q.coords,q.altitude,q.map,q.health,q.alias,q.if2p),((10,20),-5,6,400,'Bob',True))
        self.assertEqual(ir.environment,{'endhole':[1]})
    def test_unknown_fails_closed(self):
        ir=stage(self.source({'a.txt':'teleport 3\nspawn X\nat 0'}),'a.txt')
        self.assertEqual(ir.diagnostics[0]['directive'],'teleport')
        with self.assertRaises(ValueError): lower(ir,{}, {})
    def test_unterminated_fails_closed(self):
        ir=stage(self.source({'a.txt':'spawn X'}),'a.txt')
        with self.assertRaises(ValueError): lower(ir,{}, {})
    def test_vertical_lowering(self):
        ir=StageIR('test',[],scroll='down',queue=[QueueIR('spawn',at=100,character='X',coords=(20,160))])
        count,b=lower(ir,{}, {})
        self.assertEqual((count,int.from_bytes(b[:2],'little'),int.from_bytes(b[2:4],'little')),(1,80,16))
        self.assertEqual(ir.queue[0].coords,(20,160))
    def test_left_lowering(self):
        ir=StageIR('test',[],panels=[['p']],order='a',dimensions={'p':[1000,240]},scroll='left',queue=[QueueIR('spawn',at=100,character='X',coords=(20,160))])
        _,b=lower(ir,{}, {})
        self.assertEqual(int.from_bytes(b[2:4],'little'),480)
    def test_hole_control_and_order(self):
        ir=StageIR('test',[],environment={'hole':[100]},queue=[QueueIR('group',group_min=2,group_max=4),QueueIR('wait',at=20),QueueIR('spawn',character='X',at=10)])
        n,b=lower(ir,{}, {})
        self.assertEqual((n,len(b)),(4,40))
        self.assertEqual([int.from_bytes(b[i:i+2],'little') for i in (10,20,30)],[0,16,8])
        self.assertEqual(len(ir.queue),3)
    def test_scene_timing(self):
        buf=io.BytesIO();Image.new('P',(8,8)).save(buf,format='GIF',duration=5000)
        s=self.source({'s.txt':'music music.bor 1\nanimation a.gif 0 0','music.bor':b'x','a.gif':buf.getvalue()})
        ir=scene(s,'s.txt')
        self.assertEqual(ir.repeat,1)
        self.assertEqual(ir.animations[0]['delays_ms'],[5000])
    def test_content_dedup(self):
        s=self.source({'a':b'identical','b':b'identical'})
        self.assertEqual(presentation(s,StageIR('one',[],background='a')),presentation(s,StageIR('two',[],background='b')))
    def test_model_and_physical_ids(self):
        pinned={'existing':7,'foreign':20}
        a=assign_ids(['B','A','existing'],pinned)
        self.assertEqual(a,assign_ids(['a','existing','b'],pinned))
        self.assertEqual((a['existing'],a['a'],a['b']),(7,21,22))
    def test_partial_and_unlock(self):
        s=SetIR('Extra',3,1,[EntryIR('STAGE','x','x'),EntryIR('SCENE','y','y')])
        p=partial_set(s,1,1)
        self.assertTrue(p['source_unlocked']); self.assertFalse(p['selectable'])
        self.assertTrue(partial_set(s,2,1)['selectable'])
        self.assertFalse(partial_set(s,2,0)['selectable'])
    def test_original_corpus_and_determinism(self):
        r,q=compile_project(Source(PAK),BASE,ROOT/'distribution/bor.msu',SHA)
        rr,qq=compile_project(Source(PAK),BASE,ROOT/'distribution/bor.msu',SHA)
        self.assertEqual(r,rr); self.assertEqual(q,qq)
        self.assertTrue(r['golden_production_pass'])
        self.assertTrue(r['golden_converter_pass'])
        self.assertTrue(r['golden_progression_pass'])
        self.assertTrue(all(s['matches'] for s in r['golden_scene_contract']))
        self.assertTrue(all(s['source_queue_equal'] for s in r['golden']))
        self.assertEqual(len(r['golden']),24)
        self.assertEqual(r['coverage'][1]['next_flags'],[0,0,1,1,0,0,1,0,1,0])
        self.assertIn('data/normal/5b.txt',q)
        bonus=next(e for e in r['entries'] if e['set_name']=='Bonus' and e['kind']=='STAGE')
        self.assertEqual(sum(n for k,n in bonus['model_counts'].items() if k.lower()=='crab'),50)
        self.assertEqual(sum(n for k,n in bonus['model_counts'].items() if k.lower()=='lobster'),27)
        self.assertFalse(bonus['fully_compilable'])
        self.assertNotIn('data/extra.txt',q)
        self.assertNotIn('data/hard/5ahard.txt',q)


if __name__=='__main__': unittest.main()
