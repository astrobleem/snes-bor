"""Isolated native scheduler CPU proof; no production include or certification claim."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

from actor_s5_isolated import ROOT, Source, parse_model, lower_model, frame_bytes, put, pointer, sha
from actor_lowering import source_random32_step


def build(folder):
    source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    actor=lower_model(parse_model(source,'data/chars/kula/kula.txt','Kula','s6-control','historical-bor'))
    frames=next(a['frames'] for a in actor['animations'] if a['role']=='attack1')
    assert [f['delay'] for f in frames]==[4,4,4,4,2,2]
    data=b''.join(frame_bytes(f) for f in frames)
    # Three roles share source descriptors; loop metadata differs in synthetic controls.
    table=b''.join(struct.pack('<HHHBB8x',i,6,0x8000,1,loop) for i,loop in ((1,0),(2,1),(3,0),(4,0)))
    tableptr=0x18000+len(data);data+=table
    code=[];expected=[]
    fields=(0xD0,0x06,0x10,0xD4,0xE4,0xF4,0xFC,0xF6,0x2E,0x3E,0x0A,0x4C)
    def capture(name,values,selected=fields):
        index=len(expected);expected.append(dict(name=name,values=values))
        for i,offset in enumerate(selected):code.append(f'    lda ${offset:02X}\n    sta.l ${0x7e4000+index*32+i*2:06X}\n')
    def call(name):code.append(f'    jsl {name}\n')
    code.extend([pointer(0xC8,tableptr),put(0xCC,4),put(0xE0,1),put(0xF6,1),put(0xF4,0xffff),put(0x08,1),put(0x1A,1),put(0xE4,0xffff),put(0xF8,1),'    lda #1\n'])
    call('S6_SetRole');call('S5_ActivateAttack')
    capture('entry',[0,0,1,8,1,65535,0,1,1,0,0,0])
    for tick in range(1,43):
        code.append(put(0xD0,tick));call('S6_AnimationPass');call('S5_ActivateAttack')
        frame=min(sum(tick>=d for d in (8,16,24,32,36,40)),5)
        deadline=(8,16,24,32,36,40)[frame]
        capture(f'tick-{tick}',[tick,frame,int(tick<40),deadline,1,65535,0,1,frame+1,0,int(frame in (2,3)),5 if frame in (2,3) else 0])
    # Explicit compatibility selection is rejected, never rewritten to exact.
    code.extend([put(0xE0,2),put(0xD0,40)]);call('S6_AnimationPass')
    capture('policy-rejected',[40,5,0,40,1,65535,1,1,6,0,0,0])
    # Restart preserves lastanimpos, ordinary role change resets it.
    code.extend([put(0xFC,0),put(0xE0,1),put(0xF4,3),put(0xFA,1),'    lda #1\n']);call('S6_SetRole');call('S5_ActivateAttack')
    capture('forced-restart',[40,0,1,48,1,3,0,1,7,0,0,0])
    code.extend([put(0xFA,0),'    lda #2\n']);call('S6_SetRole');call('S5_ActivateAttack')
    capture('role-change',[40,0,1,48,2,65535,0,1,8,0,0,0])
    code.extend([put(0x10,65535),put(0xD0,48)]);call('S6_AnimationPass');call('S5_ActivateAttack')
    capture('reverse-wrap',[48,5,65535,52,2,65535,0,1,9,0,0,0])
    code.extend([put(0xE6,1),put(0xE8,50),put(0xD0,50)]);call('S6_ThinkPass')
    capture('think-deadline',[50,5,65535,52,2,65535,0,1,9,1,0,0])
    call('S6_ThinkPass')
    capture('think-not-repeated',[50,5,65535,52,2,65535,0,1,9,1,0,0])
    code.extend([put(0xE6,0),put(0xE8,50)]);call('S6_ThinkPass')
    capture('null-think-preserves-deadline',[50,1],(0xE8,0x3E))
    damagefields=(0xF0,0xB4,0xE6,0x06,0xE4,0x10,0x08,0x1A,0xFC)
    code.extend([put(0xF2,2),put(0xF0,20),put(0x3A,3),put(0x38,2),put(0x14,100),put(0xB8,80),
                 '    lda #5\n    ldx #0\n    ldy #0\n']);call('S6_EnemyGroundDamage')
    capture('source-force-five-pain',[15,90,2,0,3,1,0,0,0],damagefields)
    # Full knockdown lifecycle is explicitly unbound, not silently approximated.
    code.append('    lda #5\n    ldx #1\n    ldy #0\n');call('S6_EnemyGroundDamage')
    capture('drop-fails-before-mutation',[15,90,2,0,3,1,0,0,4],damagefields)
    code.extend([put(0xFC,0),put(0x10,0)]);call('S6_RecoveryThink')
    capture('pain-completion-to-idle',[15,90,1,0,2,1,0,0,0],damagefields)
    code.append('    lda #$1800\n    tcd\n')
    seed=1234567890
    for index,initial in enumerate([0,1,65535,65536,0xffffffff]+[None]*8):
        if initial is not None:seed=initial
        elif index==5:seed=1234567890
        code.extend([put(0,seed&65535),put(2,seed>>16)])
        call('S6_Random32');call('S6_RandomModulo1000')
        seed,value=source_random32_step(seed)
        capture(f'rng-{index}',[seed&65535,seed>>16,value&65535,value>>16,value%1000],(0,2,4,6,0x18))
    code.extend([put(0x20,1),put(0x22,0),'    lda #$1200\n    tcd\n    ldx #254\n    lda #0\nTargetClear:\n    .a16\n    .i16\n    sta $00,x\n    dex\n    dex\n    bpl TargetClear\n',
        pointer(0xC8,tableptr),put(0xCC,4),put(0xE0,1),put(0xF6,1),put(0xE4,65535),put(0xF2,2),put(0xF0,20),
        put(0x3A,3),put(0x38,2),put(0x14,175),put(0x16,160),put(0x1A,1),'    lda #1\n'])
    call('S6_SetRole')
    code.extend(['    lda #$1000\n    tcd\n',put(0xD0,100),put(0x34,0x1200),put(0x36,0x1800),put(0xF2,1),
        put(0x14,120),put(0x16,160),put(0x1A,1),put(0x08,1),put(0xFA,1),put(0xFC,0),put(0x3E,0),'    lda #1\n'])
    call('S6_SetRole')
    for off in range(0x70,0x80,2): code.append(put(off,0xB000+off))
    for tick in range(101,143):
        code.append(put(0xD0,tick));call('S6_AnimationPass')
        if tick%2==0:call('S6_TryHitOne')
        code.append('    lda #$1200\n    tcd\n')
        capture(f'scheduled-hit-{tick}',[20 if tick<116 else 15,0 if tick<116 else 156,0 if tick<116 else 2],(0xF0,0xB4,0xD8))
        code.append('    lda #$1000\n    tcd\n')
    capture('exact-hit-effects-once',[1,0],(0x3E,0xFC))
    capture('collision-preserves-persistent-world-bridge-fields',
            [0xB000+off for off in range(0x70,0x80,2)],tuple(range(0x70,0x80,2)))
    code.extend(['    lda #$1200\n    tcd\n',put(0xB0,0x1900),put(0x3C,4),put(0xE6,6),put(0xC2,1)])
    life=(0xE6,0xF6,0xE4,0x10,0xB2,0xE8)
    call('S6_GroundLifecycle');capture('drop-waits-for-explicit-inair',[6,1,3,1,0,0],life)
    code.append(put(0xC2,0));call('S6_GroundLifecycle');capture('drop-to-enemy',[1,1,3,1,0,0],life)
    code.extend([put(0xE6,4),put(0xEC,201),put(0xD0,200)])
    call('S6_GroundLifecycle');capture('lie-waits',[4,1,3,1,0,0],life)
    code.extend([put(0xD0,201),'    lda #$BEEF\n    sta.l $7E1900\n    sta.l $7E1902\n    sta.l $7E1904\n    sta.l $7E1906\n'])
    call('S6_GroundLifecycle');capture('lie-to-source-rise',[3,1,4,1,0,0],life)
    code.append('    lda #$1900\n    tcd\n');capture('numeric-velocity-reset',[0,0,0,0],(0,2,4,6));code.append('    lda #$1200\n    tcd\n')
    for tick in range(202,242):code.append(put(0xD0,tick));call('S6_AnimationPass')
    call('S6_RecoveryThink');capture('rise-to-idle',[1,1,2,1,0,0],life)
    code.extend([put(0xE6,4),put(0xF0,0),put(0xD0,300)])
    call('S6_GroundLifecycle');capture('death-schedules-blink',[5,1,2,1,1,700],life)
    # Host deadline dispatch is separately tested above; invoke callback at700.
    code.append(put(0xD0,700));call('S6_GroundLifecycle');capture('suicide-removes',[5,0,2,1,1,700],life)
    runtime=ROOT/'src/core/actor_source_scheduler.pasm';s5=ROOT/'src/core/actor_s5_isolated.pasm'
    damage=ROOT/'src/core/actor_source_damage.pasm'
    rng=ROOT/'src/core/actor_source_rng.pasm'
    hit=ROOT/'src/core/actor_source_hit.pasm'
    asm='''.snes
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
    lda #$1000
    tcd
    ldx #254
    lda #0
Clear:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl Clear
'''+''.join(code)+'''
    lda #$5336
    sta.l $7E2000
Done:
    .a16
    .i16
    bra Done
S6_FrameChanged:
    .a16
    .i16
    inc $2E
    rtl
S6_Think:
    .a16
    .i16
    inc $3E
    rtl
S5_HostRandom03:
    .a16
    .i16
    rtl
S6_HitEffects:
    .a16
    .i16
    inc $3E
    rtl
'''+f'.include "{s5.as_posix()}"\n.include "{runtime.as_posix()}"\n.include "{damage.as_posix()}"\n.include "{rng.as_posix()}"\n.include "{hit.as_posix()}"\n'+'''
.org $FFC0
    .db "S6 SCHEDULER FIXTURE  "
    .db $20,$00,$06,$00,$01,$00,$00
    .dw $FFFF,0
.org $FFE0
    .dw 0,0,Done,Done,0,Done,0,Done
    .dw 0,0,Done,0,0,Done,Reset,Done
.bank 1
.org $8000
'''+ '\n'.join('    .db '+','.join(f'${b:02X}' for b in data[i:i+16]) for i in range(0,len(data),16))+'\n'
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    result=subprocess.run([r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(pasm),'-s',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(result.stdout+result.stderr)
    if result.returncode or 'warning' in (result.stdout+result.stderr).lower():raise RuntimeError(result.stdout+result.stderr)
    blob=bytearray((folder/'fixture.bin').read_bytes());assert len(blob)<=65536
    blob.extend(bytes(65536-len(blob)));blob[0x7fdc:0x7fe0]=b'\xff\xff\x00\x00'
    checksum=sum(blob)&65535;struct.pack_into('<HH',blob,0x7fdc,checksum^65535,checksum)
    rom=folder/'fixture.sfc';rom.write_bytes(blob)
    (folder/'cases.json').write_text(json.dumps(expected,indent=2))
    return rom,expected


def main():
    p=argparse.ArgumentParser();p.add_argument('--build-only',action='store_true');args=p.parse_args()
    folder=Path(tempfile.mkdtemp(prefix='actor_s6_scheduler_',dir=ROOT/'out'));print(folder,flush=True)
    rom,cases=build(folder)
    report=dict(status='BUILD_ONLY',rom_sha256=sha(rom),production_changed=False,full_actor_certification=False)
    report['runtime_sha256']={p.name:sha(p) for p in [
        ROOT/'src/core'/name for name in ('actor_source_scheduler.pasm','actor_source_damage.pasm',
        'actor_source_hit.pasm','actor_source_rng.pasm','actor_s5_isolated.pasm')]}
    report['source_reference_sha256']={name:sha(ROOT/'out/bor_compile_s6'/name)
        for name in ('BOR.C','RAND32.ASM','RAND32.H')}
    if not args.build_only:
        from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact
        with McpSession(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),boot_wait=1,stderr_log=folder/'mesen.log') as m:
            m.reset_emulator();run_frames_exact(m,10);m.pause();ram=m.read_memory('snesMemory',0x7e0000,65536)
        (folder/'wram.bin').write_bytes(ram)
        assert struct.unpack_from('<H',ram,0x2000)[0]==0x5336,'native fixture did not finish'
        for i,c in enumerate(cases):
            actual=list(struct.unpack_from('<'+str(len(c['values']))+'H',ram,0x4000+i*32))
            assert actual==c['values'],(c['name'],actual,c['values'])
        report.update(status='PASS',native_cases=len(cases),graphics_proof=False,world_ai_proof=False)
    (folder/'proof.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
