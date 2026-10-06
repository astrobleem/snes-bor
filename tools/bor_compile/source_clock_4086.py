"""4086 SDL timer policy mapped to an explicit NTSC hardware-field epoch.

The source polls integer milliseconds and uses five-ms blocks at GAME_SPEED
200. The target samples its own NTSC, non-interlace field boundaries. This is
an explicit clock/observation adaptation, not PC SDL wall-time equivalence.
Short fields cost four fewer master clocks. Backlog limits and pause consumption
come from pinned getinterval/update; logical time advances only at tick commit.
"""
from dataclasses import dataclass
from source_world_clock import MASTER_HZ
from dialect_4086 import GAME_SPEED,ENGINE_COMMIT

FIELD_CLOCKS=262*1364
SHORT_CLOCKS=4
READY=0xb4c5
INITIALIZED=0xb4c6
ADDRESS=0x7ffa00
FIRST_UNUSED=0x7ffa50


def cap_interval(ticks):
    if ticks>GAME_SPEED:return 1
    return min(ticks,GAME_SPEED//4)


def credits():
    return [divmod(FIELD_CLOCKS*GAME_SPEED*(1<<bit),MASTER_HZ) for bit in range(16)]


def emit():
    # Separate labels preserve each column's ROM bank in Poppy. Arithmetic on
    # a banked label can lose its bank, unlike arithmetic on literal equates.
    lines=[]
    short=[divmod(SHORT_CLOCKS*GAME_SPEED*(1<<bit),MASTER_HZ) for bit in range(16)]
    for prefix,rows in [('Credit',credits()),('ShortCredit',short)]:
        columns=[('TicksLo',[q&65535 for q,r in rows]),('TicksHi',[q>>16 for q,r in rows]),
                 ('RemainderLo',[r&65535 for q,r in rows]),('RemainderHi',[r>>16 for q,r in rows])]
        for name,values in columns:
            lines += ['SourceClock4086_'+prefix+name+':','    .dw '+','.join('$%04X'%v for v in values)]
    return '\n'.join(lines)+'\n'


@dataclass
class Clock:
    fields:int=0
    shorts:int=0
    phase:int=0
    due:int=0
    time:int=0

    def observe(self,fields,shorts,running=True):
        if self.due:raise ValueError('SOURCE_CLOCK_TICK_PENDING')
        delta=(fields-self.fields)&0xffffffff
        shortened=(shorts-self.shorts)&0xffffffff
        if delta>=32768 or shortened>delta:raise ValueError('SOURCE_CLOCK_OBSERVATION_DOMAIN')
        total=self.phase+(delta*FIELD_CLOCKS-shortened*SHORT_CLOCKS)*GAME_SPEED
        ticks,self.phase=divmod(total,MASTER_HZ)
        self.fields,self.shorts=fields,shorts
        self.due=cap_interval(ticks) if running else 0
        return self.due

    def commit(self):
        if not self.due:raise ValueError('SOURCE_CLOCK_NO_TICK')
        self.due-=1;self.time=(self.time+1)&0xffffffff
        return self.time
