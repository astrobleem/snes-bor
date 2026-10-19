"""Measured publication fusion plus exact abort-map copy optimization."""
from __future__ import annotations
import json,os,subprocess
from pathlib import Path
from unittest.mock import patch
import fused_capture_evidence as capture
import m4_commit_rebuild_fuse_native as accepted
import abort_copy as overlay

BASE=Path('out/byor-motu-commit-rebuild-fuse-static-v2/candidate/native')
BASE_SHA='c926a1808dd809f54474788f08ef857a9977b786e17146248f15daaa926dae37'
ACCEPTED_AUDIT=accepted.audit_rom
PATCH_PC=0x39A349
CONTINUE_PC=0x39A35A


def require(ok,code):
    if not ok:raise ValueError('ABORT_COPY:'+code)


def independent_code():
    code=bytearray.fromhex('08af00d642d0034c38afc9050090034c38af8bf44242ababd8a20000')
    labels=dict(CaCopy=0x39AE40,CaPhaseCheck=0x39AE4A,CaFast=0x39AE52,
        CaLoop=0x39AE5C,CaDone=0x39AF2A,CaFallback=0x39AF38,CaCodeEnd=0x39AF40,
        CaContinue=CONTINUE_PC,CaLegacyCopy=0x39A34D)
    access={}
    for i in range(32):
        for opcode,address,kind in ((0xbd,0xc800+2*i,'read'),(0x9d,0xc000+2*i,'write')):
            code.append(opcode);code.extend(address.to_bytes(2,'little'))
            access[0x39AE40+len(code)]=(kind,2*i)
    code.extend(bytes.fromhex('8a18694000aae00008b0034c5caea200d0a000c8ab28a900004c5aa3288ba9ff074c4da3'))
    require(len(code)==256,'LITERAL_SIZE')
    return bytes(code),labels,access


def audit_rom(rom,native):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    require(capture.sha(BASE/'bor.sfc')==BASE_SHA,'FUSION_ROM_DIGEST')
    original=(BASE/'bor.sfc').read_bytes();inherited=ACCEPTED_AUDIT(original,BASE)
    lines=(native/'publisher.pasm').read_text().splitlines()
    require(lines==overlay.transform((BASE/'publisher.pasm').read_text().splitlines()),'EXACT_SOURCE_TRANSFORM')
    sy=symbols(native/'publisher.sym');old=symbols(BASE/'publisher.sym')
    require(all(sy.get(k)==v for k,v in old.items()),'ORIGINAL_SYMBOL_MOVED')
    literal,labels,_=independent_code();require(all(sy.get(k)==v for k,v in labels.items()),'INDEPENDENT_LAYOUT')
    at=offset(PATCH_PC);start,end=offset(labels['CaCopy']),offset(labels['CaCodeEnd'])
    require(not any(original[start:end]) and labels['CaCodeEnd']<0x39b000,'ZERO_HELPER_GAP')
    compiled=(native/'publisher.bin').read_bytes()
    require(original[at:at+4]==bytes.fromhex('8ba9ff07') and compiled[at:at+4]==bytes.fromhex('4c40aeea'),'DISPATCH_OPCODES')
    require(compiled[start:end]==literal,'INDEPENDENT_OPCODES')
    require(original[offset(CONTINUE_PC)-3:offset(CONTINUE_PC)+4]==bytes.fromhex('a900008f00d642'),'ORIGINAL_CONTINUATION')
    expected=bytearray(original);expected[at:at+4]=bytes.fromhex('4c40aeea');expected[start:end]=literal
    require(bytes(rom)==expected,'UNAUTHORIZED_ROM_BYTE')
    sizing=[{'cld':' clc','tyx':' tax'}.get(line.strip(),line) for line in accepted.accepted.accepted._sizing(lines)]
    branches=audit_branches(sizing,sy,compiled)
    inherited['abort_copy']=dict(status='PASS',fusion_rom_sha256=BASE_SHA,patch_pc=PATCH_PC,patch_bytes=4,
        continuation_pc=CONTINUE_PC,code_start=labels['CaCopy'],code_end=labels['CaCodeEnd'],code_bytes=256,
        branch_sites=branches,all_original_symbols_identical=True,original_owner_close_store_retained=True,
        allowed_rom_byte_ranges=[[at,at+4],[start,end]],global_read_write_interleaving_changed_in_fixture_abort_section=True)
    return inherited


def build(folder,control=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract=accepted.build(folder,control=control);native=folder/'native';contract['abort_copy']=not control
    if not control:
        require(capture.sha(native/'bor.sfc')==BASE_SHA,'FUSION_REBUILD_IDENTITY')
        lines=(native/'publisher.pasm').read_text().splitlines()
        (native/'publisher.pasm').write_text('\n'.join(overlay.transform(lines))+'\n')
        command=[os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'),
            os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
            str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),'--symbols',str(native/'publisher.sym'),'--no-pansy']
        run=subprocess.run(command,capture_output=True,text=True)
        (native/'abort-copy-build.log').write_text(run.stdout+run.stderr);require(run.returncode==0,'POPPY_ASSEMBLY')
        compiled=(native/'publisher.bin').read_bytes();rom=bytearray((native/'bor.sfc').read_bytes())
        literal,labels,_=independent_code();at=offset(PATCH_PC);start=offset(labels['CaCopy'])
        rom[at:at+4]=compiled[at:at+4];rom[start:start+len(literal)]=compiled[start:start+len(literal)]
        audit=audit_rom(rom,native);(native/'bor.sfc').write_bytes(rom)
        contract['native_symbols'].update(symbols(native/'publisher.sym'));contract['eight_pair_audit']=audit
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n');return contract


def observer(script,contract):
    accepted.observer(script,contract)
    if not contract['abort_copy']:return
    sy=contract['native_symbols'];_,_,access=independent_code()
    with script.open('a') as stream:
        stream.write("""
local caGuard=false;local caStart=nil;local caOwner=nil;local caSerial=0;local caTrace=nil;local caReads=0;local caClose=nil;local caPath=nil;local caBus=nil;local caScanned=false
local function caRegs(s)
 return s['cpu.a']..'|'..s['cpu.x']..'|'..s['cpu.y']..'|'..s['cpu.d']..'|'..s['cpu.dbr']..'|'..s['cpu.sp']..'|'..s['cpu.ps']..'|'..nbWord(0x3470)
end
""")
        stream.write('local caAccess={'+','.join(f"[{pc}]={{'{kind}',{at}}}" for pc,(kind,at) in access.items())+'}\n')
        stream.write("""
local function caEnter()
 caOwner=nbWord(0x42d600)
 if caGuard or caStart then nbLog('FAULT','CA_ENTRY_OWNER')end
 local s=emu.getState();caStart=s['masterClock'];caSerial=caSerial+1;caTrace={};caReads=0;caClose={};caPath=nil;caBus={};caScanned=false
 nbLog('CA_ENTRY',nbTxn..'|'..caSerial..'|'..caRegs(s)..'|'..cpDump(0x42c000,2048)..'|'..cpDump(0x42c800,2048)..'|'..cpDump(0x42d000,1536)..'|'..caOwner)
 caGuard=true
end
local function caChoose(path)
 if not caGuard or not caStart or caPath~=nil or ((path=='fast')~=(caOwner>=1 and caOwner<=4))then nbLog('FAULT','CA_PATH_OWNER')end
 caPath=path;nbLog('CA_PATH',nbTxn..'|'..caSerial..'|'..path);caGuard=true
end
local function caScan()
 caGuard=false
 if not caStart or nbWord(0x42d600)~=caOwner then nbLog('FAULT','CA_SCAN_OWNER');return end
 local s=emu.getState()
 nbLog('CA_SCAN',nbTxn..'|'..caSerial..'|'..(s['masterClock']-caStart)..'|'..caRegs(s)..'|'..cpDump(0x42c000,2048)..'|'..cpDump(0x42c800,2048)..'|'..cpDump(0x42d000,1536)..'|'..table.concat(caTrace)..'|'..caReads..'|'..table.concat(caBus))
 caScanned=true;caGuard=true
end
local function caClosed()
 caGuard=false
 if not caStart or not caScanned or nbWord(0x42d600)~=0 then nbLog('FAULT','CA_CLOSE_OWNER');return end
 nbLog('CA_CLOSED',nbTxn..'|'..caSerial..'|'..table.concat(caClose)..'|'..nbWord(0x42d600))
 caStart=nil;caOwner=nil;caTrace=nil;caClose=nil;caPath=nil;caBus=nil
end
local function caAccessCheck(a,v,cpu,write)
 if not caGuard then return end
 local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];local off=a&0xffff;local x=s['cpu.x'];local rule=caAccess[pc]
 local expected=nil;local paired=false
 if cpu=='snes' and nbWord(0x42d600)==caOwner and s['cpu.dbr']==0x42 then
  if caPath=='fast' and rule and x%64==0 and x<2048 and write==(rule[1]=='write') then
   expected=(write and 0xc000 or 0xc800)+x+rule[2];paired=true
  elseif caPath=='legacy' and pc==0x39a356 and x>=0xc800 and x<0xd000 and s['cpu.y']==x-0x800 then
   expected=write and s['cpu.y'] or x
  end
 end
 if expected==nil or (off~=expected and (not paired or off~=expected+1))then nbLog('FAULT','CA_EXCLUSIVE_ACCESS:'..cpu..'|'..tostring(write)..'|'..a..'|'..pc)end
 if write then caTrace[#caTrace+1]=string.format('%04x%02x',off,v)else caReads=caReads+1 end
 caBus[#caBus+1]=string.format('%s%04x%02x',write and 'W' or 'R',off,v)
end
""")
        for pc,body in ((sy['CaCopy'],'caEnter()'),(sy['CaFast'],"caChoose('fast')"),
            (sy['CaFallback'],"caChoose('legacy')"),(sy['CaContinue'],'caScan()'),(sy['CaContinue']+4,'caClosed()')):
            stream.write(f'emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        for cpu in ('snes','sa1'):
            for kind in ('read','write'):
                stream.write(f"emu.addMemoryCallback(function(a,v)caAccessCheck(a,v,'{cpu}',{str(kind=='write').lower()})end,emu.callbackType.{kind},0x2c000,0x2d5ff,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
            stream.write("emu.addMemoryCallback(function(a,v)if caGuard then local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];if '"+cpu+"'~='snes' or not caScanned or pc~="+str(sy['CaContinue']+4)+" or v~=0 then nbLog('FAULT','CA_OWNER_WRITE:"+cpu+"|'..a..'|'..pc)end;caClose[#caClose+1]=string.format('%04x%02x',a&0xffff,v)end end,emu.callbackType.write,0x2d600,0x2d601,emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")


def profile(folder):
    import abort_copy_evidence as evidence
    result=dict(classification='ABORT_COPY_PROFILE_PASS',rom_sha256=capture.sha(folder/'native/bor.sfc'),
        copies=evidence.native_copies(folder/'native/mesen.log'),
        boundaries='CaCopy entry through original zero-owner STA, with both-CPU exclusivity guards through completion of that STA.')
    (folder/'abort-copy-profile.json').write_text(json.dumps(result,indent=2)+'\n');return result


def collect_suite(root,seal):
    import abort_copy_evidence as evidence
    output=root/'abort-copy-receipt.json';require(not output.exists(),'EXISTING_PASS_RECEIPT_MUST_BE_RETAINED')
    before=capture.verify_capture(root,seal)
    require(all(json.loads((root/case/'contract.json').read_bytes()).get('abort_copy') is True
        for case in capture.CASES),'ENABLED_CONTRACT_INVENTORY')
    with patch.object(accepted,'audit_rom',audit_rom):report=accepted.collect_suite(root,seal)
    costs={case:profile(root/case) for case in capture.CASES}
    require(any(row['path']=='fast' for cost in costs.values() for row in cost['copies'].values()),'NO_NATIVE_FAST_COPY')
    require(capture.verify_capture(root,seal)==before,'RAW_CAPTURE_CHANGED')
    report.update(classification='BYOR_MOTU_ABORT_COPY_PASS',abort_copy=costs,
        publication_fusion_and_abort_copy_both_required=True,all_case_timing_gate_retained=True,
        abort_global_read_write_interleaving_changed_under_exclusive_fixture_owner=True)
    with output.open('x',encoding='utf-8') as stream:stream.write(json.dumps(report,indent=2)+'\n')
    return report
