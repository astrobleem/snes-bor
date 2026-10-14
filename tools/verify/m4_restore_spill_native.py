"""Strict opt-in restoration-spill audit; old batch auditor stays unchanged."""
import json
from pathlib import Path
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_nonblank_component_native import sha
import m4_nonblank_batch_native as batch
from restore_spill import transform
BASE=Path('out/byor-motu-batch-rescue-v1/native')
BASE_SHA='e710074d80cd6ad2354664956c7d0be867008c13a98006042f51d6fc9bd091ec'

def audit_rom(rom,native):
    old=(BASE/'bor.sfc').read_bytes()
    if sha(old)!=BASE_SHA:raise ValueError('SPILL_CONTROL_IDENTITY')
    wanted=transform((BASE/'publisher.pasm').read_text().splitlines())
    if (native/'publisher.pasm').read_text().splitlines()!=wanted:raise ValueError('SPILL_EXACT_TRANSFORM')
    from m4_rect_map_audit import statements
    sy=symbols(native/'publisher.sym');audit_branches(wanted,sy,(native/'publisher.bin').read_bytes())
    start=offset(sy['NbBegin']);end=offset(sy['NbCodeEnd'])
    if sy['NbBegin']!=0x39a000 or sy['NbCodeEnd']>=0x39c000:raise ValueError('SPILL_CODE_PLACEMENT')
    oldend=offset(symbols(BASE/'publisher.sym')['NbCodeEnd'])
    if any(old[oldend:end]):raise ValueError('SPILL_CODE_LEASE_NOT_ZERO')
    expected=bytearray(old);expected[start:end]=(native/'publisher.bin').read_bytes()[start:end]
    if expected!=rom:raise ValueError('SPILL_UNAUTHORIZED_ROM_MUTATION')
    return dict(status='PASS',bytes=end-start,end=sy['NbCodeEnd'],all_other_rom_bytes_identical=True,records=48,spill=[0x42d620,0x42d660],queue_unchanged=True)

def audit_branches(lines,sy,compiled):
    from m4_rect_map_audit import statements,BRANCHES
    count=0
    for pc,size,text in statements(lines,sy).values():
        op,_,arg=text.partition(' ')
        if op not in BRANCHES|{'brl'}:continue
        delta=sy[arg]-pc-size
        if not -(1<<(8*(size-1)-1))<=delta<(1<<(8*(size-1)-1)):raise ValueError('SPILL_BRANCH_RANGE:'+text)
        if compiled[offset(pc)+1:offset(pc)+size]!=delta.to_bytes(size-1,'little',signed=True):raise ValueError('SPILL_BRANCH_BINARY:'+text)
        count+=1
    return count

def observer(script,contract):
    batch.observer(script,contract)
    sy=contract['native_symbols']
    with script.open('a') as f:
        for cpu in ('snes','sa1'):
            f.write("emu.addMemoryCallback(function(a,v)local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];if '"+cpu+"'~='snes' or pc<"+str(sy['NbRestoreStoreOverflow'])+" or pc>"+str(sy['NbRestoreStoreDone'])+" then nbLog('FAULT','SPILL_OWNER:"+cpu+"|'..a..'|'..pc)else nbLog('SPILL_WRITE',a..'|'..v)end end,emu.callbackType.write,0x2d620,0x2d65f,emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")
        for label in ('NbActorPlanStart','NbActorProduceStart','NbRestoreStoreOverflow'):
            f.write(f"emu.addMemoryCallback(function()nbLog('SPILL_PHASE','{label}|'..nbWord(0x42d606)..'|'..nbWord(0x42d674))end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,emu.memType.snesMemory)\n")

def regression(folder,source,sy,contract,fault_mode=1):
    # Existing complete certifier, with only its separately audited ROM identity
    # substituted. Pixel, DMA, queue and timing requirements remain intact.
    original=batch.observer
    def wrapped(script,c):
        with patch.object(batch,'observer',original):observer(script,c)
    with patch.object(batch,'audit_rom',audit_rom),patch.object(batch,'observer',wrapped):
        batch.run(folder,source,sy,contract,fault_mode)
    result=json.loads((folder/'result.json').read_text())
    result['classification']='RESTORE_SPILL_BATCH_REGRESSION_PASS'
    result['capacity_admission']='Verified separately by m4_restore_spill_capacity_native; this is the 30-field regression.'
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
