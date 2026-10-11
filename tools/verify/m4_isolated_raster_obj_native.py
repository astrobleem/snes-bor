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


def lease_queue_vram(occupied,byte_count):
    """Private fixture allocation from exact uploaded ranges, never live leases."""
    if type(byte_count)is not int or byte_count<0 or byte_count>4096 or byte_count%2:raise ValueError('NATIVE_QUEUE_VRAM_EXTENT')
    ranges=sorted(occupied)
    if any(type(a)is not int or type(b)is not int or not 0<=a<=b<=65536 for a,b in ranges):raise ValueError('NATIVE_QUEUE_VRAM_OCCUPIED_DOMAIN')
    cursor=0
    for left,right in ranges+[(65536,65536)]:
        if cursor+byte_count<=left:return cursor
        cursor=max(cursor,right);cursor+=(cursor%2)
    raise ValueError('NATIVE_QUEUE_VRAM_NO_DISJOINT_LEASE')


def compile_rom(base,source_path,scene,schedule,folder,timer=44,sa1_mapping=False,foreground_stress=False,production_nmi_services=False,nmi_queue_bytes=512,foreground_wai=False,prepare_next_line=False,control_traffic=None,delta_control_traffic=False,controls_before_palette=False,authored_context=None):
    if production_nmi_services and(not sa1_mapping or not 0<=nmi_queue_bytes<=4096 or nmi_queue_bytes%2):raise ValueError('NATIVE_PRODUCTION_NMI_SERVICE_DOMAIN')
    if foreground_wai and foreground_stress:raise ValueError('NATIVE_WAI_AND_FOREGROUND_STRESS_CONFLICT')
    if delta_control_traffic and control_traffic is None:raise ValueError('NATIVE_DELTA_CONTROL_TRAFFIC_REQUIRED')
    if controls_before_palette and control_traffic is None:raise ValueError('NATIVE_PREPALETTE_CONTROL_TRAFFIC_REQUIRED')
    control_rows={}
    authored_main=authored_context is not None and schedule.get('color_math')=='additive'
    if control_traffic is not None:
        if not control_traffic.get('scanline_math_controls_source_bound'):raise ValueError('NATIVE_SOURCE_BOUND_CONTROL_TRAFFIC_REQUIRED')
        mode_bits={'add':0,'half-add':0x40,'subtract':0x80,'half-subtract':0xc0}
        for key,descriptor in control_traffic['compiled_color_window_descriptors'].items():
            y=int(key);bounds=descriptor['bounds'];mode=control_traffic['selected_modes'][str(y)]
            if not 0<=y<224 or len(bounds)!=2 or any(len(pair)!=2 or any(type(v)is not int or not 0<=v<=255 for v in pair)for pair in bounds)or mode not in mode_bits:raise ValueError('NATIVE_CONTROL_TRAFFIC_DOMAIN')
            if descriptor['wobjsel_color_bits']&~0xf0 or descriptor['wobjlog_color_bits']not in(0,4)or descriptor.get('cgwsel_clip_and_prevent_bits')!=0x10:raise ValueError('NATIVE_CONTROL_WINDOW_ROUTING_DOMAIN')
            control_rows[y]=[[0x2126,bounds[0][0]],[0x2127,bounds[0][1]],[0x2128,bounds[1][0]],[0x2129,bounds[1][1]],[0x2125,descriptor['wobjsel_color_bits']],[0x212b,descriptor['wobjlog_color_bits']],[0x2131,mode_bits[mode]|(0x10 if authored_main else 0)]]
    constant_controls={}
    if controls_before_palette and control_rows:
        for address in(0x2125,0x212b):
            values={dict(row)[address]for row in control_rows.values()}
            if len(values)==1:constant_controls[address]=next(iter(values))
    if delta_control_traffic:
        previous={a:0 for a in(0x2125,0x2126,0x2127,0x2128,0x2129,0x212b,0x2131)};planned={}
        for y,desired in sorted(control_rows.items()):
            row=[]
            for i in(0,2):
                pair=desired[i:i+2]
                if any(previous[a]!=v for a,v in pair):row.extend(pair)
            row.extend((a,v)for a,v in desired[4:]if previous[a]!=v)
            for a,v in desired:previous[a]=v
            if row:planned[y]=[list(value)for value in row]
        control_rows=planned
    if constant_controls:
        control_rows={y:[(address,value)for address,value in row if address not in constant_controls]for y,row in control_rows.items()}
    production=symbols(Path('src/main.sym'))if production_nmi_services else {}
    if production_nmi_services:
        address=production['nmi_handler']&65535
        wanted=b'\x22'+production['StageWater_Nmi'].to_bytes(3,'little')+b'\x20'+(production['Core_Nmi_Play']&65535).to_bytes(2,'little')+b'\x40'
        if base[address-0x8000:address-0x8000+8]!=wanted:raise ValueError('NATIVE_PRODUCTION_NMI_AUTHORITY')
    if schedule.get('physical_slot_layout',{}).get('status')!='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN':raise ValueError('NATIVE_PHYSICAL_PRECOMPOSITED_SCHEDULE_REQUIRED')
    bg_assets=[];underlay_report=None
    if authored_context is None:
        if schedule.get('color_math')!='precomposited':raise ValueError('NATIVE_PHYSICAL_PRECOMPOSITED_SCHEDULE_REQUIRED')
        isolation=schedule.get('isolated_context')
        if not isolation:raise ValueError('NATIVE_CONTROLLED_UNDERLAY_REQUIRED')
        source,stage,_=isolated_source(source_path,tuple(isolation['underlay_rgb8']))
        expected,metadata=compose_rgb8(source,stage,scene);expected=rgb555(expected).astype('<u2')
    else:
        if authored_main:
            if control_traffic is None or not schedule.get('scanline_math_controls_source_bound')or control_traffic.get('source_rgb555_sha256')!=schedule.get('source_rgb555_sha256')or control_traffic.get('metadata')!=schedule.get('metadata')or set(map(int,control_traffic['compiled_color_window_descriptors']))!=set(range(224)):raise ValueError('NATIVE_AUTHORED_MAIN_COMPLETE_SOURCE_CONTROLS_REQUIRED')
        elif control_traffic is not None or schedule.get('color_math')!='subscreen-additive' or not schedule.get('main_screen_obj_disabled'):raise ValueError('NATIVE_AUTHORED_CONSTANT_SUBSCREEN_ROUTING_REQUIRED')
        from source_obj_underlay import compile_underlay
        from raster_slot_refine import verify_packets
        from raster_obj_math_cover import apply_math
        verify_packets(schedule)
        expected=np.asarray(authored_context['expected'],dtype='<u2');metadata=authored_context['metadata']
        background=np.asarray(authored_context['background'],dtype='<u2')
        if background.shape!=(224,256)or expected.shape!=background.shape or metadata!=schedule.get('metadata'):raise ValueError('NATIVE_AUTHORED_CONTEXT_IDENTITY')
        replay=background.copy()
        for p,image in zip(schedule['pieces'],demand(schedule)[2]):
            for ly,lx in zip(*np.where(image>=0)):
                y,x=p['y']+int(ly),p['x']+int(lx)
                if authored_main:
                    from raster_math_windows import evaluate
                    enabled=p['bank']>=4 and evaluate(control_traffic['compiled_color_window_descriptors'][str(y)],x)
                    replay[y,x]=apply_math(int(image[ly,lx]),int(background[y,x]),control_traffic['selected_modes'][str(y)])if enabled else int(image[ly,lx])
                else:replay[y,x]=apply_math(int(image[ly,lx]),int(background[y,x]),'add')
        if not np.array_equal(replay,expected):raise ValueError('NATIVE_AUTHORED_COMPLETE_ALPHA_PIXEL_IDENTITY')
        underlay_report,bgchr,bgmap,bgpal=compile_underlay(background)
        for offset in range(0,len(bgchr),32768):
            bg_assets.append(dict(bank=0xab+offset//32768,rom=(107 if sa1_mapping else 43)+offset//32768,target=offset//2,data=bgchr[offset:offset+32768]))
        bg_assets.append(dict(bank=0xad,rom=109 if sa1_mapping else 45,target=0x5800,data=bgmap))
    if schedule['source_rgb555_sha256']!=hashlib.sha256(expected.tobytes()).hexdigest():raise ValueError('NATIVE_SOURCE_CONTEXT_IDENTITY')
    _,_,pixels=demand(schedule);chr_report,objchr,oam=compile_chr(schedule)
    queue_vram_byte_address=0
    queue_vram_lease=None
    if authored_context is not None and production_nmi_services:
        occupied=[[2*a['target'],2*a['target']+len(a['data'])]for a in bg_assets]+[[0xc000,0xc000+len(objchr)]]
        queue_vram_byte_address=lease_queue_vram(occupied,nmi_queue_bytes)
        queue_vram_lease=dict(scope='PRIVATE_STATIC_UPLOADED_ASSETS_ONLY',occupied_byte_ranges=occupied,
            queue_byte_range=[queue_vram_byte_address,queue_vram_byte_address+nmi_queue_bytes],
            live_background_streaming_admitted=False,production_runtime_admitted=False)
    initial=bytearray(512)
    if authored_context is None:
        underlay=isolation['underlay_rgb8'];struct.pack_into('<H',initial,0,int(rgb555(np.array([[underlay]],dtype=np.uint8))[0,0]))
    else:initial[:256]=bgpal
    for event in schedule['trace'][0]['updates']:struct.pack_into('<H',initial,2*(128+16*event['bank']+event['slot']),event['color'])
    code_bank,row_bank,asset_bank=0xa7,0xa8,0xaa
    code_rom,row_rom,asset_rom=(103,104,106)if sa1_mapping else(39,40,42)
    assets=bytearray(initial+oam+objchr);queue_source=0x8000+len(assets)
    if production_nmi_services:assets.extend(bytes((i*13+7)&255 for i in range(nmi_queue_bytes)))
    streams={ch:bytearray()for ch in range(1,8)};rows=[]
    for y,row in enumerate(schedule['prepared_dma_packets']):
        if row['scanline']!=y or len(row['packets'])>4:raise ValueError('NATIVE_PACKET_DOMAIN')
        counts={ch:0 for ch in range(1,8)};mask=0;packets=row['packets']if y else[]
        for i,packet in enumerate(packets):
            data=bytes.fromhex(packet['data_hex']);ch=1+2*i
            if len(data)!=packet['word_count']*2:raise ValueError('NATIVE_PACKET_LENGTH')
            streams[ch].extend(data);counts[ch]=len(data);mask|=1<<ch
            if i:streams[ch-1].append(packet['cgram_word_address']);counts[ch-1]=1;mask|=1<<(ch-1)
        rows.append(dict(counts=counts,mask=mask,first_address=packets[0]['cgram_word_address']if packets else 128))
    if prepare_next_line and any(n>255 for row in rows for n in row['counts'].values()):raise ValueError('NATIVE_PREPARED_BYTE_COUNT_DOMAIN')
    offsets={}
    for ch,data in streams.items():offsets[ch]=0x8000+len(assets);assets.extend(data or b'\0')
    if len(assets)>32768:raise ValueError('NATIVE_PALETTE_STREAM_BANK_CAPACITY')
    asm=['.snes','.bank 39','.org $8000','IsolatedRasterReset:','.a16','.i16',' sei',' clc',' xce',' rep #$30',' ldx #$1FFF',' txs',' lda #$0000',' tcd',' sep #$20','.a8',' lda #$00',' pha',' plb']
    def store(address,value):asm.extend([f' lda #${value:02X}',f' sta ${address:04X}'])
    for a,v in((0x4200,0),(0x420c,0),(0x2100,128),(0x420d,1),(0x2115,128)):store(a,v)
    if production_nmi_services:
        asm.extend([' rep #$20','.a16',' lda #$0000',' ldx #$0000','IsolatedRasterColdRamClear:','.a16','.i16',' sta.l $7E0000,x',' sta.l $7F0000,x',' inx',' inx',' bne IsolatedRasterColdRamClear',' sep #$20','.a8'])
    def dma(offset,dest,size,mode,target=None,source_bank=None):
        if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
        for a,v in((0x4370,mode),(0x4371,dest),(0x4372,offset&255),(0x4373,offset>>8),(0x4374,asset_bank if source_bank is None else source_bank),(0x4375,size&255),(0x4376,size>>8),(0x420b,128)):store(a,v)
    for asset in bg_assets:dma(0x8000,0x18,len(asset['data']),1,asset['target'],asset['bank'])
    dma(0x8000+512+544,0x18,len(objchr),1,0x6000)
    store(0x2102,0);store(0x2103,0);dma(0x8200,4,len(oam),0)
    store(0x2121,0);dma(0x8000,0x22,512,0)
    for ch in range(1,8):
        for a,v in((0x4300+16*ch,0),(0x4301+16*ch,0x22 if ch%2 else 0x21),(0x4302+16*ch,offsets[ch]&255),(0x4303+16*ch,offsets[ch]>>8),(0x4304+16*ch,asset_bank)):store(a,v)
    if prepare_next_line:
        for ch in range(1,8):store(0x4306+16*ch,0)
    for a,v in((0x2101,3|(chr_report['obj_size_mode']<<5)),(0x2105,1),(0x212c,16),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2133,0),(0x4207,timer&255),(0x4208,timer>>8)):store(a,v)
    if authored_context is not None:
        for a,v in((0x2105,3),(0x2107,0x58),(0x210b,0),(0x210d,0),(0x210d,0),(0x210e,255),(0x210e,255),(0x212c,17 if authored_main else 1),(0x212d,1 if authored_main else 16),(0x2125,0),(0x212b,0),(0x2130,0x12 if authored_main else 2),(0x2131,0x10 if authored_main else 1),(0x2132,0xe0)):store(a,v)
    for address,value in constant_controls.items():store(address,value)
    if production_nmi_services:
        asm.extend([' rep #$20','.a16',' lda #$0000',' ldx #$003E','IsolatedRasterNmiStateClear:','.a16','.i16',' sta.l $7E5000,x',' dex',' dex',' bpl IsolatedRasterNmiStateClear',' ldx #$003E','IsolatedRasterDmaStateClear:','.a16','.i16',f" sta.l ${production['DmaQueue']:06X},x",' dex',' dex',' bpl IsolatedRasterDmaStateClear'])
        for name in('DmaQueue_CurrentSlot','DmaQueue_BudgetTotal','SourceClock4086_Ready','StageWater_Enabled','StageWater_Pending','StageFp_BG2Active','StageFp_BG2Loaded','StreamScrollFp_Enabled','StreamScrollFp_ColPending','Oam_UploadFlag'):
            asm.extend([f" sta.l ${production[name]:06X}"])
        asm.extend([' sep #$20','.a8'])
        for address,value in((0x7e5003,0x90),(0x7e5004,15),(0x7e500c,16),(0x7e500f,1)):
            asm.extend([f' lda #${value:02X}',f' sta.l ${address:06X}'])
    if authored_context is not None and production_nmi_services:
        for address,value in((0x7e500c,17 if authored_main else 1),(0x7e500f,3),(0x7e5010,0x58),(0x7e5019,255),(0x7e501a,255)):
            asm.extend([f' lda #${value:02X}',f' sta.l ${address:06X}'])
    asm.extend([' rep #$20','.a16',' lda #IsolatedRasterRow0',' sta $1E00',' sep #$20','.a8',f' lda #${row_bank:02X}',' sta $1E02',' stz $1E08',
        'IsolatedRasterWaitBlank:',' lda $4212',' and #$80',' beq IsolatedRasterWaitBlank'])
    asm.extend([' rep #$20','.a16',' lda #$B401',' sta $1E04',' sep #$20','.a8'])
    store(0x2100,15);store(0x4200,0x90)
    asm.extend([' rep #$30','.a16','.i16',(' lda #$4300'if foreground_wai else' lda #$2345'),' tcd',' ldx #$5678',' ldy #$9ABC',' sep #$20','.a8',(' lda #$00'if foreground_wai else' lda #$40'),' pha',' plb',' rep #$20','.a16',' lda #$1234',' sed',' sec',' cli','IsolatedRasterHold:'])
    if foreground_wai:asm.append(' wai')
    if foreground_stress:asm.extend([' lda.l $7E1D00',' sta.l $7E1D02',' eor #$FFFF',' pha',' pla',' sep #$20','.a8',' lda.l $7E1D04',' rep #$20','.a16'])
    asm.append(' bra IsolatedRasterHold')
    asm.extend(['.org $9000','IsolatedRasterIrq:','.a16','.i16',' rep #$38',' pha'])
    if not foreground_wai:asm.extend([' phx',' phb',' sep #$20','.a8',' lda #$00',' pha',' plb'])
    else:asm.extend([' sep #$20','.a8'])
    asm.extend([' lda $4211',' lda $4212',' and #$80',' bne IsolatedRasterReturn8',' rep #$20','.a16',' jml [$1E00]',
        'IsolatedRasterReturn8:','.a8','.i16',' rep #$20','IsolatedRasterReturn:','.a16','.i16'])
    if not foreground_wai:asm.extend([' plb',' plx'])
    asm.extend([' pla','IsolatedRasterIrqRti:',' rti'])
    asm.extend(['.org $9200','IsolatedRasterNmi:','.a16','.i16',' rep #$38',' pha',' phx',' phb',' sep #$20','.a8',' lda #$00',' pha',' plb',' lda #$01',' sta $1E08',' lda $4210'])
    if production_nmi_services:
        asm.extend([' rep #$20','.a16',' phd',' lda #$0000',' tcd'])
        for name in('Nmi_FrameBusy','Nmi_Busy'):
            asm.extend([f" sta.l ${production[name]:06X}"])
        if nmi_queue_bytes:
            for offset,value in((0,nmi_queue_bytes),(2,queue_vram_byte_address),(5,queue_source)):
                asm.extend([f' lda #${value:04X}',f" sta.l ${production['DmaQueue']+offset:06X}"])
        asm.extend([' sep #$20','.a8'])
        if nmi_queue_bytes:
            for offset,value in((7,asset_bank),(4,0x40)):
                asm.extend([f' lda #${value:02X}',f" sta.l ${production['DmaQueue']+offset:06X}"])
        asm.extend([f' lda #${code_bank:02X}',' pha',' pea IsolatedRasterProductionNmiReturn',' php',f" jml ${production['nmi_handler']:06X}",'IsolatedRasterProductionNmiReturn:','.a8','.i16'])
    store(0x2121,128);dma(0x8100,0x22,256,0)
    asm.extend([' rep #$20','.a16'])
    for ch in range(1,8):asm.extend([f' lda #${offsets[ch]:04X}',f' sta ${0x4302+16*ch:04X}'])
    if production_nmi_services:asm.append(' pld')
    asm.extend([' lda #IsolatedRasterRow0',' sta $1E00',' sep #$20','.a8',' stz $1E08',' rep #$20','.a16',' plb',' plx',' pla','IsolatedRasterNmiRti:',' rti','.bank 40','.org $8000'])
    def emit_controls(y,leave_a8=False,part='all',a8_already=False):
        if y not in control_rows:return False
        controls=dict(control_rows[y])
        for address in(0x2126,0x2128):
            if part!='bytes'and address in controls:
                value=controls[address]|controls[address+1]<<8
                asm.extend([f' lda #${value:04X}',f' sta ${address:04X}']if value else[f' stz ${address:04X}'])
        byte_writes=[(address,value)for address,value in control_rows[y]if part!='words'and address in(0x2125,0x212b,0x2131)]
        if byte_writes:
            if not a8_already:asm.extend([' sep #$20','.a8'])
            for address,value in byte_writes:asm.extend([f' lda #${value:02X}',f' sta ${address:04X}']if value else[f' stz ${address:04X}'])
            if not leave_a8:asm.extend([' rep #$20','.a16'])
        return bool(byte_writes)and leave_a8
    for y in range(224):
        row=rows[y];asm.extend([f'IsolatedRasterRow{y}:','.a16','.i16'])
        control_a8=emit_controls(y,bool(row['mask']))if controls_before_palette else False
        if row['mask']:
            if not prepare_next_line:
                for ch,count in row['counts'].items():asm.extend([f' lda #${count:04X}',f' sta ${0x4305+16*ch:04X}'])
            if not control_a8:asm.append(' sep #$20')
            asm.extend(['.a8',f' lda #${row["first_address"]:02X}',' sta $2121',f' lda #${row["mask"]:02X}',' sta $420B',' rep #$20','.a16'])
        if not controls_before_palette:emit_controls(y,part='words')
        if prepare_next_line and y+1<len(rows) and rows[y+1]['mask']:
            asm.extend([' sep #$20','.a8'])
            count_groups={}
            for ch,count in rows[y+1]['counts'].items():
                if not count:continue
                count_groups.setdefault(count,[]).append(ch)
            for count,channels in count_groups.items():
                asm.append(f' lda #${count:02X}')
                for ch in channels:
                    target=f'${0x05+16*ch:02X}'if foreground_wai else f'${0x4305+16*ch:04X}'
                    asm.append(f' sta {target}')
            if not controls_before_palette:emit_controls(y,leave_a8=True,part='bytes',a8_already=True)
            asm.extend([' rep #$20','.a16'])
        elif not controls_before_palette:emit_controls(y,part='bytes')
        asm.extend([f' lda #IsolatedRasterRow{y+1}',' sta $1E00',' jml IsolatedRasterReturn'])
    asm.extend(['IsolatedRasterRow224:','.a16','.i16',' jml IsolatedRasterReturn'])
    path=folder/'fixture.pasm';path.write_text('\n'.join(asm)+'\n')
    run=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(path),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise ValueError('NATIVE_RASTER_ASSEMBLY')
    sy=symbols(folder/'fixture.sym');binary=(folder/'fixture.bin').read_bytes();raw=bytearray(base)
    for bank in(code_rom,row_rom,asset_rom,*(a['rom']for a in bg_assets)):
        if raw[bank*32768:(bank+1)*32768]!=bytes(32768):raise ValueError('NATIVE_PRIVATE_ROM_BANK_NOT_EMPTY')
    for original_bank,target_bank in((39,code_rom),(40,row_rom)):
        section=binary[original_bank*32768:(original_bank+1)*32768].ljust(32768,b'\0')
        if sa1_mapping and original_bank==40:
            target=sy['IsolatedRasterReturn'];old=bytes([0x5c,target&255,target>>8&255,target>>16&255]);new=old[:3]+bytes([code_bank])
            if section.count(old)!=225:raise ValueError('NATIVE_RETURN_ALIAS_RELOCATION_COUNT')
            section=section.replace(old,new)
        raw[target_bank*32768:(target_bank+1)*32768]=section
    raw[asset_rom*32768:asset_rom*32768+len(assets)]=assets
    for asset in bg_assets:raw[asset['rom']*32768:asset['rom']*32768+len(asset['data'])]=asset['data']
    reset=struct.unpack_from('<H',raw,0x7ffc)[0]
    if reset<0x8000:raise ValueError('NATIVE_RESET_VECTOR_DOMAIN')
    raw[reset-0x8000:reset-0x8000+4]=bytes([0x5c,0,0x80,code_bank])
    raw[0x100:0x104]=bytes([0x5c,0,0x90,code_bank]);raw[0x120:0x124]=bytes([0x5c,0,0x92,code_bank])
    struct.pack_into('<H',raw,0x7fee,0x8100);struct.pack_into('<H',raw,0x7fea,0x8120)
    # Standalone LoROM fixture: production SA-1 mapping is not initialized by
    # this private reset owner and is outside this isolated timing proof.
    if not sa1_mapping:raw[0x7fd5]=0x30;raw[0x7fd6]=0
    resources=dict(chr_report=chr_report,stream_offsets=offsets,stream_bytes={ch:len(s)for ch,s in streams.items()},asset_bytes=len(assets),source_metadata=metadata,empty_scanline_dma_setup_skipped=sum(not r['mask']for r in rows),
        private_fixture_only=True,controls_before_palette=controls_before_palette,delta_control_traffic=delta_control_traffic,control_traffic_rows=control_rows,control_traffic_math_layer_selection_disabled=control_traffic is not None,foreground_context='BOUNDED_LONG_WRAM_STACK_AND_ACCUMULATOR_WIDTH_MIX'if foreground_stress else'WAI_EACH_RASTER_IRQ'if foreground_wai else'HELD_BRA',dma_counts_prepared_previous_line=prepare_next_line,prepared_count_high_bytes_zero=prepare_next_line,idle_irq_bank_zero_abi=foreground_wai,idle_irq_x_untouched=foreground_wai,idle_irq_direct_page=0x4300 if foreground_wai else None,actual_source_vm_execution_proven=False,production_nmi_service_code_executed=production_nmi_services,production_nmi_queue_bytes=nmi_queue_bytes if production_nmi_services else 0,production_queue_registration_executed=False,production_queue_byte_cap=2816,within_production_queue_byte_cap=nmi_queue_bytes<2816 if production_nmi_services else None,service_path_stress_only=production_nmi_services and nmi_queue_bytes>=2816,initial_palette_vblank_bytes=256,raster_cgram_owned_word_range=[128,255],production_cold_boot_proven=False,code_rom_banks=[code_rom,row_rom],asset_rom_bank=asset_rom,sa1_mmc_registers_changed=False,standalone_lorom=not sa1_mapping,production_sa1_mapping_proven=sa1_mapping,production_sa1_worker_execution_proven=False,bank_zero_growth_bytes=0,irq_dma_channels=list(range(1,8)),hdma_channels=[],source_alpha_policy='BOR4086_SCREEN_RGB8_PRECOMPOSITED_ON_CONTROLLED_CONSTANT_UNDERLAY')
    resources.update(production_queue_vram_byte_address=queue_vram_byte_address,production_queue_private_vram_lease=queue_vram_lease)
    resources['hoisted_constant_controls']=constant_controls
    if authored_context is not None:
        resources.update(underlay=underlay_report,obj_operand_screen='main'if authored_main else'subscreen',main_obj_disabled=not authored_main,source_alpha_policy='EXACT_BOR4086_SCREEN_RGB8_THEN_RGB555',authored_source_context_bound=True,
            background_asset_banks=[a['bank']for a in bg_assets],background_asset_rom_banks=[a['rom']for a in bg_assets],background_asset_bytes=sum(len(a['data'])for a in bg_assets),
            concurrent_actor_layer_routing_proven=False,full_field_native_identity_still_required=True)
    resources.update(authored_main_screen_obj_math=authored_main,
        control_traffic_math_layer_selection_disabled=control_traffic is not None and not authored_main)
    if authored_context is not None:resources['source_alpha_policy']='EXACT_BOR4086_SCREEN_RGB8_THEN_RGB555'
    return bytes(raw),expected,bytes(initial),oam,sy,resources


def observer(sy,sa1_mapping=False,queue_address=0,queue_bytes=0,control_traffic=False,physical_cgram=False,foreground_wai=False,queue_vram_byte_address=0):
    def prg(name):v=sy[name];return((v>>16&127)+(64 if sa1_mapping else 0))*32768+(v&65535)-32768
    register_observer=''
    if control_traffic:
        row_map='{'+','.join('['+str(prg('IsolatedRasterRow'+str(y)))+']='+str(y)for y in range(224))+'}'
        register_observer="local controlRow=-1;local rowMap="+row_map+"\nfor address,y in pairs(rowMap)do local row=y;emu.addMemoryCallback(function()controlRow=row end,emu.callbackType.exec,address,address,emu.cpuType.snes,emu.memType.snesPrgRom)end\nemu.addMemoryCallback(function(a,v)if active and not restoring and(a==0x2125 or(a>=0x2126 and a<=0x2129)or a==0x212b or a==0x2131)then local s=emu.getState();local h=(s.masterClock+4*(s['ppu.frameCount']//2))%1364;emu.log('ISOREG|'..s['ppu.frameCount']..','..controlRow..','..s['ppu.scanline']..','..h..','..a..','..v)end end,emu.callbackType.write,0x2125,0x2131,emu.cpuType.snes,emu.memType.snesMemory)\n"
    lua='''local active=false;local restoring=false;local high=false;local address=0;local low=0;local packets={};local current=nil;local pending=nil;local faults=0;local contexts=0;local entryclock=0;local irqpeak=0;local oam={};local nmiPending=nil;local nmiClock=0;local nmiChecks=0;local nmiFaults=0;local nmiPeak=0;local nmiStartFrame=0;local nmiStartLine=0
emu.addMemoryCallback(function(a,v)restoring=v~=0 end,emu.callbackType.write,0x1e08,0x1e08,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if not active then oam[#oam+1]=string.format('%02x',v)end end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if v==15 and not active then active=true;emu.log('ISOOAM|'..table.concat(oam,''))end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)address=v;high=false end,emu.callbackType.write,0x2121,0x2121,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if active and restoring and v~=0 then local s=emu.getState();local n=emu.read(0x4375,emu.memType.snesMemory)+256*emu.read(0x4376,emu.memType.snesMemory);emu.log('ISONMIDMA|'..s['ppu.frameCount']..','..emu.read(0x4371,emu.memType.snesMemory)..','..n)end;if active and not restoring and v~=0 then local s=emu.getState();current={s['ppu.frameCount'],s['ppu.scanline'],0,0,0,0,0,words={}}end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
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
emu.addMemoryCallback(function()nmiPending=snapshot();local s=emu.getState();nmiClock=s.masterClock;nmiStartFrame=s['ppu.frameCount'];nmiStartLine=s['ppu.scanline'] end,emu.callbackType.exec,NMI,NMI,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()local now=snapshot();if not nmiPending then nmiFaults=nmiFaults+1 else for i,v in ipairs(now)do if v~=nmiPending[i]then nmiFaults=nmiFaults+1 end end end;nmiChecks=nmiChecks+1;nmiPeak=math.max(nmiPeak,emu.getState().masterClock-nmiClock);nmiPending=nil;local s=emu.getState();emu.log('ISONMICONTEXT|'..nmiChecks..','..nmiFaults..','..nmiPeak..','..nmiStartFrame..','..nmiStartLine..','..s['ppu.frameCount']..','..s['ppu.scanline'])end,emu.callbackType.exec,NMIRTI,NMIRTI,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()pending=snapshot();entryclock=emu.getState().masterClock end,emu.callbackType.exec,IRQ,IRQ,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 local now=snapshot();if not pending then faults=faults+1 else for i,v in ipairs(now)do if v~=pending[i]then faults=faults+1 end end end
 contexts=contexts+1;irqpeak=math.max(irqpeak,emu.getState().masterClock-entryclock);pending=nil
 if current then emu.log('ISOPACKET|'..table.concat(current,','));emu.log('ISOWORDS|'..current[1]..','..current[2]..','..table.concat(current.words,','));current=nil end
end,emu.callbackType.exec,RTI,RTI,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addEventCallback(function()if active then local s=emu.getState();emu.log('ISOFLAGS|'..s['ppu.frameCount']..','..emu.read(0x213e,emu.memType.snesMemory));emu.log('ISOCONTEXT|'..contexts..','..faults..','..irqpeak)end end,emu.eventType.endFrame)
'''.replace("nmiChecks=nmiChecks+1;", "nmiChecks=nmiChecks+1;local bad=0;for i=0,"+str(queue_bytes-1)+" do if emu.read(i+"+str(queue_vram_byte_address)+",emu.memType.snesVideoRam)~=(i*13+7)%256 then bad=bad+1 end end;emu.log('ISONMIQUEUE|'..nmiChecks..','..bad..','..emu.read("+str(queue_address+4)+",emu.memType.snesMemory));" if queue_address else "nmiChecks=nmiChecks+1;").replace('NMIRTI',str(prg('IsolatedRasterNmiRti'))).replace('NMI,NMI',str(prg('IsolatedRasterNmi'))+','+str(prg('IsolatedRasterNmi'))).replace('IRQ',str(prg('IsolatedRasterIrq'))).replace('RTI',str(prg('IsolatedRasterIrqRti')))+register_observer
    if physical_cgram:
        lua='local planned={};local initialShadow={};\n'+lua
        lua=lua.replace('restoring=v~=0 end','restoring=v~=0;if restoring and active then for i=0,511 do planned[i]=initialShadow[i]end end end')
        lua=lua.replace('active=true;emu.log',"for i=0,511 do initialShadow[i]=emu.read(i,emu.memType.snesCgRam);planned[i]=initialShadow[i]end;active=true;emu.log")
        lua=lua.replace('current.words[#current.words+1]=address;', 'planned[2*address]=low;planned[2*address+1]=v%128;current.words[#current.words+1]=address;')
        lua=lua.replace("if current then emu.log('ISOPACKET|'", "if current then local bad=0;for i=0,511 do if emu.read(i,emu.memType.snesCgRam)~=planned[i]then bad=bad+1 end end;emu.log('ISOCGRAM|'..current[1]..','..current[2]..','..bad);emu.log('ISOPACKET|'")
    if control_traffic:
        lua+="\nlocal phaseStart=nil;local function phase()local s=emu.getState();return {s['ppu.frameCount'],s['ppu.scanline'],(s.masterClock+4*(s['ppu.frameCount']//2))%1364,s.masterClock}end\n"
        lua+=f"emu.addMemoryCallback(function()if active then phaseStart=phase()end end,emu.callbackType.exec,{prg('IsolatedRasterIrq')},{prg('IsolatedRasterIrq')},emu.cpuType.snes,emu.memType.snesPrgRom)\n"
        lua+=f"emu.addMemoryCallback(function()if active and phaseStart then local finish=phase();emu.log('ISOIRQPHASE|'..table.concat(phaseStart,',')..','..table.concat(finish,',')..','..controlRow);phaseStart=nil end end,emu.callbackType.exec,{prg('IsolatedRasterIrqRti')},{prg('IsolatedRasterIrqRti')},emu.cpuType.snes,emu.memType.snesPrgRom)\n"
        if foreground_wai:lua+=f"emu.addMemoryCallback(function()if active then emu.log('ISOFGWAIT|'..table.concat(phase(),',')..','..controlRow)end end,emu.callbackType.exec,{prg('IsolatedRasterHold')},{prg('IsolatedRasterHold')},emu.cpuType.snes,emu.memType.snesPrgRom)\n"
    return lua


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source','scene','schedule','rom','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage',help='Bind an authored source underlay with subscreen ADD or complete source-bound main OBJ controls; private proof only.')
    p.add_argument('--sa1-mapping',action='store_true')
    p.add_argument('--foreground-stress',action='store_true')
    p.add_argument('--foreground-wai',action='store_true',help='Measure an explicitly idle 65816 foreground awaiting each raster IRQ; excludes foreground stress.')
    p.add_argument('--production-nmi-services',action='store_true')
    p.add_argument('--delta-control-traffic',action='store_true',help='Write only changed control fields; paired window bounds remain atomic word writes.')
    p.add_argument('--controls-before-palette',action='store_true',help='Measure source-bound control register writes before palette DMA; previous-line pixel deadlines require a separate check.')
    p.add_argument('--control-traffic',type=Path,help='Execute source-bound alpha/window register traffic with layer math selection disabled; measures transport only, not authored alpha rendering.')
    p.add_argument('--prepare-next-line',action='store_true',help='Prepare the following row DMA counts after the current transfer, shortening the next IRQ critical path.')
    p.add_argument('--nmi-queue-bytes',type=int,default=512)
    p.add_argument('--timer',type=int,default=44);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    schedule=json.loads(a.schedule.read_text());scene=json.loads(a.scene.read_text());authored_context=None
    if a.stage:
        from compiler import Source
        from source_scene_obj_raster import prepare
        source=Source(a.source);_,metadata,composed=prepare(source,a.stage,scene)
        background=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0])
        authored_context=dict(metadata=metadata,expected=rgb555(composed),background=background)
    raw,expected,initial,oam,sy,resources=compile_rom(a.rom.read_bytes(),a.source,scene,schedule,folder,a.timer,a.sa1_mapping,a.foreground_stress,a.production_nmi_services,a.nmi_queue_bytes,a.foreground_wai,a.prepare_next_line,json.loads(a.control_traffic.read_text())if a.control_traffic else None,a.delta_control_traffic,a.controls_before_palette,authored_context)
    production_sy=symbols(Path('src/main.sym'))if a.production_nmi_services else {}
    rom=folder/'proof.sfc';rom.write_bytes(raw);lua=folder/'observer.lua';lua.write_text(observer(sy,a.sa1_mapping,production_sy.get('DmaQueue',0),a.nmi_queue_bytes,a.control_traffic is not None,True,a.foreground_wai,resources['production_queue_vram_byte_address']))
    if authored_context is not None:
        with lua.open('a')as f:f.write("\nlocal routing={};emu.addMemoryCallback(function(a,v)if a==0x2105 or a==0x2107 or a==0x210b or a==0x212c or a==0x212d or a==0x2130 or a==0x2131 or a==0x2132 then routing[a]=v end end,emu.callbackType.write,0x2105,0x2132,emu.cpuType.snes,emu.memType.snesMemory)\nemu.addEventCallback(function()if active then for a,v in pairs(routing)do emu.log('ISOROUTE|'..a..','..v)end end end,emu.eventType.endFrame)\n")
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log')as m:
        advancement=[];ready_fields=0
        for _ in range(24):
            step=m.run_frames(1);advancement.append(step)
            if m.read_memory('SnesMemory',0x7e1e04,2)==bytes.fromhex('01 b4'):ready_fields+=step['framesAdvanced']
            if ready_fields>=4:break
        shot=m.tool('take_screenshot',{'format':'path','path':str(folder/'screenshot.png')});cg=m.read_memory('SnesCgRam',0,512);observed_oam=m.read_memory('SnesSpriteRam',0,544);ppu=m.get_ppu_state();cpu=m.get_cpu_state()
        observed_chr=m.read_memory('SnesVideoRam',0xc000,resources['chr_report']['obj_chr_bytes'])
        chr_identity=hashlib.sha256(observed_chr).hexdigest()==resources['chr_report']['chr_sha256']
        queued_vram=m.read_memory('SnesVideoRam',resources['production_queue_vram_byte_address'],a.nmi_queue_bytes)if a.production_nmi_services and a.nmi_queue_bytes else b''
        production_sy=symbols(Path('src/main.sym'))if a.production_nmi_services else {}
        queue_state=m.read_memory('SnesMemory',production_sy['DmaQueue'],8)if a.production_nmi_services else b''
        nmi_fields=int.from_bytes(m.read_memory('SnesMemory',production_sy['Nmi_FrameCounter'],2),'little')if a.production_nmi_services else None
        underlay_identity=True
        if authored_context is not None:
            from source_obj_underlay import compile_underlay
            _,bgchr,bgmap,bgpal=compile_underlay(authored_context['background'])
            underlay_identity=m.read_memory('SnesVideoRam',0,len(bgchr))==bgchr and m.read_memory('SnesVideoRam',0xb000,len(bgmap))==bgmap and cg[:256]==bgpal
    if Path(shot['path']).resolve()!=folder/'screenshot.png':shutil.copyfile(shot['path'],folder/'screenshot.png')
    actual=rgb555(np.asarray(Image.open(folder/'screenshot.png').convert('RGB')))
    log=(folder/'mesen.log').read_text();packets=[];words=[];contexts=[];flags=[];oamlog=[];nmi_contexts=[];nmi_dmas=[];nmi_queues=[];register_writes=[]
    for line in log.splitlines():
        for token,target in(('ISOPACKET|',packets),('ISOWORDS|',words),('ISOCONTEXT|',contexts),('ISOFLAGS|',flags),('ISONMICONTEXT|',nmi_contexts),('ISONMIDMA|',nmi_dmas),('ISONMIQUEUE|',nmi_queues),('ISOREG|',register_writes)):
            if token in line:target.append(list(map(int,line.split(token,1)[1].split(','))))
        if 'ISOOAM|'in line:oamlog.append(line.split('ISOOAM|',1)[1])
    frames=sorted({r[0]for r in words if r[0]>=1});complete=[];word_faults=0
    expected_rows={r['scanline']:[v for q in r['packets']for i in range(q['word_count'])for v in(q['cgram_word_address']+i,int.from_bytes(bytes.fromhex(q['data_hex'])[2*i:2*i+2],'little'))]for r in schedule['prepared_dma_packets']if r['scanline']and r['packets']}
    if not expected_rows:frames=sorted({r[0]for r in flags[1:]if r[0]>=1})
    for frame in frames:
        seen={r[1]:r[2:]for r in words if r[0]==frame}
        if seen==expected_rows:complete.append(frame)
        else:word_faults+=1
    identity=actual.shape==expected.shape and np.array_equal(actual,expected);context=contexts[-1]if contexts else[0,-1,0]
    nmi_context=nmi_contexts[-1]if nmi_contexts else[0,-1,0]
    nmi_window=bool(nmi_contexts)and all(v[3]==v[5]and 225<=v[4]<=v[6]<262 for v in nmi_contexts)
    queue_payload_identity=not a.production_nmi_services or queued_vram==bytes((i*13+7)&255 for i in range(a.nmi_queue_bytes))
    queue_identity=not a.production_nmi_services or(queue_payload_identity and nmi_window and len(nmi_queues)>=2 and all(q[1]==0 and not(q[2]&64)for q in nmi_queues)and nmi_fields>=2 and nmi_context[0]>=2 and nmi_context[1]==0 and (not a.nmi_queue_bytes or sum(d[1]==24 and d[2]==a.nmi_queue_bytes for d in nmi_dmas)>=2))
    control_fields=[]
    expected_controls={int(y):[list(entry)for entry in rows]for y,rows in resources['control_traffic_rows'].items()}
    for frame in sorted({r[0]for r in register_writes}):
        seen={}
        for f,y,line,h,address,value in register_writes:
            if f==frame:seen.setdefault(y,[]).append([address,value])
        if seen==expected_controls:control_fields.append(frame)
    control_identity=a.control_traffic is None or len(control_fields)>=2
    irq_phases=[list(map(int,line.split('ISOIRQPHASE|',1)[1].split(',')))for line in log.splitlines()if'ISOIRQPHASE|'in line]
    foreground_waits=[list(map(int,line.split('ISOFGWAIT|',1)[1].split(',')))for line in log.splitlines()if'ISOFGWAIT|'in line]
    physical_checks=[list(map(int,line.split('ISOCGRAM|',1)[1].split(',')))for line in log.splitlines()if'ISOCGRAM|'in line]
    physical_identity=(not expected_rows and cg==initial)or(bool(physical_checks)and all(row[2]==0 for row in physical_checks))
    routing={}
    for line in log.splitlines():
        if 'ISOROUTE|'in line:
            address,value=map(int,line.split('ISOROUTE|',1)[1].split(','));routing[address]=value
    main_math=resources['authored_main_screen_obj_math']
    last_math=0x10
    for row in resources['control_traffic_rows'].values():
        for address,value in row:
            if address==0x2131:last_math=value
    routing_identity=authored_context is None or routing=={0x2105:3,0x2107:0x58,0x210b:0,0x212c:17 if main_math else 1,0x212d:1 if main_math else 16,0x2130:0x12 if main_math else 2,0x2131:last_math if main_math else 1,0x2132:0xe0}
    result=dict(schema='BYOR_CONTROLLED_SOURCE_RASTER_OBJ_NATIVE_V1',status='PASS'if identity and len(complete)>=2 and word_faults==0 and sum(r[3]for r in packets)==0 and observed_oam==oam and oamlog==[oam.hex()]and context[1]==0 and all(not(r[1]&192)for r in flags)and queue_identity and control_identity and underlay_identity and routing_identity and physical_identity and chr_identity else'FAIL',
        control_traffic_fields=control_fields,control_traffic_identity_verified=control_identity,control_traffic_source_file_sha256=hashlib.sha256(a.control_traffic.read_bytes()).hexdigest()if a.control_traffic else None,
        irq_phase_observer=irq_phases,
        foreground_wait_observer=foreground_waits,
        nmi_context_checks=nmi_context[0],nmi_context_faults=nmi_context[1],peak_nmi_entry_to_rti_master_clocks=nmi_context[2],production_nmi_fields=nmi_fields,nmi_completed_within_vblank=nmi_window,production_queue_vram_identity_verified=queue_identity if a.production_nmi_services else None,production_queue_state_hex=queue_state.hex(),production_queue_payload_identity_verified=queue_payload_identity if a.production_nmi_services else None,
        physical_cgram_identity_verified=physical_identity,physical_cgram_checks=len(physical_checks),physical_cgram_byte_identity_faults=sum(row[2]for row in physical_checks),
        pixel_identity_verified=identity,pixel_mismatches=int(np.count_nonzero(actual!=expected))if actual.shape==expected.shape else None,
        complete_packet_fields=complete,packet_identity_faults=word_faults,unsafe_high_commits=sum(r[3]for r in packets),
        peak_observed_commit_span=max((r[4]for r in packets),default=None),first_high_hclock_range=[min((r[5]for r in packets),default=0),max((r[5]for r in packets),default=0)],
        irq_context_checks=context[0],irq_context_faults=context[1],peak_irq_entry_to_rti_master_clocks=context[2],
        oam_ram_identity_verified=observed_oam==oam,oam_observer_identity_verified=oamlog==[oam.hex()],obj_overflow_flags=flags,
        obj_chr_vram_identity_verified=chr_identity,obj_chr_vram_sha256=hashlib.sha256(observed_chr).hexdigest(),
        source_frame_sha256=next(l['sha256']for l in resources['source_metadata']['layers']if l['kind'].startswith('actor:')),
        input_schedule_file_sha256=hashlib.sha256(a.schedule.read_bytes()).hexdigest(),
        compiled_transfer_descriptor_sha256=hashlib.sha256(json.dumps(schedule['prepared_dma_packets'],sort_keys=True).encode()).hexdigest(),
        compiled_schedule_sha256=schedule['compiled_schedule_sha256'],rom_sha256=hashlib.sha256(raw).hexdigest(),expected_rgb555_sha256=hashlib.sha256(expected.tobytes()).hexdigest(),
        foreground_wait_for_irq=a.foreground_wai,foreground_stress=a.foreground_stress,dma_counts_prepared_previous_line=a.prepare_next_line,
        timer=a.timer,resources=resources,frame_advancement=advancement,ppu=ppu,cpu=cpu,no_color_reduction=True,
        production_runtime_admitted=False,authored_stage_and_concurrent_actors_proven=False,motu_gameplay_proven=False)
    if authored_context is not None:
        result.update(authored_stage_source_pixels_proven=identity,authored_underlay_vram_palette_identity=underlay_identity,layer_routing_observer_identity=routing_identity,layer_routing_observer=routing,
            physical_cgram_identity_verified=physical_identity,physical_cgram_checks=len(physical_checks),physical_cgram_byte_identity_faults=sum(row[2]for row in physical_checks),
            source_alpha_policy='EXACT_BOR4086_SCREEN_RGB8_THEN_RGB555',concurrent_actor_layer_routing_proven=False)
    (folder/'expected.rgb555').write_bytes(expected.tobytes());(folder/'cgram.bin').write_bytes(cg);(folder/'oam.bin').write_bytes(observed_oam)
    (folder/'obj.chr').write_bytes(observed_chr)
    (folder/'cgram-observer.json').write_text(json.dumps(dict(packets=packets,words=words,nmi_dmas=nmi_dmas,nmi_contexts=nmi_contexts,nmi_queues=nmi_queues,register_writes=register_writes,physical_cgram_checks=physical_checks),separators=(',',':'))+'\n');(folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','pixel_mismatches','complete_packet_fields','unsafe_high_commits','peak_observed_commit_span','first_high_hclock_range','irq_context_checks','irq_context_faults','production_runtime_admitted')}))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
