"""Bounded native execution of a physical source-OBJ schedule on a constant matte.

Private boot/IRQ/NMI owner; no gameplay or production resource lease admission.
Code lives outside bank zero. DMA payload cursors advance in hardware.
"""
import argparse,hashlib,json,shutil,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_isolated_context import isolated_source
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from raster_slot_greedy import demand
from raster_obj_chr import compile as compile_chr
from actor_s5_entity_fixture import symbols
from _harness import McpSession,MESEN_EXE,_free_tcp_port


def compile_rom(base,source_path,scene,schedule,folder,timer=44,sa1_mapping=False,foreground_stress=False):
    if schedule.get('color_math')!='precomposited' or schedule.get('physical_slot_layout',{}).get('status')!='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN':raise ValueError('NATIVE_PHYSICAL_PRECOMPOSITED_SCHEDULE_REQUIRED')
    isolation=schedule.get('isolated_context')
    if not isolation:raise ValueError('NATIVE_CONTROLLED_UNDERLAY_REQUIRED')
    source,stage,_=isolated_source(source_path,tuple(isolation['underlay_rgb8']))
    expected,metadata=compose_rgb8(source,stage,scene);expected=rgb555(expected).astype('<u2')
    if schedule['source_rgb555_sha256']!=hashlib.sha256(expected.tobytes()).hexdigest():raise ValueError('NATIVE_SOURCE_CONTEXT_IDENTITY')
    _,_,pixels=demand(schedule);chr_report,objchr,oam=compile_chr(schedule)
    initial=bytearray(512);underlay=isolation['underlay_rgb8'];struct.pack_into('<H',initial,0,int(rgb555(np.array([[underlay]],dtype=np.uint8))[0,0]))
    for event in schedule['trace'][0]['updates']:struct.pack_into('<H',initial,2*(128+16*event['bank']+event['slot']),event['color'])
    code_bank,row_bank,asset_bank=0xa7,0xa8,0xaa
    code_rom,row_rom,asset_rom=(103,104,106)if sa1_mapping else(39,40,42)
    assets=bytearray(initial+oam+objchr);streams={ch:bytearray()for ch in range(1,8)};rows=[]
    for y,row in enumerate(schedule['prepared_dma_packets']):
        if row['scanline']!=y or len(row['packets'])>4:raise ValueError('NATIVE_PACKET_DOMAIN')
        counts={ch:0 for ch in range(1,8)};mask=0;packets=row['packets']if y else[]
        for i,packet in enumerate(packets):
            data=bytes.fromhex(packet['data_hex']);ch=1+2*i
            if len(data)!=packet['word_count']*2:raise ValueError('NATIVE_PACKET_LENGTH')
            streams[ch].extend(data);counts[ch]=len(data);mask|=1<<ch
            if i:streams[ch-1].append(packet['cgram_word_address']);counts[ch-1]=1;mask|=1<<(ch-1)
        rows.append(dict(counts=counts,mask=mask,first_address=packets[0]['cgram_word_address']if packets else 128))
    offsets={}
    for ch,data in streams.items():offsets[ch]=0x8000+len(assets);assets.extend(data or b'\0')
    if len(assets)>32768:raise ValueError('NATIVE_PALETTE_STREAM_BANK_CAPACITY')
    asm=['.snes','.bank 39','.org $8000','IsolatedRasterReset:','.a16','.i16',' sei',' clc',' xce',' rep #$30',' ldx #$1FFF',' txs',' lda #$0000',' tcd',' sep #$20','.a8',' lda #$00',' pha',' plb']
    def store(address,value):asm.extend([f' lda #${value:02X}',f' sta ${address:04X}'])
    for a,v in((0x4200,0),(0x420c,0),(0x2100,128),(0x420d,1),(0x2115,128)):store(a,v)
    def dma(offset,dest,size,mode,target=None):
        if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
        for a,v in((0x4370,mode),(0x4371,dest),(0x4372,offset&255),(0x4373,offset>>8),(0x4374,asset_bank),(0x4375,size&255),(0x4376,size>>8),(0x420b,128)):store(a,v)
    dma(0x8000+512+544,0x18,len(objchr),1,0x6000)
    store(0x2102,0);store(0x2103,0);dma(0x8200,4,len(oam),0)
    store(0x2121,0);dma(0x8000,0x22,512,0)
    for ch in range(1,8):
        for a,v in((0x4300+16*ch,0),(0x4301+16*ch,0x22 if ch%2 else 0x21),(0x4302+16*ch,offsets[ch]&255),(0x4303+16*ch,offsets[ch]>>8),(0x4304+16*ch,asset_bank)):store(a,v)
    for a,v in((0x2101,3|(chr_report['obj_size_mode']<<5)),(0x2105,1),(0x212c,16),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2133,0),(0x4207,timer&255),(0x4208,timer>>8)):store(a,v)
    asm.extend([' rep #$20','.a16',' lda #IsolatedRasterRow0',' sta $1E00',' sep #$20','.a8',f' lda #${row_bank:02X}',' sta $1E02',' stz $1E08',
        'IsolatedRasterWaitBlank:',' lda $4212',' and #$80',' beq IsolatedRasterWaitBlank'])
    store(0x2100,15);store(0x4200,0x90)
    asm.extend([' rep #$30','.a16','.i16',' lda #$2345',' tcd',' ldx #$5678',' ldy #$9ABC',' sep #$20','.a8',' lda #$40',' pha',' plb',' rep #$20','.a16',' lda #$1234',' sed',' sec',' cli','IsolatedRasterHold:'])
    if foreground_stress:asm.extend([' lda.l $7E1D00',' sta.l $7E1D02',' eor #$FFFF',' pha',' pla',' sep #$20','.a8',' lda.l $7E1D04',' rep #$20','.a16'])
    asm.append(' bra IsolatedRasterHold')
    asm.extend(['.org $9000','IsolatedRasterIrq:','.a16','.i16',' rep #$38',' pha',' phx',' phb',' sep #$20','.a8',' lda #$00',' pha',' plb',' lda $4211',' lda $4212',' and #$80',' bne IsolatedRasterReturn8',' rep #$20','.a16',' jml [$1E00]',
        'IsolatedRasterReturn8:','.a8','.i16',' rep #$20','IsolatedRasterReturn:','.a16','.i16',' plb',' plx',' pla','IsolatedRasterIrqRti:',' rti'])
    asm.extend(['.org $9200','IsolatedRasterNmi:','.a16','.i16',' rep #$38',' pha',' phx',' phb',' sep #$20','.a8',' lda #$00',' pha',' plb',' lda #$01',' sta $1E08',' lda $4210'])
    store(0x2121,0);dma(0x8000,0x22,512,0)
    asm.extend([' rep #$20','.a16'])
    for ch in range(1,8):asm.extend([f' lda #${offsets[ch]:04X}',f' sta ${0x4302+16*ch:04X}'])
    asm.extend([' lda #IsolatedRasterRow0',' sta $1E00',' sep #$20','.a8',' stz $1E08',' rep #$20','.a16',' plb',' plx',' pla','IsolatedRasterNmiRti:',' rti','.bank 40','.org $8000'])
    for y in range(224):
        row=rows[y];asm.extend([f'IsolatedRasterRow{y}:','.a16','.i16'])
        for ch,count in row['counts'].items():asm.extend([f' lda #${count:04X}',f' sta ${0x4305+16*ch:04X}'])
        asm.extend([' sep #$20','.a8',f' lda #${row["first_address"]:02X}',' sta $2121',f' lda #${row["mask"]:02X}',' sta $420B',' rep #$20','.a16',f' lda #IsolatedRasterRow{y+1}',' sta $1E00',' jml IsolatedRasterReturn'])
    asm.extend(['IsolatedRasterRow224:','.a16','.i16',' jml IsolatedRasterReturn'])
    path=folder/'fixture.pasm';path.write_text('\n'.join(asm)+'\n')
    run=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(path),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise ValueError('NATIVE_RASTER_ASSEMBLY')
    sy=symbols(folder/'fixture.sym');binary=(folder/'fixture.bin').read_bytes();raw=bytearray(base)
    for bank in(code_rom,row_rom,asset_rom):
        if raw[bank*32768:(bank+1)*32768]!=bytes(32768):raise ValueError('NATIVE_PRIVATE_ROM_BANK_NOT_EMPTY')
    for original_bank,target_bank in((39,code_rom),(40,row_rom)):
        section=binary[original_bank*32768:(original_bank+1)*32768].ljust(32768,b'\0')
        if sa1_mapping and original_bank==40:
            target=sy['IsolatedRasterReturn'];old=bytes([0x5c,target&255,target>>8&255,target>>16&255]);new=old[:3]+bytes([code_bank])
            if section.count(old)!=225:raise ValueError('NATIVE_RETURN_ALIAS_RELOCATION_COUNT')
            section=section.replace(old,new)
        raw[target_bank*32768:(target_bank+1)*32768]=section
    raw[asset_rom*32768:asset_rom*32768+len(assets)]=assets
    reset=struct.unpack_from('<H',raw,0x7ffc)[0]
    if reset<0x8000:raise ValueError('NATIVE_RESET_VECTOR_DOMAIN')
    raw[reset-0x8000:reset-0x8000+4]=bytes([0x5c,0,0x80,code_bank])
    raw[0x100:0x104]=bytes([0x5c,0,0x90,code_bank]);raw[0x120:0x124]=bytes([0x5c,0,0x92,code_bank])
    struct.pack_into('<H',raw,0x7fee,0x8100);struct.pack_into('<H',raw,0x7fea,0x8120)
    # Standalone LoROM fixture: production SA-1 mapping is not initialized by
    # this private reset owner and is outside this isolated timing proof.
    if not sa1_mapping:raw[0x7fd5]=0x30;raw[0x7fd6]=0
    return bytes(raw),expected,bytes(initial),oam,sy,dict(chr_report=chr_report,stream_offsets=offsets,stream_bytes={ch:len(s)for ch,s in streams.items()},asset_bytes=len(assets),source_metadata=metadata,
        private_fixture_only=True,foreground_context='BOUNDED_LONG_WRAM_STACK_AND_ACCUMULATOR_WIDTH_MIX'if foreground_stress else'HELD_BRA',actual_source_vm_execution_proven=False,code_rom_banks=[code_rom,row_rom],asset_rom_bank=asset_rom,sa1_mmc_registers_changed=False,standalone_lorom=not sa1_mapping,production_sa1_mapping_proven=sa1_mapping,production_sa1_worker_execution_proven=False,bank_zero_growth_bytes=0,irq_dma_channels=list(range(1,8)),hdma_channels=[],source_alpha_policy='BOR4086_SCREEN_RGB8_PRECOMPOSITED_ON_CONTROLLED_CONSTANT_UNDERLAY')


def observer(sy,sa1_mapping=False):
    def prg(name):v=sy[name];return((v>>16&127)+(64 if sa1_mapping else 0))*32768+(v&65535)-32768
    return '''local active=false;local restoring=false;local high=false;local address=0;local low=0;local packets={};local current=nil;local pending=nil;local faults=0;local contexts=0;local entryclock=0;local irqpeak=0;local oam={}
emu.addMemoryCallback(function(a,v)restoring=v~=0 end,emu.callbackType.write,0x1e08,0x1e08,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if not active then oam[#oam+1]=string.format('%02x',v)end end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if v==15 and not active then active=true;emu.log('ISOOAM|'..table.concat(oam,''))end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)address=v;high=false end,emu.callbackType.write,0x2121,0x2121,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if active and not restoring and v~=0 then local s=emu.getState();current={s['ppu.frameCount'],s['ppu.scanline'],0,0,0,0,0,words={}}end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if active and not restoring and current then
  local s=emu.getState();local h=(s.masterClock+4*(s['ppu.frameCount']//2))%1364
  if high then
   current[3]=current[3]+1;if h>=88 and h<1096 then current[4]=current[4]+1 end
   if current[3]==1 then current.first=s.masterClock;current[6]=h end
   current[5]=s.masterClock-current.first;current[7]=h
   current.words[#current.words+1]=address;current.words[#current.words+1]=low+(v%128)*256;address=(address+1)%256
  else low=v end
 end
 high=not high
end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
local function snapshot()local s=emu.getState();local r={};for _,k in ipairs({'a','x','y','d','dbr','sp'})do r[#r+1]=s['cpu.'..k]end;for i=1,4 do r[#r+1]=emu.read(0x7e0000+s['cpu.sp']+i,emu.memType.snesMemory)end;return r end
emu.addMemoryCallback(function()pending=snapshot();entryclock=emu.getState().masterClock end,emu.callbackType.exec,IRQ,IRQ,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 local now=snapshot();if not pending then faults=faults+1 else for i,v in ipairs(now)do if v~=pending[i]then faults=faults+1 end end end
 contexts=contexts+1;irqpeak=math.max(irqpeak,emu.getState().masterClock-entryclock);pending=nil
 if current then emu.log('ISOPACKET|'..table.concat(current,','));emu.log('ISOWORDS|'..current[1]..','..current[2]..','..table.concat(current.words,','));current=nil end
end,emu.callbackType.exec,RTI,RTI,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addEventCallback(function()if active then local s=emu.getState();emu.log('ISOFLAGS|'..s['ppu.frameCount']..','..emu.read(0x213e,emu.memType.snesMemory));emu.log('ISOCONTEXT|'..contexts..','..faults..','..irqpeak)end end,emu.eventType.endFrame)
'''.replace('IRQ',str(prg('IsolatedRasterIrq'))).replace('RTI',str(prg('IsolatedRasterIrqRti')))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source','scene','schedule','rom','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sa1-mapping',action='store_true')
    p.add_argument('--foreground-stress',action='store_true')
    p.add_argument('--timer',type=int,default=44);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    schedule=json.loads(a.schedule.read_text());raw,expected,initial,oam,sy,resources=compile_rom(a.rom.read_bytes(),a.source,json.loads(a.scene.read_text()),schedule,folder,a.timer,a.sa1_mapping,a.foreground_stress)
    rom=folder/'proof.sfc';rom.write_bytes(raw);lua=folder/'observer.lua';lua.write_text(observer(sy,a.sa1_mapping))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log')as m:
        advancement=[];count=0
        for _ in range(16):
            step=m.run_frames(1);advancement.append(step);count+=step['framesAdvanced']
            if count>=4:break
        shot=m.tool('take_screenshot',{'format':'path','path':str(folder/'screenshot.png')});cg=m.read_memory('SnesCgRam',0,512);observed_oam=m.read_memory('SnesSpriteRam',0,544);ppu=m.get_ppu_state();cpu=m.get_cpu_state()
    if Path(shot['path']).resolve()!=folder/'screenshot.png':shutil.copyfile(shot['path'],folder/'screenshot.png')
    actual=rgb555(np.asarray(Image.open(folder/'screenshot.png').convert('RGB')))
    log=(folder/'mesen.log').read_text();packets=[];words=[];contexts=[];flags=[];oamlog=[]
    for line in log.splitlines():
        for token,target in(('ISOPACKET|',packets),('ISOWORDS|',words),('ISOCONTEXT|',contexts),('ISOFLAGS|',flags)):
            if token in line:target.append(list(map(int,line.split(token,1)[1].split(','))))
        if 'ISOOAM|'in line:oamlog.append(line.split('ISOOAM|',1)[1])
    frames=sorted({r[0]for r in words if r[0]>=1});complete=[];word_faults=0
    expected_rows={r['scanline']:[v for q in r['packets']for i in range(q['word_count'])for v in(q['cgram_word_address']+i,int.from_bytes(bytes.fromhex(q['data_hex'])[2*i:2*i+2],'little'))]for r in schedule['prepared_dma_packets']if r['scanline']and r['packets']}
    for frame in frames:
        seen={r[1]:r[2:]for r in words if r[0]==frame}
        if seen==expected_rows:complete.append(frame)
        else:word_faults+=1
    identity=actual.shape==expected.shape and np.array_equal(actual,expected);context=contexts[-1]if contexts else[0,-1,0]
    result=dict(schema='BYOR_CONTROLLED_SOURCE_RASTER_OBJ_NATIVE_V1',status='PASS'if identity and len(complete)>=2 and word_faults==0 and sum(r[3]for r in packets)==0 and observed_oam==oam and oamlog==[oam.hex()]and context[1]==0 and all(not(r[1]&192)for r in flags)else'FAIL',
        pixel_identity_verified=identity,pixel_mismatches=int(np.count_nonzero(actual!=expected))if actual.shape==expected.shape else None,
        complete_packet_fields=complete,packet_identity_faults=word_faults,unsafe_high_commits=sum(r[3]for r in packets),
        peak_observed_commit_span=max((r[4]for r in packets),default=None),first_high_hclock_range=[min((r[5]for r in packets),default=0),max((r[5]for r in packets),default=0)],
        irq_context_checks=context[0],irq_context_faults=context[1],peak_irq_entry_to_rti_master_clocks=context[2],
        oam_ram_identity_verified=observed_oam==oam,oam_observer_identity_verified=oamlog==[oam.hex()],obj_overflow_flags=flags,
        source_frame_sha256=next(l['sha256']for l in resources['source_metadata']['layers']if l['kind'].startswith('actor:')),
        compiled_schedule_sha256=schedule['compiled_schedule_sha256'],rom_sha256=hashlib.sha256(raw).hexdigest(),expected_rgb555_sha256=hashlib.sha256(expected.tobytes()).hexdigest(),
        timer=a.timer,resources=resources,frame_advancement=advancement,ppu=ppu,cpu=cpu,no_color_reduction=True,
        production_runtime_admitted=False,authored_stage_and_concurrent_actors_proven=False,motu_gameplay_proven=False)
    (folder/'expected.rgb555').write_bytes(expected.tobytes());(folder/'cgram.bin').write_bytes(cg);(folder/'oam.bin').write_bytes(observed_oam)
    (folder/'cgram-observer.json').write_text(json.dumps(dict(packets=packets,words=words),separators=(',',':'))+'\n');(folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','pixel_mismatches','complete_packet_fields','unsafe_high_commits','peak_observed_commit_span','first_high_hclock_range','irq_context_checks','irq_context_faults','production_runtime_admitted')}))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
