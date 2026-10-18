"""Strict standalone Poppy/Mesen native adapter for the eight-pair scratch DMA.

This package cannot run the retained Windows/Mesen/PAK fixtures locally.
Run --suite on Sol's checkout, where prior accepted native controls exist.
All old default files/flags and original independent pixel oracles are untouched.
"""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import argparse,copy,hashlib,inspect,json,os,shutil,subprocess,textwrap

import eight_pair_direct as q8

BASE=Path('out/byor-motu-seven-pair-v2/success/native')
BASELINE=Path('out/byor-motu-seven-pair-v2')
RECEIPT=Path('docs/receipts/byor-motu-seven-pair-spill.json')
MS=21477.270
CASES=('success','valid','early','ready','partial','stale','insufficient','right')
_Q7_OBSERVER=None
_Q7_WINDOWS=None


def prior():
    import m4_seven_pair_native as q7
    return q7


def original_q7_functions():
    """Capture actual accepted callables BEFORE the per-case monkey patches."""
    global _Q7_OBSERVER,_Q7_WINDOWS
    q7=prior()
    if _Q7_OBSERVER is None:_Q7_OBSERVER=q7.observer
    if _Q7_WINDOWS is None:_Q7_WINDOWS=q7.presentation_windows
    return _Q7_OBSERVER,_Q7_WINDOWS


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok,code):
    if not ok:raise ValueError('Q8_ACCEPTANCE:'+code)


def prepare_capture_runtime(destination,executable,settings=None):
    """Use identical Mesen binaries with a private, writable screenshot folder.

    take_screenshot has no output-path argument: the managed tool waits for
    the native core to write in ConfigManager.ScreenshotFolder. A portable
    settings copy preserves rendering and emulation settings, relocates only
    capture/save output paths, and seeds the existing bor.srm input verbatim.
    It avoids writes to the user's Documents directory in a sandbox.
    """
    destination=Path(destination).resolve();executable=Path(executable).resolve()
    source=executable.parent
    required=(executable.name,'Mesen.dll','MesenCore.dll',
              'Mesen.deps.json','Mesen.runtimeconfig.json')
    require(all((source/name).is_file() for name in required),'CAPTURE_MATCHED_BUILD_MISSING')
    if settings is None:
        settings=source/'settings.json'
        if not settings.is_file():
            if os.name=='nt':
                import ctypes
                documents=ctypes.create_unicode_buffer(32768)
                require(ctypes.windll.shell32.SHGetFolderPathW(None,5,None,0,documents)==0,
                        'CAPTURE_DOCUMENTS_PATH')
                settings=Path(documents.value)/'Mesen2/settings.json'
            else:settings=Path.home()/'.config/Mesen2/settings.json'
    settings=Path(settings)
    original=json.loads(settings.read_text(encoding='utf-8-sig')) if settings.is_file() else {}
    require(isinstance(original,dict) and isinstance(original.get('Preferences',{}),dict),
            'CAPTURE_SETTINGS_OBJECT')
    destination.mkdir(parents=True,exist_ok=False)
    copied=[]
    for file in source.iterdir():
        if file.is_file() and file.suffix.lower() in ('.exe','.dll','.json','.zip') and file.name!='settings.json':
            shutil.copy2(file,destination/file.name);copied.append(file.name)
        elif file.is_dir() and file.name=='Dependencies':
            shutil.copytree(file,destination/file.name)
            copied.extend(str(p.relative_to(source)) for p in file.rglob('*') if p.is_file())
    hashes={name:sha(source/name) for name in copied}
    require(all(sha(destination/name)==value for name,value in hashes.items()),'CAPTURE_BINARY_IDENTITY')
    screenshots=destination/'Screenshots';screenshots.mkdir()
    saves=destination/'Saves';saves.mkdir()
    states=destination/'SaveStates';states.mkdir()
    old_preferences=original.get('Preferences',{})
    old_saves=(Path(old_preferences['SaveDataFolder']) if old_preferences.get('OverrideSaveDataFolder')
               else settings.parent/'Saves')
    seed=old_saves/'bor.srm'
    initial_sram=None
    if seed.is_file():
        shutil.copy2(seed,saves/seed.name)
        initial_sram=dict(source=str(seed),sha256=sha(seed),bytes=seed.stat().st_size)
        require(sha(saves/seed.name)==initial_sram['sha256'],'CAPTURE_SRAM_INPUT_IDENTITY')
    private=copy.deepcopy(original);preferences=private.setdefault('Preferences',{})
    preferences.update(OverrideScreenshotFolder=True,ScreenshotFolder=str(screenshots),
                       OverrideSaveDataFolder=True,SaveDataFolder=str(saves),
                       OverrideSaveStateFolder=True,SaveStateFolder=str(states))
    (destination/'settings.json').write_text(json.dumps(private,indent=2)+'\n',encoding='utf-8')
    manifest=dict(source_executable=str(executable),executable=str(destination/executable.name),
                  source_settings=str(settings),source_settings_sha256=sha(settings) if settings.is_file() else None,
                  screenshot_folder=str(screenshots),binary_sha256=hashes,initial_sram=initial_sram,
                  changed_settings=['Preferences.'+name for name in
                    ('OverrideScreenshotFolder','ScreenshotFolder','OverrideSaveDataFolder',
                     'SaveDataFolder','OverrideSaveStateFolder','SaveStateFolder')],
                  global_settings_modified=False)
    (destination/'capture-runtime.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return destination/executable.name


def configure_capture_runtime(root):
    executable=os.environ.get('MESEN_EXE','E:/gh/Mesen2/bin/win-x64/Release/Mesen.exe')
    os.environ['MESEN_EXE']=str(prepare_capture_runtime(root/'capture-runtime',executable))


def policy_write_completions(code,begin):
    """Exact post-STA PCs reported by Mesen's 65816 write callbacks."""
    store=bytes.fromhex('8f76d642')
    starts=[i for i in range(len(code)-3) if code[i:i+4]==store]
    require(len(starts)==2 and starts[0]>=3 and starts[1]>=3 and
            code[starts[0]-3:starts[0]]==bytes.fromhex('a90600') and
            code[starts[1]-3:starts[1]]==bytes.fromhex('a90800') and
            starts[-1]+4==len(code),'Q8_POLICY_STORE_DRIFT')
    return [begin+i+4 for i in starts]


def audit_rom(rom,native):
    """Compare entire cartridge; permit A000 edits and operand-only relinks."""
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    from m4_restore_spill_native import audit_branches
    q7=prior();base_rom=(BASE/'bor.sfc').read_bytes()
    require(sha(BASE/'bor.sfc')==q8.BASE_ROM_SHA256,'BASE_ROM_SHA_DRIFT')
    old=(BASE/'publisher.pasm').read_text().splitlines()
    wanted=q8.transform(old)
    require((native/'publisher.pasm').read_text().splitlines()==wanted,'EXACT_SOURCE_OVERLAY')
    sy=symbols(native/'publisher.sym');oldsy=symbols(BASE/'publisher.sym')
    compiled=(native/'publisher.bin').read_bytes()
    branches=audit_branches([' iny' if l.strip()=='dey' else l for l in wanted],sy,compiled)
    require(sy['NbBegin']==oldsy['NbBegin']==0x39A000 and
            sy['NbCodeEnd']<0x39B000 and sy['NbCodeEnd']>oldsy['NbCodeEnd'] and
            sy['SpCodeEnd']==oldsy['SpCodeEnd'] and sy['BhCodeEnd']==oldsy['BhCodeEnd'],
            'CODE_REGION_COLLISION')
    for name in ('WarmDirectPair','OnlineDmaDone8','OnlineDmaDone9',
                 'BhBitmapBuilt','BhInitialize','NbRestorePlan'):
        require(sy[name]==oldsy[name],'UNRELATED_ENTRY_MOVED:'+name)
    a,b=offset(oldsy['NbCodeEnd']),offset(sy['NbCodeEnd'])
    require(not any(base_rom[a:b]),'A000_EXTENSION_NOT_ZERO')
    # Independent literal 65816 bytes for the new dispatch. Poppy cannot
    # certify an emitted opcode solely by comparing output with itself.
    def opcode(label,expected):
        at=offset(sy[label]);got=compiled[at:at+len(expected)]
        require(got==expected,'Q8_INDEPENDENT_OPCODE:'+label)
    def near_jsr(label,target):
        opcode(label,bytes([0x20,sy[target]&255,(sy[target]>>8)&255]))
    def near_jmp(label,target):
        opcode(label,bytes([0x4C,sy[target]&255,(sy[target]>>8)&255]))
    near_jsr('Q8DirectScratch','WarmDirectPair')
    near_jsr('Q8StageCopy','Q7SourceFromIndex')
    near_jsr('Q8StagedPair','Q7SourceFromIndex')
    near_jmp('Q8DirectComplete','NbPairComplete')
    opcode('Q8ScratchNoStage',bytes.fromhex('af60d642'))  # LDA long queue count
    policy=compiled[offset(sy['Q7PolicyBegin']):offset(sy['Q7PolicyDone'])]
    limit_write_pcs=policy_write_completions(policy,sy['Q7PolicyBegin'])
    # Existing original ROM helper instruction bytes are preserved except for
    # references into the moved A000 part, which q7 audits operand by operand.
    expected,fixups=q7.helper_relocations(base_rom,compiled,old,wanted,oldsy,sy)
    expected=bytearray(expected)
    start=offset(0x39A000);end=offset(sy['NbCodeEnd'])
    expected[start:end]=compiled[start:end]
    require(expected==rom,'UNAUTHORIZED_ROM_BYTE')
    # The underlying bank-42 direct routine and its two DMA completion markers
    # must be the exact accepted bytes: the code itself is NOT rewritten.
    begin=offset(sy['WarmDirectPair']);end_direct=offset(sy['OnlineDmaDone9'])+3
    require(base_rom[begin:end_direct]==rom[begin:end_direct],
            'DIRECT_SCRATCH_DMA_CHANGED')
    require(q8.NEW_LIMIT_WORD not in (0x42D670,0x42D674) and
            sum(' $42D676' in line for line in wanted)==4,'NEW_METADATA_LEASE_UNEXPECTED')
    return dict(status='PASS',branch_sites=branches,
         accepted_rom_sha=q8.BASE_ROM_SHA256,old_A000_end=oldsy['NbCodeEnd'],
         new_A000_end=sy['NbCodeEnd'],new_A000_bytes=sy['NbCodeEnd']-oldsy['NbCodeEnd'],
         helper_operand_only_fixups=fixups,packet_source_index7=[q8.SCRATCH_HIGH,q8.SCRATCH_LOW],
         eighth_physical_slot_word=0x42D670,limit_word=0x42D676,
         limit_write_callback_pcs=limit_write_pcs,
         full_other_rom_identity=True,additional_header_bytes=2,
         no_new_RAM_region=True,no_additional_VRAM=True)


def candidate_home_certifier(folder):
    """Original full 64KiB replay/source oracle with only two queue limits edited."""
    import m4_home_borrow_evidence as home
    code=textwrap.dedent(inspect.getsource(home.certify))
    edits={
      "high['source'] not in range(0x3500,0x36e0,80)":
       "high['source'] not in (*range(0x3500,0x36e0,80),0x34b0,0x42d680)",
      'not 1<=count<=6':'not 1<=count<=8',
    }
    for old,new in edits.items():
        if code.count(old)!=1:raise ValueError('Q8_ORIGINAL_HOME_ORACLE_DRIFT:'+old)
        code=code.replace(old,new,1)
    scope=dict(home.__dict__,audit_rom=audit_rom)
    require(code.count('def certify(')==1,'ORIGINAL_HOME_CERTIFIER_CHANGED')
    exec(code.replace('def certify(','def certify_q8(',1),scope)
    return scope['certify_q8'](folder)


def candidate_right_certifier(folder,contract,fields):
    """Same independently verified RIGHT oracle; add only Q7+Q8 exact sources."""
    q7=prior();code=textwrap.dedent(inspect.getsource(q7.ORIGINAL_RIGHT_CERTIFIER))
    edits={
      "h['source'] not in range(0x3500,0x36e0,80)":
       "h['source'] not in (*range(0x3500,0x36e0,80),0x34b0,0x42d680)",
      '(0x3500+80*i,0x3540+80*i)':
       '((0x42d680,0x42d6c0) if i==7 else (0x34b0,0x34f0) if i==6 else (0x3500+80*i,0x3540+80*i))',
      "0x3500<=e['source']<0x36e0":
       "(0x34b0<=e['source']<0x36e0 or 0x42d680<=e['source']<0x42d6d0)",
    }
    for old,new in edits.items():
        if code.count(old)!=1:raise ValueError('Q8_ORIGINAL_RIGHT_ORACLE_DRIFT:'+old)
        code=code.replace(old,new,1)
    require(code.count('def certify(')==1,'ORIGINAL_RIGHT_CERTIFIER_CHANGED')
    import m4_nonblank_batch_native as right
    scope=dict(right.__dict__,audit_rom=audit_rom)
    exec(code.replace('def certify(','def certify_right_q8(',1),scope)
    return scope['certify_right_q8'](folder,contract,fields)


def _patch_q7_observer(text):
    """Move Q7 limit from now-live eighth slot and retain all Q7 write guards."""
    original='nbWord(0x42d670)'
    n=text.count(original)
    if n!=4:raise ValueError('Q8_Q7_OBSERVER_ADDRESS_DRIFT:'+str(n))
    text=text.replace(original,'nbWord(0x42d676)')
    old='records<=12 and mode~=2 and 7 or 6'
    if text.count(old)!=1:raise ValueError('Q8_Q7_OBSERVER_POLICY_DRIFT')
    text=text.replace(old,'records<=12 and mode~=2 and 8 or 6')
    token='nbWord(0x42d676)~=7'
    if text.count(token)!=3:raise ValueError('Q8_Q7_OBSERVER_SEVEN_POLICY_DRIFT')
    text=text.replace(token,'nbWord(0x42d676)~=8')
    return text


def observer(script,contract):
    saved_observer,_=original_q7_functions()
    # q7.observer invokes the full accepted shared observer and extends it;
    # temporarily use a private output from q7 then minimally rewrite its
    # four existing limit reads in our new script, never an old file.
    # q7.observer itself calls ORIGINAL_SHARED_OBSERVER by captured function.
    saved_observer(script,contract)
    content=_patch_q7_observer(script.read_text())
    sy=contract['native_symbols']
    limit_pc_guard=' and '.join('pc~='+str(pc) for pc in
                                contract['eight_pair_audit']['limit_write_callback_pcs'])
    def cb(name,body):
        return (f'emu.addMemoryCallback(function() {body} end,emu.callbackType.exec,'
                f'{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n')
    # Q8ScratchNoStage is the merge of BOTH staging and skipped paths;
    # only queue index 7 takes the scratch lease. Indexed identity D670 is
    # already written before the merge; pending count still equals seven.
    content+='local q8Held=false;local q8Raw=nil;local q8Slot=nil\n'
    content+=cb('Q8ScratchNoStage',
       "if nbWord(0x3470)==7 then "
       "if q8Held or nbWord(0x42d676)~=8 or nbWord(0x42d606)>12 or "
       "nbWord(0x42d602)==2 or nbWord(0x42d660)~=7 then nbLog('FAULT','Q8_SCRATCH_LIFETIME')end;"
       "q8Held=true;q8Raw=cpDump(0x42d680,80);q8Slot=nbWord(0x42d670);"
       "nbLog('Q8_HELD',nbTxn..'|'..q8Slot..'|'..q8Raw) "
       "elseif nbWord(0x3470)>7 then nbLog('FAULT','Q8_QUEUE_INDEX')end")
    content+=cb('Q8DirectScratch',
       "if not q8Held or nbWord(0x3470)~=7 or nbWord(0x42d660)~=8 or "
       "nbWord(0x42d670)~=q8Slot or cpDump(0x42d680,80)~=q8Raw then "
       "nbLog('FAULT','Q8_SCRATCH_CHANGED_OR_INDEX')end;"
       "nbLog('Q8_DIRECT',nbTxn..'|'..q8Slot..'|'..cpDump(0x42d680,80))")
    content+=cb('Q8DirectComplete',
       "if not q8Held then nbLog('FAULT','Q8_COMPLETE_WITHOUT_HOLD')end;"
       "nbLog('Q8_FENCED',nbTxn..'|'..q8Slot);q8Held=false")
    for name in ('NbVisible','NbAbort','BhRollbackFinished','BhRollbackEmpty'):
        content+=cb(name,"if q8Held then nbLog('FAULT','Q8_UNRELEASED_SCRATCH')end")
    # No BW-RAM compositor or CPU may touch the live eighth pair before DMA.
    for cpu in ('snes','sa1'):
        content+=("emu.addMemoryCallback(function(a,v)local s=emu.getState();"
          "local pc=s['cpu.pc']+65536*s['cpu.k'];"
          f"if '{cpu}'~='snes' or ({limit_pc_guard}) "
          "then nbLog('FAULT','Q8_LIMIT_WRITE_OWNER:'..a..'|'..pc)end end,"
          f"emu.callbackType.write,0x2d676,0x2d677,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
        content+=("emu.addMemoryCallback(function(a,v)local s=emu.getState();"
          "local pc=s['cpu.pc']+65536*s['cpu.k'];"
          f"if '{cpu}'~='snes' or pc<{sy['NbQueueSpace']} or pc>={sy['NbFlushQueue']} "
          "or nbWord(0x42d676)~=8 or nbWord(0x42d660)~=7 "
          "then nbLog('FAULT','Q8_SLOT_WRITE_OWNER:'..a..'|'..pc)end end,"
          f"emu.callbackType.write,0x2d670,0x2d671,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
    for cpu in ('snes','sa1'):
        content+=("emu.addMemoryCallback(function(a,v)if q8Held then "
            "nbLog('FAULT','Q8_SCRATCH_WRITTEN:"+cpu+"|'..a)end end,"
            f"emu.callbackType.write,0x2d680,0x2d6cf,emu.cpuType.{cpu},emu.memType.snesSaveRam)\n")
    content+=cb('Q7PolicyDone',
       "if nbWord(0x42d676)~=((nbWord(0x42d606)<=12 and nbWord(0x42d602)~=2) and 8 or 6) "
       "then nbLog('FAULT','Q8_LIMIT_POLICY')end")
    script.write_text(content)



def presentation_windows(folder):
    """Reuse Q7's exact batch/fence/map clock audit with 8-source policy.

    The base audit verifies complete-batch margins, 2*count packets, exact
    source sequence, both HIGH/LOW VRAM word relationships, VBlank margins and
    map-commit completion. Only the capacity/source-address oracle changes.
    """
    q7=prior()
    _,saved_windows=original_q7_functions()
    def source_address(index,records,mode=0):
        return q8.output_sources(index,records,mode)[0]
    with patch.object(q7.q7,'queue_limit',q8.queue_capacity),\
         patch.object(q7.q7,'queue_address',source_address):
        return saved_windows(folder)


def packet_evidence(folder):
    """Audit eighth scratch source byte-for-byte against its held 80B payload."""
    events=[]
    for line in (Path(folder)/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'callback_owner.lua:' in line:raise ValueError('Q8_LUA_CALLBACK_ERROR:'+line)
        if 'NB_' not in line:continue
        parts=line[line.index('NB_'):].split('|')
        if parts[0]=='NB_FAULT':raise ValueError('Q8_NATIVE_SAFETY:'+'|'.join(parts[4:]))
        events.append(dict(kind=parts[0][3:],clock=int(parts[1]),txn=parts[4] if len(parts)>4 else None,
                           data=parts[4:]))
    policies={};held=[];direct=[];fenced=[];packets=[];done=[]
    for event in events:
        d=event['data'];kind=event['kind']
        if kind=='Q7_POLICY':
            txn,records,mode,cap=map(int,d[:4]);policies.setdefault(txn,[]).append((records,mode,cap))
            if cap!=q8.queue_capacity(records,mode):raise ValueError('Q8_POLICY_MISMATCH')
        if kind=='Q8_HELD':
            txn,slot,data=d[:3];held.append(dict(txn=int(txn),slot=int(slot),data=bytes.fromhex(data),clock=event['clock']))
        if kind=='Q8_DIRECT':
            txn,slot,data=d[:3];direct.append(dict(txn=int(txn),slot=int(slot),data=bytes.fromhex(data),clock=event['clock']))
        if kind=='Q8_FENCED':
            txn,slot=d[:2];fenced.append(dict(txn=int(txn),slot=int(slot),clock=event['clock']))
        if kind=='PACKET':
            txn,target,word,source,size=d[:5]
            packets.append(dict(txn=int(txn),target=int(target),word=int(word),source=int(source),size=int(size),
                                payload=bytes.fromhex(d[5]),clock=event['clock']))
        if kind=='DONE':
            txn,source,size,target=d[:4]
            done.append(dict(txn=int(txn),source=int(source),size=int(size),target=int(target),clock=event['clock']))
    # Original cold DMA can also use WarmDirectPair; only after a Q8 policy
    # is active does scratch DMA require an eighth-slot lease.
    warm_policy_txns=set(policies)
    scratch_high=[p for p in packets if p['source']==q8.SCRATCH_HIGH and p['txn'] in warm_policy_txns]
    scratch_low=[p for p in packets if p['source']==q8.SCRATCH_LOW and p['txn'] in warm_policy_txns]
    if not (len(held)==len(direct)==len(fenced)==len(scratch_high)==len(scratch_low)):
        raise ValueError('Q8_INCOMPLETE_ZERO_COPY_PAIR')
    for h,b,e,hi,lo in zip(held,direct,fenced,scratch_high,scratch_low):
        if h['txn']!=b['txn'] or h['slot']!=b['slot'] or h['data']!=b['data'] or \
           len(h['data'])!=80 or h['txn']!=e['txn'] or e['slot']!=h['slot'] or \
           (hi['txn'],hi['target'],hi['size'],hi['word'],hi['payload']) != \
           (h['txn'],0x18,64,h['slot']*32,h['data'][:64]) or \
           (lo['txn'],lo['target'],lo['size'],lo['word'],lo['payload']) != \
           (h['txn'],0x18,16,0x6000+h['slot']*8,h['data'][64:]) or \
           not h['clock']<b['clock']<=hi['clock']<lo['clock']<e['clock']:
            raise ValueError('Q8_SCRATCH_CONTENT_OR_DMA_PAIR_DRIFT')
        for p in (hi,lo):
            if not any(t['txn']==p['txn'] and t['source']==p['source'] and
                       t['size']==p['size'] and t['target']==p['target'] and
                       p['clock']<t['clock']<e['clock'] for t in done):
                raise ValueError('Q8_MISSING_DMA_COMPLETION_FENCE')
        if not any(cap==8 and records<=12 and mode!=2 for records,mode,cap in policies.get(h['txn'],[])):
            raise ValueError('Q8_SCRATCH_DMA_WITHOUT_POLICY')
    seventh=[p for p in packets if p['source']==0x34B0 and p['size']==64]
    q7_resolves=[x for x in events if x['kind']=='Q7_SOURCE7']
    if len(q7_resolves)<len(seventh):
        raise ValueError('Q8_EXISTING_SEVENTH_SOURCE_OBSERVATION_MISSING')
    return dict(policy={str(k):v for k,v in policies.items()},eighth_high_pairs=len(scratch_high),
                eighth_transactions=[x['txn'] for x in scratch_high],
                high_source=q8.SCRATCH_HIGH,low_source=q8.SCRATCH_LOW,
                source_payloads_identical=True,all_eighth_fences_complete=True)


def certify(folder):
    import m4_home_borrow_bitmap_native as bm
    import m4_restore_single_pass_native as single
    import m4_bitmap_shared_native as shared
    result=candidate_home_certifier(folder)
    result['bitmap']=bm.bitmap_evidence(folder)
    result['single_pass_restoration']=single.evidence(folder)
    result['shared_cells']=shared.shared_evidence(folder)
    result['eight_pair']=packet_evidence(folder)
    result['presentation_windows']=presentation_windows(folder)
    result['classification']='EIGHT_PAIR_DIRECT_NATIVE_CORRECT'
    (Path(folder)/'eight-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result



def certify_right(folder):
    """Native re-certification of RIGHT using the full original pixel oracle."""
    import m4_source_safepoint_native as safe
    import m4_nonblank_batch_native as right
    import m4_home_borrow_bitmap_native as bm
    import m4_restore_single_pass_native as single
    import m4_bitmap_shared_native as shared
    contract=json.loads((folder/'contract.json').read_text())
    fields=json.loads((folder/'fields.json').read_text())
    with patch.object(safe,'audit_rom',audit_rom),\
         patch.object(right,'certify',candidate_right_certifier):
        result=safe.certify(folder,contract,fields)
    require(result['classification']=='BYOR_MOTU_SOURCE_SAFEPOINT_PASS',
            'RIGHT_ORIGINAL_SOURCE_SAFETY')
    result['bitmap']=bm.bitmap_evidence(folder)
    result['single_pass_restoration']=single.evidence(folder)
    result['shared_cells']=shared.shared_evidence(folder)
    require(not result['bitmap']['plans'] and not result['shared_cells'],
            'RIGHT_UNEXPECTED_BITMAP')
    result['eight_pair']=packet_evidence(folder)
    result['presentation_windows']=presentation_windows(folder)
    result['classification']='EIGHT_PAIR_RIGHT_CONTROL'
    (folder/'eight-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def build(folder,base=BASE,dotnet=None,poppy=None):
    from actor_s5_entity_fixture import symbols
    from m4_input_controller_native import offset
    if folder.exists():raise ValueError('Q8_USE_FRESH_OUTPUT_DIR')
    base=Path(base)
    if sha(base/'bor.sfc')!=q8.BASE_ROM_SHA256:raise ValueError('Q8_BASE_ROM_CHANGED')
    old=(base/'publisher.pasm').read_text().splitlines()
    wanted=q8.transform(old)
    native=folder/'native';native.mkdir(parents=True)
    (native/'publisher.pasm').write_text('\n'.join(wanted)+'\n')
    dotnet=dotnet or Path(os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe'))
    poppy=poppy or Path(os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll'))
    result=subprocess.run([str(dotnet),str(poppy),str(native/'publisher.pasm'),
                           '--output',str(native/'publisher.bin'),
                           '--symbols',str(native/'publisher.sym'),'--no-pansy'],capture_output=True,text=True)
    (native/'publisher-build.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise ValueError('Q8_POPPY_ASSEMBLY; inspect publisher-build.log')
    sy=symbols(native/'publisher.sym');oldsy=symbols(base/'publisher.sym')
    oldrom=(base/'bor.sfc').read_bytes();compiled=(native/'publisher.bin').read_bytes()
    expected,fixups=prior().helper_relocations(oldrom,compiled,old,wanted,oldsy,sy)
    rom=bytearray(expected)
    start=offset(0x39A000);end=offset(sy['NbCodeEnd'])
    rom[start:end]=compiled[start:end]
    audit=audit_rom(rom,native)
    (native/'bor.sfc').write_bytes(rom)
    contract=copy.deepcopy(json.loads((base.parent/'contract.json').read_text()))
    contract['native_symbols'].update(sy)
    contract.update(eight_pair_direct=True,eight_pair_audit=audit,
         eighth_scratch_pair=[q8.SCRATCH_HIGH,q8.SCRATCH_END],
         eighth_slot_word=q8.SLOT8_WORD,queue_capacity_word=q8.NEW_LIMIT_WORD)
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    import m4_restore_single_pass_native as single
    (native/'callback_owner.lua').write_text(single.bootstrap_prefix((base/'callback_owner.lua').read_text()))
    os.link((base/'bor.msu').resolve(),native/'bor.msu')
    return contract


def run_case(folder,case):
    q7=prior()
    original_q7_functions()
    # Q7's real controller/fixture driver is reused unchanged, including all
    # authentic source operations and fault injection. The native certifiers
    # are extended only for exact eighth queue metadata and BW-RAM scratch DMA.
    with patch.object(q7,'observer',observer),patch.object(q7,'audit_rom',audit_rom),\
         patch.object(q7,'certify',certify),patch.object(q7,'packet_evidence',packet_evidence),\
         patch.object(q7,'candidate_home_certifier',candidate_home_certifier),\
         patch.object(q7,'candidate_right_certifier',candidate_right_certifier),\
         patch.object(q7,'presentation_windows',presentation_windows):
        result=q7.run_case(folder,case)
    if case=='right':return certify_right(folder)
    return certify(folder)


def verify_pool_identity(actual,accepted,case):
    """Compare the same pool fields across live int keys and JSON str keys."""
    normalized={str(key):value for key,value in actual.items()}
    require(len(normalized)==len(actual),case+':AMBIGUOUS_POOL_TRANSACTION')
    for txn,accepted_pool in accepted.items():
        key=str(txn)
        require(key in normalized,case+':MISSING_POOL_TRANSACTION:'+key)
        actual_pool=normalized[key]
        require(all(actual_pool[k]==accepted_pool[k] for k in
                    ('homes','original_invalid','original_valid','policy','limit','need')),
                case+':BORROWING_ORDER_CHANGED:'+key)


def verify_partial_fallback(evidence):
    # packet_evidence stores (completed records, fault mode, capacity).
    policies=evidence['policy'].get('3',[])
    require(bool(policies) and all(len(row)==3 and tuple(row[1:])==(2,6) for row in policies)
            and 3 not in evidence['eighth_transactions'],'PARTIAL_MODE_2_USED_DIRECT_PAIR')


def collect_suite(root,baseline_root=BASELINE):
    base=json.loads(RECEIPT.read_text())
    results={}
    for name in CASES:
        child=root/name
        result=certify_right(child) if name=='right' else certify(child)
        require(result['pixel_mismatches']==result['resource_faults']==result['unsafe_ppu_operations']==0,name+':NATIVE_PIXELS_OR_RESOURCE')
        require(result['eight_pair']==packet_evidence(child),name+':Q8_TRACE_CHANGED')
        require(result['min_batch_margin_clocks']>=10000,name+':BATCH_VBLANK')
        require(all(x['margin_clocks']>=10000 for x in result['presentation_windows']['batches']),name+':COMPLETE_BATCH_MARGIN')
        require(all(x['margin_clocks']>=10000 for x in result['presentation_windows']['maps']),name+':MAP_COMMIT_MARGIN')
        baseline=base['cases'][name]
        for suffix in ('world','committed','pending','refs','cgram'):
            for file in (child/'native').glob('*-'+suffix+'.bin'):
                original=baseline_root/name/'native'/file.name
                require(original.exists() and original.read_bytes()==file.read_bytes(),name+':NATIVE_SOURCE_OR_STATE_DRIFT:'+file.name)
        # Different emulator runs can retain distinct unreferenced startup CHR.
        # But every PHYSICALLY REFERENCED HIGH/LOW pair and both maps must be
        # byte-identical to the accepted seven-pair renderer at checkpoints.
        for file in (child/'native').glob('*-vram.bin'):
            if file.name in ('initial-vram.bin','handoff-vram.bin'):continue
            accepted=baseline_root/name/'native'/file.name
            require(accepted.exists(),'MISSING_ACCEPTED_VRAM:'+file.name)
            a=file.read_bytes();b=accepted.read_bytes()
            require(len(a)==len(b)==65536 and a[61440:]==b[61440:],name+':VRAM_MAP_DRIFT:'+file.name)
            slots={int.from_bytes(a[j:j+2],'little')&0x3fff for j in range(61440,65536,2)}
            require(all(k<768 and
                        a[64*k:64*(k+1)]==b[64*k:64*(k+1)] and
                        a[49152+16*k:49152+16*(k+1)]==b[49152+16*k:49152+16*(k+1)]
                        for k in slots),name+':REFERENCED_CHR_DRIFT:'+file.name)
        if name!='right':
            require(result['source_pixel_difference']==1816,name+':SOURCE_CHANGED_PIXELS')
            if 'pools' in baseline:
                verify_pool_identity(result['pools'],baseline['pools'],name)
        results[name]=result
    success=results['success'];baseline=base['cases']['success']
    a,b=success['transactions'][:2];oa,ob=baseline['transactions'][:2]
    require(a['fields']<=25 and a['master_clocks']<=1.01*oa['master_clocks'],'EPOCH2_REGRESSION')
    require(b['fields']<=36 and b['master_clocks']<ob['master_clocks'],'EPOCH3_NOT_IMPROVED')
    batches=[x for x in success['batches'] if x['transaction']==3]
    require(len(batches)==14 and [int(x['pairs']) for x in batches]==[8]*13+[1],
            'Q8_EXPECT_14_BATCHES')
    require(success['eight_pair']['eighth_transactions'].count(3)==13,'Q8_EXPECT_13_DIRECT_PAIRS')
    transfer=next(x for x in success['transfers'] if x['transaction']==3)
    require((transfer['chr_pairs'],transfer['chr_bytes'],transfer['map_bytes'],transfer['descriptors'])==(105,8400,4096,212),
            'UNCHANGED_TRANSFER_CONTENT')
    plan=next(p for p in success['ready_residency_checks'] if p['transaction']==3)
    require((plan['actor_tiles'],len(plan['restoration_homes']),plan['tail_reservations'],plan['borrowed_reservations'])==
            (95,10,64,41),'UNCHANGED_RESERVATIONS')
    require(success['source_pixel_difference']==1816,'UP_SOURCE_PIXELS_DRIFT')
    refs=(root/'success/native/after-second-refs.bin').read_bytes()
    require(len(refs)==1536 and sum(bool(int.from_bytes(refs[i:i+2],'little')&0x3fff)
                                    for i in range(0,1536,2))==639,'FINAL_REFERENCED_639')
    require(any(x['transaction']==4 and x['home']==204 and x['destination']==634 and not x['rollback']
                for x in results['valid']['backdrop_restorations']), 'HOME204_RESTORATION_CHANGED')
    for mode in ('early','ready','partial','stale'):
        require(results[mode]['validity_clear_events'],mode+':VALID_HOME_ROLLBACK')
    verify_partial_fallback(results['partial']['eight_pair'])
    require(next(t for t in results['insufficient']['transfers'] if t['transaction']==3)['descriptors']==0,
            'INSUFFICIENT_BUDGET_DMA')
    require(results['right']['transition_fields']<=base['cases']['right']['transition_fields'],
            'RIGHT_GAINED_FIELD')
    import m4_bitmap_shared_native as shared
    dirty=shared.inherited_fingerprints(json.loads(Path('docs/receipts/byor-motu-restore-single-pass.json').read_text()))
    require(len(dirty)==29 and all(sha(x['path'])==x['sha256'] for x in dirty),
            'INHERITED_DIRTY_FILES_CHANGED')
    require(not Path('SNES-BOR-Engine-Prompt.md').exists(),'UNRELATED_DELETION_CHANGED')
    report=dict(classification='BYOR_MOTU_EIGHT_PAIR_DIRECT_PASS',
        starting_commit=q8.BASE_COMMIT,
        original_sha256=q8.BASE_ROM_SHA256,
        observed_fields=sum(v['observed_fields'] for v in results.values()),
        verified_rgb555_pixels=sum(v['verified_pixels'] for v in results.values()),
        pixel_mismatches=0,resource_faults=0,unsafe_ppu_operations=0,
        cases=results,epoch2=a,epoch3=b,eighth_sources=[q8.SCRATCH_HIGH,q8.SCRATCH_LOW],
        transaction_header_new_bytes=2,no_new_ram_region=True,nonclaims=['30 FPS','200 Hz','SA-1 concurrency','audio','HUD','combat','Demo completion'])
    (root/'eight-pair-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--suite',action='store_true')
    p.add_argument('--collect-suite',action='store_true')
    p.add_argument('--build-only',action='store_true')
    p.add_argument('--base-native',type=Path,default=BASE)
    p.add_argument('--baseline-root',type=Path,default=BASELINE)
    p.add_argument('--dotnet',type=Path,default=Path(os.environ.get('DOTNET_EXE','C:/Users/chad/.dotnet/dotnet.exe')))
    p.add_argument('--poppy',type=Path,default=Path(os.environ.get('POPPY_DLL','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll')))
    p.add_argument('--case',choices=CASES,default='success')
    a=p.parse_args();root=a.output.resolve()
    if a.collect_suite:
        result=collect_suite(root,a.baseline_root)
        print(result['classification'],result['observed_fields'],result['verified_rgb555_pixels'])
        return
    if a.suite:
        if root.exists():raise ValueError('Q8_SUITE_MUST_USE_NEW_DIRECTORY')
        if not a.build_only:configure_capture_runtime(root)
        for name in CASES:
            child=root/name
            print('Q8 NATIVE CASE',name,flush=True)
            build(child,a.base_native,a.dotnet,a.poppy)
            if not a.build_only:run_case(child,name)
        if not a.build_only:
            result=collect_suite(root,a.baseline_root)
            print(result['classification'],result['observed_fields'],result['verified_rgb555_pixels'])
    else:
        if root.exists():raise ValueError('Q8_SINGLE_CASE_MUST_USE_NEW_DIRECTORY')
        if not a.build_only:configure_capture_runtime(root)
        build(root,a.base_native,a.dotnet,a.poppy)
        if not a.build_only:run_case(root,a.case)

if __name__=='__main__':main()
