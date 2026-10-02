"""Build/run ONLY an isolated S5 CPU fixture; never rebuild/install production.

python tools/verify/actor_s5_isolated.py
Outputs are in a fresh out/actor_s5_isolated_* directory, including rejected
attempts. Requires local Poppy and Mesen. --build-only makes NO live claim.
One ModelIR per subject is parsed from the PAK, then lower_model/apply_policy
are consumed without changing compiler/profile code or certification status.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/bor_compile'))
from compiler import Source
from model_ir import parse_model
from actor_lowering import lower_model
from lowering_policy import Profile, apply_policy
from actor_frame_abi import pack_source_frame

BOR_COMMIT = 'eba02fe6c9e97e388126c51560a92024f406d8c0'
BOR_URL = f'https://raw.githubusercontent.com/Plombo/beatsofrage/{BOR_COMMIT}/BOR.C'
SCALE = 2560
RATE = 21477270  # Mesen Core/SNES/SnesConsole.cpp NTSC master clock rate.
TICKS = 200
KINDS = {'attack': 0, 'blast': 1, 'burn': 2, 'freeze': 3, 'shock': 4}


def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def protected():
    # Production artifacts plus source inputs placed outside our ownership.
    paths = [ROOT / 'build_rom.py', ROOT / 'src/main.pasm']
    paths += list((ROOT / 'tools/bor_compile').glob('*.py'))
    paths += [p for p in (ROOT / 'src/generated').rglob('*') if p.is_file()]
    paths += [ROOT / d / n for d in ('build', 'distribution')
              for n in ('bor.sfc', 'bor.msu') if (ROOT / d / n).exists()]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def word(n):
    if not -32768 <= n <= 65535:
        raise ValueError(f'word overflow: {n}')
    return n & 65535


def units(n):
    result = Fraction(n) * SCALE
    if result.denominator != 1 or not -(1 << 31) <= result < (1 << 31):
        raise ValueError(f'not exactly representable in isolated numeric ABI: {n}')
    return int(result)


def animation_loop(actor, role):
    animation=next(a for a in actor['animations'] if a['role']==role)
    values=animation['properties'].get('loop', [['0']])
    return int(values[-1][0])


def frame_bytes(frame, *, compat=False):
    if frame['source_binding'] is None:
        raise ValueError('historical source binding required')
    # Recompute from authored values; also check the current lowering output.
    x, y = frame['offset']
    bx, by, bw, bh = frame['bbox']
    body = [bx-x, by-y, bx-x+bw, by-y+bh]
    attack = frame['attack']
    if attack:
        ax, ay, aw, ah = attack['box']
        box = [ax-x, ay-y, ax-x+aw, ay-y+ah]
        force, drop, kind = attack['force'], attack['drop'], KINDS[attack['kind']]
    else:
        box, force, drop, kind = [0]*4, 0, 0, 0
    assert frame['source_binding']['body_corners'] == body
    assert frame['source_binding']['delay_ticks'] == frame['delay'] * 2
    assert frame['source_binding']['vulnerable'] == bool(bw and bh)
    if attack:
        assert frame['source_binding']['attack_corners'] == box
    values = [4 if compat else frame['delay']*2, int(bool(bw and bh)),
              *body, 4 if compat else force, drop, kind, *box, 0, 0, 0]
    return struct.pack('<16H', *map(word, values))


def put(offset, value):
    return f'    lda #${value & 65535:04X}\n    sta ${offset:02X}\n'


def put32(offset, value):
    return put(offset, value) + put(offset+2, value >> 16)


def pointer(offset, address):
    return put(offset, address & 65535) + put(offset+2, address >> 16)


def collision_expected(frame, target, params, compat=False):
    ax, az, aa, ad, tx, tz, ta, td, same = params
    if same:
        return 0
    if compat:
        return int(abs(ax-tx) < 32 and abs((az-aa)-(tz-ta)) < 64)
    if abs(az-tz) > 12 or not all(target['bbox'][2:]):
        return 0

    def world(box, offset, x, z, a, direction):
        l, t = box[0]-offset[0], box[1]-offset[1]
        r, b = l+box[2], t+box[3]
        return ((x+l, z-a+t, x+r, z-a+b) if direction else
                (x-r, z-a+t, x-l, z-a+b))

    a = world(frame['attack']['box'], frame['offset'], ax, az, aa, ad)
    b = world(target['bbox'], target['offset'], tx, tz, ta, td)
    return int(a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3])


class Fixture:
    def __init__(self):
        self.data = bytearray()
        self.code = []
        self.cases = []

    def table(self, frames, compat=False):
        addr = 0x018000 + len(self.data)
        exact=[pack_source_frame(frame) for frame in frames]
        assert exact==[frame_bytes(frame) for frame in frames], 'compiler ABI differs from authored-value oracle'
        blob = b''.join(frame_bytes(frame,compat=True) for frame in frames) if compat else b''.join(exact)
        if (addr & 65535) + len(blob) > 65536:
            raise ValueError('frame table crosses bank')
        self.data.extend(blob)
        return addr

    def case(self, name, setup, calls, expected, frame=None):
        i = len(self.cases)
        if i >= 128:
            raise ValueError('fixture result capacity')
        self.code += ['    jsr Fixture_Clear\n', setup]
        self.code += [f'    jsl {call}\n' for call in calls]
        self.code += [f'''    ldx #0
Fixture_Copy_{i}:
    .a16
    .i16
    lda $00,x
    sta.l ${0x7e4000+i*256:06X},x
    inx
    inx
    cpx #256
    bne Fixture_Copy_{i}
''']
        self.cases.append(dict(name=name, expected=expected,
                               frame_hex=None if frame is None else frame.hex()))


def build(folder, source_path):
    source = Source(source_path)
    subjects = {}
    for name in ('Kula', 'Lobster', 'Crab', 'Ramon'):
        # Names select golden subjects only, never runtime dispatch.
        ir = parse_model(source, f'data/chars/{name}/{name}.txt', name,
                         's5-isolated-fixture', 'historical-bor')
        subjects[name] = lower_model(ir)
    original = copy.deepcopy(subjects)
    kula = next(a['frames'] for a in subjects['Kula']['animations'] if a['role'] == 'attack1')
    lobster = next(a['frames'] for a in subjects['Lobster']['animations'] if a['role'] == 'fall')
    crab = next(a['frames'] for a in subjects['Crab']['animations'] if a['role'] == 'walk')
    assert [f['delay'] for f in kula] == [4, 4, 4, 4, 2, 2]
    assert [i for i, f in enumerate(kula) if f['attack'] and f['attack']['force']] == [2, 3]
    assert all(kula[i]['attack']['force'] == 5 for i in (2, 3))
    behavior = subjects['Crab']['behavior']
    assert behavior['type'] == 'none' and behavior['driver'] == 'noncombat_horizontal_drift'
    speed = units(behavior['source_speed'])

    # Explicit, user-approved golden CONTROL. Not a forged immutable delegate
    # certificate: the baseline string and report distinguish its narrow scope.
    accepted = dict(baseline='isolated-user-approved-Kula-control',
        source_identity=subjects['Kula']['source_identity'],
        source_sha256=subjects['Kula']['source_sha256'], runtime_id=0,
        animations={'attack1': dict(delay=4, geometry='fixed accepted control')},
        contract=dict(damage=4, collision=[32,64], behavior='host attack-state flag',
                      stats='unbound', effects='unbound', palettes='unbound'))
    exact = apply_policy(subjects['Kula'], Profile.SOURCE_EXACT)
    compat = apply_policy(subjects['Kula'], Profile.ACCEPTED_COMPAT, accepted=accepted)
    assert exact['source_fingerprint'] == compat['source_fingerprint']
    assert exact['status'] == compat['status'] == 'BLOCKED'

    f = Fixture()
    kp, lp, cp = f.table(kula), f.table(lobster), f.table(crab)
    ap = f.table(kula, compat=True)
    zero = copy.deepcopy(kula[:1]); zero[0]['delay'] = 0
    zero[0]['source_binding']['delay_ticks'] = 0
    zp = f.table(zero)

    def setup(table, count, index=0, flags=1, policy=1):
        return pointer(0, table) + put(4,count) + put(6,index) + put(8,flags) + put(0xe0,policy)

    for name, frames, table in [('kula',kula,kp), ('lobster',lobster,lp)]:
        indices = range(6) if name == 'kula' else (0,1,len(frames)-1)
        for i in indices:
            for flags in (0,1,2,4):
                force = (frames[i]['attack'] or {}).get('force',0)
                f.case(f'{name}_frame{i}_flags{flags}', setup(table,len(frames),i,flags),
                       ['S5_LoadFrame','S5_ActivateAttack'],
                       {0x0a:int(bool((flags & 3) and force)), 0x0c:1, 0x4c:force, 0x2c:0},
                       frame_bytes(frames[i]))
    for i in range(6):
        f.case(f'compat_kula_frame{i}',setup(ap,6,i,1,2),
               ['S5_LoadFrame','S5_ActivateAttack'],{0x0a:1,0x4c:4,0x40:4},frame_bytes(kula[i],compat=True))
    for name, count, index, policy in [('past_end',6,6,1),('negative',6,65535,1),
                                      ('empty',0,0,1),('invalid_policy',6,2,0)]:
        f.case(name,setup(kp,count,index,1,policy),['S5_LoadFrame','S5_ActivateAttack'],
               {0x0a:0,0x0c:0,0x2c:1},bytes(32))

    # Independent geometry oracle reads authored boxes, not emitted descriptors
    # or actor_lowering.attack_at. Edge/depth and both facing signs included.
    geometries = [
        ('overlap', (100,200,0,1,144,200,0,1,0), kp, kula[0]),
        ('touch_x', (100,200,0,1,163,200,0,1,0), kp, kula[0]),
        ('miss_x', (100,200,0,1,164,200,0,1,0), kp, kula[0]),
        ('left', (100,200,0,0,73,200,0,1,0), kp, kula[0]),
        ('target_left', (100,200,0,1,160,200,0,0,0), kp, kula[0]),
        ('depth12', (100,200,0,1,144,212,0,1,0), kp, kula[0]),
        ('depth13', (100,200,0,1,144,213,0,1,0), kp, kula[0]),
        ('depth_minus13', (100,200,0,1,144,187,0,1,0), kp, kula[0]),
        ('altitude_miss', (100,200,0,1,144,200,120,1,0), kp, kula[0]),
        ('same_entity', (100,200,0,1,144,200,0,1,1), kp, kula[0]),
        ('zero_body', (100,200,0,1,144,200,0,1,0), lp, lobster[0]),
        ('negative_world', (-100,200,0,1,-56,200,0,1,0), kp,kula[0]),
        ('different_body_frame', (100,200,0,1,160,200,0,1,0), kp+5*32,kula[5]),
    ]
    for name, params, tp, target in geometries:
        state = setup(kp,6,2) + pointer(0x26,tp)
        state += ''.join(put(0x14+2*i,v) for i,v in enumerate(params))
        expected = collision_expected(kula[2],target,params)
        f.case('box_'+name,state,['S5_LoadFrame','S5_ActivateAttack','S5_CheckCollision'],{0x2a:expected})
    for dx,dy in [(31,63),(32,63),(31,64),(-31,-63),(-32,0),(0,-64)]:
        params = (100,200,0,1,100+dx,200+dy,0,1,0)
        state=setup(ap,6,0,1,2)+put(0xe2,1)+pointer(0x26,lp)
        state+=''.join(put(0x14+2*i,v) for i,v in enumerate(params))
        f.case(f'compat_box_{dx}_{dy}',state,
               ['S5_LoadFrame','S5_ActivateAttack','S5_CheckCollision'],
               {0x2a:collision_expected(kula[0],lobster[0],params,True)})
    f.case('zero_delay_not_coerced',setup(zp,1),
           ['S5_AnimationBegin','S5_AnimationTick'],{0x06:0,0x0e:0,0x10:1,0x40:0,0xd0:1,0xd4:0})
    for animation in subjects['Ramon']['animations']:
        frames=animation['frames']
        assert len(frames)==1 and frames[0]['delay']==0 and frames[0]['bbox']==[0,0,0,0]
        rp=f.table(frames)
        f.case('ramon_'+animation['role'],setup(rp,1)+put32(0xd0,12345),
               ['S5_AnimationBegin']+['S5_AnimationTick']*3,
               {0x06:0,0x0e:0,0x10:1,0x42:0,0x0a:0,0xd0:12348,0xd4:12345})
    f.case('absolute_deadline_u32_wrap',setup(kp,6)+put32(0xd0,0xfffffffc),
           ['S5_AnimationBegin']+['S5_AnimationTick']*8,
           {0x06:1,0x0e:8,0xd0:4,0xd2:0,0xd4:12,0xd6:0})
    f.case('loop_per_frame_delays',setup(kp,6,5)+put(0x12,1),
           ['S5_AnimationBegin']+['S5_AnimationTick']*4,{0x06:0,0x0e:8,0x10:1})

    def drift(x, authored, sample, camera=0, kind=0, walk=1):
        return (put(0xe0,1)+put32(0xa0,units(x))+put32(0xa8,units(camera))+
                put32(0xac,speed)+put(0xb0,authored)+put(0xb2,kind)+put(0xb4,walk)+
                put(0xe8,sample)+put(8,3)+put(0xbc,123))

    for name,x,auth,sample,camera,steps in [
        ('sample0',100,159,0,0,2), ('sample_mid',100,160,3840,0,2),
        ('sample_max',100,-1,7679,0,2), ('lower_edge',-80,160,0,0,2),
        ('upper_edge',400,0,0,0,2), ('below',-80-Fraction(1,SCALE),0,0,0,1),
        ('above',400+Fraction(1,SCALE),160,0,0,1),
        ('camera_lower',920,160,3840,1000,2), ('camera_upper',1400,0,3840,1000,2)]:
        velocity=(speed+sample)*(1 if auth<160 else -1)
        position,alive=units(x),1
        for _ in range(steps):
            if alive:
                if position<units(camera-80) or position>units(camera+400): alive=0
                else: position+=velocity
        f.case('drift_'+name,drift(x,auth,sample,camera),
               ['S5_DriftBind','S5_DriftBind']+['S5_DriftTick']*steps,
               {0xa0:position & 65535,0xa2:(position>>16)&65535,
                0xa4:velocity&65535,0xa6:(velocity>>16)&65535,
                0xb6:alive,0xb8:1,0xba:int(auth<160),0xbc:0,8:0,0xea:1})
    for name,kind,walk,sample,calls in [('non_none',2,1,0,0),('no_walk',0,0,0,0),('bad_rng',0,1,7680,1)]:
        f.case('drift_'+name,drift(100,0,sample,kind=kind,walk=walk),
               ['S5_DriftBind','S5_DriftTick'],{0xb8:0,0xb6:0,0x2c:2,0xea:calls})

    for name,rate,delta,remainder,calls,count,rem,error in [
        ('one_second_200_ticks',RATE,RATE*100,0,2,200,0,0),
        ('sub_tick',RATE,RATE-1,0,1,0,RATE-1,0),
        ('carry_to_next_tick',RATE,RATE-1,1,1,1,0,0),
        ('zero_rate',0,123,0,1,0,0,1),
        ('invalid_remainder',RATE,0,RATE,1,0,RATE,1),
        ('overflow',RATE,0xffffffff,1,1,0,1,2)]:
        state=put32(0,delta)+put32(4,remainder)+put32(8,rate)
        state+='    lda #1\n    sta.l $7E2040\n'
        f.case('clock_'+name,state,['S5_ClockAdvance']*calls,
               {0x0c:count,0x0e:0,4:rem&65535,6:rem>>16,0x16:error,0x18:count})

    # Live contexts: 1100 exact Kula, 1200 Crab, 1300 clock, 1400 compat Kula,
    # 1500 separate Crab WALK timing probe (continues after the drift actor dies).
    # Runtime frame updates and snapshots execute entirely inside this ROM.
    live_init = ('    lda #0\n    sta.l $7E2040\n'+
                 '    lda #$1100\n    tcd\n    jsr Fixture_Clear\n'+setup(kp,6)+
                 '    jsl S5_AnimationBegin\n    lda #$1200\n    tcd\n    jsr Fixture_Clear\n'+
                 setup(cp,len(crab))+put(0x12,animation_loop(subjects['Crab'],'walk'))+drift(390,0,3840)+
                 '    jsl S5_DriftBind\n    jsl S5_AnimationBegin\n'+
                 '    lda #$1500\n    tcd\n    jsr Fixture_Clear\n'+setup(cp,len(crab))+
                 put(0x12,animation_loop(subjects['Crab'],'walk'))+'    jsl S5_AnimationBegin\n'+
                 '    lda #$1400\n    tcd\n    jsr Fixture_Clear\n'+setup(ap,6,0,1,2)+
                 '    jsl S5_AnimationBegin\n    lda #$1300\n    tcd\n    jsr Fixture_Clear\n'+
                 put32(8,RATE))
    runtime=ROOT/'src/core/actor_s5_isolated.pasm'
    clock=ROOT/'src/core/actor_s5_clock_isolated.pasm'
    # First vblank synchronizes the epoch; subsequent NMI intervals use the
    # departing frame's real odd/even bit ($213F), including short scanline.
    # ScreenInterlace=0, NTSC, no emulator overclock required by this fixture.
    asm=f'''.snes
.bank 0
.org $8000
Fixture_Reset:
    sei
    clc
    xce
    rep #$38
    .a16
    .i16
    lda #$1FFF
    tcs
    lda #0
    pha
    plb
    plb
    sep #$20
    .a8
    lda #$80
    sta $2100
    stz $4200
    stz $2133
    rep #$30
    .a16
    .i16
    ldx #0
    lda #0
Fixture_ClearResults:
    .a16
    .i16
    sta.l $7E2000,x
    inx
    inx
    cpx #$C000
    bne Fixture_ClearResults
    lda #$1000
    tcd
{''.join(f.code)}
{live_init}
    lda #$5335
    sta.l $7E2000
    lda #{len(f.cases)}
    sta.l $7E2002
; BUILD_ID_STORES
    sep #$20
    .a8
    lda #$80
    sta $4200
    rep #$30
    .a16
    .i16
Fixture_Main:
    .a16
    .i16
    wai
    bra Fixture_Main

Fixture_Clear:
    .a16
    .i16
    ldx #254
    lda #0
Fixture_ClearLoop:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl Fixture_ClearLoop
    rts

S5_HostRandom03:
    rep #$30
    .a16
    .i16
    inc $EA
    lda $E8
    sta $BE
    rtl

Fixture_Nmi:
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phd
    sep #$20
    .a8
    lda $4210
    rep #$30
    .a16
    .i16
    lda #$1300
    tcd
    lda $10
    bne Fixture_Nmi__interval
    inc $10
    brl Fixture_Nmi__parity
Fixture_Nmi__interval:
    .a16
    .i16
    lda $12
    cmp #70
    bcc Fixture_Nmi__advance
    brl Fixture_Nmi__done
Fixture_Nmi__advance:
    .a16
    .i16
    inc $12
    lda $12
    sta.l $7E2004
    ; Clock delta is integer master cycles, scaled by the source rate 200.
{put32(0,357368*200)}
    lda $14
    beq Fixture_Nmi__clock
    lda $00
    sec
    sbc #800
    sta $00
    lda $02
    sbc #0
    sta $02
Fixture_Nmi__clock:
    .a16
    .i16
    jsl S5_ClockAdvance
    lda $0C
    sta.l $7E2006
    lda $04
    sta.l $7E2008
    lda $06
    sta.l $7E200A
    ; Accepted available-animation-tick control: one per fixture vblank.
    lda #$1400
    tcd
    jsl S5_AnimationTick
    lda #$1300
    tcd
    lda $12
    asl a
    asl a
    asl a
    asl a
    tax
    lda $0C
    sta.l $7EC000,x
    lda $04
    sta.l $7EC002,x
    lda $06
    sta.l $7EC004,x
    lda $14
    sta.l $7EC006,x
    lda $1406
    sta.l $7EC008,x
    lda $140E
    sta.l $7EC00A,x
    lda $1410
    sta.l $7EC00C,x
Fixture_Nmi__parity:
    .a16
    .i16
    sep #$20
    .a8
    lda $213F
    and #$80
    rep #$20
    .a16
    and #$00FF
    sta $14
Fixture_Nmi__done:
    .a16
    .i16
    pld
    ply
    plx
    pla
    rti

S5_HostSourceTick:
    rep #$30
    .a16
    .i16
    lda.l $7E2040
    beq Fixture_SourceTick__live
    inc $18
    rtl
Fixture_SourceTick__live:
    .a16
    .i16
    phd
    lda $0C
    sta.l $7E2010
    lda #$1100
    tcd
    jsl S5_AnimationTick
    lda #$1200
    tcd
    lda $B6
    beq Fixture_SourceTick__walk
    jsl S5_AnimationTick
    lda.l $7E2010
    and #1
    bne Fixture_SourceTick__walk
    jsl S5_DriftTick
Fixture_SourceTick__walk:
    .a16
    .i16
    lda #$1500
    tcd
    jsl S5_AnimationTick
Fixture_SourceTick__log:
    .a16
    .i16
    lda.l $7E2010
    cmp #240
    bcs Fixture_SourceTick__done
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $7E2010
    sta.l $7E2100,x
    lda $1106
    sta.l $7E2102,x
    lda $110E
    sta.l $7E2104,x
    lda $110A
    sta.l $7E2106,x
    lda $114C
    sta.l $7E2108,x
    lda $1110
    sta.l $7E210A,x
    lda $12A0
    sta.l $7E210C,x
    lda $12A2
    sta.l $7E210E,x
    lda $12B6
    sta.l $7E2110,x
    lda $12EA
    sta.l $7E2112,x
    lda $1206
    sta.l $7E2114,x
    lda $120E
    sta.l $7E2116,x
    lda $1208
    sta.l $7E2118,x
    lda $12BC
    sta.l $7E211A,x
    lda $1506
    sta.l $7E211C,x
    lda $150E
    sta.l $7E211E,x
Fixture_SourceTick__done:
    .a16
    .i16
    pld
    rtl

.include "{runtime.as_posix()}"
.include "{clock.as_posix()}"
.org $FFC0
    .db "S5 ISOLATED CPU PROOF "
    .db $20,$00,$06,$00,$01,$00,$00
    .dw $FFFF,$0000
.org $FFE0
    .dw 0,0,Fixture_Trap,Fixture_Trap,0,Fixture_Nmi,0,Fixture_Trap
    .dw 0,0,Fixture_Trap,0,0,Fixture_Nmi,Fixture_Reset,Fixture_Trap
.bank 1
.org $8000
Fixture_Descriptors:
'''
    asm+='\n'.join('    .db '+','.join(f'${b:02X}' for b in f.data[i:i+16])
                   for i in range(0,len(f.data),16))+'\n'
    # Trap lives before vector area in bank 0; hard failures leave no PASS.
    asm=asm.replace('.org $FFC0','Fixture_Trap:\n    stp\n.org $FFC0')
    build_id=hashlib.sha256(asm.encode()+runtime.read_bytes()+clock.read_bytes()).digest()
    identity=''.join(f'    lda #${value:04X}\n    sta.l ${0x7e2020+i*2:06X}\n'
                     for i,value in enumerate(struct.unpack('<16H',build_id)))
    asm=asm.replace('; BUILD_ID_STORES',identity)
    pasm=folder/'fixture.pasm'
    pasm.write_text(asm,encoding='utf-8')
    assert subjects == original, 'fixture mutated shared source descriptors'
    (folder/'descriptors.json').write_text(json.dumps(subjects,indent=2)+'\n')
    (folder/'cases.json').write_text(json.dumps(f.cases,indent=2)+'\n')
    dotnet=os.environ.get('DOTNET_EXE',r'C:\Users\chad\.dotnet\dotnet.exe')
    poppy=os.environ.get('POPPY_DLL',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')
    result=subprocess.run([dotnet,poppy,str(pasm),'-s',str(folder/'fixture.sym')],
                          capture_output=True,text=True)
    (folder/'poppy.log').write_text(result.stdout+result.stderr)
    if result.returncode or 'warning' in (result.stdout+result.stderr).lower():
        raise RuntimeError('Poppy failed or warned: '+result.stdout+result.stderr)
    blob=bytearray((folder/'fixture.bin').read_bytes())
    assert blob[0] == 0x78 and blob[0x8000:0x8000+len(f.data)] == f.data
    assert len(blob)<=65536
    blob.extend(bytes(65536-len(blob)))
    # Fill LoROM checksum/complement after all vectors/data/padding exist.
    blob[0x7fdc:0x7fe0]=b'\xff\xff\x00\x00'
    checksum=sum(blob)&65535
    struct.pack_into('<HH',blob,0x7fdc,checksum^65535,checksum)
    rom=folder/'fixture.sfc';rom.write_bytes(blob)
    audit=subprocess.run([sys.executable,str(ROOT/'tools/rom_audit/check_label_drift.py'),
                          '--pasm',str(pasm),'--sym',str(folder/'fixture.sym'),
                          '--bin',str(folder/'fixture.bin')],capture_output=True,text=True)
    (folder/'label_audit.log').write_text(audit.stdout+audit.stderr)
    if audit.returncode:
        raise RuntimeError('isolated label audit failed: '+audit.stdout+audit.stderr)
    return dict(cases=f.cases,rom=rom,speed=speed,crab_count=len(crab),build_id=build_id,
        metadata=dict(source_url=BOR_URL,source_sha256={k:v['source_sha256'] for k,v in subjects.items()},
                      source_fingerprint=exact['source_fingerprint'],
                      profiles={p['profile']:dict(status=p['status'],blockers=p['blockers']) for p in (exact,compat)},
                      compatibility_control=accepted, numeric_units_per_pixel=SCALE,
                      random_binding='host supplies one sample in integer [0,7680); RNG algorithm/distribution unproven',
                      rom_sha256=sha(rom),poppy_sha256=sha(poppy),
                      fixture_build_id=build_id.hex(),
                      runtime_sha256={p.name:sha(p) for p in (runtime,clock)}))


def verify_live(folder, built):
    from _harness import McpSession, MESEN_EXE, _free_tcp_port, run_frames_exact
    with McpSession(rom=built['rom'],mesen=MESEN_EXE,port=_free_tcp_port(),boot_wait=1.0,
                    stderr_log=folder/'mesen.log') as m:
        m.reset_emulator()
        run_frames_exact(m,100)
        m.pause()
        # A single large, explicit bus read avoids documented stale tiny reads.
        ram=m.read_memory('snesMemory',0x7e0000,65536)
        (folder/'wram.bin').write_bytes(ram)
        ppu=m.get_ppu_state()
        (folder/'ppu.json').write_text(json.dumps(ppu,indent=2)+'\n')
        (folder/'emulator_state.json').write_text(json.dumps(m.get_state(),indent=2)+'\n')
    def u16(offset): return struct.unpack_from('<H',ram,offset)[0]
    assert u16(0x2000)==0x5335, f'fixture did not complete reset tests: {ram[0x2000:0x2020].hex()}'
    assert u16(0x2002)==len(built['cases'])
    assert ram[0x2020:0x2040]==built['build_id'],'executed ROM build identity differs'
    assert u16(0x2004)==70, 'live clock did not finish 70 vblank intervals'
    rows=[]
    for i,case in enumerate(built['cases']):
        base=0x4000+i*256
        for offset,expected in case['expected'].items():
            actual=u16(base+offset)
            assert actual==expected, f"{case['name']} DP {offset:02x}: {actual} != {expected}"
        if case['frame_hex'] is not None:
            assert ram[base+0x40:base+0x60].hex()==case['frame_hex'],case['name']+' descriptor mismatch'
        rows.append(dict(name=case['name'],status='PASS'))

    # Clock oracle: integer elapsed master clocks, independently accumulated
    # from the hardware parity captured by the NMI (not a nominal 60Hz ratio).
    elapsed=0
    frame_rows=[]
    for interval in range(1,71):
        b=0xc000+interval*16
        parity=u16(b+6)
        assert parity in (0,128)
        if interval>1: assert parity!=frame_rows[-1]['parity']
        elapsed += (357368-(4 if parity else 0))*200
        ticks,rem=divmod(elapsed,RATE)
        assert u16(b)==ticks, f'200Hz clock count at interval {interval}'
        assert u16(b+2)+(u16(b+4)<<16)==rem, f'200Hz clock remainder at interval {interval}'
        compat_frame=min(interval//4,5)
        compat_remaining=0 if interval>=24 else 4-interval%4
        assert (u16(b+8),u16(b+10),u16(b+12))==(compat_frame,compat_remaining,int(interval<24))
        frame_rows.append(dict(interval=interval,parity=parity,source_ticks=ticks,remainder=rem))
    total=frame_rows[-1]['source_ticks']
    assert total<240 and u16(0x2006)==total
    trace=[]
    pos,alive=units(390),1
    deadlines=[8,16,24,32,36,40]
    for tick in range(1,total+1):
        b=0x2100+tick*32
        frame=min(sum(tick>=end for end in deadlines),5)
        remaining=max(0,deadlines[frame]-tick)
        active=int(frame in (2,3))
        if tick%2==0 and alive:
            if pos<units(-80) or pos>units(400): alive=0
            else: pos+=built['speed']+3840
        expected=(tick,frame,remaining,active,5 if active else 0,int(tick<40),
                  pos&65535,(pos>>16)&65535,alive,1)
        actual=struct.unpack_from('<10H',ram,b)
        assert actual==expected, f'live source tick {tick}: {actual} != {expected}'
        # The drift actor stops updating when dead. A separate live animation
        # probe proves all eight WALK frames and looping beyond 112 ticks.
        assert (u16(b+20),u16(b+22))==(0,14-min(tick,12))
        assert (u16(b+28),u16(b+30))==((tick//14)%built['crab_count'],14-tick%14)
        assert u16(b+24)==u16(b+26)==0
        trace.append(dict(tick=tick,kula_frame=frame,remaining=remaining,active=active,
                          force=5 if active else 0,crab_x_units=pos,crab_alive=alive))
    (folder/'live_trace.json').write_text(json.dumps(dict(vblanks=frame_rows,ticks=trace),indent=2)+'\n')
    return dict(status='PASS',emulator_sha256=sha(MESEN_EXE),static_live_cases=rows,
                logical_source_hz=200,logical_think_hz=100,vblank_intervals=70,source_ticks=total,
                kula_transition_ticks=deadlines,crab_first_outside_tick=10,crab_removed_tick=12,
                cpu_execution=True,organic_spawn_proof=False,graphics_proof=False,
                real_hardware_proof=False,source_float_rng_equivalence=False,
                full_source_actor_certificate=False,immutable_compat_delegate_certificate=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    parser.add_argument('--build-only',action='store_true')
    args=parser.parse_args()
    folder=Path(tempfile.mkdtemp(prefix='actor_s5_isolated_',dir=ROOT/'out'))
    before=protected()
    report=dict(status='INCOMPLETE',output=str(folder),protected_before=before)
    print(f'Isolated output: {folder}',flush=True)
    try:
        built=build(folder,args.source)
        report.update(built['metadata'])
        report['proof']={'status':'NOT_RUN'} if args.build_only else verify_live(folder,built)
        report['status']='BUILD_ONLY' if args.build_only else 'PASS'
    except Exception as exc:
        report.update(status='FAIL',error=repr(exc))
        raise
    finally:
        after=protected()
        report['protected_after']=after
        report['protected_unchanged']=before==after
        report['shared_source_concurrency']='main coordinator and Kepler may edit compiler/main/generated; differences are observations, not fixture attribution'
        report['shared_source_changes']=[p for p in before if before[p]!=after.get(p)]
        report['production_artifacts_unchanged']=all(before[p]==after.get(p)
            for p in before if p.startswith(('build\\','distribution\\','build/','distribution/')))
        (folder/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
        print(f"{report['status']}: {folder / 'proof.json'}",flush=True)
        if before!=after:
            # Concurrent owner work is reported, never reverted or overwritten.
            print('Protected inputs changed during run; compare hashes for concurrent-owner changes.',flush=True)


if __name__=='__main__':
    main()
