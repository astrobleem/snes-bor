"""Candidate-only native adapter; accepted ROM and certifiers remain intact."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess

import capacity_scan as overlay
import m4_abort_copy_native as accepted

BASE=Path('out/byor-motu-abort-copy-v1/success/native')
BASE_SHA='2ae50b27ac69986a07925e37fd99f5f5506044dec6195662ea54524a8ac4166f'
q8=accepted.accepted.accepted.accepted.accepted.accepted.q8


def require(ok,code):
    if not ok:raise ValueError('CAPACITY_SCAN:'+code)


def audit_rom(rom,native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    original=(BASE/'bor.sfc').read_bytes()
    require(accepted.capture.sha(BASE/'bor.sfc')==BASE_SHA,'BASE_DIGEST')
    prior=accepted.audit_rom(original,BASE)
    lines=(native/'publisher.pasm').read_text().splitlines()
    require(lines==overlay.transform((BASE/'publisher.pasm').read_text().splitlines()),'SOURCE_TRANSFORM')
    sy=symbols(native/'publisher.sym');old=symbols(BASE/'publisher.sym')
    require(all(sy.get(k)==v for k,v in old.items()),'OLD_LABEL_MOVED')
    require(sy['CsPredict']==overlay.START and sy['CsCodeEnd']<overlay.LIMIT,'CODE_LEASE')
    at=offset(overlay.PATCH);start=offset(overlay.START);end=offset(sy['CsCodeEnd'])
    require(original[at:at+6]==bytes.fromhex('a90000a20000') and not any(original[start:end]),'ORIGINAL_BYTES')
    compiled=(native/'publisher.bin').read_bytes()
    patch=b'\x4c'+(overlay.START&65535).to_bytes(2,'little')+b'\xea'*3
    require(compiled[at:at+6]==patch,'DISPATCH')
    helper=compiled[start:end]
    # Verify both bank-local authorities and the only long bitmap stores.
    require(helper.count(bytes.fromhex('b900c0'))==1 and helper.count(bytes.fromhex('bd00d0'))==2,'LOCAL_READS')
    require(helper.count(bytes.fromhex('9f803400'))==2,'BITMAP_STORES')
    require(helper[:8]==bytes.fromhex('8b5af44242ababA9'),'BANK_STACK_PROLOGUE')
    expected=bytearray(original);expected[at:at+6]=patch;expected[start:end]=helper
    require(bytes(rom)==expected,'UNAUTHORIZED_ROM_BYTE')
    sizing=[{'cld':' clc','tyx':' tax'}.get(line.strip(),line) for line in accepted.accepted.accepted.accepted._sizing(lines)]
    branches=audit_branches(sizing,sy,compiled)
    prior['capacity_scan']=dict(status='STATIC_CANDIDATE',base_rom_sha256=BASE_SHA,
        dispatch=[overlay.PATCH,overlay.PATCH+6],helper=[overlay.START,sy['CsCodeEnd']],
        helper_bytes=end-start,branch_sites=branches,all_original_labels_retained=True,
        bitmap=[0x3480,0x34cc],no_new_ram_or_vram=True)
    return prior


def build(folder,control=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    require(not folder.exists(),'FRESH_OUTPUT_REQUIRED')
    folder.mkdir(parents=True);native=folder/'native';native.mkdir()
    contract=json.loads((BASE.parent/'contract.json').read_text())
    source=(BASE/'publisher.pasm').read_text().splitlines()
    lines=overlay.transform(source,enabled=not control)
    (native/'publisher.pasm').write_text('\n'.join(lines)+'\n')
    command=[os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'),
        os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
        str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),
        '--symbols',str(native/'publisher.sym'),'--no-pansy']
    run=subprocess.run(command,capture_output=True,text=True)
    (native/'capacity-scan-build.log').write_text(run.stdout+run.stderr)
    require(run.returncode==0,'ASSEMBLY')
    original=(BASE/'bor.sfc').read_bytes();rom=bytearray(original)
    sy=symbols(native/'publisher.sym');compiled=(native/'publisher.bin').read_bytes()
    if not control:
        for lo,hi in ((overlay.PATCH,overlay.PATCH+6),(overlay.START,sy['CsCodeEnd'])):
            a,b=offset(lo),offset(hi);rom[a:b]=compiled[a:b]
        contract['eight_pair_audit']=audit_rom(rom,native)
    else:
        require(compiled==(BASE/'publisher.bin').read_bytes(),'DISABLED_CODE_IDENTITY')
        require(bytes(rom)==original,'DISABLED_ROM_IDENTITY')
    (native/'bor.sfc').write_bytes(rom)
    os.link((BASE/'bor.msu').resolve(),native/'bor.msu')
    # Runtime callback owner contains native startup metadata/constructor input;
    # copy its original source, never a generated graphics result.
    import m4_restore_single_pass_native as single
    (native/'callback_owner.lua').write_text(single.bootstrap_prefix((BASE/'callback_owner.lua').read_text()))
    contract['native_symbols'].update(sy);contract['capacity_scan']=not control
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    return contract


def observer(script,contract):
    accepted.observer(script,contract)
    if not contract.get('capacity_scan'):return
    from m4_input_controller_native import offset
    sy=contract['native_symbols'];blob=(script.parent/'publisher.bin').read_bytes()
    start,end=offset(overlay.START),offset(sy['CsCodeEnd'])
    pcs=[overlay.START+i+4 for i in range(end-start-3)
         if blob[start+i:start+i+4]==bytes.fromhex('9f803400')]
    require(len(pcs)==2,'EXACT_WRITE_PC_INVENTORY')
    text=script.read_text()
    old='or pc<'+str(sy['NbCapacityPredict'])+' or pc>='+str(sy['NbCodeEnd'])
    new='or not ('+' or '.join('pc=='+str(pc)for pc in pcs)+')'
    require(text.count(old)==2,'PINNED_BITMAP_OWNERSHIP_GUARDS')
    text=text.replace(old,new)
    # The outer queue/record guard predates the prediction-specific guard.
    # Admit the relocated stores through BOTH guards, only for their lifetime.
    outer="if not (bbLive and 'snes'=='snes'"
    require(text.count(outer)==1,'PINNED_OUTER_QUEUE_GUARD')
    exact='('+ ' or '.join('pc=='+str(pc)for pc in pcs)+')'
    lease=("csActive and "+exact+" and (a&0x7ff)>=0x480 and (a&0x7ff)<0x4cc"
           " and nbWord(0x42d600)==1 and nbWord(0x42d606)==0"
           " and nbWord(0x42d608)==0 and nbWord(0x42d60a)==0"
           " and nbWord(0x42d660)==0 and nbWord(0x42d674)==0"
           " and nbWord(0x42d70c)==0")
    text=text.replace(outer,'if not ('+lease+") and not (bbLive and 'snes'=='snes'")
    text='local csActive=false\n'+text
    text+='''
local csEntry=nil
local function csRegs(s)
 return s['cpu.a']..'|'..s['cpu.x']..'|'..s['cpu.y']..'|'..s['cpu.dbr']..'|'..s['cpu.d']..'|'..s['cpu.sp']..'|'..s['cpu.ps']
end
'''
    for pc,body in ((overlay.PATCH,
        "local s=emu.getState();if csActive or nbWord(0x42d600)~=1 or nbWord(0x42d70c)~=0 then nbLog('FAULT','CS_OWNER')end;csActive=true;csEntry=s['masterClock'];nbLog('CS_ENTRY',nbTxn..'|'..csRegs(s)..'|'..cpDump(0x42c000,2048)..'|'..cpDump(0x42d000,1536)..'|'..cpDump(0x3400,128))"),
        (sy['NbCapacityPredictionReturned'],
        "local s=emu.getState();if not csEntry or not csActive or nbWord(0x42d600)~=1 or nbWord(0x42d606)~=0 or nbWord(0x42d660)~=0 or nbWord(0x42d70c)~=0 then nbLog('FAULT','CS_OPEN_CALL')else nbLog('CS_RETURN',nbTxn..'|'..(s['masterClock']-csEntry)..'|'..csRegs(s)..'|'..cpDump(0x3400,128));csEntry=nil;csActive=false end")):
        text+=f'emu.addMemoryCallback(function() {body} end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n'
    for cpu in ('snes','sa1'):
        text+=f"emu.addMemoryCallback(function(a,v)if csActive then nbLog('FAULT','CS_AUTHORITY_WRITE:{cpu}|'..a)end end,emu.callbackType.write,0x2c000,0x2d5ff,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n"
        for lo,hi in ((0x2d600,0x2d60b),(0x2d660,0x2d661),(0x2d674,0x2d675),(0x2d70c,0x2d70d)):
            text+=f"emu.addMemoryCallback(function(a,v)if csActive then nbLog('FAULT','CS_METADATA_WRITE:{cpu}|'..a)end end,emu.callbackType.write,{lo},{hi},emu.cpuType.{cpu},emu.memType.snesSaveRam)\n"
    script.write_text(text)


def profile(folder):
    from ready_validate_evidence import events
    from test_early_capacity import ProbeVM
    rows=events(folder/'native/mesen.log');pending=None;result=[]
    for row in rows:
        if row['kind']=='CS_ENTRY':
            require(pending is None,'NESTED_ENTRY');pending=row
        elif row['kind']=='CS_RETURN':
            require(pending is not None,'RETURN_WITHOUT_ENTRY')
            a=pending['data'];b=row['data'];require(a[0]==b[0],'TRANSACTION')
            regs=list(map(int,a[1:8]));actual=list(map(int,b[2:9]))
            maps=bytes.fromhex(a[8]);refs=bytes.fromhex(a[9]);dp=bytes.fromhex(a[10])
            words=lambda raw:[int.from_bytes(raw[i:i+2],'little')for i in range(0,len(raw),2)]
            vm=ProbeVM(words(maps),words(refs));vm.A,vm.X,vm.Y=regs[:3]
            vm.dp={i:int.from_bytes(dp[i:i+2],'little')for i in range(0,128,2)}
            carry=vm.run();expected_dp=bytearray(dp)
            for at,value in vm.dp.items():expected_dp[at:at+2]=value.to_bytes(2,'little')
            require(bytes.fromhex(b[9])==expected_dp,'EXACT_DP_RESULT')
            require((regs[6]&0x38)==0 and regs[4]==0x3400,'CALLER_BINARY_A16_I16_DP')
            require(actual[:3]==[vm.A,vm.X,vm.Y] and actual[3:5]==regs[3:5]
                    and actual[5]==((regs[5]+2)&65535),'REGISTER_STACK_DBR_DP')
            require(bool(actual[6]&1)==carry and bool(actual[6]&2)==vm.Z,'CARRY_ZERO')
            require((actual[6]&0x3c)==(regs[6]&0x3c),'CALLER_MODE_FLAGS')
            negative=vm.A<(49 if vm.dp[0x74]>=49 else vm.dp[0x70])
            overflow=bool(regs[6]&0x40) if vm.dp[0x74]>=49 else False
            require(bool(actual[6]&0x80)==negative and bool(actual[6]&0x40)==overflow,'NEGATIVE_OVERFLOW')
            result.append(dict(transaction=int(a[0]),clocks=int(b[1]),exact_result=True,
                               free=vm.dp[0x70],actors=vm.dp[0x72],homes=vm.dp[0x74],reject=carry))
            pending=None
    require(pending is None,'OPEN_CALL')
    output=dict(classification='CAPACITY_SCAN_NATIVE_PROFILE',calls=result)
    (folder/'capacity-scan-profile.json').write_text(json.dumps(output,indent=2)+'\n')
    return output


def collect_suite(root,seal):
    """Retain every inherited certifier and compare all timings to a5ecc1f."""
    from unittest.mock import patch
    from ready_validate_evidence import events
    from borrow_invalidate_evidence import compare_case_timings
    capture=accepted.capture
    output=root/'capacity-scan-receipt.json'
    require(not output.exists(),'EXISTING_RECEIPT')
    old_root=BASE.parent.parent
    old_seal=capture.CaptureSeal(
        'd32f4c27ee4bf5ae5f6b5361091302365927ede33b9ab498b207eeec498b4282',
        'f7a2d69a5db7b48f57f304b16b5c5a58e2e3da9a7b0d613e22abe24be52e4ba8')
    before=capture.verify_capture(root,seal)
    before_old=capture.verify_capture(old_root,old_seal)
    baseline=capture._pinned_json(old_root/'abort-copy-receipt.json',
        'dcfc8339cdcb8d0564c870cabf799505b1e0ca5cbb876853b215ae6e4bc178b1',
        'ACCEPTED_ABORT_COPY_RECEIPT')
    require(all(json.loads((root/case/'contract.json').read_text()).get('capacity_scan') is True
                for case in capture.CASES),'ENABLED_CASE_INVENTORY')
    with patch.object(accepted,'audit_rom',audit_rom):
        result=accepted.collect_suite(root,seal)
    comparisons=compare_case_timings(result,baseline)
    predictions={}
    for case in capture.CASES:
        calls=profile(root/case)['calls']
        old=[r for r in events(old_root/case/'native/mesen.log')if r['kind']=='EARLY_RESULT']
        require(len(calls)==len(old),case+':PREDICTION_INVENTORY')
        rows=[]
        for call,previous in zip(calls,old):
            data=list(map(int,previous['data']))
            require((call['transaction'],call['free'],call['actors'],call['homes'])==tuple(data[:4]),
                    case+':PREDICTION_INPUT_COUNTS')
            require(call['clocks']<=data[4],case+':PREDICTION_REGRESSION')
            rows.append(dict(transaction=call['transaction'],before_clocks=data[4],
                             after_clocks=call['clocks'],saved_clocks=data[4]-call['clocks']))
        predictions[case]=rows
    target=[r for r in predictions['success']if r['transaction']==3]
    require(len(target)==1 and target[0]['after_clocks']*5<=target[0]['before_clocks']*4,
            'PREDICTION_GAIN_BELOW_20_PERCENT')
    # A leaf gain with unchanged field cadence is insufficient for the chosen
    # next step. Require the ordinary pressured publication to lose a field.
    old_epoch3=next(t for t in baseline['cases']['success']['transactions']if t['transaction']==3)
    new_epoch3=next(t for t in result['cases']['success']['transactions']if t['transaction']==3)
    require(new_epoch3['fields']<old_epoch3['fields'],'NO_ORDINARY_FIELD_ADVANCE')
    require(capture.verify_capture(root,seal)==before and
            capture.verify_capture(old_root,old_seal)==before_old,'RAW_CAPTURE_CHANGED')
    result.update(classification='BYOR_MOTU_CAPACITY_SCAN_PASS',
        starting_commit='a5ecc1f01a401cc5f77e9df8a57bd4197706be02',
        accepted_abort_copy_capture_evidence=before_old,
        all_case_timing_comparison_to_abort_copy=comparisons,
        capacity_prediction_comparison=predictions,prediction_gain_threshold_percent=20,
        ordinary_epoch3_field_advance=True,no_new_ram_or_vram=True)
    with output.open('x',encoding='utf-8') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    return result
