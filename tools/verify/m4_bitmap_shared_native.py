"""Opt-in Poppy/Mesen runner for exact shared-cell bitmap bitmap update.

Requires existing accepted files, assets, and tools on the user's Windows repo.
The accepted renderer is not changed. This adapter is unexecuted natively in
its authoring environment; offline instruction-bytes tests are separate.
"""
from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import argparse,copy,hashlib,json,os,subprocess

import home_bitmap_shared_cells as bc
import m4_restore_single_pass_native as prior
from bitmap_shared_vm import assemble

BASE=Path('out/byor-motu-restore-single-v2/success/native')
BASELINE=Path('out/byor-motu-restore-single-v2')
CLOCKS_PER_MS=21477.270
ORIGINAL_AUDIT=prior.audit_rom
ORIGINAL_OBSERVER=prior.observer
ORIGINAL_CERTIFY=prior.certify
ORIGINAL_RUN=prior.run_case
ORIGINAL_FULL=prior.full_overlay


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def overlay(source):
    return bc.transform(ORIGINAL_FULL(source))


def audit_rom(rom,native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    # Reuse every accepted source/asset/ROM/stack owner check. Only the exact
    # composed source expectation changes, never the checked machine bytes.
    with patch.object(prior,'full_overlay',overlay):
        evidence=ORIGINAL_AUDIT(rom,native)
    sy=symbols(native/'publisher.sym')
    emitted=(native/'publisher.pasm').read_text().splitlines()
    if emitted!=bc.transform((BASE/'publisher.pasm').read_text().splitlines()):
        raise ValueError('BC_NATIVE_PINNED_SOURCE_MISMATCH')
    source=bc.bitmap_parts(emitted)
    program=assemble(source,base=sy['BhBitmapBuild'])
    from_bitmap=offset(sy['BhBitmapBuild']);to_bitmap=offset(sy['BhBitmapCodeEnd'])
    if program.data!=bytes(rom[from_bitmap:to_bitmap]):
        raise ValueError('BC_INDEPENDENT_BUILDER_MACHINE_BYTES')
    if len(program.data)!=240 or 'BhBitmapSharedHit' not in program.symbols or \
       'BhBitmapDifferent' not in program.symbols:
        raise ValueError('BC_BITMAP_BUILDER_OPCODE_LAYOUT')
    if any(sy[k]!=program.symbols[k] for k in ('BhBitmapSharedHit','BhBitmapDifferent',
                                              'BhBitmapMapLoop','BhBitmapBuilt')):
        raise ValueError('BC_BITMAP_LABEL_ADDRESS')
    oldrom=(BASE/'bor.sfc').read_bytes()
    if sha(BASE/'bor.sfc')!=bc.BASE_ROM_SHA256:
        raise ValueError('BC_ACCEPTED_ROM_CHANGED')
    oldsym=symbols(BASE/'publisher.sym')
    if (sy['BhCodeEnd']-oldsym['BhCodeEnd']!=35 or
            sy['NbCodeEnd']!=oldsym['NbCodeEnd'] or
            sy['SpCodeEnd']!=oldsym['SpCodeEnd'] or
            sy['BhBitmapBuild']!=oldsym['BhBitmapBuild'] or
            sy['BhCodeEnd']>=0x39c000):
        raise ValueError('BC_UNEXPECTED_ROM_LEASE_OR_RELOCATION')
    expected=bytearray(oldrom)
    a=offset(0x39B300);b=offset(sy['BhCodeEnd'])
    if any(oldrom[offset(oldsym['BhCodeEnd']):b]):
        raise ValueError('BC_EXTENSION_NOT_ZERO')
    expected[a:b]=rom[a:b]
    if expected!=rom:raise ValueError('BC_ROM_OUTSIDE_HELPER_CHANGED')
    evidence.update(bitmap_shared_cells=dict(extra_code_bytes=35,ram_added=0,rom_mask_table_unchanged=True,
         exact_opcode_df_present=True,original_allocator_and_restoration_unchanged=True,
         only_authorized_code=[0x39B300,sy['BhCodeEnd']]))
    return evidence


def observer(script,contract):
    ORIGINAL_OBSERVER(script,contract)
    sy=contract['native_symbols']
    def cb(name,expr):
        return (f"emu.addMemoryCallback(function() {expr} end,emu.callbackType.exec,"
                f"{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n")
    s="local bcLive=false;local bcRows=0;local bcFast=0;local bcSlow=0\n"
    s+=cb('BhBitmapLeaseBegin',"if bcLive then nbLog('FAULT','BC_NESTED')end;bcLive=true;bcRows=0;bcFast=0;bcSlow=0;nbLog('BC_START',nbTxn)")
    s+=cb('BhBitmapMapLoop',"if not bcLive then nbLog('FAULT','BC_LOOP_OUTSIDE')end;bcRows=bcRows+1")
    s+=cb('BhBitmapSharedHit',"if not bcLive then nbLog('FAULT','BC_FAST_OUTSIDE')end;bcFast=bcFast+1")
    s+=cb('BhBitmapDifferent',"if not bcLive then nbLog('FAULT','BC_SLOW_OUTSIDE')end;bcSlow=bcSlow+1")
    s+=cb('BhBitmapBuilt',"if not bcLive or bcRows~=1024 then nbLog('FAULT','BC_INCOMPLETE')end;nbLog('BC_DONE',nbTxn..'|'..bcFast..'|'..bcSlow..'|'..bcRows);bcLive=false")
    for end in ('BhPrepareBad','BhPrepareOK'):
        s+=cb(end,"if bcLive then nbLog('FAULT','BC_LEASE_NOT_CLOSED')end")
    with script.open('a') as stream:stream.write(s)


def shared_evidence(folder):
    # Compare actual branch visits to raw native committed/pending maps logged
    # by the accepted bitmap lifetime observer. Never infer counts from epochs.
    events=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'callback_owner.lua:' in line:raise ValueError('BC_LUA_OBSERVER_ERROR:'+line)
        if 'NB_' not in line:continue
        fields=line[line.index('NB_'):].split('|')
        kind=fields[0][3:]
        if kind=='FAULT':raise ValueError('BC_NATIVE_FAULT:'+'|'.join(fields[4:]))
        events.append(dict(kind=kind,clock=int(fields[1]),data=fields[4:]))
    begins=[e for e in events if e['kind']=='BITMAP_BEGIN']
    starts=[e for e in events if e['kind']=='BC_START']
    done=[e for e in events if e['kind']=='BC_DONE']
    if len(begins)!=len(starts) or len(done)!=len(starts):
        raise ValueError('BC_MISSING_BRANCH_OR_LIFETIME_EVENTS')
    observations=[]
    for begin,start,end in zip(begins,starts,done):
        txn=int(start['data'][0]);count=len(bytes.fromhex(begin['data'][1]))//2
        if int(begin['data'][0])!=txn or int(end['data'][0])!=txn or count!=1024:
            raise ValueError('BC_BITMAP_TRACE_DOMAIN')
        def words(raw):
            b=bytes.fromhex(raw)
            return [int.from_bytes(b[i:i+2],'little') for i in range(0,len(b),2)]
        cm,pm=words(begin['data'][1]),words(begin['data'][2])
        if len(cm)!=1024 or len(pm)!=1024:raise ValueError('BC_BITMAP_MAP_LENGTH')
        expected_fast=sum(h<596 and h==p for h,p in zip(cm,pm))
        expected_slow=sum(h<596 and h!=p for h,p in zip(cm,pm))
        fast,slow,rows=map(int,end['data'][1:4])
        if (fast,slow,rows)!=(expected_fast,expected_slow,1024):
            raise ValueError('BC_NATIVE_PATH_COUNTS_NOT_MAP_DERIVED')
        clocks=end['clock']-start['clock']
        if clocks<=0:raise ValueError('BC_CLOCK_BOUNDARY')
        observations.append(dict(transaction=txn,shared_fast_cells=fast,different_home_cells=slow,
            rows=rows,bitmap_build_clocks=clocks,bitmap_build_ms=clocks/CLOCKS_PER_MS))
    return observations


def certify(folder):
    with patch.object(prior,'audit_rom',audit_rom):
        result=ORIGINAL_CERTIFY(folder)
    result['shared_cells']=shared_evidence(folder)
    result['classification']='BITMAP_SHARED_CELLS_NATIVE_CORRECT'
    (folder/'shared-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def build(folder,base=BASE,dotnet=None,poppy=None):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    if folder.exists():raise ValueError('BC_USE_FRESH_OUTPUT_FOLDER')
    base=Path(base)
    if sha(base/'bor.sfc')!=bc.BASE_ROM_SHA256:
        raise ValueError('BC_PINNED_SINGLE_PASS_BASE_ROM')
    native=folder/'native';native.mkdir(parents=True)
    current=(base/'publisher.pasm').read_text().splitlines()
    candidate=bc.transform(current)
    (native/'publisher.pasm').write_text('\n'.join(candidate)+'\n')
    dotnet=dotnet or Path(os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'))
    poppy=poppy or Path(os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'))
    command=[str(dotnet),str(poppy),str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),
             '--symbols',str(native/'publisher.sym'),'--no-pansy']
    proc=subprocess.run(command,capture_output=True,text=True)
    (native/'publisher-build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise RuntimeError('BC_POPPY_ASSEMBLY_FAILED; read publisher-build.log')
    oldsy=symbols(base/'publisher.sym');sy=symbols(native/'publisher.sym')
    if any(sy[x]!=oldsy[x] for x in ('NbCodeEnd','SpCodeEnd','BhBitmapBuild')):
        raise ValueError('BC_RELOCATION_OUTSIDE_BITMAP_HELPER')
    if sy['BhCodeEnd']-oldsy['BhCodeEnd']!=35 or sy['BhCodeEnd']>=0x39C000:
        raise ValueError('BC_HELPER_SIZE')
    oldrom=(base/'bor.sfc').read_bytes()
    compiled=(native/'publisher.bin').read_bytes()
    from_at=offset(0x39B300);to_at=offset(sy['BhCodeEnd'])
    if any(oldrom[offset(oldsy['BhCodeEnd']):to_at]):
        raise ValueError('BC_CODE_EXTENSION_LEASE_NOT_ZERO')
    rom=bytearray(oldrom)
    rom[from_at:to_at]=compiled[from_at:to_at]
    audit=audit_rom(rom,native)
    (native/'bor.sfc').write_bytes(rom)
    contract=copy.deepcopy(json.loads((base.parent/'contract.json').read_text()))
    contract['native_symbols'].update(sy)
    contract.update(bitmap_shared_cells=True,bitmap_shared_audit=audit,
                    bitmap_shared_base_sha256=bc.BASE_ROM_SHA256)
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    (native/'callback_owner.lua').write_text(prior.bootstrap_prefix((base/'callback_owner.lua').read_text()))
    os.link((base/'bor.msu').resolve(),native/'bor.msu')
    return contract


def run_case(folder,case):
    # Keep the accepted eight native cases/fault injection and exact certification.
    with patch.object(prior,'observer',observer),patch.object(prior,'audit_rom',audit_rom),\
         patch.object(prior,'certify',certify):
        result=ORIGINAL_RUN(folder,case)
    if case=='right':
        result['shared_cells']=shared_evidence(folder)
        if result['shared_cells']:raise ValueError('BC_RIGHT_UNEXPECTED_BITMAP')
        (folder/'shared-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def ensure(ok,reason):
    if not ok:raise ValueError('BC_NATIVE_ACCEPTANCE:'+reason)


def inherited_fingerprints(baseline):
    entries=baseline['handoff']['inherited_dirty_files_preserved']
    ensure(len(entries)==29,'29 inherited fingerprints required')
    return entries


def collect_suite(root,baseline_root=BASELINE):
    old=prior.legacy()
    baseline=json.loads((Path('docs/receipts/byor-motu-restore-single-pass.json')).read_text())
    cases={}
    for case in old.module.CASES:
        folder=root/case
        result=json.loads((folder/'shared-result.json').read_text())
        # Recompute native branch counts and fail on any unfiltered callback error.
        ensure(result['shared_cells']==shared_evidence(folder),case+':shared branch trace drift')
        ensure(result['pixel_mismatches']==result['resource_faults']==result['unsafe_ppu_operations']==0,
               case+':pixel/resource fault')
        ref=baseline['cases'][case]
        if case=='right':
            ensure(not result['shared_cells'], 'RIGHT used bitmap')
            ensure(result['transition_fields']<=ref['transition_fields'],'RIGHT gained a field')
        else:
            ensure(result['source_pixel_difference']==1816,case+':source pixels')
            ensure(len(result['shared_cells'])==1,case+':bitmap invocation')
            ensure(result['shared_cells'][0]['bitmap_build_clocks'] < 1407502,case+':bitmap builder not faster')
        for suf in ('world','committed','pending','refs','cgram'):
            for file in (folder/'native').glob('*-'+suf+'.bin'):
                prior_file=baseline_root/case/'native'/file.name
                ensure(prior_file.exists() and prior_file.read_bytes()==file.read_bytes(),
                       case+':native source or map drift '+file.name)
        cases[case]=result
    up=cases['success']; old=baseline['cases']['success']
    initial,second=up['transactions'][:2];old_first,old_second=old['transactions'][:2]
    ensure(initial['fields']<=old_first['fields'] and
           initial['master_clocks']<=1.01*old_first['master_clocks'],'epoch 2 regression')
    ensure(second['fields']<=old_second['fields'] and
           second['master_clocks']<old_second['master_clocks'],'epoch 3 not faster')
    pools=up['pools']['3'];priorp=old['pools']['3']
    ensure(all(pools[k]==priorp[k] for k in ('homes','original_invalid','original_valid','policy','limit','need')),'inventory/reservations')
    transfer=next(x for x in up['transfers'] if x['transaction']==3)
    ensure((transfer['chr_pairs'],transfer['chr_bytes'],transfer['map_bytes'],transfer['descriptors'])==(105,8400,4096,212),'transfer workload')
    ensure(sum(bool(int.from_bytes((root/'success/native/after-second-refs.bin').read_bytes()[j:j+2],'little')&0x3fff)
               for j in range(0,1536,2))==639,'639 referenced slots')
    ensure(any(x['transaction']==4 and x['home']==204 and x['destination']==634 and not x['rollback']
               for x in cases['valid']['backdrop_restorations']),'home 204 later restoration')
    for case in ('early','ready','partial','stale'):
        ensure(cases[case]['validity_clear_events'],case+':rollback fences')
    ensure(next(x for x in cases['insufficient']['transfers'] if x['transaction']==3)['descriptors']==0,'insufficient DMA')
    previous_dirty=inherited_fingerprints(baseline)
    for entry in previous_dirty:
        ensure(sha(entry['path'])==entry['sha256'],'inherited dirty '+entry['path'])
    ensure(not Path('SNES-BOR-Engine-Prompt.md').exists(),'unrelated unstaged deletion')
    report=dict(classification='BYOR_MOTU_BITMAP_SHARED_CELLS_PASS',
      starting_commit=bc.BASE_COMMIT,verified_fields=sum(v['observed_fields'] for v in cases.values()),
      verified_pixels=sum(v['verified_pixels'] for v in cases.values()),
      pixel_mismatches=0,resource_faults=0,unsafe_ppu_operations=0,
      cases=cases,fast_path_counts=up['shared_cells'],
      code_bytes_added=35,persistent_ram_bytes_added=0,
      nonclaims=['30 FPS','200-Hz','SA-1','audio','HUD','combat','Demo readiness'])
    (root/'bitmap-shared-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['classification'],report['verified_fields'],report['verified_pixels'])
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--base-native',type=Path,default=BASE)
    p.add_argument('--baseline-root',type=Path,default=BASELINE)
    p.add_argument('--dotnet',type=Path,default=Path(os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe')))
    p.add_argument('--poppy',type=Path,default=Path(os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll')))
    p.add_argument('--suite',action='store_true')
    p.add_argument('--collect-suite',action='store_true')
    p.add_argument('--build-only',action='store_true')
    p.add_argument('--case',choices=('success','valid','early','ready','partial','stale','insufficient','right'),default='success')
    a=p.parse_args();out=a.output.resolve()
    if a.collect_suite:
        if a.suite or a.build_only:raise ValueError('BC_USE_COLLECT_SUITE_ALONE')
        collect_suite(out,a.baseline_root);return
    if a.suite:
        if out.exists():raise ValueError('BC_SUITE_OUTPUT_EXISTS')
        for case in prior.legacy().module.CASES:
            child=out/case
            print('BITMAP SHARED CASE',case,flush=True)
            build(child,a.base_native,a.dotnet,a.poppy)
            if not a.build_only:run_case(child,case)
        if not a.build_only:collect_suite(out,a.baseline_root)
    else:
        build(out,a.base_native,a.dotnet,a.poppy)
        if not a.build_only:run_case(out,a.case)

if __name__=='__main__':main()
