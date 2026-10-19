"""Bounded bank-local reference rebuild over accepted d5803ef."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import fused_capture_evidence as capture
import m4_ready_validate_native as accepted
import ref_rebuild as overlay
import ref_rebuild_evidence as evidence

BASELINE = evidence.BASELINE
BASE = BASELINE / 'success/native'
STARTING_COMMIT = 'd5803ef7d9ede527a9eeb8f47a8779072fd92775'
ACCEPTED_AUDIT = accepted.audit_rom
PATCH_PC = 0x39A279
CONTINUE_PC = 0x39A2A9
PATCH_BEFORE = bytes.fromhex('a20000')
PATCH_AFTER = bytes.fromhex('4c00a9')
# Independently encoded 65816 blocks. Each BCS skips the BRL by +3;
# signed BRL displacements are -184 ($FF48) and -232 ($FF18).
LITERAL_HEX = ('8bf44242ababa20000' + 'bd00d02900809d00d0e8e8' * 16 +
    'e00006b0038248ffa00000' + 'b900c00aaabd00d01a9d00d0c8c8' * 16 +
    'c00008b0038218ffabc000084ca9a2')
CLEAR_STORES = tuple(0x39A912 + 11 * i for i in range(16))
PUBLISH_STORES = tuple(0x39A9D0 + 14 * i for i in range(16))


def require(ok, code):
    evidence.require(ok, code)


def audit_rom(rom, native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    require(capture.sha(BASE / 'bor.sfc') == evidence.BASE_ROM_SHA256, 'BASE_ROM_DIGEST')
    original = (BASE / 'bor.sfc').read_bytes()
    inherited = ACCEPTED_AUDIT(original, BASE)
    old = (BASE / 'publisher.pasm').read_text().splitlines()
    lines = (native / 'publisher.pasm').read_text().splitlines()
    require(lines == overlay.transform(old), 'EXACT_SOURCE_TRANSFORM')
    sy = symbols(native / 'publisher.sym'); oldsy = symbols(BASE / 'publisher.sym')
    require(all(sy.get(name) == pc for name, pc in oldsy.items()), 'ORIGINAL_SYMBOL_MOVED')
    fixed = dict(RfRebuild=0x39A900, RfClearLoop=0x39A909, RfClearDone=0x39A9C1,
                 RfPublishLoop=0x39A9C4, RfPublishDone=0x39AAAC,
                 RfContinue=CONTINUE_PC, RfCodeEnd=0x39AAB3)
    require(all(sy.get(name) == pc for name, pc in fixed.items()), 'INDEPENDENT_HELPER_LAYOUT')
    require(sy['RfCodeEnd'] < overlay.CODE_LIMIT, 'HELPER_PLACEMENT')
    start, end = offset(sy['RfRebuild']), offset(sy['RfCodeEnd'])
    literal = bytes.fromhex(LITERAL_HEX); compiled = (native / 'publisher.bin').read_bytes()
    require(not any(original[start:end]), 'HELPER_GAP_NOT_ZERO')
    require(len(literal) == end - start == 435 and compiled[start:end] == literal,
            'INDEPENDENT_HELPER_OPCODES')
    at = offset(PATCH_PC)
    require(original[at:at + 3] == PATCH_BEFORE and compiled[at:at + 3] == PATCH_AFTER,
            'INDEPENDENT_DISPATCH_OPCODES')
    expected = bytearray(original); expected[at:at + 3] = PATCH_AFTER; expected[start:end] = literal
    require(bytes(rom) == bytes(expected), 'UNAUTHORIZED_ROM_BYTE')
    branches = audit_branches(accepted._sizing(lines), sy, compiled)
    inherited['ref_rebuild'] = dict(status='PASS', baseline_sha256=evidence.BASE_ROM_SHA256,
        patch_pc=PATCH_PC, patch_bytes=3, continuation_pc=CONTINUE_PC,
        code_start=sy['RfRebuild'], code_end=sy['RfCodeEnd'], code_bytes=435,
        branch_sites=branches, all_original_symbols_identical=True,
        all_original_guards_retained=True, no_new_memory_or_queue_capacity=True,
        allowed_rom_byte_ranges=[[at, at + 3], [start, end]])
    return inherited


def build(folder, disabled=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract = accepted.build(folder)
    native = folder / 'native'
    require(capture.sha(native / 'bor.sfc') == evidence.BASE_ROM_SHA256, 'BASE_REBUILD_IDENTITY')
    if disabled:
        return contract
    lines = (native / 'publisher.pasm').read_text().splitlines()
    (native / 'publisher.pasm').write_text('\n'.join(overlay.transform(lines)) + '\n')
    command = [os.environ.get('DOTNET_EXE', 'C:/Users/chad/.dotnet/dotnet.exe'),
        os.environ.get('POPPY_DLL', 'E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
        str(native / 'publisher.pasm'), '--output', str(native / 'publisher.bin'),
        '--symbols', str(native / 'publisher.sym'), '--no-pansy']
    result = subprocess.run(command, capture_output=True, text=True)
    (native / 'ref-rebuild-build.log').write_text(result.stdout + result.stderr)
    require(result.returncode == 0, 'POPPY_ASSEMBLY')
    sy = symbols(native / 'publisher.sym'); compiled = (native / 'publisher.bin').read_bytes()
    at = offset(PATCH_PC); start, end = offset(sy['RfRebuild']), offset(sy['RfCodeEnd'])
    rom = bytearray((native / 'bor.sfc').read_bytes())
    rom[at:at + 3] = compiled[at:at + 3]; rom[start:end] = compiled[start:end]
    audit = audit_rom(rom, native)
    (native / 'bor.sfc').write_bytes(rom)
    contract['native_symbols'].update(sy)
    contract.update(ref_rebuild=True, eight_pair_audit=audit)
    (folder / 'contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    return contract


def observer(script, contract):
    accepted.observer(script, contract)
    sy = contract['native_symbols']
    stores = ','.join('[' + str(pc) + ']=true' for pc in CLEAR_STORES + PUBLISH_STORES)
    with script.open('a') as stream:
        stream.write("""
local rfStart=nil;local rfTrace=nil
local function rfRegs(s)
 return s['cpu.a']..'|'..s['cpu.x']..'|'..s['cpu.y']..'|'..s['cpu.d']..'|'..s['cpu.dbr']..'|'..s['cpu.sp']..'|'..s['cpu.ps']..'|'..nbWord(0x3470)
end
""")
        stream.write('local rfStores={' + stores + '}\n')
        def cb(pc, body):
            stream.write(f'emu.addMemoryCallback(function() {body} end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        cb(sy['RfRebuild'], "if rfStart or nbWord(0x42d600)~=4 then nbLog('FAULT','RF_ENTRY_OWNER')end;local s=emu.getState();rfStart=s['masterClock'];rfTrace={};nbLog('RF_ENTRY',nbTxn..'|'..rfRegs(s)..'|'..cpDump(0x42d000,1536)..'|'..cpDump(0x42c000,2048))")
        cb(sy['RfContinue'], "if not rfStart then nbLog('FAULT','RF_EXIT_WITHOUT_ENTRY')else local s=emu.getState();nbLog('RF_SCAN',nbTxn..'|'..(s['masterClock']-rfStart)..'|'..rfRegs(s)..'|'..cpDump(0x42d000,1536)..'|'..cpDump(0x42c000,2048)..'|'..table.concat(rfTrace));rfStart=nil;rfTrace=nil end")
        for cpu in ('snes', 'sa1'):
            stream.write("emu.addMemoryCallback(function(a,v)if rfStart then local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];if '" + cpu + "'~='snes' or not rfStores[pc] then nbLog('FAULT','RF_REF_WRITE_OWNER:" + cpu + "|'..a..'|'..pc)end;rfTrace[#rfTrace+1]=string.format('%04x%02x',a&0xffff,v)end end,emu.callbackType.write,0x2d000,0x2d5ff,emu.cpuType." + cpu + ",emu.memType.snesSaveRam)\n")


def profile(folder):
    path = folder / 'native/mesen.log'
    result = dict(classification='REF_REBUILD_PROFILE_PASS',
        rom_sha256=capture.sha(folder / 'native/bor.sfc'),
        scans=evidence.native_rebuilds(path), postmap_intervals=evidence.postmap_intervals(path),
        boundaries='Original NbMapsComplete through original NbVisible; helper entry through original publish-key continuation.')
    (folder / 'ref-rebuild-profile.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def collect_suite(root, seal):
    baseline = evidence.load_baseline()
    before_control = capture.verify_capture(BASELINE, evidence.BASE_SEAL)
    before = capture.verify_capture(root, seal)
    controls = {case: evidence.postmap_intervals(BASELINE / case / 'native/mesen.log')
                for case in capture.CASES}
    with patch.object(accepted, 'audit_rom', audit_rom):
        report = accepted.collect_suite(root, seal)
    costs = {case: profile(root / case) for case in capture.CASES}
    comparisons = {case: evidence.compare_intervals(costs[case]['postmap_intervals'], controls[case])
                   for case in capture.CASES}
    require(all(set(costs[case]['scans']) == set(controls[case]) for case in capture.CASES),
            'BASELINE_SCAN_TRANSACTION_DRIFT')
    cost = comparisons['success']['3']
    require(cost['after_clocks'] * 5 <= cost['before_clocks'] * 4, 'POSTMAP_GAIN_BELOW_20_PERCENT')
    evidence.verify_timing(report, baseline)
    for case in capture.CASES:
        for name in accepted.accepted.accepted.expected_checkpoints(case):
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
    require(capture.verify_capture(BASELINE, evidence.BASE_SEAL) == before_control,
            'BASELINE_CAPTURE_CHANGED')
    report.update(classification='BYOR_MOTU_REF_REBUILD_PASS', starting_commit=STARTING_COMMIT,
        baseline_ready_epoch2=baseline['candidate_epoch2'], baseline_ready_epoch3=baseline['candidate_epoch3'],
        accepted_ready_receipt_sha256=evidence.BASE_RECEIPT_SHA256, ref_rebuild=costs,
        postmap_interval_comparison=comparisons,
        expected_rebuild_transactions={case: sorted(rows) for case, rows in controls.items()},
        accepted_ready_capture_evidence=before_control, raw_and_ready_baseline_unchanged=True)
    (root / 'ref-rebuild-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
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
    evidence.load_baseline(); capture.verify_capture(BASELINE, evidence.BASE_SEAL)
    if not args.build_only:
        accepted.accepted.accepted.q8.configure_capture_runtime(root)
    for case in capture.CASES if args.suite else (args.case,):
        print('REF REBUILD CASE', case, flush=True)
        child = root / case; build(child, args.disabled)
        if args.build_only:
            continue
        with patch.object(accepted.accepted.accepted.q8, 'audit_rom', audit_rom), \
             patch.object(accepted.accepted.accepted.q8, 'observer', observer):
            accepted.accepted.accepted.q8.run_case(child, case)
        accepted.accepted.accepted.profile(child, required=case == 'success')
        accepted.profile(child); profile(child)
    if args.suite and not args.build_only:
        seal = capture.seal_native_capture(root)
        print('CAPTURE PINS', seal.provenance_sha256, seal.raw_manifest_sha256, flush=True)
        report = collect_suite(root, seal)
        print(report['classification'], report['observed_fields'], report['verified_rgb555_pixels'], flush=True)


if __name__ == '__main__':
    main()
