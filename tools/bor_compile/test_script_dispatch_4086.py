import unittest
from pathlib import Path
from compiler import Source
from script_dispatch_4086 import compile_source
from script_vm_reference import Machine,Value,integer


class ScriptDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak')
        cls.report=compile_source(cls.source)

    def environment(self,role,frame,model='He_ManB'):
        handle=next(h['handle'] for h in self.report['animation_handles'] if h['model']==model and h['role']==role)
        local={'frame':integer(frame),'animhandle':integer(handle),'self':Value('POINTER',1)}
        properties={'direction':integer(0),'x':Value('DECIMAL',80.0),
                    'z':Value('DECIMAL',220.0),'a':Value('DECIMAL',0.0)}
        births=[];changes=[]
        hooks={'getlocalvar':lambda k:local[k.data],
               'getentityproperty':lambda e,k:properties[k.data],
               'clearspawnentry':lambda:Value(),'setspawnentry':lambda *args:Value(),
               'spawn':lambda:(births.append('spawn') or Value('POINTER',2)),
               'projectile':lambda *args:(births.append([v.data for v in args]) or Value('POINTER',len(births)+1)),
               'changeentityproperty':lambda *args:(changes.append([v.data for v in args]) or Value())}
        return local,births,changes,hooks

    def program(self,model):return next(p['program'] for p in self.report['programs'] if p['model']==model)

    def test_source_frame_guard_and_distinct_default_model_handle(self):
        local,births,changes,hooks=self.environment('freespecial4',4)
        Machine(self.program('He_ManB'),hooks).call('main')
        self.assertEqual(births,['spawn']);self.assertEqual(changes[0],[2,'position',62.0,220.0,93.0])
        births.clear();changes.clear();local['frame']=integer(3)
        Machine(self.program('He_ManB'),hooks).call('main');self.assertEqual(births,[])
        local['frame']=integer(4)
        Machine(self.program('He_Man'),hooks).call('main');self.assertEqual(births,[])

    def test_both_same_frame_projectile_commands_execute_in_source_order(self):
        _,births,changes,hooks=self.environment('freespecial3',4)
        Machine(self.program('He_ManB'),hooks).call('main')
        self.assertEqual(len(births),2)
        self.assertEqual(births[0][:5],['ShWave',105.0,220.0,0.0,0])
        velocities=[c for c in changes if c[1]=='velocity']
        self.assertEqual(velocities,[[2,'velocity',0,-1.5,0],[3,'velocity',0,1.5,0]])
        self.assertFalse(self.report['native_vm_bound'])


if __name__=='__main__':unittest.main()
