"""Bounded exact boolean row scanner over the accepted a7a240b renderer."""
from __future__ import annotations
import argparse,json,os,subprocess
from pathlib import Path
from unittest.mock import patch

import m4_exact_coverage_native as accepted
import coverage_fused as fused
import fused_capture_evidence as capture
from fused_timing_baseline import RECEIPT_SHA256, load_timing_baseline

BASELINE=Path('out/byor-motu-exact-coverage-v1')
BASE=BASELINE/'success/native'
BASE_SHA='0ad890b7390e83e593596e456469fece2ab37ab9378ac733c80b581a56841edd'
STARTING_COMMIT='a7a240b110df678a9968ed4d4be8ac1973d9fa3a'
ACCEPTED_AUDIT=accepted.audit_rom
PROFILE_SHA='c5d7de2871711ada9a59798c97661136b424cd31a0d1a7c272a4a4cd47b8fc68'
RIGHT_PROFILE_SHA='0fe1c74c7d330a2b703d3ce27647de0714c111d3136b9d0aa054bb217cdb17ff'
# Independent 65816 encoding, including all five branch displacements.
# OnlineRowPointers remains $39C000; existing code/symbols may not move.
LITERAL_HEX=(
    '2000c0a900008558a900008532a556c546b01ca654e220bf0000f4c220'
    '29ff0049ff008532eb0532a0000037088532e658a532d022a556300e'
    'a5081865488508a50a690000850ae656e654a558c9080090b6a90000'
    '8003a9010060')


def require(ok,code):
    if not ok:raise ValueError('FUSED_COVERAGE:'+code)


def load_accepted_profile(case='success'):
    require(case in accepted.q8.CASES,'UNKNOWN_PROFILE_CASE')
    path=BASELINE/case/'exact-coverage-profile.json'
    require(path.is_file(),'ACCEPTED_PROFILE_MISSING')
    require(accepted.q8.sha(path)==(RIGHT_PROFILE_SHA if case=='right' else PROFILE_SHA),'ACCEPTED_PROFILE_DIGEST')
    result=json.loads(path.read_text())
    require(result['rom_sha256']==BASE_SHA,'ACCEPTED_PROFILE_ROM')
    return result


def compare_row_profiles(current,baseline):
    result=accepted.compare_profiles(current,baseline)
    for txn in baseline['transactions']:
        require([x['row_counter'] for x in current['transactions'][txn]['verdicts']]==
                [x['row_counter'] for x in baseline['transactions'][txn]['verdicts']],
                'EXACT_ROW_VISIT_DRIFT:'+txn)
    return result


def verify_timing(report,baseline):
    require(report['epoch2']['fields']<=baseline['candidate_epoch2']['fields'] and
            report['epoch2']['master_clocks']<=baseline['candidate_epoch2']['master_clocks'],
            'ACCEPTED_EPOCH2_REGRESSION')
    require(report['epoch3']['fields']<baseline['candidate_epoch3']['fields'] and
            report['epoch3']['master_clocks']<baseline['candidate_epoch3']['master_clocks'],
            'ACCEPTED_EPOCH3_NOT_IMPROVED')


def audit_rom(rom,native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_rect_map_audit import statements
    from m4_restore_spill_native import audit_branches
    require(accepted.q8.sha(BASE/'bor.sfc')==BASE_SHA,'ACCEPTED_ROM_HASH')
    original=(BASE/'bor.sfc').read_bytes()
    inherited=ACCEPTED_AUDIT(original,BASE)
    old=(BASE/'publisher.pasm').read_text().splitlines()
    lines=(native/'publisher.pasm').read_text().splitlines()
    require(lines==fused.transform(old),'EXACT_SOURCE_TRANSFORM')
    sy=symbols(native/'publisher.sym');oldsy=symbols(BASE/'publisher.sym')
    require(all(sy.get(k)==v for k,v in oldsy.items()),'ORIGINAL_SYMBOL_MOVED')
    require(sy['FcCoverage']==fused.CODE_START and sy['FcCodeEnd']<fused.CODE_LIMIT,
            'HELPER_LAYOUT')
    require([sy[name] for name in ('FcCoverageRow','FcMaskDone','FcStepNegative','FcCovered','FcHit','FcCodeEnd')]==
            [0x39A748,0x39A76F,0x39A787,0x39A797,0x39A79A,0x39A79B],
            'INDEPENDENT_LABEL_LAYOUT')
    start,end=offset(sy['FcCoverage']),offset(sy['FcCodeEnd'])
    require(not any(original[start:end]),'HELPER_GAP_NOT_ZERO')
    literal=bytes.fromhex(LITERAL_HEX)
    require(bool(literal) and len(literal)==end-start,'INDEPENDENT_LITERAL_LENGTH')
    compiled=(native/'publisher.bin').read_bytes()
    require(compiled[start:end]==literal,'INDEPENDENT_HELPER_OPCODES')
    pc=accepted.callsite(old,oldsy);at=offset(pc)
    require(original[at:at+3]==bytes((0x20,oldsy['EcCoverage']&255,oldsy['EcCoverage']>>8&255)),
            'ACCEPTED_BOOLEAN_CALL_BYTES')
    replacement=bytes((0x20,sy['FcCoverage']&255,sy['FcCoverage']>>8&255))
    require(compiled[at:at+3]==replacement,'NEW_BOOLEAN_CALL_BYTES')
    expected=bytearray(original);expected[at+1:at+3]=replacement[1:];expected[start:end]=literal
    require(bytes(rom)==expected,'UNAUTHORIZED_ROM_BYTE')
    for p,n,s in statements([' iny' if x.strip()=='dey' else x for x in old],oldsy).values():
        off=offset(p)
        require(compiled[off:off+n]==expected[off:off+n],'ORIGINAL_INSTRUCTION_CHANGED:'+hex(p)+':'+s)
    branches=audit_branches([' iny' if x.strip()=='dey' else x for x in lines],sy,compiled)
    inherited['fused_coverage']=dict(status='PASS',baseline_sha256=BASE_SHA,
        callsite=pc,old_target=oldsy['EcCoverage'],new_target=sy['FcCoverage'],
        code_start=sy['FcCoverage'],code_end=sy['FcCodeEnd'],code_bytes=len(literal),
        branch_sites=branches,all_original_symbols_identical=True,
        old_helpers_identical=True,no_new_memory_or_queue_capacity=True)
    return inherited


def build(folder,disabled=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract=accepted.build(folder)
    native=folder/'native'
    require(accepted.q8.sha(native/'bor.sfc')==BASE_SHA,'ACCEPTED_REBUILD_IDENTITY')
    if disabled:return contract
    lines=(native/'publisher.pasm').read_text().splitlines()
    (native/'publisher.pasm').write_text('\n'.join(fused.transform(lines))+'\n')
    command=[os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'),
             os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
             str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),
             '--symbols',str(native/'publisher.sym'),'--no-pansy']
    result=subprocess.run(command,capture_output=True,text=True)
    (native/'fused-coverage-build.log').write_text(result.stdout+result.stderr)
    require(result.returncode==0,'POPPY_ASSEMBLY')
    sy=symbols(native/'publisher.sym');pc=accepted.callsite(lines,contract['native_symbols'])
    at=offset(pc);start=offset(sy['FcCoverage']);end=offset(sy['FcCodeEnd'])
    compiled=(native/'publisher.bin').read_bytes();rom=bytearray((native/'bor.sfc').read_bytes())
    rom[at+1:at+3]=compiled[at+1:at+3];rom[start:end]=compiled[start:end]
    audit=audit_rom(rom,native)
    (native/'bor.sfc').write_bytes(rom)
    contract['native_symbols'].update(sy)
    contract.update(fused_coverage=True,eight_pair_audit=audit)
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    return contract


def observer(script,contract):
    # All accepted observers stay installed, including mark boundaries. The
    # old EcCoverage is retained but no longer entered by the boolean caller.
    accepted.observer(script,contract)
    sy=contract['native_symbols']
    with script.open('a') as stream:
        def cb(pc,body):
            stream.write(f'emu.addMemoryCallback(function() {body} end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb(sy['FcCoverage'],"if nbTxn>=0 and nbWord(0x42d674)==1 and nbWord(0x42d600)==1 then if ecStart then nbLog('FAULT','FC_COVER_NESTED')end;ecStart=emu.getState()['masterClock'];ecIndex=nbWord(0x3418)end")
        cb(sy['FcHit'],"if ecStart then local s=emu.getState();nbLog('EC_COVER',nbTxn..'|'..ecIndex..'|'..(s['masterClock']-ecStart)..'|'..s['cpu.a']..'|'..nbWord(0x3458));ecStart=nil end")


def collect_suite(root,seal=capture.RETAINED_SEAL):
    # Retain all original eight-case source/pixel/allocation/DMA certifiers,
    # but reject incomplete or unsealed evidence before any derived writes.
    baseline=load_timing_baseline()
    evidence=capture.verify_capture(root,seal)
    controls={case:load_accepted_profile(case) for case in accepted.q8.CASES}
    for case in accepted.q8.CASES:
        accepted.require_checkpoint_inventory(BASELINE/case/'native',case)
    with patch.object(accepted,'audit_rom',audit_rom):report=accepted.collect_suite(root)
    for case in accepted.q8.CASES:
        for name in accepted.expected_checkpoints(case):
            current_bytes=(root/case/'native'/name).read_bytes()
            old_bytes=(BASELINE/case/'native'/name).read_bytes()
            if name.endswith('-vram.bin'):
                if name in ('initial-vram.bin','handoff-vram.bin'):continue
                require(len(current_bytes)==len(old_bytes)==65536 and current_bytes[61440:]==old_bytes[61440:],
                        case+':ACCEPTED_MAP_DRIFT:'+name)
                slots={int.from_bytes(current_bytes[i:i+2],'little')&0x3fff for i in range(61440,65536,2)}
                require(all(k<768 and current_bytes[64*k:64*(k+1)]==old_bytes[64*k:64*(k+1)] and
                            current_bytes[49152+16*k:49152+16*(k+1)]==old_bytes[49152+16*k:49152+16*(k+1)]
                            for k in slots),case+':ACCEPTED_REFERENCED_CHR_DRIFT:'+name)
            else:
                require(current_bytes==old_bytes,case+':ACCEPTED_STATE_DRIFT:'+name)
    verify_timing(report,baseline)
    case_coverage={case:compare_row_profiles(
        json.loads((root/case/'exact-coverage-profile.json').read_text()),controls[case])
        for case in accepted.q8.CASES}
    after=capture.verify_capture(root,seal)
    require(after==evidence,'RAW_CAPTURE_CHANGED_DURING_CERTIFICATION')
    require(report['observed_fields']==evidence['observed_fields'],'FIELD_TOTAL_DRIFT')
    report.update(classification='BYOR_MOTU_FUSED_COVERAGE_PASS',starting_commit=STARTING_COMMIT,
        baseline_exact_epoch2=baseline['candidate_epoch2'],baseline_exact_epoch3=baseline['candidate_epoch3'],
        fused_coverage=case_coverage['success'],case_coverage=case_coverage,
        accepted_profile_sha256=PROFILE_SHA,accepted_right_profile_sha256=RIGHT_PROFILE_SHA,
        accepted_timing_receipt_sha256=RECEIPT_SHA256,capture_evidence=evidence,
        raw_capture_unchanged_after_certification=True)
    (root/'fused-coverage-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--suite',action='store_true');parser.add_argument('--collect-suite',action='store_true')
    parser.add_argument('--build-only',action='store_true');parser.add_argument('--disabled',action='store_true')
    parser.add_argument('--case',choices=accepted.q8.CASES,default='success')
    parser.add_argument('--provenance-sha256',help='trusted capture-provenance digest for re-collection')
    parser.add_argument('--raw-manifest-sha256',help='trusted raw-input manifest digest for re-collection')
    a=parser.parse_args();root=a.output.resolve()
    require(bool(a.provenance_sha256)==bool(a.raw_manifest_sha256),'BOTH_CAPTURE_PINS_REQUIRED')
    require(not a.provenance_sha256 or a.collect_suite,'CAPTURE_PINS_REQUIRE_COLLECTION')
    if a.collect_suite:
        seal=(capture.CaptureSeal(a.provenance_sha256,a.raw_manifest_sha256)
              if a.provenance_sha256 else capture.RETAINED_SEAL)
        result=collect_suite(root,seal);print(result['classification'],result['observed_fields'],result['verified_rgb555_pixels'],flush=True);return
    require(not root.exists(),'OUTPUT_MUST_BE_NEW')
    require(not a.disabled or a.build_only,'DISABLED_IS_BUILD_CONTROL')
    if not a.build_only:accepted.q8.configure_capture_runtime(root)
    for case in accepted.q8.CASES if a.suite else (a.case,):
        print('FUSED COVERAGE CASE',case,flush=True)
        child=root/case;build(child,a.disabled)
        if a.build_only:continue
        with patch.object(accepted.q8,'audit_rom',audit_rom),patch.object(accepted.q8,'observer',observer):
            accepted.q8.run_case(child,case)
        accepted.profile(child,required=case=='success')
    if a.suite and not a.build_only:
        seal=capture.seal_native_capture(root)
        print('CAPTURE PINS',seal.provenance_sha256,seal.raw_manifest_sha256,flush=True)
        result=collect_suite(root,seal);print(result['classification'],result['observed_fields'],result['verified_rgb555_pixels'],flush=True)


if __name__=='__main__':main()
