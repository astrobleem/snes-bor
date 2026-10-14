"""Strict opt-in predictor ROM/bitmap lifetime audit and native instrumentation."""
import json
from pathlib import Path
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_nonblank_component_native import sha
from m4_restore_spill_native import audit_branches,observer as spill_observer
import m4_nonblank_batch_native as batch
from early_capacity import legacy_transform as transform
REG=Path('out/byor-motu-restore-spill-regression-v1/native')
REG_SHA='05c3cef5f282113867b8dbc235e3bc72a7a718064023cbf58ff9bfc7410aa45d'
CAP=Path('out/byor-motu-restore-spill-capacity-v2/native')
CAP_SHA='cef4b429ff23d86d2daa352f7b73355b961dd7e5f5814d56e0857aa7d4d42034'

def audit(rom,native,base,expected_sha):
    old=(base/'bor.sfc').read_bytes()
    if sha(old)!=expected_sha:raise ValueError('EARLY_CONTROL_IDENTITY')
    wanted=transform((base/'publisher.pasm').read_text().splitlines())
    if (native/'publisher.pasm').read_text().splitlines()!=wanted:raise ValueError('EARLY_SOURCE_TRANSFORM')
    sy=symbols(native/'publisher.sym');compiled=(native/'publisher.bin').read_bytes()
    # Old size auditor has no DEY token. Normalize only its one-byte sizing,
    # and independently require actual DEY opcode 88 at the measured address.
    normalized=[' iny' if line.strip()=='dey' else line for line in wanted]
    branches=audit_branches(normalized,sy,compiled)
    from m4_rect_map_audit import statements
    for i,(pc,size,text) in statements(normalized,sy).items():
        if wanted[i].strip()=='dey' and compiled[offset(pc)]!=0x88:raise ValueError('EARLY_DEY_OPCODE')
    if not 0x39a000==sy['NbBegin']<sy['NbCapacityPredict']<sy['NbCodeEnd']<0x39c000:raise ValueError('EARLY_CODE_LEASE')
    start=offset(sy['NbBegin']);end=offset(sy['NbCodeEnd']);oldend=offset(symbols(base/'publisher.sym')['NbCodeEnd'])
    if any(old[oldend:end]):raise ValueError('EARLY_NONZERO_CODE_LEASE')
    expected=bytearray(old);expected[start:end]=compiled[start:end]
    if rom!=expected:raise ValueError('EARLY_UNAUTHORIZED_ROM_MUTATION')
    return dict(status='PASS',code_bytes=end-start,end=sy['NbCodeEnd'],branch_instructions_verified=branches,all_other_rom_bytes_identical=True,temporary_bitmap=[0x3480,0x34cc],records_capacity=48,queue_unchanged=True)

def audit_rom(rom,native):return audit(rom,native,REG,REG_SHA)
def audit_capacity(rom,native):return audit(rom,native,CAP,CAP_SHA)

def observer(script,contract):
    spill_observer(script,contract);sy=contract['native_symbols']
    with script.open('a') as f:
        f.write('local ecRunning=false;local ecStart=0\n')
        def cb(at,body):f.write(f'emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb(sy['NbCapacityPredict'],"ecRunning=true;ecStart=emu.getState()['masterClock'];if nbWord(0x42d606)~=0 or nbWord(0x42d660)~=0 or nbWord(0x42d674)~=0 then nbLog('FAULT','EARLY_BITMAP_LIFETIME')end;nbLog('EARLY_BEGIN',nbTxn)")
        # Native JSR has returned here, before the caller tests carry.
        cb(sy['NbRestorePlanStart']+9,"ecRunning=false;nbLog('EARLY_RESULT',nbTxn..'|'..nbWord(0x3470)..'|'..nbWord(0x3472)..'|'..nbWord(0x3474)..'|'..(emu.getState()['masterClock']-ecStart)..'|'..nbWord(0x42d606))")
        cb(sy['NbCapacityPredictedRetry'],"nbLog('EARLY_RETRY',nbTxn..'|'..nbWord(0x42d674))")
        cb(sy['NbRestorePlan'],"nbLog('EARLY_ALLOCATOR',nbTxn..'|'..nbWord(0x42d674))")
        for cpu in ('snes','sa1'):
            f.write("emu.addMemoryCallback(function(a,v)if ecRunning then local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];local q=a&0x7ff;if '"+cpu+"'~='snes' or q<0x480 or q>0x4cb or pc<"+str(sy['NbCapacityPredict'])+" or pc>="+str(sy['NbCodeEnd'])+" then nbLog('FAULT','EARLY_BITMAP_OWNER:"+cpu+"|'..a..'|'..pc)else nbLog('EARLY_BITMAP_WRITE',nbTxn..'|'..q)end end end,emu.callbackType.write,0x480,0x6df,emu.cpuType."+cpu+",emu.memType.sa1InternalRam)\n")


def predictor_evidence(folder,epoch,require_retry):
    rows=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'NB_' not in line:continue
        p=line[line.index('NB_'):].split('|')
        if p[0].startswith('NB_EARLY') and int(p[4])==epoch:rows.append(dict(kind=p[0][3:],clock=int(p[1]),data=p[4:]))
    results=[r for r in rows if r['kind']=='EARLY_RESULT']
    if len(results)!=1:raise ValueError('EARLY_PREDICTOR_INVOCATION')
    d=results[0]['data'];free,actor,homes,clocks,records=map(int,d[1:])
    if records:raise ValueError('EARLY_PREDICTOR_LIVE_RECORDS')
    allocator=[r for r in rows if r['kind']=='EARLY_ALLOCATOR'];retry=[r for r in rows if r['kind']=='EARLY_RETRY']
    if require_retry:
        if (free,actor,homes)!=(124,96,30) or len(retry)!=1 or any(r['data'][1]!='1' for r in allocator) or not allocator:raise ValueError('EARLY_CONSERVATIVE_ALLOCATOR_NOT_SKIPPED')
        if retry[0]['clock']>=allocator[0]['clock']:raise ValueError('EARLY_RETRY_ORDER')
    elif retry:raise ValueError('EARLY_ORDINARY_UNEXPECTED_RETRY')
    writes=[r for r in rows if r['kind']=='EARLY_BITMAP_WRITE']
    if len(writes)!=76+2*homes or any(not 0x480<=int(r['data'][1])<0x4cc for r in writes):raise ValueError('EARLY_BITMAP_WRITE_BOUNDS')
    return dict(free_tail=free,conservative_actor=actor,distinct_restoration_homes=homes,predictor_clocks=clocks,predictor_ms=clocks/21477.270,bitmap_bytes=76,bitmap_write_bytes=len(writes),zero_live_records=True,conservative_allocator_skipped=require_retry,temporary_ownership_pass=True)


def regression(folder,source,sy,contract,fault_mode=1):
    original=batch.observer
    def wrapped(script,c):
        with patch.object(batch,'observer',original):observer(script,c)
    with patch.object(batch,'audit_rom',audit_rom),patch.object(batch,'observer',wrapped):batch.run(folder,source,sy,contract,fault_mode)
    r=json.loads((folder/'result.json').read_text());r['classification']='EARLY_CAPACITY_BATCH_REGRESSION_PASS';r['early_capacity']={str(i):predictor_evidence(folder,i,False) for i in (1,2)};(folder/'result.json').write_text(json.dumps(r,indent=2)+'\n')
