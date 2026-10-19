"""Bounded register-indexed READY validator over accepted f9fb79f."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import fused_capture_evidence as capture
import m4_fused_coverage_native as accepted
import ready_validate as rv
import ready_validate_evidence as evidence

BASELINE = evidence.BASELINE
BASE = BASELINE / 'success/native'
BASE_SHA = evidence.BASE_ROM_SHA256
STARTING_COMMIT = 'f9fb79f0b7fae45f754e18af3eff9b0456d77740'
ACCEPTED_AUDIT = accepted.audit_rom
PATCH_PC = 0x39A1F7
CONTINUE_PC = 0x39A223
PATCH_BEFORE = bytes.fromhex('a670bf00c042')
PATCH_AFTER = bytes.fromhex('4c00a8eaeaea')
# Independent 65816 encoding: BPL +8, BCC +5, BCC -38, and both fixed JMPs.
LITERAL_HEX = ('a20000bf00c0421008a9008086704c3fa329ff3fc90003900586704c3fa3'
               '9f00c042e8e8e0000890daa2fe07a900088570c900084c23a2')


def require(ok, code):
    evidence.require(ok, code)


def _sizing(lines):
    # The inherited size-only lexer lacks DEY. Actual opcode bytes remain
    # independently checked; this does not rewrite the assembled source.
    return [' iny' if line.strip() == 'dey' else line for line in lines]


def audit_rom(rom, native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    require(capture.sha(BASE / 'bor.sfc') == BASE_SHA, 'BASE_ROM_DIGEST')
    original = (BASE / 'bor.sfc').read_bytes()
    inherited = ACCEPTED_AUDIT(original, BASE)
    old = (BASE / 'publisher.pasm').read_text().splitlines()
    lines = (native / 'publisher.pasm').read_text().splitlines()
    require(lines == rv.transform(old), 'EXACT_SOURCE_TRANSFORM')
    sy = symbols(native / 'publisher.sym'); oldsy = symbols(BASE / 'publisher.sym')
    require(all(sy.get(name) == pc for name, pc in oldsy.items()), 'ORIGINAL_SYMBOL_MOVED')
    expected_symbols = dict(RvValidate=0x39A800, RvValidateLoop=0x39A803,
        RvUntagged=0x39A811, RvValid=0x39A81E,
        RvCodeEnd=0x39A837, RvContinue=CONTINUE_PC)
    require(all(sy.get(name) == pc for name, pc in expected_symbols.items()),
            'INDEPENDENT_HELPER_LAYOUT')
    require(sy['NbValidate'] == PATCH_PC and sy['RvCodeEnd'] < rv.CODE_LIMIT,
            'HELPER_PLACEMENT')
    start, end = offset(sy['RvValidate']), offset(sy['RvCodeEnd'])
    require(not any(original[start:end]), 'HELPER_GAP_NOT_ZERO')
    compiled = (native / 'publisher.bin').read_bytes(); literal = bytes.fromhex(LITERAL_HEX)
    require(len(literal) == end - start == 55 and compiled[start:end] == literal,
            'INDEPENDENT_HELPER_OPCODES')
    at = offset(PATCH_PC)
    require(original[at:at + 6] == PATCH_BEFORE and compiled[at:at + 6] == PATCH_AFTER,
            'INDEPENDENT_DISPATCH_OPCODES')
    expected = bytearray(original); expected[at:at + 6] = PATCH_AFTER
    expected[start:end] = literal
    require(bytes(rom) == bytes(expected), 'UNAUTHORIZED_ROM_BYTE')
    branches = audit_branches(_sizing(lines), sy, compiled)
    inherited['ready_validate'] = dict(status='PASS', baseline_sha256=BASE_SHA,
        patch_pc=PATCH_PC, patch_bytes=6, continuation_pc=CONTINUE_PC,
        code_start=sy['RvValidate'], code_end=sy['RvCodeEnd'], code_bytes=55,
        branch_sites=branches, all_original_symbols_identical=True,
        all_original_guards_retained=True, no_new_memory_or_queue_capacity=True,
        allowed_rom_byte_ranges=[[at, at + 6], [start, end]])
    return inherited


def build(folder, disabled=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract = accepted.build(folder)
    native = folder / 'native'
    require(capture.sha(native / 'bor.sfc') == BASE_SHA, 'BASE_REBUILD_IDENTITY')
    if disabled:
        return contract
    lines = (native / 'publisher.pasm').read_text().splitlines()
    (native / 'publisher.pasm').write_text('\n'.join(rv.transform(lines)) + '\n')
    command = [os.environ.get('DOTNET_EXE', 'C:/Users/chad/.dotnet/dotnet.exe'),
        os.environ.get('POPPY_DLL', 'E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
        str(native / 'publisher.pasm'), '--output', str(native / 'publisher.bin'),
        '--symbols', str(native / 'publisher.sym'), '--no-pansy']
    result = subprocess.run(command, capture_output=True, text=True)
    (native / 'ready-validate-build.log').write_text(result.stdout + result.stderr)
    require(result.returncode == 0, 'POPPY_ASSEMBLY')
    sy = symbols(native / 'publisher.sym'); compiled = (native / 'publisher.bin').read_bytes()
    at = offset(PATCH_PC); start = offset(sy['RvValidate']); end = offset(sy['RvCodeEnd'])
    rom = bytearray((native / 'bor.sfc').read_bytes())
    rom[at:at + 6] = compiled[at:at + 6]; rom[start:end] = compiled[start:end]
    audit = audit_rom(rom, native)
    (native / 'bor.sfc').write_bytes(rom)
    contract['native_symbols'].update(sy)
    contract.update(ready_validate=True, eight_pair_audit=audit)
    (folder / 'contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    return contract


def observer(script, contract):
    accepted.observer(script, contract)
    sy = contract['native_symbols']
    with script.open('a') as stream:
        stream.write("""
local rvStart=nil;local rvBefore=nil
local function rvRegs(s)
 return s['cpu.a']..'|'..s['cpu.x']..'|'..s['cpu.y']..'|'..s['cpu.d']..'|'..s['cpu.dbr']..'|'..s['cpu.sp']..'|'..s['cpu.ps']..'|'..nbWord(0x3470)
end
""")
        def cb(pc, body):
            stream.write(f'emu.addMemoryCallback(function() {body} end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb(sy['RvValidate'], "local s=emu.getState();if rvStart then nbLog('FAULT','RV_NESTED')end;rvStart=s['masterClock'];rvBefore=s;nbLog('RV_ENTRY',nbTxn..'|'..rvRegs(s)..'|'..cpDump(0x42c000,2048))")
        cb(sy['RvContinue'], "if rvStart then local s=emu.getState();for _,k in ipairs({'cpu.y','cpu.d','cpu.dbr','cpu.sp'})do if s[k]~=rvBefore[k]then nbLog('FAULT','RV_CONTEXT:'..k)end end;if s['cpu.a']~=2048 or s['cpu.x']~=2046 or nbWord(0x3470)~=2048 or s['cpu.ps']~=((rvBefore['cpu.ps']&0x7c)|3)then nbLog('FAULT','RV_EXIT_ABI')end;nbLog('RV_SCAN',nbTxn..'|'..(s['masterClock']-rvStart)..'|'..rvRegs(s)..'|'..cpDump(0x42c000,2048));rvStart=nil;rvBefore=nil end")
        cb(sy['NbAbort'], "if rvStart then nbLog('FAULT','RV_UNEXPECTED_REJECTION')end")
        for cpu in ('snes', 'sa1'):
            stream.write("emu.addMemoryCallback(function(a,v)if rvStart then local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];local off=a&0xffff;local x=s['cpu.x'];if '" + cpu + "'~='snes' or pc~=0x39a822 or x%2~=0 or x>=2048 or (off~=0xc000+x and off~=0xc001+x)then nbLog('FAULT','RV_MAP_WRITE_OWNER:" + cpu + "|'..a..'|'..pc)end end end,emu.callbackType.write,0x2c000,0x2c7ff,emu.cpuType." + cpu + ",emu.memType.snesSaveRam)\n")


def profile(folder):
    path = folder / 'native/mesen.log'
    result = dict(classification='READY_VALIDATE_PROFILE_PASS',
        rom_sha256=capture.sha(folder / 'native/bor.sfc'),
        scans=evidence.native_scans(path), ready_intervals=evidence.ready_intervals(path),
        boundaries='Last NbQueueDrainDone callback through original NbReady callback; helper entry through original source-epoch-check continuation.')
    (folder / 'ready-validate-profile.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def collect_suite(root, seal):
    baseline = evidence.load_baseline()
    before_control = capture.verify_capture(BASELINE)
    before = capture.verify_capture(root, seal)
    initial_sram = evidence.runtime_initial_sram(root)
    controls = {case: evidence.ready_intervals(BASELINE / case / 'native/mesen.log')
                for case in capture.CASES}
    expected_scans = {case: evidence.ready_successes(BASELINE / case / 'native/mesen.log')
                      for case in capture.CASES}
    with patch.object(accepted, 'audit_rom', audit_rom):
        report = accepted.collect_suite(root, seal)
    costs = {case: profile(root / case) for case in capture.CASES}
    require(all(set(costs[case]['scans']) == set(expected_scans[case])
                for case in capture.CASES), 'BASELINE_SCAN_TRANSACTION_DRIFT')
    comparisons = {case: evidence.compare_intervals(costs[case]['ready_intervals'], controls[case])
                   for case in capture.CASES}
    evidence.verify_timing(report, baseline)
    require(comparisons['success']['3']['after_clocks'] * 4 <=
            comparisons['success']['3']['before_clocks'] * 3, 'READY_CPU_GAIN_BELOW_25_PERCENT')
    for case in capture.CASES:
        for name in accepted.accepted.expected_checkpoints(case):
            current = (root / case / 'native' / name).read_bytes()
            old = (BASELINE / case / 'native' / name).read_bytes()
            if name.endswith('-vram.bin'):
                if name in ('initial-vram.bin', 'handoff-vram.bin'):
                    continue
                require(len(current) == len(old) == 65536 and current[61440:] == old[61440:],
                        case + ':BASELINE_MAP_DRIFT:' + name)
                slots = {int.from_bytes(current[i:i + 2], 'little') & 0x3fff
                         for i in range(61440, 65536, 2)}
                require(all(k < 768 and current[k * 64:(k + 1) * 64] == old[k * 64:(k + 1) * 64]
                    and current[49152 + k * 16:49152 + (k + 1) * 16] == old[49152 + k * 16:49152 + (k + 1) * 16]
                    for k in slots), case + ':BASELINE_REFERENCED_CHR_DRIFT:' + name)
            else:
                require(current == old, case + ':BASELINE_STATE_DRIFT:' + name)
    require(capture.verify_capture(root, seal) == before, 'RAW_CAPTURE_CHANGED')
    require(capture.verify_capture(BASELINE) == before_control, 'BASELINE_CAPTURE_CHANGED')
    require(evidence.runtime_initial_sram(root) == initial_sram, 'INITIAL_SRAM_CHANGED')
    report.update(classification='BYOR_MOTU_READY_VALIDATE_PASS', starting_commit=STARTING_COMMIT,
        baseline_fused_epoch2=baseline['candidate_epoch2'], baseline_fused_epoch3=baseline['candidate_epoch3'],
        accepted_fused_receipt_sha256=evidence.BASE_RECEIPT_SHA256,
        ready_validation=costs, ready_interval_comparison=comparisons,
        expected_scan_transactions={case: sorted(rows) for case, rows in expected_scans.items()},
        accepted_fused_capture_evidence=before_control, raw_and_baseline_unchanged=True,
        capture_initial_sram=initial_sram)
    (root / 'ready-validate-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--suite', action='store_true'); parser.add_argument('--collect-suite', action='store_true')
    parser.add_argument('--build-only', action='store_true'); parser.add_argument('--disabled', action='store_true')
    parser.add_argument('--case', choices=capture.CASES, default='success')
    parser.add_argument('--provenance-sha256'); parser.add_argument('--raw-manifest-sha256')
    args = parser.parse_args(); root = args.output.resolve()
    require(bool(args.provenance_sha256) == bool(args.raw_manifest_sha256), 'BOTH_CAPTURE_PINS_REQUIRED')
    require(not args.provenance_sha256 or args.collect_suite, 'CAPTURE_PINS_REQUIRE_COLLECTION')
    if args.collect_suite:
        require(bool(args.provenance_sha256), 'EXPLICIT_TRUSTED_CAPTURE_PINS_REQUIRED')
        report = collect_suite(root, capture.CaptureSeal(args.provenance_sha256, args.raw_manifest_sha256))
        print(report['classification'], report['observed_fields'], report['verified_rgb555_pixels'], flush=True)
        return
    require(not root.exists(), 'OUTPUT_MUST_BE_NEW')
    require(not args.disabled or args.build_only, 'DISABLED_IS_BUILD_CONTROL')
    require(root.is_relative_to(capture.ROOT.resolve()), 'OUTPUT_MUST_BE_IN_REPOSITORY')
    evidence.load_baseline(); capture.verify_capture(BASELINE)
    if not args.build_only:
        accepted.accepted.q8.configure_capture_runtime(root)
    for case in capture.CASES if args.suite else (args.case,):
        print('READY VALIDATE CASE', case, flush=True)
        child = root / case; build(child, args.disabled)
        if args.build_only:
            continue
        with patch.object(accepted.accepted.q8, 'audit_rom', audit_rom), \
             patch.object(accepted.accepted.q8, 'observer', observer):
            accepted.accepted.q8.run_case(child, case)
        accepted.accepted.profile(child, required=case == 'success')
        profile(child)
    if args.suite and not args.build_only:
        seal = capture.seal_native_capture(root)
        print('CAPTURE PINS', seal.provenance_sha256, seal.raw_manifest_sha256, flush=True)
        report = collect_suite(root, seal)
        print(report['classification'], report['observed_fields'], report['verified_rgb555_pixels'], flush=True)


if __name__ == '__main__':
    main()
