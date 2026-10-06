"""Private foreign-owner fixture using the production cold boot and NMI.

The original first-stage dispatcher is stopped at its outer loop boundary.
This measures the real NMI handler, not live MOTU gameplay or audio admission.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from unittest.mock import patch
import m4_bg_components_native as bg
from m4_raster_irq_gate_native import combine,gate_observer
from actor_s5_entity_fixture import symbols
from _harness import McpSession,Reporter,exact_input_edge,run_frames_exact
import game_bor_startup_select as startup


def offset(address):
    return (address>>16)*32768+(address&65535)-32768


def build(raw,report,folder,original,sy,canvas_nmi=False,direct_targets_rom=False,palette_prefix=0,frame_hook=None,extra_asm='',audio_service=False):
    private,private_sy=combine(raw,report,folder,76)
    # Regenerate only bank 39, with real long-call destinations and wrappers.
    from source_raster_irq import fetch_prologue,emit
    contract={key:sy[value] for key,value in dict(timer_hook='StageTimer_NmiField',audio_fence='Tad_StreamOneShotHdmaFence',
              frame_counter='Nmi_FrameCounter',hdma_enable='Nmi_HdmaEnable',hdma_current='Nmi_HdmaEnableCurrent').items()}
    if not 0<=palette_prefix<236:raise ValueError('INITIAL_PALETTE_PREFIX_RANGE')
    asm='.snes\nStageWater_Nmi = $%06X\n'%sy['StageWater_Nmi']+emit(contract if canvas_nmi else None,
         0xb48000 if direct_targets_rom else None,(4+palette_prefix,236-palette_prefix),frame_hook)
    asm+='\n.bank 39\n.org $C000\nSourceRasterFetchWrapper:\n.a16\n.i16\n'+fetch_prologue()
    asm+='    plp\n    jml $%06X\n'%sy['Vm_FetchSource']
    asm+='''
.org $C100
SourceRasterColdInit:
.a16
.i16
    php
    rep #$30
    pha
    sep #$20
.a8
    lda #$81
    sta.l $002223
    rep #$20
.a16
    lda #0
    sta.l SourceRaster_Ready
    sta.l SourceRaster_Fault
    sta.l SourceRaster_CoreMode
    sta.l $7FF860
    sta.l $7FF882
    pla
    plp
    jml $%06X
'''%sy['Vm_FetchSourceInit']
    asm+='''
.org $C200
SourceRasterFieldGate:
.a16
.i16
    php
    rep #$30
    pha
    lda.l $7FF860
    and #$00FF
    cmp #$00A5
    bne SourceRasterFieldOrdinary
    lda #0
    sta.l $7FF860
    pla
    plp
    jml $A88000
SourceRasterFieldOrdinary:
.a16
.i16
    pla
    plp
    jml $%06X
'''%sy['Tad_StreamFrameService']
    asm+=extra_asm
    if audio_service:
        asm+='''
.bank 39
.org $C600
SourceCanvasAudioService:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda #0
    tcd
    sep #$20
.a8
    pha
    plb
    rep #$20
.a16
    lda.l $7FF882
    cmp #$B4C1
    beq SourceCanvasAudioReady
    lda #$B4C1
    sta.l $7FF882
    lda #0
    sta.l $7FF884
    sep #$20
.a8
    lda #2
    sta.l $%(source_id)06X
    jsl $A7C780
    rep #$30
.a16
.i16
    lda #$FFFF
    sta.l $7FF880
SourceCanvasAudioReady:
.a16
.i16
    lda.l $%(frame_counter)06X
    cmp.l $7FF880
    beq SourceCanvasAudioReturn
    sta.l $7FF880
SourceCanvasAudioStart:
.a16
.i16
    jsl $%(service)06X
    jsl $%(late)06X
    rep #$30
.a16
.i16
    lda.l $7FF884
    inc a
    sta.l $7FF884
SourceCanvasAudioDone:
.a16
.i16
    nop
SourceCanvasAudioReturn:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
.org $C780
SourceCanvasAudioNearCall:
.a16
.i16
    ; The production stream policy returns RTS. Supply a near return to
    ; an existing RTL in its own bank, above this JSL's far return frame.
    pea $%(near_relay)04X
    sep #$20
.a8
    lda #$%(near_bank)02X
    pha
    pea $%(near_target)04X
    rtl
'''%dict(source_id=sy['AudioStream_SourceId'],source_start=sy['AudioSemantic_StreamBackendPolicy'],
         frame_counter=sy['Nmi_FrameCounter'],service=sy['Tad_StreamFrameService'],late=sy['Tad_StreamLatePump'],
         near_relay=(sy['Tad_ProcessMaybeStream__return']&65535)-1,
         near_bank=sy['AudioSemantic_StreamBackendPolicy']>>16,
         near_target=(sy['AudioSemantic_StreamBackendPolicy']&65535)-1)
        if sy['AudioSemantic_StreamBackendPolicy']>>16!=sy['Tad_ProcessMaybeStream__return']>>16:
            raise ValueError('AUDIO_NEAR_RELAY_BANK')
        if original[offset(sy['Tad_ProcessMaybeStream__return'])]!=0x6b:
            raise ValueError('AUDIO_NEAR_RELAY_NOT_RTL')
    (folder/'production-gate.pasm').write_text(asm)
    command=[r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(folder/'production-gate.pasm'),
             '--output',str(folder/'production-gate.bin'),'--symbols',str(folder/'production-gate.sym'),'--no-pansy']
    process=subprocess.run(command,capture_output=True,text=True)
    (folder/'production-poppy.log').write_text(process.stdout+process.stderr)
    if process.returncode:raise ValueError('PRODUCTION_GATE_ASSEMBLY_FAILED')
    gates=symbols(folder/'production-gate.sym')
    rom=bytearray(original)
    for bank in range(39,46):
        if rom[bank*32768:(bank+1)*32768]!=bytes(32768):raise ValueError('PRODUCTION_PADDING_RESERVATION_OCCUPIED')
    emitted=(folder/'production-gate.bin').read_bytes()
    rom[39*32768:40*32768]=emitted[39*32768:40*32768].ljust(32768,b'\xff')
    for old,new in [(2,41),(3,42),(4,43),(5,44),(6,45)]:
        rom[new*32768:(new+1)*32768]=private[old*32768:(old+1)*32768]
    if direct_targets_rom:
        if rom[52*32768:53*32768]!=bytes(32768):raise ValueError('IMMUTABLE_TARGET_ROM_RESERVATION_OCCUPIED')
        rom[52*32768:52*32768+224]=private[0x2a800:0x2a800+224]
    code=bytearray(private[0x8000:0x8400]);end=code.find(bytes([255])*32)
    if end<0:raise ValueError('PRIVATE_OWNER_END')
    code=code[:end]
    for old,new in [(2,41),(3,42),(4,43),(5,44),(6,45)]:
        code=code.replace(bytes([0xa9,old,0x8d,0x74,0x43]),bytes([0xa9,new,0x8d,0x74,0x43]))
    # Drain previously queued ordinary presentation before acquiring VRAM.
    # The producer is stopped; at most eight admitted atomic slots remain.
    # Existing NMI code is invoked with a genuine native RTI frame, entirely
    # from this banked fixture. No bank-zero instruction is added.
    at=code.find(bytes.fromhex('a9 80 8d 15 21'))+5
    if at<5:raise ValueError('FORCED_BLANK_HANDOFF_POINT')
    drain=bytearray()
    for _ in range(8):
        return_pc=0x8000+at+len(drain)+11
        drain.extend(bytes([0xa9,0xa8,0x48,0xf4,return_pc&255,return_pc>>8,0x08,0x5c]))
        drain.extend(sy['nmi_handler'].to_bytes(3,'little'))
        drain.extend(bytes.fromhex('a9 00 8d 00 42 a9 80 8d 00 21'))
    for slot in range(8):
        address=sy['DmaQueue']+slot*8+4
        drain.extend(bytes([0xaf,address&255,(address>>8)&255,address>>16,0x29,0x40,0xf0,8]))
        drain.extend(bytes.fromhex('a9 01 8f 56 f8 7f 80 fe'))
    code[at:at]=drain
    # Preserve the real channel-zero HDMA configuration; omit dummy audio.
    for address in range(0x4300,0x4305):
        needle=bytes([0x8d,address&255,address>>8]);at=code.find(needle)
        if at<2 or code[at-2]!=0xa9:raise ValueError('DUMMY_HDMA_SETUP_NOT_FOUND')
        del code[at-2:at+3]
    code=code.replace(bytes.fromhex('a9 01 8d 0c 42'),b'')
    for address,old,new in [(0x7ff846,5,44),(0x7ff84a,6,45),(0x7ff850,5,44)]:
        before=bytes([0xa9,old,0,0x8f,address&255,(address>>8)&255,address>>16])
        after=bytes([0xa9,new,0,0x8f,address&255,(address>>8)&255,address>>16])
        if code.count(before)!=1:raise ValueError('PALETTE_DESCRIPTOR_RELOCATION')
        code=code.replace(before,after)
    for address,old,new in [(0x7ff844,0xa800,0 if direct_targets_rom else 0xa800),
                            (0x7ff84e,0x9008,0x9008+palette_prefix*2)]:
        before=bytes([0xa9,old&255,old>>8,0x8f,address&255,(address>>8)&255,address>>16])
        after=bytes([0xa9,new&255,new>>8,0x8f,address&255,(address>>8)&255,address>>16])
        if code.count(before)!=1:raise ValueError('RANGED_PALETTE_OR_TARGET_DESCRIPTOR')
        code=code.replace(before,after)
    # Replace owner body after the boot's final mode switch. Install shadows
    # before exposing Ready, so the production NMI commits this scene.
    marker=code.find(bytes.fromhex('e2 20 a9 01 8d 0d 42 a9 0f 8d 00 21 a9 81 8d 00 42 58'))
    if marker<0:raise ValueError('PRIVATE_OWNER_PUBLICATION')
    code=code[:marker]
    code.extend(bytes.fromhex('e2 20'))
    for address in (0x2123,0x2124,0x2125,0x212a,0x212b,0x212e,0x212f):
        code.extend(bytes([0xa9,0,0x8d,address&255,address>>8]))
    shadows={0x7e5000:0,0x7e5004:15,0x7e500c:1,0x7e500d:0,0x7e500e:2,0x7e500f:4,
             0x7e5010:0x78,0x7e5011:report['offset_map_base']>>9 if 'offset_map_base' in report else 0x58,0x7e5012:0x60,0x7e5003:0x81}
    # The composed foreign canvas owns BG2, including its source foreground.
    # Retire the ordinary frontpanel producer before acquiring that resource.
    for name in ('StageFp_BG2Loaded','StageFp_BG2Active','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):
        shadows[sy[name]]=0
    # Offset-map address is derived from the actual private BG register setup.
    at=private[0x8000:0x8400].find(bytes.fromhex('8d 09 21'))
    shadows[0x7e5011]=private[0x8000+at-1]
    for address,value in shadows.items():code.extend(bytes([0xa9,value,0x8f,address&255,(address>>8)&255,address>>16]))
    code.extend(bytes.fromhex('c2 30'))
    for address,value in [(0x7ff862,0xb4b1 if canvas_nmi else 0),(0x7e5017,0),(0x7e5019,65535),(0x7e501b,0),(0x7e501d,65535),(0x7e501f,0),(0x7e5021,0)]:
        code.extend(bytes([0xa9,value&255,value>>8,0x8f,address&255,(address>>8)&255,address>>16]))
    code.extend(bytes.fromhex('e2 20 a9 01 8d 0d 42 a9 0f 8d 00 21 a9 81 8d 00 42 58'))
    loop=0x8000+len(code)
    code.extend(bytes.fromhex('22 00 c6 a7' if audio_service else '22 00 c0 a7'))
    code.extend(bytes([0x5c,loop&255,loop>>8,0xa8]))
    if len(code)>32768:raise ValueError('PRIVATE_OWNER_BANK_OVERFLOW')
    rom[40*32768:40*32768+len(code)]=code
    # All bank-zero substitutions preserve instruction size and bank0 end.
    fetch=offset(sy['Vm_Fetch']);assert rom[fetch]==0x22
    rom[fetch+1:fetch+4]=bytes.fromhex('00 c0 a7')
    nmi=offset(sy['nmi_handler']);assert rom[nmi]==0x22
    rom[nmi+1:nmi+4]=bytes.fromhex('00 80 a7')
    rom[0x7fee:0x7ff0]=struct.pack('<H',sy['Vm_Fetch']&65535)
    needle=bytes([0x22])+sy['Vm_FetchSourceInit'].to_bytes(3,'little')
    if rom.count(needle)!=1:raise ValueError('COLD_LEASE_OWNER_CALL_NOT_UNIQUE')
    at=rom.find(needle);rom[at+1:at+4]=bytes.fromhex('00 c1 27')
    field=offset(sy['scpu_main_loop'])
    needle=bytes([0x22])+sy['Tad_StreamFrameService'].to_bytes(3,'little')
    at=rom.find(needle,field,field+32)
    if at<0:raise ValueError('FIELD_GATE_ORIGINAL_CALL_NOT_FOUND')
    rom[at+1:at+4]=bytes.fromhex('00 c2 a7')
    return bytes(rom),gates


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--canvas-nmi',action='store_true',help='Own foreign-canvas presentation while retaining timer/audio field fences')
    p.add_argument('--direct-target-rom',action='store_true')
    p.add_argument('--palette-prefix-colors',type=int,default=0)
    a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    original=a.rom.resolve().read_bytes();sy=symbols(Path(__file__).resolve().parents[2]/'src/main.sym')
    compile_base=bg.compile_rom;details={};report=json.loads(a.report.read_text())
    initial=json.loads((a.report.parent/'initial.json').read_text())
    for row in report['trace']:
        for event in row['updates']:
            if event['slot']<=a.palette_prefix_colors and event['color']!=initial[event['slot']-1]:
                raise ValueError('INITIAL_PALETTE_PREFIX_NOT_IMMUTABLE')
    def compile_production(*args,**kwargs):
        raw,trace,resources=compile_base(*args,**kwargs);raw,gates=build(raw,report,folder,original,sy,a.canvas_nmi,a.direct_target_rom,a.palette_prefix_colors);details['gates']=gates
        resources.update(irq_entry_prg_offset=39*32768+4096,irq_exit_prg_offset=offset(gates['SourceRasterIrqReturn']),
                         production_nmi=True,canvas_nmi=a.canvas_nmi,dummy_hdma=False,bank0_runtime_growth=0)
        resources.update(direct_target_rom=a.direct_target_rom,initial_palette_prefix_colors=a.palette_prefix_colors,
                         per_field_palette_restore_bytes=(236-a.palette_prefix_colors)*2)
        for path in [a.rom.resolve().with_suffix('.msu'),*a.rom.resolve().parent.glob('bor-*.pcm')]:
            destination=folder/('proof'+path.name[3:])
            if not destination.exists():os.link(path,destination)
        return raw,trace,resources
    class Extra(McpSession):
        def __enter__(self):
            lua=folder/'observer.lua';s=lua.read_text().replace('if v==15 and not active','if v==15 and not active and emu.read(0x7ff840,emu.memType.snesMemory)==0xb0')
            s+=gate_observer(details['gates'],report['span']*2,offset(sy['Vm_Fetch']),offset(sy['nmi_handler']))
            s+='''
local handoffevents=0
emu.addMemoryCallback(function(a,v)
 if handoffevents<64 then
  handoffevents=handoffevents+1;local c=emu.getState()
  emu.log('GATEHANDOFF|'..a..','..c['cpu.pc']..','..c['cpu.k']..','..c['cpu.sp']..','..c['cpu.ps'])
 end
end,emu.callbackType.exec,1310720,1311232,emu.cpuType.snes,emu.memType.snesPrgRom)
'''
            lua.write_text(s)
            super().__enter__()
            reporter=Reporter('M4-PRODUCTION-NMI',kind='GATE')
            try:
                with patch.object(self,'reset_emulator',return_value=None):startup.cold_to_title(self,reporter)
                startup.title_to_charselect(self);exact_input_edge(self,self.BTN_START,1,port=0)
                if not startup.wait_state(self,startup.PLAYING,300):raise ValueError('PRODUCTION_PLAYING_REQUIRED')
                run_frames_exact(self,12);self.write_u8(0x7ff860,0xa5)
                fields=0
                for attempt in range(2400):
                    if startup.u16(self,0x7ff840)==0xb4b0:break
                    if startup.u16(self,0x7ff856):raise ValueError('ORDINARY_DMA_HANDOFF_NOT_QUIESCENT')
                    if fields>=1200:raise ValueError('FOREIGN_OWNER_NOT_REACHED')
                    progress=self.tool('run_frames',{'count':1})
                    if progress['framesAdvanced'] not in (0,1):raise ValueError('OWNER_WAIT_FRAME_OVERRUN')
                    fields+=progress['framesAdvanced']
                else:raise ValueError('FOREIGN_OWNER_WAIT_NO_PROGRESS')
            except Exception:
                (folder/'boot-failure.json').write_text(json.dumps(dict(cpu=self.get_cpu_state(),state=startup.u16(self,startup.STATE),
                    raster=self.read_memory('SnesMemory',0x7ff840,32)),indent=2,default=lambda value:value.hex()))
                super().__exit__(*sys.exc_info())
                raise
            return self
        def __exit__(self,*args):
            (folder/'gate-state.json').write_text(json.dumps(self.read_memory('SnesMemory',0x7ff840,32),default=lambda value:value.hex()))
            (folder/'cpu-state.json').write_text(json.dumps(self.get_cpu_state(),indent=2))
            (folder/'ordinary-dma-queue.bin').write_bytes(self.read_memory('SnesMemory',sy['DmaQueue'],64))
            return super().__exit__(*args)
    argv=['m4_bg_components_native','--report',str(a.report),'--assets',str(a.report.parent),'--output',str(folder),'--timer','76']
    with patch.object(bg,'compile_rom',compile_production),patch.object(bg,'McpSession',Extra),patch.object(sys,'argv',argv):
        try:bg.main()
        except SystemExit as error:
            if error.code!=1:raise
    r=json.loads((folder/'result.json').read_text());log=(folder/'mesen.log').read_text()
    contexts=[line.split('GATECONTEXT|',1)[1] for line in log.splitlines() if 'GATECONTEXT|' in line]
    counts=[int(v) for v in contexts[-1].split(',')] if contexts else [0,0,-1,0,-1,0]
    r.update(production_base_sha256=hashlib.sha256(original).hexdigest(),context_witness=contexts[-1] if contexts else None,
             irq_context_checks=counts[0],nmi_context_checks=counts[1],context_faults=counts[2],
             peak_gateway_to_rti_master_clocks=counts[3],all_field_unsafe_data_writes=counts[4],
             peak_nmi_gateway_to_rti_master_clocks=counts[5],
             sa1_bank3_mapping=0x81,memsel=1,ordinary_bg2_producer_retired=True,ordinary_window_masks_cleared=True,
             scope='Production cold boot and NMI, with a private stationary foreign owner. No live MOTU world or production TAD service admission.')
    r['pass']=r['pass'] and counts[0]>=224 and counts[1]>=2 and counts[2]==0 and counts[4]==0
    (folder/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    if not r['pass']:raise SystemExit(1)


if __name__=='__main__':main()
