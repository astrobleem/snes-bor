"""Returning lossless bitmap jobs in an actual persistent BOR world.

Explicit immutable source poses; no live camera or PPU publication claim.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

from _source_leaf_fixture import run_fixture, REQUEST
from _harness import Reporter, run_frames_exact
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
import game_bor_startup_select as startup
from sa1_workspace_jobs import (install_workspace_gate, returning_graphics_kernel,
                               returning_graphics_row, entry_trampoline)

ASM = r'''
GraphicsWait:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l REQUEST
 cmp #$B4AD
 bne GraphicsWaitDone
 lda #0
 sta.l REQUEST
 jsl GraphicsFixture
 bcc GraphicsWaitGood
 lda #1
 sta.l ERROR
 bra GraphicsWaitDone
GraphicsWaitGood:
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #6
 bcs GraphicsWaitDone
 lda #$B4AD
 sta.l REQUEST
GraphicsWaitDone:
 ply
 plx
 pla
 plp
 jml REALWAIT
GraphicsFixture:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 phd
 phb
 lda #0
 tcd
 sep #$20
.a8
 pha
 plb
 rep #$30
.a16
.i16
 lda #$B66D
 sta.l $412028
 lda.l INDEX
 inc a
 sta.l $41202A
 lda #0
 sta.l $41202C
 lda #1
 sta.l $41202E
GraphicsAcquireWait:
 lda.l $41202E
 cmp #2
 bne GraphicsAcquireWait
GraphicsAcquired:
 nop
 sep #$20
.a8
 lda #2
 sta.w $2220
 lda #3
 sta.w $2221
 rep #$30
.a16
.i16
 ldx #0
GraphicsProducerCopy:
 lda.l $3B8000,x
 sta.l $003200,x
 inx
 inx
 cpx #PRODUCERBYTES
 bne GraphicsProducerCopy
 ldx #0
GraphicsRowCopy:
 lda.l $3B8800,x
 sta.l $003500,x
 inx
 inx
 cpx #ROWBYTES
 bne GraphicsRowCopy
 ldx #0
GraphicsOriginsCopy:
 lda.l $C30000,x
 sta.l $42D000,x
 inx
 inx
 cpx #ORIGINBYTES
 bne GraphicsOriginsCopy
 lda.l INDEX
 cmp #1
 beq GraphicsMoveOrigin
 cmp #5
 bne GraphicsOriginReady
GraphicsMoveOrigin:
 lda.l $42D004
 sec
 sbc #30
 sta.l $42D004
GraphicsOriginReady:
 lda #EPOCHLOW
 sta.l $42D100
 lda #EPOCHHIGH
 sta.l $42D102
 lda #TOKENLOW
 sta.l $42D104
 lda #TOKENHIGH
 sta.l $42D106
 lda.l INDEX
 cmp #5
 bne GraphicsPhaseOrdinary
 lda #1
 bra GraphicsPhaseReady
GraphicsPhaseOrdinary:
 cmp #2
 bcc GraphicsPhaseReady
 lda #0
GraphicsPhaseReady:
 sta.l $003416
 lda #ENTRYLOW
 sta.l $0037C0
 lda #ENTRYHIGH
 sta.l $0037C2
 lda #0
 sta.l $0034D0
GraphicsInputsReady:
 nop
 lda #3
 sta.l $41202E
GraphicsJobWait:
 lda.l $41202E
 cmp #4
 beq GraphicsProduced
 cmp #6
 bne GraphicsJobWait
GraphicsProduced:
 nop
 lda.l $41202E
 cmp #4
 bne GraphicsExpectedFault
 lda.l INDEX
 cmp #2
 bcs GraphicsFailed
 lda #0
 bra GraphicsRelease
GraphicsExpectedFault:
 lda.l INDEX
 cmp #2
 bcc GraphicsFailed
 lda #0
 bra GraphicsRelease
GraphicsFailed:
 lda #1
GraphicsRelease:
 pha
 sep #$20
.a8
 lda #0
 sta.w $2220
 lda #1
 sta.w $2221
 rep #$30
.a16
.i16
 lda #5
 sta.l $41202E
GraphicsReleaseWait:
 lda.l $41202E
 bne GraphicsReleaseWait
GraphicsReleased:
 nop
 pla
 beq GraphicsSuccess
 plb
 pld
 ply
 plx
 pla
 plp
 sec
 rtl
GraphicsSuccess:
 plb
 pld
 ply
 plx
 pla
 plp
 clc
 rtl
'''

LUA = r'''
local active=false;local before=nil;local bad=0
local function resident()local t={};for a=0x411700,0x411fff do t[#t+1]=emu.read(a,emu.memType.snesMemory)end;for a=0x3025,0x3027 do t[#t+1]=emu.read(a,emu.memType.snesMemory)end;return t end
emu.addMemoryCallback(function()before=resident();active=true;bad=0;emu.log('GRAPHICS|acquired|'..emu.getState().masterClock)end,emu.callbackType.exec,ACQUIRED,ACQUIRED,emu.cpuType.snes,emu.memType.snesMemory)
local function guard(a)if active and not((a>=0x420000 and a<0x421ae0)or(a>=0x42d000 and a<0x42d000+ORIGINBYTES)or(a>=0x42d100 and a<0x42d108)or(a>=0x41202e and a<0x412030))then bad=bad+1 end end
for _,cpu in ipairs({emu.cpuType.snes,emu.cpuType.sa1})do emu.addMemoryCallback(guard,emu.callbackType.write,0x400000,0x43ffff,cpu,emu.memType.snesMemory)end
emu.addMemoryCallback(function()
 local i=emu.read(INDEX,emu.memType.snesMemory)
 local a=({[2]=0x42d100,[3]=0x42d000,[4]=0x42d104})[i]
 if a then emu.write(a,(emu.read(a,emu.memType.snesMemory)+1)%256,emu.memType.snesMemory)end
 -- Test-only entry redirection exercises the nested row-fault return ABI.
 if i==5 then emu.write(0x3500,0x4c,emu.memType.sa1Memory);emu.write(0x3501,ROWFAULT%256,emu.memType.sa1Memory);emu.write(0x3502,ROWFAULT//256,emu.memType.sa1Memory)end
end,emu.callbackType.exec,INPUTSREADY,INPUTSREADY,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 active=false;local after=resident();local n=0;for i,v in ipairs(after)do if v~=before[i]then n=n+1 end end
 emu.log('GRAPHICS|resident|'..n);emu.log('GRAPHICS|writes|'..bad);emu.log('GRAPHICS|produced|'..emu.getState().masterClock)
 local t={};for a=0x420000,0x421adf do t[#t+1]=string.format('%02x',emu.read(a,emu.memType.snesMemory))end;emu.log('GRAPHICSBITMAP|'..table.concat(t))
 local t={};for a=0x34d0,0x34d9 do t[#t+1]=string.format('%02x',emu.read(a,emu.memType.snesMemory))end;emu.log('GRAPHICSSTATUS|'..table.concat(t))
end,emu.callbackType.exec,PRODUCED,PRODUCED,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()emu.log('GRAPHICS|released|'..emu.getState().masterClock)end,emu.callbackType.exec,RELEASED,RELEASED,emu.cpuType.snes,emu.memType.snesMemory)
'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--graphics',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.rom=a.rom.resolve();a.graphics=a.graphics.resolve()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    sealed=(a.graphics/'proof.sfc').read_bytes();gr=json.loads((a.graphics/'report.json').read_text())
    if hashlib.sha256(sealed).hexdigest()!=gr['ROM_sha256']:raise ValueError('GRAPHICS_SEAL')
    observer=(a.graphics/'observer.lua').read_text()
    entries={n:int(re.search(r"DIRECTJOB\|"+n+r"\|.*?callbackType.exec,(\d+)",observer).group(1))for n in ('done','epoch_fault','fixed_actor_fault')}
    original=sealed[0x9000:0x9200]
    producer=returning_graphics_kernel(original,entries)
    row=returning_graphics_row(sealed[0x9c00:0x9c00+gr['row_worker_IRAM_bytes']])
    marker=bytes.fromhex('a9 ae b4 8f d0 34 00')
    if row.count(marker)!=1:raise ValueError('GRAPHICS_ROW_FAULT_LAYOUT')
    row_fault=0x3500+row.index(marker)
    if len(row)&1:row+=b'\xea'
    epochs=[]
    for address in (bytes.fromhex('af 00 d1 42 c9'),bytes.fromhex('af 02 d1 42 c9')):
        if original.count(address)!=1:raise ValueError('GRAPHICS_EPOCH_LAYOUT')
        i=original.index(address)+len(address);epochs.append(int.from_bytes(original[i:i+2],'little'))
    pattern=bytes.fromhex('a5 04 18 69 10 00 85 04 c9')
    if original.count(pattern)!=1:raise ValueError('GRAPHICS_DESCRIPTOR_LAYOUT')
    i=original.index(pattern)+len(pattern);span_bytes=int.from_bytes(original[i:i+2],'little')
    origin_bytes=max(struct.unpack_from('<H',sealed,0x20000+j+6)[0]for j in range(0,span_bytes,16))+4
    token=gr['fixed_underlay_native_frame_guard'][1]
    trampoline=entry_trampoline(0x3200)
    values=dict(PRODUCERBYTES=len(producer),ROWBYTES=len(row),ORIGINBYTES=origin_bytes,
                EPOCHLOW=epochs[0],EPOCHHIGH=epochs[1],TOKENLOW=token&65535,TOKENHIGH=token>>16,
                ENTRYLOW=int.from_bytes(trampoline[:2],'little'),ENTRYHIGH=int.from_bytes(trampoline[2:],'little'))
    values['ROWFAULT']=row_fault
    asm=ASM;lua=LUA
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm);lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    r=Reporter('M4-COOPERATIVE-SOURCE-GRAPHICS-NATIVE',kind='GATE');world={}
    def transform(raw,sy):
        install_workspace_gate(raw,symbols(a.rom.parent/'worker.sym'),sy)
        if any(raw[0x200000:]):raise ValueError('GRAPHICS_ROM_TAIL_RESERVATION')
        raw[0x200000:]=sealed
        for at,data in ((59*32768,producer),(59*32768+0x800,row)):
            if any(raw[at:at+len(data)]):raise ValueError('GRAPHICS_KERNEL_RESERVATION')
            raw[at:at+len(data)]=data
        at=offset(sy['Core_Nmi_WaitFrame'])
        if raw[at:at+4]!=b'\x5c'+sy['Tad_StreamWaitFrame'].to_bytes(3,'little'):raise ValueError('GRAPHICS_WAIT_LAYOUT')
        raw[at+1:at+4]=sy['GraphicsWait'].to_bytes(3,'little')
    def before(m,sy):
        run_frames_exact(m,144)
        if startup.u16(m,0x7e175c)==0:raise ValueError('GRAPHICS_RESIDENT_WORLD_NOT_ACQUIRED')
        m.write_u16(REQUEST+6,0)
        for name in ('SourceVMRun4086_Ready','SourceVMRun4086_Busy','VmSourceFrame_Pending'):m.write_u16(sy[name],0)
        world['ack_before']=startup.u16(m,0x412004)
    def close(m,sy,completed):
        (out/'diagnostic.json').write_text(json.dumps(dict(completed=completed,SCPU=m.get_cpu_state('Snes'),SA1=m.get_cpu_state('Sa1'),status=m.read_memory('SnesMemory',0x34d0,10).hex(),lease=startup.u16(m,0x41202e)),indent=2)+'\n')
        run_frames_exact(m,30)
        world.update(ack_after=startup.u16(m,0x412004),state=startup.u16(m,sy['Game_State']),fault=m.read_memory('SnesMemory',0x412008,3).hex(),lease=startup.u16(m,0x41202e))
    raw,log=run_fixture(a.rom,out,[{} for _ in range(6)],'GraphicsFixture','SourceAudio_Status',0xb4ad,[],lua,r,
                       append=asm,bindings=dict(REALWAIT='Tad_StreamWaitFrame'),
                       probes=dict(ACQUIRED='GraphicsAcquired',PRODUCED='GraphicsProduced',RELEASED='GraphicsReleased',INPUTSREADY='GraphicsInputsReady'),
                       batch_size=1,frame_limit=120,rom_transform=transform,before_start=before,closeout=close,link_pcm=False)
    bitmaps=[bytes.fromhex(s.split('GRAPHICSBITMAP|',1)[1].strip())for s in log.splitlines()if 'GRAPHICSBITMAP|'in s]
    hashes=[hashlib.sha256(b).hexdigest()for b in bitmaps]
    expected=['68c7861e4af75225f0d1b145aa1ccc8ac4b6da50157c442f574b7473b987436d','893eafe85fb3ca631cb214731dc27dcd7e3bd9f1247ed245937e9906b0671794']
    r.check('both native source bitmap identities exact',hashes[:2]==expected)
    statuses=[s.split('GRAPHICSSTATUS|',1)[1].strip()for s in log.splitlines()if 'GRAPHICSSTATUS|'in s]
    events=[]
    for s in log.splitlines():
        if 'GRAPHICS|'in s:
            name,value=s.split('GRAPHICS|',1)[1].strip().split('|')
            if name in ('acquired','produced','released'):events.append((name,int(value)))
    timings=[]
    if len(events)==18 and [n for n,_ in events]==['acquired','produced','released']*6:
        for i in range(0,18,3):
            timings.append(dict(staging_and_job_master_clocks=events[i+1][1]-events[i][1],
                                lease_master_clocks=events[i+2][1]-events[i][1]))
    r.check('six acquired produced released event sequences measured',len(timings)==6)
    r.check('invalid epoch origin and frame token rejected before bitmap mutation',len(statuses)==6 and [s[:4]for s in statuses[:5]]==['abb4','abb4','e1b4','a3b4','a3b4'] and hashes[2:5]==[expected[1]]*3)
    r.check('test-only row fault entry unwinds producer and returns explicit failure',len(statuses)==6 and statuses[5][:4]=='aeb4')
    r.check('resident context and legacy mailbox unchanged',log.count('GRAPHICS|resident|0')==6)
    r.check('native writes remain in owned graphics inputs and output',log.count('GRAPHICS|writes|0')==6)
    r.check('resident world resumes without a fault',world['ack_after']>world['ack_before']and world['state']==startup.PLAYING and world['fault']=='000000'and world['lease']==0)
    report=dict(schema='BYOR_COOPERATIVE_SOURCE_GRAPHICS_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',checks=r.results,ROM_sha256=hashlib.sha256(raw).hexdigest(),graphics_component_ROM=gr['ROM_sha256'],bitmap_sha256=hashes,native_status=statuses,world=world,producer_bytes=len(producer),row_bytes=len(row),origin_bytes=origin_bytes,live_source_camera_binding=False,PPU_publication_proven=False,production_payload_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
    report.update(timings=timings,row_fault_test_policy='test-only row entry JMP to existing palette failure handler; not a palette capacity proof')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
