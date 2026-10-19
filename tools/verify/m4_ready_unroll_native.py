"""Optional bank-local READY scan over the published reference-rebuild ROM."""
from __future__ import annotations
import json,os,subprocess
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch

import fused_capture_evidence as capture
import m4_ref_rebuild_native as accepted
import ready_unroll as overlay

BASE=Path('out/byor-motu-ref-rebuild-v2/success/native')
BASE_SHA='41c505ad5f821bc7a6c458524cfd61f5212362f976d01a3f107a2d14381b9941'
STARTING_COMMIT='afd627bb7d49cf402df788066ea875356fb4c7ca'
ACCEPTED_AUDIT=accepted.audit_rom
PATCH_PC=0x39A1F7


def require(ok,code):
    if not ok:raise ValueError('READY_UNROLL:'+code)


def independent_code():
    """Literal 65816 encoding independent of the overlay and assembler."""
    code=bytearray();labels={};fix=[]
    def emit(value):code.extend(bytes.fromhex(value))
    def label(name):labels[name]=0x39AB00+len(code)
    def jump(target):emit('4c0000');fix.append((len(code)-2,target,False))
    def branch(op,target):emit(op+'00');fix.append((len(code)-1,target,True))
    label('RuValidate');emit('088bf44242ababd8a20000')
    label('RuBlockLoop')
    for i in range(32):
        emit('bd');code.extend((0xC000+2*i).to_bytes(2,'little'))
        emit('29ffbfc90003');branch('90',f'RuValid{i:02d}');jump(f'RuReject{i:02d}')
        label(f'RuValid{i:02d}');emit('9d');code.extend((0xC000+2*i).to_bytes(2,'little'))
    emit('8a18694000aae00008');branch('b0','RuSuccess');jump('RuBlockLoop')
    label('RuSuccess');emit('ab28a2fe07a900088570c900084c23a2')
    for i in range(32):
        label(f'RuReject{i:02d}');emit('8a1869');code.extend((2*i).to_bytes(2,'little'))
        emit('aa');jump('RuReject')
    label('RuReject');emit('bd00c0');branch('10','RuSlotReload');jump('RuTaggedBad')
    label('RuSlotReload');emit('29ff3f');jump('RuSlotFail')
    label('RuTaggedBad');emit('ab288a');branch('f0','RuTaggedCarry');emit('18')
    label('RuTaggedCarry');emit('a9008086704c3fa3')
    label('RuSlotFail');emit('ab28c9000386704c3fa3')
    label('RuCodeEnd')
    for at,target,relative in fix:
        value=labels[target]-(0x39AB00+at+1) if relative else labels[target]&65535
        code[at:at+(1 if relative else 2)]=value.to_bytes(1 if relative else 2,'little',signed=relative)
    return bytes(code),labels


def sizing(lines):
    # Size-only inherited lexer lacks CLD/DEY. Literal bytes are checked above.
    return [' clc' if line.strip()=='cld' else line for line in accepted.accepted._sizing(lines)]


@contextmanager
def size_lexer_compatibility():
    # Legacy observer/profile discovery walks all source statements and lacks
    # CLD in its size-only lexer. Preserve its one-byte size; the independent
    # D8 literal, model and fault test verify the actual instruction semantics.
    import m4_rect_map_audit as lexer
    original=lexer.statements
    def statements(lines,sy):
        return original([' clc' if line.strip()=='cld' else line for line in lines],sy)
    with patch.object(lexer,'statements',statements):yield


def audit_rom(rom,native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    require(capture.sha(BASE/'bor.sfc')==BASE_SHA,'BASE_ROM_DIGEST')
    original=(BASE/'bor.sfc').read_bytes();inherited=ACCEPTED_AUDIT(original,BASE)
    lines=(native/'publisher.pasm').read_text().splitlines()
    require(lines==overlay.transform((BASE/'publisher.pasm').read_text().splitlines()),'EXACT_SOURCE_TRANSFORM')
    sy=symbols(native/'publisher.sym');old=symbols(BASE/'publisher.sym')
    require(all(sy.get(k)==v for k,v in old.items()),'ORIGINAL_SYMBOL_MOVED')
    literal,labels=independent_code();require(all(sy.get(k)==v for k,v in labels.items()),'INDEPENDENT_LAYOUT')
    start,end=offset(overlay.CODE_START),offset(labels['RuCodeEnd']);at=offset(PATCH_PC)
    require(labels['RuCodeEnd']<overlay.CODE_LIMIT and not any(original[start:end]),'ZERO_HELPER_GAP')
    compiled=(native/'publisher.bin').read_bytes()
    require(original[at:at+3]==bytes.fromhex('4c00a8') and compiled[at:at+3]==bytes.fromhex('4c00ab'),'DISPATCH_OPCODES')
    require(compiled[start:end]==literal,'INDEPENDENT_OPCODES')
    expected=bytearray(original);expected[at:at+3]=bytes.fromhex('4c00ab');expected[start:end]=literal
    require(bytes(rom)==expected,'UNAUTHORIZED_ROM_BYTE')
    branches=audit_branches(sizing(lines),sy,compiled)
    inherited['ready_unroll']=dict(status='PASS',baseline_sha256=BASE_SHA,code_start=overlay.CODE_START,
        code_end=labels['RuCodeEnd'],code_bytes=len(literal),patch_pc=PATCH_PC,patch_bytes=3,
        words_per_block=32,branch_sites=branches,all_original_symbols_identical=True,
        original_validator_retained=True,allowed_rom_byte_ranges=[[at,at+3],[start,end]])
    return inherited


def build(folder,control=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract=accepted.build(folder);native=folder/'native'
    require(capture.sha(native/'bor.sfc')==BASE_SHA,'BASE_REBUILD_IDENTITY')
    contract['ready_unroll']=not control
    if not control:
        lines=(native/'publisher.pasm').read_text().splitlines()
        (native/'publisher.pasm').write_text('\n'.join(overlay.transform(lines))+'\n')
        command=[os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'),
            os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
            str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),'--symbols',str(native/'publisher.sym'),'--no-pansy']
        result=subprocess.run(command,capture_output=True,text=True)
        (native/'ready-unroll-build.log').write_text(result.stdout+result.stderr);require(result.returncode==0,'POPPY_ASSEMBLY')
        sy=symbols(native/'publisher.sym');literal,labels=independent_code()
        compiled=(native/'publisher.bin').read_bytes();rom=bytearray((native/'bor.sfc').read_bytes())
        at=offset(PATCH_PC);start=offset(overlay.CODE_START)
        rom[at:at+3]=compiled[at:at+3];rom[start:start+len(literal)]=compiled[start:start+len(literal)]
        audit=audit_rom(rom,native);(native/'bor.sfc').write_bytes(rom)
        contract['native_symbols'].update(sy);contract['eight_pair_audit']=audit
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n');return contract


def observer_text(text,sy):
    """Relocate only the entry hook and exact byte-write ownership predicate."""
    before=f",{sy['RvValidate']},{sy['RvValidate']},emu.cpuType.snes,emu.memType.snesMemory)"
    lines=[line for line in text.splitlines() if "nbLog('RV_ENTRY'" in line and before in line]
    require(len(lines)==1,'ENTRY_OBSERVER_ANCHOR')
    after=f",{sy['RuValidate']},{sy['RuValidate']},emu.cpuType.snes,emu.memType.snesMemory)"
    text=text.replace(lines[0],lines[0].replace(before,after))
    old='pc~=0x39a822 or x%2~=0 or x>=2048 or (off~=0xc000+x and off~=0xc001+x)'
    new='ruOffsets[pc]==nil or x%64~=0 or x>=2048 or (off~=0xc000+x+ruOffsets[pc] and off~=0xc001+x+ruOffsets[pc])'
    require(text.count(old)==2,'WRITE_OBSERVER_ANCHORS')
    text=text.replace(old,new)
    offsets={sy['RuBlockLoop']+17*(i+1):2*i for i in range(32)}
    prefix='local ruOffsets={'+','.join(f'[{pc}]={at}' for pc,at in offsets.items())+'}\n'
    return prefix+text


def observer(script,contract):
    with size_lexer_compatibility():accepted.observer(script,contract)
    if not contract['ready_unroll']:return
    sy=contract['native_symbols'];script.write_text(observer_text(script.read_text(),sy))
    with script.open('a') as stream:
        stream.write("""
local ruTrace=nil;local ruTxn=nil
local function ruEnter()
 if ruTrace then nbLog('FAULT','RU_TRACE_REENTRY')end
 ruTrace={};ruTxn=nbTxn
end
local function ruExit()
 if not ruTrace or ruTxn~=nbTxn then nbLog('FAULT','RU_TRACE_EXIT_WITHOUT_ENTRY');return end
 nbLog('RU_TRACE',ruTxn..'|'..table.concat(ruTrace));ruTrace=nil;ruTxn=nil
end
""")
        for pc,body in ((sy['RuValidate'],'ruEnter()'),(sy['RvContinue'],'ruExit()')):
            stream.write(f'emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        for cpu in ('snes','sa1'):
            stream.write("emu.addMemoryCallback(function(a,v)if ruTrace then ruTrace[#ruTrace+1]=string.format('%04x%02x',a&0xffff,v)end end,emu.callbackType.write,0x2c000,0x2c7ff,emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")


def inherited_profiles(folder,required=True):
    with size_lexer_compatibility():
        accepted.accepted.accepted.accepted.profile(folder,required=required)
        accepted.accepted.profile(folder);accepted.profile(folder)


def profile(folder):
    import ready_unroll_evidence as evidence
    result=dict(classification='READY_UNROLL_PROFILE_PASS',rom_sha256=capture.sha(folder/'native/bor.sfc'),
        scans=evidence.native_scans(folder/'native/mesen.log'),
        ready_intervals=evidence.ready.ready_intervals(folder/'native/mesen.log'),
        postmap_intervals=accepted.evidence.postmap_intervals(folder/'native/mesen.log'),
        boundaries=dict(ready='Last NbQueueDrainDone through original NbReady.',
            postmap='Original NbMapsComplete through original NbVisible; separate interval after map commit.',
            helper='RuValidate through the original source-epoch continuation.'))
    (folder/'ready-unroll-profile.json').write_text(json.dumps(result,indent=2)+'\n');return result


def collect_suite(root,seal):
    import ready_unroll_evidence as evidence
    output=root/'ready-unroll-receipt.json'
    require(not output.exists(),'EXISTING_PASS_RECEIPT_MUST_BE_RETAINED_BEFORE_RECOLLECTION')
    baseline=evidence.baseline.load_baseline()
    native_baseline=evidence.baseline.load_native_baseline(baseline)
    before_base=capture.verify_capture(evidence.baseline.BASELINE,evidence.baseline.BASE_SEAL)
    before=capture.verify_capture(root,seal)
    require(all(json.loads((root/case/'contract.json').read_bytes()).get('ready_unroll') is True
        for case in capture.CASES),'ENABLED_CONTRACT_INVENTORY')
    with patch.object(accepted,'audit_rom',audit_rom):report=accepted.collect_suite(root,seal)
    costs={case:profile(root/case) for case in capture.CASES}
    controls={case:evidence.ready.ready_intervals(evidence.baseline.BASELINE/case/'native/mesen.log')
        for case in capture.CASES}
    comparisons={case:evidence.ready.compare_intervals(costs[case]['ready_intervals'],controls[case])
        for case in capture.CASES}
    evidence.compare_ready(costs['success']['ready_intervals'],controls['success'])
    timings=evidence.verify_timing(report,native_baseline)
    # Compare every original checkpoint, including map data and all referenced
    # CHR bytes. Unused cache contents and initial bootstrap VRAM are excluded
    # by the same accepted checkpoint policy, never by a timing exception.
    for case in capture.CASES:
        for name in accepted.accepted.accepted.accepted.expected_checkpoints(case):
            current=(root/case/'native'/name).read_bytes()
            old=(evidence.baseline.BASELINE/case/'native'/name).read_bytes()
            if name.endswith('-vram.bin'):
                if name in ('initial-vram.bin','handoff-vram.bin'):continue
                require(len(current)==len(old)==65536 and current[61440:]==old[61440:],case+':BASELINE_MAP:'+name)
                slots={int.from_bytes(current[i:i+2],'little')&0x3fff for i in range(61440,65536,2)}
                require(all(k<768 and current[k*64:(k+1)*64]==old[k*64:(k+1)*64]
                    and current[49152+k*16:49152+(k+1)*16]==old[49152+k*16:49152+(k+1)*16]
                    for k in slots),case+':BASELINE_REFERENCED_CHR:'+name)
            else:require(current==old,case+':BASELINE_STATE:'+name)
    require(capture.verify_capture(root,seal)==before,'RAW_CAPTURE_CHANGED')
    require(capture.verify_capture(evidence.baseline.BASELINE,evidence.baseline.BASE_SEAL)==before_base,'BASE_CAPTURE_CHANGED')
    report.update(classification='BYOR_MOTU_READY_UNROLL_PASS',starting_commit=STARTING_COMMIT,
        accepted_reference_receipt_sha256=evidence.baseline.BASE_RECEIPT_SHA256,
        accepted_reference_capture_evidence=before_base,ready_unroll=costs,
        ready_comparison_to_reference=comparisons,all_case_timing_nonregression=timings,
        new_ready_gain_threshold_percent=25,original_reference_postmap_gain_threshold_percent=20,
        boundaries='READY is before map commit. The inherited reference-rebuild postmap comparison remains separate.',
        raw_and_reference_capture_unchanged=True)
    with output.open('x',encoding='utf-8') as stream:stream.write(json.dumps(report,indent=2)+'\n')
    return report
