"""Attach a native retained bitmap to the existing isolated canvas owner.

This remains an explicit source pose and a private whole-canvas owner. It does
not bind the foreign gameplay dispatcher, source camera or live actor frames.
"""
import json
from m4_bg_components_native import compile_rom
from m4_raster_production_nmi import build
from sa1_character_conversion import type1_descriptor


def conversion_asm(high_target,tile_count):
    code=r'''
GraphicsCanvasConvert:
.a8
.i16
 php
 rep #$30
.a16
.i16
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
 sei
 lda #0
 sta.w $4200
 lda #$80
 sta.w $2100
 rep #$30
.a16
.i16
 lda #$B66D
 sta.l $412028
 lda #$B408
 sta.l $41202A
 lda #1
 sta.l $41202C
 sta.l $41202E
GraphicsCanvasAcquire:
 lda.l $41202E
 cmp #2
 bne GraphicsCanvasAcquire
GraphicsCanvasLeaseAcquired:
 nop
 ; Returning SA-1 helper: enable type-1; retain the resident world stack.
 lda #$20E2
 sta.l $003500
 lda #$B0A9
 sta.l $003502
 lda #$308F
 sta.l $003504
 lda #$0022
 sta.l $003506
 lda #$20C2
 sta.l $003508
 lda #$6B18
 sta.l $00350A
 lda #$005C
 sta.l $0037C0
 lda #$0035
 sta.l $0037C2
 lda #3
 sta.l $41202E
GraphicsCanvasType1Ready:
 lda.l $41202E
 cmp #4
 bne GraphicsCanvasType1Ready
 sep #$20
.a8
 lda #$80
 sta.w $2115
'''
    descriptors=[type1_descriptor(0x420000,8,1,tile_count,high_target),
                 type1_descriptor(0x420000+tile_count*64,2,1,tile_count,49152)]
    for i,d in enumerate(descriptors):
        for address,value in ((0x2231,d['cdma']),(0x2232,d['source']&255),
                              (0x2233,d['source']>>8&255),(0x2234,0x42),
                              (0x2235,0),(0x2236,0x36)):
            code+=f' lda #{value}\n sta.w ${address:04X}\n'
        code+=f'''GraphicsCanvasChrReady{i}:
 lda.w $2300
 and #$20
 beq GraphicsCanvasChrReady{i}
 lda #$20
 sta.w $2202
 rep #$20
.a16
 lda #{d['vram_word_address']}
 sta.w $2116
 lda #$1801
 sta.w $4370
 lda #{d['source']&65535}
 sta.w $4372
 lda #$42
 sta.w $4374
 lda #{d['bytes']}
 sta.w $4375
 sep #$20
.a8
 lda #$80
GraphicsCanvasDMA{i}:
 sta.w $420B
 lda #$80
 sta.w $2231
'''
    code+=r'''
 ; Both conversion modes are disabled before any ordinary BW-RAM access.
 rep #$30
.a16
.i16
 lda #$00A9
 sta.l $003502
 lda #3
 sta.l $41202E
GraphicsCanvasType1Disabled:
 lda.l $41202E
 cmp #4
 bne GraphicsCanvasType1Disabled
GraphicsCanvasConversionDone:
 nop
 lda #5
 sta.l $41202E
GraphicsCanvasRelease:
 lda.l $41202E
 bne GraphicsCanvasRelease
GraphicsCanvasConverted:
 nop
 plb
 pld
 ply
 plx
 pla
 plp
 rtl
'''
    return code,descriptors


def install(raw,sy,graphics,folder):
    context=graphics/'palette-context-1'
    assets=context/'native-input'
    report=json.loads((assets/'report.json').read_text())
    source=json.loads((context/'report.json').read_text())
    cache=context/'native-window-atlas'
    obj=(context/'obj_chr.bin').read_bytes()
    high_target=max(4096,((len(obj)+4095)//4096)*4096)
    component,trace,resources=compile_rom(report,assets,76,cache_assets=cache,
        offset_alias='low',high_base=0,high_tile_offset=high_target//64,
        obj_chr=obj,oam=(context/'oam.bin').read_bytes(),obj_obsel=source['native_obsel'],
        obj_rom_bank=5,obj_rom_address=0xb000)
    rom,gates=build(component,report,folder,bytes(raw),sy,canvas_nmi=True,
                    compact_canvas_nmi=True)
    rom=bytearray(rom)
    # Insert the returning conversion call after static atlas/PPU setup and
    # before the owner's fresh VBlank edge and visible publication.
    base=40*32768
    owner=rom[base:base+32768]
    marker=bytes.fromhex('e2 20 ad 12 42 29 80 d0 f9 ad 12 42 29 80 f0 f9')
    if owner.count(marker)!=1:raise ValueError('NATIVE_CANVAS_CONVERSION_HANDOFF')
    at=owner.index(marker)
    # The bootstrap has no intra-body jumps after this point except its final
    # loop JML; adjust that target exactly, leaving all bank-zero sizes intact.
    loop=bytes.fromhex('22 00 c0 a7 5c')
    ending=owner.find(loop,at)
    if ending<0 or owner[ending+7]!=0xa8:raise ValueError('NATIVE_CANVAS_BOOTSTRAP_END')
    end=ending+8
    code=bytearray(owner[:end]);tail=code[-4:]
    if tail[0]!=0x5c or tail[3]!=0xa8:raise ValueError('NATIVE_CANVAS_LOOP_LAYOUT')
    target=int.from_bytes(tail[1:3],'little')
    if target<0x8000+at:raise ValueError('NATIVE_CANVAS_LOOP_TARGET')
    code[at:at]=b'\x22'+sy['GraphicsCanvasConvert'].to_bytes(3,'little')
    code[-3:-1]=(target+4).to_bytes(2,'little')
    rom[base:base+32768]=code.ljust(32768,b'\xff')
    resources.update(native_bitmap_HIGH_VRAM=high_target,native_bitmap_LOW_VRAM=49152,
                     production_bank_zero_growth_bytes=0,canvas_gates=gates,
                     native_CGRAM_expected_trace=trace)
    return rom,resources


def observer():
    return r'''
local shown=false;local fields=0;local unsafe=0;local restoring=false
local rows={};local oam={};local oamCount=0
local conversionMonitor=false;local conversionActive=false;local conversionReads=0;local conversionBad=0;local conversionResident=nil;local conversionClock=0
local function resident()local t={};for a=0x411700,0x411fff do t[#t+1]=emu.read(a,emu.memType.snesMemory)end;for a=0x3025,0x3027 do t[#t+1]=emu.read(a,emu.memType.snesMemory)end;return t end
emu.addMemoryCallback(function()conversionMonitor=true;conversionResident=resident();conversionClock=emu.getState().masterClock end,emu.callbackType.exec,CONVERSIONACQUIRED,CONVERSIONACQUIRED,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if conversionMonitor then
  if a==0x2231 and (v&0x80)~=0 then conversionActive=false end
  if a==0x2236 then conversionActive=true end
 end
end,emu.callbackType.write,0x2231,0x2236,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a)
 if conversionActive then conversionReads=conversionReads+1;if a<0x420000 or a>=0x421ae0 then conversionBad=conversionBad+1 end end
end,emu.callbackType.read,0x400000,0x43ffff,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 conversionMonitor=false;local n=0;local after=resident();for i,v in ipairs(after)do if v~=conversionResident[i]then n=n+1 end end
 emu.log('NATIVECHRRESIDENT|'..n);emu.log('NATIVECHRREADS|'..conversionReads..'|'..conversionBad..'|'..(conversionActive and 1 or 0))
 emu.log('NATIVECHRCLOCKS|'..(emu.getState().masterClock-conversionClock))
end,emu.callbackType.exec,CONVERSIONDONE,CONVERSIONDONE,emu.cpuType.snes,emu.memType.snesMemory)
local function word(a)return emu.read(a,emu.memType.snesMemory)+256*emu.read(a+1,emu.memType.snesMemory)end
emu.addMemoryCallback(function(a,v)restoring=v==1 end,emu.callbackType.write,0x7ff85c,0x7ff85c,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if v==15 and word(0x7ff840)==0xb4b0 then shown=true end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)
 if not shown then oamCount=oamCount+1;oam[(oamCount-1)%544+1]=string.format('%02x',v)end
end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)
local burstByte=0;local firstClock=0;local burstPeak=0;local firstMin=9999;local lastMax=0
emu.addMemoryCallback(function(a,v)
 if shown and not restoring and fields==1 then
  rows[#rows+1]=string.format('%04x:%02x',a,v)
  if a==0x2121 then burstByte=0 else
   burstByte=burstByte+1;local s=emu.getState();local h=(s.masterClock+4*(s['ppu.frameCount']//2))%1364
   if s['ppu.scanline']<225 and h>=88 and h<1096 then unsafe=unsafe+1 end
   if burstByte==1 then firstClock=s.masterClock;firstMin=math.min(firstMin,h)end
   if burstByte==30 then burstPeak=math.max(burstPeak,s.masterClock-firstClock);lastMax=math.max(lastMax,h<88 and h+1364 or h)end
  end
 end
end,emu.callbackType.write,0x2121,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 if shown and fields<6 then
  fields=fields+1
  if fields==2 then local ordered={};for i=1,544 do ordered[i]=oam[(oamCount+i-1)%544+1]or ''end;emu.log('NATIVEPPUCGRAM|'..table.concat(rows,','));emu.log('NATIVEPPUOAM|'..table.concat(ordered,''));emu.log('NATIVEPPUSAFE|'..unsafe);emu.log('NATIVEPPUBUDGET|'..burstPeak..'|'..firstMin..'|'..lastMax)end
  emu.log('NATIVEPPUFLAGS|'..emu.read(0x213e,emu.memType.snesMemory))
 end
end,emu.eventType.endFrame)
'''
