"""Discrete reference controls. These do not certify C float motion or SNES execution."""
import copy
import unittest
from source_actor_execution import Actor, World, UnsupportedExecution


def model(delays=(4,4,4,4,2,2), loop=0):
    def animation(role):
        return dict(role=role,properties={'loop':[[str(loop)]]},frames=[
            dict(delay=d,move=0,bbox=[0,0,10,20],offset=[0,0],attack=None)
            for d in delays])
    return dict(stats={'type':'enemy'},behavior={'source_speed':'1'},
                animations=[animation(r) for r in ('idle','attack1','pain','fall','rise','walk')])


class ExecutionTests(unittest.TestCase):
    def start(self, **kwargs):
        m=model(**kwargs); e=Actor(m,0); w=World([e]); w.set_role(e,'attack1')
        return m,e,w

    def test_variable_delays(self):
        m,e,w=self.start(); original=copy.deepcopy(m)
        for _ in range(42):w.tick()
        self.assertEqual([v[0] for v in w.events if v[1]=='frame'],[0,8,16,24,32,36])
        self.assertEqual((e.frame,e.animating),(5,0))
        self.assertEqual(m,original)

    def test_same_role_and_reset_lastframe(self):
        _,e,w=self.start(); w.tick(); e.last_frame=3
        w.set_role(e,'attack1'); self.assertEqual(e.nextanim,8)
        w.set_role(e,'attack1',reset=True)
        self.assertEqual((e.nextanim,e.last_frame),(9,3))
        w.set_role(e,'pain'); self.assertEqual(e.last_frame,-1)

    def test_reverse_loop(self):
        _,e,w=self.start(delays=(1,1,1),loop=1); e.animating=-1
        for _ in range(6):w.tick()
        self.assertEqual([v[-1] for v in w.events if v[1]=='frame'],[0,2,1,0])

    def test_zero_delay_is_not_caught_up(self):
        _,e,w=self.start(delays=(0,0,1))
        # A role selected during think can advance in this tick's animation pass.
        w.animation_tick(e); self.assertEqual(e.frame,1)
        w.tick(); self.assertEqual(e.frame,1)

    def test_autokill_nonloop(self):
        _,e,w=self.start(delays=(1,));e.autokill=True
        w.tick();w.tick();self.assertFalse(e.exists)

    def test_think_before_animation_completion(self):
        _,e,w=self.start(delays=(1,));e.driver='pain';e.nextthink=2
        w.tick();w.tick()
        self.assertEqual((e.driver,e.animating),('pain',0))
        w.tick();w.tick();self.assertEqual((e.driver,e.role),('enemy','idle'))

    def test_unknown_driver_fails(self):
        _,e,w=self.start();e.driver='unbound'
        p=Actor(model(),1);p.model['stats']['type']='player';w.actors.append(p)
        with self.assertRaisesRegex(UnsupportedExecution,'UNKNOWN_DRIVER'):w.tick()

    def test_deadline_wrap(self):
        _,e,w=self.start(delays=(1,1));w.time=0xffffffff
        w.set_role(e,'attack1',reset=True)
        self.assertEqual(e.nextanim,1)
        w.tick();self.assertEqual(e.frame,0)
        w.tick();self.assertEqual(e.frame,1)

    def test_source_host_update_before_increment_and_cap(self):
        _,e,w=self.start(delays=(0,0,1));w.run_interval(1)
        self.assertEqual((w.time,e.frame),(1,1))
        w.run_interval(500,paused=True);self.assertEqual(w.time,1)
        w.run_interval(500);self.assertEqual(w.time,101)

    def test_hit_force_pain_and_attack_id(self):
        attacker=Actor(model(delays=(10,)),0,x=10);attacker.model['stats']['type']='player'
        attacker.descriptor['attack']=dict(box=[0,0,10,20],force=5,drop=0,kind='attack')
        attacker.attacking=True;target=Actor(model(delays=(10,)),1,x=20,health=20)
        w=World([attacker,target],time=2)
        w.do_attack(attacker)
        self.assertEqual((target.health,target.driver,target.role,target.pain_until),(15,'pain','pain',42))
        self.assertEqual((attacker.attack_id,target.hit_by),(2,2))
        w.time=44;w.do_attack(attacker);self.assertEqual(target.health,15)
        attacker.attack_id=0;w.do_attack(attacker);self.assertEqual(target.health,10)

    def test_contact_depth_and_exact_edge(self):
        a=Actor(model(),0);b=Actor(model(),1,x=10,z=192)
        a.descriptor['attack']=dict(box=[0,0,10,20],force=5,drop=0,kind='attack')
        w=World([a,b]);self.assertTrue(w.checkhit(a,b))
        b.z=193;self.assertFalse(w.checkhit(a,b))

    def test_grounded_enemy_choice_is_source_range_strict(self):
        e=Actor(model(),0,x=100,driver='enemy');p=Actor(model(),1,x=180)
        p.model['stats']['type']='player';w=World([e,p],time=1)
        self.assertFalse(w.ranged(e,p,'attack1'))
        p.x=179;self.assertTrue(w.ranged(e,p,'attack1'))
        w.think(e);self.assertEqual(e.driver,'prepare')
        self.assertTrue(51<=e.stall<71)

    def test_source_inair_threshold_is_not_positive_z(self):
        from fractions import Fraction
        e=Actor(model(),0)
        e.a=Fraction(1,20);self.assertFalse(e.inair)
        e.a=Fraction(1,10);self.assertTrue(e.inair)
        e.a=-Fraction(1,10);self.assertTrue(e.inair)
        self.assertFalse(e.jumping)

    def test_null_think_does_not_advance_deadline(self):
        e=Actor(model(),0,driver='none',nextthink=10)
        w=World([e],time=10);w.update_actors()
        self.assertEqual(e.nextthink,10)


class CorpusReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from compiler import ROOT,Source
        from model_ir import parse_model
        from actor_lowering import lower_model
        source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        cls.enemy=lower_model(parse_model(source,'data/chars/k/k.txt',"K'",'s6-test','historical-bor'))
        cls.player=lower_model(parse_model(source,'data/chars/kula/kula.txt','Kula','s6-test','historical-bor'))

    def test_source_spawn_stats_alias_and_height(self):
        w=World();before=copy.deepcopy(self.enemy)
        e=w.spawn(self.enemy,x=-20,z=180,a=12,alias='instance label')
        self.assertEqual((e.health,e.a,e.base,e.driver,e.nextthink),(60,12,0,'drop',1))
        self.assertEqual(e.display_name,'instance label')
        self.assertEqual(self.enemy,before)
        self.assertFalse(e.jumping)

    def test_ordinary_reference_walk_prepare_and_pain(self):
        # Numerical control is speed1/half-speed, exactly representable in the
        # bounded binary domain. This is a source reference, NOT live AI proof.
        from fractions import Fraction
        w=World();e=w.spawn(self.enemy,x=-20,z=180)
        p=Actor(self.player,1,x=100,z=180,health=100,driver='none');w.actors.append(p)
        for _ in range(21):w.tick()
        self.assertEqual((e.x,e.z,e.driver,e.role),(Fraction(-25),Fraction(175),'enemy','walk'))
        self.assertEqual(e.animating,-1)
        p.x=e.x+30;p.z=e.z
        w.tick();w.tick();self.assertEqual(e.driver,'prepare')
        while e.driver=='prepare':w.tick()
        self.assertEqual((e.driver,e.role),('attack','attack1'))
        # Keep the controlled target outside depth contact while the authored
        # animation executes; player-controller input is outside this reference.
        p.z=e.z+20
        while not any(v[1]=='attack' for v in w.events):w.tick()
        w.damage(e,p,5,False,'attack')
        self.assertEqual((e.health,e.driver,e.role),(55,'pain','pain'))
        for _ in range(200):
            if e.driver!='pain':break
            w.tick()
        self.assertEqual((e.driver,e.role),('enemy','idle'))


if __name__=='__main__':unittest.main()
