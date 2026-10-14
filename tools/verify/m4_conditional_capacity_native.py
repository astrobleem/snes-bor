"""Conditional gate: strict ROM audit, independent native intervals and decisions."""
import inspect,json
from pathlib import Path
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_nonblank_component_native import sha
import m4_nonblank_batch_native as batch
import m4_early_capacity_native as prior
from early_capacity import transform

REG=prior.REG;CAP=prior.CAP

def audit_rom(rom,native):
    with patch.object(prior,'transform',transform):return prior.audit(rom,native,REG,prior.REG_SHA)
def audit_capacity(rom,native):
    with patch.object(prior,'transform',transform):return prior.audit(rom,native,CAP,prior.CAP_SHA)

def observer(script,contract):
    # Preserve the unconditional observer for historical controls. Its post-JSR
    # boundary is relocated to an explicit label in the conditional candidate.
    ns=dict(prior.__dict__);body=inspect.getsource(prior.observer).replace('def observer(', 'def conditional_observer(').replace("sy['NbRestorePlanStart']+9","sy['NbCapacityPredictionReturned']")
    exec(body,ns);ns['conditional_observer'](script,contract);sy=contract['native_symbols']
    with script.open('a') as f:
        f.write('local cgRunning=false;local cgStart=0;local cgStorage=nil;local cgReads=0\n')
        def cb(at,body):f.write(f'emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb(sy['NbCapacityPressureGate'],"cgRunning=true;cgStart=emu.getState()['masterClock'];cgReads=0;cgStorage={};for i=0x480,0x6df do cgStorage[#cgStorage+1]=emu.read(i,emu.memType.sa1InternalRam)end;if nbWord(0x42d606)~=0 or nbWord(0x42d660)~=0 or nbWord(0x42d674)~=0 then nbLog('FAULT','PRESSURE_LIFETIME')end;nbLog('PRESSURE_BEGIN',nbTxn)")
        cb(sy['NbCapacityPressureReturned'],"cgRunning=false;for i=0x480,0x6df do if emu.read(i,emu.memType.sa1InternalRam)~=cgStorage[i-0x480+1]then nbLog('FAULT','PRESSURE_STORAGE_CHANGED')end end;nbLog('PRESSURE_RESULT',nbTxn..'|'..nbWord(0x3470)..'|'..cgReads..'|'..(emu.getState()['masterClock']-cgStart))")
        f.write("emu.addMemoryCallback(function(a,v)if cgRunning then if a<0x42d4a8 or a>0x42d5ff then nbLog('FAULT','PRESSURE_REF_RANGE')else cgReads=cgReads+1 end end end,emu.callbackType.read,0x42d000,0x42d5ff,emu.cpuType.snes,emu.memType.snesMemory)\n")
        for cpu in ('snes','sa1'):
            f.write("emu.addMemoryCallback(function(a,v)if cgRunning then nbLog('FAULT','PRESSURE_RECORD_QUEUE_WRITE:"+cpu+"|'..a)end end,emu.callbackType.write,0x480,0x6df,emu.cpuType."+cpu+",emu.memType.sa1InternalRam)\n")
        f.write("emu.addMemoryCallback(function(a,v)if cgRunning then nbLog('FAULT','PRESSURE_MAP_READ')end end,emu.callbackType.read,0x42c000,0x42c7ff,emu.cpuType.snes,emu.memType.snesMemory)\n")

def evidence(folder,epoch,free_actual,require_prediction):
    import numpy as np
    refpath=folder/'native'/('before-refs.bin' if require_prediction else 'cold-refs.bin')
    measured_free=int(np.count_nonzero((np.frombuffer(refpath.read_bytes(),dtype='<u2')&0x3fff)[596:]==0))
    if measured_free!=free_actual:raise ValueError('PRESSURE_SOURCE_OWNED_FREE_COUNT')
    rows=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'NB_' not in line:continue
        p=line[line.index('NB_'):].split('|')
        if p[0].startswith(('NB_PRESSURE','NB_EARLY')) and int(p[4])==epoch:rows.append(dict(kind=p[0][3:],clock=int(p[1]),data=p[4:]))
    gates=[r for r in rows if r['kind']=='PRESSURE_RESULT'];predictors=[r for r in rows if r['kind']=='EARLY_RESULT']
    if len(gates)!=1 or sum(r['kind']=='PRESSURE_BEGIN' for r in rows)!=1:raise ValueError('PRESSURE_ONE_CALL_PER_CONSERVATIVE_MARK')
    count,reads,clocks=map(int,gates[0]['data'][1:])
    if count!=min(129,free_actual) or reads%2 or not 1<=reads//2<=172:raise ValueError('PRESSURE_COUNTER_OR_READS')
    if require_prediction:
        if len(predictors)!=1:raise ValueError('PRESSURE_REQUIRED_PREDICTOR_MISSING')
        result=prior.predictor_evidence(folder,epoch,True)
    else:
        if predictors or any(r['kind'] in ('EARLY_BEGIN','EARLY_RETRY','EARLY_BITMAP_WRITE') for r in rows):raise ValueError('PRESSURE_SKIP_NOT_COMPLETE')
        result=dict(predictor_clocks=0,predictor_ms=0,bitmap_write_bytes=0,conservative_allocator_skipped=False)
        allocator=[r for r in rows if r['kind']=='EARLY_ALLOCATOR']
        if not allocator or any(r['data'][1]!='0' for r in allocator):raise ValueError('PRESSURE_ORIGINAL_PLANNER_BYPASSED')
    result.update(gate_master_clocks=clocks,gate_ms=clocks/21477.270,gate_calls=1,predictor_invocations=len(predictors),free_tail_actual=free_actual,gate_free_count=count,reference_words_read=reads//2,gate_storage_unchanged=True,exact_retry_skips_both=True)
    return result

def regression(folder,source,sy,contract,fault_mode=1):
    original=batch.observer
    def wrapped(script,c):
        with patch.object(batch,'observer',original):observer(script,c)
    with patch.object(batch,'audit_rom',audit_rom),patch.object(batch,'observer',wrapped):batch.run(folder,source,sy,contract,fault_mode)
    r=json.loads((folder/'result.json').read_text());r['classification']='CONDITIONAL_CAPACITY_BATCH_CORRECT';r['conditional_capacity']={str(i):evidence(folder,i,134,False) for i in (1,2)};(folder/'result.json').write_text(json.dumps(r,indent=2)+'\n')
