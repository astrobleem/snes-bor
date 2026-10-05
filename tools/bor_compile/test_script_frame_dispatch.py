import unittest
from pathlib import Path
from compiler import Source
from script_dispatch_4086 import compile_source
from script_frame_dispatch import compile_frames,link_frames,pack_dispatch,select_frame
from script_vm_reference import Machine,Value,integer


class FrameDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak')
        cls.original=compile_source(source);cls.frames=compile_frames(source)

    def execute(self,program,root,handle,frame,direction):
        events=[];locals={'self':Value('POINTER',1),'frame':integer(frame),
                         'animhandle':integer(handle),'animnum':integer(handle)}
        properties={'direction':integer(direction),'health':integer(130),'maxhealth':integer(400),
                    'playerindex':integer(0),'animationid':integer(handle),'animnum':integer(handle),
                    'x':Value('DECIMAL',80.0),'z':Value('DECIMAL',220.0),'a':Value('DECIMAL',0.0)}
        hooks={'getlocalvar':lambda k:locals.get(k.data,Value()),
               'getentityproperty':lambda e,k:properties[k.data.lower()],
               'rand':lambda:integer(3),'checkwall':lambda *a:integer(0),
               'playerkeys':lambda *a:integer(1),'findtarget':lambda *a:Value('POINTER',2),
               'NULL':lambda:Value(),'openborconstant':lambda k:integer(sum(k.data.encode('latin1')))}
        def effect(name,result):
            def call(*args):
                events.append((name,tuple((v.kind,v.data) for v in args)))
                if name=='setlocalvar':locals[args[0].data]=args[1]
                return result
            return call
        for name in program['builtin_requirements']:
            if name not in hooks:hooks[name]=effect(name,Value('POINTER',3) if name in ('spawn','projectile') else Value())
        if root is not None:Machine(program,hooks,max_steps=20000).call(root)
        return events

    def test_every_authored_frame_preserves_ordered_effects_for_both_facings(self):
        checked=0
        for item in self.frames['programs']:
            original=next(p['program'] for p in self.original['programs'] if p['model']==item['model'])
            for route in item['routes']:
                for frame,root in enumerate(route['frames']):
                    for direction in (0,1):
                        args=(route['animation_handle'],frame,direction)
                        self.assertEqual(self.execute(original,'main',*args),self.execute(item['program'],root,*args),
                                         (item['model'],route['role'],frame,direction))
                        checked+=1
            foreign=next(h['handle'] for h in self.frames['animation_handles'] if h['model']!=item['model'])
            self.assertEqual(self.execute(original,'main',foreign,0,0),[])
        self.assertGreater(checked,500)

    def test_empty_frames_and_inline_routes_are_explicit_and_fit_real_bounds(self):
        code,metadata,linked=link_frames(self.frames)
        self.assertLessEqual(len(code),32768);self.assertLessEqual(len(metadata),17760)
        self.assertLessEqual(linked['slot_count'],1024)
        player=next(p for p in linked['programs'] if p['identity']['model']=='He_ManB')
        breath=next(r for r in player['routes'] if r['role']=='freespecial4')
        self.assertIsNone(breath['entry_ips'][3]);self.assertIsNotNone(breath['entry_ips'][4])
        for item in linked['programs']:
            for route in item['routes']:
                if route['inline_body_preserved']:
                    self.assertEqual(len(set(route['entry_ips'])),1)
                    self.assertIsNotNone(route['entry_ips'][0])
        self.assertFalse(linked['frame_dispatch_bound'])

    def test_dispatch_validates_even_empty_routes_and_serializes_every_entry(self):
        code,metadata,linked=link_frames(self.frames);table=pack_dispatch(self.frames,linked,code,metadata)
        for index,program in enumerate(linked['programs']):
            for route in program['routes']:
                for frame,entry in enumerate(route['entry_ips']):
                    self.assertEqual(select_frame(table,index,route['animation_handle'],frame,context_valid=True),entry)
        player=next(i for i,p in enumerate(linked['programs']) if p['identity']['model']=='He_ManB')
        handle=next(r['animation_handle'] for r in linked['programs'][player]['routes'] if r['role']=='freespecial4')
        for args,lease,error in [((player,handle,3),False,'CONTEXT_REQUIRED'),
                                 ((player,0,0),True,'IDENTITY'),((player,handle,1000),True,'FRAME_RANGE')]:
            with self.assertRaisesRegex(ValueError,error):select_frame(table,*args,context_valid=lease)
        foreign=next(h for h in self.frames['animation_handles'] if h['model']=='He_Man')
        self.assertIsNone(select_frame(table,player,foreign['handle'],0,context_valid=True))
        broken=bytearray(table);broken[-1]^=1
        with self.assertRaisesRegex(ValueError,'TABLE_ABI'):select_frame(broken,player,handle,3,context_valid=True)


if __name__=='__main__':unittest.main()
