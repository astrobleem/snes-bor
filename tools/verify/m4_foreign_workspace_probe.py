"""Lease guards after the real isolated canvas has retired the old frontpanel."""
import json

ASM = r'''
ForeignCanvasWait:
.a16
.i16
 php
 rep #$30
 pha
 lda.l $7FBFE2
 bne ForeignCanvasReturn
 sei
 sep #$20
.a8
 lda #0
 sta.w $4200
 rep #$30
.a16
 phx
 phy
 ldx #$4086
 ldy #1
ForeignLeaseInit:
 nop
 jsl SourceForeignWork_Init
ForeignLeaseInitialized:
 nop
 lda #0
 sta.l $7FBFE4
ForeignLeaseLoop:
 ldx #$4086
 ldy #1
ForeignLeaseCase:
 nop
 jsl SourceForeignWork_Check
ForeignLeaseResult:
 nop
 lda.l $7FBFE4
 inc a
 sta.l $7FBFE4
 cmp #30
 bne ForeignLeaseLoop
ForeignLeaseRestore:
 nop
 lda #1
 sta.l $7FBFE2
 ply
 plx
ForeignCanvasReturn:
 pla
 plp
 rtl
'''


def install(rom, sy):
    base=40*32768
    needle=bytes.fromhex('e2 20 ad 12 42 29 80 d0 f9 ad 12 42 29 80 f0 f9')
    owner=rom[base:base+32768]
    if owner.count(needle)!=1:
        raise ValueError('FOREIGN_WORKSPACE_CANVAS_LOOP')
    at=owner.index(needle)
    ending=owner.index(bytes.fromhex('22 00 c0 a7 5c'),at)+8
    code=bytearray(owner[:ending])
    target=int.from_bytes(code[-3:-1],'little')
    code[at:at]=b'\x22'+sy['ForeignCanvasWait'].to_bytes(3,'little')
    code[-3:-1]=(target+4).to_bytes(2,'little')
    rom[base:base+32768]=code.ljust(32768,b'\xff')


def observer(sy):
    flags=[sy[n] for n in ('StageFp_BG2Loaded','StageFp_BG2Active',
        'StageFp_BG2DmaPending','StageFp_BG2Booting',
        'StreamScrollFp_ColPending','StreamScrollFp_Enabled')]
    return 'local fwflags='+json.dumps(flags).replace('[','{').replace(']','}')+'\n'+r'''
local fmt=emu.memType.snesMemory;local saved={};local fq=FWQUEUE
local function fwput(a,v)emu.write(a,v&255,fmt);emu.write(a+1,(v>>8)&255,fmt)end
local function fww(a)return emu.read(a,fmt)|(emu.read(a+1,fmt)<<8)end
local function fwreset()for a,v in pairs(saved)do emu.write(a,v,fmt)end end
emu.addMemoryCallback(function()
 emu.write(0x7fbfe2,0,fmt);fwput(0x7fbfda,0)
 for a=0x7fa000,0x7fb8ff do emu.write(a,0xa5,fmt)end
end,emu.callbackType.exec,FWINIT,FWINIT,emu.cpuType.snes,fmt)
emu.addMemoryCallback(function()
 local bad=0;for a=0x7fa000,0x7fb8ff do if emu.read(a,fmt)~=0 then bad=bad+1 end;emu.write(a,(a*13)&255,fmt)end
 emu.log('FOREIGNINIT|'..fww(0x7fbfda)..'|'..fww(0x7fbfdc)..'|'..bad)
 local ranges={{0x7ff840,2},{0x7ff862,2},{0x7ff866,2},{0x7ff856,2},{0x7ff846,2},{0x7fbfda,8},{fq,64}}
 for _,a in ipairs(fwflags)do ranges[#ranges+1]={a,1}end
 for _,r in ipairs(ranges)do for a=r[1],r[1]+r[2]-1 do saved[a]=emu.read(a,fmt)end end
end,emu.callbackType.exec,FWINITIALIZED,FWINITIALIZED,emu.cpuType.snes,fmt)
emu.addMemoryCallback(function()
 fwreset();local i=fww(0x7fbfe4)
 if i==1 then fwput(0x7fbfda,0)
 elseif i==2 then fwput(0x7fbfde,0x4087)
 elseif i==3 then fwput(0x7fbfe0,2)
 elseif i==4 then fwput(0x7ff840,0)
 elseif i==5 then fwput(0x7ff862,0)
 elseif i==6 then fwput(0x7ff856,1)
 elseif i>=7 and i<=12 then emu.write(fwflags[i-6],1,fmt)
 elseif i>=13 and i<=20 then
  local q=fq+(i-13)*8;fwput(q,2);emu.write(q+4,0x40,fmt);fwput(q+5,0xa000);emu.write(q+7,0x7f,fmt)
 elseif i==28 then fwput(0x7ff846,0x7f)
 elseif i==29 then fwput(0x7ff866,0)
 elseif i>=21 then
  local rows={{0x40,0x7e,0xa000,2},{0x40,0x7f,0x9fff,1},{0x40,0x7f,0xb900,2},{0xc0,0x7f,0xb8ff,2},{0xc0,0x7f,0xb900,2},{0x40,0x7f,0xfffe,4},{0x20,0x7f,0xa000,2}}
  local d=rows[i-20];fwput(fq,d[4]);emu.write(fq+4,d[1],fmt);fwput(fq+5,d[3]);emu.write(fq+7,d[2],fmt)
 end
end,emu.callbackType.exec,FWCASE,FWCASE,emu.cpuType.snes,fmt)
emu.addMemoryCallback(function()
 local i=fww(0x7fbfe4);local bad=0
 for a=0x7fa000,0x7fb8ff do if emu.read(a,fmt)~=((a*13)&255)then bad=bad+1 end end
 emu.log('FOREIGNCHECK|'..i..'|'..fww(0x7fbfdc)..'|'..bad)
end,emu.callbackType.exec,FWRESULT,FWRESULT,emu.cpuType.snes,fmt)
emu.addMemoryCallback(fwreset,emu.callbackType.exec,FWRESTORE,FWRESTORE,emu.cpuType.snes,fmt)
'''.replace('FWQUEUE',str(sy['DmaQueue']))


def checks(log, reporter):
    init=[s.split('FOREIGNINIT|')[1].strip() for s in log.splitlines() if 'FOREIGNINIT|' in s]
    reporter.check('retired frontpanel workspace initialized by native canvas owner',init==['46705|1|0'])
    rows=[list(map(int,s.split('FOREIGNCHECK|')[1].strip().split('|'))) for s in log.splitlines() if 'FOREIGNCHECK|' in s]
    allowed={0,21,22,23,25,27}
    reporter.check('all workspace generation canvas and DMA guards preserve payload',
        rows==[[i,1 if i in allowed else 2,0] for i in range(30)])
    return dict(init=init,cases=rows,production_gameplay_binding=False)
