#!/usr/bin/env python3
"""Opt-in native Ramon/Normal5A fixture, NOT full campaign/source-world proof.

Default: source audit only. After Main authorizes serialized native use:
 BOR_TEST_ROM=build/s8_candidate/bor.sfc python tools/verify/game_s8_ramon.py
   --run --rom-sha256 HASH --msu-sha256 HASH --symbols-sha256 HASH
   --output out/s8_ramon_RUN

Legal Normal difficulty/player selection; explicit authored-predecessor stage
handoff and queue-prefix acceleration (same fixture pattern as timer_driver).
Only those routing fields, camera/queue controls, and actor POS are writable.
Never write HP, model/roster, animation, facing, timers, hits, or CPU registers.
Lua records real source spawn BEFORE one journaled POS isolation: its authored
5A position otherwise enters endhole before the combat test can run.
Compatibility pain uses hit-stun/idle; source Ramon pain shares the idle image.
No distinct ANI_PAIN state or source-exact AI/timing claim. No production edits.
"""
import argparse
import contextlib
import io
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/bor_compile'), str(ROOT/'tools/audio'), str(ROOT/'tools/verify')]
from compiler import Source, stage, project
from production_campaign import compile_queues
from shipped_content import STAGE_CONFIGS, ROSTER_CONFIGS
from game_s8_stage_bounds import sha, symbols, selected_rom_path, require_idle_emulator, Proof


def source_spec():
    physical, cfg = next((i, c) for i, c in enumerate(STAGE_CONFIGS)
                         if c['source_level'].replace('\\', '/').lower() == 'data/normal/5a.txt')
    roster, model = next((i, c) for i, c in enumerate(ROSTER_CONFIGS)
                         if c['source_character'].replace('\\', '/').lower() == 'data/chars/ramon')
    source = Source(ROOT/cfg['pak'])
    definition = source.read(model['source_definition'])
    text = definition.decode().replace('\r', '')
    anims = re.findall(r'^anim\s+(\S+)', text, re.M)
    frames = re.findall(r'^\s*frame\s+(\S+)', text, re.M)
    health = int(re.search(r'^health\s+(\d+)', text, re.M)[1])
    speed = int(re.search(r'^speed\s+(\d+)', text, re.M)[1])
    if anims != ['idle', 'walk', 'pain', 'fall'] or len(set(frames)) != 1 or health != 10 or speed != 1:
        raise AssertionError('Ramon source contract changed; review explicit sparse/pain adapter')
    ir = stage(source, cfg['source_level'])
    index, event = next((i, e) for i, e in enumerate(ir.queue) if e.character == 'Ramon')
    queue = compile_queues([cfg], ROSTER_CONFIGS)[cfg['spawn']]
    record = queue[index*10:index*10+10]
    if roster != 45 or record[9] != roster or record[7] != 6 or event.health is not None:
        raise AssertionError('actual source-derived roster/health binding changed')
    normal = next(s for s in project(source).sets if s.name == 'Normal')
    ordinal = next(i for i, e in enumerate(normal.entries)
                   if e.source_path.replace('\\', '/').lower() == 'data/normal/5a.txt')
    return dict(stage=physical, ordinal=ordinal, set_id=normal.source_id, campaign=3, set='Normal',
                roster=roster, queue_index=index, queue=queue.hex(), queue_path=cfg['spawn'],
                prefix=model['converted_prefix'], source_health=health, source_speed=speed,
                hp=record[7], source_map=event.map, source_anims=anims,
                source_definition_sha256=hashlib.sha256(definition).hexdigest(),
                source_frame_sha256=hashlib.sha256(source.read(frames[0])).hexdigest(),
                adapter='ACCEPTED_COMPAT sparse enemy; pain=hit-stun with identical authored idle image',
                nonclaims=['source-world AI/timing', 'full campaign progression', 'manual visual acceptance'])


def preflight(args, spec):
    if not os.environ.get('BOR_TEST_ROM', '').strip():
        raise AssertionError('explicit candidate BOR_TEST_ROM required')
    paths = dict(rom=selected_rom_path(), msu=selected_rom_path().with_suffix('.msu'),
                 symbols=Path(args.symbols).resolve())
    for name, path in paths.items():
        wanted = getattr(args, name+'_sha256')
        if not wanted or sha(path) != wanted.lower():
            raise AssertionError(name+' hash missing/mismatched; no native launch')
    s = symbols(paths['symbols'])
    for name in ('StageDrop_State','StageDrop_BeforeActor','Character_Throw_Play__still_air'):
        if name not in s: raise AssertionError('candidate lacks integrated drop publication: '+name)
    rom = paths['rom'].read_bytes()
    def at(name, index=0):
        a = s[name]
        return rom[((a >> 16) & 127)*0x8000+(a & 0x7fff)+index]
    if bytes(at('Character_Throw_Play__still_air',i) for i in range(3))!=bytes.fromhex('e2206b'):
        raise AssertionError('air-return observer opcode contract changed')
    if not at('BorSet_ContentAvailable', spec['set_id']) or at('BorSet_CampaignMap', spec['set_id']) != 3:
        raise AssertionError('candidate Normal gate/map not enabled; never bypass it')
    if (ROOT/spec['queue_path']).read_bytes() != bytes.fromhex(spec['queue']):
        raise AssertionError('generated queue differs from fresh strict source compilation')
    sys.path.insert(0, str(ROOT/'tools/bor_converter'))
    import pack_msu_roster as pack
    with paths['msu'].open('rb') as f:
        f.seek(pack.DIRECTORY_BASE+spec['roster']*pack.RECORD_SIZE)
        record = f.read(pack.RECORD_SIZE)
        offset = int.from_bytes(record[8:12], 'little')
        # Read-only pack of generated Ramon assets, never a synthetic actor.
        with contextlib.redirect_stdout(io.StringIO()):
            blob, info = pack.pack_character_blob(str(ROOT/spec['prefix']), extended_maps=True)
        f.seek(offset)
        if f.read(len(blob)) != blob or bytes(pack.build_record(info, offset)) != record:
            raise AssertionError('candidate Ramon media/directory differs from its own generated assets')
        if record[:3] != bytes((1, 1, 0)) or record[6] != 1 or record[12] or record[14]:
            raise AssertionError('sparse authored media counts differ; no fabricated attack/rise allowed')
        pain = pack.bake_anim_bytes(str(ROOT/(spec['prefix']+'_pain')))
        if pain != blob[32:32+768]:
            raise AssertionError('source pain no longer matches idle pixels; explicit pain adapter needed')
        # Independent allocation, not another character's directory pointer.
        f.seek(pack.DIRECTORY_BASE)
        directory = f.read(len(ROSTER_CONFIGS)*pack.RECORD_SIZE)
        offsets = [int.from_bytes(directory[i+8:i+12], 'little')
                   for i in range(0, len(directory), pack.RECORD_SIZE)]
        if offsets.count(offset) != 1:
            raise AssertionError('Ramon media aliases another roster allocation')
    spec.update(paths={k:str(v) for k,v in paths.items()}, hashes={k:sha(v) for k,v in paths.items()},
                media_offset=offset, media_sha256=hashlib.sha256(blob).hexdigest(),
                frame_bytes=blob[32:32+768].hex(), record=record.hex())
    return s


FIELDS = {'hp':('CHAR_HP',1), 'mode':('CHAR_INPUT_DRIVEN',1), 'roster':('CHAR_ROSTER_INDEX',1),
          'x':('CHAR_POS_X',2), 'y':('CHAR_POS_Y',1), 'selected':('CHAR_SELECTED',1),
          'frame':('CHAR_FRAME_INDEX',1), 'stun':('CHAR_HIT_STUN',1),
          'idle':('CHAR_IDLE_FCOUNT',1), 'walk':('CHAR_WALK_FCOUNT',1),
          'attack':('CHAR_ATTACK_FCOUNT',1), 'attack2':('CHAR_ATTACK2_FCOUNT',1),
          'attack3':('CHAR_ATTACK3_FCOUNT',1), 'attack4':('CHAR_ATTACK4_FCOUNT',1),
          'palette':('CHAR_PALETTE_BASE_LO',3), 'idle_base':('CHAR_IDLE_BASE_LO',3),
          'walk_base':('CHAR_WALK_BASE_LO',3), 'fall':('CHAR_FALL_FCOUNT',1)}
FIELDS['tile_column'] = ('CHAR_TILE_COLUMN',1)
FIELDS['map'] = ('CHAR_MAP_INDEX',1)
FIELDS.update(zpos=('CHAR_THROW_ZPOS',2), zvel=('CHAR_THROW_ZVEL',2),
              tick=('CHAR_TICK_COUNTER',1), fall_timer=('CHAR_FALL_STATE_TIMER',1),
              idle_delay=('CHAR_IDLE_DELAY',1), walk_delay=('CHAR_WALK_DELAY',1),
              fall_delay=('CHAR_FALL_DELAY',1))


def observer(s, spec, birth_path=None):
    fields = ','.join(f'{k}={{{s[n]},{size}}}' for k,(n,size) in FIELDS.items())
    def pc(name):
        a=s[name]; return ((a>>16)&127)*0x8000+(a&0x7fff)
    birth_journal='' if birth_path is None else f'''
 if event=='source_spawn' then
  local out=assert(io.open({json.dumps(Path(birth_path).as_posix())},'a'))
  out:write(table.concat(p,'|'),'\\n');out:close()
 end
'''
    return f'''-- Native observation; ONLY initial source-spawn POS isolation writes.
local fields={{{fields}}}
local base={0x7e0000+s['PlayerEntity_DpBase']}
local stride={s['CHAR_ZP_LEN']}
local target=nil
local function read(a,n)
 local v=0;for i=0,n-1 do v=v+emu.read(a+i,emu.memType.snesMemory)*256^i end;return v
end
local function capture(event,slot)
 local p={{'S8R',event,'slot='..slot}}
 for k,f in pairs(fields) do p[#p+1]=k..'='..read(base+slot*stride+f[1],f[2]) end
 p[#p+1]='queue='..read({s['Spawn_Index']},1)
 if event=='source_spawn' then
  local idx=read({s['Spawn_ScratchIdx']},2)
  p[#p+1]='admitted_index='..idx
  p[#p+1]='kind='..read({s['Spawn_ScratchKind']},1)
  p[#p+1]='subtype='..read({s['Spawn_ScratchSubtype']},1)
  p[#p+1]='bound_roster='..read({s['Spawn_ScratchRosterIdx']},1)
  for i=0,9 do p[#p+1]='q'..i..'='..read({s['SpawnTable_Wram']}+idx*10+i,1) end
 end
 p[#p+1]='stream_busy='..read({s['Msu1_StreamBusy']},1)
 p[#p+1]='drop_state='..read({s['StageDrop_State']}+slot*stride,2)
 local cpu=emu.getState()
 for _,k in ipairs({{'d','dbr','sp','ps'}}) do p[#p+1]=k..'='..cpu['cpu.'..k] end
 if event=='load' then
  p[#p+1]='loadbase='..read({s['AnimHeaderStaging']},3)
  p[#p+1]='loadframe='..(emu.getState()['cpu.a']%256)
 end
 emu.log(table.concat(p,'|'))
{birth_journal}
end
local function hook(a,f)
 emu.addMemoryCallback(f,emu.callbackType.exec,a,a,emu.cpuType.snes,emu.memType.snesPrgRom)
end
hook({pc('Spawn_Play__environment_done')},function()
 if target or read({s['Game_CampaignId']},1)~=3 or read({s['Game_StageIndex']},2)~={spec['stage']} then return end
 if read({s['Spawn_ScratchIdx']},2)~={spec['queue_index']} then return end
 local slot=read({s['Spawn_ScratchSlotOfs']},2)/stride
 if slot<1 or slot>5 or slot~=math.floor(slot) then return end
 target=slot;capture('source_spawn',slot)
 -- Record a wrong binding but do not reposition it or search for a better
 -- matching actor. Python rejects this first completed source admission.
 if read(base+slot*stride+{s['CHAR_ROSTER_INDEX']},1)~={spec['roster']} then return end
 for _,w in ipairs({{{{{s['CHAR_POS_X']},128,2}},{{{s['CHAR_POS_Y']},180,1}}}}) do
  local a=base+slot*stride+w[1]
  emu.log('S8R|position_write|address='..a..'|value='..w[2]..'|size='..w[3])
  for i=0,w[3]-1 do emu.write(a+i,math.floor(w[2]/256^i)%256,emu.memType.snesMemory) end
 end
 capture('isolated_spawn',slot)
end)
hook({pc('Anim_Play__dispatch')},function()
 if target and emu.getState()['cpu.d']==(base+target*stride)%65536 then capture('dispatch',target) end
end)
hook({pc('Msu1_LoadFrame')},function()
 if target and emu.getState()['cpu.d']==(base+target*stride)%65536 then capture('load',target) end
end)
hook({pc('Character_Throw_Play')},function()
 if target and emu.getState()['cpu.d']==(base+target*stride)%65536 then capture('throw_entry',target) end
end)
-- __still_air is SEP #$20; RTL. The isolated emitted test pins these bytes.
hook({pc('Character_Throw_Play__still_air')+2},function()
 if target and emu.getState()['cpu.d']==(base+target*stride)%65536 then capture('throw_air_return',target) end
end)
emu.addEventCallback(function() if target then capture('frame',target) end end,emu.eventType.endFrame)
'''


def parse_log(text):
    result=[]
    for line in text.splitlines():
        if 'S8R|' not in line: continue
        parts=line[line.index('S8R|'):].split('|')
        result.append(dict(event=parts[1], **{k:int(float(v)) for k,v in (p.split('=',1) for p in parts[2:])}))
    return result


def check_birth(births,spec):
    if len(births)!=1: raise AssertionError('exactly one completed native source spawn required')
    birth=births[0]; start=spec['queue_index']*10
    record=bytes.fromhex(spec['queue'])[start:start+10]
    if birth['queue']!=spec['queue_index'] or birth['admitted_index']!=spec['queue_index']:
        raise AssertionError('native source admission index differs from authored record')
    if bytes(birth['q'+str(i)] for i in range(10))!=record:
        raise AssertionError('native source admission record bytes differ')
    # Ten-byte ABI: kind is byte6 low3; subtype is bits5..7 (bits3..4 map).
    if birth['kind']!=record[6]&7 or birth['subtype']!=(record[6]>>5)&7:
        raise AssertionError('native decoded source kind/subtype differs')
    if birth['roster']!=spec['roster'] or birth['bound_roster']!=record[9] or birth['hp']!=spec['hp']:
        raise AssertionError('completed native source model/HP binding differs')
    return birth


def run(args, spec, s, report):
    import _harness as h
    import mesen_mcp.session as session_module
    sys.path.insert(0,str(ROOT)); import build_rom
    folder=args.output.resolve(); folder.mkdir(parents=True,exist_ok=False)
    birth_journal=folder/'birth.log';birth_journal.write_text('')
    script=folder/'observer.lua'; script.write_text(observer(s,spec,birth_journal))
    log=folder/'mesen.log'
    report.update(status='FAIL', scope='explicit accelerated Normal5A source-queue encounter, NOT campaign proof',
                  writes=[],inputs=[],samples=[],checks=[],spec=spec)
    require_idle_emulator()
    def launch(argv,**kwargs): return subprocess.Popen([*argv,'--debug.scriptwindow.allowioosaccess=true',str(script)],**kwargs)
    proxy=SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE,TimeoutExpired=subprocess.TimeoutExpired)
    try:
        with patch.object(session_module,'subprocess',proxy), h.open_session(__file__,stderr_log=log) as m:
            report['native_executed']=True
            r=h.Reporter('S8-RAMON'); report['checks']=r.results
            p=Proof(m,s,r,report)
            # Fresh MCP process is reset already; another reset unloads Lua.
            with patch.object(m,'reset_emulator',lambda:None): p.native_start(spec)
            bases=p.bases
            def sample(slot):
                row={k:p.mem(bases[slot]+s[n],size) for k,(n,size) in FIELDS.items()}
                row['pit']=p.mem(s['StageBounds_State']+slot*s['CHAR_ZP_LEN'],2)
                row['stream_busy']=p.mem(s['Msu1_StreamBusy'],1)
                row['drop_state']=p.mem(s['StageDrop_State']+slot*s['CHAR_ZP_LEN'],2)
                report['samples'].append(dict(slot=slot,**row));return row
            routing={s[n]:size for n,size in [('Game_CampaignOrdinal',1),('Game_StageIndex',2),
                       ('Stage_LoadPending',1),('Game_State',2),('Spawn_Index',1),('Screen_PosY',2)]}
            positions={(b+s[n]):size for b in bases for n,size in [('CHAR_POS_X',2),('CHAR_POS_Y',1)]}
            def write(address,value,size,reason):
                if {**routing,**positions}.get(address)!=size: raise AssertionError('forbidden fixture write')
                report['writes'].append(dict(address=address,value=value,size=size,reason=reason))
                (m.write_u16 if size==2 else m.write_u8)(address,value)
            def edge(button):
                report['inputs'].append(button);p.edge(m,button,1,port=0)
            entries=build_rom.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']
            previous=entries[spec['ordinal']-1]
            p.need('authored predecessor is a stage',previous[0]=='stage')
            for name,value,size in [('Game_CampaignOrdinal',spec['ordinal']-1,1),('Game_StageIndex',previous[1],2),
                                    ('Stage_LoadPending',1,1),('Game_State',s['GAME_STATE_STAGECLEAR'],2)]:
                write(s[name],value,size,'explicit authored-predecessor 5A fixture handoff')
            p.wait(lambda:p.val('Game_StageIndex')==spec['stage'] and p.val('Game_State')==s['GAME_STATE_PLAYING'],1200)
            queue=bytes.fromhex(spec['queue'])
            p.need('actual native 5A queue matches source compiler',bytes(p.read(m,s['SpawnTable_Wram'],max(32,len(queue))))[:len(queue)]==queue)
            write(s['Spawn_Index'],spec['queue_index'],1,'skip authored prefix; admit actual Ramon record')
            write(s['Screen_PosY'],int.from_bytes(queue[spec['queue_index']*10:][:2],'little'),2,'source admission trigger')
            found=[]
            def spawned():
                # HP/roster become visible mid-Spawn_Play, before final
                # environment binding. Wait for the actual Lua boundary;
                # no queue or position writes are allowed before this event.
                # McpSession spools stderr_log only on close. The dedicated
                # Lua file is closed/flushed at the actual birth callback.
                text=birth_journal.read_text()
                events=parse_log(text.rsplit('\n',1)[0])
                births=[e for e in events if e['event']=='source_spawn']
                if births:
                    report['completed_birth']=check_birth(births,spec)
                    found[:]=[report['completed_birth']['slot']]
                return bool(found)
            p.wait(spawned,600); slot=found[0]; report['slot']=slot
            p.wait(lambda:p.val('Spawn_Index',1)>spec['queue_index'],600)
            write(s['Spawn_Index'],p.val('Spawn_Count',1),1,'suspend subsequent queue admission')
            row=sample(slot)
            p.need('independent runtime roster/media and HP6',row['hp']==6 and row['mode']==s['CHAR_INPUT_DRIVEN_AI']
                   and row['palette']==spec['media_offset'] and row['idle_base']==spec['media_offset']+32
                   and row['walk_base']==row['idle_base']+768 and row['idle']==row['walk']==row['fall']==1
                   and all(row[n]==0 for n in ('attack','attack2','attack3','attack4')))
            def isolate(close):
                for i,b in enumerate(bases):
                    x,y=(128,180) if i==slot else ((112 if close else 32),180) if i==0 else (16,208)
                    for name,value,size in [('CHAR_POS_X',x,2),('CHAR_POS_Y',y,1)]:
                        write(b+s[name],value,size,'position-only combat/pit isolation')
            def park_others():
                for i,b in enumerate(bases):
                    if i in (0,slot): continue
                    write(b+s['CHAR_POS_X'],16,2,'keep unrelated actors outside encounter')
                    write(b+s['CHAR_POS_Y'],220,1,'keep unrelated actors outside encounter')
            # SCROLL_DOWN really spawns airborne. Do not clear its selector,
            # altitude, velocity, frame sentinel, or timers to manufacture a
            # walking actor. Retain a bounded trace even if native gravity or
            # landing publication is broken.
            isolate(False)
            landing=[]; grounded=0
            for _ in range(600):
                park_others(); p.tick(); row=sample(slot); landing.append(row)
                p.need('drop identity and HP retained outside pit',
                       row['roster']==spec['roster'] and row['hp']==6 and row['pit']==0)
                if row['drop_state']==3 and 0<row['zpos']<0x8000 and 'airborne_screenshot' not in report:
                    column=row['tile_column']
                    pixels=b''.join(bytes(p.read(m,0x8000+column*128+i*512,128,'snesVideoRam')) for i in range(6))
                    report['airborne_frame_sha256']=hashlib.sha256(pixels).hexdigest()
                    p.need('airborne resident OBJ is own authored idle frame',pixels==bytes.fromhex(spec['frame_bytes']))
                    report['airborne_actor']=row
                    report['airborne_screenshot']=m.take_screenshot()
                grounded = grounded+1 if native_landed(row) else 0
                if grounded>=3: break
            report['landing_samples']=landing
            p.need('native drop landed and recovered without state writes',grounded>=3)
            p.need('native airborne idle publication observed before landing','airborne_screenshot' in report)
            isolate(False); walking=[]
            for _ in range(45): park_others();p.tick();walking.append(sample(slot))
            p.need('real walk dispatch and movement',any(v['selected']==1 for v in walking) and any(v['x']!=128 for v in walking))
            isolate(True); hp=p.mem(bases[0]+s['CHAR_HP'],1); idle=[]
            for _ in range(90): park_others();p.tick();idle.append(sample(slot))
            p.need('near-target idle and no fabricated attack/damage',any(v['selected']==0 for v in idle)
                   and all(v['selected']!=2 and v['hp']==6 and v['pit']==0 for v in walking+idle)
                   and p.mem(bases[0]+s['CHAR_HP'],1)==hp)
            # Actual six strided OBJ tile rows, matching Msu1_LoadFrame's
            # $8000 + CHAR_TILE_COLUMN*128 + row*512 byte VRAM layout.
            column=sample(slot)['tile_column']
            pixels=b''.join(bytes(p.read(m,0x8000+column*128+i*512,128,'snesVideoRam')) for i in range(6))
            report['native_frame_sha256']=hashlib.sha256(pixels).hexdigest()
            p.need('actual OBJ tiles equal own authored Ramon frame',pixels==bytes.fromhex(spec['frame_bytes']))
            # Living actor after independent OBJ byte proof, before any
            # controller attack. Separate from the existing death screenshot.
            report['living_screenshot']=m.take_screenshot()
            report['living_screenshot_actor']=sample(slot)
            p.need('living screenshot actor remains alive',report['living_screenshot_actor']['hp']==6)
            pain=False; dead=False
            for frame in range(900):
                park_others()
                if frame%48==0:
                    isolate(True);edge(m.BTN_RIGHT);edge(m.BTN_Y)
                else:p.tick()
                row=sample(slot)
                p.need('identity retained; combat is not pit damage',row['roster']==spec['roster']
                       and row['palette']==spec['media_offset'] and row['pit']==0)
                pain |= 0<row['hp']<6 and row['stun']>0 and row['selected']==0
                if row['hp']==0:dead=True;break
            p.need('controller damage and compatibility pain observed',pain)
            p.need('controller-caused native death',dead)
            report['screenshot']=m.take_screenshot()
            for _ in range(45):p.tick()
            p.need('death remains retired without synthetic stock/HP writes',sample(slot)['hp']==0)
        events=parse_log(log.read_text(errors='replace')); report['events']=events
        entry=None; air_returns=0
        for event in events:
            if event['event']=='throw_entry': entry=event
            elif event['event']=='throw_air_return':
                if entry is None or entry['selected']!=6:
                    raise AssertionError('air return without actual THROWN entry')
                if any(event[k]!=entry[k] for k in ('d','dbr','sp')) or event['ps']&0x30!=0x20:
                    raise AssertionError('throw airborne D/DBR/stack/width contract')
                if entry['ps']&8:
                    raise AssertionError('throw arithmetic entered with decimal mode set')
                if event['zpos']!=(entry['zpos']+entry['zvel'])&0xffff or event['zvel']!=(entry['zvel']+s['JUMP_GRAVITY'])&0xffff:
                    raise AssertionError('native airborne position/velocity integration')
                air_returns+=1
        report['native_throw_air_returns']=air_returns
        if not air_returns: raise AssertionError('native airborne gate observer missing')
        births=[e for e in events if e['event']=='source_spawn']
        check_birth(births,spec)
        dispatch=[e for e in events if e['event']=='dispatch' and e['hp']>0]
        if not dispatch or any(e['selected']==2 for e in dispatch):
            raise AssertionError('sparse enemy dispatched an invented attack or observer missing')
        loads=[e for e in events if e['event']=='load']
        airborne_loads=[e for e in loads if 0<e['zpos']<0x8000]
        if not airborne_loads or any(e['loadbase']!=spec['media_offset']+32 or e['loadframe']!=0 for e in airborne_loads):
            raise AssertionError('new live drop must publish authored idle, not airborne walk/fall')
        allowed={spec['media_offset']+32+i*768 for i in range(3)}  # idle/walk/fall
        if not loads or any(e['loadframe']!=0 or e['loadbase'] not in allowed for e in loads):
            raise AssertionError('native media request outside authored single-frame roles')
        report['status']='OBSERVED_PASS_VISUAL_REVIEW_PENDING'
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}'
    finally:
        if log.exists():
            report['log_sha256']=sha(log)
            report.setdefault('events',parse_log(log.read_text(errors='replace')))
        (folder/'report.json').write_text(json.dumps(report,indent=2))


def native_landed(row):
    """Grounded idle/walk after native FALL recovery, not merely PLAYING."""
    return row['zpos']==0 and row['zvel']==0 and row['selected'] in (0,1)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',action='store_true')
    for n in ('rom','msu','symbols'):ap.add_argument('--'+n+'-sha256')
    ap.add_argument('--symbols',default=str(ROOT/'src/main.sym'))
    ap.add_argument('--output',type=Path,default=ROOT/'out/s8_ramon')
    args=ap.parse_args(argv); report={'status':'FAIL','native_executed':False}
    try:
        spec=source_spec()
        if args.run:
            s=preflight(args,spec)
            run(args,spec,s,report)
        else:report.update(status='SOURCE_ONLY_NOT_RUN',spec=spec)
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}'
    print(json.dumps(report if not args.run else dict(status=report['status'],error=report.get('error'),output=str(args.output)),indent=2))
    return int(report['status']=='FAIL')


if __name__=='__main__':raise SystemExit(main())
