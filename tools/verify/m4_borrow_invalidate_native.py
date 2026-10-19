"""Bounded cached borrowed-home lookup over accepted reference rebuild."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import borrow_invalidate as overlay
import borrow_invalidate_evidence as evidence
import fused_capture_evidence as capture
import m4_ref_rebuild_native as accepted

BASELINE = evidence.BASELINE
BASE = BASELINE/'success/native'
STARTING_COMMIT = '438b519ff32879298d97e050ca25a3f119a7401a'
ACCEPTED_AUDIT = accepted.audit_rom
PATCH_PC = 0x39B4D5
PATCH_BEFORE, PATCH_AFTER = bytes.fromhex('a20000'), bytes.fromhex('4c00ab')
# Independent literal encoding. Relative branches: +40,+23,+8,-15.
LITERAL_HEX = ('5a8bf44242ababad04d7c95502b028a20000a8f017'
    'bd10d729ff3fc52cf008e8e888d0f14c2cab'
    'ab7a4cf6b4ab7a8a4acf04d7424c27b5ab7aa200004cd8b4')
FIXED = dict(IvFind=0x39AB00,IvLoop=0x39AB15,IvFound=0x39AB27,
             IvMiss=0x39AB2C,IvFallback=0x39AB37,IvCodeEnd=0x39AB3F)
RETURN_PCS = (evidence.RETURN_REFERENCED,evidence.RETURN_OK,evidence.RETURN_BAD)
TABLE_WRITE_PC, REF_WRITE_PC = 0x39B516, 0x39B525


def require(ok,code):
    evidence.require(ok,code)


def audit_rom(rom,native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    require(capture.sha(BASE/'bor.sfc') == evidence.BASE_ROM_SHA256,'BASE_ROM_DIGEST')
    original = (BASE/'bor.sfc').read_bytes()
    inherited = ACCEPTED_AUDIT(original,BASE)
    old = (BASE/'publisher.pasm').read_text().splitlines()
    lines = (native/'publisher.pasm').read_text().splitlines()
    require(lines == overlay.transform(old),'EXACT_SOURCE_TRANSFORM')
    sy = symbols(native/'publisher.sym'); oldsy = symbols(BASE/'publisher.sym')
    require(all(sy.get(name) == pc for name,pc in oldsy.items()),'ORIGINAL_SYMBOL_MOVED')
    require(all(sy.get(name) == pc for name,pc in FIXED.items()),'INDEPENDENT_HELPER_LAYOUT')
    require(sy['IvCodeEnd'] < overlay.CODE_LIMIT,'HELPER_PLACEMENT')
    start,end = offset(sy['IvFind']),offset(sy['IvCodeEnd'])
    compiled = (native/'publisher.bin').read_bytes(); literal = bytes.fromhex(LITERAL_HEX)
    require(not any(original[start:end]),'HELPER_GAP_NOT_ZERO')
    require(len(literal) == end-start == 63 and compiled[start:end] == literal,
            'INDEPENDENT_HELPER_OPCODES')
    at = offset(PATCH_PC)
    require(original[at:at+3] == PATCH_BEFORE and compiled[at:at+3] == PATCH_AFTER,
            'INDEPENDENT_DISPATCH_OPCODES')
    expected = bytearray(original); expected[at:at+3] = PATCH_AFTER; expected[start:end] = literal
    require(bytes(rom) == bytes(expected),'UNAUTHORIZED_ROM_BYTE')
    require(original[offset(TABLE_WRITE_PC)-4] == original[offset(REF_WRITE_PC)-4] == 0x9f
            and all(original[offset(pc)] == 0x60 for pc in RETURN_PCS)
            and original[offset(evidence.CALLER_JSR):offset(evidence.CALLER_RETURN)] == bytes.fromhex('20bfb4')
            and original[offset(evidence.CALLER_RETURN)] == 0x90,'ORIGINAL_OBSERVER_OPCODE')
    branches = audit_branches(accepted.accepted._sizing(lines),sy,compiled)
    inherited['borrow_invalidate'] = dict(status='PASS',baseline_sha256=evidence.BASE_ROM_SHA256,
        patch_pc=PATCH_PC,patch_bytes=3,code_start=sy['IvFind'],code_end=sy['IvCodeEnd'],code_bytes=63,
        branch_sites=branches,all_original_symbols_identical=True,all_original_guards_retained=True,
        no_new_memory_or_queue_capacity=True,max_fast_count=596,
        fallback_to_original_loop=True,allowed_rom_byte_ranges=[[at,at+3],[start,end]])
    return inherited


def build(folder,control=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract = accepted.build(folder)
    native = folder/'native'
    require(capture.sha(native/'bor.sfc') == evidence.BASE_ROM_SHA256,'BASE_REBUILD_IDENTITY')
    if control:
        contract['borrow_invalidate'] = False
        (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        return contract
    lines = (native/'publisher.pasm').read_text().splitlines()
    (native/'publisher.pasm').write_text('\n'.join(overlay.transform(lines))+'\n')
    command = [os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'),
        os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
        str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),
        '--symbols',str(native/'publisher.sym'),'--no-pansy']
    result = subprocess.run(command,capture_output=True,text=True)
    (native/'borrow-invalidate-build.log').write_text(result.stdout+result.stderr)
    require(result.returncode == 0,'POPPY_ASSEMBLY')
    sy = symbols(native/'publisher.sym'); compiled = (native/'publisher.bin').read_bytes()
    at = offset(PATCH_PC); start,end = offset(sy['IvFind']),offset(sy['IvCodeEnd'])
    rom = bytearray((native/'bor.sfc').read_bytes())
    rom[at:at+3] = compiled[at:at+3]; rom[start:end] = compiled[start:end]
    audit = audit_rom(rom,native)
    (native/'bor.sfc').write_bytes(rom)
    contract['native_symbols'].update(sy)
    contract.update(borrow_invalidate=True,eight_pair_audit=audit)
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    return contract


def observer(script,contract):
    accepted.observer(script,contract)
    sy = contract['native_symbols']
    with script.open('a') as stream:
        stream.write("""
local biStart=nil;local biSeq=0;local biTrace=nil;local biReturned=false
local function biRegs(s)
 return s['cpu.a']..'|'..s['cpu.x']..'|'..s['cpu.y']..'|'..s['cpu.d']..'|'..s['cpu.dbr']..'|'..s['cpu.sp']..'|'..s['cpu.ps']..'|'..nbWord(0x3470)
end
local function biWords()
 return nbWord(0x342c)..'|'..nbWord(0x42d704)..'|'..nbWord(0x42d70c)..'|'..cpDump(0x42d000,1536)..'|'..cpDump(0x42d710,1192)
end
local function biEnter()
 if biStart then nbLog('FAULT','BI_REENTRY')end
 local s=emu.getState();biStart=s['masterClock'];biSeq=biSeq+1;biTrace={};biReturned=false
 local caller=0x390000+((nbWord(s['cpu.sp']+1)+1)&0xffff)
 nbLog('BI_ENTRY',biSeq..'|'..nbTxn..'|'..biRegs(s)..'|'..biWords()..'|'..caller)
end
local function biRts(pc)
 if not biStart or biReturned then nbLog('FAULT','BI_RTS_WITHOUT_ENTRY');return end
 local s=emu.getState();biReturned=true
 nbLog('BI_RTS',biSeq..'|'..nbTxn..'|'..pc..'|'..biRegs(s)..'|'..biWords()..'|'..table.concat(biTrace))
end
local function biExit(pc)
 if not biStart or not biReturned then nbLog('FAULT','BI_EXIT_WITHOUT_RTS');return end
 local s=emu.getState()
 nbLog('BI_EXIT',biSeq..'|'..nbTxn..'|'..(s['masterClock']-biStart)..'|'..pc..'|'..biRegs(s)..'|'..biWords()..'|'..table.concat(biTrace))
 biStart=nil;biTrace=nil
end
""")
        def cb(pc,body):
            stream.write(f'emu.addMemoryCallback(function() {body} end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb(sy['BhInvalidate'],'biEnter()')
        for pc in RETURN_PCS: cb(pc,f'biRts({pc})')
        cb(evidence.CALLER_RETURN,f'biExit({evidence.CALLER_RETURN})')
        for cpu in ('snes','sa1'):
            for start,end,pc in ((0x2d000,0x2d5ff,REF_WRITE_PC),(0x2d710,0x2dbb7,TABLE_WRITE_PC)):
                stream.write("emu.addMemoryCallback(function(a,v)if biStart then local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];if '"+cpu+"'~='snes' or pc~="+str(pc)+" then nbLog('FAULT','BI_WRITE_OWNER:"+cpu+"|'..a..'|'..pc)end;biTrace[#biTrace+1]=string.format('%04x%02x',a&0xffff,v)end end,emu.callbackType.write,"+str(start)+","+str(end)+",emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")
            for start,end in ((0x2d704,0x2d705),(0x2d70c,0x2d70d)):
                stream.write("emu.addMemoryCallback(function(a,v)if biStart then nbLog('FAULT','BI_MUTABLE_COUNT_OR_OWNER:"+cpu+"|'..a)end end,emu.callbackType.write,"+str(start)+","+str(end)+",emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")
            stream.write("emu.addMemoryCallback(function(a,v)if biStart then nbLog('FAULT','BI_MUTABLE_HOME:"+cpu+"|'..a)end end,emu.callbackType.write,13356,13357,emu.cpuType."+cpu+",emu.memType.snesMemory)\n")


def profile(folder):
    calls = evidence.native_calls(folder/'native/mesen.log')
    totals = {}
    for row in calls:
        txn = row['transaction']; total = totals.setdefault(txn,dict(calls=0,master_clocks=0))
        total['calls'] += 1; total['master_clocks'] += row['master_clocks']
    result = dict(classification='BORROW_INVALIDATE_PROFILE_PASS',
        rom_sha256=capture.sha(folder/'native/bor.sfc'),calls=calls,transactions=totals,
        boundary='Original BhInvalidate entry through the original caller continuation, after RTS; separate pre-RTS ABI snapshot.')
    (folder/'borrow-invalidate-profile.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def collect_suite(root,seal,control_root,control_digest):
    require(not (root/'borrow-invalidate-receipt.json').exists(),
            'EXISTING_PASS_RECEIPT_MUST_BE_RETAINED_BEFORE_RECOLLECTION')
    baseline = evidence.load_baseline()
    native_baseline = evidence.load_native_baseline(baseline)
    before_base = capture.verify_capture(BASELINE,evidence.BASE_SEAL)
    before = capture.verify_capture(root,seal)
    control_before = evidence.verify_control(control_root,control_digest)
    require(all(json.loads((root/case/'contract.json').read_bytes()).get('borrow_invalidate') is True
                for case in capture.CASES),'CANDIDATE_ENABLED_CONTRACT')
    require(json.loads((control_root/'success/contract.json').read_bytes()).get('borrow_invalidate') is False,
            'CONTROL_DISABLED_CONTRACT')
    control = evidence.native_calls(control_root/'success/native/mesen.log')
    with patch.object(accepted,'audit_rom',audit_rom):
        report = accepted.collect_suite(root,seal)
    costs = {case:profile(root/case) for case in capture.CASES}
    comparison = evidence.compare_calls(costs['success']['calls'],control)
    evidence.verify_timing(report,baseline)
    case_timings = evidence.compare_case_timings(report,native_baseline)
    require(capture.verify_capture(root,seal) == before,'RAW_CAPTURE_CHANGED')
    require(capture.verify_capture(BASELINE,evidence.BASE_SEAL) == before_base,'BASELINE_CAPTURE_CHANGED')
    require(evidence.verify_control(control_root,control_digest) == control_before,'CONTROL_CAPTURE_CHANGED')
    report.update(classification='BYOR_MOTU_BORROW_INVALIDATE_PASS',starting_commit=STARTING_COMMIT,
        baseline_ref_epoch2=baseline['candidate_epoch2'],baseline_ref_epoch3=baseline['candidate_epoch3'],
        accepted_ref_receipt_sha256=evidence.BASE_RECEIPT_SHA256,borrow_invalidate=costs,
        invalidate_cpu_comparison=comparison,accepted_ref_capture_evidence=before_base,
        all_case_timing_nonregression=case_timings,
        control_capture_evidence=control_before,control_root=control_root.relative_to(capture.ROOT).as_posix(),
        raw_candidate_baseline_and_control_unchanged=True)
    (root/'borrow-invalidate-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--suite',action='store_true'); parser.add_argument('--collect-suite',action='store_true')
    parser.add_argument('--build-only',action='store_true'); parser.add_argument('--control',action='store_true')
    parser.add_argument('--case',choices=capture.CASES,default='success')
    parser.add_argument('--provenance-sha256'); parser.add_argument('--raw-manifest-sha256')
    parser.add_argument('--control-root',type=Path); parser.add_argument('--control-manifest-sha256')
    args = parser.parse_args(); root = args.output.resolve()
    require(bool(args.provenance_sha256) == bool(args.raw_manifest_sha256),'BOTH_CAPTURE_PINS_REQUIRED')
    require(not args.provenance_sha256 or args.collect_suite,'CAPTURE_PINS_REQUIRE_COLLECTION')
    require(bool(args.control_root) == bool(args.control_manifest_sha256),'BOTH_CONTROL_PINS_REQUIRED')
    if args.collect_suite:
        require(bool(args.provenance_sha256) and bool(args.control_root),'EXPLICIT_TRUSTED_PINS_REQUIRED')
        report = collect_suite(root,capture.CaptureSeal(args.provenance_sha256,args.raw_manifest_sha256),
                               args.control_root.resolve(),args.control_manifest_sha256)
        print(report['classification'],report['observed_fields'],report['verified_rgb555_pixels'],flush=True)
        return
    require(not root.exists(),'OUTPUT_MUST_BE_NEW')
    require(root.is_relative_to(capture.ROOT.resolve()),'OUTPUT_MUST_BE_IN_REPOSITORY')
    require(not args.control or (not args.suite and args.case == 'success'),'CONTROL_IS_SINGLE_SUCCESS')
    require(not args.control_root or args.suite,'CONTROL_PINS_REQUIRE_SUITE_OR_COLLECTION')
    require(not args.suite or args.build_only or args.control_root,'SUITE_REQUIRES_TRUSTED_CONTROL')
    evidence.load_baseline(); capture.verify_capture(BASELINE,evidence.BASE_SEAL)
    if args.control_root: evidence.verify_control(args.control_root.resolve(),args.control_manifest_sha256)
    if not args.build_only: accepted.accepted.accepted.accepted.q8.configure_capture_runtime(root)
    for case in capture.CASES if args.suite else (args.case,):
        print('BORROW INVALIDATE CASE',case,'CONTROL' if args.control else 'CANDIDATE',flush=True)
        child = root/case; build(child,args.control)
        if args.build_only: continue
        q8 = accepted.accepted.accepted.accepted.q8
        with patch.object(q8,'audit_rom',ACCEPTED_AUDIT if args.control else audit_rom),patch.object(q8,'observer',observer):
            q8.run_case(child,case)
        accepted.accepted.accepted.accepted.profile(child,required=case == 'success')
        accepted.accepted.profile(child); accepted.profile(child); profile(child)
    if args.control and not args.build_only:
        digest = evidence.seal_control(root)
        print('CONTROL MANIFEST PIN',digest,flush=True)
        print('BORROW_INVALIDATE_CONTROL_PASS',flush=True)
    if args.suite and not args.build_only:
        seal = capture.seal_native_capture(root)
        print('CAPTURE PINS',seal.provenance_sha256,seal.raw_manifest_sha256,flush=True)
        report = collect_suite(root,seal,args.control_root.resolve(),args.control_manifest_sha256)
        print(report['classification'],report['observed_fields'],report['verified_rgb555_pixels'],flush=True)


if __name__ == '__main__':
    main()
