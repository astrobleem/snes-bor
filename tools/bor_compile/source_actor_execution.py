"""Pinned historical-BOR execution reference, not a runtime certificate.

Integer/discrete semantics are exact. Fractional motion is a rational reference;
it is NOT a claim of equivalence to the original C floating-point implementation.
Unsupported event/world hooks fail closed rather than disappearing.
"""
from dataclasses import dataclass, field
from fractions import Fraction
from actor_lowering import source_random32_step

class UnsupportedExecution(ValueError): pass

def prop(animation,name,default):
    values=animation['properties'].get(name)
    return default if not values else [int(v) for v in values[-1]]

@dataclass
class Actor:
    model: dict
    slot: int
    x: Fraction=Fraction(0)
    z: Fraction=Fraction(180)
    a: Fraction=Fraction(0)
    base: Fraction=Fraction(0)
    health: int=10
    direction: int=1
    role: str='idle'
    frame: int=0
    last_frame: int=-1
    animating: int=1
    nextanim: int=0
    nextthink: int=1
    driver: str='none'
    stall: int=0
    pain_until: int=0
    attacking: bool=False
    projectile: bool=False
    jumping: bool=False
    autokill: bool=False
    exists: bool=True
    xdir: Fraction=Fraction(0)
    zdir: Fraction=Fraction(0)
    tossv: Fraction=Fraction(0)
    toss_time: int=0
    attack_id: int=0
    hit_by: int=0
    landing_damage: int=0
    blink: bool=False
    linked: bool=False
    remove_on_attack: bool=False
    combo_until: int=0
    display_name: str=''

    @property
    def roles(self):return {a['role']:a for a in self.model['animations']}
    @property
    def animation(self):return self.roles[self.role]
    @property
    def descriptor(self):return self.animation['frames'][self.frame]
    @property
    def type(self):return self.model['stats'].get('type','none')
    @property
    def speed(self):return Fraction(self.model['behavior']['source_speed'])
    @property
    def inair(self):return abs(self.a-self.base)>=Fraction(1,10)

@dataclass
class World:
    actors: list=field(default_factory=list)
    time: int=0
    seed: int=1234567890
    new_attack_id: int=1
    camera: Fraction=Fraction(0)
    level_completed: bool=False
    events: list=field(default_factory=list)

    def spawn(self,model,*,x,z,a=0,health_override=0,flip=0,alias='',vertical=False):
        """Source smartspawn reference. Fractional paths remain non-certified.

        No name-based behavior selection: the already-parsed semantic driver
        controls dispatch. This is not a replacement for a production loader.
        """
        driver=model['behavior']['driver']
        if driver not in ('enemy_drop_then_ai','noncombat_horizontal_drift','none'):
            raise UnsupportedExecution('SPAWN_DRIVER: '+driver)
        slot=next((i for i in range(150) if not any(e.exists and e.slot==i for e in self.actors)),None)
        if slot is None:return None
        e=Actor(model,slot,x=Fraction(x)+int(self.camera),z=Fraction(z),a=Fraction(a),
                health=int(model['behavior'].get('default_health',0)),direction=flip,
                role='',nextthink=self.time+1,display_name=alias or model['stats'].get('name',''))
        self.actors.append(e);self.set_role(e,'idle')
        if health_override:e.health=health_override
        if driver=='enemy_drop_then_ai':
            e.driver='drop'
            if (vertical and -30<e.x<350) or 0<x<320:
                e.a=240+Fraction(self.random()%1000,25)
                self.events.append((self.time,'numeric_reference_only','spawn_drop'))
                if e.health<1:self.set_role(e,'fall');e.driver='fall'
        elif driver=='noncombat_horizontal_drift':
            e.xdir=(e.speed+Fraction(3*(self.random()%1000),1000))*(1 if x<160 else -1)
            e.driver='drift';self.set_role(e,'walk')
            self.events.append((self.time,'numeric_reference_only','drift_speed'))
        return e

    def random(self):
        self.seed,value=source_random32_step(self.seed)
        self.events.append((self.time,'random',value))
        return value

    def emit_frame(self,e):
        f=e.descriptor
        e.x+=f.get('move',0)*(1 if e.direction else -1)
        self.events.append((self.time,'frame',e.slot,e.role,e.frame))
        a=e.animation
        if 'sound' in a['properties'] or 'soundframe' in a['properties']:
            raise UnsupportedExecution('FRAME_SOUND_EVENT requires an audio event sink')

    def set_role(self,e,role,reset=False):
        if role not in e.roles:raise UnsupportedExecution('MISSING_ROLE: '+role)
        if role==e.role and not reset:return
        e.role=role;e.frame=0;e.animating=1
        if not reset:e.last_frame=-1
        e.nextanim=(self.time+e.descriptor['delay']*2)&0xffffffff
        self.emit_frame(e)

    def animation_tick(self,e):
        if e.nextanim!=self.time:return
        f=e.frame+e.animating
        if not 0<=f<len(e.animation['frames']):
            f=len(e.animation['frames'])-1 if f<0 else 0
            if not prop(e.animation,'loop',[0])[0]:
                e.animating=0
                if e.autokill:e.exists=False;return
        if e.animating:
            e.frame=f;e.nextanim=(self.time+e.descriptor['delay']*2)&0xffffffff
            self.emit_frame(e)

    def target(self,e):
        p=[a for a in self.actors if a.exists and a.type=='player'][:2]
        if not p:return None
        if len(p)==1:return p[0]
        d=[e.x-a.x for a in p]
        if d[0]*d[1]<0:return p[0] if (d[0]<0 if e.direction else d[0]>0) else p[1]
        return p[0] if abs(d[0])+abs(e.z-p[0].z)<abs(d[1])+abs(e.z-p[1].z) else p[1]

    def ranged(self,e,t,role):
        if role not in e.roles:return False
        lo,hi=prop(e.roles[role],'range',[-10,80])
        d=(t.x-e.x)*(1 if e.direction else -1)
        return lo<d<hi

    def move_enemy(self,e,x,z):
        # Fixture world is explicitly empty of holes/obstacles/grab targets.
        if 'throw' in e.roles or 'grab' in e.roles:
            raise UnsupportedExecution('WORLD_CONTACT_GRAB_THROW callbacks required')
        if not e.inair and not e.projectile:
            if e.zdir and e.z<160:e.zdir=e.speed/2
            if e.zdir and e.z>232:e.zdir=-e.speed/2
        e.x+=x;e.z+=z

    def think(self,e):
        d=e.driver
        if d=='none':return
        if d=='suicide':e.exists=False;return
        if d=='drift':
            if e.x<self.camera-80 or e.x>self.camera+400:e.exists=False
            else:e.x+=e.xdir
            return
        if d=='drop':
            if not e.inair:
                e.driver='enemy'
                if e.health<=0:e.exists=False
            return
        if d in ('pain','rise','throw','grab'):
            if e.animating:return
            if e.linked:raise UnsupportedExecution('LINKED_ACTOR_TRANSITION')
            e.driver='enemy';self.set_role(e,'idle')
            if d=='rise':e.xdir=e.zdir=Fraction(0)
            return
        if d=='lie':
            if e.health<=0:
                e.driver='suicide';e.nextthink=self.time+400;e.blink=True;return
            if self.time<e.stall:return
            self.set_role(e,'rise');e.xdir=e.zdir=Fraction(0);e.driver='rise';return
        if d=='fall':
            amount=Fraction(5,2) if e.projectile else Fraction(6,5)
            self.move_enemy(e,-amount if e.direction else amount,0)
            if e.inair:
                if e.a<-250 and e.health<=0:e.exists=False
                return
            if e.projectile:
                if e.landing_damage:self.damage(e,e,e.landing_damage,False,'attack')
                e.landing_damage=0;e.projectile=False
            if e.tossv<-2:self.toss(e,Fraction(1));return
            e.driver='lie';e.stall=self.time+200;return
        t=self.target(e)
        if d=='attack':
            e.attacking=True
            for event in ('throwframe','shootframe','jumpframe'):
                if e.frame!=e.last_frame and e.frame==prop(e.animation,event,[-1])[0]:
                    raise UnsupportedExecution('ANIMATION_EVENT: '+event)
            e.last_frame=e.frame
            if e.animating:return
            e.attacking=False;e.xdir=e.zdir=Fraction(0)
            if t and abs(e.x-t.x)<80 and self.random()&3:
                self.set_role(e,'walk');e.driver='runoff'
            else:self.set_role(e,'idle');e.driver='enemy'
            e.stall=self.time+200;return
        if not t:
            if d=='prepare':e.driver='enemy'
            return
        e.direction=int(e.x<t.x)
        if d=='prepare':
            if self.time<e.stall:return
            pick=[self.ranged(e,t,'attack'+str(i)) for i in (1,2,3)]
            if pick[1] and self.random()&31<10:pick[0]=False
            if pick[2] and self.random()&31<10:pick[1]=False
            for i,yes in enumerate(pick,1):
                if yes:self.set_role(e,'attack'+str(i));e.driver='attack';return
            e.driver='enemy';return
        if d=='runoff':
            e.xdir=-e.speed/2 if e.direction else e.speed/2
            self.move_enemy(e,e.xdir,0)
            if self.time>e.stall:e.driver='enemy'
            return
        if d!='enemy':raise UnsupportedExecution('UNKNOWN_DRIVER: '+d)
        if e.animating and e.role=='walk':
            e.animating=-1 if (e.xdir<0 if e.direction else e.xdir>0) else 1
        if abs(e.z-t.z)<12:
            if t.jumping and 'upper' in e.roles and 10<abs(t.x-e.x)<120:
                self.set_role(e,'upper');e.driver='attack';return
            if any(self.ranged(e,t,'attack'+str(i)) for i in (1,2,3)):
                self.set_role(e,'idle');e.driver='prepare';e.stall=self.time+50+self.random()%20;return
            if 150<abs(e.x-t.x)<200 and any(r in e.roles for r in ('jumpattack','jumpattack2')):
                raise UnsupportedExecution('JUMPATTACK_WORLD_LIFECYCLE')
        if e.stall<self.time:
            walk=0;e.xdir=e.zdir=Fraction(0);r=self.random()
            if r&7<3 or abs(e.x-t.x)>160:e.xdir=e.speed*(1 if e.direction else -1);walk=1
            elif r&7>4:e.xdir=e.speed/2*(-1 if e.direction else 1);walk=-1
            r=self.random()
            if r&7<2:e.zdir=-e.speed/2;walk|=1
            elif r&7>5:e.zdir=e.speed/2;walk|=1
            self.set_role(e,'walk' if walk else 'idle');e.stall=self.time+200
        self.move_enemy(e,e.xdir,e.zdir)

    def toss(self,e,lift):
        e.toss_time=self.time+1;e.tossv=lift;e.a+=Fraction(1,2)

    @staticmethod
    def rectangle(e, attack=False):
        f=e.descriptor
        box=f['attack']['box'] if attack else f['bbox']
        ox,oy=f['offset'];left,top=box[0]-ox,box[1]-oy
        right,bottom=left+box[2],top+box[3]
        # BOR truncates float anchors to int before adding corner offsets.
        x,y=int(e.x),int(e.z-e.a)
        return ((x+left,y+top,x+right,y+bottom) if e.direction else
                (x-right,y+top,x-left,y+bottom))

    def checkhit(self,e,t,counter=False):
        if e is t or abs(e.z-t.z)>12 or not all(t.descriptor['bbox'][2:]):return False
        if counter and t.descriptor.get('attack') is None:return False
        a=self.rectangle(e,True);b=self.rectangle(t,counter)
        return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]

    def do_attack(self,e):
        if self.level_completed:return
        if e.type=='player' or e.projectile:types=('player','enemy','obstacle')
        elif e.type=='enemy':types=('player',)
        else:return
        if not e.attack_id:
            self.new_attack_id=(self.new_attack_id+1)&0xffffffff
            if not self.new_attack_id:self.new_attack_id=1
            e.attack_id=self.new_attack_id
        attack=e.descriptor['attack'];hit=False
        for counter in (False,True) if e.role=='upper' else (False,):
            for t in self.actors:
                if not (t.exists and t.type in types and t.pain_until<self.time):continue
                if not counter and t.hit_by==e.attack_id:continue
                if not self.checkhit(e,t,counter):continue
                self.damage(t,e,attack['force'],True if counter else attack['drop'],attack['kind'])
                if not counter:t.hit_by=e.attack_id
                # These explicit output events require real media/audio/score sinks.
                self.events.append((self.time,'hit_flash',e.slot,t.slot))
                if e.type=='player':e.combo_until=self.time+100
                hit=True
        if hit:
            self.events.append((self.time,'hit_sound','indirect' if e.projectile else 'beat',100 if e.projectile else 105-attack['force']))
            if e.remove_on_attack:e.exists=False

    def damage(self,e,other,force,drop,kind):
        if e.type not in ('enemy','player'):raise UnsupportedExecution('DAMAGE_CALLBACK: '+e.type)
        if e.linked:raise UnsupportedExecution('DAMAGE_UNLINK_LIFECYCLE')
        if e.a<-250:raise UnsupportedExecution('PIT_DEATH_WORLD_LIFECYCLE')
        e.pain_until=self.time+40;e.attacking=False
        if e.x<other.x:e.direction=1
        elif e.x>other.x or e.type=='player':e.direction=0
        if e.type=='player':
            e.jumping=False;e.xdir=-e.xdir
            if other.type=='player':force=int(force/2)
        if kind=='blast':e.projectile=True;drop=True
        e.health-=force;self.events.append((self.time,'damage',e.slot,force,e.health))
        if other is e:return
        if drop or e.health<=0 or e.inair:
            lift=Fraction(3) if e.type=='player' else Fraction(5,2)+Fraction(self.random()%1000,1000)
            self.toss(e,lift);self.set_role(e,'fall',True)
            e.driver='fall' if e.type=='enemy' else 'player_fall'
        else:
            self.set_role(e,'pain',True);e.driver='pain' if e.type=='enemy' else 'player_pain'

    def tick(self):
        """Fixture convenience: advance clock, then execute that absolute tick.

        The source host's update-before-increment loop is run_interval below.
        This helper deliberately excludes an already-executed initial tick.
        """
        self.time=(self.time+1)&0xffffffff
        self.update_actors()

    def run_interval(self, elapsed, paused=False):
        if not isinstance(elapsed,int) or elapsed<0:raise ValueError('TIMER_INTERVAL')
        for _ in range(0 if paused else min(elapsed,100)):
            self.update_actors()
            # Scroller/game timer are explicit missing host dependencies.
            self.time=(self.time+1)&0xffffffff

    def update_actors(self):
        for e in self.actors:
            if e.exists and (e.tossv>0 or e.inair) and e.toss_time<=self.time:
                e.a+=e.tossv
                if e.tossv>-6:e.tossv-=Fraction(1,10)
                if e.a<=e.base:e.a=e.base
                e.toss_time=self.time+2
        for e in self.actors:
            if e.exists and e.driver!='none' and e.nextthink==self.time:
                e.nextthink=self.time+2;self.think(e)
        for e in self.actors:
            if e.exists:self.animation_tick(e)
        # Hit resolution is a separate all-actor pass, alternating slot parity.
        # Reference hit side effects are events, not claims of live media binding.
        for e in self.actors:
            if e.exists and e.slot%2==self.time%2:
                attack=e.descriptor.get('attack')
                if (e.attacking or e.projectile) and attack and attack['force']:
                    self.events.append((self.time,'attack',e.slot,e.role,e.frame,attack['force']))
                    self.do_attack(e)
                else:e.attack_id=0
