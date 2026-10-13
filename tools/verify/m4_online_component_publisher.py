"""Online source-indexed dirty tiles feeding the established lossless BG pair.

There is one actor-free immutable backdrop, not position-keyed canvases. This
producer projects the sealed Q16 world, gathers original indexed art, preserves
foreground coverage, encodes native planar tiles and allocates paired residency.
All preflight failures precede forced blank and retain the previous epoch.
"""
import json
import subprocess
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_bg_components_native import compile_rom
from m4_live_ground_owner import SNAPSHOT
from m4_bounded_component_publisher import READY,DISPLAY_EPOCH
from bg_component_residency import emit_native_planar_pixel

MAP=0x42c000
REF=0x42d000
CHUNK=0x42d600
HIGH=0x42d680
LOW=0x42d6c0


def build(original,sy,folder,assets):
    rom=bytearray(original);report=json.loads((assets/'report.json').read_text())
    authority=json.loads((assets/'source-assets.json').read_text())
    if rom[57*32768:58*32768]!=bytes(32768):raise ValueError('ONLINE_CODE_LEASE')
    if any(row['updates'] for row in report['trace'][1:]):raise ValueError('ONLINE_IMMUTABLE_PALETTE_REQUIRED')
    raw,_,resources=compile_rom(report,assets,cache_assets=assets,offset_alias=True)
    resources.update(hdma_channels=[],per_field_palette_restore_bytes=0,code_bank=57,
                     runtime_publication='Forced blank; all DMA channel 7; static palette; no HDMA/IRQ.')
    def put(at,data):
        if at+len(data)>len(rom) or any(rom[at:at+len(data)]):raise ValueError('ONLINE_ROM_ASSET_LEASE')
        rom[at:at+len(data)]=data
    put(0x200000,raw[0x10000:0x30000])
    put(0x220000,(assets/'backdrop-pixels.bin').read_bytes())
    put(0x240000,(assets/'foreground.bin').read_bytes())
    frame_banks=[];cursor=0x250000
    for f in authority['frames']:
        data=(assets/(f['role']+'.indices')).read_bytes();frame_banks.append(0xc0+(cursor>>16))
        put(cursor,data);cursor+=((len(data)+65535)//65536)*65536
    palette_address=0xc00000+cursor
    put(cursor,(assets/'actor-palette.bin').read_bytes())
    code=bytearray(raw[0x8000:0x8400]);end=code.find(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    if end<11:raise ValueError('ONLINE_COMPONENT_BOOTSTRAP_CONTRACT')
    code=code[11:end] # retain compiler DMA/PPU setup; online owner seals/unblanks
    for j in range(len(code)-14):
        if code[j]==0xa9 and code[j+2:j+5]==bytes.fromhex('8d7243') and code[j+5]==0xa9 and code[j+7:j+10]==bytes.fromhex('8d7343') and code[j+10]==0xa9 and code[j+12:j+15]==bytes.fromhex('8d7443'):
            old=code[j+11];address=code[j+1]|code[j+6]<<8
            if old not in (2,3,4,5):raise ValueError('ONLINE_BOOTSTRAP_DMA_BANK')
            address-=0x8000 if old%2==0 else 0
            code[j+1]=address&255;code[j+6]=address>>8;code[j+11]=0xe0+(old-2)//2
    for reg in range(0x4304,0x4375,16):
        code=code.replace(bytes([0xa9,5,0x8d,reg&255,reg>>8]),bytes([0xa9,0xe1,0x8d,reg&255,reg>>8]))
    lines=['.snes','.bank 57','.org $8000','OnlinePublish:','.a16','.i16',
           ' php',' rep #$30',' pha',' phx',' phy',' phb',' phd',' lda #$3400',' tcd',
           ' sep #$20','.a8',' lda #0',' pha',' plb',' rep #$20','.a16']
    def add(*s):lines.extend(s)
    serial=0
    def branch(op,target):
        nonlocal serial
        serial+=1;skip=f'OnlineSkip{serial}'
        inverse=dict(bne='beq',beq='bne',bcs='bcc',bcc='bcs',bmi='bpl',bpl='bmi')[op]
        add(f' {inverse} {skip}',f' jmp {target}',skip+':','.a16','.i16')
    def guard(at,value):
        add(f' lda.l {at}',f' cmp #{value}');branch('bne','OnlineReject')
    # Native leases and source capability checks. No mutation of source state.
    guard(SNAPSHOT,0x4000);guard(SNAPSHOT+2,0x41);guard(SNAPSHOT+4,1);guard(SNAPSHOT+6,0)
    guard(SNAPSHOT+80,authority['model_id']);guard(SNAPSHOT+28,1);guard(SNAPSHOT+30,0)
    guard(SNAPSHOT+12,0);guard(SNAPSHOT+14,0);guard(SNAPSHOT+86,0)
    guard(sy['SourcePhysicsState4086_Ready'],0)
    guard(0x433830,0) # source player remap, immutable map-zero palette authority
    # Supported positive foot-coordinate domain is continuous, not a tuple list.
    for at,maximum in ((54,255),(62,223)):
        add(f' lda.l {SNAPSHOT+at}',f' cmp #{maximum+1}');branch('bcs','OnlineReject')
    add(f' lda.l {SNAPSHOT+84}')
    for i,f in enumerate(authority['frames']):
        add(f' cmp #{f["handle"]}');branch('beq',f'OnlineFrame{i}')
    add(' jmp OnlineReject')
    for i,f in enumerate(authority['frames']):
        bx,by,ex,ey=f['bounds'];ox,oy=f['offset'];w,h=f['dimensions']
        add(f'OnlineFrame{i}:','.a16','.i16',f' lda.l {SNAPSHOT+54}',' sec',f' sbc #{ox}',' sta $00',
            f' lda.l {SNAPSHOT+62}',' sec',f' sbc #{oy}',' sta $02',f' lda #{w}',' sta $04',f' lda #{h}',' sta $06',
            ' lda #0',' sta $08',f' lda #{frame_banks[i]}',' sta $0A')
        for origin,bound,dp,maxi in ((0,bx,0x10,31),(0,ex-1,0x12,31),(2,by,0x14,27),(2,ey-1,0x16,27)):
            tag=f'OnlineClamp{i}_{dp}'
            add(f' lda ${origin:02X}',' clc',f' adc #{bound}',f' bpl {tag}Pos',' lda #0',tag+'Pos:',
                '.a16','.i16',f' cmp #{(maxi+1)*8}',f' bcc {tag}Max',f' lda #{maxi*8}',tag+'Max:',
                '.a16','.i16',' lsr a',' lsr a',' lsr a',f' sta ${dp:02X}')
        add(' jmp OnlinePreflight')
    add('OnlinePreflight:','.a16','.i16',' lda #0',' ldx #0','OnlineClearRefs:','.a16','.i16',
        f' sta.l {REF},x',' inx',' inx',' cpx #1536',' bne OnlineClearRefs',
        ' lda #0',' sta $18',' sta $3A')
    # Build pending maps and count only references outside the dirty rectangle.
    add('OnlineMapLoop:','.a16','.i16',' lda $18',' and #31',' cmp $10');branch('bcc','OnlineUnchanged')
    add(' cmp $12');branch('bcc','OnlineMapTestY');branch('bne','OnlineUnchanged')
    add('OnlineMapTestY:','.a16','.i16',' lda $18',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' cmp $14');branch('bcc','OnlineUnchanged')
    add(' cmp $16');branch('bcc','OnlineMarkDirty');branch('bne','OnlineUnchanged')
    add('OnlineMarkDirty:','.a16','.i16',' inc $3A',' lda $18',' asl a',' tax',' lda #$FFFF',f' sta.l {MAP},x',' jmp OnlineMapNext')
    add('OnlineUnchanged:','.a16','.i16',' lda $18',' asl a',' tax',' lda.l $E18000,x',f' sta.l {MAP},x',' asl a',' tax',
        f' lda.l {REF},x',' inc a',f' sta.l {REF},x','OnlineMapNext:','.a16','.i16',' inc $18',' lda $18',' cmp #1024');branch('bcc','OnlineMapLoop')
    add(' lda #0',' sta $18',' sta $2E','OnlineAllocate:','.a16','.i16',' lda $18',' asl a',' tax',f' lda.l {MAP},x',' cmp #$FFFF');branch('bne','OnlineAllocateNext')
    add('OnlineFindFree:','.a16','.i16',' lda $2E',' cmp #768');branch('bcs','OnlineReject')
    add(' asl a',' tax',f' lda.l {REF},x');branch('beq','OnlineFreeFound')
    add(' inc $2E',' jmp OnlineFindFree','OnlineFreeFound:','.a16','.i16',' lda #1',f' sta.l {REF},x',
        ' lda $18',' asl a',' tax',' lda $2E',f' sta.l {MAP},x',' inc $2E')
    add('OnlineAllocateNext:','.a16','.i16',' inc $18',' lda $18',' cmp #896');branch('bcc','OnlineAllocate')
    # Only now retire displayed references. All subsequent changes are blanked.
    add('OnlineBlank:','.a16','.i16',' sep #$20','.a8',' lda #0',' sta.l $004200',' sta.l $00420C',
        ' lda #$80',' sta.l $002100',' sta.l $002231',' lda #$20',' sta.l $002200',' lda #0')
    add(*(f' sta.l ${r:06X}' for r in (*range(0x2123,0x212c),0x212e,0x212f)))
    add(*(' .db '+','.join(f'${b:02X}' for b in code[j:j+16]) for j in range(0,len(code),16)))
    add(' rep #$20','.a16',' lda $14',' asl a',' asl a',' asl a',' asl a',' asl a',' clc',' adc $10',' sta $18')
    add('OnlineTile:','.a16','.i16',' lda $18',' asl a',' tax',f' lda.l {MAP},x',' sta $2C',
        ' lda.l $E18000,x',' sta $2A',' and #511',' asl a',' asl a',' asl a',' asl a',' asl a',' asl a',' asl a',' sta $0C',
        ' lda $2A',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' clc',' adc #$E2',' sta $0E',
        ' lda $18',' and #31',' asl a',' asl a',' asl a',' sta $1A',
        ' lda $18',' and #$FFE0',' asl a',' asl a',' asl a',' sta $1C', # tileY*8*256 = tileI&FFE0 *64 (below)
        ' asl a',' asl a',' asl a',' sta $24', # full screen byte offset y*256
        ' lda #0',' sta $1E',' sta $22')
    add('OnlineRow:','.a16','.i16',' lda #0',' sta $20','OnlinePixel:','.a16','.i16',
        ' lda $22',' asl a',' tay',' lda [$0C],y',' sta $30',
        ' lda $24',' clc',' adc $1A',' adc $20',' tax',' sep #$20','.a8',' lda.l $E40000,x',
        ' rep #$20','.a16',' and #255');branch('bne','OnlinePixelStore')
    add(' lda $1A',' clc',' adc $20',' sec',' sbc $00',' cmp $04');branch('bcs','OnlinePixelStore')
    add(' sta $26',' lda $18',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' asl a',' asl a',' asl a',
        ' clc',' adc $1E',' sec',' sbc $02',' cmp $06');branch('bcs','OnlinePixelStore')
    # Exact integer indexed row address; geometry is <=255, hardware multiply.
    add(' sta $28',' sep #$20','.a8',' sta.l $004202',' lda $04',' sta.l $004203',' nop',' nop',' nop',' nop',
        ' rep #$20','.a16',' lda #0',' sta $3E',' lda $04',' and #$FF00',' beq OnlineSmallRow',
        ' lda $28',' xba',' and #$FF00',' clc',' adc.l $004216',' sta $3C',' lda #0',' adc #0',' sta $3E',' jmp OnlineRowAddress',
        'OnlineSmallRow:','.a16','.i16',' lda.l $004216',' sta $3C',
        'OnlineRowAddress:','.a16','.i16',' lda $3C',' clc',' adc $26',' tay',' lda $3E',' adc $0A',' sta $3E',' lda #0',' sta $3C',
        ' sep #$20','.a8',' lda [$3C],y',' rep #$20','.a16',' and #255');branch('beq','OnlinePixelStore')
    add(' asl a',' tax',f' lda.l ${palette_address:06X},x',' sta $30','OnlinePixelStore:','.a16','.i16',
        ' lda $22',' asl a',' tax',' lda $30',f' sta.l {CHUNK},x',
        ' inc $22',' inc $20',' lda $20',' cmp #8');branch('bcc','OnlinePixel')
    add(' lda $24',' clc',' adc #256',' sta $24',' inc $1E',' lda $1E',' cmp #8');branch('bcc','OnlineRow')
    add('OnlineEncode:','.a16','.i16',' lda #0',' ldx #0','OnlineClearPlanar:','.a16','.i16',f' sta.l {HIGH},x',
        ' inx',' inx',' cpx #80',' bne OnlineClearPlanar',' lda #0',' sta $1E',' sta $22')
    add('OnlineEncodeRow:','.a16','.i16',' lda $1E',' asl a',' sta $38',' lda #128',' sta $32',' lda #0',' sta $20',
        'OnlineEncodePixel:','.a16','.i16',' lda $22',' asl a',' tax',f' lda.l {CHUNK},x',' sta $34',' xba',' and #255',' sta $36',' ldx $38')
    # The same planar bit ordering as bg_component_residency.encode. Component
    # bytes are produced natively, not injected by the independent verifier.
    add(*emit_native_planar_pixel(HIGH,LOW))
    add(' lsr $32',' inc $22',' inc $20',' lda $20',' cmp #8');branch('bcc','OnlineEncodePixel')
    add(' inc $1E',' lda $1E',' cmp #8');branch('bcc','OnlineEncodeRow')
    add('OnlineTransfer:','.a16','.i16',' lda $2C',' asl a',' asl a',' asl a',' asl a',' asl a',' sta.l $002116')
    dma_serial=0
    def dma(source,size,mode=1,dest=0x18):
        nonlocal dma_serial
        dma_serial+=1
        add(' sep #$20','.a8')
        for r,v in ((0x4370,mode),(0x4371,dest),(0x4372,source&255),(0x4373,(source>>8)&255),(0x4374,source>>16),
                    (0x4375,size&255),(0x4376,size>>8),(0x420b,128)):
            add(f' lda #{v}',f' sta.l ${r:06X}')
        add(f'OnlineDmaDone{dma_serial}:',' rep #$20','.a16')
    dma(HIGH,64)
    add(' lda $2C',' asl a',' asl a',' asl a',' clc',' adc #$6000',' sta.l $002116');dma(LOW,16)
    add(' lda $18',' and #31',' cmp $12');branch('bcc','OnlineNextX')
    add(' lda $18',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' cmp $16');branch('beq','OnlineMapsTransfer')
    add(' lda $18',' and #$FFE0',' clc',' adc #32',' adc $10',' sta $18',' jmp OnlineTile',
        'OnlineNextX:','.a16','.i16',' inc $18',' jmp OnlineTile',
        'OnlineMapsTransfer:','.a16','.i16',' lda #$7800',' sta.l $002116');dma(MAP,2048)
    add(' lda #$7C00',' sta.l $002116');dma(MAP,2048)
    add('OnlineComplete:','.a16','.i16',f' lda #{0xb4b8}',f' sta.l {READY}',f' lda.l {SNAPSHOT+144}',f' sta.l {DISPLAY_EPOCH}',
        ' sep #$20','.a8','OnlineVblank:',' lda.l $004212',' and #$80',' beq OnlineVblank',
        ' lda #15',' sta.l $002100',' rep #$20','.a16',' pld',' plb',' ply',' plx',' pla',' plp',' clc',' rtl',
        'OnlineReject:','.a16','.i16',' pld',' plb',' ply',' plx',' pla',' plp',' sec',' rtl')
    entry=sy['nmi_handler'];at=offset(entry);prior=bytes(rom[at:at+8])
    if prior[0]!=0x22 or prior[4]!=0x20 or prior[7]!=0x40:raise ValueError('ONLINE_NMI_HANDOFF')
    stage=int.from_bytes(prior[1:4],'little');core=int.from_bytes(prior[5:7],'little')
    add('.org $F000','OnlineNmi:','.a16','.i16',' php',' rep #$30',' pha',f' lda.l {READY}',f' cmp #{0xb4b8}',
        ' beq OnlineNmiOwned',' pla',' plp',f' jsl ${stage:06X}',f' pea ${entry+6:04X}',f' jml ${core:06X}',
        'OnlineNmiOwned:','.a16','.i16',' lda.l $004210',' pla',' plp',' rti')
    path=folder/'publisher.pasm';path.write_text('\n'.join(lines)+'\n')
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(path),'--output',str(folder/'publisher.bin'),'--symbols',str(folder/'publisher.sym'),'--no-pansy'],capture_output=True,text=True)
    (folder/'publisher-build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('ONLINE_PUBLISHER_ASSEMBLY')
    fs=symbols(folder/'publisher.sym');blob=(folder/'publisher.bin').read_bytes()[57*32768:58*32768]
    rom[57*32768:57*32768+len(blob)]=blob
    rom[at:at+4]=bytes([0x5c])+fs['OnlineNmi'].to_bytes(3,'little')
    return bytes(rom),dict(resources=resources,source_assets=authority,complete_actor_contexts=0,
        code_bank=57,code_bytes=fs['OnlineReject']-fs['OnlinePublish'],source_asset_rom=[0xe0,palette_address>>16],
        bwram_lease=[MAP,0x42d700],dp_lease=[0x3400,0x3440],paired_slots=768,
        native_symbols={k:v for k,v in fs.items() if k.startswith('Online')},
        publication='Preflight residency; forced blank retires old references; restore immutable backdrop; native dirty source tiles; coherent paired maps; DMA complete then visible epoch.',
        finite_position_selector=False,host_graphics_injection=False)
