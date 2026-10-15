"""Isolated Poppy/Mesen adapter for the bitmap overlay; no historical file edits.

Run from snes-bor root with PYTHONPATH=.;tools/bor_compile;tools/verify.
This script itself has NOT been run in the author's environment: the retained
ROM/PAK, private fixtures, Windows Poppy and Mesen are on the user's machine.
It reuses their existing native proofs and adds explicit bitmap-lifetime checks.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from home_borrow_bitmap import (transform as bitmap_transform,membership_reference,
    BASE_ROM_SHA256,COMMITTED_BITS,PENDING_BITS,BITMAP_END)

DEFAULT_BASE=Path('out/byor-motu-home-borrow-success-v5/native')
_saved=None


def legacy():
    global _saved
    if _saved is None:
        import home_borrow
        import m4_home_borrow_native as native
        import m4_home_borrow_evidence as evidence
        _saved=SimpleNamespace(native=native,evidence=evidence,raw_transform=home_borrow.transform,
            audit=native.audit_rom,observe=native.observer,run_case=native.run_case,
            run_right=native.run_right_control,certify=evidence.certify)
    return _saved


def composed_transform(source):
    return bitmap_transform(legacy().raw_transform(source))


def audit_rom(rom,native):
    old=legacy()
    # Retain the same whole-ROM, movement-body, branch and memory-lease auditor.
    # Only its exact expected source transformation is candidate-specific.
    with patch.object(old.native,'transform',composed_transform):
        result=old.audit(rom,native)
    from actor_s5_entity_fixture import symbols
    sy=symbols(native/'publisher.sym')
    if not sy['BhBitmapLeaseBegin']<sy['BhBitmapBuilt']<sy['BhBitmapAddress']<sy['BhBitmapMasks']<sy['BhCodeEnd']<0x39C000:
        raise ValueError('BITMAP_HELPER_CODE_LAYOUT')
    result['temporary_queue_bitmap_lease']=[COMMITTED_BITS,BITMAP_END]
    result['bitmap_payload_bytes']=152
    result['bitmap_rom_mask_bytes']=32
    result['bitmap_persistent_ram_added']=0
    return result


def authorize_empty_queue_builder(script:str,sy:dict[str,int])->str:
    """Narrow the existing S-CPU queue guard exception to these exact writes.

    The SA-1 rule and all ordinary producer/record/canary rules are untouched.
    bbLive is a Lua observer state, NOT a runtime RAM allocation.
    """
    old=f"if 'snes'~='snes' or pc<{sy['NbBegin']} or pc>={sy['NbCodeEnd']} then nbLog('FAULT','QUEUE_OWNER:snes|'..a)"
    allowed=(f"bbLive and 'snes'=='snes' and pc>={sy['BhBitmapLeaseBegin']} "
             f"and pc<{sy['BhBitmapBuilt']} and (a&0x7ff)>=0x500 and (a&0x7ff)<0x598 "
             "and nbWord(0x42d600)==1 and nbWord(0x42d660)==0 "
             "and nbWord(0x42d608)==0 and nbWord(0x42d60a)==0 and nbWord(0x42d70c)==0")
    new=(f"if not ({allowed}) and ('snes'~='snes' or pc<{sy['NbBegin']} or pc>={sy['NbCodeEnd']}) "
         "then nbLog('FAULT','QUEUE_OWNER:snes|'..a)")
    if script.count(old)!=1:
        raise ValueError('BITMAP_QUEUE_OBSERVER_ANCHOR_CHANGED')
    return 'local bbLive=false;local bbBuilding=false;local bbLoops=0;local bbQueries=0\n'+script.replace(old,new,1)


def observer(script,contract):
    legacy().observe(script,contract)
    sy=contract['native_symbols']
    text=authorize_empty_queue_builder(script.read_text(),sy)
    def cb(name,body):
        return (f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,'
                f'{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n')
    text+=cb('BhBitmapLeaseBegin',
        "if bbLive then nbLog('FAULT','BITMAP_REENTRANT_LEASE')end;"
        "bbLive=true;bbBuilding=true;bbLoops=0;bbQueries=0;"
        "nbLog('BITMAP_BEGIN',nbTxn..'|'..cpDump(0x42c800,2048)..'|'..cpDump(0x42c000,2048)..'|'..cpDump(0x42d000,1536))")
    text+=cb('BhBitmapMapLoop',"bbLoops=bbLoops+1")
    text+=cb('BhBitmapBuilt',
        "if not bbLive or not bbBuilding or bbLoops~=1024 then nbLog('FAULT','BITMAP_BUILD_LIFETIME')end;"
        "bbBuilding=false;nbLog('BITMAP_BUILT',nbTxn..'|'..bbLoops..'|'..cpDump(0x3500,152))")
    text+=cb('BhEligible',
        "if not bbLive or bbBuilding then nbLog('FAULT','BITMAP_LOOKUP_WITHOUT_BUILD')end;bbQueries=bbQueries+1")
    for name in ('BhPrepareOK','BhPrepareBad'):
        text+=cb(name,
            "if bbLive then if bbBuilding or nbWord(0x42d660)~=0 then nbLog('FAULT','BITMAP_RELEASE_LIFETIME')end;"
            "bbLive=false;nbLog('BITMAP_END',nbTxn..'|'..bbQueries..'|'..cpDump(0x42c800,2048)..'|'..cpDump(0x42c000,2048)..'|'..cpDump(0x42d000,1536))end")
    for name in ('NbPreloadPair','NbAbort','SpReadyBoundary'):
        text+=cb(name,"if bbLive then nbLog('FAULT','BITMAP_LEASE_NOT_RELEASED')end")
    # Both CPUs remain subject to physical write ownership. Host observation is
    # never accepted as source execution, and no fault log is filtered out.
    for cpu in ('snes','sa1'):
        text+=("emu.addMemoryCallback(function(a,v)if bbLive then local s=emu.getState();"
            "local pc=s['cpu.pc']+65536*s['cpu.k'];"
            f"if '{cpu}'~='snes' or pc<{sy['BhBitmapLeaseBegin']} or pc>={sy['BhBitmapBuilt']} "
            "or (a&0x7ff)<0x500 or (a&0x7ff)>=0x598 then nbLog('FAULT','BITMAP_QUEUE_WRITE_OWNER')end "
            f"end end,emu.callbackType.write,0x500,0x6df,emu.cpuType.{cpu},emu.memType.sa1InternalRam)\n")
        text+=("emu.addMemoryCallback(function(a,v)if bbLive then nbLog('FAULT','BITMAP_FROZEN_MAP_OR_REF_WRITE')end end,"
            f"emu.callbackType.write,0x2c000,0x2d5ff,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
        text+=("emu.addMemoryCallback(function(a,v)if bbLive and not bbBuilding then nbLog('FAULT','BITMAP_REPEATED_MAP_READ')end end,"
            f"emu.callbackType.read,0x2c000,0x2cfff,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
    script.write_text(text)


def bitmap_evidence(folder):
    active=None;records=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'callback_owner.lua:' in line:
            raise ValueError('BITMAP_OBSERVER_LUA_ERROR:'+line)
        if 'NB_' not in line:continue
        p=line[line.index('NB_'):].split('|')
        kind=p[0][3:];clock=int(p[1]);data=p[4:]
        if kind=='FAULT':raise ValueError('BITMAP_NATIVE_FAULT:'+'|'.join(data))
        if kind=='BITMAP_BEGIN':
            if active is not None:raise ValueError('BITMAP_OVERLAPPING_PLANS')
            txn,cm,pm,refs=data
            active=dict(transaction=int(txn),start=clock,committed=cm,pending=pm,refs=refs)
        elif kind=='BITMAP_BUILT':
            if active is None or active['transaction']!=int(data[0]):raise ValueError('BITMAP_BUILD_WITHOUT_BEGIN')
            if 'built' in active or int(data[1])!=1024:raise ValueError('BITMAP_NOT_ONE_MAP_PASS')
            def words(s):
                b=bytes.fromhex(s)
                return [int.from_bytes(b[i:i+2],'little') for i in range(0,len(b),2)]
            expected=b''.join(membership_reference(words(active['committed']),words(active['pending'])))
            if bytes.fromhex(data[2])!=expected:raise ValueError('BITMAP_NATIVE_BITS_INCORRECT')
            active['built']=clock;active['bitmap_sha256']=hashlib.sha256(expected).hexdigest()
        elif kind=='BITMAP_END':
            if active is None or active['transaction']!=int(data[0]) or 'built' not in active:
                raise ValueError('BITMAP_RELEASE_WITHOUT_COMPLETE_BUILD')
            if data[2:]!=[active['committed'],active['pending'],active['refs']]:
                raise ValueError('BITMAP_INPUTS_CHANGED_DURING_PLAN')
            records.append(dict(transaction=active['transaction'],lookup_calls=int(data[1]),
                map_words_per_input=1024,build_clocks=active['built']-active['start'],
                indexed_lifetime_clocks=clock-active['start'],bitmap_sha256=active['bitmap_sha256']))
            active=None
    if active is not None:raise ValueError('BITMAP_LIVE_LEASE_AT_EXIT')
    return dict(plans=records,all_memberships_independently_verified=True,
                zero_bitmap_map_rescans=True,zero_live_queue_borrow=True,
                scratch_bytes=152,persistent_ram_bytes_added=0)


def certify(folder):
    old=legacy()
    with patch.object(old.evidence,'audit_rom',audit_rom):
        result=old.certify(folder)
    result['bitmap']=bitmap_evidence(folder)
    result['classification']='BYOR_MOTU_HOME_BORROW_BITMAP_NATIVE_CORRECT'
    (folder/'bitmap-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def bootstrap_script(script):
    # The accepted home-borrow fixture already uses the nonblank observer.
    marker='-- NONBLANK_OBSERVER_BEGIN'
    if script.count(marker)!=1:raise ValueError('BITMAP_BOOTSTRAP_OBSERVER_MARKER')
    return script.split(marker)[0]


def build(folder,base,dotnet,poppy):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    if folder.exists():raise ValueError('Use a NEW output directory; nothing will be overwritten')
    oldrom=(base/'bor.sfc').read_bytes()
    if hashlib.sha256(oldrom).hexdigest()!=BASE_ROM_SHA256:raise ValueError('BITMAP_BASE_ROM_SHA')
    legacy().audit(oldrom,base)
    source=(base/'publisher.pasm').read_text().splitlines()
    lines=bitmap_transform(source)
    native=folder/'native';native.mkdir(parents=True)
    (native/'publisher.pasm').write_text('\n'.join(lines)+'\n')
    command=[str(dotnet),str(poppy),str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),
             '--symbols',str(native/'publisher.sym'),'--no-pansy']
    run=subprocess.run(command,capture_output=True,text=True)
    (native/'publisher-build.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError('Poppy failed; see publisher-build.log')
    sy=symbols(native/'publisher.sym');compiled=(native/'publisher.bin').read_bytes()
    oldsy=symbols(base/'publisher.sym')
    if sy['BhCodeEnd']>=0x39C000:raise ValueError('BITMAP_ROM_CAPACITY')
    if any(oldrom[offset(oldsy['BhCodeEnd']):offset(sy['BhCodeEnd'])]):
        raise ValueError('BITMAP_EXTENSION_LEASE_NOT_ZERO')
    rom=bytearray(oldrom)
    ranges=((0x398000,sy['OnlineReject']+8),(0x39A000,sy['NbCodeEnd']),
            (0x39B000,sy['SpCodeEnd']),(0x39B300,sy['BhCodeEnd']))
    for lo,hi in ranges:
        start,end=offset(lo),offset(hi)
        if end>len(compiled):raise ValueError('BITMAP_SHORT_ASSEMBLER_OUTPUT')
        rom[start:end]=compiled[start:end]
    audit=audit_rom(rom,native)
    (native/'bor.sfc').write_bytes(rom)
    contract=json.loads((base.parent/'contract.json').read_text())
    contract=copy.deepcopy(contract);contract['native_symbols'].update(sy)
    contract.update(home_borrow_bitmap=True,bitmap_base_sha256=BASE_ROM_SHA256,
        bitmap_queue_lease=[COMMITTED_BITS,BITMAP_END],bitmap_audit=audit)
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    script=(base/'callback_owner.lua').read_text()
    (native/'callback_owner.lua').write_text(bootstrap_script(script))
    # Reuse the same media; never duplicate PCM or regenerate assets.
    os.link((base/'bor.msu').resolve(),native/'bor.msu')
    return contract


CASES={
    'success':{},
    'valid':dict(policy=1,valid_limit=1,later_restore=True),
    'early':dict(policy=1,valid_limit=1,fault=1),
    'ready':dict(policy=1,valid_limit=1,mode=1),
    'partial':dict(policy=1,valid_limit=1,mode=2),
    'stale':dict(policy=1,valid_limit=1,mode=3),
    'insufficient':dict(limit=40),
    'right':None,
}


def run_case(folder,case):
    from actor_s5_entity_fixture import symbols
    from compiler import Source
    old=legacy();contract=json.loads((folder/'contract.json').read_text())
    if not contract.get('home_borrow_bitmap'):raise ValueError('Not a bitmap candidate')
    source=Source(Path('Masters of the Universe [v.3.0 Build 4086].pak'))
    sy=symbols(Path('src/main.sym'))
    with patch.object(old.native,'observer',observer),patch.object(old.native,'audit_rom',audit_rom),\
         patch.object(old.evidence,'audit_rom',audit_rom):
        if case=='right':old.run_right(folder,source,sy,contract)
        else:old.run_case(folder,source,sy,contract,**CASES[case])
    if case=='right':
        result=json.loads((folder/'result.json').read_text())
        result['bitmap']=bitmap_evidence(folder)
        if result['bitmap']['plans']:raise ValueError('Unexpected bitmap work in RIGHT control')
        (folder/'bitmap-result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    return certify(folder)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--base-native',type=Path,default=DEFAULT_BASE)
    p.add_argument('--dotnet',type=Path,default=Path(os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe')))
    p.add_argument('--poppy',type=Path,default=Path(os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll')))
    p.add_argument('--case',choices=tuple(CASES),default='success')
    p.add_argument('--suite',action='store_true',help='Build and run all eight cases SEQUENTIALLY')
    p.add_argument('--build-only',action='store_true')
    p.add_argument('--run-existing',action='store_true')
    p.add_argument('--collect',action='store_true',help='Re-certify an existing non-RIGHT case')
    a=p.parse_args();folder=a.output.resolve();base=a.base_native.resolve()
    if a.collect:
        if a.suite or a.build_only or a.run_existing:raise ValueError('Use --collect by itself')
        certify(folder);return
    if a.suite:
        if folder.exists():raise ValueError('Suite output directory must be new')
        results={}
        for case in CASES:
            child=folder/case
            print('BITMAP CASE',case,flush=True)
            build(child,base,a.dotnet,a.poppy)
            if not a.build_only:results[case]=run_case(child,case)
        if results:(folder/'bitmap-suite.json').write_text(json.dumps(results,indent=2)+'\n')
    else:
        if not a.run_existing:build(folder,base,a.dotnet,a.poppy)
        if not a.build_only:run_case(folder,a.case)

if __name__=='__main__':main()
