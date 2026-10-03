"""Prepared, bounded native HUD probe; no emulator starts without --run.

One Normal 1A encounter: organic aliased spawn, P1 hit, P2 hit, native death
and row removal. Controller attacks exercise the actual native callbacks.
Only encounter POS_X/POS_Y may be
written. Never seed HP, aliases, models, opponent handles, animation or VRAM.
Position isolation is a fixture, not an organic campaign/gameplay claim.

Run ONLY after the candidate is built and emulator use is authorized:
  Set BOR_TEST_ROM=build/s8_candidate/bor.sfc (same path used by the harness).
  The MSU is resolved beside that ROM; --symbols selects its hashed symbols.
  python tools/verify/game_s8_opponent_hud.py --run --rom-sha256 HASH \
    --msu-sha256 HASH --symbols-sha256 HASH --output out/s8_opponent_hud.json
Without --run, this prints the plan and performs no emulator operations.
Time pickup testing belongs to the separate timer probe.
"""
from pathlib import Path
from contextlib import contextmanager
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/bor_compile'), str(ROOT / 'tools/audio')]
from compiler import Source, stage, key, model_catalog, project
from shipped_content import STAGE_CONFIGS, ROSTER_CONFIGS

PLAN = dict(scope='one Normal 1A source alias, two players, native damage/death',
            fixture_writes=['actor POS_X/POS_Y for encounter isolation only'],
            forbidden_writes=['HP', 'alias', 'roster', 'opponent', 'animation', 'VRAM'],
            checks=['persistent worker ownership', 'real P1 input-driven movement',
                    'organic source opponent AI progress', 'P1 source hit/damage',
                    'ordered event drain and BG3 health/name row'],
            limits=dict(stage_load=900, spawn=600, combat=900,
                        retirement_fields_per_tick=8, retirement_stall=64, row_clear=64),
            runtime_status='NOT_RUN', visual_acceptance='PENDING_MANUAL', time_pickup='OUT_OF_SCOPE')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_symbols(path):
    return {name: (int(bank, 16) << 16) | int(addr, 16)
            for bank, addr, name in re.findall(r'^([\dA-Fa-f]{2}):([\dA-Fa-f]{4,6}) (\S+)$',
                                               Path(path).read_text(), re.M)}


def read_worker_symbols(path):
    return {name: (int(bank, 16) << 16) | int(addr, 16)
            for bank, addr, name in re.findall(r'^([\dA-Fa-f]{2}):([\dA-Fa-f]{4,6}) (\S+)$',
                                               Path(path).read_text(), re.M)}


def pc(address):
    return (address >> 16) * 0x8000 + (address & 0x7fff)


def rom_string(rom, address):
    start = pc(address)
    end = rom.index(0, start, min(len(rom), start + 21))
    return rom[start:end].decode('latin1')


def expected_row(sym, name, hp):
    row = [0] * 32
    row[1] = sym['HUD_TILE_CAP_LEFT'] | (sym['HUD_ENTRY_HIGH'] << 8)
    for i in range(sym['HUD_BAR_TILES']):
        row[2+i] = (sym['HUD_TILE_FILL_BASE'] + max(0, min(8, hp-i*8))
                    | (sym['HUD_ENTRY_HIGH'] << 8))
    row[10] = sym['HUD_TILE_CAP_RIGHT'] | (sym['HUD_ENTRY_HIGH'] << 8)
    for col, byte in enumerate(name.encode('latin1')[:20], 12):
        if not sym['FONT_ASCII_FIRST'] <= byte <= sym['FONT_ASCII_LAST']:
            byte = ord('?')
        row[col] = (sym['FONT_TILE_INDEX_BASE'] + byte - sym['FONT_ASCII_FIRST']
                    | 0x2000 | (sym['FONT_CGRAM_PAL_ID'] << 10))
    return row


def candidate_paths(symbols):
    # Never silently fall back to the accepted distribution for this probe.
    if not os.environ.get('BOR_TEST_ROM', '').strip():
        raise ValueError('HUD candidate probe requires explicit BOR_TEST_ROM')
    from _harness import rom_path
    selected_rom = Path(rom_path(__file__)).resolve(strict=True)
    return dict(rom=selected_rom, msu=selected_rom.with_suffix('.msu').resolve(strict=True),
                symbols=Path(symbols).resolve(strict=True))


def preflight(args):
    paths = candidate_paths(args.symbols)
    hashes = {name: sha(path) for name, path in paths.items()}
    for name in paths:
        wanted = getattr(args, name + '_sha256')
        if not wanted or not re.fullmatch(r'[0-9a-fA-F]{64}', wanted) or hashes[name] != wanted.lower():
            raise ValueError(f'{name} candidate SHA256 missing/mismatched; no emulator started')
    sym, rom = read_symbols(paths['symbols']), paths['rom'].read_bytes()
    # The Normal production source world is a separate SA-1 image. Its
    # candidate-adjacent symbol map is authoritative for worker hooks; S-CPU
    # labels at similar offsets are not evidence that the source path ran.
    worker_sym_path = paths['rom'].with_name('worker.sym')
    worker_syms = read_worker_symbols(worker_sym_path)
    for name in ('WHost_PlayerAction__attack', 'W6_WorldAttack',
                 'W6_TryHitOne__geometry', 'W6_SourceCollision',
                 'W6_TryHitOne__damage', 'W6_HitEffects'):
        if name not in worker_syms:
            raise ValueError(f'candidate worker symbols lack SA-1 hook {name}')
        sym['_SA1_' + name] = worker_syms[name]
    from _harness import pasm_constant_in
    for name in ('S6Host_HitEvents', 'S6Host_FrameEvents'):
        sym[name] = pasm_constant_in('src/core/actor_source_host.pasm', name)
    hooks = [('Character_HitApply__ApplyDamage', 'HudOpponentHost_VictimX'),
             ('Character_HitApply__TryGrab__do', 'HudOpponentHost_Grab'),
             ('Character_HitApply_VsPlayer__hp_ok', 'HudOpponentHost_StorePlayerHp'),
             ('Spawn_ResetKnockdownFall', 'HudOpponentHost_RetireX'),
             ('ActorBehavior_RestoreRoster', 'HudOpponent_Reset'),
             ('HudOpponent_Play', 'HudOpponentHost_PurgeRetired')]
    for caller, target in hooks:
        start = pc(sym[caller])
        if rom[start:start+4] != b'\x22' + sym[target].to_bytes(3, 'little'):
            raise ValueError(f'candidate lacks actual native hook: {caller} -> {target}')
    physical, config = next((i, c) for i, c in enumerate(STAGE_CONFIGS)
                            if key(c['source_level']) == 'data/normal/1a.txt')
    source = Source(ROOT / config['pak'])
    ir = stage(source, config['source_level'])
    queue_index, event = next((i, e) for i, e in enumerate(ir.queue)
                             if e.kind == 'spawn' and e.alias)
    queue_index += len(ir.environment.get('hole', []))
    records = pc(sym['StageEnv_AliasRecords'])
    alias_id = next(int.from_bytes(rom[r+2:r+4], 'little')
                    for r in range(records, records+sym['StageEnv_AliasRecordCount']*4, 4)
                    if tuple(rom[r:r+2]) == (physical, queue_index))
    pointer = pc(sym['StageEnv_AliasNamePtrs']) + alias_id*2
    name = rom_string(rom, 0x0D0000 | int.from_bytes(rom[pointer:pointer+2], 'little'))
    if name != event.alias[:20]:
        raise ValueError('candidate alias table does not match the source spawn')
    model = model_catalog(source)[event.character.casefold()]
    model_path = key(model['source_path'])
    models = [i for i, c in enumerate(ROSTER_CONFIGS) if c['family'] == config['family']
              and (key(c.get('source_definition', c['source_character'])) == model_path
                   or key(c['source_character']) in (model_path.removesuffix('.txt'),
                                                      model_path.rsplit('/', 1)[0]))]
    if len(models) != 1:
        raise ValueError('source opponent identity must resolve uniquely')
    binding = dict(stage=physical, queue=queue_index, alias_id=alias_id, name=name,
                   difficulty=next(i for i, entry in enumerate(project(source).sets)
                                   if entry.name == 'Normal'),
                   source_model=event.character, roster=models[0], map=event.map,
                   source_path=config['source_level'], pak_sha256=sha(ROOT / config['pak']))
    return paths, hashes, sym, rom, binding


class Probe:
    def __init__(self, m, sym, binding, report):
        self.m, self.s, self.binding, self.report = m, sym, binding, report
        self.frame = 0
        self.phase = 'load'
        self.slot = None
        self.combat_deadline = None
        self.fixture_fence_held = False

    def read(self, address, length=32, kind='snesMemory'):
        return self.m.read_memory(kind, address, max(32, length))[:length]

    def u8(self, name):
        return self.read(self.s[name])[0]

    def u16(self, name):
        return int.from_bytes(self.read(self.s[name])[:2], 'little')

    def snapshot(self):
        s, stride = self.s, self.s['CHAR_ZP_LEN']
        base = 0x7E0000 | s['PlayerEntity_DpBase']
        actors, aliases = self.read(base, stride*6), self.read(s['StageEnv_AliasId'], stride*5+2)
        rows = []
        for i in range(6):
            actor = actors[i*stride:(i+1)*stride]
            rows.append(dict(slot=i, hp=actor[s['CHAR_HP']], model=actor[s['CHAR_ROSTER_INDEX']],
                             palette=actor[s['CHAR_PALETTE_SLOT']], map=actor[s['CHAR_MAP_INDEX']],
                             driver=actor[s['CHAR_INPUT_DRIVEN']], selected=actor[s['CHAR_SELECTED']],
                             attack_fcount=actor[s['CHAR_ATTACK_FCOUNT']],
                             attack2_fcount=actor[s['CHAR_ATTACK2_FCOUNT']],
                             get_fcount=actor[s['CHAR_GET_FCOUNT']],
                             fall_timer=actor[s['CHAR_FALL_STATE_TIMER']],
                             fall_count=actor[s['CHAR_FALL_FCOUNT']],
                             fall_delay=actor[s['CHAR_FALL_DELAY']],
                             hit_stun=actor[s['CHAR_HIT_STUN']],
                             grab_target=actor[s['CHAR_GRAB_TARGET']],
                             grabbed_by=actor[s['CHAR_GRABBED_BY']],
                             grab_timer=actor[s['CHAR_GRAB_TIMER']],
                             facing_left=actor[s['CHAR_FACING_LEFT']],
                             animation_frame=actor[s['CHAR_FRAME_INDEX']],
                             tick_counter=actor[s['CHAR_TICK_COUNTER']],
                             attack_variant=actor[s['CHAR_ATTACK_VARIANT']],
                             hit_applied=actor[s['CHAR_HIT_APPLIED']],
                             x=int.from_bytes(actor[s['CHAR_POS_X']:s['CHAR_POS_X']+2], 'little'),
                             y=actor[s['CHAR_POS_Y']],
                             alias=int.from_bytes(aliases[i*stride:i*stride+2], 'little')))
        targets = self.read(s['HudOpponent_Targets'])
        host_rows = self.read(s['StageEnv_Actors'], stride*6)
        host = [dict(action=int.from_bytes(host_rows[i*stride+74:i*stride+76], 'little'),
                     frame=int.from_bytes(host_rows[i*stride+84:i*stride+86], 'little'),
                     role=int.from_bytes(host_rows[i*stride+86:i*stride+88], 'little'))
                for i in range(6)]
        worker_contexts = self.read(0x11900, 6 * 0x100, 'snesSaveRam')
        worker_rows = []
        for i in range(6):
            at = i * 0x100
            worker_rows.append(dict(
                frame_ptr=int.from_bytes(worker_contexts[at:at+3], 'little'),
                frame_count=int.from_bytes(worker_contexts[at+0x04:at+0x06], 'little'),
                frame_index=int.from_bytes(worker_contexts[at+0x06:at+0x08], 'little'),
                attack_flags=int.from_bytes(worker_contexts[at+0x08:at+0x0A], 'little'),
                attack_active=int.from_bytes(worker_contexts[at+0x0A:at+0x0C], 'little'),
                frame_valid=int.from_bytes(worker_contexts[at+0x0C:at+0x0E], 'little'),
                frame_ticks=int.from_bytes(worker_contexts[at+0x0E:at+0x10], 'little'),
                animating=int.from_bytes(worker_contexts[at+0x10:at+0x12], 'little'),
                current_source_time=int.from_bytes(worker_contexts[at+0xD0:at+0xD4], 'little'),
                next_animation_time=int.from_bytes(worker_contexts[at+0xD4:at+0xD8], 'little'),
                current_role=int.from_bytes(worker_contexts[at+0xE4:at+0xE6], 'little'),
                behavior_state=int.from_bytes(worker_contexts[at+0xE6:at+0xE8], 'little'),
                next_think_time=int.from_bytes(worker_contexts[at+0xE8:at+0xEC], 'little'),
                last_animation_position=int.from_bytes(worker_contexts[at+0xF4:at+0xF6], 'little'),
                x=int.from_bytes(worker_contexts[at+0x14:at+0x16], 'little', signed=True),
                y=int.from_bytes(worker_contexts[at+0x16:at+0x18], 'little', signed=True),
                direction=int.from_bytes(worker_contexts[at+0x1A:at+0x1C], 'little'),
                pain_deadline=int.from_bytes(worker_contexts[at+0xB4:at+0xB8], 'little'),
                last_hit_id=int.from_bytes(worker_contexts[at+0xD8:at+0xDC], 'little'),
                current_attack_id=int.from_bytes(worker_contexts[at+0xDC:at+0xE0], 'little'),
                hp=int.from_bytes(worker_contexts[at+0xF0:at+0xF2], 'little'),
                actor_type=worker_contexts[at+0xF2],
                exists=int.from_bytes(worker_contexts[at+0xF6:at+0xF8], 'little')))
        vram = []
        for row in (s['HUD_ROW_BOSS'], 10):
            raw = self.read((s['BG3_TILEMAP_VRAM_WORD']+row*s['TEXT_ROW_ENTRIES'])*2,
                            64, 'snesVideoRam')
            vram.append([int.from_bytes(raw[i:i+2], 'little') for i in range(0, 64, 2)])
        result = dict(frame=self.frame, phase=self.phase, stage=self.u8('Game_StageIndex'),
                      inputs=[dict(port=port, press=self.u16(prefix+'press_Addr'),
                                   trigger=self.u16(prefix+'trigger_Addr'),
                                   raw=self.u16(prefix+'last_raw_Addr'))
                              for port, prefix in enumerate(('Input_', 'Input2_'))],
                      state=self.u16('Game_State'), spawn_index=self.u8('Spawn_Index'), actors=rows,
                      source_visual=dict(
                          error=self.u8('SourceVisual_Error'),
                          last_error=self.u8('SourceVisual_DebugLastError'),
                          queue_stage=self.u8('SourceVisual_DebugQueueStage'),
                          key=self.read(s['SourceVisual_Key'], 4).hex(),
                          host_d=self.u16('SourceVisual_HostLastD'),
                          host_roster=self.u8('SourceVisual_HostLastRoster'),
                          host_policy=self.u8('SourceVisual_HostLastPolicy'),
                          call_count=self.u16('SourceVisual_CallCount'),
                          presentations=self.u16('SourceVisual_AfterPassCount')),
                      source_world=dict(hit_events=self.u16('S6Host_HitEvents'),
                                         frame_events=self.u16('S6Host_FrameEvents'),
                                         attack_id=int.from_bytes(
                                             self.read(0x11720,4,'snesSaveRam'),'little')),
                      worker_mailbox=dict(
                          ticks_target=int.from_bytes(self.read(0x12002,2,'snesSaveRam'),'little'),
                          ticks_completed=int.from_bytes(self.read(0x12004,2,'snesSaveRam'),'little'),
                          snapshot_request=self.read(0x12006,1,'snesSaveRam')[0],
                          snapshot_ack=self.read(0x12007,1,'snesSaveRam')[0],
                          fault=self.read(0x1200A,1,'snesSaveRam')[0],
                          mutation_fence=self.read(0x1200C,1,'snesSaveRam')[0],
                          event_producer=int.from_bytes(self.read(0x12430,2,'snesSaveRam'),'little'),
                          event_consumer=int.from_bytes(self.read(0x12432,2,'snesSaveRam'),'little'),
                          event_overflow=self.read(0x12434,1,'snesSaveRam')[0],
                          owner=self.read(0x7E175C,1,'snesMemory')[0],
                          owner_state=self.read(0x7E175E,1,'snesMemory')[0]),
                      targets=[int.from_bytes(targets[i:i+2], 'little') for i in (0, 2)],
                      worker_actors=worker_rows, worker_roles=host, vram=vram)
        self.report['samples'].append(result)
        return result

    def step(self, buttons=0, port=0):
        if self.combat_deadline is not None and not self.phase.startswith('native_removal') and self.frame >= self.combat_deadline:
            raise AssertionError(f'{self.phase}: total 900-frame native combat budget exhausted')
        from _harness import exact_input_edge, run_frames_exact
        if buttons:
            delivery = exact_input_edge(self.m, buttons, 1, port)
            self.report.setdefault('input_edges', []).append(dict(
                frame=self.frame+1, phase=self.phase, port=port, buttons=buttons,
                delivery=delivery))
        else:
            run_frames_exact(self.m, 1)
        self.frame += 1
        events = self.m.drain_notifications(timeout=0)
        if events:
            self.report['events'].append(dict(frame=self.frame, notifications=events))
        return self.snapshot()

    def neutralize_inputs(self, stable_rounds=2, max_rounds=8):
        from _harness import exact_input_edge
        previous = None
        stable = 0
        start = self.frame
        snap = self.report['samples'][-1]
        for _ in range(max_rounds):
            for port in (0, 1):
                delivery = exact_input_edge(self.m, 0, 8, port=port)
                self.report.setdefault('input_edges', []).append(dict(
                    frame=self.frame+1, phase='neutralize_before_combat', port=port,
                    buttons=0, delivery=delivery))
                self.frame += 8
            snap = self.snapshot()
            positions = tuple(snap['worker_actors'][port]['x'] for port in (0, 1))
            released = all(not row['press'] for row in snap['inputs'])
            stable = stable + 1 if positions == previous and released else 0
            if stable >= stable_rounds:
                self.report['input_settle'] = dict(start=start, end=self.frame,
                    rounds=(self.frame-start)//16, stable_positions=positions)
                return snap
            previous = positions
        raise AssertionError('source input queue did not settle after neutral release')

    @contextmanager
    def mutation_fence(self, reason):
        """Park the persistent source worker before fixture-only POS writes."""
        if self.fixture_fence_held:
            raise AssertionError('nested source mutation fence')
        control, fault = 0x1200C, 0x1200A
        before = self.read(control, 1, 'snesSaveRam')[0]
        if before != 0:
            raise AssertionError(f'mutation fence not idle before {reason}: {before}')
        # Match the production S-CPU store to $41:200C. Actor rows are read
        # directly through the SaveRAM view, but the control handshake must
        # travel through the mapped SNES bus so SA-1 observes the same write.
        self.m.write_memory('snesMemory', 0x41200C, '01')
        request_readback = self.read(control, 1, 'snesSaveRam')[0]
        if request_readback != 1:
            raise AssertionError(f'mutation fence request bus write read back {request_readback}')
        requested = self.frame
        try:
            for _ in range(8):
                snap = self.step()
                state = self.read(control, 1, 'snesSaveRam')[0]
                worker_fault = self.read(fault, 1, 'snesSaveRam')[0]
                if worker_fault:
                    raise AssertionError(f'mutation fence worker fault {worker_fault}')
                if state == 2:
                    self.m.pause()
                    self.fixture_fence_held = True
                    rows = [dict(slot=slot, x=row['x'], y=row['y'],
                                 exists=row['exists'], hp=row['hp'])
                            for slot, row in enumerate(snap['worker_actors'])]
                    self.report.setdefault('mutation_fences', []).append(dict(
                        reason=reason, request_field=requested, parked_field=self.frame,
                        wait_fields=self.frame-requested, state=state, worker_actors=rows))
                    break
                if state != 1:
                    raise AssertionError(f'mutation fence invalid state {state}')
            else:
                final_state = self.read(control, 1, 'snesSaveRam')[0]
                final_fault = self.read(fault, 1, 'snesSaveRam')[0]
                target = int.from_bytes(self.read(0x12002, 2, 'snesSaveRam'), 'little')
                completed = int.from_bytes(self.read(0x12004, 2, 'snesSaveRam'), 'little')
                owner = self.read(0x7E175C, 1, 'snesMemory')[0]
                owner_state = self.read(0x7E175E, 1, 'snesMemory')[0]
                cpu_debug = {}
                for cpu in ('Sa1', 'Snes'):
                    try:
                        cpu_debug[cpu] = self.m.get_cpu_state(cpu_type=cpu)
                    except Exception as debug_error:
                        cpu_debug[cpu] = {'error': repr(debug_error)}
                self.report['mutation_fence_timeout'] = dict(
                    field=self.frame, reason=reason, control=final_state,
                    fault=final_fault, ticks_target=target,
                    ticks_completed=completed, owner=owner,
                    owner_state=owner_state, cpu=cpu_debug)
                raise AssertionError(
                    f'mutation fence did not park within 8 fields ({reason}); '
                    f'control={final_state} fault={final_fault} '
                    f'ticks={completed}/{target} owner={owner}/{owner_state}')
            yield
        finally:
            if self.fixture_fence_held:
                self.m.write_memory('snesMemory', 0x41200C, '00')
                self.fixture_fence_held = False
                self.m.resume()
                self.report.setdefault('mutation_fences', []).append(dict(
                    reason=reason, release_field=self.frame, state=0))
            else:
                # A timed-out request must never strand the production worker.
                state = self.read(control, 1, 'snesSaveRam')[0]
                if state != 0:
                    self.m.write_memory('snesMemory', 0x41200C, '00')

    def fixture_write(self, address, value, size, reason):
        s, base = self.s, 0x11900
        # The S-CPU entity rows at $7E0A00 are only mirrors on this runtime;
        # the persistent SA-1 contexts occupy BW-RAM offset $11900 (the
        # physical offset corresponding to CPU bank $41:$1900) with a
        # $100-byte slot stride. Their source-DP X/Y words are at $14/$16;
        # the native S-CPU CHAR_POS_X/Y layout is a different structure. The
        # native touch-pickup service consumes the projected player rows, so
        # P1/P2 position isolation may update those two coordinate fields as
        # well; no gameplay state or NPC mirror field is writable here.
        allowed_bw = {(base+i*0x100+off, 2) for i in range(6) for off in (0x14, 0x16)}
        cpu_base = 0x7E0000 | s['PlayerEntity_DpBase']
        allowed_cpu = {(cpu_base+i*s['CHAR_ZP_LEN']+off, 2)
                       for i in (0, 1) for off in (s['CHAR_POS_X'], s['CHAR_POS_Y'])}
        if (address, size) in allowed_bw:
            if not self.fixture_fence_held:
                raise AssertionError('SA-1 actor fixture write outside mutation fence')
            memory = 'snesSaveRam'
        elif (address, size) in allowed_cpu:
            if not self.fixture_fence_held:
                raise AssertionError('native position mirror write outside mutation fence')
            memory = 'snesMemory'
        else:
            raise AssertionError('probe attempted a non-fixture write')
        self.m.write_u16(address, value, mem_type=memory)
        readback = int.from_bytes(self.read(address, size, memory), 'little')
        self.report['fixture_writes'].append(dict(frame=self.frame, address=address,
                                                  memory=memory, size=size, value=value,
                                                  readback=readback, reason=reason))

    def native_y_before_worker(self, player, value, reason):
        """Fixture-only native position write before SA-1 ownership starts."""
        s = self.s
        owner = self.read(0x7E175C, 1, 'snesMemory')[0]
        if owner != 0 or self.fixture_fence_held:
            raise AssertionError('pre-owner native position write after SA-1 ownership began')
        address = ((0x7E0000 | s['PlayerEntity_DpBase'])
                   + player*s['CHAR_ZP_LEN'] + s['CHAR_POS_Y'])
        self.m.pause()
        try:
            self.m.write_u16(address, value, mem_type='snesMemory')
            readback = int.from_bytes(self.read(address, 2), 'little')
            if readback != value:
                raise AssertionError('pre-owner native position fixture readback mismatch')
            self.report['fixture_writes'].append(dict(
                frame=self.frame, address=address, memory='snesMemory', size=2,
                value=value, readback=readback, owner=owner,
                reason=reason+' (worker not yet owner)'))
        finally:
            self.m.resume()

    def isolate(self, attacker=None, direction_override=None):
        camera, s = self.u16('Screen_PosX'), self.s
        base = 0x11900
        with self.mutation_fence('position-only encounter isolation'):
            attacker_x = camera + 120
            target_x = attacker_x
            if attacker is not None:
                # Kula's authored attack box begins 59 source units forward
                # of the source-world anchor. Read facing only after the
                # worker parks, then place the live target inside that box.
                raw_direction = int.from_bytes(self.read(
                    base+attacker*0x100+0x1A, 2, 'snesSaveRam'), 'little')
                if raw_direction not in (0, 1):
                    raise AssertionError(f'unsupported source facing value {raw_direction}')
                direction = raw_direction if direction_override is None else direction_override
                if direction not in (0, 1):
                    raise AssertionError(f'unsupported fixture attack direction {direction}')
                target_x += -80 if direction == 0 else 80
                self.report.setdefault('attack_setups', []).append(dict(
                    frame=self.frame, attacker=attacker, direction=direction,
                    attacker_x=attacker_x, target_x=target_x,
                    target_offset=target_x-attacker_x,
                    reason='source attack-box forward contact'))
            for i in range(6):
                if i == attacker:
                    x, y = attacker_x, 180
                elif i == self.slot:
                    x, y = target_x, 180
                elif i < 2:
                    x, y = camera+20, (0 if attacker is not None else 145)
                else:
                    x, y = camera+240, (0 if attacker is not None else 220)
                address = base+i*0x100
                self.fixture_write(address+0x14, x, 2, 'position-only encounter isolation')
                self.fixture_write(address+0x16, y, 2, 'position-only encounter isolation')

    def require_identity(self, snap):
        actor = snap['actors'][self.slot]
        if (actor['model'], actor['alias'], actor['map'], actor['palette']) != self.identity:
            raise AssertionError('source instance identity/map/palette changed during encounter')

    def attempt_deadline(self, budget):
        end = self.frame + budget
        return min(end, self.combat_deadline) if self.combat_deadline is not None else end

    def await_retirement(self):
        """Anim_Play_Fall: authored frames, then DEATH_BLINK_FRAMES+1, then FF.

        These are native service ticks, not emulator fields. HUD03 measured
        multi-field services. Eight fields/tick is a bounded probe allowance,
        NOT a claim that BOR's source timer runs at that rate. A 64-field
        no-progress watchdog rejects stalls; neither deadline is extended.
        """
        self.phase = 'native_removal_fall'
        snap = self.snapshot()
        actor = snap['actors'][self.slot]
        count, delay = actor['fall_count'], actor['fall_delay']
        if not 1 <= count <= 255 or not 1 <= delay <= 255:
            raise AssertionError('native_removal: invalid authored fall timing')
        limits = PLAN['limits']
        factor = limits['retirement_fields_per_tick']
        for phase, ticks, complete in (
                ('fall', count*delay+1, lambda a: a['fall_timer'] != 0),
                ('blink', self.s['DEATH_BLINK_FRAMES']+1, lambda a: a['fall_timer'] == 255)):
            self.phase = 'native_removal_' + phase
            end = self.frame + ticks*factor
            last_progress = self.frame
            previous = None
            self.report.setdefault('retirement_bounds', []).append(dict(
                phase=self.phase, start=self.frame, deadline=end, native_ticks=ticks,
                fields_per_tick_allowance=factor, stall_fields=limits['retirement_stall']))
            while not complete(snap['actors'][self.slot]):
                actor = snap['actors'][self.slot]
                progress = (actor['animation_frame'], actor['tick_counter'], actor['fall_timer'])
                if progress != previous:
                    previous, last_progress = progress, self.frame
                if self.frame >= end or self.frame-last_progress >= limits['retirement_stall']:
                    raise AssertionError(f'{self.phase}: native progress deadline exceeded; {actor}')
                if self.frame % 16 == 0:
                    self.isolate()
                snap = self.step()
                self.require_identity(snap)
                if snap['actors'][self.slot]['hp'] != 0:
                    raise AssertionError(f'{self.phase}: dead instance regained HP')
        self.phase = 'native_removal_unlink_dma'
        end = self.frame + limits['row_clear']
        while True:
            if snap['targets'] == [0, 0] and all(row == [0]*32 for row in snap['vram']):
                return snap
            if self.frame >= end:
                raise AssertionError('native_removal_unlink_dma: terminal FF reached but handles/VRAM not cleared')
            snap = self.step()
            self.require_identity(snap)

    def verify_font(self, rom):
        """Live PPU font data, never WRAM staging or an old screenshot oracle."""
        s = self.s
        for label, kind, address, source, length in (
                ('font_tiles', 'snesVideoRam', s['FONT_TILES_VRAM_WORD']*2,
                 s['Font_TilesData'], s['FONT_TILE_BYTES']),
                ('font_palette', 'snesCgRam', s['FONT_CGRAM_BYTE_ADDR'],
                 s['Font_PaletteData'], s['FONT_PALETTE_BYTES'])):
            actual = bytes(self.read(address, length, kind))
            expected = rom[pc(source):pc(source)+length]
            matches = len(expected) == length and actual == expected
            self.report.setdefault('font_checks', []).append(dict(
                frame=self.frame, phase=self.phase, label=label, memory=kind,
                address=address, source=source, length=length, passed=matches,
                actual_sha256=hashlib.sha256(actual).hexdigest(),
                expected_sha256=hashlib.sha256(expected).hexdigest()))
            if not matches:
                raise AssertionError(f'{self.phase}: live {label} differs from candidate ROM')

    def observed_press(self, player, buttons, mask, end):
        # Emulator delivery is not a gameplay poll. Release through a real
        # poll, then hold across fields until the game records a new edge.
        snap = (self.report['samples'][-1] if self.report.get('samples') else
                {'inputs': [dict(press=0), dict(press=0)]})
        if snap['inputs'][player]['press'] & mask:
            for _ in range(8):
                if self.frame >= end:
                    return self.snapshot()
                snap = self.step()
                if not snap['inputs'][player]['press'] & mask:
                    break
            else:
                raise AssertionError(f'{self.phase}: controller release not sampled')
        for _ in range(8):
            if self.frame >= end:
                return self.snapshot()
            # The persistent source world may consume its sequenced input at
            # a different boundary from the field-level controller poll. Hold
            # the real controller edge for several NTSC fields so at least
            # one source command can carry it; a one-field pulse can fall
            # between those boundaries even though Mesen delivered it.
            fields = min(4, end - self.frame)
            if hasattr(self.m, 'set_input'):
                from _harness import exact_input_edge
                delivery = exact_input_edge(self.m, buttons, fields, port=player)
                self.report.setdefault('input_edges', []).append(dict(
                    frame=self.frame+1, phase=self.phase, port=player, buttons=buttons,
                    delivery=delivery))
                self.frame += fields
                snap = self.snapshot()
                if snap['inputs'][player]['trigger'] & mask:
                    return snap
            else:
                # Unit-test harnesses model the held interval as consecutive
                # field steps so they can expose the first sampled edge.
                for _ in range(fields):
                    snap = self.step(buttons, player)
                    if snap['inputs'][player]['trigger'] & mask:
                        return snap
        raise AssertionError(f'{self.phase}: game did not sample port {player} edge {mask:#x}')

    def hit_and_name(self, player, budget=300, phase=None):
        self.phase = phase or f'p{player+1}_hit'
        end = self.attempt_deadline(budget)
        if self.frame >= end:
            raise AssertionError(f'{self.phase}: no remaining native combat budget')
        before = self.snapshot()['actors'][self.slot]['hp']
        snap = self.report['samples'][-1]
        handle = self.slot*self.s['CHAR_ZP_LEN']+1
        next_attack = self.frame
        while self.frame < end:
            attacker = snap['actors'][player]
            victim = snap['actors'][self.slot]
            ready = (attacker['hit_stun'] == 0 and victim['hit_stun'] == 0
                     and attacker['grabbed_by'] == 255 and attacker['grab_target'] == 255
                     # Attack edges are only read at the ordinary player
                     # input gate.  An active attack (selected=2), including
                     # the non-combat GET pose (variant 10), owns animation
                     # advancement and cannot start a fresh move yet.
                     and attacker['selected'] in (0, 1)
                     and attacker['attack_variant'] != self.s['GET_MOVE_VARIANT'])
            if self.frame >= next_attack and ready:
                direction_override = 1 if player == 1 else None
                buttons = self.m.BTN_Y
                if player == 1:
                    # Movement/facing is applied before attack edges inside
                    # the same source tick, avoiding a separate-turn race with
                    # active opponents while still using real port-2 input.
                    buttons |= self.m.BTN_RIGHT
                self.isolate(player, direction_override=direction_override)
                snap = self.observed_press(player, buttons, 0x4000, end)
                next_attack = self.frame + 40
            else:
                # Recover out of contact; never seed stun/grab/animation/HP.
                if attacker['hit_stun'] or attacker['grabbed_by'] != 255:
                    self.isolate()
                snap = self.step()
            self.require_identity(snap)
            hp = snap['actors'][self.slot]['hp']
            if hp < before:
                self.report.setdefault('landed_hit_observations', []).append(dict(
                    frame=self.frame, player=player, before_hp=before, observed_hp=hp,
                    targets=list(snap['targets']), source_hit_events=snap['source_world']['hit_events']))
                # A single source attack can keep its authored hitbox active
                # for several source ticks. Stop issuing input on the first
                # damage observation, then let the ordered HUD event and DMA
                # converge without accidentally driving the victim to death.
                for _ in range(16):
                    if (snap['targets'][player] == handle
                            and snap['vram'][player] == expected_row(
                                self.s, self.binding['name'], hp)):
                        return snap
                    if self.frame >= end:
                        break
                    snap = self.step()
                    self.require_identity(snap)
                    hp = snap['actors'][self.slot]['hp']
                raise AssertionError(
                    f'{self.phase}: source damage landed but HUD target/VRAM did not converge; '
                    f'handle={handle}, targets={snap["targets"]}, hp={hp}, '
                    f'row={snap["vram"][player][1:11]}')
        reason = 'no additional native damage'
        raise AssertionError(f'{self.phase}: P{player+1} {reason}; '
                             f'HP {before}->{snap["actors"][self.slot]["hp"]}, '
                             f'frame={self.frame}, attempt_end={end}, '
                             f'combat_deadline={self.combat_deadline}')


def run(args):
    if not args.output or args.output.exists():
        raise ValueError('--run requires a new --output path')
    paths, hashes, sym, rom, binding = preflight(args)
    # Delayed imports ensure plan/preflight inspection cannot launch Mesen.
    sys.path.insert(0, str(ROOT / 'tools/verify'))
    from _harness import open_session, Reporter, exact_input_edge, run_frames_exact, poll_until
    import game_bor_startup_select as startup
    report = dict(plan=PLAN, paths={n: str(p) for n, p in paths.items()},
                  hashes=hashes, binding=binding, checks=[], samples=[], events=[],
                  fixture_writes=[], passed=False, runtime_status='RUNNING', screenshots=[])
    worker_sym_path = paths['rom'].with_name('worker.sym')
    worker_sym_hash = sha(worker_sym_path)
    report['worker_symbols_sha256'] = worker_sym_hash
    def check(label, condition):
        report['checks'].append(dict(label=label, passed=bool(condition)))
        if not condition:
            raise AssertionError(label)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open_session(__file__) as m:
            p = Probe(m, sym, binding, report)
            # Verify the session's mapped ROM as well as disk hashes.
            address = sym['HudOpponentHost_StorePlayerHp']
            check('loaded session contains candidate HUD code',
                  p.read(address, 32) == rom[pc(address):pc(address)+32])
            startup_checks = Reporter('S8-HUD-STARTUP', kind='GATE')
            startup.cold_to_title(m, startup_checks)
            check('cold TITLE startup', all(ok for _, ok in startup_checks.results))
            exact_input_edge(m, m.BTN_START, 1, port=1)
            run_frames_exact(m, 2)
            exact_input_edge(m, m.BTN_START, 1, port=0)
            check('real difficulty selector ready', poll_until(m, lambda _:
                  p.u16('Game_State') == sym['GAME_STATE_CHARSELECT'] and
                  p.u8('BorDifficulty_Chosen') == 1, 240))
            for _ in range(binding['difficulty']):
                exact_input_edge(m, m.BTN_RIGHT, 1, port=0)
                run_frames_exact(m, 1)
            check('Normal cursor selected', p.u8('BorSet_Selected') == binding['difficulty'])
            exact_input_edge(m, m.BTN_START, 1, port=0)
            check('Normal accepted and player selector ready', poll_until(m, lambda _:
                  p.u8('BorDifficulty_Chosen') == 3 and p.u8('CharSelect_Step') == 3, 240))
            entries = startup.normal_player_entries('bor-original')
            ordinal, runtime = next((i, index) for i, (index, entry) in enumerate(entries)
                                    if startup.entry_name(entry).upper() == 'KULA')
            for port in (0, 1):
                for _ in range(ordinal):
                    exact_input_edge(m, m.BTN_RIGHT, 1, port=port)
                    run_frames_exact(m, 1)
            exact_input_edge(m, m.BTN_START, 1, port=1)
            exact_input_edge(m, m.BTN_START, 1, port=0)
            for _ in range(PLAN['limits']['stage_load']):
                snap = p.step()
                if snap['stage'] == binding['stage'] and snap['state'] == sym['GAME_STATE_PLAYING']:
                    break
            else:
                raise AssertionError('real Normal selection did not reach Normal 1A')
            # Normal 1A's authored pickup overlaps the players' stage-entry
            # lane. Park the S-CPU and set only their depth coordinates before
            # the persistent worker claims the source contexts, so binding
            # starts in the safe lane and cannot inherit a GET pose.
            p.native_y_before_worker(0, 0, 'position-only pickup avoidance')
            p.native_y_before_worker(1, 0, 'position-only pickup avoidance')
            snap = p.snapshot()
            # The state byte changes before the first post-OOP render seam.
            # That seam starts the persistent worker epoch; do not issue a
            # fixture mutation fence against the previous (inactive) epoch.
            for _ in range(60):
                mb = snap['worker_mailbox']
                if (mb['owner'] == 1 and mb['owner_state'] == 2
                        and mb['ticks_target'] > 0
                        and mb['ticks_target'] == mb['ticks_completed']):
                    report['worker_ready'] = dict(field=p.frame, mailbox=mb,
                                                  actors=snap['worker_actors'])
                    break
                snap = p.step()
            else:
                raise AssertionError(
                    'Normal PLAYING did not acquire persistent SA-1 owner and complete a fresh tick; '
                    f"mailbox={snap['worker_mailbox']}")
            check('persistent SA-1 owns the live Normal source world',
                  snap['worker_mailbox']['owner'] == 1
                  and snap['worker_mailbox']['owner_state'] == 2)
            check('real Normal campaign and independent P1/P2 identities',
                  p.u8('Game_CampaignId') == 3 and p.u8('Game_CampaignOrdinal') == 0
                  and p.u8('G13_TwoPlayerEnabled') == 1
                  and p.u8('BorSelect_P1Ready') == 1 and p.u8('BorSelect_P2Ready') == 1
                  and all(a['model'] == runtime for a in snap['actors'][:2]))
            check('stage reset clears both opponent handles', snap['targets'] == [0, 0])
            for name in ('HudOpponentHost_VictimX', 'HudOpponentHost_StorePlayerHp',
                         'HudOpponentHost_Grab', 'HudOpponentHost_RetireX', 'HudOpponent_Reset'):
                m.add_exec_hook(sym[name])
            for name in ('WHost_PlayerAction__attack', 'W6_WorldAttack',
                         'W6_TryHitOne__geometry', 'W6_SourceCollision',
                         'W6_TryHitOne__damage', 'W6_HitEffects'):
                m.add_exec_hook(sym['_SA1_' + name], cpu_type='Sa1')
            # Keep both players on a fixture-only depth lane away from the
            # authored ground pickups while P1 advances the stage to the
            # target spawn.  The probe later positions the real actors for
            # melee; it never seeds inventory, GET, attack, or HP state.
            with p.mutation_fence('player position-only pickup avoidance'):
                for player in (0, 1):
                    p.fixture_write(0x11900 + player*0x100 + 0x16, 0, 2,
                                    'position-only pickup avoidance during spawn wait')
                    native_y = ((0x7E0000 | sym['PlayerEntity_DpBase'])
                                + player*sym['CHAR_ZP_LEN'] + sym['CHAR_POS_Y'])
                    p.fixture_write(native_y, 0, 2,
                                    'position-only pickup avoidance during spawn wait')
            p.phase = 'organic_spawn'
            for _ in range(PLAN['limits']['spawn']):
                snap = p.step(m.BTN_RIGHT, 0)
                candidates = [a for a in snap['actors'][2:] if a['alias'] == binding['alias_id']
                              and a['model'] == binding['roster'] and a['hp'] > 0]
                if candidates:
                    target = candidates[0]
                    p.slot = target['slot']
                    break
            else:
                raise AssertionError('source alias spawn did not appear through Spawn_Play')
            report['native_target'] = dict(slot=target['slot'], hp=target['hp'],
                                           alias=target['alias'], model=target['model'])
            p.identity = (target['model'], target['alias'], target['map'], target['palette'])
            check('organic instance has authored map', target['map'] == binding['map'])
            check('enough authored HP for two player hits', target['hp'] > sym['CHAR_HP_PER_HIT'])
            player_at_spawn = snap['worker_actors'][0]
            enemy_at_spawn = snap['worker_actors'][target['slot']]
            snap = p.neutralize_inputs()
            enemy_after_neutral = snap['worker_actors'][target['slot']]
            activity = dict(
                player_start=report['worker_ready']['actors'][0],
                player_at_spawn=player_at_spawn,
                enemy_at_spawn=enemy_at_spawn,
                enemy_after_neutral=enemy_after_neutral)
            report['source_world_activity'] = activity
            check('real controller input moved the SA-1 player context',
                  activity['player_at_spawn']['x'] != activity['player_start']['x'])
            check('organic opponent AI advanced between neutral snapshots',
                  (enemy_after_neutral['x'], enemy_after_neutral['y'],
                   enemy_after_neutral['current_role'], enemy_after_neutral['behavior_state'])
                  != (enemy_at_spawn['x'], enemy_at_spawn['y'],
                      enemy_at_spawn['current_role'], enemy_at_spawn['behavior_state']))
            p.combat_deadline = p.frame + PLAN['limits']['combat']
            first = p.hit_and_name(0)
            p.verify_font(rom)
            check('P1 damage/name observed', first['targets'][0] == p.slot*sym['CHAR_ZP_LEN']+1)
            mb = first['worker_mailbox']
            check('sequenced event ring drained without overflow',
                  mb['event_producer'] == mb['event_consumer'] and mb['event_overflow'] == 0)
            check('source worker protocol fault remains clear', mb['fault'] == 0)
            report['screenshots'].append(m.take_screenshot())
            check('bounded probe never left Normal 1A', all(s['stage'] == binding['stage']
                  for s in report['samples'] if s['phase'] != 'load'))
            m.pause()
            check('candidate artifacts remained unchanged', all(sha(paths[n]) == h for n, h in hashes.items()))
            report['passed'] = True
            report['runtime_status'] = 'PASS_PERSISTENT_SA1_HIT_HUD'
    except Exception as error:
        report['runtime_status'] = 'FAIL'
        report['error'] = repr(error)
        raise
    finally:
        # Audit on FAIL too. Missing/changed files must never leave a PASS.
        was_passed = report['passed']
        report['final_hashes'] = {}
        for name, path in paths.items():
            try:
                report['final_hashes'][name] = sha(path)
            except Exception as error:
                report['final_hashes'][name] = {'error': repr(error)}
        unchanged = report['final_hashes'] == hashes
        report['worker_symbols_unchanged'] = (
            sha(worker_sym_path) == worker_sym_hash if worker_sym_path.is_file() else False)
        report['artifacts_unchanged'] = unchanged
        if not unchanged or not report['worker_symbols_unchanged']:
            report['passed'] = False
            report['runtime_status'] = 'FAIL'
            report['artifact_error'] = 'candidate ROM/MSU/symbol/worker-symbol artifacts changed or became unreadable'
        # Preserve actual screenshots when the server returns a path; retain
        # the original response too. Machine VRAM PASS is not manual acceptance.
        for i, shot in enumerate(report['screenshots']):
            source = shot.get('path') if isinstance(shot, dict) else None
            if source and Path(source).is_file():
                dest = args.output.with_name(args.output.stem + f'-{i}.png')
                if not dest.exists():
                    try:
                        shutil.copyfile(source, dest)
                        shot['saved_path'] = str(dest)
                    except Exception as error:
                        shot['copy_error'] = repr(error)
        with args.output.open('x', encoding='utf-8') as output:
            output.write(json.dumps(report, indent=2) + '\n')
        if was_passed and (not unchanged or not report['worker_symbols_unchanged']):
            raise AssertionError(report['artifact_error'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--rom-sha256')
    parser.add_argument('--msu-sha256')
    parser.add_argument('--symbols-sha256')
    parser.add_argument('--symbols', type=Path, default=ROOT / 'src/main.sym',
                        help='exact candidate symbol file (build currently emits src/main.sym)')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.run:
        print(json.dumps(PLAN, indent=2))
        return
    run(args)


if __name__ == '__main__':
    main()
