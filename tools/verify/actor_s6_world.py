"""Native source pass-order test. Host hooks log calls; not live AI/physics proof."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import itertools

from actor_s5_isolated import ROOT, Source, parse_model, lower_model, frame_bytes, put, pointer, sha
from source_actor_link import link_world_contexts
from actor_s5_entity_fixture import symbols


def main():
    folder=Path(tempfile.mkdtemp(prefix='actor_s6_world_',dir=ROOT/'out'))
    print(folder,flush=True)
    source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    model=lower_model(parse_model(source,'data/chars/kula/kula.txt','Kula','s6-world-control','historical-bor'))
    frames=next(a['frames'] for a in model['animations'] if a['role']=='attack1')
    data=b''.join(frame_bytes(f) for f in frames)
    roleptr=0x18000+len(data)
    data+=struct.pack('<HHHBB8x',1,len(frames),0x8000,1,0)
    data+=struct.pack('<HHHBB8x',2,len(frames),0x8000,1,1)
    slotptr=0x18000+len(data)
    slots,layout=link_world_contexts([0x1000,None,0x1200,0x1300],world_address=0x1800,table_address=slotptr,
                                   reserved_regions=[(0x1900,0x1F00)])
    data+=slots
    code=[];cases=[]
    def add(s):code.append(s+'\n')
    def dp(n):add(f'    lda #${n:04X}\n    tcd')
    def call(n):add('    jsl '+n)
    def run(name,tick,events,error=0):
        dp(0x1800);add(put(0x3C,tick));add('    lda #0\n    sta.l $7E2040')
        call('S6_UpdateWorld')
        index=len(cases);base=0x7E4000+index*128
        add(f'    lda $3A\n    sta.l ${base:06X}\n    lda.l $7E2040\n    sta.l ${base+2:06X}')
        for i in range(len(events)):
            add(f'    lda.l ${0x7E7000+2*i:06X}\n    sta.l ${base+4+2*i:06X}')
        cases.append(dict(name=name,base=base-0x7E0000,error=error,events=events))
    for actor in (0x1000,0x1200,0x1300):
        dp(actor)
        for off,val in ((0xE0,1),(0xF6,1),(0xE4,65535),(0xE6,1),(0xCC,1),(0x1A,1),(0xE8,8)):
            add(put(off,val))
        add(pointer(0xC8,roleptr));add('    lda #1');call('S6_SetRole')
    dp(0x1800);add(pointer(0x30,slotptr));add(put(0x34,4));add(put(0x40,1))
    def ev(p,actors=(0x10,0x12,0x13)):return [p*256+a for a in actors]
    run('all-pass-order-even',8,ev(0)+ev(1)+ev(2)+ev(3)+ev(4,(0x10,0x12))+ev(5))
    run('odd-slot-parity-with-hole',9,ev(0)+ev(1)+ev(4,(0x13,))+ev(5))
    dp(0x1300);add(put(0xC6,1))
    run('think-removal-excluded-from-later-passes',10,ev(0)+ev(1)+ev(2)+ev(4,(0x10,0x12))+ev(5,(0x10,0x12)))
    dp(0x1800);add(put(0x40,0))
    run('no-level-skips-lost-and-gravity',16,ev(3,(0x10,0x12))+ev(4,(0x10,0x12))+ev(5,(0x10,0x12)))
    dp(0x1200);add(put(0xE0,2))
    run('policy-preflight-before-any-callback',17,[],1)
    dp(0x1200);add(put(0xE0,1))
    dp(0x1800);add(put(0x34,151))
    run('source-slot-limit-fail-closed',17,[],9)
    dp(0x1800);add(put(0x34,4));add(put(0x40,1))
    dp(0x1000);add(put(0xC4,1))
    run('callback-error-stops-subsequent-passes',17,ev(0,(0x10,0x12))+ev(1,(0x10,)),123)
    target_cases=[]
    dp(0x1800);add(put(0x44,0x1200));add(put(0x46,0x1300))
    target_grid=list(itertools.product((-16,0,16),(-16,0,16),(-16,0,16),(0,1)))
    target_grid+=list(itertools.product((-8192,8191),(-8192,8191),(-8192,8191),(0,1)))
    for sx,p0x,p1x,direction in target_grid:
        sz,p0z,p1z=0,4,-4
        for actor,x,z in ((0x1000,sx,sz),(0x1200,p0x,p0z),(0x1300,p1x,p1z)):
            dp(actor);add(put(0x14,x&65535));add(put(0x16,z&65535))
        dp(0x1000);add(put(0xFC,0));add(put(0x36,0x1800));add(put(0x1A,direction))
        call('S6_SelectTarget')
        dx0,dx1=sx-p0x,sx-p1x
        if dx0*dx1<0:
            first=dx0<0 if direction else dx0>0
        else:
            first=abs(dx0)+abs(sz-p0z)<abs(dx1)+abs(sz-p1z)
        base=0x5000+len(target_cases)*4
        add(f'    lda $34\n    sta.l ${0x7E0000+base:06X}\n    lda $FC\n    sta.l ${0x7E0002+base:06X}')
        target_cases.append(dict(inputs=[sx,sz,p0x,p0z,p1x,p1z,direction],base=base,
                                 target=0x1200 if first else 0x1300,error=0))
    for p0,p1,sx,expected,error in (
        (0,0,0,0,0),(0,0x1300,0,0x1300,0),(0x1200,0,0,0x1200,0),
        (0x1201,0,0,0,9),(0,0x1F00,0,0,9),
        (0x1200,0x1300,8192,0,10),(0x1200,0x1300,-8193,0,10)):
        dp(0x1800);add(put(0x44,p0));add(put(0x46,p1))
        dp(0x1000);add(put(0xFC,0));add(put(0x14,sx&65535))
        call('S6_SelectTarget')
        base=0x5000+len(target_cases)*4
        add(f'    lda $34\n    sta.l ${0x7E0000+base:06X}\n    lda $FC\n    sta.l ${0x7E0002+base:06X}')
        target_cases.append(dict(inputs=dict(players=[p0,p1],self_x=sx),base=base,
                                 target=expected,error=error))
    lifecycle_cases=[]
    def life_snapshot(name,reads,expected):
        base=0x6000+len(lifecycle_cases)*32
        for i,address in enumerate(reads):
            add(f'    lda.l ${address:06X}\n    sta.l ${0x7E0000+base+2*i:06X}')
        lifecycle_cases.append(dict(name=name,base=base,expected=expected))
    for actor,hp in ((0x1000,20),(0x1200,0),(0x1300,10)):
        dp(actor)
        for off,value in ((0xE0,1),(0xFC,0),(0xF6,1),(0xF0,hp),(0xF2,2),(0xC4,0),(0x36,0x1800)):
            add(put(off,value))
    dp(0x1300);add(put(0xF6,0))
    dp(0x1800);add('    lda #2');call('S6_CountEntities')
    life_snapshot('exists-not-positive-hp-owns-count',[0x7E184C,0x7E183A],[2,0])
    for off in (0x44,0x46,0x4E,0x50):add(put(off,0x1200))
    dp(0x1200);call('S6_KillUnlinked')
    life_snapshot('kill-clears-hp-existence-and-all-player-references',
                  [0x7E12F0,0x7E12F6,0x7E1844,0x7E1846,0x7E184E,0x7E1850],[0]*6)
    dp(0x1800);add('    lda #2');call('S6_CountEntities')
    life_snapshot('removal-releases-count',[0x7E184C],[1])
    dp(0x1000);add(put(0xC4,1));call('S6_KillUnlinked')
    life_snapshot('linked-removal-fails-before-mutation',[0x7E10FC,0x7E10F0,0x7E10F6],[4,20,1])
    add(put(0xFC,0));add(put(0xC4,0))
    for hp,old,expected in ((20,23,22),(20,17,18),(20,20,20),(-32768,32767,32766),(32767,-32768,32769)):
        add(put(0xF0,hp&65535));add(put(0x70,old&65535));call('S6_DisplayHealth')
        life_snapshot(f'health-{hp}-{old}',[0x7E1070],[expected])
    # Component test against the real ABI offsets, NOT an organic world gate.
    production_symbols=symbols(ROOT/'src/main.sym')
    constants=('CHAR_ZP_LEN','CHAR_POS_X','CHAR_POS_Y','CHAR_HP','CHAR_FACING_LEFT',
               'CHAR_INPUT_DRIVEN','CHAR_SELECTED','CHAR_SELECTED_JUMP',
               'CHAR_GRAB_TARGET','CHAR_GRABBED_BY',
               'CHAR_THROW_ZPOS','CHAR_THROW_ZVEL','StageEnv_Actors',
               'StageEnv_BaseFraction','StageEnv_BaseInteger')
    assert production_symbols['CHAR_ZP_LEN']==133
    meta=production_symbols['StageEnv_Actors']
    def absolute(address,value):add(f'    lda #${value&65535:04X}\n    sta.l ${address:06X}')
    dp(0x1900);add(put(0x7A,0));add(put(0xFC,0))
    for address,value in ((meta+64,0x101),(meta+66,20),(meta+68,0x1900),
                          (meta,0),(meta+2,0),
                          (0x7E0A00+production_symbols['CHAR_POS_X'],240),
                          (0x7E0A00+production_symbols['CHAR_POS_Y'],144),
                          (0x7E0A00+production_symbols['CHAR_THROW_ZPOS'],0),
                          (0x7E0A00+production_symbols['CHAR_THROW_ZVEL'],0),
                          (0x7E0A00+production_symbols['CHAR_HP'],20),
                          (0x7E0A00+production_symbols['CHAR_GRAB_TARGET'],65535),
                          (0x7E0A00+production_symbols['CHAR_FACING_LEFT'],0)):
        absolute(address,value)
    call('S6Bridge_Import')
    life_snapshot('bridge-reads-real-production-fields',
        [0x7E1914,0x7E1916,0x7E1918,0x7E19F0,0x7E19F6,0x7E191A,0x7E19FC],
        [300,180,0,20,1,1,0])
    add(put(0xF0,15));add(put(0x70,19));add(put(0x14,305));call('S6Bridge_Export')
    life_snapshot('bridge-writes-real-position-and-health',
        [0x7E0A00+production_symbols['CHAR_POS_X'],
         0x7E0A00+production_symbols['CHAR_HP'],meta+66,0x7E19FC],[244,15,19,0])
    add(put(0xF0,14));add(put(0x14,306));call('S6Bridge_Export')
    life_snapshot('bridge-rejects-lossy-projection-before-health-mutation',
        [0x7E0A00+production_symbols['CHAR_POS_X'],
         0x7E0A00+production_symbols['CHAR_HP'],0x7E19FC],[244,15,10])
    dp(0x1800)
    for off,val in ((0,1234567890&65535),(2,1234567890>>16),(0x44,0x1200),(0x46,0)):
        add(put(off,val))
    dp(0x1200);add(put(0x14,150));add(put(0x16,180))
    dp(0x1000)
    for off,val in ((0x14,100),(0x16,180),(0xFC,0),(0xE6,1),(0xD0,100),(0xD2,0),
                    (0xCC,2),(0x38,2),(0xA0,1),(0xA2,65526),(0xA4,80),(0xA6,2),
                    (0xA8,0),(0xB0,0x1D00)):
        add(put(off,val))
    call('S6_EnemyDecision')
    life_snapshot('ordinary-source-decision-prepares-with-shared-rng',
        [0x7E10E6,0x7E10EC,0x7E10EE,0x7E10E4,0x7E101A,0x7E10FC],[11,157,0,2,1,0])
    add(put(0xD0,156));call('S6_EnemyDecision')
    life_snapshot('ordinary-prepare-does-not-start-early',[0x7E10E6,0x7E10E4],[11,2])
    add(put(0xD0,158));call('S6_EnemyDecision')
    life_snapshot('ordinary-prepare-selects-source-attack-role',[0x7E10E6,0x7E10E4,0x7E10FC],[12,1,0])
    call('S6_EnemyDecision')
    life_snapshot('ordinary-attack-driver-owns-attacking',[0x7E1008,0x7E10F4],[1,0])
    add(put(0x10,0));call('S6_EnemyDecision')
    life_snapshot('ordinary-completion-selects-source-runoff-with-shared-rng',
        [0x7E10E6,0x7E10E4,0x7E1008,0x7E10EC,0x7E10FC],[13,2,0,358,0])
    for off,val in ((0xF2,1),(0xF0,50),(0x76,2),(0x3A,1),(0xC2,0),(0xC4,0),
                    (0x18,0),(0xB8,150),(0x74,0)):
        add(put(off,val))
    add('    lda #18\n    ldx #0\n    ldy #0');call('S6_GroundDamage')
    life_snapshot('source-enemy-force-enters-player-pain',
        [0x7E10F0,0x7E10E6,0x7E10B4,0x7E101A,0x7E1074,0x7E10FC],[32,7,198,1,0,0])
    add(put(0x76,1));add('    lda #5\n    ldx #0\n    ldy #0');call('S6_GroundDamage')
    life_snapshot('source-player-friendly-damage-halves-integer-force',[0x7E10F0,0x7E10FC],[30,0])
    for off,value in ((0xB0,0x17B0),(0xF2,1),(0xF0,30),(0x76,1),(0xC2,0),
                      (0xC4,0),(0x18,0),(0x14,100),(0xB8,150),(0x74,0),
                      (0xD0,100),(0xD2,0),(0x3A,1),(0xFC,0)):
        add(put(off,value))
    absolute(0x7E17B0,0xFFEE)
    absolute(0x7E17B2,0)
    add('    lda #5\n    ldx #0\n    ldy #0');call('S6_GroundDamage')
    life_snapshot('source-player-damage-reverses-supported-moving-xdir',
        [0x7E10F0,0x7E17B0,0x7E10E6,0x7E10FC],[28,18,7,0])
    add(put(0x18,65285));add('    lda #5\n    ldx #0\n    ldy #0');call('S6_GroundDamage')
    life_snapshot('source-player-pit-death-is-not-faked-as-pain',[0x7E10F0,0x7E10FC],[28,4])
    includes=('actor_s5_isolated.pasm','actor_source_scheduler.pasm','actor_source_world.pasm',
              'actor_source_target.pasm','actor_source_lifecycle.pasm','actor_source_bridge.pasm',
              'actor_source_damage.pasm','actor_source_rng.pasm','actor_source_ai.pasm')
    asm=''.join(f'{key} = ${production_symbols[key]:X}\n' for key in constants)+'''.snes
.lorom
.bank 0
.org $8000
Reset:
    sei
    clc
    xce
    rep #$30
    .a16
    .i16
    ldx #$1FFF
    txs
    lda #0
    tcd
    sep #$20
    .a8
    pha
    plb
    lda #$80
    sta $2100
    stz $4200
    rep #$30
    .a16
    .i16
    ldx #$1EFE
    lda #0
Clear:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl Clear
'''+''.join(code)+'''
    lda #$5736
    sta.l $7E2000
Done:
    .a16
    .i16
    bra Done
S6_WorldLost:
    .a16
    .i16
    lda #0
    jsl LogHook
    rtl
S6_WorldGravity:
    .a16
    .i16
    lda #1
    jsl LogHook
    lda $C4
    beq GravityDone
    lda #123
    sta $FC
GravityDone:
    .a16
    .i16
    rtl
S6_Think:
    .a16
    .i16
    lda #2
    jsl LogHook
    lda $C6
    beq ThinkDone
    stz $F6
ThinkDone:
    .a16
    .i16
    rtl
S6_FrameChanged:
    .a16
    .i16
    lda #3
    jsl LogHook
    rtl
S6_WorldAttack:
    .a16
    .i16
    lda #4
    jsl LogHook
    rtl
S6_WorldHealth:
    .a16
    .i16
    lda #5
    jsl LogHook
    rtl
LogHook:
    .a16
    .i16
    xba
    sta.l $7E2044
    tdc
    xba
    and #$00FF
    ora.l $7E2044
    pha
    lda.l $7E2040
    asl a
    tax
    pla
    sta.l $7E7000,x
    lda.l $7E2040
    inc a
    sta.l $7E2040
    rtl
S5_HostRandom03:
    .a16
    .i16
    rtl
'''+''.join(f'.include "{(ROOT/"src/core"/n).as_posix()}"\n' for n in includes)+'''
.org $FFC0
    .db "S6 WORLD PASS FIXTURE "
    .db $20,$00,$06,$00,$01,$00,$00
    .dw $FFFF,0
.org $FFE0
    .dw 0,0,Done,Done,0,Done,0,Done
    .dw 0,0,Done,0,0,Done,Reset,Done
.bank 1
.org $8000
'''+ '\n'.join('    .db '+','.join(f'${v:02X}' for v in data[i:i+16]) for i in range(0,len(data),16))+'\n'
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    result=subprocess.run([r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(pasm),'-s',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(result.stdout+result.stderr)
    if result.returncode or 'warning' in (result.stdout+result.stderr).lower():raise RuntimeError(result.stdout+result.stderr)
    blob=bytearray((folder/'fixture.bin').read_bytes());assert len(blob)<=65536
    blob.extend(bytes(65536-len(blob)));blob[0x7FDC:0x7FE0]=b'\xff\xff\0\0'
    checksum=sum(blob)&65535;struct.pack_into('<HH',blob,0x7FDC,checksum^65535,checksum)
    rom=folder/'fixture.sfc';rom.write_bytes(blob)
    (folder/'cases.json').write_text(json.dumps(cases,indent=2))
    from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact
    with McpSession(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),boot_wait=1,stderr_log=folder/'mesen.log') as m:
        m.reset_emulator();run_frames_exact(m,60);m.pause();ram=m.read_memory('snesMemory',0x7E0000,65536)
    (folder/'wram.bin').write_bytes(ram)
    assert struct.unpack_from('<H',ram,0x2000)[0]==0x5736,'fixture did not finish'
    for case in cases:
        actual=list(struct.unpack_from('<'+str(2+len(case['events']))+'H',ram,case['base']))
        assert actual==[case['error'],len(case['events']),*case['events']],(case,actual)
    for case in target_cases:
        actual=struct.unpack_from('<HH',ram,case['base'])
        assert actual==(case['target'],case['error']),(case,actual)
    (folder/'target-cases.json').write_text(json.dumps(target_cases,indent=2))
    for case in lifecycle_cases:
        actual=list(struct.unpack_from('<'+str(len(case['expected']))+'H',ram,case['base']))
        assert actual==case['expected'],(case,actual)
    (folder/'lifecycle-cases.json').write_text(json.dumps(lifecycle_cases,indent=2))
    report=dict(status='PASS_NATIVE_PASS_ORDER',cases=len(cases),production_changed=False,
                full_actor_certification=False,live_ai_proof=False,gravity_numeric_proof=False,
                native_discrete_target_cases=len(target_cases),
                native_world_consumer_cases=len(lifecycle_cases),
                rom_sha256=sha(rom),runtime_sha256={n:sha(ROOT/'src/core'/n) for n in includes},
                source_reference_sha256=sha(ROOT/'out/bor_compile_s6/BOR.C'),world_layout=layout)
    (folder/'proof.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
