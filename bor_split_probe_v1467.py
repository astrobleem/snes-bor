"""Verify each private atlas slice from physical VRAM at MDMAEN return."""
import bor_fg_scope_v1447 as fg
import bor_split_atlas_v1467 as split
compose=fg.compose
evidence=fg.evidence
def observer(source,reset,raw,read):
    # The observer is generated against the patched image. Locate the private
    # MDMAEN trigger by its full instruction/restore prefix (one occurrence).
    region=read(raw,split.NMI,0x900)
    sig=bytes.fromhex('e220a9808f0b4200688f764300')
    if region.count(sig)!=1:raise ValueError('physical transfer seam')
    ret=split.NMI+region.index(sig)+8
    t=fg.observer(source,reset,raw,read)
    a=t.index('local bins={}')
    b=t.index('local wmax=',a)
    def offs(addr):return (addr>>16)*32768+(addr&32767)
    table=','.join('{%d,%d,%d}'%(offs(src),dest*2,n) for src,dest,n in split.CHUNKS)
    extra="""local slices={TABLE}
emu.addMemoryCallback(function()
 local w=emu.memType.snesWorkRam;local i=emu.read(0x4d98,w)-128+1;local z=slices[i]
 if not z then print('SPBAD|'..i);return end
 local e=0
 for j=0,z[3]-1 do if emu.read(z[1]+j,emu.memType.snesPrgRom)~=emu.read(z[2]+j,emu.memType.snesVideoRam)then e=e+1 end end
 local s=emu.getState();print('SP67|'..i..'|'..n..'|'..z[3]..'|'..e..'|'..s['ppu.scanline']..'|'..s.masterClock)
end,emu.callbackType.exec,RET,RET,emu.cpuType.snes,emu.memType.snesPrgRom)
"""
    t=t[:a]+extra.replace('TABLE',table).replace('RET',str(offs(ret)))+t[b:]
    if len(t.encode())>=4096:raise ValueError('unchanged observer cap')
    return t
