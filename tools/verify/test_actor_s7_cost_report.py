import unittest
from actor_s7_cost_report import analyze


class ExclusiveCosts(unittest.TestCase):
    def test_nested_irq_not_double_counted(self):
        def event(kind,name,ident,clock):
            return ['S7PROFILE',kind,name,str(ident),str(clock),'0','0','1','0']
        report=dict(profile_rows=[event('enter','parent',1,0),
            event('enter','child',2,20),event('return','child',2,70),
            event('return','parent',1,100)],
            rows=[['S7DMA','Core_Nmi_Play__do_commit','0','0','30'],
                  ['S7DMA','Core_Nmi_Play__done','0','0','40']],
            cpu_rows=[['S7CPU','S6Host_Tick','0','0','1'],
                      ['S7CPU','S6Host_Tick__return','0','100','1']],
            world_deadline_analysis={})
        result=analyze(report)
        self.assertEqual(result['exclusive_master_clocks'],
            {'parent':50,'child':40,'NMI/DMA measured body':10})

    def test_generator_matches_runtime(self):
        from pathlib import Path
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
        from world_pass_codegen import emit, PASSES
        text=(Path(__file__).resolve().parents[2]/'src/core/actor_source_world.pasm').read_text()
        actual=text.split('S6_UpdateWorld__start:\n',1)[1].split('S6_UpdateWorld__done:',1)[0]
        self.assertEqual(actual,emit())
        for callback in PASSES:
            self.assertEqual(actual.count('    jsl '+callback+'\n'),1)
        self.assertNotIn('S6_UpdateWorldDispatch',actual)

    def test_nested_release_is_not_lost_or_double_counted(self):
        def row(kind,name,i,t):return ['S7PROFILE',kind,name,str(i),str(t),'0','0','1','0']
        r=dict(profile_rows=[row('enter','Game_State_Play',1,0),
            row('enter','S6Host_Tick',2,10),row('return','S6Host_Tick',2,40),
            row('enter','S7Resident_Flush',3,50),row('return','S7Resident_Flush',3,70),
            row('return','Game_State_Play',1,90)],
            rows=[['S7DMA','Core_Nmi_Play__do_commit','0','0','55'],
                  ['S7DMA','Core_Nmi_Play__done','0','0','60']],
            cpu_rows=[['S7CPU','S6Host_Tick','0','10','1'],
                      ['S7CPU','S6Host_Tick__return','0','40','1']],world_deadline_analysis={})
        a=analyze(r)
        self.assertEqual(a['world_plus_release'],50)
        self.assertEqual(a['elapsed_through_final_release'],60)
        from actor_s7_cost_report import detailed
        d=detailed(r)['outside']
        self.assertEqual(d['WORLD/RELEASE']['clocks'],50)
        self.assertEqual(sum(v['clocks'] for v in d.values()),60)

    def test_callbacks_entered_after_final_nmi_are_outside_measurement(self):
        row=['S7PROFILE','enter','post-boundary',7,'110','0','0','0','0']
        report=dict(profile_rows=[row],
            rows=[['S7DMA','Core_Nmi_Play__do_commit','0','0','30'],
                  ['S7DMA','Core_Nmi_Play__done','0','0','40']],
            cpu_rows=[['S7CPU','S6Host_Tick','0','0','1'],
                      ['S7CPU','S6Host_Tick__return','0','100','1']],
            world_deadline_analysis={})
        result=analyze(report)
        self.assertNotIn('post-boundary',result['exclusive_master_clocks'])
        self.assertEqual(result['profile_intervals_clipped_at_nmi_end'],
                         [('post-boundary',7,0)])


if __name__=='__main__':
    unittest.main()
