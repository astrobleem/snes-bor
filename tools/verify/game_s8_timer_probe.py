#!/usr/bin/env python3
"""Prepare/check an observer, or explicitly --run the focused native driver.

Main attaches the generated Lua to its serialized, fully linked Normal run.
The linked manifest is an explicit external build attestation, not generated
by this tool. Runtime observations are required; synthetic tests are not proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
FILES = ('distribution/bor.sfc', 'distribution/bor.msu', 'src/main.sym')


def artifact_paths(seal):
    paths = {name: str((ROOT / seal.get('paths', {}).get(name, name)).resolve()) for name in FILES}
    candidate = os.environ.get('BOR_TEST_ROM')
    if candidate:
        paths[FILES[0]] = str(Path(candidate).resolve())
        paths[FILES[1]] = str(Path(candidate).resolve().with_suffix('.msu'))
    return paths


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare(manifest):
    seal = json.loads(Path(manifest).read_text())
    if seal.get('status') != 'LINKED':
        raise ValueError('full production LINKED attestation required')
    paths = artifact_paths(seal)
    for name in FILES:
        if seal.get('artifacts', {}).get(name) != digest(paths[name]):
            raise ValueError('linked artifact hash mismatch: ' + name)
    symbols = {n: (int(b, 16) << 16) | int(a, 16) for b, a, n in re.findall(
        r'(?m)^([0-9A-Fa-f]+):([0-9A-Fa-f]+)\s+(\w+)',
        Path(paths['src/main.sym']).read_text())}
    sys.path[:0] = [str(ROOT / 'tools/bor_compile'), str(ROOT / 'tools/audio')]
    from compiler import Source, stage, model_catalog, key
    from production_campaign import compile_queues
    from shipped_content import STAGE_CONFIGS, ROSTER_CONFIGS
    cfg = next(c for c in STAGE_CONFIGS if c['source_level'] == 'DATA\\NORMAL\\5A.TXT')
    queue = compile_queues([cfg], ROSTER_CONFIGS)[cfg['spawn']]
    if (ROOT / cfg['spawn']).read_bytes() != queue:
        raise ValueError('on-disk Normal5A queue differs from strict source compiler')
    ir = stage(Source(cfg['pak']), cfg['source_level'])
    indices = [i for i, e in enumerate(ir.queue) if e.character == 'Time']
    if not indices or any(queue[i*10+9] != 46 or queue[i*10+6] >> 5 != 6 for i in indices):
        raise ValueError('actual source Time queue binding is not roster46/effect6')
    spec = dict(artifacts=seal['artifacts'], paths=paths, symbols=symbols, stage=STAGE_CONFIGS.index(cfg),
                queue=queue.hex(), time_indices=indices, queue_sha256=hashlib.sha256(queue).hexdigest())
    spec['spawn_indices'] = [i for i, e in enumerate(ir.queue) if e.kind == 'spawn' and e.character != 'Time']
    # Required ordinary-source enemy reuse is selected from SOURCE identity,
    # never from today's lossy byte9=0 encoding. Do not avoid this case by
    # choosing only appended/explicit models; that hides stale-prop reuse.
    models = model_catalog(Source(cfg['pak']))
    for index in spec['spawn_indices']:
        event = ir.queue[index]
        model = models[event.character.casefold()]
        path = key(model['source_path'])
        bound = [i for i, r in enumerate(ROSTER_CONFIGS) if r['family'] == cfg['family']
                 and cfg.get('source_set_id') in r.get('runtime_binding_sets', (0, 1))
                 and key(r['source_character']) in (path.rsplit('/', 1)[0], path.removesuffix('.txt'))]
        if len(bound) == 1 and bound[0] < 29 and model['entity'].get('type') == 'enemy' and not event.boss:
            spec['ordinary_reuse_case'] = dict(index=index, model=event.character,
                                               expected_roster=bound[0], source_path=model['source_path'])
            break
    if 'ordinary_reuse_case' not in spec:
        raise ValueError('missing source ordinary enemy reuse case')
    fields = {
        'campaign': ('Game_CampaignId', 1), 'stage': ('Game_StageIndex', 2),
        'state': ('Game_State', 2), 'left': ('StageTimer_Left', 2),
        'show': ('StageTimer_ShowTimeOver', 2), 'field': ('StageTimer_FieldCounter', 2),
        'fault': ('StageTimer_Fault', 2), 'phase': ('StageTimer_ClockPhase', 2),
        'lives': ('Game_Lives', 2), 'input': ('Input_press_Addr', 2),
        'spawn': ('Spawn_Index', 1), 'busy': ('Nmi_FrameBusy', 1),
        'spawn_roster': ('Spawn_ScratchRosterIdx', 1),
        'attack1': ('Input_trigger_Addr', 2), 'attack2': ('Input2_trigger_Addr', 2),
        'owner': ('G13_PickupForP2', 1),
    }
    definitions = '\n'.join(f'  v.{key}=read({symbols[name]},{size})' for key, (name, size) in fields.items())
    zp = symbols['CHAR_ZP_LEN']
    spec['stride'] = zp
    for slot in range(6):
        definitions += f'\n  v.p{slot}=read({symbols["StageTimer_Pending"]+slot*2},2)'
        for short, name, size in [('hp', 'CHAR_HP', 1), ('kind', 'CHAR_PICKUP_TYPE', 1),
                                  ('roster', 'CHAR_ROSTER_INDEX', 1), ('x', 'CHAR_POS_X', 2),
                                  ('y', 'CHAR_POS_Y', 1)]:
            definitions += f'\n  v.{short}{slot}=read({0x7E0A00+slot*zp+symbols[name]},{size})'
    hooks = {
        'collect': 'StageTimerHost_Collect', 'retire': 'StageTimerHost_Retire',
        'retired': 'StageTimerHost_Retire__done', 'timeout': 'StageTimer_EndTick__timeout',
        'damage': 'StageTimerHost_DamagePlayer', 'reset': 'StageTimer_Reset100__done',
        'sound': 'StageTimerHost_Sound', 'render': 'Character_RenderFrame',
        'reuse': 'Spawn_DoRosterReassign',
        'oam': 'Core_Oam_SetSprite', 'audio': 'Audio_QueueResidentSemantic',
        'overlap': 'StageTimerHost_CollectFromOverlap',
    }
    # LoROM ROM offsets, matching existing repository observer convention.
    def offset(name):
        a = symbols[name]
        if a & 0xFFFF < 0x8000:
            raise ValueError('not a linked LoROM code address: ' + name)
        return ((a >> 16) & 0x7F)*0x8000 + (a & 0x7FFF)
    spec['playing'] = symbols['GAME_STATE_PLAYING']
    spec['paused'] = symbols['GAME_STATE_PAUSED']
    lua = '''-- Generated read-only S8 observer: no writes, inputs or execution redirects.
local tick, frame, lastOamFrame = 0, 0, -1
local function read(a,n)
  local v=0
  for i=0,n-1 do v=v+emu.read(a+i,emu.memType.snesMemory)*256^i end
  return v
end
local function capture(event)
  local v={}
@FIELDS@
  if v.campaign~=3 or v.stage~=@STAGE@ then return end
  local s=emu.getState()
  v.a=s['cpu.a'] or -1; v.rx=s['cpu.x'] or -1; v.d=s['cpu.d'] or -1
  if event=='oam' then
    local slot=(v.d-0x0A00)/@STRIDE@
    local pending=v['p'..tostring(math.floor(slot))] or 0
    if pending==0 and lastOamFrame==frame then return end
    lastOamFrame=frame
  end
  local parts={'S8T',event,tostring(tick),tostring(frame)}
  for k,n in pairs(v) do parts[#parts+1]=k..'='..tostring(n) end
  if event=='frame' then
    local bytes={}
    for i=0,@QLEN@-1 do bytes[#bytes+1]=string.format('%02x',read(@QUEUE@+i,1)) end
    parts[#parts+1]='queue='..table.concat(bytes)
    bytes={}
    for i=0,17 do bytes[#bytes+1]=string.format('%02x',emu.read(@VRAM@+i,emu.memType.snesVideoRam)) end
    parts[#parts+1]='vram='..table.concat(bytes)
  end
  emu.log(table.concat(parts,'|'))
end
local function hook(address,fn)
  emu.addMemoryCallback(fn,emu.callbackType.exec,address,address,emu.cpuType.snes,emu.memType.snesPrgRom)
end
hook(@TICK@,function() tick=tick+1 end)
emu.addEventCallback(function() frame=frame+1;capture('frame') end,emu.eventType.endFrame)
'''
    for key, value in {'FIELDS': definitions, 'STAGE': spec['stage'], 'QLEN': len(queue),
                       'STRIDE': zp,
                       'QUEUE': symbols['SpawnTable_Wram'], 'TICK': offset('StageTimer_BeginTick'),
                       'VRAM': (symbols['BG3_TILEMAP_VRAM_WORD']+11*32+11)*2}.items():
        lua = lua.replace('@'+key+'@', str(value))
    for event, name in hooks.items():
        lua += f"hook({offset(name)},function() capture('{event}') end)\n"
    spec['lua_sha256'] = hashlib.sha256(lua.encode()).hexdigest()
    return spec, lua


def parse(text):
    events = []
    for line in text.splitlines():
        if 'S8T|' not in line:
            continue
        parts = line[line.index('S8T|'):].split('|')
        event = dict(event=parts[1], tick=int(parts[2]), frame=int(parts[3]))
        for field in parts[4:]:
            k, value = field.split('=', 1)
            event[k] = value if k in ('queue', 'vram') else int(float(value))
        events.append(event)
    return events


def gates(spec, events):
    """Fail-closed observations, not a replacement reference-model execution."""
    checks = {}
    frames = [e for e in events if e['event'] == 'frame'
              and e['state'] in (spec['playing'], spec['paused'])]
    checks['actual_normal5a_queue'] = bool(frames) and all(e['queue'] == spec['queue'] for e in frames)
    checks['no_timer_fault'] = bool(events) and all(e['fault'] == 0 for e in events)
    collects = [e for e in events if e['event'] == 'collect']
    valid = [e for e in collects if 0 <= e['rx'] < 6 and e['left'] == 40000
             and e[f'p{e["rx"]}'] == 600 and e[f'roster{e["rx"]}'] == 46
             and e[f'kind{e["rx"]}'] == 6 and e['owner'] in (0, 1)
             and e[f'attack{e["owner"]+1}'] & 0x4000]
    checks['real_input_source_time_reset'] = bool(valid)
    neutral = [e for e in events if e['event'] == 'overlap' and 1 <= e['rx'] < 6
               and e['owner'] in (0, 1) and not e[f'attack{e["owner"]+1}'] & 0x4000
               and e[f'kind{e["rx"]}'] == 6 and e[f'p{e["rx"]}'] == 0
               and e[f'hp{e["rx"]}'] > 0]
    # Clock fields and main callbacks are not 1:1 (busy/stalled service).
    # Require sixty observed neutral fields, not sixty overlap invocations.
    checks['neutral_overlap_cannot_auto_collect'] = bool(valid) and all(any(
        n['rx'] == c['rx'] and n['frame'] <= c['frame']-60
        and len([f for f in frames if n['frame'] <= f['frame'] < c['frame']]) >= 60
        and all(f[f'hp{c["rx"]}'] > 0 and f[f'kind{c["rx"]}'] == 6
                and f[f'p{c["rx"]}'] == 0
                for f in frames if n['frame'] <= f['frame'] < c['frame'])
        for n in neutral) for c in valid)
    checks['native_queue_spawn_precedes_collection'] = bool(valid) and all(any(
        e['event'] == 'reuse' and e['rx'] == c['rx']*spec['stride']
        and e['spawn_roster'] == 46 and e['spawn'] in spec['time_indices']
        and e['tick'] <= c['tick'] for e in events) for c in valid)
    checks['retire_exactly_600_ticks'] = bool(valid) and all(any(
        r['event'] == 'retire' and r['rx'] == c['rx'] and r['tick']-c['tick'] == 600
        for r in events) for c in valid)
    windows = [[e for e in frames if c['tick'] < e['tick'] < c['tick']+600] for c in valid]
    checks['pending_occupancy_and_hide'] = bool(valid) and all(len(w) >= 20 for w in windows) and all(
        e[f'hp{c["rx"]}'] > 0 and e[f'roster{c["rx"]}'] == 46
        and e[f'kind{c["rx"]}'] == 0 and e[f'x{c["rx"]}'] == 0x7FFF
        for c, window in zip(valid, windows) for e in window)
    checks['no_pending_oam_submission'] = bool(valid) and any(e['event'] == 'oam' for e in events) and not any(
        e['event'] == 'oam' and e['d'] == 0x0A00+c['rx']*spec['stride']
        and c['tick'] <= e['tick'] < c['tick']+600 for c in valid for e in events)
    # Render may be entered before its exclusion filter. Require screenshots/OAM
    # externally rather than falsely equating entry to emitted OAM.
    ordinary = spec.get('ordinary_reuse_case')
    checks['post_retire_slot_reused_natively'] = bool(ordinary) and bool(valid) and all(any(
        e['event'] == 'reuse' and e['tick'] >= c['tick']+600
        and e['rx'] == c['rx']*spec['stride'] and e['spawn'] == ordinary['index']
        and e['spawn_roster'] == ordinary['expected_roster']
        and any(f['frame'] >= e['frame'] and f[f'hp{c["rx"]}'] > 0
                and f[f'roster{c["rx"]}'] == ordinary['expected_roster'] for f in frames)
        for e in events) for c in valid)
    checks['retirement_clears_actual_actor'] = bool(valid) and all(any(
        e['event'] == 'retired' and e['tick'] == c['tick']+600
        and e[f'hp{c["rx"]}'] == 0 and e[f'kind{c["rx"]}'] == 0
        and e[f'p{c["rx"]}'] == 0 for e in events) for c in valid)
    checks['no_premature_slot_reuse'] = bool(valid) and not any(
        e['event'] == 'reuse' and e['rx'] == c['rx']*spec['stride']
        and c['tick'] <= e['tick'] < c['tick']+600 for c in valid for e in events)
    checks['native_admission_under_reservation_pressure'] = bool(valid) and all(any(
        e['event'] == 'reuse' and e['rx'] != c['rx']*spec['stride']
        and c['tick'] < e['tick'] < c['tick']+600 for e in events) for c in valid)
    timeout = [e for e in events if e['event'] == 'timeout' and e['left'] == 0]
    checks['timeout_damage_sound_reset'] = bool(timeout) and all(
        any(e['event'] == 'damage' and e['tick'] == t['tick'] and e['a'] == 1000 for e in events)
        and any(e['event'] == 'sound' and e['tick'] == t['tick'] and e['a'] == 2 for e in events)
        and any(e['event'] == 'audio' and e['tick'] == t['tick']
                and e['a'] & 255 == 0x1D and e['rx'] == 12 for e in events)
        and any(e['show'] == 1 and e['left'] > 39600 for e in frames if e['frame'] >= t['frame'])
        for t in timeout)
    checks['timeout_reaches_native_stock_path'] = bool(timeout) and all(any(
        e['frame'] > t['frame'] and e['lives'] == t['lives']-1 and e['hp0'] > 0
        for e in frames) for t in timeout)
    paused = [e for e in frames if e['state'] == spec['paused']]
    checks['pause_frozen_with_live_nmi'] = len(paused) >= 60 and all(
        e['left'] == paused[0]['left'] and e['tick'] == paused[0]['tick'] for e in paused)
    checks['pause_frozen_with_live_nmi'] &= bool(paused) and paused[-1]['field'] != paused[0]['field']
    resumed = [e for e in frames if paused and e['frame'] > paused[-1]['frame'] and e['state'] == spec['playing']]
    checks['resume_without_paused_backlog'] = bool(resumed) and 0 <= resumed[0]['tick']-paused[-1]['tick'] <= 10
    def glyphs(s):
        return b''.join((spec['symbols']['FONT_TILE_INDEX_BASE']+ord(c)-32
                        +((spec['symbols']['HUD_ENTRY_HIGH']*256)
                          | (spec['symbols']['FONT_CGRAM_PAL_ID']*1024))).to_bytes(2,'little') for c in s).hex()
    checks['visible_countdown_and_timeover_vram'] = any(e['vram'] == glyphs('TIME OVER') for e in frames) and len({
        e['vram'] for e in frames if e['vram'] in {glyphs(f'TIME {n:02d}  ') for n in range(100)}}) >= 2
    return checks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode', required=True)
    prep = sub.add_parser('prepare'); prep.add_argument('--linked', required=True)
    check = sub.add_parser('check'); check.add_argument('--spec', required=True); check.add_argument('--log', required=True)
    run = sub.add_parser('run', help='EXPLICIT emulator launch; main must serialize')
    run.add_argument('--linked', required=True)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--fixture-normal5a', action='store_true', required=True)
    argv = ['run' if v == '--run' else v for v in sys.argv[1:]]
    args = p.parse_args(argv)
    if args.mode == 'run':
        from game_s8_timer_driver import run_native
        return run_native(args)
    if args.mode == 'prepare':
        spec, lua = prepare(args.linked)
        print(json.dumps(dict(spec=spec, lua=lua), indent=2))
    else:
        spec = json.loads(Path(args.spec).read_text())
        for name in FILES:
            if spec['artifacts'][name] != digest(spec.get('paths', {}).get(name, ROOT / name)):
                raise ValueError('artifacts changed since probe preparation: ' + name)
        result = gates(spec, parse(Path(args.log).read_text(errors='replace')))
        print(json.dumps(dict(status='OBSERVED_GATES_PASS_VISUAL_REVIEW_REQUIRED' if all(result.values()) else 'FAIL',
                              checks=result, log_sha256=digest(args.log)), indent=2))
        return 0 if all(result.values()) else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
