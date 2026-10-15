"""Isolated native integration for the supplied single-pass restoration overlay.

Run in snes-bor with the retained Windows Poppy/Mesen inputs. No original source
file or historical auditor is edited. The native execution is NOT performed by
this package's offline tests; --suite performs it and enforces acceptance.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import restore_single_pass as rp
from restore_single_pass_vm import assemble

DEFAULT_BASE = Path('out/byor-motu-home-bitmap-v2/success/native')
DEFAULT_BASELINE_ROOT = Path('out/byor-motu-home-bitmap-v2')
BASELINE_RECEIPT = Path('docs/receipts/byor-motu-home-bitmap.json')
MS = 21477.270
_saved = None


def legacy():
    global _saved
    if _saved is None:
        import m4_home_borrow_bitmap_native as bm
        _saved = SimpleNamespace(module=bm, transform=bm.bitmap_transform,
                                 audit=bm.audit_rom, observe=bm.observer,
                                 certify=bm.certify, run_case=bm.run_case)
    return _saved


def full_overlay(source):
    return rp.transform(legacy().transform(source))


def audit_rom(rom, native):
    old = legacy()
    # Reuse exact-source, full-ROM, movement-byte, storage and branch auditing.
    with patch.object(old.module, 'bitmap_transform', full_overlay):
        result = old.audit(rom, native)
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    sy = symbols(native/'publisher.sym')
    if not (sy['NbRestorePlan'] < sy['NbActorPlanStart'] < sy['RpResolveRestore']
            < sy['RpCodeEnd'] == sy['NbCodeEnd'] < 0x39B000):
        raise ValueError('RP_CODE_OR_STACK_LAYOUT')
    # Independent byte encoder checks both inserted blocks, not just Poppy's
    # comparison against its own output. All external addresses come from the
    # audited complete symbol map. Branch ranges are checked by both encoders.
    byte_checks = []
    for label, lines in (('NbRestorePlan', rp.main_loop()),
                         ('RpResolveRestore', rp.resolver())):
        locals_ = {x[:-1] for x in lines if x.endswith(':')}
        externals = {k:v for k,v in sy.items() if k not in locals_}
        program = assemble(lines, base=sy[label], externals=externals)
        start = offset(sy[label])
        if bytes(rom[start:start+len(program.data)]) != program.data:
            raise ValueError('RP_INDEPENDENT_OPCODE_MISMATCH:'+label)
        byte_checks.append(dict(label=label, bytes=len(program.data)))
    result['single_pass_restoration'] = dict(
        independent_opcode_checks=byte_checks, additional_ram=0,
        original_record_capacity=48, original_tail_allocator=True,
        resolver_entered_by_jmp=True, original_allocation_unwind_depth=True)
    return result


def observer_extension(sy):
    def cb(name, body):
        return (f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,'
                f'{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n')
    text = '''
local rpActive=false
local rpRows=0
local rpProbes=0
local rpRefs=nil
local rpCommitted=nil
local function rpFinish(reason)
 if not rpActive then return end
 if cpDump(0x42d000,1536)~=rpRefs or cpDump(0x42c800,2048)~=rpCommitted then
  nbLog('FAULT','RP_COMMITTED_OWNERSHIP_CHANGED')
 end
 nbLog('RP_END',nbTxn..'|'..reason..'|'..rpRows..'|'..rpProbes..'|'..nbWord(0x3418)..'|'..nbWord(0x342e)..'|'..nbWord(0x42d606)..'|'..cpDump(0x42c000,2048)..'|'..cpDump(0x3480,128)..'|'..cpDump(0x42d620,64))
 rpActive=false
end
'''
    text += cb('NbRestorePlan', '''
if not rpActive then
 if nbWord(0x3418)~=0 or nbWord(0x42d606)~=0 or nbWord(0x42d600)~=1 or nbWord(0x42d660)~=0 or nbWord(0x42d608)~=0 or nbWord(0x42d70c)~=0 then nbLog('FAULT','RP_START_OWNERSHIP')end
 rpActive=true;rpRows=0;rpProbes=0
 rpRefs=cpDump(0x42d000,1536);rpCommitted=cpDump(0x42c800,2048)
 nbLog('RP_BEGIN',nbTxn..'|'..nbWord(0x42d674)..'|'..nbWord(0x342e)..'|'..cpDump(0x42c000,2048)..'|'..rpRefs)
end
''')
    text += cb('RpCellLoaded', "if not rpActive or nbWord(0x3418)~=rpRows then nbLog('FAULT','RP_REPEATED_OR_SKIPPED_CELL')end;rpRows=rpRows+1")
    for label in ('RpReadIramHome', 'RpReadSpillHome'):
        text += cb(label, "if not rpActive then nbLog('FAULT','RP_RECORD_WITHOUT_PLAN')end;rpProbes=rpProbes+1")
    text += cb('NbActorPlanStart', "rpFinish('complete')")
    text += cb('NbBeginRetry', "rpFinish('retry')")
    text += cb('NbAbort', "rpFinish('abort')")
    for label in ('NbPreloadPair', 'BhPrepare', 'SpReadyBoundary'):
        text += cb(label, "if rpActive then nbLog('FAULT','RP_PLAN_NOT_FINISHED')end")
    for cpu in ('snes','sa1'):
        text += ("emu.addMemoryCallback(function(a,v)if rpActive then local s=emu.getState();"
                 "local pc=s['cpu.pc']+65536*s['cpu.k'];local off=a&0xffff;local expected=0xc000+2*nbWord(0x3418);"
                 f"if '{cpu}'~='snes' or pc<{sy['NbRestorePlan']} or pc>={sy['NbActorPlanStart']} or (off~=expected and off~=expected+1) then nbLog('FAULT','RP_NONCURRENT_MAP_WRITE')end "
                 f"end end,emu.callbackType.write,0x2c000,0x2c7ff,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
        text += ("emu.addMemoryCallback(function(a,v)if rpActive then nbLog('FAULT','RP_FROZEN_MAP_OR_DIRECTORY_WRITE')end end,"
                 f"emu.callbackType.write,0x2c800,0x2d5ff,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
        text += ("emu.addMemoryCallback(function(a,v)if rpActive then nbLog('FAULT','RP_QUEUE_TOUCHED')end end,"
                 f"emu.callbackType.write,0x500,0x6df,emu.cpuType.{cpu},emu.memType.sa1InternalRam)\n")
        text += ("emu.addMemoryCallback(function(a,v)if rpActive then nbLog('FAULT','RP_LATCH_TOUCHED')end end,"
                 f"emu.callbackType.write,0x2d60c,0x2d61f,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
        text += ("emu.addMemoryCallback(function(a,v)if rpActive then nbLog('FAULT','RP_JOURNAL_TOUCHED')end end,"
                 f"emu.callbackType.write,0x2d700,0x2d78f,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
    return text


def observer(script, contract):
    legacy().observe(script, contract)
    with script.open('a') as stream:
        stream.write(observer_extension(contract['native_symbols']))


def _words(hex_string):
    raw = bytes.fromhex(hex_string)
    if len(raw)%2:
        raise ValueError('Odd word dump')
    return [int.from_bytes(raw[i:i+2],'little') for i in range(0,len(raw),2)]


def verify_plan(begin, finish):
    """Independent eager oracle; compare completed plans and exact failures."""
    data, end = begin['data'], finish['data']
    txn, exact, cursor = map(int,data[:3])
    if len(data)!=5 or len(end)!=10 or int(end[0])!=txn:
        raise ValueError('RP_TRACE_SCHEMA_OR_TRANSACTION')
    pending, refs = _words(data[3]), _words(data[4])
    result = rp.reference(pending,refs,cursor)
    reason = end[1]
    expected_reason = ('complete' if result['success'] else
                       'retry' if not exact and result['failure']=='tail_exhausted' else 'abort')
    if reason != expected_reason:
        raise ValueError('RP_OUTCOME_CHANGED')
    rows, probes, cell, cursor_after, count = map(int,end[2:7])
    expected_rows = result['stopped_cell'] + (not result['success'])
    if rows!=expected_rows or cell!=result['stopped_cell'] or cursor_after!=result['cursor']:
        raise ValueError('RP_NOT_ONE_ORDERED_MAP_PASS')
    records_raw = _words(end[8])+_words(end[9])
    pairs = list(zip(records_raw[::2],records_raw[1::2]))[:count]
    if pairs != result['records'] or count > 48:
        raise ValueError('RP_RECORD_OR_ALLOCATION_ORDER_CHANGED')
    final = _words(end[7])
    if result['success']:
        if final != result['pending']:
            raise ValueError('RP_FINAL_MAP_CHANGED')
    else:
        # Only already-visited cells may be rerouted in a rejected private map.
        # No equality with the old planner's eager, whole-map partial reroutes
        # is assumed. The inherited native abort/retry then discards this map.
        lookup = dict(pairs)
        expected = [lookup[w]|0x4000 if i<cell and w in lookup else w
                    for i,w in enumerate(pending)]
        if final != expected:
            raise ValueError('RP_REJECTED_PRIVATE_PREFIX_INVALID')
    elapsed = finish['clock']-begin['clock']
    if elapsed<=0:
        raise ValueError('RP_INVALID_TIMING')
    return dict(transaction=txn, exact=bool(exact), outcome=reason,
                map_words=rows, restoration_record_probes=probes,
                records=[list(pair) for pair in pairs], tail_cursor_after=cursor_after,
                elapsed_clocks=elapsed, elapsed_ms=elapsed/MS,
                successful_map_matches_eager_oracle=result['success'],
                reservation_order_matches_eager_oracle=True)


def evidence(folder):
    plans=[];active=None
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'callback_owner.lua:' in line:
            raise ValueError('RP_OBSERVER_LUA_ERROR:'+line)
        if 'NB_' not in line:
            continue
        parts=line[line.index('NB_'):].split('|')
        kind=parts[0][3:]
        if kind=='FAULT':
            raise ValueError('RP_UNFILTERED_NATIVE_FAULT:'+'|'.join(parts[4:]))
        if kind=='RP_BEGIN':
            if active is not None:raise ValueError('RP_OVERLAPPING_PLANS')
            active=dict(clock=int(parts[1]),data=parts[4:])
        elif kind=='RP_END':
            if active is None:raise ValueError('RP_END_WITHOUT_BEGIN')
            plans.append(verify_plan(active,dict(clock=int(parts[1]),data=parts[4:])))
            active=None
    if active is not None or not plans:
        raise ValueError('RP_INCOMPLETE_OR_MISSING_TRACE')
    return dict(plans=plans, independent_original_planner_oracle=True,
                zero_new_ram=True, timing_boundary='First NbRestorePlan entry to NbActorPlanStart, NbAbort or NbBeginRetry; contains allocation and remapping, not BhPrepare')


def certify(folder):
    old=legacy()
    with patch.object(old.module,'audit_rom',audit_rom):
        result=old.certify(folder)
    result['single_pass_restoration']=evidence(folder)
    result['classification']='RESTORE_SINGLE_PASS_NATIVE_CORRECT'
    (folder/'remap-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def bootstrap_prefix(script):
    marker='-- NONBLANK_OBSERVER_BEGIN'
    if script.count(marker)!=1:
        raise ValueError('RP_BOOTSTRAP_MARKER')
    return script.split(marker,1)[0]


def build(folder,base,dotnet,poppy):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    if folder.exists():raise ValueError('Use a fresh output directory; nothing is overwritten')
    oldrom=(base/'bor.sfc').read_bytes()
    if hashlib.sha256(oldrom).hexdigest()!=rp.BASE_ROM_SHA256:
        raise ValueError('RP_PINNED_BITMAP_BASE_SHA')
    legacy().audit(oldrom,base)
    lines=rp.transform((base/'publisher.pasm').read_text().splitlines())
    native=folder/'native';native.mkdir(parents=True)
    (native/'publisher.pasm').write_text('\n'.join(lines)+'\n')
    command=[str(dotnet),str(poppy),str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),
             '--symbols',str(native/'publisher.sym'),'--no-pansy']
    run=subprocess.run(command,capture_output=True,text=True)
    (native/'publisher-build.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError('Poppy failed; see publisher-build.log')
    sy=symbols(native/'publisher.sym');oldsy=symbols(base/'publisher.sym')
    compiled=(native/'publisher.bin').read_bytes()
    if not (oldsy['NbCodeEnd'] < sy['NbCodeEnd'] < 0x39B000):
        raise ValueError('RP_EXPECTED_A_CODE_EXTENSION')
    if sy['NbCodeEnd']-oldsy['NbCodeEnd']!=53:
        raise ValueError('RP_UNEXPECTED_CODE_SIZE')
    if any(oldrom[offset(oldsy['NbCodeEnd']):offset(sy['NbCodeEnd'])]):
        raise ValueError('RP_EXTENSION_NOT_ZERO')
    if sy['SpCodeEnd']!=oldsy['SpCodeEnd'] or sy['BhCodeEnd']!=oldsy['BhCodeEnd']:
        raise ValueError('RP_UNRELATED_HELPER_SIZE_CHANGED')
    rom=bytearray(oldrom)
    ranges=((0x398000,sy['OnlineReject']+8),(0x39A000,sy['NbCodeEnd']),
            (0x39B000,sy['SpCodeEnd']),(0x39B300,sy['BhCodeEnd']))
    for lo,hi in ranges:
        a,b=offset(lo),offset(hi)
        if b>len(compiled):raise ValueError('RP_SHORT_ASSEMBLER_OUTPUT')
        rom[a:b]=compiled[a:b]
    audit=audit_rom(rom,native)
    (native/'bor.sfc').write_bytes(rom)
    contract=copy.deepcopy(json.loads((base.parent/'contract.json').read_text()))
    contract['native_symbols'].update(sy)
    contract.update(restore_single_pass=True,restore_single_base_sha256=rp.BASE_ROM_SHA256,
                    restore_single_audit=audit)
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    (native/'callback_owner.lua').write_text(bootstrap_prefix((base/'callback_owner.lua').read_text()))
    # Reuse existing media, never regenerate artwork or duplicate PCM.
    os.link((base/'bor.msu').resolve(),native/'bor.msu')
    return contract


def run_case(folder,case):
    old=legacy()
    with patch.object(old.module,'observer',observer),patch.object(old.module,'audit_rom',audit_rom),\
         patch.object(old.module,'certify',certify):
        result=old.run_case(folder,case)
    if case=='right':
        result['single_pass_restoration']=evidence(folder)
        (folder/'remap-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def require(condition,message):
    if not condition:raise ValueError('RESTORE_SINGLE_ACCEPTANCE:'+message)


def collect_suite(root,baseline_root=DEFAULT_BASELINE_ROOT):
    old=legacy();baseline=json.loads(BASELINE_RECEIPT.read_text());results={}
    for case in old.module.CASES:
        folder=root/case
        if case=='right':
            result=json.loads((folder/'remap-result.json').read_text())
            require(result['single_pass_restoration']==evidence(folder),'RIGHT trace drift')
        else:result=certify(folder)
        result=json.loads(json.dumps(result))  # normalize integer dictionary keys from fresh certifiers
        reference=baseline['cases'][case]
        require(result['pixel_mismatches']==result['resource_faults']==result['unsafe_ppu_operations']==0,case+': correctness')
        require(result['min_batch_margin_clocks']>=10000,case+': VBlank margin')
        for suffix in ('world','committed','pending','refs','cgram'):
            for file in (folder/'native').glob('*-'+suffix+'.bin'):
                previous=baseline_root/case/'native'/file.name
                require(previous.exists() and file.read_bytes()==previous.read_bytes(),case+': final/source identity '+file.name)
        if case=='right':
            require(result['transition_fields']<=reference['transition_fields'],'RIGHT gained a field')
        else:
            require(result['source_pixel_difference']==1816,case+': changed picture')
            pools,previous_pools=result.get('pools',{}),reference.get('pools',{})
            require(set(pools)==set(previous_pools),case+': borrowing transactions')
            require(all(all(pools[k][field]==v[field] for field in
                            ('homes','original_invalid','original_valid','policy','limit','need'))
                        for k,v in previous_pools.items()),case+': borrowed-home ordering')
            # Clock fields differ; physical choices and validity obligations do not.
            require(len(result['bitmap']['plans'])==len(reference['bitmap']['plans']),case+': bitmap branch')
        results[case]=result
    success=results['success'];prior=baseline['cases']['success']
    first,second=success['transactions'][:2]
    require(first['fields']<=32 and first['master_clocks']<=prior['transactions'][0]['master_clocks']*1.01,'epoch 2 regression')
    require(second['fields']<49 and second['master_clocks']<17751938,'no native epoch-3 improvement')
    transfer=next(t for t in success['transfers'] if t['transaction']==3)
    require((transfer['chr_pairs'],transfer['chr_bytes'],transfer['map_bytes'],transfer['descriptors'])==(105,8400,4096,212),'transfer workload')
    require(len([b for b in success['batches'] if b['transaction']==3])==18,'18 preload batches')
    plan=next(p for p in success['ready_residency_checks'] if p['transaction']==3)
    require((plan['actor_tiles'],len(plan['restoration_homes']),plan['tail_reservations'],plan['borrowed_reservations'])==(95,10,64,41),'reservation counts')
    refs=(root/'success/native/after-second-refs.bin').read_bytes()
    require(sum(bool(int.from_bytes(refs[i:i+2],'little')&0x3fff) for i in range(0,len(refs),2))==639,'final physical residency')
    require(any(p['transaction']==4 and p['home']==204 and p['destination']==634 and not p['rollback']
                for p in results['valid']['backdrop_restorations']),'later source-owned restoration')
    for case in ('early','ready','partial','stale'):
        require(bool(results[case]['validity_clear_events']),case+': restoration fences')
    require(next(t for t in results['insufficient']['transfers'] if t['transaction']==3)['descriptors']==0,'budget-failure DMA')
    # Preserve the actual inherited dirty files and unrelated deletion. This
    # reads the accepted receipt; it never stages or changes repository files.
    for entry in baseline['inherited_dirty_files_preserved']:
        require(hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()==entry['sha256'],'inherited dirty file '+entry['path'])
    require(not Path('SNES-BOR-Engine-Prompt.md').exists(),'unrelated deletion changed')
    report=dict(classification='BYOR_MOTU_RESTORATION_SINGLE_PASS_PASS',base_commit=rp.BASE_COMMIT,
                verified_fields=sum(r['observed_fields'] for r in results.values()),
                verified_pixels=sum(r['verified_pixels'] for r in results.values()),
                pixel_mismatches=0,resource_faults=0,unsafe_ppu_operations=0,
                cases=results,code_bytes_added=53,ram_bytes_added=0,
                nonclaims=['30 FPS','200-Hz scheduling','SA-1 concurrency','audio','HUD','combat','Demo readiness'])
    (root/'single-pass-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['classification'],report['verified_fields'],report['verified_pixels'],flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--base-native',type=Path,default=DEFAULT_BASE)
    p.add_argument('--baseline-root',type=Path,default=DEFAULT_BASELINE_ROOT)
    p.add_argument('--dotnet',type=Path,default=Path(os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe')))
    p.add_argument('--poppy',type=Path,default=Path(os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll')))
    p.add_argument('--suite',action='store_true')
    p.add_argument('--collect-suite',action='store_true')
    p.add_argument('--build-only',action='store_true')
    p.add_argument('--case',choices=('success','valid','early','ready','partial','stale','insufficient','right'),default='success')
    p.add_argument('--collect',action='store_true')
    a=p.parse_args();folder=a.output.resolve()
    if a.collect_suite:
        if a.suite or a.collect or a.build_only:raise ValueError('Use --collect-suite by itself')
        collect_suite(folder,a.baseline_root);return
    if a.collect:
        if a.suite or a.build_only:raise ValueError('Use --collect by itself')
        certify(folder);return
    if a.suite:
        if folder.exists():raise ValueError('Suite output must be new')
        for case in legacy().module.CASES:
            child=folder/case
            print('RESTORE SINGLE-PASS CASE',case,flush=True)
            build(child,a.base_native.resolve(),a.dotnet,a.poppy)
            if not a.build_only:run_case(child,case)
        if not a.build_only:collect_suite(folder,a.baseline_root)
    else:
        build(folder,a.base_native.resolve(),a.dotnet,a.poppy)
        if not a.build_only:run_case(folder,a.case)

if __name__=='__main__':main()
