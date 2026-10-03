"""Controlled entity binding in a private production-ROM clone.

Never writes main.pasm, build_rom.py, production ROM/MSU or compiler files.
Loads real packed actors through Anim_LoadCharacter_Long from a clone-only
central entity-update hook, with a separate legacy HitApply guard. Flags and frames are
controlled preconditions, NOT an organic source behavior/spawn certificate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from actor_s5_isolated import (ROOT, Source, parse_model, lower_model,
                               pack_source_frame, frame_bytes, sha, protected,
                               collision_expected)
from actor_frame_abi import check_actor_media_extent
from actor_catalog import generate_catalog
from analyze import scoped_id


def symbols(path):
    out={}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        match=re.match(r'([0-9A-Fa-f]+):([0-9A-Fa-f]+)\s+(\S+)',line)
        if match:
            out.setdefault(match[3],(int(match[1],16)<<16)|int(match[2],16))
    return out


def make_clone(folder):
    sym=symbols(ROOT/'src/main.sym')
    original=(ROOT/'distribution/bor.sfc').read_bytes()
    entry=sym['Character_HitApply']
    entity_entry=sym['CharacterEntity_Play']
    entity_displaced=b'\xc2\x31\x0b\x22'+sym['G13_PlayerLifecycleIsOut'].to_bytes(3,'little')
    assert original[entity_entry-0x8000:entity_entry-0x8000+7]==entity_displaced
    done=sym['Character_HitApply__done']
    assert entry<65536 and done<65536
    displaced=bytes([0xe2,0x20,0xa5,sym['CHAR_SELECTED']])
    assert original[entry-0x8000:entry-0x8000+4]==displaced,'symbol/ROM prologue disagreement'
    assert original[done-0x8000:done-0x8000+3]==bytes([0xc2,0x31,0x60]),'symbol/ROM return disagreement'
    bank=31
    start=bank*32768
    assert original[start:start+32768]==bytes(32768),'clone insertion bank is occupied'
    constants={'Game_Selected':'CHAR_SELECTED','Game_Roster':'CHAR_ROSTER_INDEX',
        'Game_SelectIndex':'CharSelect_Index','Game_SelectLoaded':'CharSelect_Loaded',
        'Game_LoadCharacterLong':'Anim_LoadCharacter_Long','Game_Frame':'CHAR_FRAME_INDEX',
        'Game_PosX':'CHAR_POS_X','Game_PosY':'CHAR_POS_Y','Game_Facing':'CHAR_FACING_LEFT',
        'Game_Hp':'CHAR_HP','Game_HitStun':'CHAR_HIT_STUN','Game_HitApplied':'CHAR_HIT_APPLIED',
        'Game_DirectorySeek':'CharDirSeek16','Game_DirectoryBusy':'Anim_LoadCharacter__record_busy'}
    for name in ('Spawn_ScratchSlotOfs','Spawn_ScratchMap','StageEnv_ApplySpawnMap',
                 'SceneVideo_PlayState','SceneVideo_SequenceActive','SceneVideo_TestActive','Nmi_FrameCounter'):
        constants[name]=name
    asm='.snes\n'+''.join(f'{k} = ${sym[v]:X}\n' for k,v in constants.items())
    original_msu=(ROOT/'distribution/bor.msu').read_bytes()
    extension=len(original_msu)
    # Catalog-derived private arena: an ending clip, never the boot clip 1.
    directory=original_msu.index(b'BORVID1\x00')
    version,clip_count,directory_bytes=struct.unpack_from('<HHI',original_msu,directory+8)
    assert version==1 and directory_bytes==24*clip_count
    clips=[struct.unpack_from('<HHHHHHIII',original_msu,directory+16+24*i) for i in range(clip_count)]
    arena=next(c for c in clips if c[0]!=1 and c[7]+c[8]<=0x1000000 and c[8]>=65536)
    arena_start,arena_end=arena[7],arena[7]+arena[8]
    assert sym[f'SceneVideo_Record{clips.index(arena)}_PayloadOffset']==arena_start
    assert sym[f'SceneVideo_Record{clips.index(arena)}_PayloadSize']==arena[8]
    directory_hook=sym['Anim_LoadCharacter__seek_computed']
    directory_displaced=b'\xe2\x20\xaf'+sym['CharDirSeek16'].to_bytes(3,'little')
    assert original[directory_hook-0x8000:directory_hook-0x8000+6]==directory_displaced
    asm+=f'Game_DirectoryResume = ${directory_hook+6:X}\nGame_ExtendedIndex = {original_msu[9]}\n'
    asm+='Game_ExtendedCount = 2\n'
    # REP/PHD is three bytes; displaced JSL lifecycle call is four more.
    # Replay that JSL in the central trampoline before returning after 7 bytes.
    asm+=f'Game_EntityResume = ${entity_entry+7:X}\nGame_Lifecycle = ${sym["G13_PlayerLifecycleIsOut"]:X}\n'
    game_entry=sym['Game_State_Play']
    assert original[game_entry-0x8000:game_entry-0x8000+7]==b'\x08\xc2\x31\xaf'+sym['Game_State'].to_bytes(3,'little')
    asm+=f'Game_StateAddress = ${sym["Game_State"]:X}\nGame_StateResume = ${game_entry+7:X}\n'
    asm+=f'Game_HitResume = ${entry+4:X}\nGame_HitDone = ${done:X}\n.bank {bank}\n.org $8000\n'
    adapter=ROOT/'src/core/actor_s5_entity_fixture.pasm'
    core=ROOT/'src/core/actor_s5_isolated.pasm'
    catalog_core=ROOT/'src/core/actor_catalog_isolated.pasm'
    clock_core=ROOT/'src/core/actor_s5_clock_isolated.pasm'
    asm+=f'.include "{adapter.as_posix()}"\n.include "{core.as_posix()}"\n.include "{catalog_core.as_posix()}"\n.include "{clock_core.as_posix()}"\nGame_ExtDirTable:\n'
    asm+='    .db '+','.join(str(b) for i in range(2) for b in (extension+50*i).to_bytes(4,'little'))+'\n.org $C000\n'
    source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    project_id=scoped_id(source)
    actors={name:lower_model(parse_model(source,f'data/chars/{name}/{name}.txt',name,
            project_id,'historical-bor')) for name in ('Kula','Lobster','Joe','Ramon')}
    sys.path.insert(0,str(ROOT/'tools/audio'))
    import shipped_content
    configs=shipped_content.ROSTER_CONFIGS
    roster={name:next(i for i,c in enumerate(configs)
        if c['source_character'].replace('\\','/').rsplit('/',1)[-1].casefold()==name.casefold())
        for name in ('Kula','Joe')}
    roster.update(Lobster=original_msu[9],Ramon=original_msu[9]+1)
    kula_frames=next(a['frames'] for a in actors['Kula']['animations'] if a['role']=='attack1')
    data,catalog=generate_catalog(actors.values(),base_address=0x1fc000,
        pinned={tuple(a['source_identity']):roster[n] for n,a in actors.items()},
        compatibility_controls=[dict(source_identity=actors['Kula']['source_identity'],role='attack1',
            frame_bytes=b''.join(frame_bytes(f,compat=True) for f in kula_frames),
            scope='ISOLATED_GOLDEN_CONTROL',policy=dict(force=4,all_attack_state_frames=True,
                timing='4 accepted animation ticks',collision='absdx<32,absdy<64'))])
    (folder/'actor_catalog.bin').write_bytes(data)
    (folder/'actor_catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    asm=asm.replace('.snes\n',f'.snes\nCatalog_Base = $1FC000\nCatalog_ProjectLo = {catalog["project_token"]&65535}\nCatalog_ProjectHi = {catalog["project_token"]>>16}\n')
    tables={}
    for name,role in [('Kula','attack1'),('Lobster','fall'),('Joe','idle')]+[
            ('Ramon',a['role']) for a in actors['Ramon']['animations']]:
        frames=next(a['frames'] for a in actors[name]['animations'] if a['role']==role)
        packed=b''.join(pack_source_frame(frame) for frame in frames)
        assert packed==b''.join(frame_bytes(frame) for frame in frames)
        row=next(r for r in catalog['entries'] if r['actor_id']==roster[name] and r['role']==role and r['profile']==1)
        assert data[row['address']-0x1fc000:row['address']-0x1fc000+len(packed)]==packed
        tables[name if name!='Ramon' else 'Ramon_'+role]=dict(role_id=row['role_id'],frames=frames,
                                                          source_identity=row['identity'])
    tables['Compat']=dict(tables['Kula'])
    asm+='\n'.join('    .db '+','.join(f'${b:02X}' for b in data[i:i+16]) for i in range(0,len(data),16))+'\n'
    pasm=folder/'adapter.pasm';pasm.write_text(asm)
    shutil.copy2(ROOT/'src/main.sym',folder/'production.sym')
    dotnet=os.environ.get('DOTNET_EXE',r'C:\Users\chad\.dotnet\dotnet.exe')
    poppy=os.environ.get('POPPY_DLL',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')
    result=subprocess.run([dotnet,poppy,str(pasm),'-s',str(folder/'adapter.sym')],capture_output=True,text=True)
    (folder/'poppy.log').write_text(result.stdout+result.stderr)
    if result.returncode or 'warning' in (result.stdout+result.stderr).lower():
        raise RuntimeError(result.stdout+result.stderr)
    emitted=pasm.with_suffix('.bin').read_bytes()
    payload=emitted[start:]
    assert len(payload)<=32768 and payload[:2]==b'\xc2\x30'
    assert payload[0x4000:]==data
    clone=bytearray(original)
    clone[start:start+len(payload)]=payload
    adapter_symbols=symbols(folder/'adapter.sym')
    nmi_return=sym['nmi_handler']+3
    assert original[nmi_return-0x8000:nmi_return-0x8000+4]==b'\x40\0\0\0'
    clone[nmi_return-0x8000:nmi_return-0x8000+4]=b'\x5c'+adapter_symbols['S5Entity_NmiClock'].to_bytes(3,'little')
    guard=adapter_symbols['S5Entity_LegacyHitGuard']
    clone[entry-0x8000:entry-0x8000+4]=b'\x5c'+guard.to_bytes(3,'little')
    clone[entity_entry-0x8000:entity_entry-0x8000+7]=bytes([0x5c,0,0x80,bank,0xea,0xea,0xea])
    clone[game_entry-0x8000:game_entry-0x8000+7]=b'\x5c'+adapter_symbols['S5Entity_GameDiagnostic'].to_bytes(3,'little')+b'\xea'*3
    directory_entry=symbols(folder/'adapter.sym')['S5Entity_Directory']
    clone[directory_hook-0x8000:directory_hook-0x8000+6]=b'\x5c'+directory_entry.to_bytes(3,'little')+b'\xea\xea'
    clone[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    checksum=sum(clone)&65535
    struct.pack_into('<HH',clone,0x7fdc,checksum^65535,checksum)
    rom=folder/'bor.sfc';rom.write_bytes(clone)
    shutil.copy2(ROOT/'distribution/bor.msu',folder/'bor.msu')
    # Read-only media reuse by hardlink; Mesen never writes input PCM files.
    for pcm in (ROOT/'distribution').glob('bor-*.pcm'):
        os.link(pcm,folder/pcm.name)
    # Golden roster identities from the actual immutable metadata artifact;
    # model names select tests only, no name comparisons enter runtime code.
    # ROSTER_CONFIGS comes from shipped_content; import for read-only metadata.
    sys.path.insert(0,str(ROOT/'tools/audio'))
    import shipped_content
    configs=shipped_content.ROSTER_CONFIGS
    roster={name:next(i for i,c in enumerate(configs)
                      if c['source_character'].replace('\\','/').rsplit('/',1)[-1].casefold()==name.casefold())
            for name in ('Kula','Joe')}
    # Lobster is unshipped and the original directory is full. Append its
    # record AND payload; the clone-only directory hook handles the extension.
    from certify_actors import encode_probe
    from pack_msu_roster import pack_character_blob, build_record
    msu=bytearray((folder/'bor.msu').read_bytes())
    slot=msu[9]
    assert slot==len(configs) and len(msu)==extension
    media_info={};records=bytearray();blobs=bytearray()
    for index,name in enumerate(('Lobster','Ramon')):
        media_folder=folder/(name.lower()+'_media')
        media=encode_probe(source.path,dict(ir=dict(dialect='historical-bor',
                           source_path=actors[name]['source_path']),
                           actor_lowering=actors[name]),media_folder)
        blob,info=pack_character_blob(str(media_folder/'actor'),extended_maps=True)
        if name=='Ramon':
            assert len(blob)==2336, 'Ramon must have its own expected blob, no alias'
        record=build_record(info,arena_start+len(blobs))
        assert len(record)==50
        extent=check_actor_media_extent(arena_start+len(blobs),len(blob),
                                       project='s5-private-clone',model=name)
        assert 0<=extent['offset']<extent['end_exclusive']<=min(arena_end,0x1000000)
        records.extend(record);blobs.extend(blob)
        roster[name]=slot+index
        media_info[name]=dict(slot=slot+index,encoding=media,record_hex=record.hex(),
                             media_extent=extent,
                             identity='fixture-only, not accepted compatibility')
    msu[9]=slot+2
    msu.extend(records)
    original_replaced=bytes(msu[arena_start:arena_start+len(blobs)])
    msu[arena_start:arena_start+len(blobs)]=blobs
    (folder/'scene_arena_original.bin').write_bytes(original_replaced)
    (folder/'scene_arena_replacement.bin').write_bytes(blobs)
    (folder/'bor.msu').write_bytes(msu)
    # Clone-only generated count binding, so the ordinary S4 map validator
    # accepts the new actor's authored maps instead of its default zero count.
    count_address=sym['StageEnv_ModelMapCounts']+roster['Lobster']
    count_offset=(count_address>>16)*32768+(count_address&65535)-32768
    assert clone[count_offset]==0
    assert media_info['Lobster']['encoding']['palette_count']==5
    clone[count_offset]=5
    clone[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    checksum=sum(clone)&65535
    struct.pack_into('<HH',clone,0x7fdc,checksum^65535,checksum)
    rom.write_bytes(clone)
    metadata=dict(production_rom_sha256=sha(ROOT/'distribution/bor.sfc'),
        project_id=project_id,source_pak_sha256=sha(Path(source.path)),
        clone_rom_sha256=sha(rom),msu_sha256=sha(folder/'bor.msu'),
        copied_symbol_sha256=sha(folder/'production.sym'),entry_patch_address=hex(entry),
        central_entity_patch_address=hex(entity_entry),central_original_bytes=entity_displaced.hex(),
        directory_patch_address=hex(directory_hook),extended_directory_offset=extension,
        original_prologue=displaced.hex(),clone_bank=bank,roster=roster,
        adapter_sha256=sha(adapter),core_sha256=sha(core),compiler_abi_sha256=sha(ROOT/'tools/bor_compile/actor_frame_abi.py'),
        source_hashes={n:a['source_sha256'] for n,a in actors.items()})
    metadata['extended_fixture_media']=media_info
    metadata['descriptor_catalog']=dict(sha256=catalog['sha256'],project_token=catalog['project_token'],
        bytes=catalog['bytes'],entries=len(catalog['entries']),lookup_sha256=sha(catalog_core),
        binding='actual entity runtime ID + source role ID + profile + actual frame; no mailbox table pointers')
    metadata['clone_clock_hook']=dict(address=hex(nmi_return),original_bytes='40000000',
        boundary='after Core_Nmi_Play, preserving registers and original hardware RTI stack',
        production_changed=False,clock_core_sha256=sha(clock_core))
    digest=lambda b:hashlib.sha256(b).hexdigest()
    metadata['private_scene_arena']=dict(owner_scene_id=arena[0],catalog_offset=directory,
        catalog_record_hex=struct.pack('<HHHHHHIII',*arena).hex(),start=arena_start,end_exclusive=arena_end,
        original_extent_sha256=digest(original_msu[arena_start:arena_end]),
        replacement_end_exclusive=arena_start+len(blobs),replacement_bytes=len(blobs),
        original_replaced_sha256=digest(original_replaced),replacement_sha256=digest(blobs),
        whole_game_publishable=False,unused_during_controlled_playing_fixture=True)
    metadata['clone_map_count_patch']=dict(address=hex(count_address),before=0,after=5)
    return sym,tables,roster,metadata


def run_clone(folder,sym,tables,roster):
    from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact,exact_input_edge
    p1=0x0a00; target=p1+2*sym['CHAR_ZP_LEN']
    mailbox=0x7e1a00
    request=0
    results=[]
    loader_results=[];map_results=[];continuation_results=[];catalog_misses=[]
    def snap(m):
        state=m.read_memory('snesMemory',0x7e0000,65536)
        for name in ('SceneVideo_PlayState','SceneVideo_SequenceActive','SceneVideo_TestActive'):
            assert state[sym[name]&65535]==0, f'scene playback active: {name}'
        assert state[0x1af0:0x1af2]==b'\0\0', 'CPU detected scene/game-state escape'
        return state
    def w(m,off,value): m.write_u16(mailbox+off,value)
    def byte(m,base,name,value): m.write_u8(0x7e0000+base+sym[name],value)
    def word(m,base,name,value): m.write_u16(0x7e0000+base+sym[name],value)
    lua=folder/'catalog_snapshot.lua'
    lua.write_text('''local seq=0
emu.addEventCallback(function()
  seq=seq+1
  local b={}
  for p=0x7e1a00,0x7e1a7f do b[#b+1]=string.format("%02x",emu.read(p,emu.memType.snesMemory)) end
  emu.log("S5CAT|"..seq.."|"..table.concat(b))
  if emu.read(0x7e1a18,emu.memType.snesMemory)==12 and emu.read(0x7e1a02,emu.memType.snesMemory)==1 then
    local fields={}
    for key,value in pairs(emu.getState()) do
      if string.find(string.lower(key),"cpu") then fields[#fields+1]=key.."="..tostring(value) end
    end
    table.sort(fields)
    emu.log("S5CPU|"..seq.."|"..table.concat(fields,";"))
  end
end,emu.eventType.endFrame)
''')
    class CatalogSession(McpSession):
        def __enter__(self):
            import mesen_mcp.session as session_module
            def launch(argv,**kwargs): return subprocess.Popen([*argv,str(lua)],**kwargs)
            proxy=SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)
            with patch.object(session_module,'subprocess',proxy): return super().__enter__()
    with CatalogSession(rom=folder/'bor.sfc',mesen=MESEN_EXE,cwd=folder,port=_free_tcp_port(),
                    stderr_log=folder/'mesen.log') as m:
        # This is already a fresh ROM process. reset_emulator removes the
        # cold-loaded Lua callbacks in the installed binary (only its first
        # pre-reset line survived in the preserved diagnostic attempt).
        m.trace_log(1)
        run_frames_exact(m,180)
        # Direct reachable PLAYING context, not title/scene/spawn proof.
        m.write_u16(sym['Game_State'],sym['GAME_STATE_PLAYING'])
        m.write_u16(sym['Game_State']+2,sym['GAME_STATE_PLAYING'])
        # Controlled gameplay context excludes all scene playback. The reserved
        # ending clip is not used during bootstrap (boot uses clip 1).
        for name in ('SceneVideo_PlayState','SceneVideo_SequenceActive','SceneVideo_TestActive'):
            m.write_u8(sym[name],0)
        m.write_memory('snesMemory',0x7e1af0,bytes(16).hex())
        m.write_u16(0x7e1af2,1) # persistent CPU guard; mailbox clearing stops at 1A7F
        m.write_u8(sym['G13_TwoPlayerEnabled'],0)
        m.write_u8(sym['Spawn_Index'],255)
        m.write_u8(sym['Spawn_Count'],0)
        for i in range(1,6):
            base=p1+i*sym['CHAR_ZP_LEN']
            byte(m,base,'CHAR_HP',0)
            byte(m,base,'CHAR_INPUT_DRIVEN',0)
        byte(m,p1,'CHAR_HP',64)
        byte(m,target,'CHAR_HP',64)
        exact_input_edge(m,0,2)

        def transact(base,op,values):
            nonlocal request
            request+=1
            m.pause()
            # Zero mailbox while paused; arm last so no partial request runs.
            m.write_memory('snesMemory',mailbox,bytes(128).hex())
            for off,value in {0:0x53a5,4:base,6:target,8:1,0x18:request,0x1c:op,**values}.items():
                w(m,off,value)
            w(m,2,1)
            diagnostic_hooks={}
            progress=[]
            for _ in range(40):
                run_frames_exact(m,3)
                state=snap(m)
                progress.append(dict(frames=(_+1)*3,ack=struct.unpack_from('<H',state,0x1a1a)[0],
                    central_entries=struct.unpack_from('<H',state,0x1a3a)[0],
                    game_updates=struct.unpack_from('<H',state,0x1a40)[0],
                    stream_scratch_hex=state[0x2390:0x23a0].hex()))
                if struct.unpack_from('<H',state,0x1a1a)[0]==request:
                    captures=[]
                    for line in list(m._stderr_lines):
                        if line.startswith(b'S5CAT|'):
                            capture=bytes.fromhex(line.decode().strip().split('|')[2])
                            if len(capture)==128 and struct.unpack_from('<H',capture,0x1a)[0]==request:
                                captures.append(capture)
                    if not captures:
                        continue # wait boundedly for a synchronous CPU-observed acknowledgement
                    (folder/f'request_{request}_synchronous.bin').write_bytes(captures[-1])
                    (folder/f'request_{request}_progress.json').write_text(json.dumps(progress,indent=2)+'\n')
                    return state
            (folder/f'timeout_{request}.bin').write_bytes(state)
            (folder/f'timeout_{request}.json').write_text(json.dumps(
                dict(trace=m.trace_log(2000),state=m.get_state(),ppu=m.get_ppu_state(),progress=progress,
                     synchronous_mailbox=[line.decode(errors='replace') for line in list(m._stderr_lines) if b'S5CAT|' in line][-5:],
                     hooks=diagnostic_hooks,events=m.drain_notifications()),indent=2)+'\n')
            raise AssertionError(f'no central entity dispatch for request {request}, actor {base:x}; inspect saved CPU trace, not just mailbox')

        def load(base,name):
            byte(m,base,'CHAR_HP',64)
            byte(m,base,'CHAR_SELECTED',0)
            byte(m,base,'CHAR_HIT_STUN',0)
            state=transact(base,2,{0x1e:roster[name]})
            assert struct.unpack_from('<H',state,0x1a36)[0]==1, 'real MSU loader failed'
            assert state[base+sym['CHAR_ROSTER_INDEX']]==roster[name]
            loader_results.append(dict(actor=name,entity_dp=base,roster=roster[name],
                                       cpu_ack=request,loaded=1))
            (folder/'loader_cases.json').write_text(json.dumps(loader_results,indent=2)+'\n')
            run_frames_exact(m,3) # allow queued palette/frame DMA to commit

        load(target,'Joe')
        # Causal ordering probe: legacy delegate runs after source loader cases.
        for name,delegate_only in (('Kula',False),('Lobster',False),('Kula',True)):
            load(p1,name)
            table=tables[name]
            scenarios=([(f'frame{i}',i,1,1,132) for i in range(6)] +
                       [('source_miss',2,1,1,220),('compat_control_frame0',0,1,2,120)] if name=='Kula' else
                       [('fall_unflagged',1,0,1,100),('fall_projectile',1,2,1,100),
                        ('fall_attacking',1,1,1,100),('fall_frame0',0,2,1,100)])
            if delegate_only:
                scenarios=[('accepted_delegate_frame0',0,1,0,120)]
            for label,frame,flags,profile,tx in scenarios:
                # Pure preconditions; HP outcome is written by CPU execution.
                m.write_memory('snesMemory',sym['Actor_InvulnFrames'],bytes(6).hex())
                m.write_u8(sym['Player_InvulnFrames'],0)
                for base,x in ((p1,100),(target,tx)):
                    word(m,base,'CHAR_POS_X',x)
                    word(m,base,'CHAR_POS_Y',160)
                    byte(m,base,'CHAR_HP',64)
                    byte(m,base,'CHAR_HIT_STUN',255 if base==target and profile==0 else 0)
                    byte(m,base,'CHAR_HIT_APPLIED',0)
                    byte(m,base,'CHAR_FACING_LEFT',0)
                    byte(m,base,'CHAR_GRAB_TARGET',255)
                    byte(m,base,'CHAR_GRABBED_BY',255)
                    byte(m,base,'CHAR_FRAME_INDEX',frame if base==p1 else 0)
                    byte(m,base,'CHAR_TICK_COUNTER',255)
                    byte(m,base,'CHAR_SELECTED',(2 if name=='Kula' else 3) if base==p1 else 0)
                    byte(m,base,'CHAR_INPUT_DRIVEN',1 if base==p1 else 2 if profile==0 else 0)
                    byte(m,base,'CHAR_ATTACK_VARIANT',0)
                    byte(m,base,'CHAR_FALL_STATE_TIMER',0)
                tp=tables['Compat'] if profile==2 else table
                args={8:profile,0xa:flags,0xc:tp['role_id'],0x12:tables['Joe']['role_id']}
                state=transact(p1,1,args)
                (folder/f'{name}_{label}.bin').write_bytes(state)
                source_frame=table['frames'][frame]
                force=4 if profile in (0,2) else (source_frame['attack'] or {}).get('force',0)
                hit=(int(abs(100-tx)<32) if profile in (0,2) else
                     collision_expected(source_frame,tables['Joe']['frames'][0],
                         (125,200,0,1,tx*5//4,200,0,1,0)) if flags&3 and force else 0)
                actual_hp=state[target+sym['CHAR_HP']]
                assert actual_hp==64-force*hit, f'{name}/{label}: HP {actual_hp} expected {64-force*hit}'
                assert state[p1+sym['CHAR_FRAME_INDEX']]==frame, 'controlled frame advanced unexpectedly'
                if profile:
                    assert struct.unpack_from('<H',state,0x1a24)[0]==hit
                    assert struct.unpack_from('<H',state,0x1a26)[0]==force
                    assert struct.unpack_from('<H',state,0x1a38)[0]==0
                results.append(dict(actor=name,case=label,profile=profile,frame=frame,
                    source_behavior_flags=flags,hit=hit,force=force,hp_before=64,hp_after=actual_hp,
                    actual_roster=state[p1+sym['CHAR_ROSTER_INDEX']],real_entity_dispatch=True))
                (folder/'partial_cases.json').write_text(json.dumps(results,indent=2)+'\n')
                if profile==0:
                    # HP mutation alone does not prove a valid legacy return.
                    # A subsequent CPU-serviced request must succeed; this
                    # catches the preserved candidate score-tail width fault.
                    continuation=transact(p1,1,{**args,8:1,0xa:0})
                    assert continuation[target+sym['CHAR_HP']]==actual_hp
                    (folder/'post_delegate_continuation.bin').write_bytes(continuation)
                    continuation_results.append(dict(cpu_ack=request,hp=actual_hp,
                        central_entries=struct.unpack_from('<H',continuation,0x1a3a)[0],
                        game_updates=struct.unpack_from('<H',continuation,0x1a40)[0]))
            if name=='Lobster':
                blob=(folder/'lobster_media/actor.bin').read_bytes()
                # Packer places its five remaps at the end of this own blob.
                expected_maps=[blob[len(blob)-160+i*32:len(blob)-160+(i+1)*32] for i in range(5)]
                assert len(set(expected_maps))==5
                for index in (4,5,6):
                    state=transact(p1,3,{0x1e:index})
                    run_frames_exact(m,3)
                    state=snap(m)
                    cgram=m.read_memory('snesCgRam',0,512)
                    selected=index if index<=5 else 0
                    assert state[p1+sym['CHAR_MAP_INDEX']]==selected
                    palette_slot=state[p1+sym['CHAR_PALETTE_SLOT']]
                    expected=expected_maps[index-1] if selected else blob[:32]
                    actual=cgram[256+32*palette_slot:288+32*palette_slot]
                    (folder/f'lobster_map{index}_state.bin').write_bytes(state)
                    (folder/f'lobster_map{index}_cgram.bin').write_bytes(cgram)
                    assert actual==expected, f'Lobster map {index}: live CGRAM mismatch'
                    map_results.append(dict(actor=name,source_identity=table['source_identity'],
                        requested=index,selected=selected,cpu_ack=request,
                        palette_slot=palette_slot,expected_hex=expected.hex(),actual_hex=actual.hex(),
                        consumer='StageEnv_ApplySpawnMap -> Anim_ApplyMapPalette -> NMI DMA'))
                    (folder/'map_cases.json').write_text(json.dumps(map_results,indent=2)+'\n')
        load(p1,'Ramon')
        for role in ('idle','walk','pain','fall'):
            table=tables['Ramon_'+role]
            assert len(table['frames'])==1
            byte(m,p1,'CHAR_SELECTED',{'idle':0,'walk':1,'pain':0,'fall':3}[role])
            byte(m,p1,'CHAR_FRAME_INDEX',0)
            byte(m,p1,'CHAR_TICK_COUNTER',255)
            byte(m,p1,'CHAR_HIT_STUN',0)
            byte(m,target,'CHAR_FRAME_INDEX',0)
            byte(m,target,'CHAR_INPUT_DRIVEN',0)
            byte(m,target,'CHAR_HP',64)
            state=transact(p1,1,{0xa:1,0xc:table['role_id'],0x12:tables['Joe']['role_id']})
            assert state[0x1940:0x1960]==pack_source_frame(table['frames'][0])
            assert struct.unpack_from('<HH',state,0x1940)==(0,0), 'source delay/vulnerability defaults'
            assert struct.unpack_from('<HH',state,0x1a24)==(0,0)
            assert state[target+sym['CHAR_HP']]==64
            (folder/f'Ramon_{role}.bin').write_bytes(state)
            results.append(dict(actor='Ramon',role=role,profile=1,cpu_ack=request,
                actual_roster=state[p1+sym['CHAR_ROSTER_INDEX']],delay_ticks=0,vulnerable=False,
                hit=0,hp_after=64,packed_role_bound=role!='pain',
                pain_note='descriptor-only; fixed packed format omits pain' if role=='pain' else None))
            (folder/'partial_cases.json').write_text(json.dumps(results,indent=2)+'\n')
        # Fail-closed CPU lookups on a real entity: role absent, and no
        # compatibility entry for this source model. No raw pointers supplied.
        for label,profile,role_id in (('unknown_role',1,65535),
                                      ('missing_compat_model',2,tables['Ramon_idle']['role_id'])):
            byte(m,p1,'CHAR_FRAME_INDEX',0)
            state=transact(p1,1,{8:profile,0xa:1,0xc:role_id,0x12:tables['Joe']['role_id']})
            assert struct.unpack_from('<H',state,0x1a38)[0]==3
            assert struct.unpack_from('<H',state,0x19b6)[0]==1
            assert state[target+sym['CHAR_HP']]==64
            assert state[0x19b0:0x19b6]==bytes(6)
            (folder/f'catalog_{label}.bin').write_bytes(state)
            catalog_misses.append(dict(case=label,cpu_ack=request,hp=64,lookup_status=1))
        # Only initial state/role are supplied by host. Once started, the CPU
        # owns the source clock, catalog-selected animation and entity frame.
        load(p1,'Kula')
        byte(m,p1,'CHAR_SELECTED',2)
        byte(m,p1,'CHAR_FRAME_INDEX',0)
        byte(m,p1,'CHAR_TICK_COUNTER',255) # hold the accepted median scheduler
        byte(m,p1,'CHAR_HIT_STUN',0)
        byte(m,p1,'CHAR_INPUT_DRIVEN',1)
        byte(m,p1,'CHAR_ATTACK_VARIANT',0)
        state=transact(p1,4,{0xa:1,0xc:tables['Kula']['role_id'],0x10:40})
        for _ in range(30):
            if struct.unpack_from('<H',state,0x1af8)[0]: break
            run_frames_exact(m,3)
            state=snap(m)
        (folder/'clock_entity_final.bin').write_bytes(state)
        assert struct.unpack_from('<H',state,0x1af8)[0]==1, 'bounded entity clock failed to complete'
        rows=[struct.unpack_from('<6H',state,0x1d00+12*i) for i in range(40)]
        delays=[struct.unpack_from('<H',pack_source_frame(f))[0] for f in tables['Kula']['frames']]
        assert delays==[8,8,8,8,4,4]
        frame=0;remaining=delays[0];animating=1;transitions=[]
        for tick,row in enumerate(rows,1):
            remaining-=1
            if not remaining:
                if frame+1<len(delays):
                    frame+=1;remaining=delays[frame]
                else: animating=0
                transitions.append(tick)
            assert row[:5]==(tick,frame,remaining,animating,frame), f'CPU clock/entity row {tick}: {row}'
        assert state[p1+sym['CHAR_FRAME_INDEX']]==5
        intervals=struct.unpack_from('<H',state,0x1c28)[0]
        assert 1<=intervals<=24
        interval_rows=[struct.unpack_from('<HHI',state,0x1c40+8*i) for i in range(intervals)]
        assert all(parity in (0,128) and numerator==(357364 if parity else 357368)*200
                   for _,parity,numerator in interval_rows)
        assert all(a[1]!=b[1] for a,b in zip(interval_rows,interval_rows[1:])), 'NTSC parity did not alternate'
        numerator=sum(row[2] for row in interval_rows)
        assert struct.unpack_from('<I',state,0x1c30)[0]==numerator
        assert struct.unpack_from('<I',state,0x1c0c)[0]==numerator//21477270
        assert struct.unpack_from('<I',state,0x1c04)[0]==numerator%21477270
        clock_binding=dict(actor='Kula',role='attack1',source_identity=tables['Kula']['source_identity'],profile=1,
            status='PASS',cpu_start_ack=request,source_ticks_applied=40,actual_entity_frame=5,
            delay_ticks=delays,transition_ticks=transitions,master_clock_hz=21477270,
            nmi_intervals=interval_rows,rows=rows,host_frame_writes_after_start=0,
            lookup='catalog actor/role/profile/frame',production_scheduler_bound=False,
            source_raster_cadence=False,clock='rational 200Hz at private NMI-return hook, live hardware parity')
        (folder/'clock_entity.json').write_text(json.dumps(clock_binding,indent=2)+'\n')
        shot=m.take_screenshot()
        (folder/'final_screenshot.json').write_text(json.dumps(shot,indent=2)+'\n')
        (folder/'ppu.json').write_text(json.dumps(m.get_ppu_state(),indent=2)+'\n')
    return dict(status='PASS',cases=results,loaders=loader_results,maps=map_results,catalog_misses=catalog_misses,
        clock_binding=clock_binding,synchronous_acknowledgements_required=True,
        timing=[clock_binding],
        post_delegate_continuation=continuation_results,actual_entity_hp_outcomes=True,
        actual_packed_actor_loader=True,organic_attack_selection=False,organic_spawn=False,
        source_raster_alignment=False,full_damage_callback=False,full_actor_certification=False,
        production_profile0_fallback='displaced prologue replay plus original routine continuation')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-only',action='store_true')
    args=parser.parse_args()
    folder=Path(tempfile.mkdtemp(prefix='actor_s5_entity_',dir=ROOT/'out'))
    before=protected()
    report=dict(status='INCOMPLETE',output=str(folder),shared_source_concurrency=True)
    print(f'Clone output: {folder}',flush=True)
    try:
        sym,tables,roster,metadata=make_clone(folder)
        report.update(metadata)
        report['proof']={'status':'NOT_RUN'} if args.build_only else run_clone(folder,sym,tables,roster)
        report['status']='BUILD_ONLY' if args.build_only else 'PASS'
    except Exception as exc:
        report.update(status='FAIL',error=repr(exc))
        raise
    finally:
        after=protected()
        report['protected_before']=before;report['protected_after']=after
        report['concurrent_shared_source_changes']=[p for p in before if before[p]!=after.get(p)]
        report['production_artifacts_unchanged']=all(before[p]==after.get(p) for p in before
                if p.startswith(('build\\','distribution\\','build/','distribution/')))
        (folder/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
        print(f"{report['status']}: {folder/'proof.json'}",flush=True)


if __name__=='__main__':
    main()
