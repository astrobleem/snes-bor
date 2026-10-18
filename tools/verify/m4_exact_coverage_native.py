"""Local bounded exact-coverage experiment against the accepted Q8 fixture."""
from __future__ import annotations
import argparse,collections,json,os,subprocess
from pathlib import Path
from unittest.mock import patch
import m4_eight_pair_native as q8
import exact_coverage as ec

BASE=Path('out/byor-motu-eight-direct-v8/success/native')
BASELINE=Path('out/byor-motu-eight-direct-v8')
BASE_SHA='4a696c9bc6d94e153188c6226744b3daf8ccfdb5301e943bf280f2697de129e9'
Q8_OBSERVER=q8.observer
Q8_AUDIT=q8.audit_rom
PROFILE_BASE=Path('out/byor-motu-exact-coverage-profile-v4/success')
BASE_PROFILE_SHA256='d9f35a7b5e5597a543bdcaf178f874012297f4a1c74f462d3941b6f2186cad5e'
CHECKPOINT_SUFFIXES=('world','committed','pending','refs','cgram','vram')
MS=21477.270


def require(ok,code):
    if not ok:raise ValueError('EXACT_COVERAGE:'+code)


def coverage_return(native,sy):
    from m4_rect_map_audit import statements
    lines=(native/'publisher.pasm').read_text().splitlines()
    lo=lines.index('OnlineCoverage:');hi=next(i for i in range(lo+1,len(lines)) if lines[i].startswith('.org '))
    stm=statements([' iny' if x.strip()=='dey' else x for x in lines],sy)
    returns=[pc for i,(pc,n,text) in stm.items() if lo<i<hi and text=='rts']
    require(len(returns)==1,'ORIGINAL_COVERAGE_RETURN_DRIFT')
    return returns[0]


def callsite(lines,sy):
    from m4_rect_map_audit import statements
    stm=statements([' iny' if x.strip()=='dey' else x for x in lines],sy)
    lo=lines.index('NbMarkTest:');hi=lines.index('NbUseSourcePresence:')
    calls=[pc for i,(pc,n,s) in stm.items()
           if lo<i<hi and s in ('jsr OnlineCoverage','jsr EcCoverage')]
    require(len(calls)==1,'BOOLEAN_CALLSITE_DRIFT')
    return calls[0]


def audit_rom(rom,native):
    """Independent helper bytes; only the pinned JSR operand and zero gap vary."""
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    from m4_rect_map_audit import statements
    require(q8.sha(BASE/'bor.sfc')==BASE_SHA,'Q8_CONTROL_HASH')
    original=(BASE/'bor.sfc').read_bytes()
    inherited=Q8_AUDIT(original,BASE)
    old=(BASE/'publisher.pasm').read_text().splitlines()
    lines=(native/'publisher.pasm').read_text().splitlines()
    require(lines==ec.transform(old),'EXACT_SOURCE_TRANSFORM')
    sy=symbols(native/'publisher.sym');oldsy=symbols(BASE/'publisher.sym')
    require(all(sy.get(k)==v for k,v in oldsy.items()),'EXISTING_SYMBOL_MOVED')
    require((sy['EcCoverage'],sy['EcCoverageRow'],sy['EcHit'],sy['EcCodeEnd'])==
            (ec.CODE_START,ec.CODE_START+8,ec.CODE_START+30,ec.CODE_START+31),
            'HELPER_LAYOUT')
    require(oldsy['NbCodeEnd']<=ec.CODE_START<sy['EcCodeEnd']<ec.CODE_LIMIT,
            'HELPER_REGION_COLLISION')
    start,end=offset(ec.CODE_START),offset(sy['EcCodeEnd'])
    require(not any(original[start:end]),'HELPER_LEASE_NOT_ZERO')
    compiled=(native/'publisher.bin').read_bytes()
    def jsr(name):return bytes((0x20,sy[name]&255,(sy[name]>>8)&255))
    literal=(jsr('OnlineRowPointers')+bytes.fromhex('a900008558')+
             jsr('OnlineRowMask')+bytes.fromhex('e658a532d00d')+
             jsr('OnlineStepRow')+bytes.fromhex('a558c9080090eda9000060'))
    require(compiled[start:end]==literal,'INDEPENDENT_HELPER_OPCODES')
    pc=callsite(old,oldsy);at=offset(pc)
    require(original[at:at+3]==jsr('OnlineCoverage'),'ORIGINAL_CALL_BYTES')
    require(compiled[at:at+3]==jsr('EcCoverage'),'NEW_CALL_BYTES')
    expected=bytearray(original)
    expected[at+1:at+3]=jsr('EcCoverage')[1:]
    expected[start:end]=literal
    require(bytes(rom)==expected,'UNAUTHORIZED_ROM_BYTE')
    # Reassembled original instructions must also match, including every old
    # coverage/row/compositor/DMA routine and every original branch operand.
    for p,n,s in statements([' iny' if x.strip()=='dey' else x for x in old],oldsy).values():
        off=offset(p)
        require(compiled[off:off+n]==expected[off:off+n],
                'ORIGINAL_INSTRUCTION_CHANGED:'+hex(p)+':'+s)
    branches=audit_branches([' iny' if x.strip()=='dey' else x for x in lines],sy,compiled)
    inherited['exact_coverage']=dict(status='PASS',callsite=pc,
        accepted_q8_rom_sha256=BASE_SHA,
        original_target=sy['OnlineCoverage'],new_target=sy['EcCoverage'],
        code_start=ec.CODE_START,code_end=sy['EcCodeEnd'],code_bytes=len(literal),
        branch_sites=branches,all_original_symbols_identical=True,
        only_original_rom_changes='Two JSR operand bytes; 31 zero-gap bytes',
        original_row_masks_and_full_coverage_identical=True,
        no_new_memory_or_queue_capacity=True)
    return inherited


def build(folder,disabled=False):
    """Fresh Q8 regeneration first; then the separately audited EC overlay."""
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract=q8.build(folder)
    native=folder/'native'
    require(q8.sha(native/'bor.sfc')==BASE_SHA,'Q8_REBUILD_IDENTITY')
    if disabled:return contract
    lines=(native/'publisher.pasm').read_text().splitlines()
    (native/'publisher.pasm').write_text('\n'.join(ec.transform(lines))+'\n')
    command=[os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'),
             os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
             str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),
             '--symbols',str(native/'publisher.sym'),'--no-pansy']
    result=subprocess.run(command,capture_output=True,text=True)
    (native/'exact-coverage-build.log').write_text(result.stdout+result.stderr)
    require(result.returncode==0,'POPPY_ASSEMBLY')
    sy=symbols(native/'publisher.sym');pc=callsite(lines,contract['native_symbols'])
    rom=bytearray((native/'bor.sfc').read_bytes());compiled=(native/'publisher.bin').read_bytes()
    at=offset(pc);start=offset(ec.CODE_START);end=offset(sy['EcCodeEnd'])
    rom[at+1:at+3]=compiled[at+1:at+3];rom[start:end]=compiled[start:end]
    audit=audit_rom(rom,native)
    (native/'bor.sfc').write_bytes(rom)
    contract['native_symbols'].update(sy)
    contract.update(exact_coverage=True,eight_pair_audit=audit)
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    return contract


def observer(script,contract):
    Q8_OBSERVER(script,contract)
    sy=contract['native_symbols'];ret=coverage_return(script.parent,sy)
    helper=sy['OnlineCoverage']
    if 'EcCoverage' in sy:helper=sy['EcCoverage'];ret=sy['EcHit']
    with script.open('a') as f:
        f.write('local ecStart=nil;local ecIndex=nil;local ecMark=nil\n')
        def cb(at,body):
            f.write(f'emu.addMemoryCallback(function() {body} end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb(sy['NbBeginRetry'],"if nbWord(0x42d674)==1 then if ecMark then nbLog('FAULT','EC_MARK_NESTED')end;ecMark=emu.getState()['masterClock'];nbLog('EC_MARK_BEGIN',nbTxn)end")
        cb(sy['NbRestorePlanStart'],"if ecMark then nbLog('EC_MARK_END',nbTxn..'|'..(emu.getState()['masterClock']-ecMark));ecMark=nil end")
        cb(helper,"if nbTxn>=0 and nbWord(0x42d674)==1 and nbWord(0x42d600)==1 then if ecStart then nbLog('FAULT','EC_COVER_NESTED')end;ecStart=emu.getState()['masterClock'];ecIndex=nbWord(0x3418)end")
        cb(ret,"if ecStart then local s=emu.getState();nbLog('EC_COVER',nbTxn..'|'..ecIndex..'|'..(s['masterClock']-ecStart)..'|'..s['cpu.a']..'|'..nbWord(0x3458));ecStart=nil end")
        for name in ('NbAllPairsReady','NbAbort','NbVisible'):
            cb(sy[name],"if ecStart or ecMark then nbLog('FAULT','EC_PROFILE_UNFINISHED')end")


def profile(folder,required=True):
    events=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'callback_owner.lua:' in line:raise ValueError('EC_LUA_ERROR:'+line)
        if 'NB_' not in line:continue
        p=line[line.index('NB_'):].split('|')
        if p[0]=='NB_FAULT':raise ValueError('EC_NATIVE_FAULT:'+'|'.join(p[4:]))
        events.append(dict(kind=p[0][3:],clock=int(p[1]),frame=int(p[2]),data=p[4:]))
    calls=collections.defaultdict(list);marks=collections.defaultdict(list)
    for e in events:
        if e['kind']=='EC_COVER':
            txn,tile,clocks,value,rows=map(int,e['data'])
            calls[txn].append(dict(tile=tile,clocks=clocks,value=value,covered=bool(value&65535),row_counter=rows))
        if e['kind']=='EC_MARK_END':
            txn,clocks=map(int,e['data']);marks[txn].append(clocks)
    if required:require(calls and calls[3] and len(marks[3])==1,'MISSING_EXACT_PASS')
    require(all(len(marks[txn])==1 for txn in calls),'EXACT_MARK_COUNT')
    result=dict(classification='EXACT_COVERAGE_PROFILE_PASS',rom_sha256=q8.sha(folder/'native/bor.sfc'),
                transactions={str(txn):dict(calls=len(rows),covered=sum(x['covered'] for x in rows),
                    helper_clocks=sum(x['clocks'] for x in rows),helper_ms=sum(x['clocks'] for x in rows)/MS,
                    mark_clocks=marks[txn],mark_ms=[x/MS for x in marks[txn]],verdicts=rows)
                    for txn,rows in calls.items()},
                boundaries='Coverage entry to RTS fetch; caller JSR/final RTS excluded. Mark is exact NbBeginRetry entry to NbRestorePlanStart. Elapsed spans include bus and interrupt time.')
    (folder/'exact-coverage-profile.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def compare_profiles(current,baseline):
    """Cell order and exact boolean verdicts must equal unchanged Q8."""
    require(set(current['transactions'])==set(baseline['transactions']),'COVERAGE_TRANSACTIONS')
    changes={}
    for txn,old in baseline['transactions'].items():
        new=current['transactions'][txn]
        require([(x['tile'],x['covered']) for x in new['verdicts']]==
                [(x['tile'],x['covered']) for x in old['verdicts']],
                'EXACT_CELL_VERDICT_DRIFT:'+txn)
        require(all(1<=x['row_counter']<=8 for x in new['verdicts']),
                'ROW_VISIT_DOMAIN:'+txn)
        changes[txn]=dict(calls=new['calls'],covered=new['covered'],
            before_helper_clocks=old['helper_clocks'],after_helper_clocks=new['helper_clocks'],
            before_mark_clocks=old['mark_clocks'],after_mark_clocks=new['mark_clocks'],
            rows_visited=sum(x['row_counter'] for x in new['verdicts']),
            baseline_rows_visited=sum(x['row_counter'] for x in old['verdicts']))
    return changes


def expected_checkpoints(case):
    """Pinned Q8 checkpoint names; neither candidate nor control defines them."""
    require(case in q8.CASES,'UNKNOWN_CHECKPOINT_CASE:'+case)
    if case=='right':
        worlds=states={'cold','deferred','moved','left','noop'}
        vram=states|{'initial','handoff'}
    else:
        worlds={'cold','deferred','moved','newer'}
        states={'cold','deferred','moved','before-second','after-second'}
        if case=='valid':
            worlds.add('restoration');states.add('after-restoration')
        vram=states|{'initial'}
    return {stem+'-'+suffix+'.bin' for suffix in CHECKPOINT_SUFFIXES
            for stem in (worlds if suffix=='world' else vram if suffix=='vram' else states)}


def require_checkpoint_inventory(native,case):
    expected=expected_checkpoints(case)
    found=[p for suffix in CHECKPOINT_SUFFIXES for p in native.glob('*-'+suffix+'.bin')]
    require(all(p.is_file() for p in found),case+':CHECKPOINT_NOT_FILE')
    actual={p.name for p in found}
    require(actual==expected,case+':CHECKPOINT_INVENTORY:missing='+
            ','.join(sorted(expected-actual))+';extra='+','.join(sorted(actual-expected)))
    return sorted(expected)


def load_baseline_profile(profile_base):
    profile_path=profile_base/'exact-coverage-profile.json'
    require(profile_path.is_file(),'BASELINE_PROFILE_MISSING')
    require(q8.sha(profile_path)==BASE_PROFILE_SHA256,'BASELINE_PROFILE_DIGEST')
    baseline=json.loads(profile_path.read_text())
    require(baseline['rom_sha256']==BASE_SHA and
            q8.sha(profile_base/'native/bor.sfc')==BASE_SHA,'PROFILE_CONTROL_HASH')
    return baseline


def collect_suite(root,profile_base=PROFILE_BASE):
    # Keep all eight original independent certifiers and every Q8 aggregate
    # gate. This wrapper adds comparison against Q8, beyond its Q7 controls.
    control_profile=load_baseline_profile(profile_base)
    inventories={case:dict(candidate=require_checkpoint_inventory(root/case/'native',case),
                           q8=require_checkpoint_inventory(BASELINE/case/'native',case))
                 for case in q8.CASES}
    with patch.object(q8,'audit_rom',audit_rom):report=q8.collect_suite(root)
    baseline=json.loads(Path('docs/receipts/byor-motu-eight-pair-direct.json').read_text())
    for case in q8.CASES:
        child=root/case;oldroot=BASELINE/case
        require(q8.sha(child/'native/bor.sfc')==q8.sha(root/'success/native/bor.sfc'),
                case+':CANDIDATE_ROM_DRIFT')
        if case!='right':
            q8.verify_pool_identity(report['cases'][case]['pools'],
                                    baseline['cases'][case]['pools'],case+':Q8')
        for suffix in ('world','committed','pending','refs','cgram'):
            for name in inventories[case]['candidate']:
                if not name.endswith('-'+suffix+'.bin'):continue
                file=child/'native'/name
                previous=oldroot/'native'/file.name
                require(previous.exists() and previous.read_bytes()==file.read_bytes(),
                        case+':Q8_STATE_DRIFT:'+file.name)
        for name in inventories[case]['candidate']:
            if not name.endswith('-vram.bin'):continue
            file=child/'native'/name
            if file.name in ('initial-vram.bin','handoff-vram.bin'):continue
            previous=oldroot/'native'/file.name
            require(previous.exists(),case+':MISSING_Q8_VRAM')
            a=file.read_bytes();b=previous.read_bytes()
            require(len(a)==len(b)==65536 and a[61440:]==b[61440:],case+':Q8_MAP_DRIFT')
            slots={int.from_bytes(a[i:i+2],'little')&0x3fff for i in range(61440,65536,2)}
            require(all(a[64*k:64*(k+1)]==b[64*k:64*(k+1)] and
                        a[49152+16*k:49152+16*(k+1)]==b[49152+16*k:49152+16*(k+1)]
                        for k in slots),case+':Q8_REFERENCED_PIXELS_DRIFT')
        profile(child,required=case=='success')
    new=report['epoch2'];old=baseline['epoch2']
    require(new['fields']<=old['fields'] and new['master_clocks']<=old['master_clocks'],
            'Q8_EPOCH2_REGRESSION')
    new=report['epoch3'];old=baseline['epoch3']
    require(new['fields']<=old['fields']-1 and new['master_clocks']<old['master_clocks'],
            'Q8_EPOCH3_ONE_FIELD_TARGET')
    require(report['cases']['right']['transition_fields']<=
            baseline['cases']['right']['transition_fields'],'Q8_RIGHT_REGRESSION')
    current=json.loads((root/'success/exact-coverage-profile.json').read_text())
    comparison=compare_profiles(current,control_profile)
    report.update(classification='BYOR_MOTU_EXACT_COVERAGE_PASS',
        baseline_q8_epoch2=baseline['epoch2'],baseline_q8_epoch3=baseline['epoch3'],
        exact_coverage=comparison,profile_baseline=str(profile_base),
        baseline_profile_sha256=BASE_PROFILE_SHA256,checkpoint_inventories=inventories,
        rom_sha256=q8.sha(root/'success/native/bor.sfc'),
        rom_audit=audit_rom((root/'success/native/bor.sfc').read_bytes(),root/'success/native'))
    (root/'exact-coverage-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--profile-only',action='store_true')
    p.add_argument('--suite',action='store_true')
    p.add_argument('--collect-suite',action='store_true')
    p.add_argument('--build-only',action='store_true')
    p.add_argument('--disabled',action='store_true')
    p.add_argument('--case',choices=q8.CASES,default='success')
    p.add_argument('--profile-baseline',type=Path,default=PROFILE_BASE)
    a=p.parse_args();folder=a.output.resolve()
    if a.collect_suite:
        measured=collect_suite(folder,a.profile_baseline)
        print(measured['classification'],measured['observed_fields'],measured['verified_rgb555_pixels'],flush=True)
        return
    require(not folder.exists(),'OUTPUT_MUST_BE_NEW')
    require(not(a.profile_only and (a.suite or a.build_only or a.disabled)),'PROFILE_OPTIONS')
    require(not(a.disabled and not a.build_only),'DISABLED_IS_BUILD_CONTROL')
    # Root owns capture inputs; each child stays absent until q8.build creates
    # it. This satisfies both fresh-directory contracts without weakening one.
    if not a.build_only:q8.configure_capture_runtime(folder)
    cases=q8.CASES if a.suite else (a.case,)
    for case in cases:
        child=folder/case
        print('EC NATIVE CASE',case,flush=True)
        if a.profile_only:
            q8.build(child)
            require(q8.sha(child/'native/bor.sfc')==BASE_SHA,'PROFILE_ROM_CHANGED')
            with patch.object(q8,'observer',observer):result=q8.run_case(child,case)
            expected=json.loads((BASELINE/case/'eight-result.json').read_text())
            require(result['transactions']==expected['transactions'],'PROFILE_TIMING_DRIFT')
            measured=profile(child)
            print(measured['classification'],json.dumps({k:{n:v for n,v in row.items() if n!='verdicts'} for k,row in measured['transactions'].items()}),flush=True)
        else:
            build(child,a.disabled)
            if not a.build_only:
                with patch.object(q8,'audit_rom',audit_rom),patch.object(q8,'observer',observer):
                    q8.run_case(child,case)
    if a.suite and not a.build_only:
        result=collect_suite(folder,a.profile_baseline)
        print(result['classification'],result['observed_fields'],result['verified_rgb555_pixels'],flush=True)


if __name__=='__main__':main()
