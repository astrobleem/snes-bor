"""Shared I-RAM ownership probe before enabling the batching backend.

Diagnostic ROM changes are a cold-only JSR and a B000 canary/DMA helper.
The genuine source controller test and old renderer execute unchanged.
"""
import json
from pathlib import Path
from unittest.mock import patch
import m4_nonblank_component_native as old
from compiler import Source
from actor_s5_entity_fixture import symbols

FOLDER=Path('out/byor-motu-batch-lease-v1')
original_observer=old.observer

def observer(script,contract):
    original_observer(script,contract)
    sy=contract['native_symbols']
    with script.open('a') as f:
        f.write("local leaseFilling=false;local leaseDone=false;local leaseBefore=0;local leaseUnexpected=0;local leaseFillWrites=0;local leaseFields=0\n")
        def cb(at,body):f.write(f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb(sy['LeaseProbe'],"leaseFilling=true;nbLog('LEASE_ENTRY',leaseBefore)")
        cb(sy['LeaseHighDone']+2,"if nbActive then nbLog('DONE',nbTxn..'|'..nbSource..'|'..nbSize..'|'..nbTarget);nbActive=false end")
        cb(sy['LeaseLowDone']+2,"if nbActive then nbLog('DONE',nbTxn..'|'..nbSource..'|'..nbSize..'|'..nbTarget);nbActive=false end")
        cb(sy['LeaseComplete'],"leaseFilling=false;leaseDone=true;local s=emu.getState();nbLog('LEASE_PERMISSIONS',tostring(s['cart.coprocessor.cpuIRamWriteProtect'])..'|'..tostring(s['cart.coprocessor.sa1IRamWriteProtect']));local t={};for i=0,607 do t[#t+1]=string.format('%02x',emu.read(0x3480+i,emu.memType.snesMemory))end;nbLog('LEASE_CANARY',table.concat(t));local v={};for i=0,63 do v[#v+1]=string.format('%02x',emu.read(0xbfc0+i,emu.memType.snesVideoRam))end;for i=0,15 do v[#v+1]=string.format('%02x',emu.read(0xeff0+i,emu.memType.snesVideoRam))end;nbLog('LEASE_DMA_READBACK',table.concat(v))")
        for cpu in ('snes','sa1'):
            f.write("emu.addMemoryCallback(function(a,v)if leaseFilling and '"+cpu+"'=='snes' then leaseFillWrites=leaseFillWrites+1 elseif not leaseDone then leaseBefore=leaseBefore+1;nbLog('LEASE_PRIOR_WRITE','"+cpu+"|'..a)else leaseUnexpected=leaseUnexpected+1;nbLog('LEASE_UNKNOWN_WRITE','"+cpu+"|'..a)end end,emu.callbackType.write,0x480,0x6df,emu.cpuType."+cpu+",emu.memType.sa1InternalRam)\n")
        f.write("emu.addEventCallback(function()if leaseDone then leaseFields=leaseFields+1;local ok=true;for i=0,607 do if emu.read(0x3480+i,emu.memType.snesMemory)~=((i&255)~0xa5)then ok=false;break end end;nbLog('LEASE_FIELD',leaseFields..'|'..tostring(ok)..'|'..leaseFillWrites..'|'..leaseUnexpected)end end,emu.eventType.endFrame)\n")


def certify(folder,contract,fields):
    lines=(folder/'native/mesen.log').read_text(errors='replace').splitlines()
    def event(name):return [line.split('NB_'+name+'|',1)[1].split('|') for line in lines if 'NB_'+name+'|' in line]
    if event('LEASE_PRIOR_WRITE') or event('LEASE_UNKNOWN_WRITE'):raise ValueError('LEASE_OCCUPIED_RUNTIME')
    snapshots=event('LEASE_FIELD')
    if len(snapshots)<250 or any(e[4]!='true' or int(e[5])!=608 or int(e[6]) for e in snapshots):raise ValueError('LEASE_CANARY_OR_WRITABILITY')
    expected=bytes((i&255)^0xa5 for i in range(608))
    if bytes.fromhex(event('LEASE_CANARY')[0][3])!=expected:raise ValueError('LEASE_CANARY_READBACK')
    if bytes.fromhex(event('LEASE_DMA_READBACK')[0][3])!=expected[128:208]:raise ValueError('LEASE_BANK00_DMA_READBACK')
    refs=(folder/'native/cold-refs.bin').read_bytes()
    if int.from_bytes(refs[1534:1536],'little')&0x3fff:raise ValueError('LEASE_PROBE_REFERENCED_SLOT')
    if any(f['ppu']['forcedBlank'] or f['ppu']['brightness']!=15 for f in fields):raise ValueError('LEASE_VISIBLE_CONTROL')
    return dict(classification='IRAM_LEASE_AUDIT_PASS',probe_rom_sha256=old.sha((folder/'native/bor.sfc').read_bytes()),prior_writes_from_both_cpus=0,unexpected_writes_from_both_cpus=0,canary_bytes=608,canary_fields=len(snapshots),verified_visible_fields=len(fields),pixels=len(fields)*57344,pixel_mismatches=0,bank00_dma_readback=True,permissions=event('LEASE_PERMISSIONS'),conditional_owner='Isolated fixture only; returning graphics worker reset, audio/video NMI services withdrawn; no future SA-1 coexecution claim')

def build_probe(folder):
    import os,shutil,subprocess

    base=Path('out/byor-motu-nonblank-v5/native');n=folder/'native';n.mkdir(parents=True,exist_ok=True)
    a=(base/'publisher.pasm').read_text().splitlines();a[a.index('OnlineComplete:'):a.index('OnlineComplete:')]=[' jsr LeaseProbe']
    probe=['.org $B000','LeaseProbe:','.a16','.i16',' php',' rep #$30',' phx',' phy',' sep #$20','.a8',' ldx #0','LeaseFill:',' txa',' eor #$A5',' sta.l $003480,x',' inx',' cpx #608',' bcc LeaseFill',' rep #$20','.a16',' jsr NbFreshVblank']
    for source,size,dest,done in ((0x3500,64,0x5fe0,'LeaseHighDone'),(0x3540,16,0x77f8,'LeaseLowDone')):
        probe +=[f' lda #{dest}',' sta.l $002116',f' lda #{source}',' sta.l $004372',f' lda #{size}',' sta.l $004375',' sep #$20','.a8']
        for reg,val in ((0x4370,1),(0x4371,0x18),(0x4374,0),(0x420b,128)):probe +=[f' lda #{val}',f' sta.l ${reg:06X}']
        probe +=[done+':',' rep #$20','.a16']
    probe +=['LeaseComplete:',' ply',' plx',' plp',' rts','LeaseCodeEnd:'];a[a.index('.org $C000'):a.index('.org $C000')]=probe
    (n/'publisher.pasm').write_text('\n'.join(a)+'\n')
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(n/'publisher.pasm'),'--output',str(n/'publisher.bin'),'--symbols',str(n/'publisher.sym'),'--no-pansy'],capture_output=True,text=True)
    if proc.returncode:raise ValueError('LEASE_PROBE_ASSEMBLY')
    rom=bytearray((base/'bor.sfc').read_bytes());rom[57*32768:58*32768]=(n/'publisher.bin').read_bytes()[57*32768:58*32768].ljust(32768,b'\0');assert len(rom)==4194304;(n/'bor.sfc').write_bytes(rom)
    sy=symbols(n/'publisher.sym');c=json.loads(Path('out/byor-motu-nonblank-v5/contract.json').read_text());c['native_symbols']={k:v for k,v in sy.items() if k.startswith(('Online','Nb','Warm','Astra','Lease'))};c['lease_probe']=True;(folder/'contract.json').write_text(json.dumps(c,indent=2)+'\n');shutil.copyfile(base/'callback_owner.lua',n/'callback_owner.lua')
    if not (n/'bor.msu').exists():os.link(base/'bor.msu',n/'bor.msu')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=FOLDER);p.add_argument('--build',action='store_true');a=p.parse_args();FOLDER=a.output.resolve()
    if a.build:build_probe(FOLDER)
    c=json.loads((FOLDER/'contract.json').read_text())
    with patch.object(old,'observer',observer),patch.object(old,'certify',certify):old.run(FOLDER,Source(Path('Masters of the Universe [v.3.0 Build 4086].pak')),symbols(Path('src/main.sym')),c)
