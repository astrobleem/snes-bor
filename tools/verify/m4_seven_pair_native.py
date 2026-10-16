"""Native Poppy/Mesen integration for a bounded seventh queued HIGH/LOW pair.

Starts from certified shared-cell ROM and only edits the A000 transaction.
The accepted eight native cases and independent 64KiB replay are reused with
candidate-specific stricter packet/queue ownership checks. This has NOT been
run on Windows Poppy/Mesen in the authoring environment.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import inspect
import textwrap
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import seven_pair_spill as q7
from m4_bitmap_shared_native import observer as ORIGINAL_SHARED_OBSERVER
from m4_nonblank_batch_native import certify as ORIGINAL_RIGHT_CERTIFIER

BASE = Path('out/byor-motu-bitmap-shared-v1/success/native')
BASELINE_ROOT = Path('out/byor-motu-bitmap-shared-v1')
REPO = 'astrobleem/snes-bor'
MS = 21477.270
CASES=('success','valid','early','ready','partial','stale','insufficient','right')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()



def helper_relocations(oldrom, compiled, oldsource, newsource, oldsy, sy):
    """Verify B000/B300 unchanged instructions; permit ONLY moved A000 operands.

    The B000 safe-point calls NbFreshVblank, and B300 rollback calls the
    preloader/flush routines. Assembler re-linking those two existing helper
    regions is mandatory when source assembly shifts A000 labels.
    """
    from m4_rect_map_audit import statements
    from m4_input_controller_native import offset
    old_statements=statements([' iny' if x.strip()=='dey' else x for x in oldsource],oldsy)
    new_statements=statements([' iny' if x.strip()=='dey' else x for x in newsource],sy)
    by_old={pc:(size,line) for pc,size,line in old_statements.values()}
    by_new={pc:(size,line) for pc,size,line in new_statements.values()}
    # No outside A000 entrypoint may retain an unpatched absolute reference to
    # a relocated queue label. B000/B300 are the only authorized helper fixups.
    for pc,(n,line) in by_old.items():
        op,_,arg=line.partition(' ')
        if arg not in oldsy or oldsy[arg]==sy.get(arg,oldsy[arg]):continue
        if not (0x39A000<=oldsy[arg]<0x39B000 and op in ('jsr','jmp','jsl','jml')):
            continue
        if (0x39A000<=pc<oldsy['NbCodeEnd'] or
            0x39B000<=pc<oldsy['SpCodeEnd'] or
            0x39B300<=pc<oldsy['BhCodeEnd']):
            continue
        raise ValueError('Q7_UNPATCHED_EXTERNAL_A000_CALLSITE:'+line)
    helpers=((0x39B000,oldsy['SpCodeEnd']),(0x39B300,oldsy['BhCodeEnd']))
    allowed=[];result=bytearray(oldrom)
    for lo,hi in helpers:
        if offset(hi)>len(compiled):
            raise ValueError('Q7_HELPER_COMPILED_OUTPUT_SHORT')
        for pc,(n,line) in by_old.items():
            if not lo<=pc<hi:continue
            if pc not in by_new or by_new[pc]!=(n,line) or pc+n>hi:
                raise ValueError('Q7_HELPER_INSTRUCTION_CHANGED:'+line)
            a=offset(pc);data=bytearray(oldrom[a:a+n])
            op,_,arg=line.partition(' ')
            if arg in oldsy and oldsy[arg]!=sy[arg]:
                if not 0x39A000<=oldsy[arg]<0x39B000 or not 0x39A000<=sy[arg]<0x39B000:
                    raise ValueError('Q7_UNEXPECTED_HELPER_TARGET:'+line)
                if op in ('jsr','jmp') and n==3:
                    data[1:]=(sy[arg]&0xFFFF).to_bytes(2,'little')
                elif op in ('jsl','jml') and n==4:
                    data[1:]=sy[arg].to_bytes(3,'little')
                else:
                    raise ValueError('Q7_HELPER_UNSUPPORTED_RELOCATION:'+line)
                allowed.append(dict(at=pc,instruction=line,old_target=oldsy[arg],new_target=sy[arg]))
            if bytes(compiled[a:a+n])!=bytes(data):
                raise ValueError('Q7_HELPER_UNEXPECTED_OPCODE:'+line)
            result[a:a+n]=data
        # Any aligned bytes not owned by instructions, such as padding, must
        # remain the accepted ROM's bytes; a hidden helper cannot slip in.
        start=offset(lo);end=offset(hi)
        if compiled[start:end]!=result[start:end]:
            raise ValueError('Q7_UNDECLARED_HELPER_BYTES')
    return result,allowed


def audit_rom(rom,native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    original=(BASE/'bor.sfc').read_bytes()
    if hashlib.sha256(original).hexdigest()!=q7.BASE_SHA256:
        raise ValueError('Q7_ACCEPTED_BASE_ROM_DRIFT')
    old=(BASE/'publisher.pasm').read_text().splitlines()
    wanted=q7.transform(old)
    actual=(native/'publisher.pasm').read_text().splitlines()
    if actual!=wanted:
        raise ValueError('Q7_SOURCE_OVERLAY_DRIFT')
    sy=symbols(native/'publisher.sym')
    oldsy=symbols(BASE/'publisher.sym')
    if not (sy['NbBegin']==oldsy['NbBegin']==0x39A000 and
            0x39A000<sy['NbCodeEnd']<0x39B000 and
            sy['SpCodeEnd']==oldsy['SpCodeEnd'] and
            sy['BhCodeEnd']==oldsy['BhCodeEnd'] and
            sy['Q7SourceFromIndex']<sy['Q7CodeEnd']==sy['NbCodeEnd']):
        raise ValueError('Q7_CODE_REGION_OR_HELPER_CHANGED')
    # The policy is inserted before actor production, so the preloader moves
    # within bank 39; only earlier code and other helper leases stay fixed.
    nonreloc=('NbBegin','NbRestorePlan','BhBitmapBuilt','BhCodeEnd','SpLatched','BhInitialize')
    if any(sy[name]!=oldsy[name] for name in nonreloc):
        raise ValueError('Q7_UNRELATED_SOURCE_MOVED')
    # The new policy inserts before actor planning, so preloader/queue labels
    # relocate *within* A000; B000/B300 helper entry points remain fixed.
    compiled=(native/'publisher.bin').read_bytes()
    verified=audit_branches([' iny' if x.strip()=='dey' else x for x in wanted],sy,compiled)
    a=offset(0x39a000)
    old_end=offset(oldsy['NbCodeEnd']);new_end=offset(sy['NbCodeEnd'])
    if new_end>old_end and any(original[old_end:new_end]):
        raise ValueError('Q7_CODE_EXTENSION_NOT_ZERO')
    expected,fixups=helper_relocations(original,compiled,old,wanted,oldsy,sy)
    expected[a:max(old_end,new_end)]=bytes(max(old_end,new_end)-a)
    expected[a:new_end]=compiled[a:new_end]
    if expected!=rom:
        raise ValueError('Q7_UNAUTHORIZED_ROM_MUTATION')
    # Metadata words have no direct claimant in the retained assembly. The
    # record range itself is indexed, so native guards prove its phase safety.
    for forbidden in ('$42D66E','$42D670','$0034B0'):
        if any(forbidden in line.upper() for line in old):
            raise ValueError('Q7_SCRATCH_WAS_ALREADY_CLAIMED:'+forbidden)
    return dict(status='PASS',verified_branches=verified,
      original_sha256=q7.BASE_SHA256,
      old_transaction_end=oldsy['NbCodeEnd'],new_transaction_end=sy['NbCodeEnd'],
      code_bytes_delta=sy['NbCodeEnd']-oldsy['NbCodeEnd'],
      source_pair_base=0x34b0,source_pair_bytes=80,
      maximum_live_restoration_records=12,
      queue_slot7_word=0x42d66e,dynamic_queue_limit_word=0x42d670,
      helper_operand_fixups=fixups,
      all_rom_bytes_outside_A000_B000_B300_authorized_ranges_unchanged=True)


def candidate_home_certifier(folder):
    """Reuse full home-borrow oracle, changing only two pinned queue limits.

    The old test allowed six source positions and six pairs per batch. We
    accept a seventh source ONLY at the exact extra 80-byte lease, and at most
    seven pairs. Independent Q7 Lua and Python checks below enforce record
    lifetime, dynamic max, source word, DMA payload, and timing margins.
    """
    import m4_home_borrow_evidence as home
    source=textwrap.dedent(inspect.getsource(home.certify))
    edits={
      "high['source'] not in range(0x3500,0x36e0,80)":
        "high['source'] not in (*range(0x3500,0x36e0,80),0x34b0)",
      'not 1<=count<=6': 'not 1<=count<=7',
    }
    for old,new in edits.items():
        if source.count(old)!=1:
            raise ValueError('Q7_INHERITED_HOME_CERTIFIER_DRIFT:'+old)
        source=source.replace(old,new,1)
    if source.count('def certify(')!=1:
        raise ValueError('Q7_CERTIFIER_FUNCTION_DRIFT')
    namespace=dict(home.__dict__,audit_rom=audit_rom)
    exec(source.replace('def certify(','def certify_q7(',1),namespace)
    return namespace['certify_q7'](folder)


def candidate_right_certifier(folder,contract,fields):
    """Retain RIGHT's independent replay oracle with the exact seventh source.

    Its own source-list/sequence checks are separate from the home oracle.
    Extend its READY fence predicate to cover the additional source as well.
    """
    import m4_nonblank_batch_native as right
    source=textwrap.dedent(inspect.getsource(ORIGINAL_RIGHT_CERTIFIER))
    edits={
      "h['source'] not in range(0x3500,0x36e0,80)":
        "h['source'] not in (*range(0x3500,0x36e0,80),0x34b0)",
      '(0x3500+80*i,0x3540+80*i)':
        '((0x34b0,0x34f0) if i==6 else (0x3500+80*i,0x3540+80*i))',
      "0x3500<=e['source']<0x36e0": "0x34b0<=e['source']<0x36e0",
    }
    for old,new in edits.items():
        if source.count(old)!=1:
            raise ValueError('Q7_INHERITED_RIGHT_CERTIFIER_DRIFT:'+old)
        source=source.replace(old,new,1)
    if source.count('def certify(')!=1:
        raise ValueError('Q7_RIGHT_CERTIFIER_FUNCTION_DRIFT')
    namespace=dict(right.__dict__,audit_rom=audit_rom)
    exec(source.replace('def certify(','def certify_right_q7(',1),namespace)
    return namespace['certify_right_q7'](folder,contract,fields)


def observer(script,contract):
    ORIGINAL_SHARED_OBSERVER(script,contract)
    sy=contract['native_symbols']
    def cb(name,body):
        return (f'emu.addMemoryCallback(function() {body} end,emu.callbackType.exec,'
                f'{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n')
    log=[]
    log.append('local q7Live=false;local q7StageWrites=0;local q7Source7=0\n')
    log.append(cb('Q7PolicyDone',
      "local records=nbWord(0x42d606);local mode=nbWord(0x42d602);local cap=nbWord(0x42d670);"
      "if cap~=(records<=12 and mode~=2 and 7 or 6) then nbLog('FAULT','Q7_POLICY_INVALID')end;"
      "if nbWord(0x42d660)~=0 or nbWord(0x42d608)~=0 then nbLog('FAULT','Q7_POLICY_QUEUE_LIVE')end;"
      "q7Live=true;nbLog('Q7_POLICY',nbTxn..'|'..records..'|'..mode..'|'..cap)"))
    log.append(cb('Q7SpillSource',
      "if not q7Live or nbWord(0x42d670)~=7 or nbWord(0x42d606)>12 or nbWord(0x3470)~=6 "
      "then nbLog('FAULT','Q7_SOURCE_INDEX_INVALID')end;"
      "q7Source7=q7Source7+1;nbLog('Q7_SOURCE7',nbTxn..'|'..q7Source7)"))
    for end in ('NbVisible','BhRollbackFinished','BhRollbackEmpty'):
        log.append(cb(end,"q7Live=false"))
    for cpu in ('snes','sa1'):
        # Original restoration-record and queue audits remain active. This
        # additional trap checks only the seventh payload's 80-byte region.
        log.append("emu.addMemoryCallback(function(a,v)if q7Live then local s=emu.getState();"
          "local pc=s['cpu.pc']+65536*s['cpu.k'];"
          f"if '{cpu}'~='snes' or pc<{sy['NbQueueSpace']} or pc>={sy['NbFlushQueue']} "
          "or nbWord(0x42d606)>12 or nbWord(0x42d670)~=7 "
          "or nbWord(0x42d660)~=6 then nbLog('FAULT','Q7_EXTRA_IRAM_WRITE_OWNER:'..a..'|'..pc) "
          "else q7StageWrites=q7StageWrites+1 end end end,"
          f"emu.callbackType.write,0x4b0,0x4ff,emu.cpuType.{cpu},emu.memType.sa1InternalRam)\n")
    log.append(cb('Q7PolicyBegin',"q7StageWrites=0;q7Source7=0"))
    with script.open('a') as f:
        f.write(''.join(log))


def packet_evidence(folder):
    native=Path(folder)/'native'
    policies=[];seventh=[];packets=[];fails=[]
    for line in (native/'mesen.log').read_text(errors='replace').splitlines():
        if 'callback_owner.lua:' in line:
            raise ValueError('Q7_LUA_OBSERVER_ERROR:'+line)
        if 'NB_' not in line:continue
        parts=line[line.index('NB_'):].split('|')
        kind=parts[0][3:]
        if kind=='FAULT':fails.append(parts[4:]);continue
        if kind=='Q7_POLICY':policies.append(tuple(map(int,parts[4:8])))
        if kind=='Q7_SOURCE7':seventh.append((int(parts[4]),int(parts[5])))
        if kind=='PACKET':
            txn,target,word,source,size=map(int,parts[4:9])
            packets.append(dict(txn=txn,target=target,word=word,source=source,size=size))
    if fails:raise ValueError('Q7_NATIVE_SAFETY:'+str(fails[:3]))
    allowed={0x3500+i*80 for i in range(6)}|{0x34b0}
    seen=[]
    for i,p in enumerate(packets):
        if p['source']!=0x34b0:continue
        if (p['source'] not in allowed or p['size']!=64 or p['target']!=0x18 or
             i+1>=len(packets) or packets[i+1]['source']!=0x34f0 or
             packets[i+1]['size']!=16 or packets[i+1]['txn']!=p['txn'] or
             packets[i+1]['word']!=0x6000+p['word']//4):
            raise ValueError('Q7_SEVENTH_HIGH_LOW_DESCRIPTOR')
        seen.append(p['txn'])
    policy_by_txn={}
    for txn,count,mode,limit in policies:
        if limit!=q7.queue_limit(count,mode):raise ValueError('Q7_RUNTIME_POLICY_MISMATCH')
        policy_by_txn.setdefault(txn,[]).append((count,mode,limit))
    for txn in seen:
        if not any(limit==7 and records<=12 for records,_,limit in policy_by_txn.get(txn,[])):
            raise ValueError('Q7_DMA_WITHOUT_SEVEN_CAPACITY')
    for txn,n in seventh:
        if n<1:raise ValueError('Q7_INDEX_COUNTER_DOMAIN')
    # Logs observe seventh source resolution twice (stage and drain), except
    # a fault abort that discards an unflushed staged seventh payload.
    if len(seventh)<len(seen):raise ValueError('Q7_MISSING_SEVENTH_SOURCE_OBSERVATION')
    return dict(policy=policies,seventh_source_calls=seventh,
                seventh_dma_high_pairs=len(seen),seventh_dma_transactions=seen)


def presentation_windows(folder):
    """Measure complete batches/maps and independently check exact queue order."""
    events=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'callback_owner.lua:' in line:raise ValueError('Q7_LUA_OBSERVER_ERROR:'+line)
        if 'NB_' not in line:continue
        p=line[line.index('NB_'):].split('|')
        if p[0]=='NB_FAULT':raise ValueError('Q7_NATIVE_SAFETY:'+'|'.join(p[4:]))
        events.append(dict(kind=p[0][3:],clock=int(p[1]),data=p[4:]))
    def window(clock):
        begin=max(e['clock'] for e in events if e['kind']=='VBLANK_START' and e['clock']<=clock)
        end=min(e['clock'] for e in events if e['kind']=='VBLANK_END' and e['clock']>begin)
        ensure(clock<end,'active-display transfer or completion')
        return begin,end
    packets=[dict(clock=e['clock'],txn=int(e['data'][0]),target=int(e['data'][1]),
        word=int(e['data'][2]),source=int(e['data'][3]),size=int(e['data'][4]))
        for e in events if e['kind']=='PACKET']
    batches=[]
    for entry in events:
        if entry['kind']!='BATCH' or entry['data'][0]!='NbQueueHasPending':continue
        txn,count=map(int,entry['data'][1:3])
        finish=next(e for e in events if e['kind']=='BATCH' and
            e['data'][0]=='NbQueueDrainDone' and e['clock']>entry['clock'])
        policy=max((e for e in events if e['kind']=='Q7_POLICY' and
            int(e['data'][0])==txn and e['clock']<=entry['clock']),key=lambda e:e['clock'])
        _,records,mode,limit=map(int,policy['data'])
        ensure(limit==q7.queue_limit(records,mode) and 1<=count<=limit,'batch dynamic capacity')
        ps=[p for p in packets if p['txn']==txn and entry['clock']<p['clock']<finish['clock']]
        ensure(len(ps)==2*count,'batch packet count')
        for i,(high,low) in enumerate(zip(ps[::2],ps[1::2],strict=True)):
            source=q7.queue_address(i,records,mode)
            ensure((high['source'],low['source'],high['size'],low['size'],high['target'],low['target'])==
                   (source,source+64,64,16,0x18,0x18),'exact paired source sequence')
            ensure(low['word']==0x6000+high['word']//4,'paired physical destination')
        begin,end=window(ps[0]['clock'])
        ensure(finish['clock']<end and end-finish['clock']>=10000,'complete batch 10000-clock margin')
        batches.append(dict(transaction=txn,pairs=count,first_dma_clock=ps[0]['clock'],
            complete_clock=finish['clock'],vblank_start=begin,vblank_end=end,
            duration_clocks=finish['clock']-ps[0]['clock'],margin_clocks=end-finish['clock']))
    maps=[]
    for complete in events:
        if complete['kind']!='PHASE' or complete['data'][0]!='NbMapsComplete':continue
        txn=int(complete['data'][1])
        start=max(e['clock'] for e in events if e['kind']=='PHASE' and
            e['data'][:2]==['NbMapCommit',str(txn)] and e['clock']<complete['clock'])
        begin,end=window(start)
        ensure(complete['clock']<end and end-complete['clock']>=10000,'map commit 10000-clock margin')
        maps.append(dict(transaction=txn,start_clock=start,complete_clock=complete['clock'],
            duration_clocks=complete['clock']-start,vblank_start=begin,vblank_end=end,
            margin_clocks=end-complete['clock']))
    seventh=[]
    for i,high in enumerate(packets):
        if high['source']!=0x34b0:continue
        low=packets[i+1]
        def fence(p):
            return min(e['clock'] for e in events if e['kind']=='DONE' and e['clock']>p['clock']
                and list(map(int,e['data'][:3]))==[p['txn'],p['source'],p['size']])
        high_end,low_end=fence(high),fence(low)
        begin,end=window(high['clock'])
        ensure(high_end<low['clock']<low_end<end,'seventh paired completion fences')
        seventh.append(dict(transaction=high['txn'],high_source=high['source'],low_source=low['source'],
            high_vram_word=high['word'],low_vram_word=low['word'],
            high_start=high['clock'],high_end=high_end,low_start=low['clock'],low_end=low_end,
            high_clocks=high_end-high['clock'],low_clocks=low_end-low['clock'],
            vblank_start=begin,vblank_end=end,low_fence_margin_clocks=end-low_end))
    ensure(batches and maps,'missing complete batch/map evidence')
    return dict(batches=batches,maps=maps,seventh_dma=seventh)


def certify(folder):
    import m4_home_borrow_bitmap_native as bm
    import m4_restore_single_pass_native as single
    import m4_bitmap_shared_native as shared
    result=candidate_home_certifier(folder)
    result['bitmap']=bm.bitmap_evidence(folder)
    result['single_pass_restoration']=single.evidence(folder)
    result['shared_cells']=shared.shared_evidence(folder)
    result['seven_pair']=packet_evidence(folder)
    result['presentation_windows']=presentation_windows(folder)
    result['classification']='SEVEN_PAIR_NATIVE_CORRECT'
    (Path(folder)/'seven-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def certify_right(folder):
    """Re-certify complete RIGHT captures without executing another world step."""
    import m4_source_safepoint_native as safe
    import m4_nonblank_batch_native as right
    import m4_home_borrow_bitmap_native as bm
    import m4_restore_single_pass_native as single
    import m4_bitmap_shared_native as shared
    contract=json.loads((folder/'contract.json').read_text())
    fields=json.loads((folder/'fields.json').read_text())
    with patch.object(safe,'audit_rom',audit_rom), \
         patch.object(right,'certify',candidate_right_certifier):
        result=safe.certify(folder,contract,fields)
    if result['classification']!='BYOR_MOTU_SOURCE_SAFEPOINT_PASS':
        raise ValueError('Q7_RIGHT_SOURCE_SAFEPOINT_NOT_CERTIFIED')
    result['bitmap']=bm.bitmap_evidence(folder)
    result['single_pass_restoration']=single.evidence(folder)
    result['shared_cells']=shared.shared_evidence(folder)
    if result['bitmap']['plans'] or result['shared_cells']:
        raise ValueError('Q7_RIGHT_UNEXPECTED_BITMAP_WORK')
    result['seven_pair']=packet_evidence(folder)
    result['presentation_windows']=presentation_windows(folder)
    result['classification']='SEVEN_PAIR_RIGHT_CONTROL'
    (folder/'seven-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def build(folder,base=BASE,dotnet=None,poppy=None):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    if folder.exists():raise ValueError('Q7_USE_FRESH_OUTPUT_DIRECTORY')
    base=Path(base)
    if sha(base/'bor.sfc')!=q7.BASE_SHA256:
        raise ValueError('Q7_BASE_ROM_SHA')
    old=(base/'publisher.pasm').read_text().splitlines()
    wanted=q7.transform(old)
    native=folder/'native';native.mkdir(parents=True)
    (native/'publisher.pasm').write_text('\n'.join(wanted)+'\n')
    dotnet=dotnet or Path(os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'))
    poppy=poppy or Path(os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'))
    proc=subprocess.run([str(dotnet),str(poppy),str(native/'publisher.pasm'),
       '--output',str(native/'publisher.bin'),'--symbols',str(native/'publisher.sym'),
       '--no-pansy'],capture_output=True,text=True)
    (native/'publisher-build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('Q7_POPPY_BUILD; read publisher-build.log')
    sy=symbols(native/'publisher.sym');oldsy=symbols(base/'publisher.sym')
    oldrom=(base/'bor.sfc').read_bytes()
    compiled=(native/'publisher.bin').read_bytes()
    a=offset(0x39A000);oldend=offset(oldsy['NbCodeEnd']);newend=offset(sy['NbCodeEnd'])
    if not 0x39A000<sy['NbCodeEnd']<0x39B000:raise ValueError('Q7_NEW_CODE_END')
    rom=bytearray(oldrom)
    wanted_lines=(native/'publisher.pasm').read_text().splitlines()
    old_lines=(base/'publisher.pasm').read_text().splitlines()
    rom,fixups=helper_relocations(rom,compiled,old_lines,wanted_lines,oldsy,sy)
    rom[a:max(oldend,newend)]=bytes(max(oldend,newend)-a)
    rom[a:newend]=compiled[a:newend]
    audit=audit_rom(rom,native)
    (native/'bor.sfc').write_bytes(rom)
    contract=copy.deepcopy(json.loads((base.parent/'contract.json').read_text()))
    contract['native_symbols'].update(sy)
    contract.update(seven_pair_spill=True,seven_pair_audit=audit,
                    seven_pair_base_sha256=q7.BASE_SHA256,
                    seventh_iram_pair=[0x34b0,0x3500],
                    seventh_metadata=[0x42d66e,0x42d672])
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    import m4_restore_single_pass_native as single
    (native/'callback_owner.lua').write_text(single.bootstrap_prefix((base/'callback_owner.lua').read_text()))
    os.link((base/'bor.msu').resolve(),native/'bor.msu')
    return contract


def run_case(folder,case):
    import m4_bitmap_shared_native as shared
    with patch.object(shared,'observer',observer),\
         patch.object(shared,'audit_rom',audit_rom),\
         patch.object(shared,'certify',certify):
        if case=='right':
            import m4_nonblank_batch_native as right
            with patch.object(right,'certify',candidate_right_certifier):
                result=shared.run_case(folder,case)
        else:
            result=shared.run_case(folder,case)
    if case=='right':
        result['seven_pair']=packet_evidence(folder)
        result['presentation_windows']=presentation_windows(folder)
        result['classification']='SEVEN_PAIR_RIGHT_CONTROL'
        (Path(folder)/'seven-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def ensure(ok,reason):
    if not ok:raise ValueError('Q7_ACCEPTANCE:'+reason)


def require_partial_six(evidence,transaction=3):
    policies=[p for p in evidence['policy'] if p[0]==transaction]
    ensure(policies and all(tuple(p[2:])==(2,6) for p in policies),
           'partial-queue fault did not select six-slot policy')
    ensure(transaction not in evidence['seventh_dma_transactions'] and
           all(txn!=transaction for txn,_ in evidence['seventh_source_calls']),
           'partial-queue fault used seventh source')


def collect_suite(root,baseline_root=BASELINE_ROOT):
    baseline=json.loads(Path('docs/receipts/byor-motu-bitmap-shared-cells.json').read_text())
    results={}
    for name in CASES:
        folder=root/name
        result=certify_right(folder) if name=='right' else certify(folder)
        result=json.loads(json.dumps(result))
        evidence=packet_evidence(folder)
        ensure(result['seven_pair']==json.loads(json.dumps(evidence)),name+':7th evidence drift')
        ensure(result['pixel_mismatches']==result['resource_faults']==result['unsafe_ppu_operations']==0,name+':pixel/resource fault')
        ensure(result['min_batch_margin_clocks']>=10000,name+':VBlank margin')
        old=baseline['cases'][name]
        for suffix in ('world','committed','pending','refs','cgram'):
            for file in (folder/'native').glob('*-'+suffix+'.bin'):
                previous=baseline_root/name/'native'/file.name
                ensure(previous.exists() and previous.read_bytes()==file.read_bytes(),
                       name+':source or final referenced authority changed:'+file.name)
        if name!='right':
            ensure(result['source_pixel_difference']==1816,name+':pixel scene changed')
            ensure(set(result['pools'])==set(old['pools']) and
                   all(all(result['pools'][txn][key]==old['pools'][txn][key]
                           for key in ('homes','original_invalid','original_valid',
                                       'policy','limit','need'))
                       for txn in old['pools']),name+':physical home allocation drift')
        results[name]=result
    up=results['success'];old=baseline['cases']['success']
    initial,second=up['transactions'][:2]
    accepted_initial,accepted_second=old['transactions'][:2]
    ensure(initial['fields']<=accepted_initial['fields'] and initial['master_clocks']<=accepted_initial['master_clocks']*1.01,
           'epoch2 publication regression')
    ensure(second['fields']<=accepted_second['fields'] and second['master_clocks']<accepted_second['master_clocks'],
           'epoch3 publication not improved')
    main_batches=[x for x in up['batches'] if x['transaction']==3]
    ensure(len(main_batches)==15 and max(b['pairs'] for b in main_batches)==7,
           'epoch3 did not use fifteen seven-pair batches')
    transfer=next(t for t in up['transfers'] if t['transaction']==3)
    ensure((transfer['chr_pairs'],transfer['chr_bytes'],transfer['map_bytes'],transfer['descriptors'])==(105,8400,4096,212),
           '105-pair DMA workload changed')
    ensure(up['seven_pair']['seventh_dma_transactions'].count(3)==15,
           'epoch3 source7 was not used fifteen times')
    require_partial_six(results['partial']['seven_pair'])
    ensure(any(x['transaction']==4 and x['home']==204 and x['destination']==634 and not x['rollback']
            for x in results['valid']['backdrop_restorations']), 'valid home 204 restoration changed')
    for case in ('early','ready','partial','stale'):
        ensure(bool(results[case]['validity_clear_events']),case+':valid-home rollback missing')
    ensure(next(x for x in results['insufficient']['transfers'] if x['transaction']==3)['descriptors']==0,
           'insufficient-budget performed DMA')
    ensure(results['right']['transition_fields']<=baseline['cases']['right']['transition_fields'],
           'RIGHT acquired a publication field')
    for path in ('docs/byor-motu-bitmap-shared-cells.md',):
        ensure(Path(path).exists(),'baseline doc missing')
    # Historical dirty list has one authorized location; missing or wrong
    # receipt schema fails closed rather than silently skipping preservation.
    import m4_bitmap_shared_native as shared
    fingerprints=shared.inherited_fingerprints(json.loads(Path('docs/receipts/byor-motu-restore-single-pass.json').read_text()))
    for entry in fingerprints:
        ensure(sha(entry['path'])==entry['sha256'],'inherited dirty '+entry['path'])
    ensure(not Path('SNES-BOR-Engine-Prompt.md').exists(),'unrelated unstaged deletion changed')
    report=dict(classification='BYOR_MOTU_SEVEN_PAIR_SPILL_PASS',
       starting_commit=q7.BASE_COMMIT,
       cases=results,
       total_fields=sum(x['observed_fields'] for x in results.values()),
       verified_pixels=sum(x['verified_pixels'] for x in results.values()),
       pixel_mismatches=0,resource_faults=0,unsafe_ppu_operations=0,
       baseline_epoch2=accepted_initial,candidate_epoch2=initial,
       baseline_epoch3=accepted_second,candidate_epoch3=second,
       source7_pairs=up['seven_pair']['seventh_dma_high_pairs'],
       stage_records_max=12,permitted_slot=[0x34b0,0x3500],
       baseline_rom_sha256=q7.BASE_SHA256,
       nonclaims=['30 FPS','200-Hz','SA-1','audio','HUD','combat','Demo readiness'])
    (root/'seven-pair-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--suite',action='store_true')
    p.add_argument('--collect-suite',action='store_true')
    p.add_argument('--build-only',action='store_true')
    p.add_argument('--case',choices=CASES,default='success')
    p.add_argument('--base-native',type=Path,default=BASE)
    p.add_argument('--baseline-root',type=Path,default=BASELINE_ROOT)
    p.add_argument('--dotnet',type=Path,default=Path(os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe')))
    p.add_argument('--poppy',type=Path,default=Path(os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll')))
    a=p.parse_args();out=a.output.resolve()
    if a.collect_suite:
        collect_suite(out,a.baseline_root);return
    if a.suite:
        if out.exists():raise ValueError('Suite must use a new directory')
        for case in CASES:
            folder=out/case
            print('Q7 NATIVE CASE',case,flush=True)
            build(folder,a.base_native,a.dotnet,a.poppy)
            if not a.build_only:run_case(folder,case)
        if not a.build_only:
            report=collect_suite(out,a.baseline_root)
            print(report['classification'],report['total_fields'],report['verified_pixels'])
    else:
        if not a.build_only:build(out,a.base_native,a.dotnet,a.poppy);run_case(out,a.case)
        else:build(out,a.base_native,a.dotnet,a.poppy)


if __name__=='__main__':main()
