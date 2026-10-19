"""Optional committed-map clone/reference recount fusion over accepted REF."""
from __future__ import annotations
import json, os, subprocess, time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import fused_capture_evidence as capture
import m4_ref_rebuild_native as accepted
import commit_rebuild_fuse as overlay

BASE=Path('out/byor-motu-ref-rebuild-v2/success/native')
BASE_SHA='41c505ad5f821bc7a6c458524cfd61f5212362f976d01a3f107a2d14381b9941'
STARTING_COMMIT='afd627bb7d49cf402df788066ea875356fb4c7ca'
PATCH_PC=0x39A26B
ACCEPTED_AUDIT=accepted.audit_rom


def require(ok,code):
    if not ok:raise ValueError('COMMIT_REBUILD_FUSE:'+code)


def independent_code():
    """Literal encoding and data-access PCs, independent of Poppy/overlay."""
    code=bytearray();labels={};fix=[];access={}
    def emit(value):code.extend(bytes.fromhex(value))
    def label(name):labels[name]=0x39AB00+len(code)
    def jump(target):emit('4c0000');fix.append((len(code)-2,target,False))
    def branch(op,target):emit(op+'00');fix.append((len(code)-1,target,True))
    def mem(op,address,kind,at):
        emit(op);code.extend(address.to_bytes(2,'little'))
        access[0x39AB00+len(code)]=(kind,at)
    label('CfFuse');emit('088bf44242ababd8a20000')
    label('CfClearLoop')
    for i in range(32):
        mem('bd',0xD000+2*i,'clear_read',2*i);emit('290080')
        mem('9d',0xD000+2*i,'clear_write',2*i)
    emit('8a18694000aae00006');branch('b0','CfClearDone');jump('CfClearLoop')
    label('CfClearDone');emit('a20000');label('CfCountLoop')
    for i in range(32):
        mem('bd',0xC000+2*i,'map_read',2*i)
        mem('9d',0xC800+2*i,'map_write',2*i);emit('0aa8')
        mem('b9',0xD000,'ref_read',0);emit('1a');mem('99',0xD000,'ref_write',0)
    emit('8a18694000aae00008');branch('b0','CfCountDone');jump('CfCountLoop')
    label('CfCountDone');mem('b9',0xD000,'final_read',0)
    emit('bba00008ab28c000084ca9a2');label('CfCodeEnd')
    for at,target,relative in fix:
        value=labels[target]-(0x39AB00+at+1) if relative else labels[target]&65535
        code[at:at+(1 if relative else 2)]=value.to_bytes(1 if relative else 2,'little',signed=relative)
    return bytes(code),labels,access


@contextmanager
def size_lexer_compatibility():
    import m4_rect_map_audit as lexer
    original=lexer.statements
    def statements(lines,sy):
        return original([{'cld':' clc','tyx':' tax'}.get(line.strip(),line) for line in lines],sy)
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
    literal,labels,_=independent_code()
    require(all(sy.get(k)==v for k,v in labels.items()),'INDEPENDENT_LAYOUT')
    start,end=offset(0x39AB00),offset(labels['CfCodeEnd']);at=offset(PATCH_PC)
    require(labels['CfCodeEnd']<0x39B000 and not any(original[start:end]),'ZERO_HELPER_GAP')
    compiled=(native/'publisher.bin').read_bytes()
    require(original[at:at+4]==bytes.fromhex('8ba9ff07') and compiled[at:at+4]==bytes.fromhex('4c00abea'),'DISPATCH_OPCODES')
    require(compiled[start:end]==literal,'INDEPENDENT_OPCODES')
    expected=bytearray(original);expected[at:at+4]=bytes.fromhex('4c00abea');expected[start:end]=literal
    require(bytes(rom)==expected,'UNAUTHORIZED_ROM_BYTE')
    sizing=[{'cld':' clc','tyx':' tax'}.get(line.strip(),line) for line in accepted.accepted._sizing(lines)]
    branches=audit_branches(sizing,sy,compiled)
    inherited['commit_rebuild_fuse']=dict(status='PASS',baseline_sha256=BASE_SHA,
        code_start=0x39AB00,code_end=labels['CfCodeEnd'],code_bytes=len(literal),patch_pc=PATCH_PC,
        patch_bytes=4,words_per_block=32,branch_sites=branches,all_original_symbols_identical=True,
        allowed_rom_byte_ranges=[[at,at+4],[start,end]],original_ready_guard_retained=True,
        global_write_interleaving_changed_under_exclusive_publication_owner=True)
    return inherited


def build(folder,control=False):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    contract=accepted.build(folder);native=folder/'native'
    require(capture.sha(native/'bor.sfc')==BASE_SHA,'BASE_REBUILD_IDENTITY')
    contract['commit_rebuild_fuse']=not control
    if not control:
        lines=(native/'publisher.pasm').read_text().splitlines()
        (native/'publisher.pasm').write_text('\n'.join(overlay.transform(lines))+'\n')
        command=[os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'),
            os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'),
            str(native/'publisher.pasm'),'--output',str(native/'publisher.bin'),'--symbols',str(native/'publisher.sym'),'--no-pansy']
        result=subprocess.run(command,capture_output=True,text=True)
        (native/'commit-rebuild-fuse-build.log').write_text(result.stdout+result.stderr)
        require(result.returncode==0,'POPPY_ASSEMBLY')
        sy=symbols(native/'publisher.sym');literal,labels,_=independent_code()
        compiled=(native/'publisher.bin').read_bytes();rom=bytearray((native/'bor.sfc').read_bytes())
        at=offset(PATCH_PC);start=offset(0x39AB00)
        rom[at:at+4]=compiled[at:at+4];rom[start:start+len(literal)]=compiled[start:start+len(literal)]
        audit=audit_rom(rom,native);(native/'bor.sfc').write_bytes(rom)
        contract['native_symbols'].update(sy);contract['eight_pair_audit']=audit
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n');return contract


def observer(script,contract):
    # All inherited READY, queue, safety and metadata monitors remain intact.
    # RF entry moves before the clone, which is now inside the fused helper.
    with size_lexer_compatibility():accepted.accepted.observer(script,contract)
    if not contract['commit_rebuild_fuse']:return
    sy=contract['native_symbols'];_,_,access=independent_code()
    with script.open('a') as stream:
        stream.write("""
local cfStart=nil;local cfGuard=false;local cfTrace=nil;local cfMapTrace=nil;local cfReads=nil
local function cfRegs(s)
 return s['cpu.a']..'|'..s['cpu.x']..'|'..s['cpu.y']..'|'..s['cpu.d']..'|'..s['cpu.dbr']..'|'..s['cpu.sp']..'|'..s['cpu.ps']..'|'..nbWord(0x3470)
end
""")
        stream.write('local cfAccess={'+','.join(f"[{pc}]={{'{kind}',{at}}}" for pc,(kind,at) in access.items())+'}\n')
        stream.write("""
local function cfEnter()
 if cfStart or nbWord(0x42d600)~=4 then nbLog('FAULT','CF_ENTRY_OWNER')end
 local s=emu.getState();cfStart=s['masterClock'];cfTrace={};cfMapTrace={};cfReads={0,0}
 nbLog('RF_ENTRY',nbTxn..'|'..cfRegs(s)..'|'..cpDump(0x42d000,1536)..'|'..cpDump(0x42c000,2048))
 nbLog('CF_ENTRY',nbTxn..'|'..cpDump(0x42c800,2048));cfGuard=true
end
local function cfExit()
 cfGuard=false
 if not cfStart then nbLog('FAULT','CF_EXIT_WITHOUT_ENTRY');return end
 local s=emu.getState()
 nbLog('RF_SCAN',nbTxn..'|'..(s['masterClock']-cfStart)..'|'..cfRegs(s)..'|'..cpDump(0x42d000,1536)..'|'..cpDump(0x42c000,2048)..'|'..table.concat(cfTrace))
 nbLog('CF_SCAN',nbTxn..'|'..cpDump(0x42c800,2048)..'|'..table.concat(cfMapTrace)..'|'..cfReads[1]..'|'..cfReads[2])
 cfStart=nil;cfTrace=nil;cfMapTrace=nil;cfReads=nil
end
local function cfAccessCheck(a,v,cpu,write)
 if not cfGuard then return end
 local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];local off=a&0xffff
 local rule=cfAccess[pc];local ok=false
 if cpu=='snes' and rule and nbWord(0x42d600)==4 and s['cpu.dbr']==0x42 then
  local kind=rule[1];local at=rule[2];local x=s['cpu.x'];local y=s['cpu.y'];local expected=nil
  if kind=='clear_read' or kind=='clear_write' then
   if x%64==0 and x<1536 and write==(kind=='clear_write') then expected=0xd000+x+at end
  elseif kind=='map_read' or kind=='map_write' then
   if x%64==0 and x<2048 and write==(kind=='map_write') then expected=(write and 0xc800 or 0xc000)+x+at end
  elseif kind=='ref_read' or kind=='ref_write' or kind=='final_read' then
   if y%2==0 and y<1536 and write==(kind=='ref_write') then expected=0xd000+y end
  end
  ok=expected~=nil and (off==expected or off==expected+1)
 end
 if not ok then nbLog('FAULT','CF_EXCLUSIVE_ACCESS:'..cpu..'|'..tostring(write)..'|'..a..'|'..pc)end
 if write then
  if off>=0xc800 and off<0xd000 then cfMapTrace[#cfMapTrace+1]=string.format('%04x%02x',off,v)
  elseif off>=0xd000 and off<0xd600 then cfTrace[#cfTrace+1]=string.format('%04x%02x',off,v)end
 elseif off>=0xc000 and off<0xc800 then cfReads[1]=cfReads[1]+1
 elseif off>=0xd000 and off<0xd600 then cfReads[2]=cfReads[2]+1 end
end
""")
        for pc,body in ((sy['CfFuse'],'cfEnter()'),(sy['RfContinue'],'cfExit()')):
            stream.write(f'emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{pc},{pc},emu.cpuType.snes,emu.memType.snesMemory)\n')
        for cpu in ('snes','sa1'):
            for kind in ('read','write'):
                stream.write(f"emu.addMemoryCallback(function(a,v)cfAccessCheck(a,v,'{cpu}',{str(kind=='write').lower()})end,emu.callbackType.{kind},0x2c000,0x2d5ff,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")


def inherited_profiles(folder,required=True):
    with size_lexer_compatibility():
        accepted.accepted.accepted.accepted.profile(folder,required=required)
        accepted.accepted.profile(folder)


@contextmanager
def observed_frame_budget(folder):
    """Bound host observer work while retaining exact emulated-frame checks.

    Physical access monitors perform thousands of Lua state reads per helper.
    An unfinished 233ms MCP wall-time slice is not an emulated frame. Resume
    only its remaining count, log every response, and reject any drift/overshoot.
    The 30s bound applies to host execution, never to a measured ROM interval.
    """
    import m4_nonblank_component_native as control
    path=folder/'native/frame-tool-progress.jsonl'
    require(not path.exists(),'FRAME_PROGRESS_LOG_EXISTS')
    with path.open('x',encoding='utf-8') as stream:
        def exact(m,count):
            return run_frames_observed(m,count,lambda row:(stream.write(json.dumps(row)+'\n'),stream.flush()))
        with patch.object(control,'run_frames_exact',exact):yield


def run_frames_observed(m,count,record,clock=time.monotonic):
    require(type(count) is int and count>0,'FRAME_COUNT')
    remaining=count;last=None;start=clock();deadline=start+max(30,count/30+1)
    @contextmanager
    def bounded_rpc():
        budget=deadline-clock();require(budget>0,'OBSERVER_HOST_FRAME_DEADLINE')
        sock=getattr(m,'_sock',None)
        previous=sock.gettimeout() if sock is not None else None
        if sock is not None:sock.settimeout(min(previous or budget,budget))
        try:yield
        finally:
            if sock is not None:sock.settimeout(previous)
    while remaining:
        with bounded_rpc():response=m.run_frames(remaining)
        advanced=response.get('framesAdvanced');begin=response.get('startFrame');end=response.get('endFrame')
        row=dict(kind='frame_response',requested=remaining,response=response,host_elapsed_seconds=clock()-start)
        # Flush the authoritative RPC response before any optional diagnostic.
        record(row)
        valid=(type(advanced) is int and type(begin) is int and type(end) is int
            and 0<=advanced<=remaining and end-begin==advanced and (last is None or begin==last))
        require(valid,'EXACT_FRAME_DRIFT')
        remaining-=advanced;last=end
        if remaining:
            require(response.get('timedOut') is True,'INCOMPLETE_FRAME_WITHOUT_TIMEOUT')
            # Diagnostics are read only at a confirmed pause and share the
            # remaining host deadline. They never advance or accept a frame.
            if response.get('isPaused') is True:
                with bounded_rpc():state=m.get_cpu_state()
                record(dict(kind='cpu_diagnostic',frame=end,state=state,host_elapsed_seconds=clock()-start))
        require(clock()<deadline,'OBSERVER_HOST_FRAME_DEADLINE')
    require(response.get('isPaused') is True,'FRAME_COMPLETION_NOT_PAUSED')


def profile(folder):
    import commit_rebuild_fuse_evidence as evidence
    result=dict(classification='COMMIT_REBUILD_FUSE_PROFILE_PASS',rom_sha256=capture.sha(folder/'native/bor.sfc'),
        scans=evidence.native_scans(folder/'native/mesen.log'),
        postmap_intervals=accepted.evidence.postmap_intervals(folder/'native/mesen.log'),
        boundaries='NbMapsComplete through NbVisible; clone and recount together under exclusive publication owner4.')
    (folder/'commit-rebuild-fuse-profile.json').write_text(json.dumps(result,indent=2)+'\n');return result


def collect_suite(root,seal):
    import commit_rebuild_fuse_evidence as evidence
    output=root/'commit-rebuild-fuse-receipt.json'
    require(not output.exists(),'EXISTING_PASS_RECEIPT_MUST_BE_RETAINED_BEFORE_RECOLLECTION')
    baseline=evidence.baseline.load_baseline()
    native_baseline=evidence.baseline.load_native_baseline(baseline)
    before_base=capture.verify_capture(evidence.baseline.BASELINE,evidence.baseline.BASE_SEAL)
    before=capture.verify_capture(root,seal)
    require(all(json.loads((root/case/'contract.json').read_bytes()).get('commit_rebuild_fuse') is True
        for case in capture.CASES),'ENABLED_CONTRACT_INVENTORY')
    # Retain all inherited READY and REF thresholds. The REF profile now spans
    # clone and recount together and still validates the same ref write trace.
    with patch.object(accepted,'audit_rom',audit_rom),patch.object(accepted,'profile',profile):
        report=accepted.collect_suite(root,seal)
    costs={case:profile(root/case) for case in capture.CASES}
    controls={case:evidence.reference.postmap_intervals(evidence.baseline.BASELINE/case/'native/mesen.log')
        for case in capture.CASES}
    comparisons={case:evidence.reference.compare_intervals(costs[case]['postmap_intervals'],controls[case])
        for case in capture.CASES}
    evidence.compare_postmap(costs['success']['postmap_intervals'],controls['success'])
    timings=evidence.verify_timing(report,native_baseline)
    for case in capture.CASES:
        for name in accepted.accepted.accepted.accepted.expected_checkpoints(case):
            current=(root/case/'native'/name).read_bytes();old=(evidence.baseline.BASELINE/case/'native'/name).read_bytes()
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
    report.update(classification='BYOR_MOTU_COMMIT_REBUILD_FUSE_PASS',starting_commit=STARTING_COMMIT,
        accepted_reference_receipt_sha256=evidence.baseline.BASE_RECEIPT_SHA256,
        accepted_reference_capture_evidence=before_base,commit_rebuild_fuse=costs,
        postmap_comparison_to_reference=comparisons,all_case_timing_nonregression=timings,
        new_postmap_gain_threshold_percent=20,raw_and_reference_capture_unchanged=True,
        global_write_interleaving_changed_under_exclusive_publication_owner=True)
    with output.open('x',encoding='utf-8') as stream:stream.write(json.dumps(report,indent=2)+'\n')
    return report
