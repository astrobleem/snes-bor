"""Returning lossless bitmap jobs in an actual persistent BOR world.

Explicit immutable source poses; no live camera or PPU publication claim.
"""
import argparse
import hashlib
import json
import re
import struct
import shutil
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
    p.add_argument('--hybrid-ppu',action='store_true')
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
    asm=ASM;lua=LUA;ppu={}
    cases=2 if a.hybrid_ppu else 6
    if a.hybrid_ppu:
        from m4_cooperative_graphics_ppu import conversion_asm, install, observer
        context=a.graphics/'palette-context-1'
        obj_bytes=(context/'obj_chr.bin').stat().st_size
        high_target=max(4096,((obj_bytes+4095)//4096)*4096)
        converter,descriptors=conversion_asm(high_target,gr['promoted_native_window_tiles'])
        asm=asm.replace(' cmp #6',' cmp #2',1)+converter
        lua+=observer()
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm);lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    r=Reporter('M4-COOPERATIVE-SOURCE-GRAPHICS-NATIVE',kind='GATE');world={}
    def transform(raw,sy):
        if a.hybrid_ppu:
            revised,resources=install(raw,sy,a.graphics,out)
            raw[:]=revised;ppu.update(resources=resources,descriptors=descriptors)
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
        for _ in range(300):
            if startup.u16(m,0x7e175c):break
            run_frames_exact(m,1)
        if startup.u16(m,0x7e175c)==0:raise ValueError('GRAPHICS_RESIDENT_WORLD_NOT_ACQUIRED')
        m.write_u16(REQUEST+6,0)
        for name in ('SourceVMRun4086_Ready','SourceVMRun4086_Busy','VmSourceFrame_Pending'):m.write_u16(sy[name],0)
        world['ack_before']=startup.u16(m,0x412004)
    def close(m,sy,completed):
        (out/'diagnostic.json').write_text(json.dumps(dict(completed=completed,SCPU=m.get_cpu_state('Snes'),SA1=m.get_cpu_state('Sa1'),status=m.read_memory('SnesMemory',0x34d0,10).hex(),lease=startup.u16(m,0x41202e)),indent=2)+'\n')
        run_frames_exact(m,30)
        world.update(ack_after=startup.u16(m,0x412004),state=startup.u16(m,sy['Game_State']),fault=m.read_memory('SnesMemory',0x412008,3).hex(),lease=startup.u16(m,0x41202e))
        if a.hybrid_ppu and completed:
            # Only a publication request; no host source bitmap or CHR handoff.
            m.write_u16(0x7ff860,0xa5)
            ppu['emulator_partial_field_timeouts']=0
            ppu['pixel_mismatches']=[]
            try:
                for field in range(16):
                    for attempt in range(20):
                        result=m.run_frames(1)
                        if result.get('framesAdvanced')==1 and not result.get('timedOut'):break
                        if result.get('framesAdvanced')!=0 or not result.get('timedOut'):
                            (out/'frame-progress-error.json').write_text(json.dumps(result,indent=2)+'\n')
                            raise ValueError('NATIVE_CANVAS_FIELD_COUNT')
                        ppu['emulator_partial_field_timeouts']+=1
                    else:raise ValueError('NATIVE_CANVAS_NO_FIELD_PROGRESS')
                    if field>=12 and startup.u16(m,0x7ff85a)>=2:
                        import numpy as np
                        from PIL import Image
                        shot=m.tool('take_screenshot',{'format':'path'})
                        rgb=np.asarray(Image.open(shot['path']).convert('RGB'),dtype=np.uint16)
                        actual=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
                        expected=np.fromfile(context/'expected.bin',dtype='<u2').reshape(224,256)
                        ppu['pixel_mismatches'].append(int(np.count_nonzero(actual!=expected))if actual.shape==expected.shape else -1)
            finally:
                (out/'canvas-dispatch-diagnostic.json').write_text(json.dumps(dict(SCPU=m.get_cpu_state('Snes'),SA1=m.get_cpu_state('Sa1'),PPU=m.get_ppu_state(),raster=m.read_memory('SnesMemory',0x7ff840,38).hex(),lease=startup.u16(m,0x41202e),SCPU_trace=m.trace_log(12)),indent=2)+'\n')
            ppu['VRAM']=m.read_memory('SnesVideoRam',high_target,5504)+m.read_memory('SnesVideoRam',49152,1376)
            ppu['fault']=startup.u16(m,0x7ff856)
            ppu['lease']=startup.u16(m,0x41202e)
            ppu['worker_fault']=m.read_memory('SnesMemory',0x412008,3).hex()
            shot=m.tool('take_screenshot',{'format':'path'});shutil.copyfile(shot['path'],out/'screenshot.png')
    probes=dict(ACQUIRED='GraphicsAcquired',PRODUCED='GraphicsProduced',RELEASED='GraphicsReleased',INPUTSREADY='GraphicsInputsReady')
    if a.hybrid_ppu:probes.update(CONVERSIONACQUIRED='GraphicsCanvasLeaseAcquired',CONVERSIONDONE='GraphicsCanvasConversionDone')
    raw,log=run_fixture(a.rom,out,[{} for _ in range(cases)],'GraphicsFixture','SourceAudio_Status',0xb4ad,[],lua,r,
                       append=asm,bindings=dict(REALWAIT='Tad_StreamWaitFrame'),
                       probes=probes,
                       batch_size=1,frame_limit=120,rom_transform=transform,before_start=before,closeout=close,link_pcm=False,fixture_bank=38 if a.hybrid_ppu else 39)
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
    if len(events)==cases*3 and [n for n,_ in events]==['acquired','produced','released']*cases:
        for i in range(0,cases*3,3):
            timings.append(dict(staging_and_job_master_clocks=events[i+1][1]-events[i][1],
                                lease_master_clocks=events[i+2][1]-events[i][1]))
    r.check('acquired produced released event sequences measured',len(timings)==cases)
    if not a.hybrid_ppu:
        r.check('invalid epoch origin and frame token rejected before bitmap mutation',len(statuses)==6 and [s[:4]for s in statuses[:5]]==['abb4','abb4','e1b4','a3b4','a3b4'] and hashes[2:5]==[expected[1]]*3)
        r.check('test-only row fault entry unwinds producer and returns explicit failure',len(statuses)==6 and statuses[5][:4]=='aeb4')
    r.check('resident context and legacy mailbox unchanged',log.count('GRAPHICS|resident|0')==cases)
    r.check('native writes remain in owned graphics inputs and output',log.count('GRAPHICS|writes|0')==cases)
    r.check('resident world resumes without a fault',world['ack_after']>world['ack_before']and world['state']==startup.PLAYING and world['fault']=='000000'and world['lease']==0)
    report=dict(schema='BYOR_COOPERATIVE_SOURCE_GRAPHICS_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',checks=r.results,ROM_sha256=hashlib.sha256(raw).hexdigest(),graphics_component_ROM=gr['ROM_sha256'],bitmap_sha256=hashes,native_status=statuses,world=world,producer_bytes=len(producer),row_bytes=len(row),origin_bytes=origin_bytes,live_source_camera_binding=False,PPU_publication_proven=False,production_payload_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
    report.update(timings=timings,row_fault_test_policy='test-only row entry JMP to existing palette failure handler; not a palette capacity proof')
    if a.hybrid_ppu:
        from m4_direct_bitmap_native import selected_tiles
        import numpy as np
        x,y,w,h=gr['window']
        mask=np.fromfile(a.graphics/'palette-context-1/promoted.bin',np.bool_).reshape(28,32)[y//8:(y+h)//8,x//8:(x+w)//8]
        planes=[np.fromfile(a.graphics/('palette-context-1/'+n+'.bin'),np.uint8).reshape(224,256)[y:y+h,x:x+w]for n in ('high','low')]
        reference=selected_tiles(np.stack(planes,axis=-1).tobytes(),w,h,mask,bitmap=False)
        pixels=ppu['pixel_mismatches']
        r.check('native converted CHR is byte exact in VRAM',ppu['VRAM']==reference)
        read_trace=[s.split('NATIVECHRREADS|')[1].strip().split('|')for s in log.splitlines()if 'NATIVECHRREADS|'in s]
        r.check('conversion forbids unrelated S-CPU BW-RAM reads and disables before release',len(read_trace)==1 and int(read_trace[0][0])==6880 and read_trace[0][1:]==['0','0'])
        r.check('conversion retains resident world and worker mailbox','NATIVECHRRESIDENT|0'in log)
        r.check('native full hybrid scene pixels are lossless',len(pixels)>=3 and not any(pixels))
        r.check('CGRAM updates remain in safe transfer windows','NATIVEPPUSAFE|0'in log)
        traces=[s.split('NATIVEPPUCGRAM|',1)[1].strip().split(',')for s in log.splitlines()if 'NATIVEPPUCGRAM|'in s]
        r.check('CGRAM observer trace matches compiled schedule',traces==[ppu['resources']['native_CGRAM_expected_trace']])
        oam=[s.split('NATIVEPPUOAM|',1)[1].strip()for s in log.splitlines()if 'NATIVEPPUOAM|'in s]
        r.check('OAM observer trace preserves compiled source pieces',oam==[(context/'oam.bin').read_bytes().hex()])
        flags=[int(s.split('NATIVEPPUFLAGS|')[1])for s in log.splitlines()if 'NATIVEPPUFLAGS|'in s]
        r.check('no native OBJ sprite or tile overflow',len(flags)>=3 and all(v&0xc0==0 for v in flags))
        r.check('native canvas and worker finish without faults',ppu['fault']==0 and ppu['lease']==0 and ppu['worker_fault']=='000000')
        ppu['conversion_BW_RAM_read_trace']=read_trace
        ppu['conversion_master_clocks']=[int(s.split('NATIVECHRCLOCKS|')[1])for s in log.splitlines()if 'NATIVECHRCLOCKS|'in s]
        ppu['CGRAM_budget_trace']=[[int(v)for v in s.split('NATIVEPPUBUDGET|')[1].split('|')]for s in log.splitlines()if 'NATIVEPPUBUDGET|'in s]
        ppu['source_RGB555_sha256']=hashlib.sha256((context/'expected.bin').read_bytes()).hexdigest()
        ppu['alpha_policy']='BOR 4086 alpha 1 RGB8 SCREEN composited before RGB555; lossless HIGH+LOW Mode4 addition'
        ppu['VRAM_sha256']=hashlib.sha256(ppu.pop('VRAM')).hexdigest();ppu['pixel_mismatches']=pixels
        report.update(PPU_publication_proven=all(ok for _,ok in r.results),hybrid_PPU=ppu,checks=r.results,status='PASS'if all(ok for _,ok in r.results)else'FAIL')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
