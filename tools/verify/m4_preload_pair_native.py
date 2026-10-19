"""Opt-in staging-copy experiment over the published reference rebuild."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import fused_capture_evidence as capture
import m4_ref_rebuild_native as accepted
import preload_pair as overlay

BASE = Path('out/byor-motu-ref-rebuild-v2/success/native')
BASE_SHA = '41c505ad5f821bc7a6c458524cfd61f5212362f976d01a3f107a2d14381b9941'
ACCEPTED_AUDIT = accepted.audit_rom
PATCH_PC = 0x39A3EC
CONTINUE_PC = 0x39A411
SOURCE_PC = 0x39A666


def require(ok, code):
    if not ok:
        raise ValueError('PRELOAD_PAIR:' + code)


def independent_code():
    """Literal ISA encoding, independent of the transform and assembler."""
    code = bytearray(); labels = {}; fixups = []
    def emit(value): code.extend(bytes.fromhex(value))
    def label(name): labels[name] = 0x39AB00 + len(code)
    def branch(op, target):
        emit(op + '00'); fixups.append((len(code)-1, target, True))
    def jump(target):
        emit('4c0000'); fixups.append((len(code)-2, target, False))
    label('PpStart'); emit('2066a608e220682908')
    branch('f0', 'PpBinary'); jump('PpFallback8')
    label('PpBinary'); emit('c220a570c90700')
    branch('90', 'PpIndexInRange'); jump('PpFallback')
    label('PpIndexInRange'); emit('c90600')
    branch('d0', 'PpNormal'); branch('80', 'PpSpill')
    label('PpNormal'); emit('a5740a0a18657418690035c572')
    branch('f0', 'PpNormalDestination'); jump('PpFallback')
    label('PpNormalDestination'); branch('80', 'PpFast')
    label('PpSpill'); emit('a572c9b034')
    branch('f0', 'PpSpillDestination'); jump('PpFallback')
    label('PpSpillDestination'); label('PpFast')
    emit('a57218695000a8a6728bf44242abab')
    label('PpCopyStart')
    for i in range(40):
        code.append(0xAD); code.extend((0xD680 + 2*i).to_bytes(2, 'little'))
        code.append(0x9F); code.extend((2*i).to_bytes(3, 'little'))
    emit('a9ffffa2d0d6ab4c11a4')
    label('PpFallback8'); emit('c220')
    label('PpFallback'); emit('4cefa3')
    label('PpCodeEnd')
    for at, name, relative in fixups:
        target = labels[name]
        value = target-(0x39AB00+at+1) if relative else target&0xffff
        code[at:at+(1 if relative else 2)] = value.to_bytes(1 if relative else 2,'little',signed=relative)
    labels['PpLegacyAfterSource'] = PATCH_PC + 3
    return bytes(code), labels


def sizing(lines):
    # Size-only inherited lexer has no DEY; exact new bytes are checked above.
    return accepted.accepted._sizing(lines)


def audit_rom(rom, native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    require(capture.sha(BASE/'bor.sfc') == BASE_SHA, 'BASE_ROM_DIGEST')
    original = (BASE/'bor.sfc').read_bytes()
    inherited = ACCEPTED_AUDIT(original, BASE)
    lines = (native/'publisher.pasm').read_text().splitlines()
    require(lines == overlay.transform((BASE/'publisher.pasm').read_text().splitlines()), 'EXACT_SOURCE_TRANSFORM')
    sy = symbols(native/'publisher.sym'); oldsy = symbols(BASE/'publisher.sym')
    require(all(sy.get(k)==v for k,v in oldsy.items()), 'ORIGINAL_SYMBOL_MOVED')
    literal, fixed = independent_code()
    require(all(sy.get(k)==v for k,v in fixed.items()), 'INDEPENDENT_LAYOUT')
    start, end = offset(overlay.CODE_START), offset(fixed['PpCodeEnd'])
    require(fixed['PpCodeEnd'] < overlay.CODE_LIMIT and not any(original[start:end]), 'ZERO_HELPER_GAP')
    compiled = (native/'publisher.bin').read_bytes(); at=offset(PATCH_PC)
    require(original[at:at+3] == bytes.fromhex('2066a6'), 'ORIGINAL_DISPATCH')
    require(compiled[at:at+3] == bytes.fromhex('4c00ab') and compiled[start:end] == literal, 'INDEPENDENT_OPCODES')
    expected=bytearray(original); expected[at:at+3]=bytes.fromhex('4c00ab'); expected[start:end]=literal
    require(bytes(rom)==expected, 'UNAUTHORIZED_ROM_BYTE')
    branches=audit_branches(sizing(lines),sy,compiled)
    inherited['preload_pair']=dict(status='PASS',baseline_sha256=BASE_SHA,
        code_start=overlay.CODE_START,code_end=fixed['PpCodeEnd'],code_bytes=len(literal),
        patch_pc=PATCH_PC,patch_bytes=3,continuation_pc=CONTINUE_PC,
        branch_sites=branches,all_original_symbols_identical=True,
        original_two_mvn_fallback_intact=True,allowed_rom_byte_ranges=[[at,at+3],[start,end]])
    return inherited


def build(folder,control=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract=accepted.build(folder); native=folder/'native'
    require(capture.sha(native/'bor.sfc')==BASE_SHA, 'BASE_REBUILD_IDENTITY')
    contract['preload_pair']=not control
    if not control:
        lines=(native/'publisher.pasm').read_text().splitlines()
        (native/'publisher.pasm').write_text('\n'.join(overlay.transform(lines))+'\n')
        command=[os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'),
            os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
            str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),
            '--symbols',str(native/'publisher.sym'),'--no-pansy']
        result=subprocess.run(command,capture_output=True,text=True)
        (native/'preload-pair-build.log').write_text(result.stdout+result.stderr)
        require(result.returncode==0,'POPPY_ASSEMBLY')
        sy=symbols(native/'publisher.sym'); literal,fixed=independent_code()
        rom=bytearray((native/'bor.sfc').read_bytes()); at=offset(PATCH_PC); start=offset(overlay.CODE_START)
        compiled=(native/'publisher.bin').read_bytes()
        rom[at:at+3]=compiled[at:at+3]; rom[start:start+len(literal)]=compiled[start:start+len(literal)]
        audit=audit_rom(rom,native); (native/'bor.sfc').write_bytes(rom)
        contract['native_symbols'].update(sy); contract['eight_pair_audit']=audit
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    return contract


def ownership_observer(text,sy):
    """Admit only new literal-checked stores, retaining both original guards."""
    offsets={sy['PpCopyStart']+7*(i+1):2*i for i in range(40)}
    prefix='local ppCopyBase=nil\nlocal ppStoreOffsets={'+','.join(
        f'[{pc}]={at}' for pc,at in offsets.items())+'}\n'+"""
local function ppStoreAllowed(a,pc)
 local offset=ppStoreOffsets[pc]
 if ppCopyBase==nil or offset==nil then return false end
 local expected=(ppCopyBase&0x7ff)+offset;local physical=a&0x7ff
 return physical==expected or physical==expected+1
end
"""
    # Replace only the S-CPU PC clauses. CPU, live-window, count/capacity,
    # canary and address-range clauses remain exactly present and effective.
    for begin,end,marker in ((sy['NbBegin'],sy['NbCodeEnd'],'QUEUE_OWNER:snes'),
                            (sy['NbQueueSpace'],sy['NbFlushQueue'],'Q7_EXTRA_IRAM_WRITE_OWNER:')):
        clause=f"'snes'~='snes' or pc<{begin} or pc>={end}"
        matches=[line for line in text.splitlines() if marker in line and clause in line]
        require(len(matches)==1 and matches[0].count(clause)==1,'OWNERSHIP_OBSERVER_ANCHOR:'+marker)
        replacement=f"'snes'~='snes' or ((pc<{begin} or pc>={end}) and not ppStoreAllowed(a,pc))"
        text=text.replace(matches[0],matches[0].replace(clause,replacement))
    return prefix+text


def observer(script,contract):
    accepted.observer(script,contract)
    if contract['preload_pair']:
        script.write_text(ownership_observer(script.read_text(),contract['native_symbols']))
    with script.open('a') as stream:
        stream.write("""
local ppStart=nil;local ppSeq=0;local ppTrace=nil
local function ppRegs(s)
 return s['cpu.a']..'|'..s['cpu.x']..'|'..s['cpu.y']..'|'..s['cpu.d']..'|'..s['cpu.dbr']..'|'..s['cpu.sp']..'|'..s['cpu.ps']..'|'..nbWord(0x3470)
end
local function ppWords()
 return nbWord(0x3470)..'|'..nbWord(0x3472)..'|'..nbWord(0x3474)..'|'..cpDump(0x42d680,80)..'|'..cpDump(0x34b0,560)
end
local function ppEnter()
 if ppStart then nbLog('FAULT','PP_REENTRY')end
 local s=emu.getState();ppStart=s['masterClock'];ppSeq=ppSeq+1;ppTrace={}
 nbLog('PP_ENTRY',ppSeq..'|'..nbTxn..'|'..ppRegs(s)..'|'..ppWords())
end
local function ppExit()
 if not ppStart then return end
 local s=emu.getState()
 nbLog('PP_EXIT',ppSeq..'|'..nbTxn..'|'..(s['masterClock']-ppStart)..'|'..ppRegs(s)..'|'..ppWords()..'|'..table.concat(ppTrace))
 ppStart=nil;ppTrace=nil
end
""")
        for pc,body in ((PATCH_PC,'ppEnter()'),(CONTINUE_PC,'ppExit()')):
            stream.write(f'emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        if contract['preload_pair']:
            stream.write("""
local function ppAuthorize()
 local index=nbWord(0x3470);local base=nbWord(0x3472)
 local expected=index==6 and 0x34b0 or 0x3500+80*index
 if not ppStart or ppCopyBase~=nil or not batchGuard or index>6 or base~=expected or nbWord(0x42d660)~=index then
  nbLog('FAULT','PP_STORE_AUTHORIZATION');return
 end
 ppCopyBase=base;nbLog('PP_STORE_BEGIN',ppSeq..'|'..nbTxn..'|'..base..'|'..index)
end
""")
            for pc,body in ((contract['native_symbols']['PpCopyStart'],'ppAuthorize()'),
                            (CONTINUE_PC,'ppCopyBase=nil')):
                stream.write(f'emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        for cpu in ('snes','sa1'):
            # Physical I-RAM callbacks catch either CPU and all mapped aliases.
            stream.write("emu.addMemoryCallback(function(a,v)if ppStart then if '"+cpu+"'~='snes' then nbLog('FAULT','PP_OTHER_CPU_WRITE')end;ppTrace[#ppTrace+1]=string.format('%04x%02x',a,v)end end,emu.callbackType.write,0x400,0x6df,emu.cpuType."+cpu+",emu.memType.sa1InternalRam)\n")
            stream.write("emu.addMemoryCallback(function(a,v)if ppStart then nbLog('FAULT','PP_SOURCE_WRITE:"+cpu+"')end end,emu.callbackType.write,0x2d680,0x2d6cf,emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")


def profile(folder):
    import preload_pair_evidence as evidence
    result=dict(classification='PRELOAD_PAIR_PROFILE_PASS',
        rom_sha256=capture.sha(folder/'native/bor.sfc'),calls=evidence.native_calls(folder/'native/mesen.log',
            enabled=json.loads((folder/'contract.json').read_bytes())['preload_pair']),
        boundary='Original Q8StageCopy before dispatch through original Q8ScratchNoStage; no added stack frame.')
    (folder/'preload-pair-profile.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
