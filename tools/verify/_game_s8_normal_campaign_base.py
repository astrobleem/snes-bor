# Reconstructed base implementation; see RECOVERY.md for validation limits.
"""S8 accelerated native campaign gate (explicitly opt-in emulator execution).

natural: full Normal, natural showcomplete and both scenes (ENDING: 1997 frames).
skip: full Normal, action-button skips of showcomplete and both scenes.
easy: bounded three-clear Easy control, with completion presentation skipped.

Player and camera progress through native directional input. A sequenced worker
unlink may retire an observed, initialized test AI incarnation to bound combat
duration. No queue index, campaign state, completion counter, scene request,
availability, or player state is injected.
With --spawn-traversal, every packed record executes; accelerated removals use
the production worker command/event path rather than fabricating damage.
Normal requires selection in CHARSELECT's difficulty prompt and availability gate.
Run each mode separately; JSON includes failures and input artifact hashes.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TRAVERSAL_STALL_LIMIT_FIELDS = 1800
SCENE_FIELD_BUDGET = 9000
traversal_camera_wait_button_value = 0

def observer_stale_fields(stage, observed_stage, field, last_change_field):
    if stage == observed_stage:
        return field - last_change_field
    return 0

def bridge_owns_source_actor(policy, exists, context, worker_policy, worker_exists, worker_context):
    return policy == 2 and (exists == 1 and ((6400 <= context and context < 7936) and (context & 255 == 0 and (worker_policy == policy and (worker_exists == 1 and worker_context == context)))))

def traversal_actor_coordinates(mode, worker_owned, ai_mode, source_xy, native_xy):
    if worker_owned:
        if mode == ai_mode:
            return source_xy
    return native_xy

def traversal_signed16(value):
    if value & 32768:
        return value - 65536
    return value

def traversal_biker_approaches(player_x, biker_x, facing_left):
    if facing_left:
        return player_x < biker_x
    return player_x > biker_x

def traversal_biker_attack_window(dx, dy, hitbox_w=32, hitbox_h=16):
    return abs(dy) < hitbox_h and abs(dx) < hitbox_w

def traversal_biker_action(dx, dy, field, mobile=True, approaching=True, hitbox_w=32, hitbox_h=16):
    if mobile:
        if not approaching:
            if abs(dx) >= hitbox_w:
                if abs(dy) > 8:
                    if dy > 0:
                        return 'depth_down'
                    return 'depth_up'
                if dx > 0:
                    return 'approach_right'
                return 'approach_left'
    if abs(dx) >= hitbox_w:
        if dx > 0:
            return 'approach_right'
        return 'approach_left'
    if abs(dy) > 8:
        if dy > 0:
            return 'depth_down'
        return 'depth_up'
    if not traversal_biker_attack_window(dx, dy, hitbox_w, hitbox_h):
        if not mobile:
            if dx > 0:
                return 'approach_right'
            return 'approach_left'
        return 'wait'
    direction = 'right' if dx > 0 else 'left'
    if traversal_attack_held(field):
        return 'attack_' + direction
    return 'face_' + direction

def traversal_target_key(target, p1x, p1y, direction):
    _, ax, ay, *_ = target
    if direction == 'left':
        forward = ax <= p1x + 32
    elif direction == 'up':
        forward = ay <= p1y + 24
    elif direction == 'down':
        forward = ay >= p1y - 24
    else:
        forward = ax >= p1x - 32
    return (0 if forward else 1, abs(ax - p1x) + abs(ay - p1y))

def traversal_blocking_props(prop_targets, player_x, player_y, prop_mode, terminal):
    if not prop_targets:
        return []
    destructible = [target for target in prop_targets if target[5] == prop_mode]
    nearby = [target for target in destructible if abs(target[1] - player_x) <= 160 if abs(target[2] - player_y) <= 32]
    if not nearby:
        if not terminal:
            return nearby
        return destructible
    return nearby

def traversal_slots_full(actor_rows, noncombat_mode):
    if len(actor_rows) != 5:
        return False
    return all((row.get('object_live', False) if row.get('input') == noncombat_mode else row.get('hp', 0) > 0 for row in actor_rows))

def traversal_combat_target_blocks(target, player_x, player_y, queue_complete, terminal, direction='right'):
    _, _, actor_x, actor_y, *_ = target
    dx = actor_x - player_x
    dy = actor_y - player_y
    if direction == 'left':
        in_forward_contact = -192 <= dx and dx <= 32
        in_lane = abs(dy) <= 192
    elif direction == 'up':
        in_forward_contact = -192 <= dy and dy <= 32
        in_lane = abs(dx) <= 192
    elif direction == 'down':
        in_forward_contact = -32 <= dy and dy <= 192
        in_lane = abs(dx) <= 192
    else:
        in_forward_contact = -32 <= dx and dx <= 192
        in_lane = abs(dy) <= 192
    if direction == 'left':
        nearby = (-128 <= dx and dx <= 32) and abs(dy) <= 64
    elif direction == 'up':
        nearby = (-128 <= dy and dy <= 32) and abs(dx) <= 128
    elif direction == 'down':
        nearby = (-32 <= dy and dy <= 128) and abs(dx) <= 128
    else:
        nearby = (-32 <= dx and dx <= 128) and abs(dy) <= 64
    return queue_complete or (terminal or (nearby or (in_forward_contact and in_lane)))

def traversal_combat_engagement_needed(target, player_x, player_y, *, group_gate_blocked=False, queue_complete=False, terminal=False, direction='right'):
    return group_gate_blocked or traversal_combat_target_blocks(target, player_x, player_y, queue_complete, terminal, direction)

def traversal_continue_needed(player_out, credits):
    return bool(player_out and credits)

def traversal_group_gate_blocks_spawn(active_enemy_count, group_min):
    return group_min > 0 and active_enemy_count >= group_min

def traversal_chase_axis(dx, dy):
    if abs(dx) > 160:
        return 'x'
    if abs(dy) > 8:
        return 'y'
    if abs(dx) > 40:
        return 'x'
    return 'attack'

def traversal_terminal_clamp(state):
    return bool(state.get('spawn_waiting')) or (state['camera_max_x'] > state['camera_min_x'] and state['camera_x'] >= state['camera_max_x'])

def traversal_terminal_prop_clear_required(slots_full, spawn_stalled, terminal):
    return slots_full or (spawn_stalled and terminal)

def traversal_camera_wait(player_x, camera_x, viewport_width, direction):
    if direction == 'right':
        return player_x > camera_x + max(64, viewport_width - 32)
    if direction == 'left':
        return player_x < camera_x + 32
    return False

def traversal_biker_attack_mask(field, button_y, button_x):
    if field // 4 % 2 == 0:
        return button_y
    return button_x

def traversal_prop_chase_action(dx, dy, slots_full):
    if not slots_full:
        if abs(dx) <= 160:
            return 'bypass'
    if slots_full:
        if 32 < abs(dx):
            if abs(dx) <= 96:
                if abs(dy) <= 8:
                    return 'detour'
        else:
            abs(dx)
    if slots_full:
        if 32 < abs(dx):
            if abs(dx) <= 96:
                if abs(dy) > 8:
                    return 'approach'
        else:
            abs(dx)
    if abs(dx) <= 32:
        if abs(dy) <= 8:
            return 'attack'
    if slots_full:
        if abs(dx) <= 160:
            if abs(dy) > 8:
                if abs(dx) <= 32:
                    return 'lane'
                return 'approach'

def traversal_pickup_needed(pickup_type, player_hp, hp_max):
    return pickup_type == 4 or (pickup_type in (1, 2) and player_hp < hp_max)

def traversal_pickup_action(dx, dy, field):
    if abs(dx) > 24:
        if dx > 0:
            return ('approach_right', False)
        return ('approach_left', False)
    if abs(dy) > 12:
        if dy > 0:
            return ('depth_down', False)
        return ('depth_up', False)
    return ('collect', traversal_attack_held(field))

def traversal_prop_bypass_complete(player_y, prop_y, direction, margin=48):
    if direction < 0:
        return player_y <= prop_y - margin
    return player_y >= prop_y + margin

def traversal_prop_bypass_action(dy, margin=48):
    if abs(dy) > margin:
        return 'forward'
    if dy > 0:
        return 'depth_up'
    return 'depth_down'

def traversal_lifecycle_input(button, hp, player_out):
    if not hp:
        if player_out:
            return button
        return None
    return button

def traversal_attack_held(field):
    return field % 4 < 2

def traversal_combat_attack_opportunity(dx, dy):
    return abs(dx) <= 192 and abs(dy) <= 32

def traversal_jump_held(field):
    return field % 12 < 6

def observer_spawn_watchdog_due(index, count, stale_fields, limit):
    return index < count and stale_fields >= limit

def traversal_script(symbols, journal, *, trace_runtime=False, trace_bind=False, trace_sparse=False, trace_player_move=False, trace_ownership=False, trace_pc_only=False, trace_player_lifecycle=False, world_symbols=None):
    from game_s8_stage_bounds import admission_script
    from game_s8_stage_bounds import lorom_offset
    initial_path = journal.with_suffix('.initial-ai.txt')
    initial_capture = ''.join([' _s8_spawn_calls=(_s8_spawn_calls or 0)+1\n _s8_initial_ai_seen=_s8_initial_ai_seen or {}\n local stage=rd(', str(symbols['Game_StageIndex']), ',2)\n if not _s8_initial_ai_seen[stage] and rd(', str(symbols['Spawn_Index']), ',1)==0 then\n  _s8_initial_ai_seen[stage]=true\n  local file=assert(io.open(', str(json.dumps(initial_path.as_posix())), ",'a'))\n  file:write(string.format('%d -1 0 0 0 0\\n',stage))\n  for slot=1,5 do\n   local offset=slot*", str(symbols['CHAR_ZP_LEN']), '\n   local actor=0x', format(8257536 + symbols['PlayerEntity_DpBase'], '06X'), '+offset\n   local input=rd(actor+', str(symbols['CHAR_INPUT_DRIVEN']), ',1)\n   local hp=rd(actor+', str(symbols['CHAR_HP']), ',1)\n   local idle=rd(actor+', str(symbols['CHAR_IDLE_FCOUNT']), ',1)\n   local obj=rd(actor+', str(symbols['OOP_SELF_SLOT_OFS']), ',1)\n   local live=obj<', str(symbols['OOP_MAX_OBJECTS'] * 2), ' and obj%2==0\n     and rd(', str(symbols['OopFlags']), '+obj,2)%2==1\n     and rd(', str(symbols['OopDp']), '+obj,2)==actor%65536\n     and rd(', str(symbols['OopNum']), '+obj,2)==rd(actor+', str(symbols['OOP_SELF_NUM_OFS']), ',2)\n   if live and hp>0 and idle>0 and (input==', str(symbols['CHAR_INPUT_DRIVEN_AI']), ' or input==', str(symbols['CHAR_INPUT_DRIVEN_BIKER']), ") then\n    file:write(string.format('%d %d %d %d %d %d\\n',stage,slot,offset,\n     rd(actor+", str(symbols['CHAR_ROSTER_INDEX']), ',1),rd(actor+', str(symbols['OOP_SELF_NUM_OFS']), ',2),input))\n   end\n  end\n  file:close()\n end\n'])
    camera_path = journal.with_suffix('.camera-trace.txt')
    player_move_path = journal.with_suffix('.player-move-trace.txt')
    camera_capture = ''.join([' _s8_camera_probe=(_s8_camera_probe or 0)+1\n if _s8_camera_probe%120==0 and rd(', str(symbols['Spawn_Index']), ',1)<4 then\n  local index=rd(', str(symbols['Spawn_Index']), ',1)\n  local rec=', str(symbols['SpawnTable_Wram']), '+index*10\n  local file=assert(io.open(', str(json.dumps(camera_path.as_posix())), ",'a'))\n  local values={_s8_camera_probe,rd(", str(symbols['Nmi_FrameCounter']), ',2),rd(', str(symbols['Game_State']), ',2),\n   index,rd(', str(symbols['Spawn_Count']), ',1),rd(0x7E1601,2),rd(0x7E1600,1),\n   rd(0x7E160A,2),rd(0x7E160E,2),rd(rec,2),rd(', str(symbols['Spawn_GroupMin']), ',1),\n   rd(', str(symbols['Spawn_GroupMax']), ',1),rd(', str(symbols['Spawn_Waiting']), ',1),\n   rd(', str(symbols['Spawn_ScratchEnemyCount']), ',1),rd(', str(symbols['Msu1_StreamBusy']), ',1),\n   rd(', str(symbols['PlayerEntity_Hp']), ',1),rd(0x7E173C,2),rd(0x7E0410,2),\n   rd(0x7E0412,2),rd(0x7E041C,2),rd(0x7E0A00+', str(symbols['CHAR_POS_X']), ',2),\n   rd(0x7E0A00+', str(symbols['CHAR_POS_Y']), ',2),\n   rd(0x7E0A00+', str(symbols['CHAR_INPUT_DRIVEN']), ',1),\n   rd(0x7E0A00+', str(symbols['CHAR_SELECTED']), ",1),\n   rd(0x411914,2),rd(0x411916,2),rd(0x4119E6,2),rd(0x4119E4,2),\n   rd(0x4119C6,2),rd(0x4119D8,2),rd(0x4119B0,2),rd(0x412020,2),\n   rd(0x412004,2)}\n  for i=1,#values do values[i]=tostring(values[i]) end\n  file:write(table.concat(values,'|'),'\\n')\n  file:close()\n  local move_file=assert(io.open(", str(json.dumps(player_move_path.as_posix())), ",'a'))\n  move_file:write(string.format('%d|%d|%d|%d|%d|%d|%d|%d|%d|%d\\n',\n   _s8_camera_probe,rd(", str(symbols['Game_StageIndex']), ',2),\n   rd(', str(symbols['Nmi_FrameCounter']), ',2),index,\n   rd(0x7E0A00+', str(symbols['CHAR_POS_X']), ',2),rd(0x411914,2),\n   rd(0x4119C6,2),rd(0x412020,2),\n   _G._s8_player_move_snes or 0,_G._s8_player_move_sa1 or 0))\n  move_file:close()\n end\n'])
    script = admission_script(symbols, journal, include_controls=True, traversal_fields=True, status_path=journal.with_suffix('.status'), heartbeat_symbol='Spawn_Play', identity_debug_path=journal.with_suffix('.identity-debug.txt'), heartbeat_callback_extra=initial_capture + camera_capture)
    header_write_path = journal.with_suffix('.header-write-trace.txt')
    script = script + ('\nlocal header_trace=assert(io.open(' + str(json.dumps(header_write_path.as_posix())) + ",'a'))\nemu.addMemoryCallback(function(a,v)\n local s=emu.getState()\n header_trace:write(string.format('%d %02X:%04X %04X %02X D=%04X SP=%04X\\n',\n  s['masterClock'],s['cpu.k'],s['cpu.pc'],a,v,s['cpu.d'],s['cpu.sp']))\n header_trace:flush()\nend,emu.callbackType.write,0x0a85,0x0a88,emu.cpuType.snes,emu.memType.snesWorkRam)\n")
    if world_symbols:
        move_callbacks = []
        if 'S6Host_PlayerMove' in world_symbols:
            move_callbacks.append(('snes', 'S6Host_PlayerMove', '_s8_player_move_snes'))
        if 'WHost_PlayerMove' in world_symbols:
            move_callbacks.append(('sa1', 'WHost_PlayerMove', '_s8_player_move_sa1'))
        if move_callbacks:
            script = script + '\n_G._s8_player_move_snes=0\n_G._s8_player_move_sa1=0\n'
        for cpu, label, counter in move_callbacks:
            move_at = lorom_offset(world_symbols[label])
            script = script + ('\nemu.addMemoryCallback(function()\n _G.' + str(counter) + '=_G.' + str(counter) + '+1\nend,emu.callbackType.exec,' + str(move_at) + ',' + str(move_at) + ',emu.cpuType.' + str(cpu) + ',emu.memType.snesPrgRom)\n')
        if trace_player_move:
            if 'WHost_PlayerMove' in world_symbols:
                entry_at = lorom_offset(world_symbols['WHost_PlayerMove'])
                y_store_at = lorom_offset(world_symbols['WHost_PlayerMove__y_store'])
                right_return_at = lorom_offset(world_symbols['WHost_PlayerMove__left']) - 1
                done_at = lorom_offset(world_symbols['WHost_PlayerMove__done'])
                axis_store_at = lorom_offset(world_symbols['W6_EnemyApplyAxis__store_remainder'])
                move_path = journal.with_suffix('.sa1-player-move.txt').resolve().as_posix()
                move_write_path = journal.with_suffix('.sa1-player-move-writes.txt').resolve().as_posix()
                move_window_path = journal.with_suffix('.sa1-player-move-window-writes.txt').resolve().as_posix()
                script = script + ('\nlocal _s8_move_calls=0\nlocal _s8_move_trace=assert(io.open(' + str(json.dumps(move_path)) + ",'w'))\nlocal function _s8_move_row(point)\n if _s8_move_calls>=80 then return end\n _s8_move_calls=_s8_move_calls+1\n local s=emu.getState()\n local d=s['cart.coprocessor.cpu.d'] or -1\n local base=(d>=0x7900 and d<0x7f00) and (0x411900+d-0x7900) or 0x411900\n local function w(a) return emu.read(a,emu.memType.snesMemory)+256*emu.read(a+1,emu.memType.snesMemory) end\n local function bw(a) return emu.read(a,emu.memType.snesSaveRam)+256*emu.read(a+1,emu.memType.snesSaveRam) end\n _s8_move_trace:write(table.concat({point,_s8_move_calls,s['ppu.frameCount'] or -1,\n  d,s['cart.coprocessor.cpu.pc'] or -1,w(base+0x14),w(base+0x16),\n  w(base+0xB0),w(base+0xB2),w(base+0xB4),w(base+0xB6),w(base+0xC6),\n  w(base+0xD8),w(base+0xDA),w(base+0xDC),w(base+0xDE),w(0x412020),w(0x412022),\n  bw(0x11914),bw(0x11916),bw(0x119D8),bw(0x119DA)},'|'),'\\n')\n _s8_move_trace:flush()\nend\nemu.addMemoryCallback(function() _s8_move_row('entry') end,emu.callbackType.exec,\n " + str(entry_at) + ',' + str(entry_at) + ",emu.cpuType.sa1,emu.memType.snesPrgRom)\nemu.addMemoryCallback(function() _s8_move_row('after_x') end,emu.callbackType.exec,\n " + str(y_store_at) + ',' + str(y_store_at) + ",emu.cpuType.sa1,emu.memType.snesPrgRom)\nemu.addMemoryCallback(function() _s8_move_row('right_return') end,emu.callbackType.exec,\n " + str(right_return_at) + ',' + str(right_return_at) + ",emu.cpuType.sa1,emu.memType.snesPrgRom)\nemu.addMemoryCallback(function() _s8_move_row('done') end,emu.callbackType.exec,\n " + str(done_at) + ',' + str(done_at) + ",emu.cpuType.sa1,emu.memType.snesPrgRom)\nemu.addMemoryCallback(function()\n local s=emu.getState();local d=s['cart.coprocessor.cpu.d'] or -1\n if _s8_move_calls>=80 then return end\n _s8_move_calls=_s8_move_calls+1\n local base=(d>=0x7900 and d<0x7f00) and (0x411900+d-0x7900) or 0x411900\n local function w(a) return emu.read(a,emu.memType.snesMemory)+256*emu.read(a+1,emu.memType.snesMemory) end\n _s8_move_trace:write(table.concat({'axis_store',_s8_move_calls,s['ppu.frameCount'] or -1,\n  d,s['cart.coprocessor.cpu.pc'] or -1,w(base+0x14),w(base+0x16),w(base+0x90),\n  w(base+0x92),w(base+0x94),w(base+0x96),w(base+0x98),w(base+0xAA),w(base+0xAE),\n  w(base+0xB0),w(base+0xC6),w(base+0xD8),w(base+0xDA),w(0x412020)},'|'),'\\n')\n _s8_move_trace:flush()\nend,emu.callbackType.exec," + str(axis_store_at) + ',' + str(axis_store_at) + ',emu.cpuType.sa1,emu.memType.snesPrgRom)\nlocal _s8_move_writes=0\nlocal _s8_move_write_trace=assert(io.open(' + str(json.dumps(move_write_path)) + ",'w'))\nemu.addMemoryCallback(function(a,v)\n if _s8_move_writes>=80 then return end\n _s8_move_writes=_s8_move_writes+1\n local s=emu.getState()\n _s8_move_write_trace:write(table.concat({'write',_s8_move_writes,s['ppu.frameCount'] or -1,\n  s['cart.coprocessor.cpu.d'] or -1,s['cart.coprocessor.cpu.pc'] or -1,a,v,\n  emu.read(0x11914,emu.memType.snesSaveRam)+256*emu.read(0x11915,emu.memType.snesSaveRam),\n  emu.read(0x11916,emu.memType.snesSaveRam)+256*emu.read(0x11917,emu.memType.snesSaveRam)},'|'),'\\n')\n _s8_move_write_trace:flush()\nend,emu.callbackType.write,0x11914,0x11915,emu.cpuType.sa1,emu.memType.snesSaveRam)\nlocal _s8_move_window_writes=0\nlocal _s8_move_window_trace=assert(io.open(" + str(json.dumps(move_window_path)) + ",'w'))\nemu.addMemoryCallback(function(a,v)\n if _s8_move_window_writes>=80 then return end\n _s8_move_window_writes=_s8_move_window_writes+1\n local s=emu.getState()\n _s8_move_window_trace:write(table.concat({'window_write',_s8_move_window_writes,\n  s['ppu.frameCount'] or -1,s['cart.coprocessor.cpu.d'] or -1,\n  s['cart.coprocessor.cpu.pc'] or -1,a,v,\n  emu.read(0x7914,emu.memType.sa1Memory)+256*emu.read(0x7915,emu.memType.sa1Memory),\n  emu.read(0x11914,emu.memType.snesSaveRam)+256*emu.read(0x11915,emu.memType.snesSaveRam)},'|'),'\\n')\n _s8_move_window_trace:flush()\nend,emu.callbackType.write,0x7914,0x7915,emu.cpuType.sa1,emu.memType.sa1Memory)\n")
    if trace_sparse:
        sparse_path = Path(os.environ.get('S8_TRACE_SPARSE_PATH', str(journal.with_suffix('.sparse-pc-trace.txt')))).resolve().as_posix()
        script = script + ''.join(['\nlocal _s8_sparse_frame=0\nlocal function _s8_sparse_word(a,mt)\n return emu.read(a,mt)+256*emu.read(a+1,mt)\nend\nemu.addEventCallback(function()\n _s8_sparse_frame=_s8_sparse_frame+1\n local s=emu.getState();local m=emu.memType.snesMemory\n local b=emu.memType.snesSaveRam\n local stage=_s8_sparse_word(', str(symbols['Game_StageIndex']), ",m)\n if (stage>=23 and _s8_sparse_frame%2~=0) or\n    (stage<23 and _s8_sparse_frame%30~=0) then return end\n local pbr=s['cpu.k'] or 0;local pc=s['cpu.pc'] or 0;local sp=s['cpu.sp'] or 0\n local romoff=(pbr%128)*32768+(pc%32768);local code={}\n for i=0,5 do code[i+1]=string.format('%02x',emu.read(romoff+i,emu.memType.snesPrgRom)) end\n local stack={}\n for i=1,8 do stack[i]=string.format('%02x',emu.read((sp+i)%65536,m)) end\n local row={_s8_sparse_frame,s['ppu.frameCount'] or -1,\n  _s8_sparse_word(", str(symbols['Nmi_FrameCounter']), ',m),\n  _s8_sparse_word(', str(symbols.get('StageTimer_FieldCounter', 8280340)), ',m),\n  _s8_sparse_word(', str(symbols['Nmi_FrameBusy']), ',m),\n  _s8_sparse_word(', str(symbols['Nmi_FrameOver']), ",m),\n  pbr,pc,s['cpu.d'] or -1,s['cpu.a'] or -1,s['cpu.x'] or -1,s['cpu.y'] or -1,\n  sp,s['cpu.ps'] or -1,table.concat(code),table.concat(stack),\n  _s8_sparse_word(", str(symbols['Game_State']), ',m),\n  _s8_sparse_word(', str(symbols['Game_StatePrev']), ',m),\n  _s8_sparse_word(', str(symbols['Game_StageIndex']), ',m),\n  emu.read(', str(symbols['Spawn_Index']), ',m),\n  _s8_sparse_word(', str(symbols['Screen_PosX']), ',m),\n  _s8_sparse_word(', str(symbols['S6Game_TickCommit']), ',m),\n  _s8_clockadvance_hits or 0,_s8_clockhost_hits or 0,_s8_relay_hits or 0,\n  _s8_relay_run_hits or 0,\n  _s8_sparse_word(0x12002,b),_s8_sparse_word(0x12004,b),\n  _s8_sparse_word(0x12008,b),emu.read(0x1200a,b),\n  _s8_sparse_word(0x12430,b),_s8_sparse_word(0x12432,b),\n  _s8_sparse_word(0x12434,b),\n  _s8_sparse_word(0x7e1760,m),_s8_sparse_word(0x7e175e,m),\n  _s8_sparse_word(', str(symbols.get('ExcA', 0)), ',m),\n  _s8_sparse_word(', str(symbols.get('ExcPc', 0)), ',m),\n  emu.read(', str(symbols.get('ExcPb', 0)), ',m),\n  _s8_sparse_word(', str(symbols.get('ExcErr', 0)), ',m),\n  _s8_sparse_word(0x7e1764,m),\n  _s8_sparse_word(', str(symbols['S6Game_TickCommit']), ",m),\n  _s8_sparse_word(0x7e173c,m),\n  s['cart.coprocessor.cpu.k'] or -1,s['cart.coprocessor.cpu.pc'] or -1,\n  s['cart.coprocessor.cpu.d'] or -1,s['cart.coprocessor.cpu.sp'] or -1,\n  s['cart.coprocessor.cpu.ps'] or -1}\n for i=1,#row do row[i]=tostring(row[i]) end\n local f=assert(io.open(", str(json.dumps(sparse_path)), ",'a'))\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.eventType.endFrame)\n"])
    if trace_player_lifecycle:
        lifecycle_path = journal.with_suffix('.player-lifecycle-trace.txt').resolve().as_posix()
        lifecycle_points = (('Game_State_Play__playing', 'game_play', False), ('StageTimerHost_ServiceDeaths', 'death_service', False), ('Core_Oop_Play', 'oop_play', False), ('CharacterEntity_Play', 'p1_actor_play', True), ('CharacterEntity_Play__bounds_unowned', 'p1_after_bounds', True), ('CharacterEntity_Play__not_out', 'p1_not_out', True), ('CharacterEntity_Play__context_ready', 'p1_context_ready', True), ('CharacterEntity_Play__no_ai_target', 'p1_before_anim', True), ('CharacterEntity_Play__no_context_exit', 'p1_context_exit', True), ('Anim_Play', 'anim_any', False), ('Anim_Play', 'p1_anim_play', True), ('Anim_Play_Fall', 'fall_any', False), ('Anim_Play_Fall', 'p1_fall_play', True), ('StageBoundsHost_BeforeActor__owned', 'bounds_owned_any', False), ('StageBoundsHost_BeforeActor__no', 'bounds_unowned_any', False), ('StageBoundsHost_BeforeActor__owned', 'p1_bounds_owned', True), ('StageBoundsHost_BeforeActor__no', 'p1_bounds_unowned', True))
        script = script + '\n_G._s8_player_lifecycle_counts={}\n'
        for label, key, p1_only in lifecycle_points:
            address = lorom_offset(symbols[label])
            actor_guard = ''
            if p1_only:
                actor_guard = " local s=emu.getState()\n if (s['cpu.d'] or -1)~=0x0A00 then return end\n"
            script = script + ('\n_G._s8_player_lifecycle_counts[' + str(json.dumps(key)) + ']=0\nemu.addMemoryCallback(function()\n' + str(actor_guard) + ' _G._s8_player_lifecycle_counts[' + str(json.dumps(key)) + ']=\n  _G._s8_player_lifecycle_counts[' + str(json.dumps(key)) + ']+1\nend,emu.callbackType.exec,' + str(address) + ',' + str(address) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
        script = script + ''.join(['\nlocal _s8_player_lifecycle_frame=0\nlocal function _s8_lifecycle_rd(a,n)\n local v=0;for i=0,n-1 do v=v+emu.read(a+i,emu.memType.snesMemory)*256^i end;return v\nend\nemu.addEventCallback(function()\n _s8_player_lifecycle_frame=_s8_player_lifecycle_frame+1\n if _s8_player_lifecycle_frame%30~=0 then return end\n local m=emu.memType.snesMemory\n local row={_s8_player_lifecycle_frame,\n  _s8_lifecycle_rd(', str(symbols['Nmi_FrameCounter']), ',2),\n  _s8_lifecycle_rd(', str(symbols['Game_State']), ',2),\n  _s8_lifecycle_rd(', str(symbols['Game_StageIndex']), ',2),\n  emu.read(', str(symbols['Spawn_Index']), ",m),\n  _G._s8_player_lifecycle_counts['game_play'],\n  _G._s8_player_lifecycle_counts['death_service'],\n  _G._s8_player_lifecycle_counts['oop_play'],\n  _G._s8_player_lifecycle_counts['p1_actor_play'],\n  _G._s8_player_lifecycle_counts['p1_after_bounds'],\n  _G._s8_player_lifecycle_counts['p1_not_out'],\n  _G._s8_player_lifecycle_counts['p1_context_ready'],\n  _G._s8_player_lifecycle_counts['p1_before_anim'],\n  _G._s8_player_lifecycle_counts['p1_context_exit'],\n  _G._s8_player_lifecycle_counts['anim_any'],\n  _G._s8_player_lifecycle_counts['p1_anim_play'],\n  _G._s8_player_lifecycle_counts['fall_any'],\n  _G._s8_player_lifecycle_counts['p1_fall_play'],\n  _G._s8_player_lifecycle_counts['bounds_owned_any'],\n  _G._s8_player_lifecycle_counts['bounds_unowned_any'],\n  _G._s8_player_lifecycle_counts['p1_bounds_owned'],\n  _G._s8_player_lifecycle_counts['p1_bounds_unowned'],\n  emu.read(0x7e0a00+", str(symbols['CHAR_INPUT_DRIVEN']), ',m),\n  emu.read(0x7e0a00+', str(symbols['CHAR_HP']), ',m),\n  emu.read(0x7e0a00+', str(symbols['CHAR_SELECTED']), ',m),\n  emu.read(0x7e0a00+', str(symbols['CHAR_FRAME_INDEX']), ',m),\n  emu.read(0x7e0a00+', str(symbols['CHAR_TICK_COUNTER']), ',m),\n  emu.read(0x7e0a00+', str(symbols['CHAR_FALL_FCOUNT']), ',m),\n  emu.read(0x7e0a00+', str(symbols['CHAR_FALL_DELAY']), ',m),\n  emu.read(0x7e0a00+', str(symbols['CHAR_FALL_STATE_TIMER']), ',m),\n  emu.read(', str(symbols['CharSelect_Loaded']), ',m),\n  emu.read(', str(symbols['Msu1_StreamBusy']), ',m),\n  emu.read(', str(symbols['StageEnv_Actors'] + 65), ',m),\n  _s8_lifecycle_rd(', str(symbols['StageBounds_State']), ',2),\n  _s8_lifecycle_rd(', str(symbols['StageBounds_Height']), ',2),\n  _s8_lifecycle_rd(', str(symbols['StageBounds_Velocity']), ',2),\n  _s8_lifecycle_rd(', str(symbols['StageDrop_State']), ',2),\n  emu.read(', str(symbols['G13_P1Out']), ',m),\n  _s8_lifecycle_rd(', str(symbols['Game_Lives']), ',2)}\n for i=1,#row do row[i]=tostring(row[i]) end\n local f=assert(io.open(', str(json.dumps(lifecycle_path)), ",'a'))\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.eventType.endFrame)\n"])
    if trace_sparse:
        if world_symbols:
            if not trace_pc_only:
                script = script + '\n_G._s8_clock_trace_counts={}\n'
                clock_trace_path = Path(os.environ.get('S8_CLOCK_TRACE_PATH', str(journal.with_suffix('.clock-call-trace.txt')))).resolve().as_posix()
                relay_row_trace = tuple(('Relay_' + str(kind) + '_B_' + str(slot) for slot in range(6) for kind in ('SnapshotZeroPolicy', 'SnapshotBound', 'SnapshotUnbound', 'ProjectNext')))
                for label in ('S6Game_PlayRender', 'S6Game_PlayRender__tick', 'S6Game_PlayRender__running', 'S6Game_PlayRender__check_error', 'S6Game_PlayRender__measure', 'S6Game_PlayRender__has_elapsed', 'S6Game_PlayRender__delta_valid', 'S6Game_PlayRender__elapsed_field', 'S6Game_PlayRender__field', 'S6Game_PlayRender__clock_returned', 'S6Game_PlayRender__flush', 'S6Game_PlayRender__post_flush', 'S6Clock_ClockAdvance', 'S6Clock_ClockAdvance__done', 'S6Clock_HostSourceTick', 'S6Host_Tick', 'S6Host_Tick__return', 'S7Resident_Flush', 'S7Resident_Flush__publish', 'S6Host_Tick__export_all', 'S6Host_Tick__export', 'Relay_Flush', 'Relay_Flush_Owned', 'Relay_Wait_Ticks', 'Relay_Request_Snapshot', 'Relay_Wait_Snapshot', 'Relay_Snapshot_Ready', 'Relay_Commit_A', 'Relay_Commit_B', 'Relay_Flush_Return', 'S6Bridge_ProjectPolicy', 'S6Bridge_ProjectPolicy__rounded', 'S6Bridge_Project', 'S6Bridge_ProjectRounded', 'Relay_DrainEvents', 'Relay_DrainEvents__record', 'Relay_DrainEvents__no_overflow', 'Relay_DrainEvents__has_event', 'Relay_DrainEvents__sequence_ok', 'Relay_DrainEvents__sequence_retry', 'Relay_DrainEvents__native_prop', 'Relay_DrainEvents__native_prop_slot_low_ok', 'Relay_DrainEvents__native_prop_slot_high_ok', 'Relay_DrainEvents__native_prop_kind_ok', 'Relay_DrainEvents__native_prop_alive', 'Relay_DrainEvents__native_prop_attacker_slot_ok', 'Relay_DrainEvents__native_prop_attacker_ok', 'Relay_DrainEvents__native_prop_landed', 'Relay_DrainEvents__native_prop_restore', 'Relay_DrainEvents__native_prop_ack', 'Relay_DrainEvents__ack', 'Relay_DrainEvents__fault', 'Relay_Timeout') + relay_row_trace:
                    address = world_symbols.get(label, symbols.get(label))
                    if not address is None:
                        at = lorom_offset(address)
                        script = script + ''.join(['\nemu.addMemoryCallback(function()\n if (_G._s8_clock_trace_counts[', str(json.dumps(label)), "] or 0)>=80 then return end\n local s=emu.getState();local sp=s['cpu.sp'] or 0;local m=emu.memType.snesMemory\n local b=emu.memType.snesSaveRam\n local et=emu.read(0x12432,b)+256*emu.read(0x12433,b)\n local ei=(et%128)*16\n local eh=emu.read(0x12430,b)+256*emu.read(0x12431,b)\n if string.sub(", str(json.dumps(label)), ",1,17)=='Relay_DrainEvents' and\n    et<540 and ", str(json.dumps(label)), "~='Relay_DrainEvents__fault' then return end\n if ", str(json.dumps(label)), "=='Relay_Wait_Ticks' or\n    ", str(json.dumps(label)), "=='Relay_Wait_Snapshot' then\n  local y=s['cpu.y'] or 0\n  if y~=65535 and y%8192~=0 then return end\n end\n _G._s8_clock_trace_counts[", str(json.dumps(label)), ']=(_G._s8_clock_trace_counts[', str(json.dumps(label)), "] or 0)+1\n local stack={}\n for i=1,6 do stack[i]=string.format('%02x',emu.read((sp+i)%65536,m)) end\n local row={", str(json.dumps(label)), ",s['ppu.frameCount'] or -1,s['cpu.k'] or -1,\n  s['cpu.pc'] or -1,s['cpu.d'] or -1,s['cpu.a'] or -1,s['cpu.x'] or -1,\n  s['cpu.y'] or -1,sp,s['cpu.ps'] or -1,table.concat(stack),\n          emu.read(", str(symbols['Nmi_FrameCounter']), ',m)+256*emu.read(', str(symbols['Nmi_FrameCounter'] + 1), ',m),\n          emu.read(', str(symbols.get('StageTimer_FieldCounter', 8280340)), ',m)+256*emu.read(', str(symbols.get('StageTimer_FieldCounter', 8280340) + 1), ',m),\n          emu.read(', str(world_symbols.get('S6Game_LastField', 8263538)), ',m)+256*emu.read(', str(world_symbols.get('S6Game_LastField', 8263538) + 1), ',m),\n          emu.read(', str(symbols['S6Game_TickCommit']), ',m)+256*emu.read(', str(symbols['S6Game_TickCommit'] + 1), ',m),\n  emu.read(0x7e1760,m)+256*emu.read(0x7e1761,m),\n  emu.read(0x7e175e,m)+256*emu.read(0x7e175f,m),\n  emu.read(0x7e1764,m)+256*emu.read(0x7e1765,m),\n  emu.read(0x7e5922,m)+256*emu.read(0x7e5923,m),\n  emu.read(0x7e5924,m)+256*emu.read(0x7e5925,m),\n  emu.read(0x12002,b)+256*emu.read(0x12003,b),\n  emu.read(0x12004,b)+256*emu.read(0x12005,b),\n  emu.read(0x1200a,b),emu.read(0x12434,b),eh,et,\n  emu.read(0x12450+ei,b)+256*emu.read(0x12451+ei,b),\n  emu.read(0x12452+ei,b)+256*emu.read(0x12453+ei,b),\n  emu.read(0x12454+ei,b)+256*emu.read(0x12455+ei,b),\n  emu.read(0x12456+ei,b)+256*emu.read(0x12457+ei,b),\n  emu.read(0x12458+ei,b)+256*emu.read(0x12459+ei,b),\n  emu.read(0x1245a+ei,b)+256*emu.read(0x1245b+ei,b),\n  emu.read(0x1245c+ei,b)+256*emu.read(0x1245d+ei,b),\n  emu.read(0x1245e+ei,b)+256*emu.read(0x1245f+ei,b),\n  emu.read(0x41415a,b),emu.read(0x41417e,b),emu.read(0x4141a2,b),\n  emu.read(0x41214a,b),emu.read(0x4121cf,b),emu.read(0x41224a,b)}\n for i=1,#row do row[i]=tostring(row[i]) end\n local f=assert(io.open(', str(json.dumps(clock_trace_path)), ",'a'))\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.callbackType.exec,", str(at), ',', str(at), ',emu.cpuType.snes,emu.memType.snesPrgRom)\n'])
                clock_probes = (('S6Clock_ClockAdvance', '_s8_clockadvance_hits'), ('S6Clock_HostSourceTick', '_s8_clockhost_hits'), ('S6Host_Tick', '_s8_relay_hits'), ('Relay_Run', '_s8_relay_run_hits'))
                for label, counter in clock_probes:
                    address = world_symbols.get(label)
                    if not address is None:
                        cpu_name = 'sa1' if label.startswith('W') else 'snes'
                        at = lorom_offset(address)
                        script = script + ('\n_G.' + str(counter) + '=0\nemu.addMemoryCallback(function() _G.' + str(counter) + '=_G.' + str(counter) + '+1 end,\n emu.callbackType.exec,' + str(at) + ',' + str(at) + ',emu.cpuType.' + str(cpu_name) + ',emu.memType.snesPrgRom)\n')
                render_trace_path = Path(os.environ.get('S8_RENDER_TRACE_PATH', str(journal.with_suffix('.render-call-trace.txt')))).resolve().as_posix()
                for label in ('S6Game_PlayRender__field', 'S6Game_PlayRender__return', 'Character_RenderPass', 'Character_RenderPass__render_done', 'StageTimerHost_RenderFrame', 'StageTimerHost_RenderFrame__source_done', 'SourceVisual_RenderCurrent', 'SourceVisual_RenderCurrent__fail', 'SourceVisual_LoadResources__pending', 'SourceVisual_ReadSheet__done', 'SourceVisual_ReadPieces__done'):
                    address = world_symbols.get(label, symbols.get(label))
                    if not address is None:
                        at = lorom_offset(address)
                        script = script + ''.join(["\n_G._s8_render_trace_hits=0\nemu.addMemoryCallback(function()\n if _G._s8_render_trace_hits>=160 then return end\n _G._s8_render_trace_hits=_G._s8_render_trace_hits+1\n local s=emu.getState();local sp=s['cpu.sp'] or 0;local m=emu.memType.snesMemory\n local stack={}\n for i=1,8 do stack[i]=string.format('%02x',emu.read((sp+i)%65536,m)) end\n local row={'", str(label), "',s['ppu.frameCount'] or -1,s['cpu.k'] or -1,\n  s['cpu.pc'] or -1,s['cpu.d'] or -1,s['cpu.a'] or -1,s['cpu.x'] or -1,\n  s['cpu.y'] or -1,sp,s['cpu.ps'] or -1,table.concat(stack),\n  emu.read(", str(symbols['Nmi_FrameCounter']), ',m)+256*emu.read(', str(symbols['Nmi_FrameCounter'] + 1), ',m),\n  emu.read(', str(symbols.get('StageTimer_FieldCounter', 8280340)), ',m)+256*emu.read(', str(symbols.get('StageTimer_FieldCounter', 8280340) + 1), ',m),\n  emu.read(', str(symbols['Game_State']), ',m)+256*emu.read(', str(symbols['Game_State'] + 1), ',m),\n  emu.read(', str(symbols['Game_StageIndex']), ',m)+256*emu.read(', str(symbols['Game_StageIndex'] + 1), ',m),\n  emu.read(', str(symbols['S6Game_TickCommit']), ',m)+256*emu.read(', str(symbols['S6Game_TickCommit'] + 1), ',m),\n  emu.read(', str(symbols.get('S6Host_Error', 8263524)), ',m)+256*emu.read(', str(symbols.get('S6Host_Error', 8263524) + 1), ',m),\n  emu.read(', str(symbols['SourceVisual_Error']), ',m),emu.read(0x7e45d8,m)+256*emu.read(0x7e45d9,m)}\n for i=1,#row do row[i]=tostring(row[i]) end\n local f=assert(io.open(', str(json.dumps(render_trace_path)), ",'a'))\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.callbackType.exec,", str(at), ',', str(at), ',emu.cpuType.snes,emu.memType.snesPrgRom)\n'])
                boundary_trace = journal.with_suffix('.sparse-pc-trace.txt').resolve().as_posix() + '.boundary'
                script = script + ('\nlocal function _s8_boundary_write(a,v)\n local stage=_s8_sparse_word(' + str(symbols['Game_StageIndex']) + ',emu.memType.snesMemory)\n if stage<22 or a<0x175c or a>0x1765 then return end\n local s=emu.getState();local m=emu.memType.snesWorkRam;local sm=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local function w(x,mt) return emu.read(x,mt)+256*emu.read(x+1,mt) end\n local f=assert(io.open(' + str(json.dumps(boundary_trace)) + ",'a'))\n f:write(table.concat({'WRAM',s['ppu.frameCount'] or -1,stage,\n  s['cpu.k'] or -1,s['cpu.pc'] or -1,s['cpu.d'] or -1,a,v,\n  w(0x175c,m),w(0x175e,m),w(0x1760,m),w(0x1764,m),\n  w(0x12002,b),w(0x12004,b),w(0x12008,b),w(0x1200a,b),\n  w(0x12430,b),w(0x12432,b),w(0x12434,b),\n  w(0x412430,emu.memType.sa1Memory),w(0x412432,emu.memType.sa1Memory),\n  w(0x412434,emu.memType.sa1Memory),w(0x412430,emu.memType.snesMemory),\n  w(0x412432,emu.memType.snesMemory),w(0x412434,emu.memType.snesMemory)},'|'),'\\n')\n f:close()\nend\nemu.addMemoryCallback(_s8_boundary_write,emu.callbackType.write,\n 0x175c,0x1765,emu.cpuType.snes,emu.memType.snesWorkRam)\n")
                for point in ('ActorBehavior_Bind', 'S6Normal_Bind__combat', 'S6Normal_IsRosterBound__yes', 'S6Normal_IsRosterBound__no', 'S6Normal_Bind__fallback', 'S6Normal_Bind__fenced_done', 'S6Normal_RetireReplacedBound', 'S6Normal_RetireReplacedBound__fault', 'S6Normal_MutationFenceBegin__fault', 'S6Host_BindExisting', 'S6Host_BindExisting__error', 'S6Bridge_Import__height_bad', 'S6Bridge_Import__numeric', 'S6Host_RemoveHandle__error', 'Worker_EventFault', 'S6_EventPush__overflow', 'Relay_DrainEvents__fault', 'Core_Error_Handler__valid_code'):
                    address = world_symbols.get(point, symbols.get(point))
                    if not address is None:
                        cpu_name = 'sa1' if point.startswith(('Worker_', 'S6_Event')) else 'snes'
                        at = lorom_offset(address)
                        script = script + ''.join(['\nlocal _s8_hits_', str(point), '=0\nemu.addMemoryCallback(function()\n if _s8_hits_', str(point), '>=16 then return end\n _s8_hits_', str(point), '=_s8_hits_', str(point), "+1\n local s=emu.getState();local m=emu.memType.snesWorkRam;local sm=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local function w(x,mt) return emu.read(x,mt)+256*emu.read(x+1,mt) end\n local d=s['cpu.d'] or 0;local row=w(0x1752,m)\n if d>=0x0a00 and d<0x0a00+0x85*6 then row=d-0x0a00 end\n local actor=0x7e0a00+row\n local ctx=0x7e0000+d;local env=", str(symbols.get('StageEnv_Actors', 0)), "+row\n local pc=(s['cart.coprocessor.cpu.pc'] and s['cart.coprocessor.cpu.pc'] or s['cpu.pc']) or -1\n local f=assert(io.open(", str(json.dumps(boundary_trace)), ",'a'))\n f:write(table.concat({'PC:", str(point), "',s['ppu.frameCount'] or -1,\n  _s8_sparse_word(", str(symbols['Game_StageIndex']), ",emu.memType.snesMemory),\n  '", str(cpu_name), "',pc,s['cpu.k'] or -1,s['cpu.a'] or -1,s['cpu.x'] or -1,\n  s['cpu.y'] or -1,d,row,w(0x1754,m),\n  emu.read(actor+", str(symbols.get('CHAR_ROSTER_INDEX', 0)), ',sm),\n  emu.read(actor+', str(symbols.get('CHAR_INPUT_DRIVEN', 0)), ',sm),\n  emu.read(actor+', str(symbols.get('CHAR_SELECTED', 0)), ',sm),\n  emu.read(actor+', str(symbols.get('CHAR_HP', 0)), ',sm),\n  w(actor+', str(symbols.get('CHAR_POS_X', 0)), ',sm),w(actor+', str(symbols.get('CHAR_POS_Y', 0)), ',sm),\n  w(actor+', str(symbols.get('CHAR_THROW_ZPOS', 0)), ',sm),\n  w(actor+', str(symbols.get('CHAR_THROW_ZVEL', 0)), ',sm),\n  emu.read(actor+', str(symbols.get('CHAR_GRAB_TARGET', 0)), ',sm),\n  emu.read(actor+', str(symbols.get('CHAR_GRABBED_BY', 0)), ",sm),\n  w(ctx+0xe0,sm),w(ctx+0xfc,sm),w(ctx+0x14,sm),w(ctx+0x16,sm),\n  w(env+64,sm),w(env+65,sm),w(env+68,sm),\n  w(0x175c,m),w(0x175e,m),\n  w(0x1760,m),w(0x1764,m),w(0x12002,b),w(0x12004,b),\n  w(0x12008,b),w(0x1200a,b),w(0x12430,b),w(0x12432,b),w(0x12434,b),\n  w(0x412430,emu.memType.sa1Memory),w(0x412432,emu.memType.sa1Memory),\n  w(0x412434,emu.memType.sa1Memory),w(0x412430,emu.memType.snesMemory),\n  w(0x412432,emu.memType.snesMemory),w(0x412434,emu.memType.snesMemory),\n  emu.read(0x2225,emu.memType.sa1Memory),emu.read(0x2225,emu.memType.snesMemory)},'|'),'\\n')\n f:close()\nend,emu.callbackType.exec,", str(at), ',', str(at), ',emu.cpuType.', str(cpu_name), ',emu.memType.snesPrgRom)\n'])
                spawn_gate_trace = journal.with_suffix('.spawn-gate-trace.txt').resolve().as_posix()
                spawn_gate_points = ('Spawn_Play', 'Spawn_Play__wait_check_done', 'Spawn_Play__have_queue', 'Spawn_Play__group_ok', 'Spawn_Play__active', 'Spawn_Play__compare_trigger', 'Spawn_Play__triggered', 'Spawn_Play__do_hole', 'Spawn_Play__hole_count_ok', 'Spawn_Play__hole_2', 'Spawn_Play__hole_3', 'Spawn_Play__advance', 'Spawn_Play__find_slot', 'Spawn_Play__find_slot_none', 'Spawn_Play__slot1', 'Spawn_Play__slot2', 'Spawn_Play__slot3', 'Spawn_Play__slot45', 'Spawn_Play__advance_index')
                for point in spawn_gate_points:
                    if not point not in symbols:
                        at = lorom_offset(symbols[point])
                        script = script + ''.join(['\nlocal _s8_spawn_gate_hits_', str(point), '=0\nemu.addMemoryCallback(function()\n local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local function w(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n local stage=w(', str(symbols['Game_StageIndex']), ',m)\n local index=emu.read(', str(symbols['Spawn_Index']), ',m)\n if not ((stage==25 and index==0) or (stage==23 and index<=2)) or\n    _s8_spawn_gate_hits_', str(point), '>=24 then return end\n _s8_spawn_gate_hits_', str(point), '=_s8_spawn_gate_hits_', str(point), "+1\n local s=emu.getState();local d=s['cpu.d'] or 0\n local row=d>=0x0a00 and d<0x0d1e and d-0x0a00 or w(0x1752,m)\n local actor=0x7e0a00+row\n local slots={}\n for n=0,5 do local a=0x7e0a00+n*133\n  slots[#slots+1]=string.format('%d:%d/%d/%d/%d/%d',n,\n   emu.read(a+35,m),emu.read(a+15,m),emu.read(a+12,m),\n   w(a+0x43,m),emu.read(a+3,m))\n end\n local q=", str(symbols['SpawnTable_Wram']), '+index*10\n local rec={};for i=0,9 do rec[#rec+1]=emu.read(q+i,m) end\n local f=assert(io.open(', str(json.dumps(spawn_gate_trace)), ",'a'))\n local values={'", str(point), "',s['ppu.frameCount'] or -1,w(", str(symbols['Nmi_FrameCounter']), ",m),\n  s['cpu.k'] or -1,s['cpu.pc'] or -1,d,s['cpu.a'] or -1,s['cpu.x'] or -1,\n  s['cpu.y'] or -1,s['cpu.ps'] or -1,w(", str(symbols['Game_State']), ',m),\n  index,w(', str(symbols['Screen_PosX']), ',m),\n  w(', str(symbols['Spawn_GroupMin']), ',m),w(', str(symbols['Spawn_GroupMax']), ',m),\n  emu.read(', str(symbols['Spawn_Waiting']), ',m),emu.read(', str(symbols['Spawn_ScratchEnemyCount']), ',m),\n  emu.read(', str(symbols['Spawn_B2Kind']), ',m),emu.read(', str(symbols['Spawn_ScratchKind']), ',m),\n  emu.read(', str(symbols['Spawn_ScratchRosterIdx']), ',m),w(', str(symbols['Spawn_ScratchSlotOfs']), ',m),\n  emu.read(actor+', str(symbols['CHAR_ROSTER_INDEX']), ',m),\n  emu.read(actor+', str(symbols['CHAR_INPUT_DRIVEN']), ',m),\n  w(actor+', str(symbols['CHAR_THROW_ZPOS']), ',m),w(actor+', str(symbols['CHAR_THROW_ZVEL']), ',m),\n  w(', str(symbols['OopObjIndex_Lo']), ",m),w(0x7e1764,m),w(0x12002,b),w(0x12004,b),\n  emu.read(0x1200a,b),table.concat(slots,','),table.concat(rec,',')}\n for i=1,#values do values[i]=tostring(values[i]) end\n f:write(table.concat(values,'|'),'\\n');f:close()\nend,emu.callbackType.exec,", str(at), ',', str(at), ',emu.cpuType.snes,emu.memType.snesPrgRom)\n'])
                nmi_gate_trace = journal.with_suffix('.stage2-loop-trace.txt').resolve().as_posix()
                nmi_gate_points = ('Core_Nmi_Start', 'nmi_handler', 'Core_Nmi_Play', 'Core_Nmi_Play__done', 'Core_Nmi_WaitFrame', 'Game_State_Play', 'StageWater_Begin', 'Game_State_Play__playing', 'Core_Oop_Play', 'Core_Oop_Play__done', 'Character_RenderPass', 'Core_Screen_Play', 'Core_Screen__SetTargetPosition', 'Core_Screen__EaseX', 'Core_Screen__EaseY', 'Core_Screen__ClampToScreen', 'Stage_ScrollPlay', 'Vm_Run', 'Core_StreamScroll_ClampCamera', 'Core_StreamScroll_Play', 'Core_StreamScroll_Play__enabled', 'Core_StreamScroll_Play__msu_free', 'Core_StreamScroll_Play__resume', 'Core_StreamScrollFp_Play', 'StageFp_BG2PlayDispatch', 'Spawn_Play', 'Spawn_Play__have_queue', 'StageWater_End', 'S6Normal_RenderHook', 'S6Normal_BindLiveActors', 'S6Normal_BindLiveActors__slot', 'S6Normal_BindLiveActors__bind', 'S6Normal_Bind', 'S6Normal_MutationFenceBegin', 'S6Normal_MutationFenceBegin__wait', 'S6Host_BindExisting', 'S6Host_BindExisting__model_found', 'S6Host_BindExisting__bridge_ok', 'S6_SetRole', 'S6_EnterFrame', 'S6_CheckPolicy', 'S6_SetRole__policy', 'S6_SetRole__find', 'S6_SetRole__search', 'S6_SetRole__found', 'S6_SetRole__load', 'S6_EnterFrame__valid', 'S5_LoadFrame', 'S5_LoadFrame__copy', 'S6Normal_MutationFenceEnd', 'S6Game_PlayRender', 'S6Game_PlayRender__load', 'S6Game_PlayRender__tick', 'S6Game_PlayRender__running', 'S6Game_PlayRender__measure', 'S6Game_PlayRender__has_elapsed', 'S6Game_PlayRender__field', 'S6Game_PlayRender__clock', 'S6Game_PlayRender__return', 'S6Normal_BeginResolve', 'S6Normal_Init')
                for point in nmi_gate_points:
                    address = symbols.get(point, world_symbols.get(point) if world_symbols else None)
                    if not address is None:
                        at = lorom_offset(address)
                        script = script + ''.join(['\nlocal _s8_stage2_loop_hits_', str(point), '=0\nemu.addMemoryCallback(function()\n local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local function w(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n if w(', str(symbols['Game_StageIndex']), ',m)~=25 or\n    _s8_stage2_loop_hits_', str(point), '>=12 then return end\n _s8_stage2_loop_hits_', str(point), '=_s8_stage2_loop_hits_', str(point), '+1\n local s=emu.getState();local f=assert(io.open(', str(json.dumps(nmi_gate_trace)), ",'a'))\n local values={'", str(point), "',s['ppu.frameCount'] or -1,s['cpu.k'] or -1,\n  s['cpu.pc'] or -1,s['cpu.d'] or -1,s['cpu.a'] or -1,s['cpu.x'] or -1,\n  s['cpu.y'] or -1,s['cpu.sp'] or -1,w(", str(symbols['Game_State']), ',m),\n  w(', str(symbols['Game_StageIndex']), ',m),w(', str(symbols['Nmi_FrameCounter']), ',m),\n  emu.read(', str(symbols['Nmi_InterruptFlags']), ',m),emu.read(', str(symbols['Nmi_FrameBusy']), ',m),\n  emu.read(', str(symbols['Nmi_Busy']), ',m),emu.read(', str(symbols['StageWater_Enabled']), ',m),\n  emu.read(', str(symbols['StageWater_Held']), ',m),emu.read(', str(symbols['StageWater_Dirty']), ',m),\n  emu.read(', str(symbols['StageWater_Pending']), ',m),emu.read(', str(symbols['Spawn_Index']), ',m),\n  w(0x7e1760,m),w(0x7e1764,m),w(0x7e175c,m),w(0x7e1752,m),\n  w(0x7e1754,m),w(0x7e1756,m),w(0x7e1770,m),\n  w(', str(symbols['S6Game_LastField']), ',m),w(', str(symbols['S6Game_TickCommit']), ",m),\n  w(0x12002,b),w(0x12004,b),\n  emu.read(0x1200a,b)}\n for i=1,#values do values[i]=tostring(values[i]) end\n f:write(table.concat(values,'|'),'\\n');f:close()\nend,emu.callbackType.exec,", str(at), ',', str(at), ',emu.cpuType.snes,emu.memType.snesPrgRom)\n'])
                early_flow_trace = journal.with_suffix('.early-flow-trace.txt').resolve().as_posix()
                early_flow_points = ('Core_Nmi_Start', 'Core_Nmi_Play', 'Game_State_Play__playing', 'Core_Nmi_Play__frame_skipped', 'Core_Nmi_Play__do_commit', 'Core_Nmi_Play__done', 'Core_Dma_ProcessQueue', 'Core_Dma_ProcessQueue__loop', 'Core_Dma_ProcessQueue__bad_type', 'Core_Dma_ProcessQueue__next', 'Core_Dma_ProcessQueue__done', 'Core_Dma_TransferVram', 'Core_Dma_TransferOam', 'Core_Dma_TransferCgram', 'Core_Oop_Play', 'Core_Oop_Play__loop', 'Core_Oop_Play__skip', 'Core_Oop_Play__done', 'Core_Oop_CollectGarbage', 'CharacterEntity_Play', 'CharacterEntity_Play__context_ready', 'CharacterEntity_Play__no_context_exit', 'S6Game_Entity', 'S6Game_Entity__normal_gate', 'S6Game_Entity__normal', 'S6Game_Entity__player_lifecycle', 'S6Game_Entity__owned_return', 'Spawn_Play', 'Spawn_Play__have_queue', 'S6Normal_RenderHook', 'S6Game_PlayRender__field', 'S6Clock_ClockAdvance', 'S6Clock_HostSourceTick__running', 'S6Host_Tick', 'Relay_Run', 'Relay_Queued', 'Relay_Flush', 'Relay_DrainEvents', 'Relay_DrainEvents__fault', 'Relay_DrainEvents__record', 'Relay_DrainEvents__visual', 'Relay_DrainEvents__hit', 'Relay_DrainEvents__unlink', 'Relay_DrainEvents__find', 'Relay_DrainEvents__found', 'Relay_DrainEvents__ack', 'S6Normal_Bind', 'S6Normal_Bind__combat', 'S6Normal_Bind__bind', 'S6Normal_Bind__worker_ready', 'S6Normal_Bind__fallback', 'S6Normal_Bind__handled', 'S6Normal_RetireReplacedBound', 'S6Normal_RetireReplacedBound__context_ready', 'S6Normal_RetireReplacedBound__unlinked', 'S6Normal_RetireReplacedBound__fault', 'S6Normal_SyncBoundContext', 'S6Normal_SyncBoundContext__metadata', 'S6Bridge_Resolve', 'S6Bridge_Resolve__bad', 'S6Bridge_Export', 'S6Bridge_Export__numeric', 'S6Bridge_Export__width', 'S6Host_RemoveHandle', 'S6Host_RemoveHandle__resident', 'S6Host_RemoveHandle__error', 'S6_KillUnlinked', 'S6_KillUnlinked__linked', 'S6_KillUnlinked__bad', 'StageEnv_ResetActors', 'StageEnv_ResetActors__worker_call', 'S6Normal_ResetStageWorld', 'S6Normal_ResetStageWorld__campaign', 'S6Normal_ResetStageWorld__mode', 'S6Normal_ResetStageWorld__owned', 'S6Normal_ResetStageWorld__slot', 'S6Normal_ResetStageWorld__context', 'S6Normal_ResetStageWorld__metadata', 'S6Normal_ResetStageWorld__return', 'Worker_Tick', 'Worker_Execute', 'Worker_Complete', 'Worker_EventFault', 'Worker_RingFault', 'Worker_WorldFault', 'Worker_Fault', 'Worker_FaultWait', 'Core_Error_Handler', 'Core_Error_Handler__valid_code', 'Character_RenderPass__dispatch', 'StageTimerHost_RenderFrame', 'StageTimerHost_RenderFrame__normal_campaign', 'StageTimerHost_RenderFrame__normal_invalid', 'StageTimerHost_RenderFrame__compat', 'StageTimerHost_RenderFrame__source_done', 'StageTimerHost_IsPendingOffset', 'StageTimerHost_IsPendingOffset__no', 'StageTimerHost_IsPendingOffset__found', 'StageTimerHost_Enabled', 'StageTimerHost_Enabled__no', 'Character_RenderFrame', 'SourceVisual_RenderCurrent', 'SourceVisual_FindEntry', 'SourceVisual_LoadResources', 'SourceVisual_Seek', 'SourceVisual_Seek__busy')
                script = script + ('\nlocal _s8_early_hits={}\nlocal function _s8_early_mark(point,cpu_name,hit_limit)\n local hits=_s8_early_hits[point] or 0\n if hits>=hit_limit then return end\n local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local stage=emu.read(' + str(symbols['Game_StageIndex']) + ',m)+256*emu.read(' + str(symbols['Game_StageIndex'] + 1) + ",m)\n local reset_trace=string.find(point,'^S6Normal_ResetStageWorld')~=nil or\n                   string.find(point,'^StageEnv_ResetActors')~=nil\n local critical_trace=string.find(point,'^Relay_DrainEvents')~=nil or\n                      point=='S6Host_RemoveHandle__error'\n if stage~=22 and stage~=23 and not reset_trace and not critical_trace then return end\n local s=emu.getState()\n local dp=cpu_name=='sa1' and (s['cart.coprocessor.cpu.d'] or -1) or (s['cpu.d'] or -1)\n if string.sub(point,1,15)=='StageTimerHost_' and dp~=0x0A85 then return end\n _s8_early_hits[point]=hits+1\n local function w(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n local pc=cpu_name=='sa1' and (s['cart.coprocessor.cpu.pc'] or -1) or (s['cpu.pc'] or -1)\n local k=cpu_name=='sa1' and (s['cart.coprocessor.cpu.k'] or -1) or (s['cpu.k'] or -1)\n local a=cpu_name=='sa1' and (s['cart.coprocessor.cpu.a'] or -1) or (s['cpu.a'] or -1)\n local x=cpu_name=='sa1' and (s['cart.coprocessor.cpu.x'] or -1) or (s['cpu.x'] or -1)\n local y=cpu_name=='sa1' and (s['cart.coprocessor.cpu.y'] or -1) or (s['cpu.y'] or -1)\n local f=assert(io.open(" + str(json.dumps(early_flow_trace)) + ",'a'))\n f:write(table.concat({point,s['ppu.frameCount'] or -1,cpu_name,\n  pc,k,dp,a,x,y,s['cpu.ps'] or -1,s['cpu.sp'] or -1,stage,\n  w(0x7e074a,m),w(0x7e074c,m),\n  emu.read(0x7e078a+x,m),w(0x7e081a+x,m),w(0x7e08aa+x,m),\n  emu.read(" + str(symbols['Spawn_Index']) + ',m),w(' + str(symbols['S6Game_TickCommit']) + ',m),\n  w(0x12002,b),w(0x12004,b),w(0x12008,b),emu.read(0x1200a,b),\n  w(0x12430,b),w(0x12432,b),w(0x12434,b),w(0x7e175c,m),\n  w(0x7e175e,m),w(0x7e1760,m),w(0x7e1764,m),\n  w(0x412002,emu.memType.sa1Memory),w(0x412004,emu.memType.sa1Memory),\n  w(0x412008,emu.memType.sa1Memory),w(0x41200a,emu.memType.sa1Memory),\n  w(0x412430,emu.memType.sa1Memory),w(0x412432,emu.memType.sa1Memory),\n  w(0x412434,emu.memType.sa1Memory),w(0x412c50,emu.memType.sa1Memory),\n  w(0x412c52,emu.memType.sa1Memory),w(0x412c54,emu.memType.sa1Memory),\n  w(0x412c56,emu.memType.sa1Memory),w(0x412c58,emu.memType.sa1Memory),\n  w(0x412c5a,emu.memType.sa1Memory),w(0x412c5c,emu.memType.sa1Memory),\n  w(0x412c5e,emu.memType.sa1Memory),w(0x412c60,emu.memType.sa1Memory),\n  w(0x412c62,emu.memType.sa1Memory),w(0x412c64,emu.memType.sa1Memory),\n  w(0x412c66,emu.memType.sa1Memory),w(0x412c68,emu.memType.sa1Memory),\n  w(0x412c6a,emu.memType.sa1Memory),emu.read(0x2000,m),emu.read(0x2001,m),\n  emu.read(0x2002,m),emu.read(0x2003,m),emu.read(0x2004,m),\n  emu.read(0x2005,m),emu.read(0x2006,m),emu.read(0x2007,m),\n  emu.read(' + str(symbols['Msu1_StreamBusy']) + ',m),\n  emu.read(0x7e0000+dp+' + str(symbols['CHAR_ROSTER_INDEX']) + ',m),\n  emu.read(0x7e0000+dp+' + str(symbols['CHAR_SELECTED']) + ',m),\n  emu.read(0x7e0000+dp+' + str(symbols['CHAR_HP']) + ',m),\n  emu.read(' + str(symbols['SourceVisual_Error']) + ',m),\n  emu.read(' + str(symbols['SourceVisual_DebugLastError']) + ',m),\n  emu.read(' + str(symbols['SourceVisual_HostLastPolicy']) + ',m),\n  w(0x12450+(w(0x12432,b)%128)*16,b),\n  w(0x12452+(w(0x12432,b)%128)*16,b),\n  w(0x12458+(w(0x12432,b)%128)*16,b),\n  w(0x1245A+(w(0x12432,b)%128)*16,b),\n  w(0x7e1752,m),w(0x7e1754,m),\n  w(0x41243c,b),\n  w(0x12458+(w(0x12432,b)%128)*16,b),\n  w(' + str(world_symbols['S6Bridge_Context']) + '+x,m),\n  w(0x7e0000+dp+0x7a,m),w(0x7e0000+dp+0xfc,m),\n  w(0x7e0000+dp+0x14,m),w(0x7e0000+dp+0x16,m),\n  w(0x7e0000+dp+0x18,m),w(0x7e0000+dp+0x1a,m),\n  w(0x7e0000+dp+0xf0,m),w(0x7e0000+dp+0xf6,m),\n  w(' + str(symbols['StageEnv_BaseInteger']) + "+w(0x7e0000+dp+0x7a,m),m)},'|'),'\\n')\n f:close()\nend\n")
                for point in early_flow_points:
                    address = symbols.get(point, world_symbols.get(point) if world_symbols else None)
                    if not address is None:
                        cpu_name = 'sa1' if point.startswith(('Worker_', 'W6_', 'S6_Event', 'Relay_')) else 'snes'
                        hit_limit = ((1 if point in ('Relay_DrainEvents__fault', 'Core_Error_Handler__valid_code') else 4 if point.startswith('StageTimerHost_') else 512 if point.startswith(('Core_Oop_Play', 'CharacterEntity_Play', 'S6Game_Entity')) else 128) if not point.startswith('SourceVisual_') else 1) if not 'Fault' in point else 1
                        at = lorom_offset(address)
                        script = script + ("\nemu.addMemoryCallback(function() _s8_early_mark('" + str(point) + "','" + str(cpu_name) + "'," + str(hit_limit) + ') end,emu.callbackType.exec,' + str(at) + ',' + str(at) + ',emu.cpuType.' + str(cpu_name) + ',emu.memType.snesPrgRom)\n')
                overflow_write_trace = journal.with_suffix('.event-overflow-write-trace.txt').resolve().as_posix()
                script = script + ('\nlocal _s8_overflow_write_hits=0\nlocal function _s8_overflow_write(a,v,cpu)\n if _s8_overflow_write_hits>=64 then return end\n local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam;local sa=emu.memType.sa1Memory\n local stage=emu.read(' + str(symbols['Game_StageIndex']) + ',m)+256*emu.read(' + str(symbols['Game_StageIndex'] + 1) + ',m)\n if stage~=22 then return end\n _s8_overflow_write_hits=_s8_overflow_write_hits+1\n local s=emu.getState();local f=assert(io.open(' + str(json.dumps(overflow_write_trace)) + ",'a'))\n local function w(x,mt) return emu.read(x,mt)+256*emu.read(x+1,mt) end\n local k=string.sub(cpu,1,3)=='sa1' and (s['cart.coprocessor.cpu.k'] or -1) or (s['cpu.k'] or -1)\n local pc=string.sub(cpu,1,3)=='sa1' and (s['cart.coprocessor.cpu.pc'] or -1) or (s['cpu.pc'] or -1)\n f:write(table.concat({s['ppu.frameCount'] or -1,cpu,k,pc,a,v,\n  w(0x12008,b),emu.read(0x1200a,b),w(0x412008,sa),\n  w(0x41200a,sa),w(0x412008,m),w(0x41200a,m),\n  w(0x12430,b),w(0x12432,b),w(0x12434,b),\n  w(0x412430,sa),w(0x412432,sa),w(0x412434,sa),\n  w(0x412430,m),w(0x412432,m),w(0x412434,m)},'|'),'\\n')\n f:close()\nend\nemu.addMemoryCallback(function(a,v) _s8_overflow_write(a,v,'snes') end,\n emu.callbackType.write,0x12434,0x12435,emu.cpuType.snes,emu.memType.snesSaveRam)\nemu.addMemoryCallback(function(a,v) _s8_overflow_write(a,v,'sa1') end,\n emu.callbackType.write,0x12434,0x12435,emu.cpuType.sa1,emu.memType.snesSaveRam)\nemu.addMemoryCallback(function(a,v) _s8_overflow_write(a,v,'snes-fault') end,\n emu.callbackType.write,0x12008,0x1200a,emu.cpuType.snes,emu.memType.snesSaveRam)\nemu.addMemoryCallback(function(a,v) _s8_overflow_write(a,v,'sa1-fault') end,\n emu.callbackType.write,0x12008,0x1200a,emu.cpuType.sa1,emu.memType.snesSaveRam)\n")
                stp_trace = journal.with_suffix('.stp-entry-trace.txt').resolve().as_posix()
                script = script + ("\nemu.addMemoryCallback(function()\n local s=emu.getState();local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local sp=(s['cpu.sp'] or 0)%65536;local stack={}\n for i=1,16 do stack[i]=string.format('%02x',emu.read((sp+i)%65536,m)) end\n local function w(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n local f=assert(io.open(" + str(json.dumps(stp_trace)) + ",'a'))\n f:write(table.concat({'STP_ENTRY',s['ppu.frameCount'] or -1,\n  s['cpu.k'] or -1,s['cpu.pc'] or -1,s['cpu.d'] or -1,\n  s['cpu.a'] or -1,s['cpu.x'] or -1,s['cpu.y'] or -1,\n  s['cpu.ps'] or -1,sp,table.concat(stack,','),\n  w(" + str(symbols['Game_StageIndex']) + ',m),emu.read(' + str(symbols['Spawn_Index']) + ',m),\n  w(' + str(symbols['Nmi_FrameCounter']) + ',m),w(' + str(symbols['S6Game_TickCommit']) + ",m),\n  w(0x12002,b),w(0x12004,b),w(0x12008,b),emu.read(0x1200a,b),\n  w(0x12430,b),w(0x12432,b),w(0x12434,b),w(0x7e175c,m),\n  w(0x7e175e,m),w(0x7e1760,m),w(0x7e1764,m)},'|'),'\\n')\n f:close()\nend,emu.callbackType.exec,0x12B26,0x12B26,emu.cpuType.snes,emu.memType.snesPrgRom)\n")
                nmi_enable_trace = journal.with_suffix('.stage2-nmi-enable-trace.txt').resolve().as_posix()
                script = script + ('\nemu.addMemoryCallback(function(a,v)\n local m=emu.memType.snesMemory;local s=emu.getState()\n local stage=emu.read(' + str(symbols['Game_StageIndex']) + ',m)+256*emu.read(' + str(symbols['Game_StageIndex'] + 1) + ',m)\n if stage~=25 then return end\n local f=assert(io.open(' + str(json.dumps(nmi_enable_trace)) + ",'a'))\n f:write(table.concat({s['ppu.frameCount'] or -1,s['cpu.k'] or -1,\n  s['cpu.pc'] or -1,s['cpu.ps'] or -1,s['cpu.sp'] or -1,a,v,\n  emu.read(0x4200,m),emu.read(" + str(symbols['Nmi_InterruptFlags']) + ',m),\n  emu.read(' + str(symbols['Nmi_FrameCounter']) + ',m),\n  emu.read(' + str(symbols['Game_State']) + ',m),emu.read(' + str(symbols['Spawn_Index']) + ",m),\n  emu.read(0x7e1760,m),emu.read(0x7e1764,m),\n  emu.read(0x7e044e,m),emu.read(0x7e044f,m)},'|'),'\\n')\n f:close()\nend,emu.callbackType.write,0x4200,0x4200,emu.cpuType.snes,emu.memType.snesMemory)\nlocal _s8_stage2_endframe=0\nemu.addEventCallback(function()\n local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local stage=emu.read(" + str(symbols['Game_StageIndex']) + ',m)+256*emu.read(' + str(symbols['Game_StageIndex'] + 1) + ',m)\n if stage~=25 then return end\n _s8_stage2_endframe=_s8_stage2_endframe+1\n if _s8_stage2_endframe%10~=0 then return end\n local s=emu.getState();local f=assert(io.open(' + str(json.dumps(nmi_enable_trace)) + ",'a'))\n local row={'FIELD',s['ppu.frameCount'] or -1,s['cpu.k'] or -1,s['cpu.pc'] or -1,\n  s['cpu.ps'] or -1,s['cpu.sp'] or -1,emu.read(0x4200,m),\n  emu.read(" + str(symbols['Nmi_InterruptFlags']) + ',m),\n  emu.read(' + str(symbols['Nmi_FrameCounter']) + ',m),emu.read(' + str(symbols['Game_State']) + ',m),\n  emu.read(' + str(symbols['Spawn_Index']) + ",m),emu.read(0x7e1760,m),\n  emu.read(0x7e1764,m),emu.read(0x7e044e,m),emu.read(0x7e044f,m),\n  emu.read(0x12002,b)+256*emu.read(0x12003,b),\n  emu.read(0x12004,b)+256*emu.read(0x12005,b),emu.read(0x1200a,b)}\n for i=1,#row do row[i]=tostring(row[i]) end\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.eventType.endFrame)\n")
                host_clock_write_trace = journal.with_suffix('.stage2-host-clock-writes.txt').resolve().as_posix()
                script = script + ('\nlocal function _s8_host_clock_write(name,a,v)\n local m=emu.memType.snesMemory;local s=emu.getState()\n local function w(x) return emu.read(x,m)+256*emu.read(x+1,m) end\n if w(' + str(symbols['Game_StageIndex']) + ')~=25 then return end\n local f=assert(io.open(' + str(json.dumps(host_clock_write_trace)) + ",'a'))\n f:write(table.concat({name,s['ppu.frameCount'] or -1,s['cpu.k'] or -1,\n  s['cpu.pc'] or -1,s['cpu.d'] or -1,s['cpu.a'] or -1,a,v,\n  w(0x7e1764),w(" + str(symbols['S6Game_LastField']) + '),\n  w(' + str(symbols['Nmi_FrameCounter']) + ")},'|'),'\\n');f:close()\nend\nemu.addMemoryCallback(function(a,v) _s8_host_clock_write('error',a,v) end,\n emu.callbackType.write,0x7e1764,0x7e1765,emu.cpuType.snes,emu.memType.snesMemory)\nemu.addMemoryCallback(function(a,v) _s8_host_clock_write('lastfield',a,v) end,\n emu.callbackType.write," + str(symbols['S6Game_LastField']) + ',' + str(symbols['S6Game_LastField'] + 1) + ',\n emu.cpuType.snes,emu.memType.snesMemory)\n')
                actor_path_trace = journal.with_suffix('.stage2-actor-path-trace.txt').resolve().as_posix()
                actor_path_points = ('Core_Oop_Play', 'Core_Oop_Play__done', 'CharacterEntity_Play', 'CharacterEntity_Play__context_ready', 'CharacterEntity_Play__no_context_exit', 'Character_PlayFrame', 'Spawn_CheckHole', 'Spawn_CheckHole__no', 'StageBoundsHost_Clamp', 'StageBoundsHost_Physics', 'StageTimerHost_FrameService', 'Anim_Play', 'Msu1_LoadFrame', 'Core_Nmi_Stop', 'Core_Nmi_Start', 'Spawn_Play')
                for point in actor_path_points:
                    if not point not in symbols:
                        at = lorom_offset(symbols[point])
                        script = script + ''.join(['\nlocal _s8_stage2_actor_hits_', str(point), '=0\nemu.addMemoryCallback(function()\n local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local function w(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n if w(', str(symbols['Game_StageIndex']), ',m)~=25 or\n    _s8_stage2_actor_hits_', str(point), '>=16 then return end\n _s8_stage2_actor_hits_', str(point), '=_s8_stage2_actor_hits_', str(point), "+1\n local s=emu.getState();local d=s['cpu.d'] or 0;local a=0x7e0000+d\n local actor=d>=0x0a00 and d<0x0d1e\n local f=assert(io.open(", str(json.dumps(actor_path_trace)), ",'a'))\n local values={'", str(point), "',s['ppu.frameCount'] or -1,s['cpu.k'] or -1,\n  s['cpu.pc'] or -1,d,s['cpu.a'] or -1,s['cpu.x'] or -1,s['cpu.y'] or -1,\n  s['cpu.sp'] or -1,w(", str(symbols['Game_State']), ',m),w(', str(symbols['Nmi_FrameCounter']), ',m),\n  emu.read(', str(symbols['Nmi_InterruptFlags']), ',m),emu.read(', str(symbols['Nmi_FrameBusy']), ',m),\n  emu.read(', str(symbols['Nmi_Busy']), ',m),w(', str(symbols['Spawn_Index']), ',m),\n  emu.read(', str(symbols['Spawn_HoleCount']), ',m),w(', str(symbols['Spawn_HolePos1']), ',m),\n  actor and emu.read(a+', str(symbols['CHAR_ROSTER_INDEX']), ',m) or -1,\n  actor and emu.read(a+', str(symbols['CHAR_INPUT_DRIVEN']), ',m) or -1,\n  actor and emu.read(a+', str(symbols['CHAR_HP']), ',m) or -1,\n  actor and emu.read(a+', str(symbols['CHAR_SELECTED']), ',m) or -1,\n  actor and w(a+', str(symbols['CHAR_THROW_ZPOS']), ',m) or -1,\n  actor and w(a+', str(symbols['CHAR_THROW_ZVEL']), ',m) or -1,\n  actor and emu.read(a+', str(symbols['CHAR_FALL_STATE_TIMER']), ",m) or -1,\n  emu.read(0x12003,b),w(0x12002,b),w(0x12004,b),emu.read(0x1200a,b)}\n for i=1,#values do values[i]=tostring(values[i]) end\n f:write(table.concat(values,'|'),'\\n');f:close()\nend,emu.callbackType.exec,", str(at), ',', str(at), ',emu.cpuType.snes,emu.memType.snesPrgRom)\n'])
                lifecycle_trace = journal.with_suffix('.sparse-pc-trace.txt').resolve().as_posix() + '.lifecycle'
                for point in ('Stage_Load_Long', 'Stage_Load', 'Stage_Load__fp_done', 'Stage_Load__keep_y', 'Core_Nmi_Start', 'G13_ClearOldStageActors', 'G13_ReapplyP1Out', 'G13_EnsureP2AfterStage', 'S6Normal_RenderHook'):
                    address = symbols.get(point, world_symbols.get(point))
                    if not address is None:
                        at = lorom_offset(address)
                        cpu_name = 'sa1' if point.startswith('Worker_') else 'snes'
                        script = script + ('\nemu.addMemoryCallback(function()\n local s=emu.getState();local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local function w(x,mt) return emu.read(x,mt)+256*emu.read(x+1,mt) end\n local f=assert(io.open(' + str(json.dumps(lifecycle_trace)) + ",'a'))\n f:write(table.concat({'" + str(point) + "',s['ppu.frameCount'] or -1,\n  s['cpu.k'] or -1,s['cpu.pc'] or -1,s['cpu.d'] or -1,s['cpu.a'] or -1,\n  s['cpu.x'] or -1,s['cpu.y'] or -1,s['cpu.sp'] or -1,\n  w(" + str(symbols['Game_State']) + ',m),w(' + str(symbols['Game_StageIndex']) + ",m),\n  w(0x7e175c,m),w(0x7e175e,m),w(0x7e1760,m),w(0x7e1764,m),\n  w(0x12002,b),w(0x12004,b),w(0x12008,b),w(0x1200a,b),\n  w(0x12430,b),w(0x12432,b),w(0x12434,b)},'|'),'\\n')\n f:close()\nend,emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
    if trace_runtime:
        trace = journal.with_suffix('.frame-trace.txt').resolve().as_posix()
        for label, counter in (('Game_State_Play__playing', '_s8_play_calls'), ('StageTimerHost_ServiceDeaths', '_s8_death_calls'), ('StageTimerHost_CheckAllOut', '_s8_allout_calls')):
            address = lorom_offset(symbols[label])
            script = script + ('\n' + str(counter) + '=' + str(counter) + ' or 0\nemu.addMemoryCallback(function() ' + str(counter) + '=' + str(counter) + '+1 end,\n emu.callbackType.exec,' + str(address) + ',' + str(address) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
        script = script + ''.join(["\nlocal _s8_frames=0\nlocal function _s8_rd(a,n,mt)\n local v=0;for i=0,n-1 do v=v+emu.read(a+i,mt)*256^i end;return v\nend\nlocal function _s8_hex(a,n,mt)\n local r={};for i=0,n-1 do r[#r+1]=string.format('%02x',emu.read(a+i,mt)) end\n return table.concat(r)\nend\nlocal _s8_fault_dumped=false\nlocal _s8_last_nmi=-1\nlocal _s8_same_nmi=0\nemu.addEventCallback(function()\n _s8_frames=_s8_frames+1\n local s=emu.getState()\n local nmi=_s8_rd(", str(symbols['Nmi_FrameCounter']), ",2,emu.memType.snesMemory)\n local worker_error=_s8_rd(0x1200A,1,emu.memType.snesSaveRam)\n if nmi==_s8_last_nmi then _s8_same_nmi=_s8_same_nmi+1 else _s8_same_nmi=0 end\n _s8_last_nmi=nmi\n local worker_target=_s8_rd(0x12002,2,emu.memType.snesSaveRam)\n if _s8_frames>400 and nmi>250 and not _s8_fault_dumped and\n    (_s8_same_nmi>=30 or (worker_error~=0 and worker_target~=0)) then\n  _s8_fault_dumped=true\n  local relay={}\n  for i=0,15 do relay[#relay+1]=string.format('%02x',_s8_rd(0x12000+i,1,emu.memType.snesSaveRam)) end\n  local events={}\n  for i=0,23 do events[#events+1]=string.format('%02x',_s8_rd(0x12430+i,1,emu.memType.snesSaveRam)) end\n  local event_rows={}\n  local event_head=_s8_rd(0x12430,2,emu.memType.snesSaveRam)\n  local event_tail=_s8_rd(0x12432,2,emu.memType.snesSaveRam)\n  local first=math.max(event_tail,event_head-8)\n  for seq=first,event_head-1 do\n   local base=0x12450+(seq%128)*16\n   local row={}\n   for i=0,15 do row[#row+1]=string.format('%02x',_s8_rd(base+i,1,emu.memType.snesSaveRam)) end\n   event_rows[#event_rows+1]=table.concat(row)\n  end\n  local world={}\n  for i=0,63,2 do world[#world+1]=string.format('%04x',_s8_rd(0x11700+i,2,emu.memType.snesSaveRam)) end\n  local bctx={}\n  local wctx={}\n  local actors={}\n  for slot=0,5 do\n   local a=0x11900+slot*256\n   bctx[#bctx+1]=string.format('%d:%04x,%04x,%04x,%04x,%04x',slot,\n    _s8_rd(a+0xE0,2,emu.memType.snesSaveRam),\n    _s8_rd(a+0xF2,2,emu.memType.snesSaveRam),\n    _s8_rd(a+0xF6,2,emu.memType.snesSaveRam),\n    _s8_rd(a+0xFC,2,emu.memType.snesSaveRam),\n    _s8_rd(a+0x14,2,emu.memType.snesSaveRam))\n   local b=0x7E1900+slot*256\n   wctx[#wctx+1]=string.format('%d:%04x,%04x,%04x,%04x,%04x',slot,\n    _s8_rd(b+0xE0,2,emu.memType.snesMemory),\n    _s8_rd(b+0xF2,2,emu.memType.snesMemory),\n    _s8_rd(b+0xF6,2,emu.memType.snesMemory),\n    _s8_rd(b+0xFC,2,emu.memType.snesMemory),\n    _s8_rd(b+0x14,2,emu.memType.snesMemory))\n   local c=0x7E0A00+slot*", str(symbols['CHAR_ZP_LEN']), "\n   actors[#actors+1]=string.format('%d:%02x,%02x,%02x,%04x,%04x,%04x',slot,\n    _s8_rd(c+", str(symbols['CHAR_HP']), ',1,emu.memType.snesMemory),\n    _s8_rd(c+', str(symbols['CHAR_INPUT_DRIVEN']), ',1,emu.memType.snesMemory),\n    _s8_rd(c+', str(symbols['CHAR_SELECTED']), ',1,emu.memType.snesMemory),\n    _s8_rd(c+', str(symbols['CHAR_POS_X']), ',2,emu.memType.snesMemory),\n    _s8_rd(c+', str(symbols['CHAR_POS_Y']), ',2,emu.memType.snesMemory),\n    _s8_rd(c+', str(symbols['CHAR_ROSTER_INDEX']), ",1,emu.memType.snesMemory))\n  end\n  local p=_s8_rd(0x11730,2,emu.memType.snesSaveRam)\n  local bank=_s8_rd(0x11732,2,emu.memType.snesSaveRam)%256\n  local slots={}\n  for i=0,5 do slots[#slots+1]=string.format('%04x',_s8_rd(bank*65536+p+i*2,2,emu.memType.snesPrgRom)) end\n  local f=assert(io.open(", str(json.dumps(trace)), "..'.fault','a'))\n  local sp=s['cpu.sp'] or 0\n  local stack={}\n  for i=1,16 do stack[i]=string.format('%02x',emu.read((sp+i)%65536,emu.memType.snesMemory)) end\n  f:write(table.concat({_s8_frames,nmi,_s8_same_nmi,worker_target,\n   _s8_rd(0x12004,2,emu.memType.snesSaveRam),worker_error,\n   _s8_rd(0x7E1760,2,emu.memType.snesMemory),_s8_rd(0x7E175E,2,emu.memType.snesMemory),\n   _s8_rd(0x7E173C,2,emu.memType.snesMemory),_s8_rd(", str(symbols['Game_StageIndex']), ',2,emu.memType.snesMemory),\n   _s8_rd(', str(symbols['Spawn_Index']), ',1,emu.memType.snesMemory),\n   _s8_rd(', str(symbols['Game_State']), ",2,emu.memType.snesMemory),\n   s['cpu.k'] or -1,s['cpu.pc'] or -1,s['cpu.d'] or -1,s['cpu.a'] or -1,s['cpu.ps'] or -1,sp,\n   s['cart.coprocessor.cpu.k'] or -1,\n   s['cart.coprocessor.cpu.pc'] or -1,\n   s['cart.coprocessor.cpu.d'] or -1,\n   s['cart.coprocessor.cpu.a'] or -1,\n   s['cart.coprocessor.cpu.x'] or -1,\n   s['cart.coprocessor.cpu.y'] or -1,\n   s['cart.coprocessor.cpu.sp'] or -1,\n   s['cart.coprocessor.cpu.ps'] or -1,\n   (s['cart.coprocessor.cpu.d'] and emu.read((s['cart.coprocessor.cpu.d']+0xC2)%65536,emu.memType.sa1Memory)) or -1,\n   (s['cart.coprocessor.cpu.d'] and emu.read((s['cart.coprocessor.cpu.d']+0xFC)%65536,emu.memType.sa1Memory)) or -1,\n   table.concat(stack,','),table.concat(relay),table.concat(events),table.concat(event_rows,','),\n   table.concat(world),string.format('%04x:%02x',p,bank),table.concat(slots,','),\n   table.concat(bctx,','),table.concat(wctx,','),table.concat(actors,',')},'|'),'\\n')\n  f:close()\n end\n if _s8_frames%30~=0 and nmi<360 then return end\n local sp=s['cpu.sp'] or 0\n local stack={}\n for i=1,8 do stack[i]=emu.read((sp+i)%65536,emu.memType.snesMemory) end\n local f=assert(io.open(", str(json.dumps(trace)), ",'a'))\n f:write(table.concat({_s8_frames,s['ppu.frameCount'] or -1,\n  s['cpu.k'] or -1,s['cpu.pc'] or -1,s['cpu.d'] or -1,s['cpu.a'] or -1,\n  s['cpu.ps'] or -1,sp,table.concat(stack,','),nmi,\n  _s8_rd(", str(symbols['Game_State']), ',2,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_Index']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_Count']), ',1,emu.memType.snesMemory),\n  _s8_rd(0x12002,2,emu.memType.snesSaveRam),\n  _s8_rd(0x12004,2,emu.memType.snesSaveRam),\n  _s8_rd(0x12430,2,emu.memType.snesSaveRam),\n  _s8_rd(0x12432,2,emu.memType.snesSaveRam),\n  _s8_hex(0x412000,16,emu.memType.snesMemory),\n  _s8_hex(0x412000,16,emu.memType.sa1Memory),\n  _s8_hex(0x10000,16,emu.memType.snesSaveRam),\n  _s8_hex(0x12000,16,emu.memType.snesSaveRam),\n  _s8_play_calls or 0,_s8_death_calls or 0,_s8_allout_calls or 0,_s8_spawn_calls or 0,\n  _s8_rd(', str(symbols['SourceVisual_Error']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Msu1_StreamBusy']), ",1,emu.memType.snesMemory)},'|'),'\\n')\n f:close()\nend,emu.eventType.endFrame)\n"])
        if world_symbols:
            if 'S6Clock_HostSourceTick__running' in world_symbols:
                clock_trace = journal.with_suffix('.source-clock-trace.txt').resolve().as_posix()
                at = lorom_offset(world_symbols['S6Clock_HostSourceTick__running'])
                tick_commit = world_symbols.get('S6Game_TickCommit', 0)
                script = script + ('\nlocal _s8_source_ticks=0\nemu.addMemoryCallback(function()\n _s8_source_ticks=_s8_source_ticks+1\n if _s8_source_ticks%128~=0 then return end\n local function rd(a,n,mt)\n  local v=0;for i=0,n-1 do v=v+emu.read(a+i,mt)*256^i end;return v\n end\n local p=emu.memType.snesMemory\n local b=emu.memType.snesSaveRam\n local row={_s8_source_ticks,rd(' + str(symbols['Nmi_FrameCounter']) + ',2,p),\n  rd(0x7E1760,2,p),rd(0x7E175C,2,p),rd(0x7E175E,2,p),\n  rd(0x7E173C,2,p),rd(' + str(tick_commit) + ',2,p),rd(0x7E1764,2,p),\n  rd(0x12002,2,b),rd(0x12004,2,b),rd(0x12440,2,b),\n  rd(0x12442,2,b),rd(0x12446,2,b),rd(0x11B00+0xD0,2,b),\n  rd(0x11B00+0xE8,2,b),rd(0x11B00+0xF0,2,b),\n  rd(0x11B00+0xF6,2,b),rd(' + str(symbols['Spawn_Index']) + ',1,p)}\n local f=assert(io.open(' + str(json.dumps(clock_trace)) + ",'a'))\n for i=1,#row do row[i]=tostring(row[i]) end\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
                host_error_trace = journal.with_suffix('.host-error-trace.txt').resolve().as_posix()
                script = script + ('\nlocal _s8_host_error_last=0\nlocal _s8_owner_last=-1\nlocal _s8_mode_last=-1\nemu.addMemoryCallback(function(a,v)\n local s=emu.getState()\n local function w(x) return emu.read(x,emu.memType.snesWorkRam)+256*emu.read(x+1,emu.memType.snesWorkRam) end\n local function bw(x) return emu.read(x,emu.memType.snesSaveRam)+256*emu.read(x+1,emu.memType.snesSaveRam) end\n local err=w(0x1764);local owner=w(0x175e);local mode=w(0x1760)\n if a==0x1764 and v==0 and _s8_host_error_last==0 then return end\n if a==0x175e and owner==_s8_owner_last then return end\n if a==0x1760 and mode==_s8_mode_last then return end\n _s8_host_error_last=err;_s8_owner_last=owner;_s8_mode_last=mode\n local f=assert(io.open(' + str(json.dumps(host_error_trace)) + ",'a'))\n f:write(table.concat({w(0x4210),a,v,s['cpu.k'] or -1,s['cpu.pc'] or -1,s['cpu.d'] or -1,\n  s['cpu.a'] or -1,s['cpu.x'] or -1,s['cpu.y'] or -1,s['cpu.sp'] or -1,\n  mode,w(0x175c),owner,err,w(0x173a),w(0x173c),w(" + str(tick_commit) + '),\n  bw(0x12002),bw(0x12004),bw(0x12008),bw(0x1200a),\n  bw(0x12440),bw(0x12442),bw(0x12446),\n  emu.read(' + str(symbols['Game_StageIndex']) + '&0xffff,emu.memType.snesWorkRam),\n  emu.read(' + str(symbols['Spawn_Index']) + "&0xffff,emu.memType.snesWorkRam)},'|'),'\\n')\n f:close()\nend,emu.callbackType.write,0x175e,0x1765,emu.cpuType.snes,emu.memType.snesWorkRam)\n")
                for point in ('S6Bridge_Import__height_bad', 'S6Bridge_Import__numeric', 'S6Host_EnvironmentBlocked'):
                    if not point not in world_symbols:
                        at = lorom_offset(world_symbols[point])
                        script = script + ("\nemu.addMemoryCallback(function()\n local s=emu.getState();local d=s['cpu.d'] or 0;local x=s['cpu.x'] or 0\n local c=0x7e0a00+x;local m=emu.memType.snesMemory;local b=emu.memType.snesSaveRam\n local function w(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n local row={'" + str(point) + "',s['ppu.frameCount'] or -1,s['cpu.k'] or -1,s['cpu.pc'] or -1,d,x,\n  emu.read(0x7e1760,m)+256*emu.read(0x7e1761,m),\n  emu.read(0x7e175e,m)+256*emu.read(0x7e175f,m),\n  emu.read(c+" + str(symbols.get('CHAR_HP', 0)) + ',m),\n  emu.read(c+' + str(symbols.get('CHAR_INPUT_DRIVEN', 0)) + ',m),\n  emu.read(c+' + str(symbols.get('CHAR_SELECTED', 0)) + ',m),\n  w(c+' + str(symbols.get('CHAR_THROW_ZPOS', 0)) + ',m),\n  w(c+' + str(symbols.get('CHAR_THROW_ZVEL', 0)) + ',m),\n  w(c+' + str(symbols.get('CHAR_POS_X', 0)) + ',m),w(c+' + str(symbols.get('CHAR_POS_Y', 0)) + ',m),\n  w(0x7e173c,m),w(' + str(symbols.get('S6Game_TickCommit', 0)) + ',m),\n  w(0x12002,b),w(0x12004,b),w(0x12008,b),w(0x1200a,b),\n  emu.read(' + str(symbols['Game_StageIndex']) + '&0xffff,emu.memType.snesWorkRam),\n  emu.read(' + str(symbols['Spawn_Index']) + '&0xffff,emu.memType.snesWorkRam)}\n local f=assert(io.open(' + str(json.dumps(host_error_trace)) + ",'a'))\n for i=1,#row do row[i]=tostring(row[i]) end\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
        if world_symbols:
            pass_points = tuple(('W6_UpdateWorld_P' + str(phase) + '__visit' for phase in range(6)))
            pass_trace = journal.with_suffix('.worker-pass-trace.txt').resolve().as_posix()
            for point in pass_points:
                if not point not in world_symbols:
                    at = lorom_offset(world_symbols[point])
                    script = script + ("\nemu.addMemoryCallback(function()\n local s=emu.getState();local x=s['cart.coprocessor.cpu.x'] or 0\n local a=0x40a000+x;local m=emu.memType.snesMemory\n local function w(o) return emu.read(a+o,m)+256*emu.read(a+o+1,m) end\n local row={'" + str(point) + "',s['ppu.frameCount'] or -1,\n  s['cart.coprocessor.cpu.pc'] or -1,s['cart.coprocessor.cpu.d'] or 0,\n  x,s['cart.coprocessor.cpu.y'] or -1,s['cart.coprocessor.cpu.a'] or -1,\n  emu.read(a+0xf6,m),w(0xfc),w(0xe0),w(0xe4),w(0xe6),w(0xc2),w(0x14),w(0x16)}\n local f=assert(io.open(" + str(json.dumps(pass_trace)) + ",'a'))\n for i=1,#row do row[i]=tostring(row[i]) end\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.sa1,emu.memType.snesPrgRom)\n')
            if 'W6_CheckPolicy' in world_symbols:
                at = lorom_offset(world_symbols['W6_CheckPolicy'])
                policy_trace = journal.with_suffix('.worker-policy-trace.txt').resolve().as_posix()
                script = script + ("\nemu.addMemoryCallback(function()\n local s=emu.getState();local d=s['cart.coprocessor.cpu.d'] or 0\n local x=s['cart.coprocessor.cpu.x'] or 0;local mt=emu.memType.sa1Memory\n local function w(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n local policy=w(d+0xe0);if policy==1 then return end\n local row={'W6_CheckPolicy',s['ppu.frameCount'] or -1,s['cart.coprocessor.cpu.k'] or -1,\n  s['cart.coprocessor.cpu.pc'] or -1,d,x,s['cart.coprocessor.cpu.y'] or -1,\n  s['cart.coprocessor.cpu.a'] or -1,policy,w(d+0xf6),w(d+0xfc),w(d+0xf2),\n  w(d+0xe6),w(d+0xe4),w(d+0xc2),w(d+0x14),w(d+0x16),w(d+0x7a)}\n local f=assert(io.open(" + str(json.dumps(policy_trace)) + ",'a'))\n for i=1,#row do row[i]=tostring(row[i]) end\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.sa1,emu.memType.snesPrgRom)\n')
            if 'Worker_WorldFault' in world_symbols:
                at = lorom_offset(world_symbols['Worker_WorldFault'])
                fault_trace = journal.with_suffix('.worker-fault-trace.txt').resolve().as_posix()
                script = script + ("\nemu.addMemoryCallback(function()\n local s=emu.getState();local d=s['cart.coprocessor.cpu.d'] or 0\n local x=s['cart.coprocessor.cpu.x'] or 0;local mt=emu.memType.sa1Memory;local b=emu.memType.snesSaveRam\n local function w(a,m) return emu.read(a,m)+256*emu.read(a+1,m) end\n local row={'Worker_WorldFault',s['ppu.frameCount'] or -1,s['cart.coprocessor.cpu.k'] or -1,\n  s['cart.coprocessor.cpu.pc'] or -1,d,x,s['cart.coprocessor.cpu.y'] or -1,\n  s['cart.coprocessor.cpu.a'] or -1,s['cart.coprocessor.cpu.sp'] or -1,\n  w(x+0x14,mt),w(x+0x16,mt),w(x+0x18,mt),w(x+0xC2,mt),\n  w(x+0xE4,mt),w(x+0xE6,mt),w(x+0xFC,mt),w(x+0xF6,mt),w(x+0xF0,mt),\n  w(0x12c50,b),w(0x12c52,b),w(0x12c54,b),w(0x12c56,b),\n  w(0x12c58,b),w(0x12c5a,b),w(0x12c5c,b),w(0x12c5e,b),\n  w(0x12c60,b),w(0x12c62,b),w(0x12c64,b),w(0x12c66,b)}\n local f=assert(io.open(" + str(json.dumps(fault_trace)) + ",'a'))\n for i=1,#row do row[i]=tostring(row[i]) end\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.sa1,emu.memType.snesPrgRom)\n')
            bind_path = journal.with_suffix('.bind-trace.txt').resolve().as_posix()
            bind_points = ('S6Host_BindExisting__bad_slot', 'S6Host_BindExisting__error', 'S6Host_Tick__unbound')
            for point in bind_points:
                if not point not in world_symbols:
                    at = lorom_offset(world_symbols[point])
                    script = script + ("\nemu.addMemoryCallback(function()\n local s=emu.getState()\n local d=s['cpu.d'] or 0\n local x=s['cpu.x'] or 0\n local a=s['cpu.a'] or 0\n local row=_s8_rd(0x7E1752,2,emu.memType.snesMemory)\n local actor=0x7E0000+d\n if '" + str(point) + "'=='S6Host_Tick__unbound' then actor=0x7E0A00+row end\n local model=" + str(world_symbols.get('S6Host_ModelTable', 0)) + "\n local rec=_s8_rd(0x7E1756,2,emu.memType.snesMemory)\n local vals={'" + str(point) + "',_s8_rd(" + str(symbols['Nmi_FrameCounter']) + ',2,emu.memType.snesMemory),\n  d,x,a,row,rec,_s8_rd(actor+' + str(symbols['CHAR_ROSTER_INDEX']) + ',1,emu.memType.snesMemory),\n  _s8_rd(actor+' + str(symbols['CHAR_INPUT_DRIVEN']) + ',1,emu.memType.snesMemory),\n  _s8_rd(actor+' + str(symbols['CHAR_HP']) + ',1,emu.memType.snesMemory),\n  _s8_rd(actor+' + str(symbols['CHAR_POS_X']) + ',2,emu.memType.snesMemory),\n  _s8_rd(actor+' + str(symbols['CHAR_POS_Y']) + ',2,emu.memType.snesMemory),\n  _s8_rd(actor+' + str(symbols['CHAR_GRAB_TARGET']) + ',1,emu.memType.snesMemory),\n  _s8_rd(actor+' + str(symbols['CHAR_GRABBED_BY']) + ',1,emu.memType.snesMemory),\n  _s8_rd(0x7E1764,2,emu.memType.snesMemory),\n  _s8_rd(0x7E173C,2,emu.memType.snesMemory),\n  _s8_rd(0x7E1754,2,emu.memType.snesMemory),\n  _s8_rd(0x7E1758,2,emu.memType.snesMemory),\n  _s8_rd(model+rec,2,emu.memType.snesMemory),\n  _s8_rd(model+rec+2,2,emu.memType.snesMemory),\n  _s8_rd(model+rec+4,2,emu.memType.snesMemory),\n  _s8_rd(model+rec+6,2,emu.memType.snesMemory),\n  _s8_rd(model+rec+12,2,emu.memType.snesMemory),\n  _s8_rd(model+rec+30,2,emu.memType.snesMemory)}\n local f=assert(io.open(' + str(json.dumps(bind_path)) + ",'a'))\n for i=1,#vals do vals[i]=string.format('%s',tostring(vals[i])) end\n f:write(table.concat(vals,'|'),'\\n');f:close()\nend,emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
        spawn_trace = journal.with_suffix('.spawn-trace.txt').resolve().as_posix()
        spawn_points = ('Spawn_Play', 'Spawn_Play__wait_check_done', 'Spawn_Play__have_queue', 'Spawn_Play__group_ok', 'Spawn_Play__active', 'Spawn_Play__triggered', 'Spawn_Play__not_yet', 'Spawn_Play__find_slot', 'Spawn_Play__find_slot_none', 'Spawn_Play__slot1', 'Spawn_Play__slot2', 'Spawn_Play__slot3', 'Spawn_Play__slot45', 'Spawn_Play__advance', 'Spawn_Play__environment_done', 'Spawn_Play__advance_index', 'Spawn_Play__slot1_not_prop', 'Spawn_Play__slot1_apply_map', 'Spawn_DoRosterReassign', 'StageEnv_ApplySpawnMap', 'ActorBehavior_Bind', 'ActorBehavior_Bind__exact', 'ActorBehavior_Bind__identity_ok', 'ActorBehavior_Bind__walk_ok', 'ActorBehavior_Bind__find', 'ActorBehavior_Bind__bad', 'ActorBehavior_Bind__bad_actor', 'S6Normal_Bind', 'S6Host_BindExisting', 'S6Host_BindExisting__slot_found', 'S6Host_BindExisting__model_found', 'S6Host_BindExisting__bridge_policy', 'S6Host_BindExisting__driver', 'S6Host_BindExisting__error', 'S6Host_BindExisting__return', 'S6Normal_MutationFenceBegin', 'S6Normal_MutationFenceBegin__wait', 'S6Normal_MutationFenceBegin__fault', 'S6Normal_MutationFenceEnd', 'S6Normal_SyncBoundContext', 'S6Normal_SyncBoundContext__metadata', 'S6Normal_Bind__fenced_done', 'S6Normal_RetireReplacedBound', 'S6Normal_RetireReplacedBound__fault', 'S7Resident_Flush')
        callback_rows = []
        for point in spawn_points:
            if not point not in symbols:
                callback_rows.append("emu.addMemoryCallback(function() _s8_spawn_mark('" + str(point) + "') end,emu.callbackType.exec," + str(lorom_offset(symbols[point])) + ',' + str(lorom_offset(symbols[point])) + ',emu.cpuType.snes,emu.memType.snesPrgRom)')
        boundary_trace = journal.with_suffix('.boundary-trace.txt').resolve().as_posix()
        boundary_points = ('Game_State_Play__playing', 'Spawn_Play', 'Game_State_Play__no_death', 'Core_Oop_Play', 'Core_Oop_Play__done', 'Character_RenderPass', 'Character_RenderPass__loop', 'Character_RenderPass__render_live', 'Character_RenderPass__dispatch', 'Character_RenderPass__render_done', 'StageTimerHost_RenderFrame', 'StageTimerHost_RenderFrame__compat', 'StageTimerHost_RenderFrame__source_done', 'StageTimerHost_RenderFrame__skip', 'SourceVisual_RenderCurrent', 'Character_RenderFrame', 'CharacterEntity_Play__context_ready', 'CharacterEntity_Play__no_context_exit', 'Character_PlayFrame__dpad_x', 'Character_PlayFrame__right', 'Character_PlayFrame__hold', 'Character_HitApply', 'StageTimerHost_ServiceDeaths', 'StageTimerHost_ServiceDeaths__normal', 'StageTimerHost_ServiceDeaths__present', 'StageTimerHost_ServiceDeaths__restore', 'StageTimerHost_ServiceDeaths__handled', 'G13_HandleP2Death', 'S6Game_DeathService', 'S6Game_DeathService__compat', 'G13_SourcePlayerDeathP1__begin', 'G13_SourcePlayerDeathP1__no', 'G13_SourcePlayerDeathP1__handled', 'G13_SourcePlayerDeathP1__respawn', 'G13_RespawnP1', 'Core_Nmi_Play', 'Core_Nmi_Play__done', 'StageTimer_NmiField', 'StageTimer_NmiField__done', 'S6Normal_RenderHook', 'S6Game_PlayRender__running', 'S6Game_PlayRender__return', 'S6Normal_RebindReturnedPlayers__done', 'S6Normal_MutationFenceBegin', 'S6Normal_MutationFenceBegin__wait', 'S6Normal_MutationFenceBegin__fault', 'S6Normal_MutationFenceEnd', 'S6Normal_SyncBoundContext', 'S6Normal_SyncBoundContext__metadata', 'S7Resident_Flush', 'Game_State_Play__stage_no_win')
        boundary_callback_rows = []
        for point in boundary_points:
            if not point not in symbols:
                boundary_callback_rows.append("emu.addMemoryCallback(function() _s8_boundary_mark('" + str(point) + "') end,emu.callbackType.exec," + str(lorom_offset(symbols[point])) + ',' + str(lorom_offset(symbols[point])) + ',emu.cpuType.snes,emu.memType.snesPrgRom)')
        script = script + ''.join(['\nlocal _s8_spawn_trace_count=0\nlocal _s8_spawn_fence_wait_nmi=-1\nlocal function _s8_spawn_mark(point)\n if _s8_rd(', str(symbols['Game_StageIndex']), ',2,emu.memType.snesMemory)~=23 then return end\n local nmi=_s8_rd(', str(symbols['Nmi_FrameCounter']), ',2,emu.memType.snesMemory)\n if nmi>9000 or _s8_spawn_trace_count>=1200 then return end\n local idx=_s8_rd(', str(symbols['Spawn_Index']), ",1,emu.memType.snesMemory)\n if idx~=2 then return end\n if point=='S6Normal_MutationFenceBegin__wait' then\n  if _s8_spawn_fence_wait_nmi==nmi then return end\n  _s8_spawn_fence_wait_nmi=nmi\n end\n _s8_spawn_trace_count=_s8_spawn_trace_count+1\n local f=assert(io.open(", str(json.dumps(spawn_trace)), ",'a'))\n local s=emu.getState()\n local cpu=table.concat({s['cpu.k'] or -1,s['cpu.pc'] or -1,s['cpu.d'] or -1,\n  s['cpu.a'] or -1,s['cpu.x'] or -1,s['cpu.y'] or -1,s['cpu.ps'] or -1,s['cpu.sp'] or -1},',')\n local actor=0x7E0A00\n local slots={}\n for n=1,5 do\n  local p=actor+n*", str(symbols['CHAR_ZP_LEN']), "\n  slots[#slots+1]=string.format('%d:%d/%d/%d/%d',n,\n   _s8_rd(p+", str(symbols['CHAR_HP']), ',1,emu.memType.snesMemory),\n   _s8_rd(p+', str(symbols['CHAR_INPUT_DRIVEN']), ',1,emu.memType.snesMemory),\n   _s8_rd(p+', str(symbols['CHAR_ROSTER_INDEX']), ',1,emu.memType.snesMemory),\n   _s8_rd(p+', str(symbols['CHAR_IDLE_FCOUNT']), ',1,emu.memType.snesMemory))\n end\n f:write(table.concat({point,nmi,\n  idx,_s8_rd(', str(symbols['Spawn_Count']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Screen_PosX']), ',2,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_GroupMin']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_GroupMax']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_ScratchEnemyCount']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_Waiting']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Msu1_StreamBusy']), ",1,emu.memType.snesMemory),\n  _s8_rd(0x7E175C,2,emu.memType.snesMemory),\n  _s8_rd(0x7E175E,2,emu.memType.snesMemory),\n  _s8_rd(0x7E1764,2,emu.memType.snesMemory),table.concat(slots,','),\n  _s8_rd(", str(symbols['Spawn_ScratchKind']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_ScratchSlotOfs']), ',2,emu.memType.snesMemory),cpu,\n  _s8_rd(0x12002,2,emu.memType.snesSaveRam),\n  _s8_rd(0x12004,2,emu.memType.snesSaveRam),\n  _s8_rd(0x1200A,1,emu.memType.snesSaveRam),\n  _s8_rd(0x1200C,1,emu.memType.snesSaveRam),\n  _s8_rd(', str(symbols['Spawn_ScratchRosterIdx']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_ScratchSubtype']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Game_Lives']), ',2,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['PlayerEntity_Hp']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['PlayerEntity_Selected']), ',1,emu.memType.snesMemory),\n  _s8_rd(0x7E0A00+', str(symbols['CHAR_FALL_STATE_TIMER']), ',1,emu.memType.snesMemory),\n  _s8_rd(0x7E0A00+', str(symbols['CHAR_TICK_COUNTER']), ",1,emu.memType.snesMemory)},'|'),'\\n')\n f:close()\nend\n", str(chr(10).join(callback_rows)), '\nlocal _s8_boundary_trace_count=0\nlocal _s8_boundary_fence_wait_nmi=-1\nlocal function _s8_boundary_mark(point)\n local nmi=_s8_rd(', str(symbols['Nmi_FrameCounter']), ',2,emu.memType.snesMemory)\n local stage=_s8_rd(', str(symbols['Game_StageIndex']), ',2,emu.memType.snesMemory)\n if nmi>9000 or _s8_boundary_trace_count>=12000 then return end\n local index=_s8_rd(', str(symbols['Spawn_Index']), ",1,emu.memType.snesMemory)\n if not ((stage==22 and index>=20 and index<=27) or\n         (stage==23 and index<=2)) then return end\n local stage23_entry=stage==23 and nmi>=870 and nmi<=930\n if point=='S6Normal_MutationFenceBegin__wait' then\n  if _s8_boundary_fence_wait_nmi==nmi then return end\n  _s8_boundary_fence_wait_nmi=nmi\n end\n local s=emu.getState()\n local pbr=(s['cpu.k'] or 0)%256\n local pc=(s['cpu.pc'] or 0)%65536\n local dp=(s['cpu.d'] or 0)%65536\n local sp=(s['cpu.sp'] or 0)%65536\n local actor_point=(string.find(point,'Character') or string.find(point,'Anim_Play'))\n if actor_point and dp~=0x0A00 then return end\n if actor_point and nmi%3~=0 then return end\n if string.find(point,'StageTimerHost_ServiceDeaths') and nmi%5~=0 then return end\n if not stage23_entry and (point=='Spawn_Play' or point=='Game_State_Play__playing' or\n     point=='S6Normal_RenderHook' or point=='S7Resident_Flush' or\n     point=='Game_State_Play__stage_no_win') and nmi%15~=0 then return end\n _s8_boundary_trace_count=_s8_boundary_trace_count+1\n local actor=0x7E0000+dp\n local actor_fields='na'\n if dp>=0x0A00 and dp<0x0D20 then\n  actor_fields=string.format('%d/%d/%d/%04x/%04x',\n   _s8_rd(actor+", str(symbols['CHAR_HP']), ',1,emu.memType.snesMemory),\n   _s8_rd(actor+', str(symbols['CHAR_INPUT_DRIVEN']), ',1,emu.memType.snesMemory),\n   _s8_rd(actor+', str(symbols['CHAR_SELECTED']), ',1,emu.memType.snesMemory),\n   _s8_rd(actor+', str(symbols['CHAR_POS_X']), ',2,emu.memType.snesMemory),\n   _s8_rd(actor+', str(symbols['CHAR_POS_Y']), ",2,emu.memType.snesMemory))\n end\n local stack={};for i=1,8 do stack[i]=string.format('%02x',emu.read((sp+i)%65536,emu.memType.snesMemory)) end\n local code={};for i=0,7 do code[i+1]=string.format('%02x',emu.read(pbr*65536+pc+i,emu.memType.snesMemory)) end\n local f=assert(io.open(", str(json.dumps(boundary_trace)), ",'a'))\n f:write(table.concat({point,nmi,pbr,pc,dp,sp,s['cpu.a'] or -1,\n  s['cpu.x'] or -1,s['cpu.y'] or -1,s['cpu.ps'] or -1,\n  _s8_rd(", str(symbols['Game_State']), ',2,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Spawn_Index']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['OopObjIndex_Lo']), ',2,emu.memType.snesMemory),actor_fields,\n  _s8_rd(0x12002,2,emu.memType.snesSaveRam),\n  _s8_rd(0x12004,2,emu.memType.snesSaveRam),\n  _s8_rd(0x1200C,1,emu.memType.snesSaveRam),\n  _s8_rd(0x1200A,1,emu.memType.snesSaveRam),\n  _s8_rd(0x7E175E,2,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['Game_Lives']), ',2,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['PlayerEntity_Hp']), ',1,emu.memType.snesMemory),\n  _s8_rd(', str(symbols['PlayerEntity_Selected']), ',1,emu.memType.snesMemory),\n  _s8_rd(0x7E0A00+', str(symbols['CHAR_FALL_STATE_TIMER']), ',1,emu.memType.snesMemory),\n  _s8_rd(0x7E0A00+', str(symbols['CHAR_TICK_COUNTER']), ",1,emu.memType.snesMemory),\n  table.concat(stack,','),table.concat(code,',')},'|'),'\\n')\n f:close()\nend\n", str(chr(10).join(boundary_callback_rows)), '\n'])
    if trace_bind:
        if world_symbols:
            bind_path = journal.with_suffix('.bind-trace.txt').resolve().as_posix()
            hit_path = journal.with_suffix('.native-hit-trace.txt').resolve().as_posix()
            script = script + '\nlocal function _s8_bind_rd(a,n)\n local v=0;for i=0,n-1 do v=v+emu.read(a+i,emu.memType.snesMemory)*256^i end;return v\nend\nlocal function _s8_sa1_rd(a,n)\n local v=0;for i=0,n-1 do v=v+emu.read(a+i,emu.memType.sa1Memory)*256^i end;return v\nend\nlocal function _s8_bw_rd(a,n)\n local v=0;for i=0,n-1 do v=v+emu.read(a+i,emu.memType.snesSaveRam)*256^i end;return v\nend\n'
            for point in ('S6Normal_Init__enabled', 'S6Normal_RenderHook', 'S6Normal_BindLiveActors__bind', 'S6Normal_BindLiveActors__roster_changed', 'S6Normal_BindLiveActors__ownership_fault', 'S6Normal_RetireReplacedBound', 'S6Normal_RetireReplacedBound__fault', 'S6Normal_RetireReplacedBound__unlinked', 'S6Normal_Bind__combat', 'S6Normal_Bind__bind', 'S6Normal_Bind__fallback', 'S6Host_BindExisting', 'S6Host_BindExisting__model_found', 'S6Host_BindExisting__bridge_policy', 'S6Host_BindExisting__bad_slot', 'S6Host_BindExisting__error', 'S6Host_BindExisting__scheduled', 'S6Host_BindExisting__return', 'S6Host_BindExisting__scheduled', 'S6Normal_SyncBoundContext__metadata_start', 'S6Normal_SyncBoundContext__done', 'S6Game_PlayRender__measure', 'S6Game_PlayRender__has_elapsed', 'S6Game_PlayRender__field', 'S6Host_Tick__unbound', 'S6Host_PlayerAction', 'S6Host_PlayerInputTrigger', 'S6Host_PlayerAction__attack', 'WHost_PlayerAction', 'WHost_PlayerInputTrigger', 'WHost_PlayerAction__attack', 'WHost_PlayerAttack', 'W6_ThinkPass', 'W6_ThinkPass__done', 'W6_Think', 'W6_UpdateWorld_P0__call', 'W6_UpdateWorld_P2__call', 'Worker_Execute', 'Worker_Tick', 'Worker_ApplyRemove', 'Worker_ApplyRemove__found', 'Worker_ApplyRemove__bad', 'Relay_Poll_P2__owned', 'Relay_Queue', 'Relay_Queued'):
                if not point not in world_symbols:
                    at = lorom_offset(world_symbols[point])
                    script = script + ''.join(["\nemu.addMemoryCallback(function()\n if '", str(point), "'=='S6Normal_RenderHook' then\n  local field=_s8_bind_rd(", str(symbols['Nmi_FrameCounter']), ",2)\n  if field%10~=0 or field==_s8_bind_last_render_field then return end\n  _s8_bind_last_render_field=field\n  _s8_bind_render_hits=(_s8_bind_render_hits or 0)+1\n  if _s8_bind_render_hits>128 then return end\n end\n if '", str(point), "'=='Worker_Execute' then\n  _s8_worker_execute_hits=(_s8_worker_execute_hits or 0)+1\n  if _s8_worker_execute_hits>32 then return end\n elseif '", str(point), "'=='W6_ThinkPass' or '", str(point), "'=='W6_Think' then\n  local state=emu.getState()\n  local actor_dp=state['cart.coprocessor.cpu.d'] or 0\n  if actor_dp~=0x7900 and actor_dp~=0x7A00 then return end\n  _s8_worker_think_hits=(_s8_worker_think_hits or 0)+1\n  if _s8_worker_think_hits>512 then return end\n elseif '", str(point), "'=='Worker_Tick' or '", str(point), "'=='Worker_ApplyRemove' or\n        '", str(point), "'=='Worker_ApplyRemove__found' or '", str(point), "'=='Worker_ApplyRemove__bad' then\n  _s8_remove_trace_hits=(_s8_remove_trace_hits or 0)+1\n  if _s8_remove_trace_hits>256 then return end\n elseif string.find('", str(point), "','S6Game_PlayRender__',1,true)==1 then\n  if '", str(point), "'~='S6Game_PlayRender__has_elapsed' then return end\n  local gap_state=emu.getState()\n  local gap=gap_state['cpu.a'] or 0\n  local error=_s8_bind_rd(0x7E1764,2)\n  if gap<8 and error==0 then return end\n  _s8_clock_trace_hits=(_s8_clock_trace_hits or 0)+1\n  if _s8_clock_trace_hits>256 then return end\n elseif '", str(point), "'=='WHost_PlayerAction' or '", str(point), "'=='WHost_PlayerInputTrigger' or\n        '", str(point), "'=='WHost_PlayerAction__attack' or '", str(point), "'=='WHost_PlayerAttack' then\n  local stage=_s8_bind_rd(", str(symbols['Game_StageIndex']), ',2)\n  local index=_s8_bind_rd(', str(symbols['Spawn_Index']), ",1)\n  if stage~=22 and stage~=23 then return end\n  _s8_player_action_hits=(_s8_player_action_hits or 0)+1\n  if _s8_player_action_hits>64 then return end\n end\n if '", str(point), "'=='WHost_PlayerAction__attack' or '", str(point), "'=='WHost_PlayerAttack' then\n  _s8_player_attack_hits=(_s8_player_attack_hits or 0)+1\n  if _s8_player_attack_hits>64 then return end\n end\n if '", str(point), "'=='Relay_Poll_P2__owned' then\n  local p1=_s8_bind_rd(", str(symbols['Input_press']), ',2)\n  local t1=_s8_bind_rd(', str(symbols['Input_trigger']), ',2)\n  local p2=_s8_bind_rd(', str(symbols['Input2_press']), ',2)\n  local t2=_s8_bind_rd(', str(symbols['Input2_trigger']), ",2)\n  if p1==_s8_bind_last_p1 and t1==0 and p2==_s8_bind_last_p2 and t2==0 then return end\n  _s8_bind_last_p1=p1;_s8_bind_last_p2=p2\n  _s8_bind_input_hits=(_s8_bind_input_hits or 0)+1\n  if _s8_bind_input_hits>128 then return end\n elseif '", str(point), "'=='Relay_Queue' then\n  local held=_s8_bind_rd(0x412014,2)\n  if math.floor(held/16384)%2==0 then return end\n  _s8_bind_input_hits=(_s8_bind_input_hits or 0)+1\n  if _s8_bind_input_hits>128 then return end\n end\n local s=emu.getState()\n local d=s['", str('cart.coprocessor.cpu.d' if point.startswith(('WHost_Player', 'W6_', 'Worker_')) else 'cpu.d'), "'] or 0\n local x=s['", str('cart.coprocessor.cpu.x' if point.startswith(('WHost_Player', 'W6_', 'Worker_')) else 'cpu.x'), "'] or 0\n local y=s['", str('cart.coprocessor.cpu.y' if point.startswith(('WHost_Player', 'W6_', 'Worker_')) else 'cpu.y'), "'] or 0\n local a=s['", str('cart.coprocessor.cpu.a' if point.startswith(('WHost_Player', 'W6_', 'Worker_')) else 'cpu.a'), "'] or 0\n local worker_context_offset=0\n local worker_bus_context=0\n if d>=0x7900 and d<0x7D00 then worker_context_offset=d-0x7900 end\n if string.sub('", str(point), "',1,18)=='W6_UpdateWorld_P' and x>=0x7900 and x<0x7D00 then\n  worker_context_offset=x-0x7900\n  worker_bus_context=0x40A000+x\n elseif d>=0x7900 and d<0x7D00 then\n  worker_bus_context=0x40A000+d\n end\n local row=_s8_bind_rd(0x7E1752,2)\n local context=_s8_bind_rd(0x7E1754,2)\n local actor=0x7E0000+d\n local policy=0\n  if string.sub('", str(point), "',1,10)=='WHost_Play' then\n   row=d-0x7900\n   actor=0x7E0000+d\n   policy=_s8_bind_rd(", str(world_symbols.get('S6Bridge_Policy', 0)), "+row,1)\n  elseif '", str(point), "'=='S6Host_Tick__unbound' then\n  actor=0x7E0A00+x\n  row=x\n  policy=_s8_bind_rd(", str(world_symbols.get('S6Bridge_Policy', 0)), '+x,1)\n else\n  row=d-0x0A00\n  if row>=0 and row<798 then\n   policy=_s8_bind_rd(', str(world_symbols.get('S6Bridge_Policy', 0)), '+row,1)\n  end\n end\n local model=', str(world_symbols.get('S6Host_ModelTable', 0)), '\n local rec=_s8_bind_rd(0x7E1756,2)\n local context_dp=_s8_bind_rd(0x7E1754,2)\n local context_valid=context_dp>=0x1900 and context_dp<0x1F00 and context_dp%0x100==0\n local context_offset=context_valid and context_dp-0x1900 or 0\n local bw_context=0x11900+context_offset\n local worker_tick_index=_s8_bw_rd(0x12004,2)%512\n local worker_tick_time=_s8_bw_rd(0x13000+worker_tick_index*8,4)\n local vals={', repr(point), ',_s8_bind_rd(', str(symbols['Nmi_FrameCounter']), ',2),\n  d,x,y,a,row,context,rec,policy,\n  _s8_bind_rd(actor+', str(symbols['CHAR_ROSTER_INDEX']), ',1),\n  _s8_bind_rd(actor+', str(symbols['CHAR_INPUT_DRIVEN']), ',1),\n  _s8_bind_rd(actor+', str(symbols['CHAR_HP']), ',1),\n  _s8_bind_rd(actor+', str(symbols['CHAR_POS_X']), ',2),\n  _s8_bind_rd(actor+', str(symbols['CHAR_POS_Y']), ',2),\n  _s8_bind_rd(actor+', str(symbols['CHAR_GRAB_TARGET']), ',1),\n  _s8_bind_rd(actor+', str(symbols['CHAR_GRABBED_BY']), ',1),\n  _s8_bind_rd(0x7E1760,2),_s8_bind_rd(0x7E1764,2),_s8_bind_rd(0x7E173C,2),\n  _s8_bind_rd(0x7E1772,2),_s8_bind_rd(0x7E1774,2),\n  _s8_bind_rd(0x7E177A,2),_s8_bind_rd(0x7E177C,2),\n   _s8_bind_rd(0x412020,2),_s8_bind_rd(0x412022,2),\n   _s8_bind_rd(0x412024,2),_s8_bind_rd(0x412026,2),\n   _s8_bind_rd(', str(symbols['Input_press']), ',2),_s8_bind_rd(', str(symbols['Input_trigger']), ',2),\n   _s8_bind_rd(', str(symbols['Input2_press']), ',2),_s8_bind_rd(', str(symbols['Input2_trigger']), ',2),\n _s8_bind_rd(0x7E0414,2),_s8_bind_rd(0x7E041A,2),\n   _s8_bind_rd(0x7E041C,2),_s8_bind_rd(0x7E041E,2),\n   _s8_bind_rd(0x415000+x,2),_s8_bind_rd(0x415002+x,2),\n   _s8_bind_rd(0x415004+x,2),_s8_bind_rd(0x415006+x,2),\n   _s8_sa1_rd(d+0x08,2),_s8_sa1_rd(d+0x14,2),\n   _s8_sa1_rd(d+0x38,2),_s8_sa1_rd(d+0xA0,2),\n   _s8_sa1_rd(d+0xD0,2),_s8_sa1_rd(d+0xD2,2),\n   _s8_sa1_rd(d+0xE6,1),_s8_sa1_rd(d+0xE8,2),\n   _s8_sa1_rd(d+0xEA,2),_s8_sa1_rd(d+0xF6,1),\n   _s8_sa1_rd(d+0xFC,1),\n   _s8_bw_rd(0x11900+worker_context_offset+0xD0,2),\n   _s8_bw_rd(0x11900+worker_context_offset+0xD2,2),\n   _s8_bw_rd(0x11900+worker_context_offset+0xE4,2),\n   _s8_bw_rd(0x11900+worker_context_offset+0xE6,2),\n   _s8_bw_rd(0x11900+worker_context_offset+0xE8,2),\n   _s8_bw_rd(0x11900+worker_context_offset+0xEA,2),\n   _s8_bind_rd(0x7E1900+context_offset+0xD0,2),\n   _s8_bind_rd(0x7E1900+context_offset+0xD2,2),\n   _s8_bind_rd(0x7E1900+context_offset+0xE6,2),\n   _s8_bind_rd(0x7E1900+context_offset+0xE8,2),\n   _s8_bind_rd(0x7E1900+context_offset+0xEA,2),\n   _s8_bind_rd(bw_context+0xD0,2),_s8_bind_rd(bw_context+0xD2,2),\n   _s8_bind_rd(bw_context+0xE6,2),_s8_bind_rd(bw_context+0xE8,2),\n   _s8_bind_rd(bw_context+0xEA,2),\n   _s8_bind_rd(worker_bus_context+0xD0,2),\n   _s8_bind_rd(worker_bus_context+0xD2,2),\n   _s8_bind_rd(worker_bus_context+0xE6,2),\n   _s8_bind_rd(worker_bus_context+0xE8,2),\n   _s8_bind_rd(worker_bus_context+0xEA,2),\n   _s8_bind_rd(0x40A0773C,2),_s8_bind_rd(0x40A0773E,2),\n   worker_tick_index,worker_tick_time,\n   _s8_bind_rd(0x12002,2),_s8_bind_rd(0x12004,2),\n   _s8_bind_rd(0x412014,2),_s8_bind_rd(0x412016,2),\n   _s8_bind_rd(0x412018,2),_s8_bind_rd(0x41201A,2),\n  _s8_bind_rd(model+rec,2),_s8_bind_rd(model+rec+2,2),\n  _s8_bind_rd(model+rec+4,2),_s8_bind_rd(model+rec+6,2),\n  _s8_bind_rd(model+rec+12,2),_s8_bind_rd(model+rec+30,2),\n  _s8_bw_rd(0x1173C,2),_s8_bw_rd(0x1243E,2),\n  _s8_bw_rd(0x12440,2),_s8_bw_rd(0x12442,2),\n  _s8_bw_rd(0x12444,2),_s8_bw_rd(0x12446,2)}\n local f=assert(io.open(', str(json.dumps(bind_path)), ",'a'))\n for i=1,#vals do vals[i]=tostring(vals[i]) end\n f:write(table.concat(vals,'|'),'\\n');f:close()\nend,emu.callbackType.exec,", str(at), ',', str(at), ',', str('emu.cpuType.sa1' if point.startswith(('WHost_Player', 'W6_', 'Worker_')) else 'emu.cpuType.snes'), ',emu.memType.snesPrgRom)\n            '])
            native_hit_points = ('Character_HitApply', 'Character_HitApply__attacking', 'Character_HitApply__do_vs_all_ai', 'StageTimerHost_VsAllGeneric', 'StageTimerHost_VsAllGeneric__target', 'Character_HitApply_VsEntityGeneric', 'Character_HitApply__ScoreAndFinish', 'Character_HitApply__ApplyDamage', 'Character_HitApply__RevealOrPickup')
            for point in native_hit_points:
                if not point not in symbols:
                    at = lorom_offset(symbols[point])
                    selected = symbols.get('CHAR_SELECTED', 0)
                    input_driven = symbols.get('CHAR_INPUT_DRIVEN', 0)
                    hp = symbols.get('CHAR_HP', 0)
                    pos_x = symbols.get('CHAR_POS_X', 0)
                    pos_y = symbols.get('CHAR_POS_Y', 0)
                    attack_frames = symbols.get('CHAR_ATTACK_FCOUNT', 0)
                    hit_applied = symbols.get('CHAR_HIT_APPLIED', 0)
                    attack_variant = symbols.get('CHAR_ATTACK_VARIANT', 0)
                    hit_target = symbols.get('HitApply_TargetIndex', 0)
                    scan_index = symbols.get('VmNativeEng_ScanIndex', 0)
                    entity_base = symbols.get('HitApply_EntityBase', 0)
                    script = script + ''.join(['\nemu.addMemoryCallback(function()\n local stage=_s8_bind_rd(', str(symbols['Game_StageIndex']), ',2)\n local index=_s8_bind_rd(', str(symbols['Spawn_Index']), ",1)\n if stage~=23 or index<32 then return end\n _s8_native_hit_trace_count=(_s8_native_hit_trace_count or 0)+1\n if _s8_native_hit_trace_count>256 then return end\n local s=emu.getState()\n local d=s['cpu.d'] or 0\n local x=s['cpu.x'] or 0\n local actor=0x7E0000+d\n local target=0x7E0A00+x\n local f=assert(io.open(", str(json.dumps(hit_path)), ",'a'))\n local vals={", repr(point), ',_s8_bind_rd(', str(symbols['Nmi_FrameCounter']), ",2),\n  index,d,x,s['cpu.y'] or 0,s['cpu.a'] or 0,\n  _s8_bind_rd(actor+", str(selected), ',1),_s8_bind_rd(actor+', str(input_driven), ',1),\n  _s8_bind_rd(actor+', str(hp), ',1),_s8_bind_rd(actor+', str(pos_x), ',2),\n  _s8_bind_rd(actor+', str(pos_y), ',2),_s8_bind_rd(actor+', str(attack_frames), ',1),\n  _s8_bind_rd(actor+', str(hit_applied), ',1),_s8_bind_rd(actor+', str(attack_variant), ',1),\n  _s8_bind_rd(target+', str(hp), ',1),_s8_bind_rd(target+', str(pos_x), ',2),\n  _s8_bind_rd(target+', str(pos_y), ',2),_s8_bind_rd(', str(hit_target), ',1),\n  _s8_bind_rd(', str(scan_index), ',2),_s8_bind_rd(', str(entity_base), ',2),\n  _s8_bind_rd(', str(symbols['PlayerEntity_Hp']), ',1),\n  _s8_bind_rd(', str(symbols['Input_press']), ',2),_s8_bind_rd(', str(symbols['Input_trigger']), ",2)}\n for i=1,#vals do vals[i]=tostring(vals[i]) end\n f:write(table.concat(vals,'|'),'\\n');f:close()\nend,emu.callbackType.exec,", str(at), ',', str(at), ',emu.cpuType.snes,emu.memType.snesPrgRom)\n'])
    if trace_ownership:
        if world_symbols:
            ownership_path = journal.with_suffix('.ownership-fault-trace.txt').resolve().as_posix()
            ownership_points = ('S6Normal_BindLiveActors__roster_changed', 'S6Normal_BindLiveActors__worker_unlinked', 'S6Normal_BindLiveActors__worker_retired', 'S6Normal_BindLiveActors__ownership_fault', 'S6Host_BindExisting__error', 'S6Bridge_Import__linked', 'S6Normal_RetireReplacedBound', 'S6Normal_RetireReplacedBound__already_unlinked', 'S6Normal_RetireReplacedBound__fault', 'S6Normal_RetireReplacedBound__unlinked', 'S6Normal_RetireReplacedBound__return')
            script = script + ''.join(["\nlocal _s8_ownership_hits=0\nlocal _s8_ownership_point_hits={}\nlocal function _s8_ownership_mark(point)\n local point_hits=_s8_ownership_point_hits[point] or 0\n local point_limit=point=='S6Normal_BindLiveActors__roster_changed' and 4 or\n                   (string.find(point,'worker_',1,true) and 8 or 16)\n if _s8_ownership_hits>=128 or point_hits>=point_limit then return end\n local s=emu.getState();local p=emu.memType.snesMemory\n local b=emu.memType.snesSaveRam\n local function rd(a,n,mt)\n  local v=0;for i=0,n-1 do v=v+emu.read(a+i,mt)*256^i end;return v\n end\n local d=s['cpu.d'] or 0;local x=s['cpu.x'] or 0;local row=rd(0x7E1752,2,p)\n if string.find(point,'S6Normal_BindLiveActors',1,true) or\n    string.find(point,'S6Bridge_Import',1,true) then row=x end\n local slot=math.floor(row/", str(symbols['CHAR_ZP_LEN']), ')\n if slot<0 or slot>=6 then slot=math.floor(math.max(0,x)/', str(symbols['CHAR_ZP_LEN']), ') end\n if slot<0 or slot>=6 then slot=0 end\n local native=0x7E0A00+slot*', str(symbols['CHAR_ZP_LEN']), '\n local context=0x7E1900+slot*256;local bridge=', str(world_symbols.get('S6Bridge_Policy', 0)), '+slot*', str(symbols['CHAR_ZP_LEN']), "\n local worker_status=rd(0x412140+row,2,p)\n local worker_context=rd(0x412144+row,2,p)\n local vals={point,s['ppu.frameCount'] or -1,\n  rd(", str(symbols['Nmi_FrameCounter']), ',2,p),rd(', str(symbols['Game_StageIndex']), ',2,p),\n  rd(', str(symbols['Spawn_Index']), ",1,p),s['cpu.k'] or -1,s['cpu.pc'] or -1,\n  d,s['cpu.a'] or -1,x,s['cpu.y'] or -1,s['cpu.sp'] or -1,\n  row,slot,rd(0x7E1760,2,p),rd(0x7E175E,2,p),rd(0x7E1764,2,p),\n  rd(0x7E1754,2,p),rd(0x7E1900+slot*256+0xE0,2,p),\n  rd(0x7E1900+slot*256+0xF6,1,p),\n  rd(native+", str(symbols['CHAR_ROSTER_INDEX']), ',1,p),\n  rd(native+', str(symbols['CHAR_INPUT_DRIVEN']), ',1,p),\n  rd(native+', str(symbols['CHAR_HP']), ',1,p),\n  rd(native+', str(symbols['CHAR_GRAB_TARGET']), ',1,p),\n  rd(native+', str(symbols['CHAR_GRABBED_BY']), ',1,p),rd(bridge+0,1,p),\n  rd(bridge+1,1,p),\n  rd(', str(world_symbols.get('S6Bridge_Context', 0)), '+row,2,p),worker_status,worker_context,\n  rd(', str(world_symbols.get('S6Normal_BoundRoster', 8263616)), '+slot,1,p),\n  rd(0x12002,2,b),rd(0x12004,2,b),rd(0x12008,2,b),rd(0x1200A,1,b)}\n for i=1,#vals do vals[i]=tostring(vals[i]) end\n local f=assert(io.open(', str(json.dumps(ownership_path)), ",'a'))\n f:write(table.concat(vals,'|'),'\\n');f:close();_s8_ownership_hits=_s8_ownership_hits+1\n _s8_ownership_point_hits[point]=point_hits+1\nend\n"])
            for point in ownership_points:
                address = world_symbols.get(point)
                if not address is None:
                    at = lorom_offset(address)
                    script = script + ("\nemu.addMemoryCallback(function() _s8_ownership_mark('" + str(point) + "') end,\n emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
            script = script + ('\nlocal _s8_host_error_writes=0\nemu.addMemoryCallback(function(a,v)\n if _s8_host_error_writes>=32 then return end\n local s=emu.getState();local p=emu.memType.snesMemory\n local function rd(x,n,mt)\n  local r=0;for i=0,n-1 do r=r+emu.read(x+i,mt)*256^i end;return r\n end\n local err=rd(0x7E1764,2,p)\n if rd(' + str(symbols['Game_CampaignId']) + ",1,p)~=3 or err==0 then return end\n local vals={'S6Host_Error_write',s['ppu.frameCount'] or -1,\n  rd(" + str(symbols['Nmi_FrameCounter']) + ',2,p),rd(' + str(symbols['Game_StageIndex']) + ',2,p),\n  rd(' + str(symbols['Spawn_Index']) + ",1,p),s['cpu.k'] or -1,s['cpu.pc'] or -1,\n  s['cpu.d'] or -1,s['cpu.a'] or -1,s['cpu.x'] or -1,s['cpu.y'] or -1,\n  a,v,err,rd(0x7E1752,2,p),rd(0x7E1754,2,p),\n  rd(0x7E175E,2,p),rd(0x7E1760,2,p),rd(0x12002,2,emu.memType.snesSaveRam),\n  rd(0x12004,2,emu.memType.snesSaveRam)}\n for i=1,#vals do vals[i]=tostring(vals[i]) end\n local f=assert(io.open(" + str(json.dumps(ownership_path)) + ",'a'))\n        f:write(table.concat(vals,'|'),'\\n');f:close();_s8_host_error_writes=_s8_host_error_writes+1\nend,emu.callbackType.write,0x1764,0x1765,emu.cpuType.snes,emu.memType.snesWorkRam)\n")
            relay_fault = world_symbols.get('Relay_DrainEvents__fault')
            if relay_fault is not None:
                fault_trace_path = journal.with_suffix('.worker-event-fault-trace.txt').resolve().as_posix()
                fault_at = lorom_offset(relay_fault)
                script = script + ("\nlocal _s8_worker_fault_hits=0\nemu.addMemoryCallback(function()\n if _s8_worker_fault_hits>=4 then return end\n _s8_worker_fault_hits=_s8_worker_fault_hits+1\n local s=emu.getState();local b=emu.memType.snesSaveRam;local m=emu.memType.snesMemory\n local function w(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n local head=w(0x12430,b);local tail=w(0x12432,b);local ri=0x12450+(tail%128)*16\n local row={'Relay_DrainEvents__fault',s['ppu.frameCount'] or -1,\n  s['cart.coprocessor.cpu.k'] or -1,s['cart.coprocessor.cpu.pc'] or -1,\n  s['cart.coprocessor.cpu.d'] or -1,s['cart.coprocessor.cpu.a'] or -1,\n  s['cart.coprocessor.cpu.x'] or -1,s['cart.coprocessor.cpu.y'] or -1,\n  s['cart.coprocessor.cpu.sp'] or -1,s['cart.coprocessor.cpu.ps'] or -1,\n  head,tail,w(0x12434,b),w(ri,b),w(ri+2,b),w(ri+4,b),w(ri+6,b),\n  w(ri+8,b),w(ri+10,b),w(ri+12,b),w(ri+14,b),\n  w(0x7e1764,m),w(0x7e175c,m),w(0x7e175e,m),w(0x7e1760,m)}\n for i=1,#row do row[i]=tostring(row[i]) end\n local f=assert(io.open(" + str(json.dumps(fault_trace_path)) + ",'a'))\n f:write(table.concat(row,'|'),'\\n');f:close()\nend,emu.callbackType.exec," + str(fault_at) + ',' + str(fault_at) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
    if trace_pc_only:
        if world_symbols:
            protocol_trace_path = Path(os.environ.get('S8_PROTOCOL_TRACE_PATH', str(journal.with_suffix('.protocol-call-trace.txt')))).resolve().as_posix()
            streaming_trace_path = Path(os.environ.get('S8_STREAMING_TRACE_PATH', str(journal.with_suffix('.streaming-state-trace.txt')))).resolve().as_posix()
            worker_error_trace_path = Path(os.environ.get('S8_WORKER_ERROR_TRACE_PATH', str(journal.with_suffix('.worker-error-pc-trace.txt')))).resolve().as_posix()
            script = script + ('\nlocal _s8_protocol_trace=assert(io.open(' + str(json.dumps(protocol_trace_path)) + ",'w'))\nlocal _s8_protocol_hits={}\n")
            script = script + ('\nlocal _s8_worker_error_trace=assert(io.open(' + str(json.dumps(worker_error_trace_path)) + ",'w'))\nlocal _s8_worker_error_hits={}\nlocal function _s8_worker_error_mark(label,cpu_name)\n local hits=_s8_worker_error_hits[label] or 0\n if hits>=32 then return end\n _s8_worker_error_hits[label]=hits+1\n local s=emu.getState();local m=emu.memType.snesMemory\n local b=emu.memType.snesSaveRam;local sm=emu.memType.sa1Memory\n local pc_key=cpu_name=='sa1' and 'cart.coprocessor.cpu.pc' or 'cpu.pc'\n local d_key=cpu_name=='sa1' and 'cart.coprocessor.cpu.d' or 'cpu.d'\n local a_key=cpu_name=='sa1' and 'cart.coprocessor.cpu.a' or 'cpu.a'\n local x_key=cpu_name=='sa1' and 'cart.coprocessor.cpu.x' or 'cpu.x'\n local y_key=cpu_name=='sa1' and 'cart.coprocessor.cpu.y' or 'cpu.y'\n local sp_key=cpu_name=='sa1' and 'cart.coprocessor.cpu.sp' or 'cpu.sp'\n local ps_key=cpu_name=='sa1' and 'cart.coprocessor.cpu.ps' or 'cpu.ps'\n local d=s[d_key] or -1;local base=(d>=0x7900 and d<0x7f00) and (0x11900+d-0x7900) or 0x11900\n local function w(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n local row={label,s['ppu.frameCount'] or -1,cpu_name,s[pc_key] or -1,d,\n  s[a_key] or -1,s[x_key] or -1,s[y_key] or -1,s[sp_key] or -1,s[ps_key] or -1,\n  w(0x7e2754,m),emu.read(0x7e586e,m),w(0x7e1764,m),w(0x12008,b),\n  emu.read(0x1200a,b),w(0x12002,b),w(0x12004,b),w(base+0x14,b),\n  w(base+0x16,b),w(base+0x44,b),w(base+0x46,b),w(base+0xFC,b),\n  (d>=0 and w((d+0xF2)%65536,sm) or -1),\n  ((s[x_key] or 0)>=0 and w(0x40a000+(s[x_key] or 0)+0xf2,m) or -1),\n  ((s[x_key] or 0)>=0 and w(0x40a000+(s[x_key] or 0)+0xf6,m) or -1),\n  (d>=0 and w((d+0xB0)%65536,sm) or -1),\n  ((s[x_key] or 0)>=0 and w(0x40a000+(s[x_key] or 0),m) or -1),\n  ((s[x_key] or 0)>=0 and w(0x40a000+(s[x_key] or 0)+2,m) or -1),\n  ((s[x_key] or 0)>=0 and w(0x7e0000+(s[x_key] or 0)-0x6000,m) or -1),\n  ((s[x_key] or 0)>=0 and w(0x7e0002+(s[x_key] or 0)-0x6000,m) or -1),\n  (d>=0 and w((d+0xBA)%65536,sm) or -1),\n  (d>=0 and w((d+0xBE)%65536,sm) or -1),\n  (d>=0 and w((d+0x76)%65536,sm) or -1),\n  (d>=0 and emu.read((d+0xC2)%65536,sm) or -1),\n  (d>=0 and emu.read((d+0xFC)%65536,sm) or -1)}\n for i=1,#row do row[i]=tostring(row[i]) end\n _s8_worker_error_trace:write(table.concat(row,'|'),'\\n')\n _s8_worker_error_trace:flush()\nend\n")
            for label, cpu_name in (('W6_TryHitOne', 'sa1'), ('W6_TryHitOne__addresses', 'sa1'), ('W6_TryHitOne__player_target', 'sa1'), ('W6_TryHitOne__target_type', 'sa1'), ('W6_TryHitOne__damage', 'sa1'), ('W6_PlayerGroundDamage', 'sa1'), ('W6_PlayerGroundDamage__range', 'sa1'), ('W6_PlayerGroundDamage__lifecycle', 'sa1'), ('W6_PlayerGroundDamage__not_damage_type', 'sa1'), ('W6_EnemyGroundDamage', 'sa1'), ('W6_EnemyGroundDamage__range', 'sa1'), ('W6_SelectTarget__numeric', 'sa1'), ('W6_TargetDelta__numeric', 'sa1'), ('WHost_EnvironmentBlocked', 'sa1'), ('W5_HostRandom03', 'sa1'), ('S6_SelectTarget__numeric', 'snes'), ('S6_TargetDelta__numeric', 'snes'), ('S6Host_EnvironmentBlocked', 'snes')):
                address = world_symbols.get(label)
                if not address is None:
                    at = lorom_offset(address)
                    script = script + ('\nemu.addMemoryCallback(function()\n _s8_worker_error_mark(' + str(json.dumps(label)) + ',' + str(json.dumps(cpu_name)) + ')\nend,emu.callbackType.exec,' + str(at) + ',' + str(at) + ',emu.cpuType.' + str(cpu_name) + ',emu.memType.snesPrgRom)\n')
            protocol_labels = ('S6Normal_Init', 'StageEnv_ResetActors__worker_call', 'S6Normal_ResetStageWorld', 'S6Normal_ResetStageWorld__return', 'S6Clock_ClockAdvance', 'S6Clock_HostSourceTick', 'S6Host_Tick', 'S6Host_Tick__resident_execute', 'Relay_Run', 'Relay_Acquire', 'Relay_InFields', 'Relay_AcquireDone', 'Relay_Queued', 'Relay_Flush', 'Relay_Request_Snapshot', 'Relay_Snapshot_Ready', 'Relay_Commit_A', 'Relay_Commit_B', 'Relay_Flush_Return', 'Relay_Timeout', 'StageComplete_Start', 'StageComplete_Update', 'StageComplete_Update__no_skip', 'StageComplete_Update__presentation', 'StageComplete_Update__step') + tuple(('Relay_' + str(kind) + '_B_' + str(slot) for slot in range(6) for kind in ('SnapshotZeroPolicy', 'SnapshotBound', 'SnapshotUnbound', 'ProjectNext', 'SnapshotPolicyFault', 'ProjectFault')))
            for label in protocol_labels:
                address = world_symbols.get(label, symbols.get(label))
                if not address is None:
                    at = lorom_offset(address)
                    script = script + ('\nemu.addMemoryCallback(function()\n local n=_s8_protocol_hits[' + str(json.dumps(label)) + '] or 0\n if n>=40 then return end\n _s8_protocol_hits[' + str(json.dumps(label)) + ']=n+1\n local s=emu.getState();local m=emu.memType.snesMemory\n local b=emu.memType.snesSaveRam;local w=emu.memType.snesWorkRam\n local function word(a,mt) return emu.read(a,mt)+256*emu.read(a+1,mt) end\n local row={' + str(json.dumps(label)) + ",s['ppu.frameCount'] or -1,\n  s['cpu.k'] or -1,s['cpu.pc'] or -1,s['cpu.d'] or -1,\n  s['cpu.a'] or -1,s['cpu.x'] or -1,s['cpu.y'] or -1,\n  s['cpu.sp'] or -1,s['cpu.ps'] or -1,\n  word(0x175c,w),word(0x175e,w),word(0x1760,w),word(0x1764,w),\n  word(0x12002,b),word(0x12004,b),word(0x1200a,b),\n  word(0x12430,b),word(0x12432,b),\n  word(0x1415a,b),word(0x1417e,b),word(0x141a2,b),\n  word(0x141c6,b),word(0x141ea,b),word(0x1420e,b),\n  word(0x41415a,m),word(0x41417e,m),word(0x4141a2,m),\n  word(0x4141c6,m),word(0x4141ea,m),word(0x41420e,m),\n  word(0x7e0410,m),word(0x7e0412,m),word(0x7e0418,m),\n  emu.read(0x7e50aa,m),emu.read(0x7e50ab,m),\n  word(0x7e50c6,m),word(0x7e50c8,m),\n  s['cart.coprocessor.cpu.k'] or -1,s['cart.coprocessor.cpu.pc'] or -1,\n  s['cart.coprocessor.cpu.d'] or -1,s['cart.coprocessor.cpu.sp'] or -1}\n for i=1,#row do row[i]=tostring(row[i]) end\n _s8_protocol_trace:write(table.concat(row,'|'),'\\n');_s8_protocol_trace:flush()\nend,emu.callbackType.exec," + str(at) + ',' + str(at) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
            stream_trace_stage = int(os.environ.get('S8_STREAM_TRACE_STAGE', '26'))
            stream_trace_min_spawn = int(os.environ.get('S8_STREAM_TRACE_MIN_SPAWN', '0'))
            script = script + ''.join(['\nlocal _s8_stream_trace=assert(io.open(', str(json.dumps(streaming_trace_path)), ",'w'))\nlocal _s8_stream_hits={}\nlocal _s8_stream_trace_stage=", str(stream_trace_stage), '\nlocal _s8_stream_trace_min_spawn=', str(stream_trace_min_spawn), '\nlocal function _s8_stream_probe(label)\n local m=emu.memType.snesMemory\n local function b(a) return emu.read(a,m) end\n local function w(a) return b(a)+256*b(a+1) end\n if w(', str(symbols.get('Game_StageIndex', 8267604)), ')~=_s8_stream_trace_stage\n  or b(', str(symbols.get('Spawn_Index', 8279296)), ")<_s8_stream_trace_min_spawn then return end\n local n=_s8_stream_hits[label] or 0\n if n>=120 then return end\n _s8_stream_hits[label]=n+1\n local s=emu.getState();local mask=0;local q={}\n for i=0,7 do\n  local t=b(0x7e0484+i*8);q[i+1]=tostring(t)\n  if t%128>=64 then mask=mask+2^i end\n end\n local row={label,s['ppu.frameCount'] or -1,w(0x7e2750),w(0x7e2752),\n  w(0x7e2754),b(0x7e275f),w(0x7e5000),b(0x7e5002),w(0x7e5023),\n  b(0x7e5001),b(0x7fb224),b(0x7fb225),b(0x7fb226),b(0x7fb234),\n  b(0x7fb238),b(0x7fb239),b(0x7ee0a0),b(0x7ee0a1),b(0x7ee0a2),\n  b(0x7ee0a3),b(0x7ee0ba),b(0x7ee0c0),w(0x7e264e),w(0x7e2658),\n  b(0x7e265e),w(0x7e0478),w(0x7e047a),w(0x7e047e),mask,\n  w(0x7e1760),b(0x7e587d),s['cpu.k'] or -1,s['cpu.pc'] or -1,\n  s['cpu.sp'] or -1,b(", str(symbols.get('Spawn_Index', 8279296)), '),\n  b(', str(symbols.get('Spawn_GroupMin', 8279297)), '),\n  b(', str(symbols.get('Spawn_GroupMax', 8279298)), '),\n  b(', str(symbols.get('Spawn_Waiting', 8279299)), '),\n  b(', str(symbols.get('Msu1_StreamBusy', 8257536)), '),\n  b(', str(symbols.get('Spawn_ScratchKind', 8280211)), '),\n  b(', str(symbols.get('Spawn_ScratchRosterIdx', 8280231)), '),\n  w(', str(symbols.get('Spawn_ScratchSlotOfs', 8280239)), '),\n  w(', str(symbols.get('Screen_PosX', 8263164)), '),\n  w(', str(symbols.get('Stage_TrueMaxX', 8267606)), "),table.concat(q,',')}\n for i=1,#row do row[i]=tostring(row[i]) end\n _s8_stream_trace:write(table.concat(row,'|'),'\\n');_s8_stream_trace:flush()\nend\n"])
            stream_labels = ('Game_State_Play', 'StageWater_Begin', 'StageWater_Begin__active', 'StageWater_End', 'StageWater_End__done', 'StageWater_End__restore', 'StageFp_BG2PlayDispatch', 'StageFp_BG2PlayDispatch__free', 'StageFp_BG2PlayDispatch__resume', 'StageFp_BG2PlayDispatch__done', 'StageFp_BG2Resolve', 'StageFp_BG2Resolve__row', 'StageFp_BG2Seek', 'StageFp_BG2Seek__busy', 'StageFp_HostHasFree', 'Core_StreamScroll_Play', 'Core_StreamScrollFp_Play', 'Core_StreamScrollFp_ResolveRows', 'Core_StreamScrollFp_ResolveRows__row', 'Core_Dma_HasFreeSlot', 'Core_Dma_HasFreeSlot__scan', 'Core_Dma_HasFreeSlot__found', 'Core_Dma_ProcessQueue', 'Core_Nmi_Play', 'Core_Nmi_Play__frame_skipped', 'Core_Nmi_Play__do_commit', 'Core_Nmi_Play__done', 'StageWater_Nmi', 'Spawn_Play', 'Spawn_Play__wait_check_done', 'Spawn_Play__group_ok', 'Spawn_Play__active', 'Spawn_Play__compare_trigger', 'Spawn_Play__triggered', 'Spawn_Play__find_slot_none', 'Spawn_Play__gate_busy', 'Spawn_Play__not_yet', 'Spawn_Play__advance')
            for label in stream_labels:
                address = symbols.get(label)
                if not address is None:
                    at = lorom_offset(address)
                    script = script + ('\nemu.addMemoryCallback(function()\n _s8_stream_probe(' + str(json.dumps(label)) + ')\nend,emu.callbackType.exec,' + str(at) + ',' + str(at) + ',emu.cpuType.snes,emu.memType.snesPrgRom)\n')
    visual_path = os.environ.get('S8_VISUAL_ADMISSION_TRACE')
    if visual_path:
        address = symbols['SourceVisual_RenderCurrent__fail']
        script += f'''
local _byor_visual_seen={{}}
emu.addMemoryCallback(function()
 local mt=emu.memType.snesMemory;local s=emu.getState()
 local function byte(a) return emu.read(a,mt) end
 local function word(a) return byte(a)+256*byte(a+1) end
 if word({symbols['Game_State']})~=0 then return end
 local error=byte({symbols['SourceVisual_Error']})
 if error==0x27 then return end -- ordinary resource transfer pending
 local stage=word({symbols['Game_StageIndex']})
 local k={{byte(0x7E4A04),byte(0x7E4A05),byte(0x7E4A06),byte(0x7E4A07)}}
 local key=stage..':'..table.concat(k,':')..':'..error
 if _byor_visual_seen[key] then return end
 _byor_visual_seen[key]=true
 local d=s['cpu.d'] or 0;local actor=0x7E0000+d
 local f=assert(io.open({json.dumps(str(Path(visual_path).resolve()).replace(chr(92), '/'))},'a'))
 f:write(table.concat({{stage,s['ppu.frameCount'] or 0,k[1],k[2],k[3],k[4],error,
 word(0x7E4B54),word(0x7E53A0),word(actor+{symbols['CHAR_POS_X']}),
 word(actor+{symbols['CHAR_POS_Y']})}},'|'),'\\n')
 f:close()
end,emu.callbackType.exec,{lorom_offset(address)},{lorom_offset(address)},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    fault_path = os.environ.get('S8_BIND_FAULT_TRACE')
    if fault_path and world_symbols:
        for label in ('S6Bridge_Import__numeric', 'S6Bridge_Import__height_bad'):
            address = world_symbols.get(label)
            if address is None:
                continue
            script += f'''
local _byor_fault_seen_{label}={{}}
emu.addMemoryCallback(function()
 local s=emu.getState();local mt=emu.memType.snesMemory
 local function word(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
 local x=s['cpu.x'] or 0;local stage=word({symbols['Game_StageIndex']})
 local key=tostring(stage)..':'..tostring(x)
 if _byor_fault_seen_{label}[key] then return end
 _byor_fault_seen_{label}[key]=true
 local actor=0x7E0A00+x
 local f=assert(io.open({json.dumps(str(Path(fault_path).resolve()).replace(chr(92), '/'))},'a'))
 f:write(table.concat({{'{label}',stage,x,s['cpu.d'] or 0,s['cpu.a'] or 0,
 word(actor+{symbols['CHAR_POS_X']}),word(actor+{symbols['CHAR_POS_Y']}),
 word(actor+{symbols['CHAR_THROW_ZPOS']}),word(actor+{symbols['CHAR_THROW_ZVEL']}),
 word(0x7E550F+x),word(0x7E5511+x),word(0x7E1778),word(0x7E177C)}},'|'),'\\n')
 f:close()
end,emu.callbackType.exec,{lorom_offset(address)},{lorom_offset(address)},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    noncombat_path = os.environ.get('BYOR_NONCOMBAT_TRACE')
    if noncombat_path:
        script += f"""
local _byor_none_field=0
emu.addEventCallback(function()
 _byor_none_field=_byor_none_field+1
 if _byor_none_field%30~=0 then return end
 local mt=emu.memType.snesMemory
 local function byte(a) return emu.read(a,mt) end
 local function word(a) return byte(a)+256*byte(a+1) end
 for slot=1,5 do
  local stride=slot*{symbols['CHAR_ZP_LEN']}
  local actor=0x7E0000+{symbols['PlayerEntity_DpBase']}+stride
  if byte(actor+{symbols['CHAR_INPUT_DRIVEN']})=={symbols['CHAR_INPUT_DRIVEN_NONCOMBAT']} then
   local f=assert(io.open({json.dumps(str(Path(noncombat_path).resolve()).replace(chr(92), '/'))},'a'))
   f:write(table.concat({{"NONE",_byor_none_field,word({symbols['Game_StageIndex']}),slot,
    word(actor+{symbols['OOP_SELF_NUM_OFS']}),byte(actor+{symbols['CHAR_ROSTER_INDEX']}),
    word(actor+{symbols['CHAR_POS_X']}),word({symbols['ActorBehavior_Alive']}+stride),
    word({symbols['ActorBehavior_Ticks']}+stride)+65536*word({symbols['ActorBehavior_Ticks']}+stride+2),
    word({symbols['ActorBehavior_Fault']}+stride),byte(actor+{symbols['CHAR_SELECTED']}),
    byte(actor+{symbols['CHAR_FRAME_INDEX']}),word({symbols['ActorBehavior_SourceHealth']}+stride),
    word({symbols['Nmi_FrameCounter']})}},'|'),'\\n');f:close()
  end
 end
end,emu.eventType.endFrame)
"""
    return script

@contextmanager
def traversal_session(symbols, report, open_session, *, trace_runtime, trace_bind, trace_sparse, trace_player_move, trace_ownership, trace_pc_only, trace_player_lifecycle):
    from unittest.mock import patch
    from actor_s5_entity_fixture import symbols as parse_symbols
    folder = Path(tempfile.mkdtemp(prefix='s8-spawn-traversal-'))
    journal = folder / 'completed-records.txt'
    journal.touch()
    script = folder / 'admissions.lua'
    world_symbols = None
    candidate = os.environ.get('BOR_TEST_ROM')
    world_sym = Path(candidate).with_name('world.sym') if candidate else None
    if world_sym:
        if world_sym.is_file():
            world_symbols = parse_symbols(world_sym)
            worker_sym = world_sym.with_name('worker.sym')
            if worker_sym.is_file():
                world_symbols.update(parse_symbols(worker_sym))
    script.write_text(traversal_script(symbols, journal, trace_runtime=trace_runtime, trace_bind=trace_bind, trace_sparse=trace_sparse, trace_player_move=trace_player_move, trace_ownership=trace_ownership, trace_pc_only=trace_pc_only, trace_player_lifecycle=trace_player_lifecycle, world_symbols=world_symbols), encoding='utf-8')
    if trace_ownership:
        report['spawn_traversal']['ownership_fault_trace'] = str(journal.with_suffix('.ownership-fault-trace.txt'))
    report['spawn_traversal']['journal'] = str(journal)
    if trace_player_lifecycle:
        report['spawn_traversal']['player_lifecycle_trace'] = str(journal.with_suffix('.player-lifecycle-trace.txt'))
    if trace_pc_only:
        report['spawn_traversal']['protocol_call_trace'] = str(journal.with_suffix('.protocol-call-trace.txt'))
        report['spawn_traversal']['streaming_state_trace'] = str(journal.with_suffix('.streaming-state-trace.txt'))
        report['spawn_traversal']['worker_error_pc_trace'] = str(journal.with_suffix('.worker-error-pc-trace.txt'))
    report['spawn_traversal']['header_write_trace'] = str(journal.with_suffix('.header-write-trace.txt'))
    report['spawn_traversal']['initial_actor_journal'] = str(journal.with_suffix('.initial-ai.txt'))
    report['spawn_traversal']['player_move_trace'] = str(journal.with_suffix('.player-move-trace.txt'))
    if trace_player_move:
        report['spawn_traversal']['sa1_player_move_trace'] = str(journal.with_suffix('.sa1-player-move.txt'))
        report['spawn_traversal']['sa1_player_move_write_trace'] = str(journal.with_suffix('.sa1-player-move-writes.txt'))
        report['spawn_traversal']['sa1_player_move_window_write_trace'] = str(journal.with_suffix('.sa1-player-move-window-writes.txt'))
    if trace_bind:
        if world_symbols:
            report['spawn_traversal']['bind_trace'] = str(journal.with_suffix('.bind-trace.txt'))
            report['spawn_traversal']['native_hit_trace'] = str(journal.with_suffix('.native-hit-trace.txt'))
    original = subprocess.Popen

    def launch(argv, **kwargs):
        if '--mcp' not in argv:
            raise AssertionError('unexpected process in traversal session')
        return original(*([*argv, '--debug.scriptwindow.allowioosaccess=true', str(script)],), **{**kwargs})
    session = open_session(__file__, stderr_log=str(folder / 'mesen.stderr.log'))
    try:
        with patch('subprocess.Popen', launch):
            m = session.__enter__()
        status = journal.with_suffix('.status')
        report['spawn_traversal']['observer_status_path'] = str(status)
        report['spawn_traversal']['stderr_path'] = str(folder / 'mesen.stderr.log')
        if not status.exists() or status.read_text() != 'READY':
            raise AssertionError('traversal Lua observer failed initialization; inspect session stderr')
        report['spawn_traversal']['cold_start'] = 'fresh McpSession process; redundant helper reset suppressed'
        with patch.object(m, 'reset_emulator', lambda: None):
            yield (m, journal)
    finally:
        if 'm' in locals():
            try:
                m.release_input(port=0)
            except Exception:
                pass
        session.__exit__(None, None, None)

def traversal_plan(build, entries, start_ordinal=0):
    from compiler import Source
    from compiler import stage
    from compiler import model_catalog
    from production_campaign import compile_queues
    entries = entries[start_ordinal:]
    configs = [build.STAGE_CONFIGS[value] for kind, value, _ in entries if kind == 'stage']
    blobs = compile_queues(configs, build.ROSTER_CONFIGS)
    source = Source(configs[0]['pak'])
    models = model_catalog(source)
    expected = []
    for kind, physical, _ in entries:
        if not kind != 'stage':
            cfg = build.STAGE_CONFIGS[physical]
            ir = stage(source, cfg['source_level'])
            prefix = len(ir.environment.get('hole', []))
            blob = blobs[cfg['spawn']]
            for index in range(len(blob) // 10):
                event = ir.queue[index - prefix] if index >= prefix else None
                spawn = event is not None and event.kind == 'spawn'
                record = blob[index * 10:(index + 1) * 10]
                model = models[event.character.casefold()] if spawn else None
                expected.append(dict(stage=physical, index=index, source_queue_index=index - prefix, record=record.hex(), spawn=spawn, source_model=event.character if spawn else None, source_type=model['entity']['type'] if spawn else None, boss=bool(event.boss) if spawn else None, source_definition=models[event.character.casefold()]['source_path'] if spawn else None, roster=record[9] if spawn else None))
    expected_spawn_count = sum((row['spawn'] for row in expected))
    if start_ordinal == 0:
        contract = {0: 545, 1: 614, 2: 753, 3: 166}[configs[0]['source_set_id']]
        if expected_spawn_count != contract:
            raise AssertionError(f'source spawn contract changed: expected {contract}')
    return expected

def read_traversal(journal):
    names = ('campaign', 'stage', 'index', 'offset', 'kind', 'exists', 'hp', 'mode', 'roster', 'object_slot', 'object_num')
    rows = []
    for line in journal.read_text().splitlines():
        values = list(map(int, line.split()))
        if len(values) != 26:
            raise AssertionError('incomplete traversal observer record')
        rows.append(dict(zip(names, values[:11]), record=bytes(values[11:21]).hex(), idle_frames=values[21], frame=values[22], load_result=values[23], nmi=values[24], boss=values[25]))
    return rows

def validate_admission(actual, expected):
    if not actual['campaign'] != 3:
        if any((actual[k] != expected[k] for k in ('stage', 'index', 'record'))):
            raise AssertionError('traversal source queue order/bytes mismatch')
        if not expected['spawn']:
            return None
        base = actual['exists'] == 1 and (actual['roster'] == expected['roster'] and (actual['idle_frames'] > 0 and (actual['load_result'] != 0 and actual['boss'] == int(expected['boss']))))
        source_type = expected['source_type']
        if source_type == 'enemy':
            initialized = actual['hp'] > 0 and actual['mode'] in (2, 4)
        elif source_type == 'steamer':
            initialized = actual['hp'] > 0 and actual['mode'] == 5
        elif source_type == 'item':
            initialized = actual['hp'] > 0 and actual['mode'] == 3
        elif source_type == 'obstacle':
            record_flags = bytes.fromhex(expected['record'])[6]
            subtype = record_flags >> 5 & 3
            if subtype == 3:
                initialized = actual['mode'] == 5
            else:
                initialized = actual['hp'] > 0 and actual['mode'] == 3
        else:
            initialized = actual['mode'] in (3, 5, 6)
        if base:
            if not initialized:
                raise AssertionError('traversal completed spawn identity/model initialization mismatch')
            return None
        raise AssertionError('traversal completed spawn identity/model initialization mismatch')
    raise AssertionError('traversal source queue order/bytes mismatch')

def run(args, report):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(ROOT))
    from _harness import Reporter
    from _harness import exact_input_edge
    from _harness import open_session
    from _harness import pasm_constant
    from _harness import pasm_constant_in
    from _harness import read_block
    from _harness import run_frames_exact
    from _harness import rom_path
    import build_rom as build
    import game_bor_startup_select as startup
    import game_g15_stage1_campaign as legal
    import game_g15_l5_campaign_rugal as l5
    import game_g15_o3_campaign_ending as o3
    r = Reporter('S8-' + args.mode.upper(), kind='GATE')
    report['checks'] = r.results
    report['resource_policy'] = dict(msu_busy_fields=0, msu_busy_runs=[], msu_busy_open_start=None, visual_busy_errors={})

    def require(name, condition):
        if not r.check(name, condition):
            raise AssertionError(name)

    def u8(addr):
        return read_block(m, addr, 32)[0]

    def u16(addr):
        return int.from_bytes(bytes(read_block(m, addr, 32)[:2]), 'little')

    def s16(addr):
        return traversal_signed16(u16(addr))

    def u32(addr):
        return int.from_bytes(bytes(read_block(m, addr, 32)[:4]), 'little')

    def runtime_diagnostics():
        host = bytes(read_block(m, 8263504, 32))
        relay = bytes(read_block(m, 73728, 32, mem_type='snesSaveRam'))
        events = bytes(read_block(m, 74800, 32, mem_type='snesSaveRam'))
        remove_control = bytes(read_block(m, 74816, 32, mem_type='snesSaveRam')[:8])
        stage_environment = bytes(read_block(m, 74784, 32, mem_type='snesSaveRam')[:16])
        worker_world = bytes(read_block(m, 71424, 128, mem_type='snesSaveRam'))
        host_world = bytes(read_block(m, 8263424, 128))
        remove_debug = bytes(read_block(m, 76880, 32, mem_type='snesSaveRam'))
        worker_contexts = []
        bridge_rows = []
        for slot in range(6):
            context = bytes(read_block(m, 71936 + slot * 256, 256, mem_type='snesSaveRam'))
            metadata = bytes(read_block(m, 73984 + slot * 133, 133, mem_type='snesSaveRam'))
            bridge = bytes(read_block(m, symbols['StageEnv_Actors'] + slot * 133, 74))
            bridge_rows.append(dict(slot=slot, policy=bridge[64], exists=bridge[65], context=int.from_bytes(bridge[68:70], 'little'), target=int.from_bytes(bridge[70:72], 'little'), worker_policy=metadata[64], worker_exists=metadata[65], worker_context=int.from_bytes(metadata[68:70], 'little')))
            worker_contexts.append(dict(*(), **{'slot': slot, 'dp': 6400 + slot * 256, 'selected': context[27], 'facing': context[26], 'attack_frames': context[34], 'hit_applied': context[50], 'attack_variant': context[77], 'x': int.from_bytes(context[20:22], 'little', signed=True), 'y': int.from_bytes(context[22:24], 'little', signed=True), 'source_time_low': int.from_bytes(context[208:210], 'little'), 'source_time_high': int.from_bytes(context[210:212], 'little'), 'nextthink_low': int.from_bytes(context[232:234], 'little'), 'nextthink_high': int.from_bytes(context[234:236], 'little'), 'speed20': int.from_bytes(context[198:200], 'little', signed=True), 'ai_features': int.from_bytes(context[168:170], 'little'), 'idle_role': int.from_bytes(context[56:58], 'little'), 'attack_role': int.from_bytes(context[160:162], 'little'), 'role': int.from_bytes(context[228:230], 'little'), 'frame': int.from_bytes(context[6:8], 'little'), 'world': int.from_bytes(context[54:56], 'little'), 'target_player0': int.from_bytes(context[68:70], 'little'), 'target_player1': int.from_bytes(context[70:72], 'little'), 'target_opponent0': int.from_bytes(context[78:80], 'little'), 'target_opponent1': int.from_bytes(context[80:82], 'little'), 'policy': context[224], 'driver': context[230], 'error': int.from_bytes(context[252:254], 'little'), 'hp': int.from_bytes(context[240:242], 'little'), 'exists': int.from_bytes(context[246:248], 'little'), 'bridge_policy': metadata[64], 'metadata_exists': metadata[65]}))
        completed_ticks = int.from_bytes(relay[4:6], 'little')
        recent_inputs = []
        for age in range(1, min(completed_ticks, 65)):
            row_index = completed_ticks - age & 511
            row = bytes(read_block(m, 86016 + row_index * 8, 32, mem_type='snesSaveRam')[:8])
            recent_inputs.append(dict(index=row_index, p1_press=int.from_bytes(row[0:2], 'little'), p1_trigger=int.from_bytes(row[2:4], 'little'), p2_press=int.from_bytes(row[4:6], 'little'), p2_trigger=int.from_bytes(row[6:8], 'little')))
        event_rows = []
        event_tail = int.from_bytes(events[2:4], 'little')
        event_head = int.from_bytes(events[0:2], 'little')
        event_count = min(event_head - event_tail & 65535, 128)
        for offset in range(event_count):
            sequence = event_tail + offset & 65535
            row = bytes(read_block(m, 74832 + (sequence & 127) * 16, 32, mem_type='snesSaveRam')[:16])
            event_rows.append(dict(sequence=int.from_bytes(row[0:2], 'little'), kind=int.from_bytes(row[2:4], 'little'), tick=int.from_bytes(row[4:6], 'little') | int.from_bytes(row[6:8], 'little') << 16, source_d=int.from_bytes(row[8:10], 'little'), x=int.from_bytes(row[10:12], 'little'), y=int.from_bytes(row[12:14], 'little'), extra=int.from_bytes(row[14:16], 'little')))
        recent_event_rows = []
        for age in range(1, min(event_head, 129)):
            sequence = event_head - age & 65535
            row = bytes(read_block(m, 74832 + (sequence & 127) * 16, 32, mem_type='snesSaveRam')[:16])
            recent_event_rows.append(dict(sequence=int.from_bytes(row[0:2], 'little'), kind=int.from_bytes(row[2:4], 'little'), tick=int.from_bytes(row[4:6], 'little') | int.from_bytes(row[6:8], 'little') << 16, source_d=int.from_bytes(row[8:10], 'little'), x=int.from_bytes(row[10:12], 'little'), y=int.from_bytes(row[12:14], 'little'), extra=int.from_bytes(row[14:16], 'little')))
        bound_row = int.from_bytes(host[2:4], 'little')
        bound_dp = int.from_bytes(host[4:6], 'little')
        bound_roster = int.from_bytes(host[8:10], 'little')
        bind_actor = None
        bind_worker_context = None
        bind_environment = None
        if 0 <= bound_row:
            if bound_row < symbols['CHAR_ZP_LEN'] * 6:
                actor = bytes(read_block(m, 8260096 + bound_row, symbols['CHAR_ZP_LEN']))
                bind_actor = dict(row=bound_row, roster=actor[symbols['CHAR_ROSTER_INDEX']], driven=actor[symbols['CHAR_INPUT_DRIVEN']], selected=actor[symbols['CHAR_SELECTED']], hp=actor[symbols['CHAR_HP']], x=int.from_bytes(actor[symbols['CHAR_POS_X']:symbols['CHAR_POS_X'] + 2], 'little', signed=True), y=int.from_bytes(actor[symbols['CHAR_POS_Y']:symbols['CHAR_POS_Y'] + 2], 'little', signed=True), throw_zpos=int.from_bytes(actor[symbols['CHAR_THROW_ZPOS']:symbols['CHAR_THROW_ZPOS'] + 2], 'little', signed=True), throw_zvel=int.from_bytes(actor[symbols['CHAR_THROW_ZVEL']:symbols['CHAR_THROW_ZVEL'] + 2], 'little', signed=True))
        else:
            bound_row
        if 6400 <= bound_dp:
            if bound_dp < 7936:
                context = bytes(read_block(m, 8257536 + bound_dp, 256))
                bind_worker_context = dict(dp=bound_dp, roster=context[symbols['CHAR_ROSTER_INDEX']], x=int.from_bytes(context[20:22], 'little', signed=True), y=int.from_bytes(context[22:24], 'little', signed=True), driver=context[230], error=int.from_bytes(context[252:254], 'little'))
                env = bytes(read_block(m, symbols['StageEnv_Actors'] + bound_row // symbols['CHAR_ZP_LEN'] * 133, 133))
                bind_environment = dict(row=bound_row, base_fraction=int.from_bytes(env[0:2], 'little'), base_integer=int.from_bytes(env[2:4], 'little', signed=True))
        else:
            bound_dp
        diagnostics = dict(*(), **{'host_mode': int.from_bytes(host[16:18], 'little'), 'persistent_owner': int.from_bytes(host[14:16], 'little'), 'host_error': int.from_bytes(host[20:22], 'little'), 'bind_row': bound_row, 'bind_dp': bound_dp, 'bind_model_record': int.from_bytes(host[6:8], 'little'), 'bind_roster': bound_roster, 'bind_actor': bind_actor, 'bind_worker_context': bind_worker_context, 'bind_environment': bind_environment, 'worker_target_ticks': int.from_bytes(relay[2:4], 'little'), 'worker_completed_ticks': int.from_bytes(relay[4:6], 'little'), 'input_mailboxes': bytes(read_block(m, 73760, 32, mem_type='snesSaveRam')[:8]).hex(), 'recent_input_records': recent_inputs, 'pending_event_records': event_rows, 'recent_event_records': recent_event_rows, 'native_prop_mask': list(read_block(m, 77056, 32, mem_type='snesSaveRam')[:6]), 'native_prop_event_counts': [int.from_bytes(read_block(m, address, 32, mem_type='snesSaveRam')[:2], 'little') for address in (77072, 77074, 77076, 77078)], 'actor_invuln_frames': list(read_block(m, 8280240, 32)[:6]), 'last_native_prop_query': dict(x=int.from_bytes(read_block(m, 8263528, 32)[:2], 'little', signed=True), y=int.from_bytes(read_block(m, 8263530, 32)[:2], 'little', signed=True)), 'worker_fault_code': int.from_bytes(relay[8:10], 'little'), 'worker_error': relay[10], 'mutation_fence_state': relay[12], 'snapshot_requested': relay[6], 'snapshot_published': relay[7], 'event_head': int.from_bytes(events[0:2], 'little'), 'event_tail': int.from_bytes(events[2:4], 'little'), 'event_overflow': int.from_bytes(events[4:6], 'little'), 'remove_request': int.from_bytes(remove_control[0:2], 'little'), 'remove_ack': int.from_bytes(remove_control[2:4], 'little'), 'remove_handle': int.from_bytes(remove_control[4:6], 'little'), 'remove_apply_tick': int.from_bytes(remove_control[6:8], 'little'), 'worker_stage_environment': dict(camera_x=int.from_bytes(stage_environment[0:2], 'little', signed=True), hole_count=int.from_bytes(stage_environment[2:4], 'little'), hole_positions=[int.from_bytes(stage_environment[i:i + 2], 'little', signed=True) for i in (4, 6, 8)]), 'remove_command_debug': remove_debug.hex(), 'remove_command_debug_words': [int.from_bytes(remove_debug[i:i + 2], 'little') for i in range(0, 28, 2)], 'worker_fault_environment': [int.from_bytes(remove_debug[i:i + 2], 'little') for i in range(16, 24, 2)], 'worker_fault_fence': int.from_bytes(remove_debug[24:26], 'little'), 'worker_fault_policy': int.from_bytes(remove_debug[26:28], 'little'), 'worker_world': dict(world_refs=[int.from_bytes(worker_world[i:i + 2], 'little') for i in (68, 70, 78, 80)], host_world_refs=[int.from_bytes(host_world[i:i + 2], 'little') for i in (68, 70, 78, 80)], random_state=worker_world[0:16].hex()), 'source_tick': u16(8263484), 'game_tick_commit': u16(symbols['S6Game_TickCommit']), 'game_tick_commit_hi': u16(symbols['S6Game_TickCommit'] + 2), 'campaign_id': u8(symbols['Game_CampaignId']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'elapsed_field_accumulator': u16(8263546), 'last_committed_field': u16(symbols['S6Game_LastField']), 'field_phase': u8(8263548), 'worker_contexts': worker_contexts, 'bridge_rows': bridge_rows, 'relay_probe': dict(save_10000=bytes(read_block(m, 65536, 32, mem_type='snesSaveRam')[:16]).hex(), save_12000=bytes(read_block(m, 73728, 32, mem_type='snesSaveRam')[:16]).hex(), scpu_bus=bytes(read_block(m, 4268032, 32, mem_type='snesMemory')[:16]).hex(), sa1_bus=bytes(read_block(m, 4268032, 32, mem_type='sa1Memory')[:16]).hex()), 'source_visual_error': u8(symbols['SourceVisual_Error']), 'source_visual_last_error': u8(symbols['SourceVisual_DebugLastError']), 'source_visual_calls': u16(symbols['SourceVisual_CallCount']), 'source_visual_presentations': u16(symbols['SourceVisual_RenderPassCount']), 'source_visual_debug': bytes(read_block(m, 8276480, 128)).hex(), 'source_visual_queue_debug': bytes(read_block(m, 8275416, 32)[:8]).hex(), 'nmi_field': u16(symbols['Nmi_FrameCounter'])})
        for cpu in ('Snes', 'Sa1'):
            try:
                diagnostics[cpu.lower() + '_cpu'] = m.get_cpu_state(cpu)
            except Exception as error:
                diagnostics[cpu.lower() + '_cpu_unavailable'] = str(type(error).__name__) + ': ' + str(error)
        return diagnostics
    gs = lambda name: pasm_constant_in('src/core/game_state.pasm', name)
    selected = gs('BorSet_Selected')
    credited = gs('BorSet_CompletionCredited')
    times = pasm_constant_in('src/core/options.pasm', 'Bor_TimesCompleted')
    complete_active = pasm_constant('StageComplete_Active')
    complete_advances = pasm_constant('StageComplete_AdvanceCount')
    selected_rom = Path(rom_path(__file__)).resolve()
    symbols = build._load_poppy_symbols(str(ROOT / 'src/main.sym'))
    candidate_symbols = selected_rom.with_name('world.sym')
    if not candidate_symbols.is_file():
        candidate_symbols = ROOT / 'build/s8_normal_sa1_candidate_final/world.sym'
    if candidate_symbols.exists():
        linked = build._load_poppy_symbols(str(candidate_symbols))
        symbols.update({name: address for name, address in linked.items() if name.startswith(('S6Normal_', 'S6Host_', 'S6Game_', 'S7Resident_'))})
    pos_y, max_y, min_x = (symbols[n] for n in ('Screen_PosY', 'Screen_MaxY', 'Screen_MinX'))
    source_set = getattr(args, 'source_set', 'Normal')
    cid = 'BOR_ORIGINAL' if args.mode == 'easy' else (
        {'Easy': 'BOR_ORIGINAL', 'Normal': 'BOR_NORMAL_1A_INTERNAL', 'Hard': 'BOR_HARD', 'Bonus': 'BOR_BONUS'}[source_set])
    report['source_set'] = 'Easy' if args.mode == 'easy' else source_set
    campaign_id = 3
    entries = build.CAMPAIGN_ENTRY_MAPS[cid]
    authored = build.CAMPAIGN_CONFIGS[cid]['entries']
    report['expected_entries'] = entries
    report['next_flags'] = [int(e['next_after']) for e in authored]
    completion_flags = build.CAMPAIGN_CONFIGS[cid]['completion_flags']
    report['completion_flags'] = completion_flags
    report['completion_policy'] = build.CAMPAIGN_CONFIGS[cid]['completion_policy']
    require('compiler exposes all source typed entries', len(entries) == len(authored) and len(authored) == (2 if source_set == 'Bonus' else 16))
    generated = (ROOT / 'tools/audio/campaign_config.pasm').read_text(encoding='ascii')

    def table(label):
        match = re.search('^' + str(re.escape(label)) + ':\\s*\\n\\s*\\.db\\s+([^\\n]+)', generated, re.M)
        if not match:
            raise AssertionError('missing generated table: ' + label)
        return [value.strip() for value in match[1].split(',')]
    set_index = 0 if args.mode == 'easy' else {'Easy': 0, 'Normal': 1, 'Hard': 2, 'Bonus': 3}[source_set]
    require('generated release gate permits selected set', table('BorSet_ContentAvailable')[set_index] == '1')
    require('generated selected campaign mapping matches ABI', table('BorSet_CampaignMap')[set_index] == 'CAMPAIGN_BOR_NORMAL_DEV')
    label = {0: 'Bor', 1: 'BorNormalDev', 2: 'BorHard', 3: 'BorBonus'}[set_index]
    require('generated next flags match source compiler', [int(v) for v in table('Campaign_' + str(label) + '_NextFlags')] == report['next_flags'])
    require('generated completion flags match explicit compatibility policy', [int(v) for v in table('Campaign_' + str(label) + '_CompleteFlags')] == completion_flags)
    if source_set != 'Bonus':
        require('source tail is 6B -> RUGAL -> 6C -> ENDING', entries[-4][0] == 'stage' and (Path(entries[-4][2].replace('\\', '/')).stem in ('6B', '6BEASY', '6BHARD') and (entries[-3][2] == 'RUGAL' and (entries[-2][0] == 'stage' and (Path(entries[-2][2].replace('\\', '/')).stem in ('6C', '6CEASY', '6CHARD') and (entries[-1][2] == 'ENDING' and authored[-2]['next_after']))))))
    report['rom_path'] = str(selected_rom)
    report['msu_path'] = str(selected_rom.with_suffix('.msu'))
    for path in (selected_rom, selected_rom.with_suffix('.msu'), ROOT / 'src/main.sym', ROOT / 'tools/audio/campaign_config.pasm'):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1048576), b''):
                digest.update(chunk)
        report.setdefault('artifacts', {})[str(path.resolve())] = digest.hexdigest()
    traversal = bool(getattr(args, 'spawn_traversal', False))
    if traversal:
        require(f'spawn traversal requires full {source_set}', args.mode != 'easy')
        plan = traversal_plan(build, entries, args.debug_start_ordinal)
        report['spawn_traversal'] = dict(expected=plan, completed=[], unlink_accelerations=[], prop_interactions=[], pickup_interactions=[], combat_interactions=[], initial_ai_combat_targets=[], controller_probe=[], input_trace=[], jump_inputs=[], status='INCOMPLETE', scope='all source queue admissions; each initial AI takes observed real damage before sequenced worker unlink')
    session = traversal_session(symbols, report, open_session, trace_runtime=getattr(args, 'trace_runtime', False), trace_bind=getattr(args, 'trace_bind', False), trace_sparse=getattr(args, 'trace_sparse', False), trace_player_move=getattr(args, 'trace_player_move', False), trace_ownership=getattr(args, 'trace_ownership', False), trace_pc_only=getattr(args, 'trace_pc_only', False), trace_player_lifecycle=getattr(args, 'trace_player_lifecycle', False)) if traversal else open_session(__file__)
    with session as opened:
        m, journal = opened if traversal else (opened, None)
        admitted = {}
        retirement_pending = {}
        prop_hp_seen = {}
        pickup_type_seen = {}
        combat_hp_seen = {}
        prop_target_last = None
        prop_bypass_directions = {}
        initial_ai_reported = set()
        observer_last_status = None
        observer_last_change_field = 0
        observer_last_stage = None
        observer_skipped_prefix = None
        controller_probe_path = journal.with_suffix('.controller.json') if traversal else None
        if traversal:
            report['spawn_traversal']['controller_probe_path'] = str(controller_probe_path)

        def harvest():
            nonlocal observer_last_change_field, observer_last_status, observer_skipped_prefix
            if not not traversal:
                status = journal.with_suffix('.status').read_text()
                report['spawn_traversal']['observer_status'] = status
                if status != observer_last_status:
                    observer_last_status = status
                    observer_last_change_field = report['frames_sampled']
                if status.startswith('ERROR'):
                    raise AssertionError('traversal Lua callback failed: ' + status)
                rows = read_traversal(journal)
                if args.debug_start_ordinal:
                    if observer_skipped_prefix is None:
                        target_stage = plan[0]['stage']
                        first_target = next((i for i, row in enumerate(rows) if row['stage'] == target_stage), None)
                        if not first_target is None:
                            observer_skipped_prefix = first_target
                            rows = rows[observer_skipped_prefix:]
                            completed = report['spawn_traversal']['completed']
                            for actual in rows[len(completed):]:
                                completed.append(actual)
                                index = len(completed) - 1
                                if index >= len(plan):
                                    raise AssertionError('extra source queue admission')
                                validate_admission(actual, plan[index])
                                if plan[index]['spawn']:
                                    if actual['offset'] not in (symbols['CHAR_ZP_LEN'] * i for i in range(1, 6)):
                                        raise AssertionError('source spawn did not occupy a physical NPC slot')
                                actual.update(source_queue_index=plan[index]['source_queue_index'], source_model=plan[index]['source_model'], source_definition=plan[index]['source_definition'])
                                if plan[index]['spawn']:
                                    admitted[actual['offset']] = (actual, report['frames_sampled'])
                    else:
                        rows = rows[observer_skipped_prefix:]
                        completed = report['spawn_traversal']['completed']
                        for actual in rows[len(completed):]:
                            completed.append(actual)
                            index = len(completed) - 1
                            if index >= len(plan):
                                raise AssertionError('extra source queue admission')
                            validate_admission(actual, plan[index])
                            if plan[index]['spawn']:
                                if actual['offset'] not in (symbols['CHAR_ZP_LEN'] * i for i in range(1, 6)):
                                    raise AssertionError('source spawn did not occupy a physical NPC slot')
                            actual.update(source_queue_index=plan[index]['source_queue_index'], source_model=plan[index]['source_model'], source_definition=plan[index]['source_definition'])
                            if plan[index]['spawn']:
                                admitted[actual['offset']] = (actual, report['frames_sampled'])
                else:
                    completed = report['spawn_traversal']['completed']
                    for actual in rows[len(completed):]:
                        completed.append(actual)
                        index = len(completed) - 1
                        if index >= len(plan):
                            raise AssertionError('extra source queue admission')
                        validate_admission(actual, plan[index])
                        if plan[index]['spawn']:
                            if actual['offset'] not in (symbols['CHAR_ZP_LEN'] * i for i in range(1, 6)):
                                raise AssertionError('source spawn did not occupy a physical NPC slot')
                        actual.update(source_queue_index=plan[index]['source_queue_index'], source_model=plan[index]['source_model'], source_definition=plan[index]['source_definition'])
                        if plan[index]['spawn']:
                            admitted[actual['offset']] = (actual, report['frames_sampled'])

        def tick(button=None, *, button2=None, hold=False):
            step_fields = (args.traversal_step_fields if traversal and hold
                           and u16(legal.GAME_STATE) == legal.PLAYING else 1)
            if hold:
                if button is None:
                    m.release_input(port=0)
                elif button & m.BTN_A:
                    m.release_input(port=0)
                    exact_input_edge(m, button, 1, port=0)
                    m.hold_input(button, port=0)
                    run_frames_exact(m, 1)
                else:
                    m.hold_input(button, port=0)
                if args.two_player:
                    if button2 is None:
                        m.release_input(port=1)
                    else:
                        m.hold_input(button2, port=1)
                if not button is None:
                    if not button & m.BTN_A:
                        run_frames_exact(m, step_fields)
                    elif traversal:
                        p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                        report['spawn_traversal']['jump_inputs'].append(dict(field=report['frames_sampled'] + 1, requested=int(button), raw=u16(8258588), press=u16(8258576), trigger=u16(8258578), selected=u8(p1_base + symbols['CHAR_SELECTED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL']), x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y'])))
                        report['spawn_traversal']['jump_inputs'] = report['spawn_traversal']['jump_inputs'][-24:]
                        if u16(legal.GAME_STATE) != legal.PLAYING:
                            run_frames_exact(m, 1)
                else:
                    run_frames_exact(m, step_fields)
            elif button is None:
                run_frames_exact(m, 1)
            else:
                exact_input_edge(m, button, 1, port=0)
            report['frames_sampled'] = report['frames_sampled'] + 1
            worker_faulted = traversal and (u16(legal.GAME_STATE) == legal.PLAYING and (u16(8263516) == 1 and bytes(read_block(m, 73728, 32, mem_type='snesSaveRam'))[10] != 0))
            host_faulted = traversal and u16(legal.GAME_STATE) == legal.PLAYING and u16(8263516) == 1 and u16(symbols['S6Host_Error']) != 0
            if host_faulted:
                report['host_error_observation'] = dict(frame=report['frames_sampled'], runtime=runtime_diagnostics())
                raise AssertionError('persistent source-world host bind fault')
            if worker_faulted:
                runtime = runtime_diagnostics()
                report['worker_error_observation'] = dict(frame=report['frames_sampled'], runtime=runtime)
                raise AssertionError('persistent Normal SA-1 source-world worker fault')
            resources = report['resource_policy']
            field = report['frames_sampled']
            busy = u8(symbols['Msu1_StreamBusy'])
            if busy:
                resources['msu_busy_fields'] = resources['msu_busy_fields'] + 1
                if resources['msu_busy_open_start'] is None:
                    resources['msu_busy_open_start'] = field
                source_error = u16(symbols['SourceVisual_Error'])
                if source_error:
                    key = str(source_error)
                    resources['visual_busy_errors'][key] = resources['visual_busy_errors'].get(key, 0) + 1
            elif resources['msu_busy_open_start'] is not None:
                start = resources['msu_busy_open_start']
                resources['msu_busy_runs'].append(dict(start_field=start, end_field=field - 1, duration_fields=field - start))
                resources['msu_busy_open_start'] = None
            harvest()

        def wait(predicate, limit, description, on_timeout=None):
            for _ in range(limit):
                if predicate():
                    return None
                tick()
            if on_timeout is not None:
                on_timeout()
            require(description, False)
        startup.cold_to_title(m, r)
        require('cold TITLE helper passed', all((ok for _, ok in r.results)))
        # Explicit pre-run save fixture; never changed after selection.
        m.write_memory('snesMemory', times, '01000000' if source_set == 'Bonus' else '00000000')
        require('fixture initializes saved completion threshold before run', u32(times) == (1 if source_set == 'Bonus' else 0))
        if args.two_player:
            exact_input_edge(m, m.BTN_START, 1, port=1)
            run_frames_exact(m, 2)
            report['player_count'] = 2
        else:
            report['player_count'] = 1
        if args.mode == 'easy':
            startup.title_to_charselect(m)
        else:
            tick(m.BTN_START)
            wait(lambda: u16(startup.STATE) == startup.CHARSELECT and u8(startup.DIFFICULTY) == 1, 360, 'TITLE START reaches difficulty prompt')
            if set_index >= 1:
                tick(m.BTN_RIGHT)
                wait(lambda: u8(selected) == 1, 120, 'difficulty RIGHT selects available Normal')
            if set_index >= 2:
                tick()
                tick(m.BTN_RIGHT)
                wait(lambda: u8(selected) == 2, 120, 'difficulty RIGHT selects available Hard')
            if set_index == 3:
                tick()
                tick(m.BTN_RIGHT)
                wait(lambda: u8(selected) == 3, 120, 'difficulty RIGHT selects unlocked Bonus')
            require(f'{source_set} selected while difficulty prompt remains active', u16(startup.STATE) == startup.CHARSELECT and u8(startup.DIFFICULTY) == 1)
            tick()
            tick(m.BTN_START)

            def normal_selector_timeout():
                report['normal_selector_timeout'] = dict(state=u16(startup.STATE), difficulty=u8(startup.DIFFICULTY), char_step=u8(startup.CHAR_STEP), selected=u8(selected), campaign_id=u8(legal.CAMPAIGN_ID), p1_status=u8(symbols['G13_P1Out']), p2_status=u8(symbols['G13_P2Out']), player_mode=u8(symbols['G13_TwoPlayerEnabled']), source_mode=u8(symbols.get('Game_PlayerCount', symbols['G13_TwoPlayerEnabled'])))
            wait(lambda: u8(startup.DIFFICULTY) == 3 and u8(startup.CHAR_STEP) == 3, 360, 'Normal confirmation reaches player selector', on_timeout=normal_selector_timeout)
        require('player selector retains selected source set', u16(startup.STATE) == startup.CHARSELECT and (u8(startup.DIFFICULTY) == 3 and (u8(startup.CHAR_STEP) == 3 and u8(selected) == set_index)))
        if args.two_player:
            require('Normal co-op session is selected', u8(symbols['G13_TwoPlayerEnabled']) == 1)
        tick()
        if args.two_player:
            exact_input_edge(m, m.BTN_START, 1, port=1)
            run_frames_exact(m, 2)
        tick(m.BTN_START)
        wait(lambda: u16(startup.STATE) == startup.PLAYING, 600, 'character select reaches PLAYING')
        report['first_entry_observation'] = dict(campaign=u8(legal.CAMPAIGN_ID), ordinal=u8(legal.CAMPAIGN_ORDINAL), physical_stage=u16(legal.STAGE_INDEX), expected_campaign=campaign_id, expected_stage=entries[0][1])
        require('native campaign starts at compiler first stage', u8(legal.CAMPAIGN_ID) == campaign_id and (u8(legal.CAMPAIGN_ORDINAL) == 0 and u16(legal.STAGE_INDEX) == entries[0][1]))
        if campaign_id == 3:
            # PLAYING is published before the source-world bind/bootstrap
            # boundary. Observe a committed worker tick before driving combat.
            wait(lambda: u16(symbols['S6Host_Mode']) == 1
                 and u16(symbols['S6Game_TickCommit']) > 0, 600,
                 'persistent source-world ready before traversal input')
        if args.debug_start_ordinal:
            if args.spawn_traversal:
                if args.mode != 'natural':
                    raise AssertionError('--debug-start-ordinal requires natural source-set traversal')
                target_ordinal = args.debug_start_ordinal
                if 0 < target_ordinal:
                    if not target_ordinal < len(entries):
                        raise AssertionError('--debug-start-ordinal is outside the compiled campaign')
                    m.write_u8(legal.CAMPAIGN_ORDINAL, target_ordinal - 1)
                    m.write_u8(symbols['Stage_LoadPending'], 1)
                    m.write_u16(legal.GAME_STATE, pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR'))
                    tick()
                    if completion_flags[target_ordinal - 1]:
                        wait(lambda: u8(symbols['StageComplete_Active']) == 1,
                             600, 'diagnostic SHOWCOMPLETE initialized')
                    start_advance_before = u16(symbols['StageComplete_AdvanceCount'])
                    for _ in range(240):
                        tick(m.BTN_A if u8(symbols['StageComplete_Active']) else None, hold=True)
                        if u16(symbols['StageComplete_AdvanceCount']) != start_advance_before:
                            break
                        if u8(legal.CAMPAIGN_ORDINAL) == target_ordinal:
                            break
                        tick()

                    def diagnostic_start_timeout():
                        report['debug_start_timeout'] = dict(state=u16(legal.GAME_STATE), state_prev=u16(symbols['Game_StatePrev']), ordinal=u8(legal.CAMPAIGN_ORDINAL), stage=u16(legal.STAGE_INDEX), pending=u8(symbols['Stage_LoadPending']), complete_active=u8(symbols.get('StageComplete_Active', 0)), complete_step=u8(symbols.get('StageComplete_Step', 0)), complete_tick=u16(symbols.get('StageComplete_Tick', 0)), complete_advance=u16(symbols.get('StageComplete_AdvanceCount', 0)), input_press=u16(8258576), input_trigger=u16(8258578), input2_trigger=u16(8258584), nmi_frame_busy=u8(8278016), nmi_frame_counter=u16(8278051))
                    wait(lambda: u16(legal.GAME_STATE) == legal.PLAYING and (u8(legal.CAMPAIGN_ORDINAL) == target_ordinal and u16(legal.STAGE_INDEX) == entries[target_ordinal][1]), 600, 'diagnostic real dispatch to compiler ordinal ' + str(target_ordinal), on_timeout=diagnostic_start_timeout)
                    if args.two_player:
                        require('both co-op players are live at campaign start', u8(symbols['G13_P1Out']) == 0 and (u8(symbols['G13_P2Out']) == 0 and u8(symbols['G13_TwoPlayerEnabled']) == 1))
                    times_before = u32(times)
                    ends_before = u16(l5.ENDS)
                    consumed_before = u16(symbols['SceneVideo_TestRequestConsumed'])
                    seen_before = u16(symbols['SceneVideo_TestRequestSeen'])
                    report['times_before'] = times_before
                    require('new run completion latch is clear', u8(credited) == 0)

                    def sample():
                        result = dict(state=u16(legal.GAME_STATE), ordinal=u8(legal.CAMPAIGN_ORDINAL), stage=u16(legal.STAGE_INDEX), campaign=u8(legal.CAMPAIGN_ID), times=u32(times), complete=u8(complete_active))
                        if traversal:
                            mailbox = bytes(read_block(m, 73728, 32, mem_type='snesSaveRam'))
                            dma_active = [u8(8258692 + i * 8) for i in range(8)]
                            result.update(*(), **{'spawn_index': u8(legal.SPAWN_INDEX), 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(symbols['Screen_PosX']), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + u8(legal.SPAWN_INDEX) * 10) if u8(legal.SPAWN_INDEX) < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'spawn_gate': dict(last_enemy_count=u8(8280221), last_kind=u8(8280211), last_roster=u8(8280231), last_slot_offset=u16(8280239), hole_count=u8(symbols['Spawn_HoleCount']), timer_pending=[u16(8280328 + i * 2) for i in range(6)], timer_fault=u16(8280326)), 'presentation_gate': dict(nmi_frame_busy=u8(8278016), nmi_busy=u8(8278017), nmi_frame_over=u8(8278018), nmi_frame_counter=u16(8278051), stage_water=dict(enabled=u8(8368677), mode=u8(8368678), pending=u8(8368676), dirty=u8(8368692), saved_busy=u8(8368696), held=u8(8368697)), frontpanel=dict(active=u8(8315040), dma_pending=u8(8315041), fault=u8(8315042), booting=u8(8315043), saved_busy=u8(8315066), loaded=u8(8315072), pending_column=u16(8267342), pending_tile=u16(8267352), budget=u8(8267358)), dma_queue=dict(current_slot=u16(8258680), budget=u16(8258682), process_remaining=u16(8258686), slot_type_flags=dma_active, active_count=sum((1 for value in dma_active if value & 64)))), 'msu_stream_busy': u8(symbols['Msu1_StreamBusy']), 'worker_mailbox': dict(target=int.from_bytes(mailbox[2:4], 'little'), completed=int.from_bytes(mailbox[4:6], 'little'), fault=int.from_bytes(mailbox[8:10], 'little'), error=mailbox[10], mutation_fence=mailbox[12]), 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'input_last_raw': u16(8258588), 'p1_hp': u8(legal.ENTITIES[0] + symbols['CHAR_HP']), 'p1_lives': u16(symbols['P1_Lives16']), 'p1_out': u8(symbols['G13_P1Out']), 'credits': u8(symbols['Game_Credits']), 'p1_x': u16(legal.ENTITIES[0] + symbols['CHAR_POS_X']), 'p1_y': u8(legal.ENTITIES[0] + symbols['CHAR_POS_Y']), 'p1_selected': u8(legal.ENTITIES[0] + symbols['CHAR_SELECTED']), 'p1_fall_timer': u8(legal.ENTITIES[0] + symbols['CHAR_FALL_STATE_TIMER']), 'p1_frame': u8(legal.ENTITIES[0] + symbols['CHAR_FRAME_INDEX']), 'p1_tick': u8(legal.ENTITIES[0] + symbols['CHAR_TICK_COUNTER'])})
                            if args.two_player:
                                p2 = 8260096 + symbols['CHAR_ZP_LEN']
                                result.update(p2_hp=u8(p2 + symbols['CHAR_HP']), p2_lives=u16(symbols['G13_P2Lives']), p2_out=u8(symbols['G13_P2Out']), p2_x=u16(p2 + symbols['CHAR_POS_X']), p2_y=u8(p2 + symbols['CHAR_POS_Y']), p2_selected=u8(p2 + symbols['CHAR_SELECTED']), p2_fall_timer=u8(p2 + symbols['CHAR_FALL_STATE_TIMER']), p2_frame=u8(p2 + symbols['CHAR_FRAME_INDEX']), p2_tick=u8(p2 + symbols['CHAR_TICK_COUNTER']))
                            actors = []
                            for slot in range(1, 6):
                                base = 8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_ZP_LEN'] * slot
                                obj = u8(base + symbols['OOP_SELF_SLOT_OFS'])
                                actors.append(dict(*(), **{'slot': slot, 'hp': u8(base + symbols['CHAR_HP']), 'input': u8(base + symbols['CHAR_INPUT_DRIVEN']), 'roster': u8(base + symbols['CHAR_ROSTER_INDEX']), 'selected': u8(base + symbols['CHAR_SELECTED']), 'facing_left': u8(base + symbols['CHAR_FACING_LEFT']), 'fall_timer': u8(base + symbols['CHAR_FALL_STATE_TIMER']), 'fall_frames': u8(base + symbols['CHAR_FALL_FCOUNT']), 'throw_zpos': u16(base + symbols['CHAR_THROW_ZPOS']), 'throw_zvel': u16(base + symbols['CHAR_THROW_ZVEL']), 'drop_state': u16(symbols['StageEnv_Actors'] + slot * symbols['CHAR_ZP_LEN'] + 102), 'hit_stun': u8(base + symbols['CHAR_HIT_STUN']), 'grab_target': u8(base + symbols['CHAR_GRAB_TARGET']), 'grabbed_by': u8(base + symbols['CHAR_GRABBED_BY']), 'x': u16(base + symbols['CHAR_POS_X']), 'y': u8(base + symbols['CHAR_POS_Y']), 'idle': u8(base + symbols['CHAR_IDLE_FCOUNT']), 'object_num': u16(base + symbols['OOP_SELF_NUM_OFS']), 'object_slot': obj, 'object_live': obj < symbols['OOP_MAX_OBJECTS'] * 2 and (obj % 2 == 0 and (u16(symbols['OopFlags'] + obj) & 1 == 1 and (u16(symbols['OopDp'] + obj) == base % 65536 and u16(symbols['OopNum'] + obj) == u16(base + symbols['OOP_SELF_NUM_OFS']))))}))
                            result['npc_slots'] = actors
                        return result

                    def scene_observation():
                        observation = dict(game=sample(), fields={})
                        observation['runtime'] = runtime_diagnostics()
                        observation['msu_stream_busy'] = u8(symbols['Msu1_StreamBusy'])
                        widths = {1: 'TestActive TestError TestErrorCode MsuDmaProbe PlayState PlaySkipCount SkipPending SequenceActive SequenceSkipCount RequestedSceneId Continuation SequenceSceneId SequenceClipOrdinal SequenceClipId SequenceClipCount TestBuffer', 2: 'TestRequest TestRequestSeen TestRequestConsumed TestHandlerEntries TestFrameIndex PlayPresented PlaySwaps PlayCompletion SequenceCompletion SequenceTransitions SequenceClipOffset LoadCount LoadStartNmi LoadEndNmi LoadCheckpoints TestWidth TestHeight TestLengthLo TestLengthHi TestMapBytes TestTileBytes TestPaletteBytes', 4: 'TestPayloadBase TestPayloadSize TestFramePointer TestFrameOffset TestFrameCount SequenceFrameCount'}
                        for width, suffixes in widths.items():
                            for suffix in suffixes.split():
                                name = 'SceneVideo_' + suffix
                                address = symbols[name]
                                observation['fields'][name] = dict(address=address, width=width, value=int.from_bytes(bytes(read_block(m, address, 32)[:width]), 'little'))
                        observation['request_latch_low'] = u8(symbols['SceneVideo_TestRequest'])
                        observation['status_note'] = 'No SceneVideo_TestStatus symbol; TestError/TestErrorCode and PlayState are actual status fields.'
                        size = symbols['DMA_QUEUE_SLOT_SIZE']
                        count = symbols['DMA_QUEUE_SLOTS']
                        queue = list(read_block(m, symbols['DmaQueue'], max(32, size * count)))
                        observation['pending_dma'] = dict(address=symbols['DmaQueue'], raw=queue, active_slots=[i for i in range(count) if queue[i * size + 4] & symbols['DMA_OPT_ACTIVE']])
                        try:
                            cpu = m.get_cpu_state()
                            observation['cpu'] = cpu
                            observation['cpu_pc'] = cpu['k'] << 16 | cpu['pc']
                        except Exception as error:
                            observation['cpu_pc_unavailable'] = f'{type(error).__name__}: {error}'
                        return observation

                    def queue_source_unlink(offset, stage_index, record_index, roster, object_num):
                        m.pause()
                        try:
                            if u16(8263516) == 0 or u16(symbols['S6Host_Mode']) not in (1, 3) or u16(8263518) not in (1, 2):
                                return None
                            control = bytes(read_block(m, 74816, 32, mem_type='snesSaveRam'))
                            request_seq = int.from_bytes(control[0:2], 'little')
                            ack_seq = int.from_bytes(control[2:4], 'little')
                            if request_seq != ack_seq:
                                return None
                            apply_tick = u16(symbols['S6Game_TickCommit']) + 1 & 65535
                            handle = 2560 + offset
                            m.write_u16(74820, handle, mem_type='snesSaveRam')
                            m.write_u16(74822, apply_tick, mem_type='snesSaveRam')
                            m.write_u16(74816, request_seq + 1 & 65535, mem_type='snesSaveRam')
                        finally:
                            m.resume()
                        return dict(sequence=request_seq + 1 & 65535, ack_before=ack_seq, handle=handle, apply_tick=apply_tick, roster=roster, object_num=object_num, record_index=record_index, source='sequenced_worker_remove')

                    def accelerate(stage_index):
                        nonlocal observer_last_change_field, observer_last_stage
                        if traversal:
                            harvest()
                            if observer_last_stage != stage_index:
                                observer_last_stage = stage_index
                                observer_last_change_field = report['frames_sampled']
                            stale_limit = 30 if getattr(args, 'trace_runtime', False) else TRAVERSAL_STALL_LIMIT_FIELDS if traversal else 120
                            stale_fields = observer_stale_fields(stage_index, observer_last_stage, report['frames_sampled'], observer_last_change_field)
                            continue_available = bool(u8(symbols['Game_Credits']) and (u8(symbols['G13_P1Out']) or (args.two_player and u8(symbols['G13_P2Out']))))
                            spawn_index = u8(legal.SPAWN_INDEX)
                            spawn_count = u8(legal.SPAWN_COUNT)
                            if report['spawn_traversal']['observer_status'].startswith('TICK '):
                                if observer_spawn_watchdog_due(spawn_index, spawn_count, stale_fields, stale_limit):
                                    if not continue_available:
                                        report['last_observation'] = sample()
                                        report['stale_observer_diagnostics'] = dict(stale_fields=stale_fields, stage=stage_index, observer_status=observer_last_status, runtime=runtime_diagnostics(), source_queue_debug=bytes(read_block(m, 8275416, 32)[:8]).hex())
                                        trace_name = report['spawn_traversal'].get('bind_trace')
                                        if trace_name:
                                            trace_path = Path(trace_name)
                                            if trace_path.is_file():
                                                report['stale_observer_diagnostics']['bind_trace_tail'] = trace_path.read_text(errors='replace').splitlines()[-160:]
                                        raise AssertionError('Spawn_Play heartbeat stopped changing for ' + str(stale_limit) + ' playing fields')
                            if retirement_pending:
                                remove_control = bytes(read_block(m, 74816, 32, mem_type='snesSaveRam'))
                                events = bytes(read_block(m, 74800, 32, mem_type='snesSaveRam'))
                                remove_ack = int.from_bytes(remove_control[2:4], 'little')
                                event_head = int.from_bytes(events[0:2], 'little')
                                event_tail = int.from_bytes(events[2:4], 'little')
                            for key, identity in list(retirement_pending.items()):
                                pending_stage, offset = key
                                if not pending_stage != stage_index:
                                    if 'sequence' in identity:
                                        if event_head == event_tail:
                                            if not remove_ack - identity['sequence'] & 65535 < 32768:
                                                base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                                if not u8(base + symbols['CHAR_ROSTER_INDEX']) != identity['roster']:
                                                    if not u16(base + symbols['OOP_SELF_NUM_OFS']) != identity['object_num']:
                                                        if u8(base + symbols['CHAR_HP']):
                                                            return None
                                        else:
                                            base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                            if not u8(base + symbols['CHAR_ROSTER_INDEX']) != identity['roster']:
                                                if not u16(base + symbols['OOP_SELF_NUM_OFS']) != identity['object_num']:
                                                    if u8(base + symbols['CHAR_HP']):
                                                        return None
                                    else:
                                        base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                        if not u8(base + symbols['CHAR_ROSTER_INDEX']) != identity['roster']:
                                            if not u16(base + symbols['OOP_SELF_NUM_OFS']) != identity['object_num']:
                                                if u8(base + symbols['CHAR_HP']):
                                                    return None
                                retirement_pending.pop(key, None)
                            index = u8(legal.SPAWN_INDEX)
                            count = u8(legal.SPAWN_COUNT)
                            retired_offsets = []
                            for offset, (receipt, first_field) in admitted.items():
                                base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                bridge = symbols['StageEnv_Actors'] + offset
                                worker_bridge = bytes(read_block(m, 73984 + offset, 133, mem_type='snesSaveRam'))
                                if not receipt['stage'] != stage_index:
                                    if not report['frames_sampled'] - first_field < 2:
                                        if not u8(base + symbols['CHAR_ROSTER_INDEX']) != receipt['roster']:
                                            if not u16(base + symbols['OOP_SELF_NUM_OFS']) != receipt['object_num']:
                                                if not u8(base + symbols['CHAR_INPUT_DRIVEN']) not in (symbols['CHAR_INPUT_DRIVEN_AI'], symbols['CHAR_INPUT_DRIVEN_BIKER']):
                                                    if u8(base + symbols['CHAR_IDLE_FCOUNT']):
                                                        if u8(base + symbols['CHAR_HP']):
                                                            if not not bridge_owns_source_actor(u8(bridge + 64), u8(bridge + 65), u16(bridge + 68), worker_bridge[64], worker_bridge[65], int.from_bytes(worker_bridge[68:70], 'little')):
                                                                grab_target = u8(base + symbols['CHAR_GRAB_TARGET'])
                                                                grabbed_by = u8(base + symbols['CHAR_GRABBED_BY'])
                                                                if not grab_target != 255:
                                                                    if not grabbed_by != 255:
                                                                        request = queue_source_unlink(offset, stage_index, receipt['index'], receipt['roster'], receipt['object_num'])
                                                                        if request is None:
                                                                            return None
                                                                        report['spawn_traversal']['unlink_accelerations'].append(dict(stage=stage_index, index=receipt['index'], offset=offset, roster=receipt['roster'], object_num=receipt['object_num'], delay_fields=report['frames_sampled'] - first_field, request=request))
                                                                        retirement_pending[stage_index, offset] = dict(roster=receipt['roster'], object_num=receipt['object_num'], sequence=request['sequence'])
                                                                        retired_offsets.append(offset)
                            initial_path = journal.with_suffix('.initial-ai.txt')
                            initial_rows = []
                            initial_captured = False
                            initial_encounter_active = False
                            if initial_path.exists():
                                for line in initial_path.read_text().splitlines():
                                    values = list(map(int, line.split()))
                                    if not values[0] != stage_index:
                                        if values[1] == -1:
                                            initial_captured = True
                                        else:
                                            initial_rows.append(values)
                            if initial_captured:
                                if report['frames_sampled'] % 120 == 0:
                                    if initial_captured:
                                        progress = dict(field=report['frames_sampled'], stage=stage_index, spawn_index=u8(legal.SPAWN_INDEX), spawn_count=u8(legal.SPAWN_COUNT), source_tick=u16(8263484), game_tick_commit=u16(symbols['S6Game_TickCommit']), camera_x=u16(legal.SCREEN_POS_X), player=dict(hp=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_HP']), x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), lives=u16(symbols['P1_Lives16']), out=u8(symbols['G13_P1Out']), fall_timer=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_FALL_STATE_TIMER'])), worker=runtime_diagnostics(), initial_ai=[])
                                        for _, slot, offset, roster, object_num, input_mode in initial_rows:
                                            base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                            progress['initial_ai'].append(dict(slot=slot, offset=offset, roster=roster, object_num=object_num, hp=u8(base + symbols['CHAR_HP']), x=u16(base + symbols['CHAR_POS_X']), y=u8(base + symbols['CHAR_POS_Y']), selected=u8(base + symbols['CHAR_SELECTED']), attack=u8(base + symbols['CHAR_ATTACK_FCOUNT']), hit_stun=u8(base + symbols['CHAR_HIT_STUN']), grab_target=u8(base + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(base + symbols['CHAR_GRABBED_BY'])))
                                        journal.with_suffix('.progress.json').write_text(json.dumps(progress, separators=(',', ':')) + '\n', encoding='utf-8')
                                for _, slot, offset, roster, object_num, input_mode in initial_rows:
                                    base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                    obj = u8(base + symbols['OOP_SELF_SLOT_OFS'])
                                    object_live = obj < symbols['OOP_MAX_OBJECTS'] * 2 and (obj % 2 == 0 and (bool(u16(symbols['OopFlags'] + obj) & 1) and (u16(symbols['OopDp'] + obj) == base % 65536 and u16(symbols['OopNum'] + obj) == object_num)))
                                    identity = u8(base + symbols['CHAR_ROSTER_INDEX']) == roster and (u16(base + symbols['OOP_SELF_NUM_OFS']) == object_num and (u8(base + symbols['CHAR_INPUT_DRIVEN']) == input_mode and (u8(base + symbols['CHAR_HP']) > 0 and object_live)))
                                    key = (stage_index, offset, object_num)
                                    if identity:
                                        if key not in initial_ai_reported:
                                            report['spawn_traversal']['initial_ai_combat_targets'].append(dict(stage=stage_index, slot=slot, offset=offset, roster=roster, object_num=object_num, input=input_mode, hp=u8(base + symbols['CHAR_HP']), x=u16(base + symbols['CHAR_POS_X']), y=u8(base + symbols['CHAR_POS_Y']), handling='real player input and native lifecycle'))
                                            initial_ai_reported.add(key)
                                    initial_encounter_active = initial_encounter_active | identity
                            for offset in retired_offsets:
                                admitted.pop(offset, None)
                            if retired_offsets:
                                return None
                            if initial_encounter_active:
                                return None
                            if index < count:
                                return None
                        else:
                            m.write_u8(legal.SPAWN_INDEX, u8(legal.SPAWN_COUNT))
                        direction = build.STAGE_CONFIGS[stage_index].get('scroll_direction', 'right')
                        if direction == 'left':
                            edge = u16(min_x)
                            if edge == 0:
                                AssertionError('left clear predicate requires positive Screen_MinX')
                            m.write_u16(legal.SCREEN_POS_X, edge)
                        elif direction == 'down':
                            m.write_u16(pos_y, u16(max_y))
                        else:
                            m.write_u16(legal.SCREEN_POS_X, u16(legal.STAGE_TRUE_MAX_X))
                        for base in () if traversal else legal.ENTITIES[1:]:
                            if u8(base + legal.CHAR_INPUT_DRIVEN) == legal.CHAR_INPUT_DRIVEN_AI:
                                m.write_u8(base + legal.CHAR_HP, 0)
                    limit_entries = 3 if args.mode == 'easy' else len(entries)
                    start_ordinal = args.debug_start_ordinal
                    for ordinal, (kind, value, name) in enumerate(entries[start_ordinal:limit_entries], start=start_ordinal):
                        if traversal:
                            if kind == 'stage':
                                tick(None, hold=True)
                                harvest()
                        current = sample()
                        require('entry ' + str(ordinal) + ' native order/identity', current['ordinal'] == ordinal and (current['campaign'] == campaign_id and (current['times'] == times_before and (current['state'] == (legal.PLAYING if kind == 'stage' else o3.SCENE) and (current['stage'] == value if kind == 'stage' else u8(o3.SCENE_ID) == value)))))
                        row = dict(ordinal=ordinal, kind=kind, source=name, physical_or_scene=value, next_after=bool(authored[ordinal]['next_after']), start=current)
                        row['runtime_start'] = runtime_diagnostics()
                        row['completion_expected'] = bool(completion_flags[ordinal])
                        report['route'].append(row)
                        traversal_buttons = None
                        traversal_p2_buttons = None
                        continue_waiting = False
                        continue_last_field = None
                        continue_p2_waiting = False
                        continue_p2_last_field = None
                        if traversal:
                            if kind == 'stage':
                                direction = build.STAGE_CONFIGS[value].get('scroll_direction', 'right')
                                traversal_buttons = m.BTN_LEFT if direction == 'left' else m.BTN_DOWN if direction == 'down' else m.BTN_RIGHT
                                if args.two_player:
                                    traversal_p2_buttons = m.BTN_RIGHT if direction == 'left' else m.BTN_UP if direction == 'down' else m.BTN_DOWN if direction == 'up' else m.BTN_LEFT
                                row['traversal_input'] = 'real directional transit; Y attacks only while engaging a live blocker; real Y-overlap collection for authored 1UP/needed health pickups; ordinary walking speed keeps player/camera trigger traversal aligned; after a full-slot queue stall, approach/attack a live native prop before transit; real per-player Start edges only for OUT players'
                                row['continue_inputs'] = []
                        else:
                            m.release_input(port=0)
                            if args.two_player:
                                m.release_input(port=1)
                        if args.screenshots:
                            row['screenshot'] = m.take_screenshot()
                        saw_complete = False
                        skip_sent = False
                        scene_before = None
                        if kind == 'scene':
                            scene_before = l5.snapshot(m)
                            row['activation_start'] = scene_observation()
                            scene_number = sum((e[0] == 'scene' for e in entries[:ordinal + 1]))

                            def immediate_skip_fences():
                                terminal_scene = ordinal == len(entries) - 1
                                state = sample()
                                if terminal_scene:
                                    return dict(skip_mode=args.mode == 'skip', preceding_real_skip=bool(ordinal and report['route'][-2].get('skip_sent')), consumed_once=u16(symbols['SceneVideo_TestRequestConsumed']) - consumed_before & 65535 == scene_number, seen_once=u16(symbols['SceneVideo_TestRequestSeen']) - seen_before & 65535 == scene_number, scene_id=u8(o3.SCENE_ID) == value and u8(symbols['SceneVideo_SequenceSceneId']) == value, inactive=u8(o3.SCENE_ACTIVE) == 0, clean=u8(symbols['SceneVideo_TestError']) == 0 and u8(symbols['SceneVideo_TestErrorCode']) == 0, skipped_once=u8(o3.SCENE_SKIP) == 1 and u16(o3.SCENE_COMPLETE) == 0, input_edge=bool(u16(symbols['SceneVideo_InputTriggerAtSkip']) & 53488), ends_once=u16(l5.ENDS) - ends_before & 65535 == scene_number, campaign=state['campaign'] == campaign_id, destination=state['state'] == legal.TITLE and state['ordinal'] == ordinal if terminal_scene else state['ordinal'] == ordinal + 1 and (state['state'] == legal.PLAYING and state['stage'] == entries[ordinal + 1][1]), credit=state['times'] == times_before + 1 & 4294967295 and u8(credited) == 1)
                                return dict(skip_mode=args.mode == 'skip', preceding_real_skip=bool(ordinal and report['route'][-2].get('skip_sent')), consumed_once=u16(symbols['SceneVideo_TestRequestConsumed']) - consumed_before & 65535 == scene_number, seen_once=u16(symbols['SceneVideo_TestRequestSeen']) - seen_before & 65535 == scene_number, scene_id=u8(o3.SCENE_ID) == value and u8(symbols['SceneVideo_SequenceSceneId']) == value, inactive=u8(o3.SCENE_ACTIVE) == 0, clean=u8(symbols['SceneVideo_TestError']) == 0 and u8(symbols['SceneVideo_TestErrorCode']) == 0, skipped_once=u8(o3.SCENE_SKIP) == 1 and u16(o3.SCENE_COMPLETE) == 0, input_edge=bool(u16(symbols['SceneVideo_InputTriggerAtSkip']) & 53488), ends_once=u16(l5.ENDS) - ends_before & 65535 == scene_number, campaign=state['campaign'] == campaign_id, destination=state['state'] == legal.TITLE and state['ordinal'] == ordinal if terminal_scene else state['ordinal'] == ordinal + 1 and (state['state'] == legal.PLAYING and state['stage'] == entries[ordinal + 1][1]), credit=state['times'] == times_before and u8(credited) == 0)

                            def activated_or_skipped():
                                if u8(o3.SCENE_ACTIVE) == 165:
                                    return True
                                fences = immediate_skip_fences()
                                if all(fences.values()):
                                    row['immediate_skip_fences'] = fences
                                    row['immediate_skip_observation'] = scene_observation()
                                    return True
                                return False

                            def activation_timeout():
                                row['activation_timeout'] = scene_observation()
                                row['activation_timeout']['immediate_skip_fences'] = immediate_skip_fences()
                                row['activation_timeout']['wait_fields'] = 120
                                report['last_observation'] = row['activation_timeout']['game']
                            wait(activated_or_skipped, 120, name + ' activates or fenced immediate skip', on_timeout=activation_timeout)
                            require(name + ' campaign scene continuation', u8(o3.SCENE_CONT) == 1)
                            track = pasm_constant_in('tools/audio/audio_music_ids.pasm', 'Music_EndingTrack' if name == 'ENDING' else 'Music_SceneTrack_' + name)
                            require(name + ' source scene audio selection', u8(o3.SCENE_TRACK) == track and u8(o3.SCENE_REPEAT) == (name in ('ENDING', 'SEWER')))
                        budget = SCENE_FIELD_BUDGET if kind == 'scene' else args.stage_fields
                        last_spawn_index = u8(legal.SPAWN_INDEX) if kind == 'stage' else 0
                        last_spawn_change_elapsed = 0
                        for elapsed in range(budget):
                            state = sample()
                            report['last_observation'] = state
                            if kind == 'scene':
                                if elapsed % 300 == 0:
                                    progress = scene_observation()
                                    progress['elapsed_fields'] = elapsed
                                    row.setdefault('scene_progress', []).append(progress)
                            if not state['ordinal'] != ordinal:
                                if state['state'] == legal.TITLE:
                                    if traversal:
                                        if state['state'] == legal.TITLE:
                                            if ordinal != len(entries) - 1:
                                                row['unexpected_exit'] = state
                                                harvest()
                                                raise AssertionError('entry ' + str(ordinal) + ' premature TITLE, not campaign progression')
                                    break
                                if not state['campaign'] != campaign_id:
                                    if state['times'] != times_before:
                                        require('no premature campaign/TimesCompleted change', False)
                                else:
                                    require('no premature campaign/TimesCompleted change', False)
                                button = None
                                button2 = None
                                target_probe = None
                                if kind == 'stage':
                                    if state['complete']:
                                        saw_complete = True
                                        if args.mode != 'natural':
                                            if not skip_sent:
                                                button = m.BTN_A
                                                skip_sent = True
                                    elif state['state'] == legal.PLAYING:
                                        accelerate(value)
                                        if traversal:
                                            current_spawn_index = u8(legal.SPAWN_INDEX)
                                            if current_spawn_index != last_spawn_index:
                                                last_spawn_index = current_spawn_index
                                                last_spawn_change_elapsed = elapsed
                                            spawn_stalled = current_spawn_index < u8(legal.SPAWN_COUNT) and elapsed - last_spawn_change_elapsed >= 24
                                            if not u8(symbols['G13_P1Out']):
                                                continue_waiting = False
                                                continue_last_field = None
                                            if traversal_continue_needed(u8(symbols['G13_P1Out']), u8(symbols['Game_Credits'])):
                                                if continue_waiting:
                                                    if not continue_last_field is None:
                                                        if elapsed - continue_last_field >= 30:
                                                            button = m.BTN_START
                                                            continue_waiting = True
                                                            continue_last_field = elapsed
                                                            row['continue_inputs'].append(dict(elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                                    else:
                                                        button = m.BTN_START
                                                        continue_waiting = True
                                                        continue_last_field = elapsed
                                                        row['continue_inputs'].append(dict(elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                                else:
                                                    button = m.BTN_START
                                                    continue_waiting = True
                                                    continue_last_field = elapsed
                                                    row['continue_inputs'].append(dict(elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                            if args.two_player:
                                                if not u8(symbols['G13_P2Out']):
                                                    continue_p2_waiting = False
                                                    continue_p2_last_field = None
                                                if traversal_continue_needed(u8(symbols['G13_P2Out']), u8(symbols['Game_Credits'])):
                                                    if continue_p2_waiting:
                                                        if not continue_p2_last_field is None:
                                                            if elapsed - continue_p2_last_field >= 30:
                                                                button2 = m.BTN_START
                                                                continue_p2_waiting = True
                                                                continue_p2_last_field = elapsed
                                                                row['continue_inputs'].append(dict(player=2, elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                                        else:
                                                            button2 = m.BTN_START
                                                            continue_p2_waiting = True
                                                            continue_p2_last_field = elapsed
                                                            row['continue_inputs'].append(dict(player=2, elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                                    else:
                                                        button2 = m.BTN_START
                                                        continue_p2_waiting = True
                                                        continue_p2_last_field = elapsed
                                                        row['continue_inputs'].append(dict(player=2, elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                            if button is None:
                                                if traversal_buttons is not None:
                                                    button = traversal_buttons
                                                    if not args.trace_player_move:
                                                        p1 = 8257536 + symbols['PlayerEntity_DpBase']
                                                        p1x = s16(p1 + symbols['CHAR_POS_X'])
                                                        # Canonical worker projection can exceed a byte.
                                                        # Wrapping 438 to 182 sends prop steering to the
                                                        # wrong source lane after a long campaign.
                                                        p1y = (s16(p1 + symbols['CHAR_POS_Y'])
                                                               if os.environ.get('S8_NORMAL_CANONICAL_P1_CONTROLLER') == '1'
                                                               else u8(p1 + symbols['CHAR_POS_Y']))
                                                        raw_p1x = p1x
                                                        world_max = u16(symbols['WorldMaxX'])
                                                        if world_max:
                                                            if raw_p1x > world_max * 2:
                                                                raw_p1x = raw_p1x // 4
                                                        world_player_x = p1x
                                                        world_player_y = p1y
                                                        world_actor_rows = None
                                                        if spawn_stalled:
                                                            world_actor_rows = bytes(read_block(m, 71936, 1536, mem_type='snesSaveRam'))
                                                            world_player_x = int.from_bytes(world_actor_rows[20:22], 'little', signed=True)
                                                            world_player_y = int.from_bytes(world_actor_rows[22:24], 'little', signed=True)
                                                        prop_targets = []
                                                        pickup_targets = []
                                                        combat_targets = []
                                                        group_enemy_count = 0
                                                        for slot in range(1, 6):
                                                            actor = p1 + slot * symbols['CHAR_ZP_LEN']
                                                            mode = u8(actor + symbols['CHAR_INPUT_DRIVEN'])
                                                            hp = u8(actor + symbols['CHAR_HP'])
                                                            object_num = u16(actor + symbols['OOP_SELF_NUM_OFS'])
                                                            roster = u8(actor + symbols['CHAR_ROSTER_INDEX'])
                                                            if hp:
                                                                if args.two_player:
                                                                    if not slot == 1:
                                                                        if mode not in (symbols['CHAR_INPUT_DRIVEN_PROP'], symbols['CHAR_INPUT_DRIVEN_STEAMER'], symbols['CHAR_INPUT_DRIVEN_STEAM']):
                                                                            group_enemy_count = group_enemy_count + 1
                                                                elif mode not in (symbols['CHAR_INPUT_DRIVEN_PROP'], symbols['CHAR_INPUT_DRIVEN_STEAMER'], symbols['CHAR_INPUT_DRIVEN_STEAM']):
                                                                    group_enemy_count = group_enemy_count + 1
                                                            if mode in (symbols['CHAR_INPUT_DRIVEN_AI'], symbols['CHAR_INPUT_DRIVEN_BIKER']):
                                                                identity = (value, slot, object_num, roster, mode)
                                                                previous_hp = combat_hp_seen.get(identity)
                                                                if previous_hp is not None:
                                                                    if previous_hp != hp:
                                                                        report['spawn_traversal']['combat_interactions'].append(dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, previous_hp=previous_hp, hp=hp, field=report['frames_sampled']))
                                                                combat_hp_seen[identity] = hp
                                                                if hp:
                                                                    bridge = symbols['StageEnv_Actors'] + slot * 133
                                                                    worker_bridge = bytes(read_block(m, 73984 + slot * 133, 133, mem_type='snesSaveRam'))
                                                                    worker_owned = world_actor_rows is not None and bridge_owns_source_actor(u8(bridge + 64), u8(bridge + 65), u16(bridge + 68), worker_bridge[64], worker_bridge[65], int.from_bytes(worker_bridge[68:70], 'little'))
                                                                    if worker_owned:
                                                                        source_actor = slot * 256
                                                                        source_xy = (int.from_bytes(world_actor_rows[source_actor + 20:source_actor + 22], 'little', signed=True), int.from_bytes(world_actor_rows[source_actor + 22:source_actor + 24], 'little', signed=True))
                                                                    else:
                                                                        source_xy = (s16(actor + symbols['CHAR_POS_X']), u8(actor + symbols['CHAR_POS_Y']))
                                                                    ax, ay = traversal_actor_coordinates(mode, worker_owned, symbols['CHAR_INPUT_DRIVEN_AI'], source_xy, (s16(actor + symbols['CHAR_POS_X']), u8(actor + symbols['CHAR_POS_Y'])))
                                                                    target_player_x, target_player_y = (world_player_x, world_player_y) if worker_owned else (raw_p1x, p1y)
                                                                    facing_left = u8(actor + symbols['CHAR_FACING_LEFT'])
                                                                    biker_approaching = mode == symbols['CHAR_INPUT_DRIVEN_BIKER'] and traversal_biker_approaches(target_player_x, ax, facing_left)
                                                                    combat_targets.append((abs(ax - target_player_x) + abs(ay - target_player_y), slot, ax, ay, object_num, roster, mode, hp, worker_owned, biker_approaching))
                                                            if not mode not in (symbols['CHAR_INPUT_DRIVEN_PROP'], symbols['CHAR_INPUT_DRIVEN_STEAMER'], symbols['CHAR_INPUT_DRIVEN_STEAM']):
                                                                pickup_raw = u8(actor + symbols['CHAR_PICKUP_TYPE'])
                                                                pickup_type = pickup_raw & 127
                                                                identity = (value, slot, object_num, roster, mode)
                                                                previous_hp = prop_hp_seen.get(identity)
                                                                if previous_hp is not None:
                                                                    if previous_hp != hp:
                                                                        report['spawn_traversal']['prop_interactions'].append(dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, previous_hp=previous_hp, hp=hp, field=report['frames_sampled']))
                                                                prop_hp_seen[identity] = hp
                                                                pickup_identity = (value, slot, object_num, roster)
                                                                previous_pickup = pickup_type_seen.get(pickup_identity, 0)
                                                                if pickup_type:
                                                                    pickup_type_seen[pickup_identity] = pickup_type
                                                                elif previous_pickup:
                                                                    prop_x = s16(actor + symbols['CHAR_POS_X'])
                                                                    prop_y = u8(actor + symbols['CHAR_POS_Y'])
                                                                    report['spawn_traversal']['pickup_interactions'].append(dict(stage=value, slot=slot, object_num=object_num, roster=roster, pickup_type=previous_pickup, result=('collected' if prop_x == 32767 else 'removed') if hp else 'removed', hp=hp, x=prop_x, y=prop_y, field=report['frames_sampled']))
                                                                    pickup_type_seen.pop(pickup_identity, None)
                                                                if not not hp:
                                                                    ax = s16(actor + symbols['CHAR_POS_X'])
                                                                    ay = u8(actor + symbols['CHAR_POS_Y'])
                                                                    prop_targets.append((slot, ax, ay, object_num, roster, mode, hp, False, False))
                                                                    player_hp = u8(symbols['PlayerEntity_Hp'])
                                                                    player_hp_max = symbols.get('CHAR_HP_MAX', 64)
                                                                    two_player_only = bool(pickup_raw & 128) and (not args.two_player)
                                                                    if pickup_type:
                                                                        if not two_player_only:
                                                                            if traversal_pickup_needed(pickup_type, player_hp, player_hp_max):
                                                                                pickup_targets.append((slot, ax, ay, object_num, roster, mode, hp, False, False, pickup_type))
                                                        all_slots_busy = traversal_slots_full(state['npc_slots'], symbols['CHAR_INPUT_DRIVEN_NONCOMBAT'])
                                                        terminal_clamp = traversal_terminal_clamp(state)
                                                        targets = []
                                                        target_pickup_type = 0
                                                        if pickup_targets:
                                                            pickup = min(pickup_targets, key=lambda target: traversal_target_key(target, raw_p1x, p1y, build.STAGE_CONFIGS[value].get('scroll_direction', 'right')))
                                                            targets = [pickup[:9]]
                                                            target_pickup_type = pickup[9]
                                                        elif spawn_stalled:
                                                            if prop_targets:
                                                                targets = traversal_blocking_props(prop_targets, raw_p1x, p1y, symbols['CHAR_INPUT_DRIVEN_PROP'], terminal_clamp)
                                                        group_gate_blocked = spawn_stalled and traversal_group_gate_blocks_spawn(group_enemy_count, state['spawn_group_min'])
                                                        queue_complete = current_spawn_index >= u8(legal.SPAWN_COUNT)
                                                        if combat_targets:
                                                            if not targets:
                                                                nearest = min(combat_targets, key=lambda target: target[0])
                                                                aim_x = world_player_x if nearest[8] else raw_p1x
                                                                aim_y = world_player_y if nearest[8] else p1y
                                                                if traversal_combat_engagement_needed(nearest, aim_x, aim_y, group_gate_blocked=group_gate_blocked, queue_complete=queue_complete, terminal=terminal_clamp, direction=build.STAGE_CONFIGS[value].get('scroll_direction', 'right')):
                                                                    _, slot, ax, ay, object_num, roster, mode, hp, worker_owned, biker_approaching = nearest
                                                                    targets = [(slot, ax, ay, object_num, roster, mode, hp, worker_owned, biker_approaching)]
                                                        if targets:
                                                            direction = build.STAGE_CONFIGS[value].get('scroll_direction', 'right')
                                                            slot, ax, ay, object_num, roster, mode, hp, worker_owned, biker_approaching = min(targets, key=lambda target: traversal_target_key(target, world_player_x if target[7] else raw_p1x, world_player_y, direction) if target[7] else traversal_target_key(target, world_player_x if target[7] else raw_p1x, p1y, direction))
                                                            aim_x = world_player_x if worker_owned else raw_p1x
                                                            aim_y = world_player_y if worker_owned else p1y
                                                            dx = ax - aim_x
                                                            dy = ay - aim_y
                                                            target_probe = dict(slot=slot, x=ax, y=ay, dx=dx, dy=dy, mode=mode, worker_owned=worker_owned, biker_approaching=biker_approaching)
                                                            prop_slots_full = traversal_terminal_prop_clear_required(all_slots_busy, spawn_stalled, terminal_clamp) if mode == symbols['CHAR_INPUT_DRIVEN_PROP'] else all_slots_busy
                                                            prop_action = 'collect' if target_pickup_type else traversal_prop_chase_action(dx, dy, prop_slots_full) if mode == symbols['CHAR_INPUT_DRIVEN_PROP'] else None
                                                            prop_bypass_direction = None
                                                            target_probe['prop_bypass_direction'] = prop_bypass_direction
                                                            button = 0
                                                            if prop_action == 'collect':
                                                                pickup_action, attack_now = traversal_pickup_action(dx, dy, elapsed)
                                                                if pickup_action == 'approach_right':
                                                                    button = button | m.BTN_RIGHT
                                                                    if abs(dx) > 64:
                                                                        button = button | m.BTN_B
                                                                elif pickup_action == 'approach_left':
                                                                    button = button | m.BTN_LEFT
                                                                    if abs(dx) > 64:
                                                                        button = button | m.BTN_B
                                                                elif pickup_action == 'depth_down':
                                                                    button = button | m.BTN_DOWN
                                                                elif pickup_action == 'depth_up':
                                                                    button = button | m.BTN_UP
                                                                elif pickup_action == 'collect':
                                                                    if abs(dx) > 4:
                                                                        button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                    if attack_now:
                                                                        button = button | m.BTN_Y
                                                            elif prop_action == 'bypass':
                                                                scroll = build.STAGE_CONFIGS[value].get('scroll_direction', 'right')
                                                                button = button | (m.BTN_LEFT if scroll == 'left' else m.BTN_RIGHT if scroll == 'right' else m.BTN_RIGHT if dx >= 0 else m.BTN_LEFT)
                                                                bypass_action = traversal_prop_bypass_action(dy)
                                                                if bypass_action == 'depth_up':
                                                                    button = button | m.BTN_UP
                                                                elif bypass_action == 'depth_down':
                                                                    button = button | m.BTN_DOWN
                                                            elif prop_action == 'lane':
                                                                button = button | (m.BTN_DOWN if dy > 0 else m.BTN_UP)
                                                                button = button | m.BTN_B
                                                            elif prop_action == 'detour':
                                                                button = button | (m.BTN_DOWN if dy < 0 else m.BTN_UP)
                                                            elif prop_action == 'approach':
                                                                button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                if abs(dx) > 64:
                                                                    button = button | m.BTN_B
                                                            elif prop_action == 'attack':
                                                                button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                    if not prop_slots_full:
                                                                        if traversal_jump_held(elapsed):
                                                                            button = button | m.BTN_A
                                                                    elif traversal_attack_held(elapsed):
                                                                        button = button | m.BTN_Y
                                                                elif traversal_attack_held(elapsed):
                                                                    button = button | m.BTN_Y
                                                            else:
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_BIKER']:
                                                                    biker_actor = 8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_ZP_LEN'] * slot
                                                                    biker_mobile = u8(biker_actor + symbols['CHAR_SELECTED']) not in (symbols['CHAR_SELECTED_FALL'], symbols['CHAR_SELECTED_RISE'])
                                                                    biker_action = traversal_biker_action(dx, dy, elapsed, mobile=biker_mobile, approaching=biker_approaching)
                                                                    if biker_action == 'depth_down':
                                                                        button = button | m.BTN_DOWN
                                                                        if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                            if traversal_combat_attack_opportunity(dx, dy):
                                                                                if traversal_attack_held(elapsed):
                                                                                    button = button | m.BTN_Y
                                                                        target = (value, slot, object_num, roster, mode)
                                                                        if target != prop_target_last:
                                                                            interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                            if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                                report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                            else:
                                                                                report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                            prop_target_last = target
                                                                        if args.two_player:
                                                                            if button2 is None:
                                                                                if traversal_p2_buttons is not None:
                                                                                    if not u8(symbols['G13_P2Out']):
                                                                                        button2 = traversal_p2_buttons
                                                                        if traversal:
                                                                            button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                        if traversal:
                                                                            if elapsed % 60 == 0:
                                                                                p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                                actors = []
                                                                                for probe_slot in range(1, 6):
                                                                                    actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                                    actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                                worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                                worker_player = worker_rows[0:256]
                                                                                spawn_index = u8(legal.SPAWN_INDEX)
                                                                                probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                                report['spawn_traversal']['controller_probe'].append(probe)
                                                                                report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                                controller_probe_path.write_text(json.dumps(probe))
                                                                        tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                        if traversal:
                                                                            if kind == 'stage':
                                                                                if button is not None:
                                                                                    if button & m.BTN_Y:
                                                                                        trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                        report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                        report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                        continue
                                                                    if biker_action == 'depth_up':
                                                                        button = button | m.BTN_UP
                                                                        if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                            if traversal_combat_attack_opportunity(dx, dy):
                                                                                if traversal_attack_held(elapsed):
                                                                                    button = button | m.BTN_Y
                                                                        target = (value, slot, object_num, roster, mode)
                                                                        if target != prop_target_last:
                                                                            interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                            if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                                report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                            else:
                                                                                report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                            prop_target_last = target
                                                                        if args.two_player:
                                                                            if button2 is None:
                                                                                if traversal_p2_buttons is not None:
                                                                                    if not u8(symbols['G13_P2Out']):
                                                                                        button2 = traversal_p2_buttons
                                                                        if traversal:
                                                                            button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                        if traversal:
                                                                            if elapsed % 60 == 0:
                                                                                p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                                actors = []
                                                                                for probe_slot in range(1, 6):
                                                                                    actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                                    actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                                worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                                worker_player = worker_rows[0:256]
                                                                                spawn_index = u8(legal.SPAWN_INDEX)
                                                                                probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                                report['spawn_traversal']['controller_probe'].append(probe)
                                                                                report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                                controller_probe_path.write_text(json.dumps(probe))
                                                                        tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                        if traversal:
                                                                            if kind == 'stage':
                                                                                if button is not None:
                                                                                    if button & m.BTN_Y:
                                                                                        trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                        report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                        report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                        continue
                                                                    if biker_action == 'approach_right':
                                                                        button = button | m.BTN_RIGHT
                                                                        if abs(dx) > 32:
                                                                            button = button | m.BTN_B
                                                                        if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                            if traversal_combat_attack_opportunity(dx, dy):
                                                                                if traversal_attack_held(elapsed):
                                                                                    button = button | m.BTN_Y
                                                                        target = (value, slot, object_num, roster, mode)
                                                                        if target != prop_target_last:
                                                                            interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                            if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                                report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                            else:
                                                                                report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                            prop_target_last = target
                                                                        if args.two_player:
                                                                            if button2 is None:
                                                                                if traversal_p2_buttons is not None:
                                                                                    if not u8(symbols['G13_P2Out']):
                                                                                        button2 = traversal_p2_buttons
                                                                        if traversal:
                                                                            button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                        if traversal:
                                                                            if elapsed % 60 == 0:
                                                                                p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                                actors = []
                                                                                for probe_slot in range(1, 6):
                                                                                    actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                                    actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                                worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                                worker_player = worker_rows[0:256]
                                                                                spawn_index = u8(legal.SPAWN_INDEX)
                                                                                probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                                report['spawn_traversal']['controller_probe'].append(probe)
                                                                                report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                                controller_probe_path.write_text(json.dumps(probe))
                                                                        tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                        if traversal:
                                                                            if kind == 'stage':
                                                                                if button is not None:
                                                                                    if button & m.BTN_Y:
                                                                                        trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                        report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                        report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                        continue
                                                                    if biker_action == 'approach_left':
                                                                        button = button | m.BTN_LEFT
                                                                        if abs(dx) > 32:
                                                                            button = button | m.BTN_B
                                                                        if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                            if traversal_combat_attack_opportunity(dx, dy):
                                                                                if traversal_attack_held(elapsed):
                                                                                    button = button | m.BTN_Y
                                                                        target = (value, slot, object_num, roster, mode)
                                                                        if target != prop_target_last:
                                                                            interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                            if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                                report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                            else:
                                                                                report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                            prop_target_last = target
                                                                        if args.two_player:
                                                                            if button2 is None:
                                                                                if traversal_p2_buttons is not None:
                                                                                    if not u8(symbols['G13_P2Out']):
                                                                                        button2 = traversal_p2_buttons
                                                                        if traversal:
                                                                            button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                        if traversal:
                                                                            if elapsed % 60 == 0:
                                                                                p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                                actors = []
                                                                                for probe_slot in range(1, 6):
                                                                                    actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                                    actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                                worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                                worker_player = worker_rows[0:256]
                                                                                spawn_index = u8(legal.SPAWN_INDEX)
                                                                                probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                                report['spawn_traversal']['controller_probe'].append(probe)
                                                                                report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                                controller_probe_path.write_text(json.dumps(probe))
                                                                        tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                        if traversal:
                                                                            if kind == 'stage':
                                                                                if button is not None:
                                                                                    if button & m.BTN_Y:
                                                                                        trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                        report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                        report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                        continue
                                                                    if biker_action.startswith('attack_'):
                                                                        button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                        button = button | traversal_biker_attack_mask(elapsed, m.BTN_Y, m.BTN_X)
                                                                        if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                            if traversal_combat_attack_opportunity(dx, dy):
                                                                                if traversal_attack_held(elapsed):
                                                                                    button = button | m.BTN_Y
                                                                        target = (value, slot, object_num, roster, mode)
                                                                        if target != prop_target_last:
                                                                            interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                            if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                                report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                            else:
                                                                                report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                            prop_target_last = target
                                                                        if args.two_player:
                                                                            if button2 is None:
                                                                                if traversal_p2_buttons is not None:
                                                                                    if not u8(symbols['G13_P2Out']):
                                                                                        button2 = traversal_p2_buttons
                                                                        if traversal:
                                                                            button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                        if traversal:
                                                                            if elapsed % 60 == 0:
                                                                                p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                                actors = []
                                                                                for probe_slot in range(1, 6):
                                                                                    actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                                    actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                                worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                                worker_player = worker_rows[0:256]
                                                                                spawn_index = u8(legal.SPAWN_INDEX)
                                                                                probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                                report['spawn_traversal']['controller_probe'].append(probe)
                                                                                report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                                controller_probe_path.write_text(json.dumps(probe))
                                                                        tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                        if traversal:
                                                                            if kind == 'stage':
                                                                                if button is not None:
                                                                                    if button & m.BTN_Y:
                                                                                        trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                        report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                        report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                        continue
                                                                    if biker_action.startswith('face_'):
                                                                        button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                        if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                            if traversal_combat_attack_opportunity(dx, dy):
                                                                                if traversal_attack_held(elapsed):
                                                                                    button = button | m.BTN_Y
                                                                        target = (value, slot, object_num, roster, mode)
                                                                        if target != prop_target_last:
                                                                            interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                            if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                                report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                            else:
                                                                                report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                            prop_target_last = target
                                                                        if args.two_player:
                                                                            if button2 is None:
                                                                                if traversal_p2_buttons is not None:
                                                                                    if not u8(symbols['G13_P2Out']):
                                                                                        button2 = traversal_p2_buttons
                                                                        if traversal:
                                                                            button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                        if traversal:
                                                                            if elapsed % 60 == 0:
                                                                                p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                                actors = []
                                                                                for probe_slot in range(1, 6):
                                                                                    actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                                    actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                                worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                                worker_player = worker_rows[0:256]
                                                                                spawn_index = u8(legal.SPAWN_INDEX)
                                                                                probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                                report['spawn_traversal']['controller_probe'].append(probe)
                                                                                report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                                controller_probe_path.write_text(json.dumps(probe))
                                                                        tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                        if traversal:
                                                                            if kind == 'stage':
                                                                                if button is not None:
                                                                                    if button & m.BTN_Y:
                                                                                        trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                        report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                        report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                        continue
                                                                    if biker_action == 'wait':
                                                                        if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                            if traversal_combat_attack_opportunity(dx, dy):
                                                                                if traversal_attack_held(elapsed):
                                                                                    button = button | m.BTN_Y
                                                                        target = (value, slot, object_num, roster, mode)
                                                                        if target != prop_target_last:
                                                                            interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                            if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                                report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                            else:
                                                                                report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                            prop_target_last = target
                                                                        if args.two_player:
                                                                            if button2 is None:
                                                                                if traversal_p2_buttons is not None:
                                                                                    if not u8(symbols['G13_P2Out']):
                                                                                        button2 = traversal_p2_buttons
                                                                        if traversal:
                                                                            button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                        if traversal:
                                                                            if elapsed % 60 == 0:
                                                                                p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                                actors = []
                                                                                for probe_slot in range(1, 6):
                                                                                    actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                                    actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                                worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                                worker_player = worker_rows[0:256]
                                                                                spawn_index = u8(legal.SPAWN_INDEX)
                                                                                probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                                report['spawn_traversal']['controller_probe'].append(probe)
                                                                                report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                                controller_probe_path.write_text(json.dumps(probe))
                                                                        tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                        if traversal:
                                                                            if kind == 'stage':
                                                                                if button is not None:
                                                                                    if button & m.BTN_Y:
                                                                                        trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                        report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                        report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                        continue
                                                                    raise AssertionError('unknown Biker traversal action')
                                                                if traversal_chase_axis(dx, dy) == 'x':
                                                                    button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                    if abs(dx) > 64:
                                                                        button = button | m.BTN_B
                                                                elif traversal_chase_axis(dx, dy) == 'y':
                                                                    button = button | (m.BTN_DOWN if dy > 0 else m.BTN_UP)
                                                                else:
                                                                    button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                    if traversal_attack_held(elapsed):
                                                                        button = button | m.BTN_Y
                                                            if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                if traversal_combat_attack_opportunity(dx, dy):
                                                                    if traversal_attack_held(elapsed):
                                                                        button = button | m.BTN_Y
                                                            target = (value, slot, object_num, roster, mode)
                                                            if target != prop_target_last:
                                                                interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                    report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                else:
                                                                    report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                prop_target_last = target
                                                        else:
                                                            prop_target_last = None
                                                            if build.STAGE_CONFIGS[value].get('scroll_direction', 'right') in ('up', 'down'):
                                                                button = button | (m.BTN_LEFT if elapsed % 32 < 16 else m.BTN_RIGHT)
                                                            else:
                                                                button = button | (m.BTN_UP if elapsed % 32 < 16 else m.BTN_DOWN)
                                                            direction = build.STAGE_CONFIGS[value].get('scroll_direction', 'right')
                                                            if traversal_camera_wait(raw_p1x, state['camera_x'], u16(symbols['Screen_SizeX']) if 'Screen_SizeX' in symbols else 256, direction):
                                                                button = traversal_camera_wait_button_value
                                                            vertical_scroll = build.STAGE_CONFIGS[value].get('scroll_direction', 'right') in ('up', 'down')
                                                            for slot in range(1, 6):
                                                                actor = p1 + slot * symbols['CHAR_ZP_LEN']
                                                                mode = u8(actor + symbols['CHAR_INPUT_DRIVEN'])
                                                                if not mode not in (symbols['CHAR_INPUT_DRIVEN_AI'], symbols['CHAR_INPUT_DRIVEN_BIKER']):
                                                                    if not u8(actor + symbols['CHAR_HP']):
                                                                        continue
                                                                    ax = u16(actor + symbols['CHAR_POS_X'])
                                                                    ay = u8(actor + symbols['CHAR_POS_Y'])
                                                                    if not abs(ax - p1x) > 72:
                                                                        if abs(ay - p1y) > 28:
                                                                            continue
                                                                        if vertical_scroll:
                                                                            button = button | (m.BTN_LEFT if p1x >= ax else m.BTN_RIGHT)
                                                                        else:
                                                                            button = button | (m.BTN_UP if p1y >= ay else m.BTN_DOWN)
                                                                    else:
                                                                        continue
                                                                else:
                                                                    continue
                                                                break
                                            if args.two_player:
                                                if button2 is None:
                                                    if traversal_p2_buttons is not None:
                                                        if not u8(symbols['G13_P2Out']):
                                                            button2 = traversal_p2_buttons
                                            if traversal:
                                                button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                            if traversal:
                                                if elapsed % 60 == 0:
                                                    p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                    actors = []
                                                    for probe_slot in range(1, 6):
                                                        actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                        actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                    worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                    worker_player = worker_rows[0:256]
                                                    spawn_index = u8(legal.SPAWN_INDEX)
                                                    probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                    report['spawn_traversal']['controller_probe'].append(probe)
                                                    report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                    controller_probe_path.write_text(json.dumps(probe))
                                elif args.mode == 'skip':
                                    if not skip_sent:
                                        if u16(o3.SCENE_PRESENTED) >= 1:
                                            button = m.BTN_A
                                            skip_sent = True
                                tick(button, button2=button2, hold=traversal and kind == 'stage')
                                if traversal:
                                    if kind == 'stage':
                                        if button is not None:
                                            if button & m.BTN_Y:
                                                trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                report['spawn_traversal']['input_trace'].append(trace_row)
                                                report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                continue
                            if traversal:
                                if state['state'] == legal.TITLE:
                                    if ordinal != len(entries) - 1:
                                        row['unexpected_exit'] = state
                                        harvest()
                                        raise AssertionError('entry ' + str(ordinal) + ' premature TITLE, not campaign progression')
                            break
                        else:
                            row['exit_timeout'] = scene_observation() if kind == 'scene' else dict(game=sample())
                            row['exit_timeout']['elapsed_fields'] = budget
                            row['exit_timeout']['runtime'] = runtime_diagnostics()
                            report['last_observation'] = row['exit_timeout']['game']
                            row['timeout_runtime'] = runtime_diagnostics()
                            require('entry ' + str(ordinal) + ' bounded native exit', False)
                        if kind == 'scene':
                            row['exit_observation'] = scene_observation()
                            row['exit_observation']['elapsed_fields'] = elapsed
                        row['frames'] = elapsed
                        row['saw_showcomplete'] = saw_complete
                        row['skip_sent'] = skip_sent
                        if kind == 'stage':
                            if traversal:
                                harvest()
                                completed = report['spawn_traversal']['completed']
                                require('entry ' + str(ordinal) + ' every packed record consumed natively', sum((r['stage'] == value for r in completed)) == sum((r['stage'] == value for r in plan)))
                                m.release_input(port=0)
                                if args.two_player:
                                    m.release_input(port=1)
                            require('entry ' + str(ordinal) + ' completion policy behavior', saw_complete == row['completion_expected'])
                            if saw_complete:
                                require('entry ' + str(ordinal) + ' showcomplete advances exactly once', u16(complete_advances) == 1 and u8(complete_active) == 0)
                        else:
                            row['scene'] = dict(presented=u16(o3.SCENE_PRESENTED), transitions=u16(o3.SCENE_TRANSITIONS), completion=u16(o3.SCENE_COMPLETE), skip=u8(o3.SCENE_SKIP), late=u16(o3.SCENE_LATE), retries=u16(o3.SCENE_RETRIES))
                            require(name + ' preserves score/lives/credits', l5.snapshot(m) == scene_before)
                            require(name + ' clean scene transport', row['scene']['late'] == row['scene']['retries'] and row['scene']['retries'] == 0)
                            if args.mode == 'natural':
                                require(name + ' complete natural playback', row['scene']['presented'] == ({'ENDING': 1997, 'RUGAL': 126, 'SEWER': 3}[name]) and (row['scene']['completion'] == 1 and row['scene']['skip'] == 0))
                                if name == 'ENDING':
                                    require('ENDING has four clip transitions', row['scene']['transitions'] == 4)
                            else:
                                require(name + ' real input skip exactly once', bool(row.get('immediate_skip_fences')) and row['scene']['skip'] == 1 if not skip_sent else row['scene']['skip'] == 1)
                                require(name + ' no swaps after skip cleanup', u16(o3.SCENE_SKIP_SWAPS) == u16(o3.SCENE_SWAPS))
                        expected_ordinal = min(ordinal + 1, len(entries) - 1)
                        terminal = ordinal == len(entries) - 1
                        next_state = legal.TITLE if terminal else legal.PLAYING if entries[ordinal + 1][0] == 'stage' else o3.SCENE
                        wait(lambda: u8(legal.CAMPAIGN_ORDINAL) == expected_ordinal and u16(legal.GAME_STATE) == next_state, 900, 'entry ' + str(ordinal) + ' next dispatch')
                        row['end'] = sample()
                        row['runtime_end'] = runtime_diagnostics()
                    if args.mode == 'easy':
                        require('bounded Easy control leaves TimesCompleted unchanged', u32(times) == times_before)
                        report['scope'] = 'Easy first three legal clears only; no full Easy completion claim'
                    else:
                        require('all requested compiler entries consumed in order', len(report['route']) == len(entries) - args.debug_start_ordinal)
                        require('completion credited exactly once', u32(times) == times_before + 1 & 4294967295 and u8(credited) == 1)
                        require('authored scene continuations exactly once', u16(l5.ENDS) - ends_before & 65535 == sum(e[0] == 'scene' for e in entries))
                        final_swaps = u16(o3.SCENE_SWAPS)
                        final_ends = u16(l5.ENDS)
                        for _ in range(180):
                            tick()
                            if not u32(times) != times_before + 1 & 4294967295:
                                if not u16(legal.GAME_STATE) != legal.TITLE:
                                    if not u8(credited) != 1:
                                        if not u16(l5.ENDS) != final_ends:
                                            if u8(legal.CAMPAIGN_ORDINAL) != len(entries) - 1:
                                                require('TITLE dwell retains exactly-once completion', False)
                                        else:
                                            require('TITLE dwell retains exactly-once completion', False)
                                    else:
                                        require('TITLE dwell retains exactly-once completion', False)
                                else:
                                    require('TITLE dwell retains exactly-once completion', False)
                            else:
                                require('TITLE dwell retains exactly-once completion', False)
                        require('TITLE dwell has no late scene swaps', u16(o3.SCENE_SWAPS) == final_swaps)
                    report['times_after'] = u32(times)
                    report['final'] = sample()
                    report['final']['selected_source_set'] = u8(symbols['BorSet_Selected'])
                    report['final']['completion_credited'] = u8(credited)
                    require('terminal completion retains selected source set',
                            report['final']['selected_source_set'] == set_index)
                    report['runtime_final'] = runtime_diagnostics()
                    if traversal:
                        harvest()
                        require('all authored source spawn identities and every control record observed', len(report['spawn_traversal']['completed']) == len(plan))
                        report['spawn_traversal']['status'] = 'PASS'
                else:
                    target_ordinal
                    raise AssertionError('--debug-start-ordinal is outside the compiled campaign')
            else:
                raise AssertionError('--debug-start-ordinal requires natural source-set traversal')
        else:
            if args.two_player:
                require('both co-op players are live at campaign start', u8(symbols['G13_P1Out']) == 0 and (u8(symbols['G13_P2Out']) == 0 and u8(symbols['G13_TwoPlayerEnabled']) == 1))
            times_before = u32(times)
            ends_before = u16(l5.ENDS)
            consumed_before = u16(symbols['SceneVideo_TestRequestConsumed'])
            seen_before = u16(symbols['SceneVideo_TestRequestSeen'])
            report['times_before'] = times_before
            require('new run completion latch is clear', u8(credited) == 0)

            def sample():
                result = dict(state=u16(legal.GAME_STATE), ordinal=u8(legal.CAMPAIGN_ORDINAL), stage=u16(legal.STAGE_INDEX), campaign=u8(legal.CAMPAIGN_ID), times=u32(times), complete=u8(complete_active))
                if traversal:
                    mailbox = bytes(read_block(m, 73728, 32, mem_type='snesSaveRam'))
                    dma_active = [u8(8258692 + i * 8) for i in range(8)]
                    result.update(*(), **{'spawn_index': u8(legal.SPAWN_INDEX), 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(symbols['Screen_PosX']), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + u8(legal.SPAWN_INDEX) * 10) if u8(legal.SPAWN_INDEX) < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'spawn_gate': dict(last_enemy_count=u8(8280221), last_kind=u8(8280211), last_roster=u8(8280231), last_slot_offset=u16(8280239), hole_count=u8(symbols['Spawn_HoleCount']), timer_pending=[u16(8280328 + i * 2) for i in range(6)], timer_fault=u16(8280326)), 'presentation_gate': dict(nmi_frame_busy=u8(8278016), nmi_busy=u8(8278017), nmi_frame_over=u8(8278018), nmi_frame_counter=u16(8278051), stage_water=dict(enabled=u8(8368677), mode=u8(8368678), pending=u8(8368676), dirty=u8(8368692), saved_busy=u8(8368696), held=u8(8368697)), frontpanel=dict(active=u8(8315040), dma_pending=u8(8315041), fault=u8(8315042), booting=u8(8315043), saved_busy=u8(8315066), loaded=u8(8315072), pending_column=u16(8267342), pending_tile=u16(8267352), budget=u8(8267358)), dma_queue=dict(current_slot=u16(8258680), budget=u16(8258682), process_remaining=u16(8258686), slot_type_flags=dma_active, active_count=sum((1 for value in dma_active if value & 64)))), 'msu_stream_busy': u8(symbols['Msu1_StreamBusy']), 'worker_mailbox': dict(target=int.from_bytes(mailbox[2:4], 'little'), completed=int.from_bytes(mailbox[4:6], 'little'), fault=int.from_bytes(mailbox[8:10], 'little'), error=mailbox[10], mutation_fence=mailbox[12]), 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'input_last_raw': u16(8258588), 'p1_hp': u8(legal.ENTITIES[0] + symbols['CHAR_HP']), 'p1_lives': u16(symbols['P1_Lives16']), 'p1_out': u8(symbols['G13_P1Out']), 'credits': u8(symbols['Game_Credits']), 'p1_x': u16(legal.ENTITIES[0] + symbols['CHAR_POS_X']), 'p1_y': u8(legal.ENTITIES[0] + symbols['CHAR_POS_Y']), 'p1_selected': u8(legal.ENTITIES[0] + symbols['CHAR_SELECTED']), 'p1_fall_timer': u8(legal.ENTITIES[0] + symbols['CHAR_FALL_STATE_TIMER']), 'p1_frame': u8(legal.ENTITIES[0] + symbols['CHAR_FRAME_INDEX']), 'p1_tick': u8(legal.ENTITIES[0] + symbols['CHAR_TICK_COUNTER'])})
                    if args.two_player:
                        p2 = 8260096 + symbols['CHAR_ZP_LEN']
                        result.update(p2_hp=u8(p2 + symbols['CHAR_HP']), p2_lives=u16(symbols['G13_P2Lives']), p2_out=u8(symbols['G13_P2Out']), p2_x=u16(p2 + symbols['CHAR_POS_X']), p2_y=u8(p2 + symbols['CHAR_POS_Y']), p2_selected=u8(p2 + symbols['CHAR_SELECTED']), p2_fall_timer=u8(p2 + symbols['CHAR_FALL_STATE_TIMER']), p2_frame=u8(p2 + symbols['CHAR_FRAME_INDEX']), p2_tick=u8(p2 + symbols['CHAR_TICK_COUNTER']))
                    actors = []
                    for slot in range(1, 6):
                        base = 8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_ZP_LEN'] * slot
                        obj = u8(base + symbols['OOP_SELF_SLOT_OFS'])
                        actors.append(dict(*(), **{'slot': slot, 'hp': u8(base + symbols['CHAR_HP']), 'input': u8(base + symbols['CHAR_INPUT_DRIVEN']), 'roster': u8(base + symbols['CHAR_ROSTER_INDEX']), 'selected': u8(base + symbols['CHAR_SELECTED']), 'facing_left': u8(base + symbols['CHAR_FACING_LEFT']), 'fall_timer': u8(base + symbols['CHAR_FALL_STATE_TIMER']), 'fall_frames': u8(base + symbols['CHAR_FALL_FCOUNT']), 'throw_zpos': u16(base + symbols['CHAR_THROW_ZPOS']), 'throw_zvel': u16(base + symbols['CHAR_THROW_ZVEL']), 'drop_state': u16(symbols['StageEnv_Actors'] + slot * symbols['CHAR_ZP_LEN'] + 102), 'hit_stun': u8(base + symbols['CHAR_HIT_STUN']), 'grab_target': u8(base + symbols['CHAR_GRAB_TARGET']), 'grabbed_by': u8(base + symbols['CHAR_GRABBED_BY']), 'x': u16(base + symbols['CHAR_POS_X']), 'y': u8(base + symbols['CHAR_POS_Y']), 'idle': u8(base + symbols['CHAR_IDLE_FCOUNT']), 'object_num': u16(base + symbols['OOP_SELF_NUM_OFS']), 'object_slot': obj, 'object_live': obj < symbols['OOP_MAX_OBJECTS'] * 2 and (obj % 2 == 0 and (u16(symbols['OopFlags'] + obj) & 1 == 1 and (u16(symbols['OopDp'] + obj) == base % 65536 and u16(symbols['OopNum'] + obj) == u16(base + symbols['OOP_SELF_NUM_OFS']))))}))
                    result['npc_slots'] = actors
                return result

            def scene_observation():
                observation = dict(game=sample(), fields={})
                observation['runtime'] = runtime_diagnostics()
                observation['msu_stream_busy'] = u8(symbols['Msu1_StreamBusy'])
                widths = {1: 'TestActive TestError TestErrorCode MsuDmaProbe PlayState PlaySkipCount SkipPending SequenceActive SequenceSkipCount RequestedSceneId Continuation SequenceSceneId SequenceClipOrdinal SequenceClipId SequenceClipCount TestBuffer', 2: 'TestRequest TestRequestSeen TestRequestConsumed TestHandlerEntries TestFrameIndex PlayPresented PlaySwaps PlayCompletion SequenceCompletion SequenceTransitions SequenceClipOffset LoadCount LoadStartNmi LoadEndNmi LoadCheckpoints TestWidth TestHeight TestLengthLo TestLengthHi TestMapBytes TestTileBytes TestPaletteBytes', 4: 'TestPayloadBase TestPayloadSize TestFramePointer TestFrameOffset TestFrameCount SequenceFrameCount'}
                for width, suffixes in widths.items():
                    for suffix in suffixes.split():
                        name = 'SceneVideo_' + suffix
                        address = symbols[name]
                        observation['fields'][name] = dict(address=address, width=width, value=int.from_bytes(bytes(read_block(m, address, 32)[:width]), 'little'))
                observation['request_latch_low'] = u8(symbols['SceneVideo_TestRequest'])
                observation['status_note'] = 'No SceneVideo_TestStatus symbol; TestError/TestErrorCode and PlayState are actual status fields.'
                size = symbols['DMA_QUEUE_SLOT_SIZE']
                count = symbols['DMA_QUEUE_SLOTS']
                queue = list(read_block(m, symbols['DmaQueue'], max(32, size * count)))
                observation['pending_dma'] = dict(address=symbols['DmaQueue'], raw=queue, active_slots=[i for i in range(count) if queue[i * size + 4] & symbols['DMA_OPT_ACTIVE']])
                try:
                    cpu = m.get_cpu_state()
                    observation['cpu'] = cpu
                    observation['cpu_pc'] = cpu['k'] << 16 | cpu['pc']
                except Exception as error:
                    observation['cpu_pc_unavailable'] = f'{type(error).__name__}: {error}'
                return observation

            def queue_source_unlink(offset, stage_index, record_index, roster, object_num):
                m.pause()
                try:
                    if u16(8263516) == 0 or u16(symbols['S6Host_Mode']) not in (1, 3) or u16(8263518) not in (1, 2):
                        return None
                    control = bytes(read_block(m, 74816, 32, mem_type='snesSaveRam'))
                    request_seq = int.from_bytes(control[0:2], 'little')
                    ack_seq = int.from_bytes(control[2:4], 'little')
                    if request_seq != ack_seq:
                        return None
                    apply_tick = u16(symbols['S6Game_TickCommit']) + 1 & 65535
                    handle = 2560 + offset
                    m.write_u16(74820, handle, mem_type='snesSaveRam')
                    m.write_u16(74822, apply_tick, mem_type='snesSaveRam')
                    m.write_u16(74816, request_seq + 1 & 65535, mem_type='snesSaveRam')
                finally:
                    m.resume()
                return dict(sequence=request_seq + 1 & 65535, ack_before=ack_seq, handle=handle, apply_tick=apply_tick, roster=roster, object_num=object_num, record_index=record_index, source='sequenced_worker_remove')

            def accelerate(stage_index):
                nonlocal observer_last_change_field, observer_last_stage
                if traversal:
                    harvest()
                    if observer_last_stage != stage_index:
                        observer_last_stage = stage_index
                        observer_last_change_field = report['frames_sampled']
                    stale_limit = 30 if getattr(args, 'trace_runtime', False) else TRAVERSAL_STALL_LIMIT_FIELDS if traversal else 120
                    stale_fields = observer_stale_fields(stage_index, observer_last_stage, report['frames_sampled'], observer_last_change_field)
                    continue_available = bool(u8(symbols['Game_Credits']) and (u8(symbols['G13_P1Out']) or (args.two_player and u8(symbols['G13_P2Out']))))
                    spawn_index = u8(legal.SPAWN_INDEX)
                    spawn_count = u8(legal.SPAWN_COUNT)
                    if report['spawn_traversal']['observer_status'].startswith('TICK '):
                        if observer_spawn_watchdog_due(spawn_index, spawn_count, stale_fields, stale_limit):
                            if not continue_available:
                                report['last_observation'] = sample()
                                report['stale_observer_diagnostics'] = dict(stale_fields=stale_fields, stage=stage_index, observer_status=observer_last_status, runtime=runtime_diagnostics(), source_queue_debug=bytes(read_block(m, 8275416, 32)[:8]).hex())
                                trace_name = report['spawn_traversal'].get('bind_trace')
                                if trace_name:
                                    trace_path = Path(trace_name)
                                    if trace_path.is_file():
                                        report['stale_observer_diagnostics']['bind_trace_tail'] = trace_path.read_text(errors='replace').splitlines()[-160:]
                                raise AssertionError('Spawn_Play heartbeat stopped changing for ' + str(stale_limit) + ' playing fields')
                    if retirement_pending:
                        remove_control = bytes(read_block(m, 74816, 32, mem_type='snesSaveRam'))
                        events = bytes(read_block(m, 74800, 32, mem_type='snesSaveRam'))
                        remove_ack = int.from_bytes(remove_control[2:4], 'little')
                        event_head = int.from_bytes(events[0:2], 'little')
                        event_tail = int.from_bytes(events[2:4], 'little')
                    for key, identity in list(retirement_pending.items()):
                        pending_stage, offset = key
                        if not pending_stage != stage_index:
                            if 'sequence' in identity:
                                if event_head == event_tail:
                                    if not remove_ack - identity['sequence'] & 65535 < 32768:
                                        base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                        if not u8(base + symbols['CHAR_ROSTER_INDEX']) != identity['roster']:
                                            if not u16(base + symbols['OOP_SELF_NUM_OFS']) != identity['object_num']:
                                                if u8(base + symbols['CHAR_HP']):
                                                    return None
                                else:
                                    base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                    if not u8(base + symbols['CHAR_ROSTER_INDEX']) != identity['roster']:
                                        if not u16(base + symbols['OOP_SELF_NUM_OFS']) != identity['object_num']:
                                            if u8(base + symbols['CHAR_HP']):
                                                return None
                            else:
                                base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                if not u8(base + symbols['CHAR_ROSTER_INDEX']) != identity['roster']:
                                    if not u16(base + symbols['OOP_SELF_NUM_OFS']) != identity['object_num']:
                                        if u8(base + symbols['CHAR_HP']):
                                            return None
                        retirement_pending.pop(key, None)
                    index = u8(legal.SPAWN_INDEX)
                    count = u8(legal.SPAWN_COUNT)
                    retired_offsets = []
                    for offset, (receipt, first_field) in admitted.items():
                        base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                        bridge = symbols['StageEnv_Actors'] + offset
                        worker_bridge = bytes(read_block(m, 73984 + offset, 133, mem_type='snesSaveRam'))
                        if not receipt['stage'] != stage_index:
                            if not report['frames_sampled'] - first_field < 2:
                                if not u8(base + symbols['CHAR_ROSTER_INDEX']) != receipt['roster']:
                                    if not u16(base + symbols['OOP_SELF_NUM_OFS']) != receipt['object_num']:
                                        if not u8(base + symbols['CHAR_INPUT_DRIVEN']) not in (symbols['CHAR_INPUT_DRIVEN_AI'], symbols['CHAR_INPUT_DRIVEN_BIKER']):
                                            if u8(base + symbols['CHAR_IDLE_FCOUNT']):
                                                if u8(base + symbols['CHAR_HP']):
                                                    if not not bridge_owns_source_actor(u8(bridge + 64), u8(bridge + 65), u16(bridge + 68), worker_bridge[64], worker_bridge[65], int.from_bytes(worker_bridge[68:70], 'little')):
                                                        grab_target = u8(base + symbols['CHAR_GRAB_TARGET'])
                                                        grabbed_by = u8(base + symbols['CHAR_GRABBED_BY'])
                                                        if not grab_target != 255:
                                                            if not grabbed_by != 255:
                                                                request = queue_source_unlink(offset, stage_index, receipt['index'], receipt['roster'], receipt['object_num'])
                                                                if request is None:
                                                                    return None
                                                                report['spawn_traversal']['unlink_accelerations'].append(dict(stage=stage_index, index=receipt['index'], offset=offset, roster=receipt['roster'], object_num=receipt['object_num'], delay_fields=report['frames_sampled'] - first_field, request=request))
                                                                retirement_pending[stage_index, offset] = dict(roster=receipt['roster'], object_num=receipt['object_num'], sequence=request['sequence'])
                                                                retired_offsets.append(offset)
                    initial_path = journal.with_suffix('.initial-ai.txt')
                    initial_rows = []
                    initial_captured = False
                    initial_encounter_active = False
                    if initial_path.exists():
                        for line in initial_path.read_text().splitlines():
                            values = list(map(int, line.split()))
                            if not values[0] != stage_index:
                                if values[1] == -1:
                                    initial_captured = True
                                else:
                                    initial_rows.append(values)
                    if initial_captured:
                        if report['frames_sampled'] % 120 == 0:
                            if initial_captured:
                                progress = dict(field=report['frames_sampled'], stage=stage_index, spawn_index=u8(legal.SPAWN_INDEX), spawn_count=u8(legal.SPAWN_COUNT), source_tick=u16(8263484), game_tick_commit=u16(symbols['S6Game_TickCommit']), camera_x=u16(legal.SCREEN_POS_X), player=dict(hp=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_HP']), x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), lives=u16(symbols['P1_Lives16']), out=u8(symbols['G13_P1Out']), fall_timer=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_FALL_STATE_TIMER'])), worker=runtime_diagnostics(), initial_ai=[])
                                for _, slot, offset, roster, object_num, input_mode in initial_rows:
                                    base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                                    progress['initial_ai'].append(dict(slot=slot, offset=offset, roster=roster, object_num=object_num, hp=u8(base + symbols['CHAR_HP']), x=u16(base + symbols['CHAR_POS_X']), y=u8(base + symbols['CHAR_POS_Y']), selected=u8(base + symbols['CHAR_SELECTED']), attack=u8(base + symbols['CHAR_ATTACK_FCOUNT']), hit_stun=u8(base + symbols['CHAR_HIT_STUN']), grab_target=u8(base + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(base + symbols['CHAR_GRABBED_BY'])))
                                journal.with_suffix('.progress.json').write_text(json.dumps(progress, separators=(',', ':')) + '\n', encoding='utf-8')
                        for _, slot, offset, roster, object_num, input_mode in initial_rows:
                            base = 8257536 + symbols['PlayerEntity_DpBase'] + offset
                            obj = u8(base + symbols['OOP_SELF_SLOT_OFS'])
                            object_live = obj < symbols['OOP_MAX_OBJECTS'] * 2 and (obj % 2 == 0 and (bool(u16(symbols['OopFlags'] + obj) & 1) and (u16(symbols['OopDp'] + obj) == base % 65536 and u16(symbols['OopNum'] + obj) == object_num)))
                            identity = u8(base + symbols['CHAR_ROSTER_INDEX']) == roster and (u16(base + symbols['OOP_SELF_NUM_OFS']) == object_num and (u8(base + symbols['CHAR_INPUT_DRIVEN']) == input_mode and (u8(base + symbols['CHAR_HP']) > 0 and object_live)))
                            key = (stage_index, offset, object_num)
                            if identity:
                                if key not in initial_ai_reported:
                                    report['spawn_traversal']['initial_ai_combat_targets'].append(dict(stage=stage_index, slot=slot, offset=offset, roster=roster, object_num=object_num, input=input_mode, hp=u8(base + symbols['CHAR_HP']), x=u16(base + symbols['CHAR_POS_X']), y=u8(base + symbols['CHAR_POS_Y']), handling='real player input and native lifecycle'))
                                    initial_ai_reported.add(key)
                            initial_encounter_active = initial_encounter_active | identity
                    for offset in retired_offsets:
                        admitted.pop(offset, None)
                    if retired_offsets:
                        return None
                    if initial_encounter_active:
                        return None
                    if index < count:
                        return None
                else:
                    m.write_u8(legal.SPAWN_INDEX, u8(legal.SPAWN_COUNT))
                direction = build.STAGE_CONFIGS[stage_index].get('scroll_direction', 'right')
                if direction == 'left':
                    edge = u16(min_x)
                    if edge == 0:
                        AssertionError('left clear predicate requires positive Screen_MinX')
                    m.write_u16(legal.SCREEN_POS_X, edge)
                elif direction == 'down':
                    m.write_u16(pos_y, u16(max_y))
                else:
                    m.write_u16(legal.SCREEN_POS_X, u16(legal.STAGE_TRUE_MAX_X))
                for base in () if traversal else legal.ENTITIES[1:]:
                    if u8(base + legal.CHAR_INPUT_DRIVEN) == legal.CHAR_INPUT_DRIVEN_AI:
                        m.write_u8(base + legal.CHAR_HP, 0)
            limit_entries = 3 if args.mode == 'easy' else len(entries)
            start_ordinal = args.debug_start_ordinal
            for ordinal, (kind, value, name) in enumerate(entries[start_ordinal:limit_entries], start=start_ordinal):
                if traversal:
                    if kind == 'stage':
                        tick(None, hold=True)
                        harvest()
                current = sample()
                require('entry ' + str(ordinal) + ' native order/identity', current['ordinal'] == ordinal and (current['campaign'] == campaign_id and (current['times'] == times_before and (current['state'] == (legal.PLAYING if kind == 'stage' else o3.SCENE) and (current['stage'] == value if kind == 'stage' else u8(o3.SCENE_ID) == value)))))
                row = dict(ordinal=ordinal, kind=kind, source=name, physical_or_scene=value, next_after=bool(authored[ordinal]['next_after']), start=current)
                row['runtime_start'] = runtime_diagnostics()
                row['completion_expected'] = bool(completion_flags[ordinal])
                report['route'].append(row)
                traversal_buttons = None
                traversal_p2_buttons = None
                continue_waiting = False
                continue_last_field = None
                continue_p2_waiting = False
                continue_p2_last_field = None
                if traversal:
                    if kind == 'stage':
                        direction = build.STAGE_CONFIGS[value].get('scroll_direction', 'right')
                        traversal_buttons = m.BTN_LEFT if direction == 'left' else m.BTN_DOWN if direction == 'down' else m.BTN_RIGHT
                        if args.two_player:
                            traversal_p2_buttons = m.BTN_RIGHT if direction == 'left' else m.BTN_UP if direction == 'down' else m.BTN_DOWN if direction == 'up' else m.BTN_LEFT
                        row['traversal_input'] = 'real directional transit; Y attacks only while engaging a live blocker; real Y-overlap collection for authored 1UP/needed health pickups; ordinary walking speed keeps player/camera trigger traversal aligned; after a full-slot queue stall, approach/attack a live native prop before transit; real per-player Start edges only for OUT players'
                        row['continue_inputs'] = []
                else:
                    m.release_input(port=0)
                    if args.two_player:
                        m.release_input(port=1)
                if args.screenshots:
                    row['screenshot'] = m.take_screenshot()
                saw_complete = False
                skip_sent = False
                scene_before = None
                if kind == 'scene':
                    scene_before = l5.snapshot(m)
                    row['activation_start'] = scene_observation()
                    scene_number = sum((e[0] == 'scene' for e in entries[:ordinal + 1]))

                    def immediate_skip_fences():
                        terminal_scene = ordinal == len(entries) - 1
                        state = sample()
                        if terminal_scene:
                            return dict(skip_mode=args.mode == 'skip', preceding_real_skip=bool(ordinal and report['route'][-2].get('skip_sent')), consumed_once=u16(symbols['SceneVideo_TestRequestConsumed']) - consumed_before & 65535 == scene_number, seen_once=u16(symbols['SceneVideo_TestRequestSeen']) - seen_before & 65535 == scene_number, scene_id=u8(o3.SCENE_ID) == value and u8(symbols['SceneVideo_SequenceSceneId']) == value, inactive=u8(o3.SCENE_ACTIVE) == 0, clean=u8(symbols['SceneVideo_TestError']) == 0 and u8(symbols['SceneVideo_TestErrorCode']) == 0, skipped_once=u8(o3.SCENE_SKIP) == 1 and u16(o3.SCENE_COMPLETE) == 0, input_edge=bool(u16(symbols['SceneVideo_InputTriggerAtSkip']) & 53488), ends_once=u16(l5.ENDS) - ends_before & 65535 == scene_number, campaign=state['campaign'] == campaign_id, destination=state['state'] == legal.TITLE and state['ordinal'] == ordinal if terminal_scene else state['ordinal'] == ordinal + 1 and (state['state'] == legal.PLAYING and state['stage'] == entries[ordinal + 1][1]), credit=state['times'] == times_before + 1 & 4294967295 and u8(credited) == 1)
                        return dict(skip_mode=args.mode == 'skip', preceding_real_skip=bool(ordinal and report['route'][-2].get('skip_sent')), consumed_once=u16(symbols['SceneVideo_TestRequestConsumed']) - consumed_before & 65535 == scene_number, seen_once=u16(symbols['SceneVideo_TestRequestSeen']) - seen_before & 65535 == scene_number, scene_id=u8(o3.SCENE_ID) == value and u8(symbols['SceneVideo_SequenceSceneId']) == value, inactive=u8(o3.SCENE_ACTIVE) == 0, clean=u8(symbols['SceneVideo_TestError']) == 0 and u8(symbols['SceneVideo_TestErrorCode']) == 0, skipped_once=u8(o3.SCENE_SKIP) == 1 and u16(o3.SCENE_COMPLETE) == 0, input_edge=bool(u16(symbols['SceneVideo_InputTriggerAtSkip']) & 53488), ends_once=u16(l5.ENDS) - ends_before & 65535 == scene_number, campaign=state['campaign'] == campaign_id, destination=state['state'] == legal.TITLE and state['ordinal'] == ordinal if terminal_scene else state['ordinal'] == ordinal + 1 and (state['state'] == legal.PLAYING and state['stage'] == entries[ordinal + 1][1]), credit=state['times'] == times_before and u8(credited) == 0)

                    def activated_or_skipped():
                        if u8(o3.SCENE_ACTIVE) == 165:
                            return True
                        fences = immediate_skip_fences()
                        if all(fences.values()):
                            row['immediate_skip_fences'] = fences
                            row['immediate_skip_observation'] = scene_observation()
                            return True
                        return False

                    def activation_timeout():
                        row['activation_timeout'] = scene_observation()
                        row['activation_timeout']['immediate_skip_fences'] = immediate_skip_fences()
                        row['activation_timeout']['wait_fields'] = 120
                        report['last_observation'] = row['activation_timeout']['game']
                    wait(activated_or_skipped, 120, name + ' activates or fenced immediate skip', on_timeout=activation_timeout)
                    require(name + ' campaign scene continuation', u8(o3.SCENE_CONT) == 1)
                    track = pasm_constant_in('tools/audio/audio_music_ids.pasm', 'Music_EndingTrack' if name == 'ENDING' else 'Music_SceneTrack_' + name)
                    require(name + ' source scene audio selection', u8(o3.SCENE_TRACK) == track and u8(o3.SCENE_REPEAT) == (name in ('ENDING', 'SEWER')))
                budget = SCENE_FIELD_BUDGET if kind == 'scene' else args.stage_fields
                last_spawn_index = u8(legal.SPAWN_INDEX) if kind == 'stage' else 0
                last_spawn_change_elapsed = 0
                for elapsed in range(budget):
                    state = sample()
                    report['last_observation'] = state
                    if kind == 'scene':
                        if elapsed % 300 == 0:
                            progress = scene_observation()
                            progress['elapsed_fields'] = elapsed
                            row.setdefault('scene_progress', []).append(progress)
                    if not state['ordinal'] != ordinal:
                        if state['state'] == legal.TITLE:
                            if traversal:
                                if state['state'] == legal.TITLE:
                                    if ordinal != len(entries) - 1:
                                        row['unexpected_exit'] = state
                                        harvest()
                                        raise AssertionError('entry ' + str(ordinal) + ' premature TITLE, not campaign progression')
                            break
                        if not state['campaign'] != campaign_id:
                            if state['times'] != times_before:
                                require('no premature campaign/TimesCompleted change', False)
                        else:
                            require('no premature campaign/TimesCompleted change', False)
                        button = None
                        button2 = None
                        target_probe = None
                        if kind == 'stage':
                            if state['complete']:
                                saw_complete = True
                                if args.mode != 'natural':
                                    if not skip_sent:
                                        button = m.BTN_A
                                        skip_sent = True
                            elif state['state'] == legal.PLAYING:
                                if traversal:
                                    from byor_native_interaction import sample as sample_native_interaction
                                    sample_native_interaction(m, symbols, report)
                                accelerate(value)
                                if traversal:
                                    current_spawn_index = u8(legal.SPAWN_INDEX)
                                    if current_spawn_index != last_spawn_index:
                                        last_spawn_index = current_spawn_index
                                        last_spawn_change_elapsed = elapsed
                                    spawn_stalled = current_spawn_index < u8(legal.SPAWN_COUNT) and elapsed - last_spawn_change_elapsed >= 24
                                    if not u8(symbols['G13_P1Out']):
                                        continue_waiting = False
                                        continue_last_field = None
                                    if traversal_continue_needed(u8(symbols['G13_P1Out']), u8(symbols['Game_Credits'])):
                                        if continue_waiting:
                                            if not continue_last_field is None:
                                                if elapsed - continue_last_field >= 30:
                                                    button = m.BTN_START
                                                    continue_waiting = True
                                                    continue_last_field = elapsed
                                                    row['continue_inputs'].append(dict(elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                            else:
                                                button = m.BTN_START
                                                continue_waiting = True
                                                continue_last_field = elapsed
                                                row['continue_inputs'].append(dict(elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                        else:
                                            button = m.BTN_START
                                            continue_waiting = True
                                            continue_last_field = elapsed
                                            row['continue_inputs'].append(dict(elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                    if args.two_player:
                                        if not u8(symbols['G13_P2Out']):
                                            continue_p2_waiting = False
                                            continue_p2_last_field = None
                                        if traversal_continue_needed(u8(symbols['G13_P2Out']), u8(symbols['Game_Credits'])):
                                            if continue_p2_waiting:
                                                if not continue_p2_last_field is None:
                                                    if elapsed - continue_p2_last_field >= 30:
                                                        button2 = m.BTN_START
                                                        continue_p2_waiting = True
                                                        continue_p2_last_field = elapsed
                                                        row['continue_inputs'].append(dict(player=2, elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                                else:
                                                    button2 = m.BTN_START
                                                    continue_p2_waiting = True
                                                    continue_p2_last_field = elapsed
                                                    row['continue_inputs'].append(dict(player=2, elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                            else:
                                                button2 = m.BTN_START
                                                continue_p2_waiting = True
                                                continue_p2_last_field = elapsed
                                                row['continue_inputs'].append(dict(player=2, elapsed_field=elapsed, credits_before=u8(symbols['Game_Credits'])))
                                    if button is None:
                                        if traversal_buttons is not None:
                                            button = traversal_buttons
                                            if not args.trace_player_move:
                                                p1 = 8257536 + symbols['PlayerEntity_DpBase']
                                                p1x = s16(p1 + symbols['CHAR_POS_X'])
                                                p1y = (s16(p1 + symbols['CHAR_POS_Y'])
                                                       if os.environ.get('S8_NORMAL_CANONICAL_P1_CONTROLLER') == '1'
                                                       else u8(p1 + symbols['CHAR_POS_Y']))
                                                raw_p1x = p1x
                                                world_max = u16(symbols['WorldMaxX'])
                                                if world_max:
                                                    if raw_p1x > world_max * 2:
                                                        raw_p1x = raw_p1x // 4
                                                world_player_x = p1x
                                                world_player_y = p1y
                                                world_actor_rows = None
                                                if spawn_stalled:
                                                    world_actor_rows = bytes(read_block(m, 71936, 1536, mem_type='snesSaveRam'))
                                                    world_player_x = int.from_bytes(world_actor_rows[20:22], 'little', signed=True)
                                                    world_player_y = int.from_bytes(world_actor_rows[22:24], 'little', signed=True)
                                                prop_targets = []
                                                pickup_targets = []
                                                combat_targets = []
                                                group_enemy_count = 0
                                                for slot in range(1, 6):
                                                    actor = p1 + slot * symbols['CHAR_ZP_LEN']
                                                    mode = u8(actor + symbols['CHAR_INPUT_DRIVEN'])
                                                    hp = u8(actor + symbols['CHAR_HP'])
                                                    object_num = u16(actor + symbols['OOP_SELF_NUM_OFS'])
                                                    roster = u8(actor + symbols['CHAR_ROSTER_INDEX'])
                                                    if hp:
                                                        if args.two_player:
                                                            if not slot == 1:
                                                                if mode not in (symbols['CHAR_INPUT_DRIVEN_PROP'], symbols['CHAR_INPUT_DRIVEN_STEAMER'], symbols['CHAR_INPUT_DRIVEN_STEAM']):
                                                                    group_enemy_count = group_enemy_count + 1
                                                        elif mode not in (symbols['CHAR_INPUT_DRIVEN_PROP'], symbols['CHAR_INPUT_DRIVEN_STEAMER'], symbols['CHAR_INPUT_DRIVEN_STEAM']):
                                                            group_enemy_count = group_enemy_count + 1
                                                    if mode in (symbols['CHAR_INPUT_DRIVEN_AI'], symbols['CHAR_INPUT_DRIVEN_BIKER']):
                                                        identity = (value, slot, object_num, roster, mode)
                                                        previous_hp = combat_hp_seen.get(identity)
                                                        if previous_hp is not None:
                                                            if previous_hp != hp:
                                                                report['spawn_traversal']['combat_interactions'].append(dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, previous_hp=previous_hp, hp=hp, field=report['frames_sampled']))
                                                        combat_hp_seen[identity] = hp
                                                        if hp:
                                                            bridge = symbols['StageEnv_Actors'] + slot * 133
                                                            worker_bridge = bytes(read_block(m, 73984 + slot * 133, 133, mem_type='snesSaveRam'))
                                                            worker_owned = world_actor_rows is not None and bridge_owns_source_actor(u8(bridge + 64), u8(bridge + 65), u16(bridge + 68), worker_bridge[64], worker_bridge[65], int.from_bytes(worker_bridge[68:70], 'little'))
                                                            if worker_owned:
                                                                source_actor = slot * 256
                                                                source_xy = (int.from_bytes(world_actor_rows[source_actor + 20:source_actor + 22], 'little', signed=True), int.from_bytes(world_actor_rows[source_actor + 22:source_actor + 24], 'little', signed=True))
                                                            else:
                                                                source_xy = (s16(actor + symbols['CHAR_POS_X']), u8(actor + symbols['CHAR_POS_Y']))
                                                            ax, ay = traversal_actor_coordinates(mode, worker_owned, symbols['CHAR_INPUT_DRIVEN_AI'], source_xy, (s16(actor + symbols['CHAR_POS_X']), u8(actor + symbols['CHAR_POS_Y'])))
                                                            target_player_x, target_player_y = (world_player_x, world_player_y) if worker_owned else (raw_p1x, p1y)
                                                            facing_left = u8(actor + symbols['CHAR_FACING_LEFT'])
                                                            biker_approaching = mode == symbols['CHAR_INPUT_DRIVEN_BIKER'] and traversal_biker_approaches(target_player_x, ax, facing_left)
                                                            combat_targets.append((abs(ax - target_player_x) + abs(ay - target_player_y), slot, ax, ay, object_num, roster, mode, hp, worker_owned, biker_approaching))
                                                    if not mode not in (symbols['CHAR_INPUT_DRIVEN_PROP'], symbols['CHAR_INPUT_DRIVEN_STEAMER'], symbols['CHAR_INPUT_DRIVEN_STEAM']):
                                                        pickup_raw = u8(actor + symbols['CHAR_PICKUP_TYPE'])
                                                        pickup_type = pickup_raw & 127
                                                        identity = (value, slot, object_num, roster, mode)
                                                        previous_hp = prop_hp_seen.get(identity)
                                                        if previous_hp is not None:
                                                            if previous_hp != hp:
                                                                report['spawn_traversal']['prop_interactions'].append(dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, previous_hp=previous_hp, hp=hp, field=report['frames_sampled']))
                                                        prop_hp_seen[identity] = hp
                                                        pickup_identity = (value, slot, object_num, roster)
                                                        previous_pickup = pickup_type_seen.get(pickup_identity, 0)
                                                        if pickup_type:
                                                            pickup_type_seen[pickup_identity] = pickup_type
                                                        elif previous_pickup:
                                                            prop_x = s16(actor + symbols['CHAR_POS_X'])
                                                            prop_y = u8(actor + symbols['CHAR_POS_Y'])
                                                            report['spawn_traversal']['pickup_interactions'].append(dict(stage=value, slot=slot, object_num=object_num, roster=roster, pickup_type=previous_pickup, result=('collected' if prop_x == 32767 else 'removed') if hp else 'removed', hp=hp, x=prop_x, y=prop_y, field=report['frames_sampled']))
                                                            pickup_type_seen.pop(pickup_identity, None)
                                                        if not not hp:
                                                            ax = s16(actor + symbols['CHAR_POS_X'])
                                                            ay = u8(actor + symbols['CHAR_POS_Y'])
                                                            prop_targets.append((slot, ax, ay, object_num, roster, mode, hp, False, False))
                                                            player_hp = u8(symbols['PlayerEntity_Hp'])
                                                            player_hp_max = symbols.get('CHAR_HP_MAX', 64)
                                                            two_player_only = bool(pickup_raw & 128) and (not args.two_player)
                                                            if pickup_type:
                                                                if not two_player_only:
                                                                    if traversal_pickup_needed(pickup_type, player_hp, player_hp_max):
                                                                        pickup_targets.append((slot, ax, ay, object_num, roster, mode, hp, False, False, pickup_type))
                                                all_slots_busy = traversal_slots_full(state['npc_slots'], symbols['CHAR_INPUT_DRIVEN_NONCOMBAT'])
                                                terminal_clamp = traversal_terminal_clamp(state)
                                                targets = []
                                                target_pickup_type = 0
                                                if pickup_targets:
                                                    pickup = min(pickup_targets, key=lambda target: traversal_target_key(target, raw_p1x, p1y, build.STAGE_CONFIGS[value].get('scroll_direction', 'right')))
                                                    targets = [pickup[:9]]
                                                    target_pickup_type = pickup[9]
                                                elif spawn_stalled:
                                                    if prop_targets:
                                                        targets = traversal_blocking_props(prop_targets, raw_p1x, p1y, symbols['CHAR_INPUT_DRIVEN_PROP'], terminal_clamp)
                                                group_gate_blocked = spawn_stalled and traversal_group_gate_blocks_spawn(group_enemy_count, state['spawn_group_min'])
                                                queue_complete = current_spawn_index >= u8(legal.SPAWN_COUNT)
                                                if combat_targets:
                                                    if not targets:
                                                        nearest = min(combat_targets, key=lambda target: target[0])
                                                        aim_x = world_player_x if nearest[8] else raw_p1x
                                                        aim_y = world_player_y if nearest[8] else p1y
                                                        if traversal_combat_engagement_needed(nearest, aim_x, aim_y, group_gate_blocked=group_gate_blocked, queue_complete=queue_complete, terminal=terminal_clamp, direction=build.STAGE_CONFIGS[value].get('scroll_direction', 'right')):
                                                            _, slot, ax, ay, object_num, roster, mode, hp, worker_owned, biker_approaching = nearest
                                                            targets = [(slot, ax, ay, object_num, roster, mode, hp, worker_owned, biker_approaching)]
                                                if targets:
                                                    direction = build.STAGE_CONFIGS[value].get('scroll_direction', 'right')
                                                    slot, ax, ay, object_num, roster, mode, hp, worker_owned, biker_approaching = min(targets, key=lambda target: traversal_target_key(target, world_player_x if target[7] else raw_p1x, world_player_y, direction) if target[7] else traversal_target_key(target, world_player_x if target[7] else raw_p1x, p1y, direction))
                                                    aim_x = world_player_x if worker_owned else raw_p1x
                                                    aim_y = world_player_y if worker_owned else p1y
                                                    dx = ax - aim_x
                                                    dy = ay - aim_y
                                                    target_probe = dict(slot=slot, x=ax, y=ay, dx=dx, dy=dy, mode=mode, worker_owned=worker_owned, biker_approaching=biker_approaching)
                                                    prop_slots_full = traversal_terminal_prop_clear_required(all_slots_busy, spawn_stalled, terminal_clamp) if mode == symbols['CHAR_INPUT_DRIVEN_PROP'] else all_slots_busy
                                                    prop_action = 'collect' if target_pickup_type else traversal_prop_chase_action(dx, dy, prop_slots_full) if mode == symbols['CHAR_INPUT_DRIVEN_PROP'] else None
                                                    prop_bypass_direction = None
                                                    target_probe['prop_bypass_direction'] = prop_bypass_direction
                                                    button = 0
                                                    if prop_action == 'collect':
                                                        pickup_action, attack_now = traversal_pickup_action(dx, dy, elapsed)
                                                        if pickup_action == 'approach_right':
                                                            button = button | m.BTN_RIGHT
                                                            if abs(dx) > 64:
                                                                button = button | m.BTN_B
                                                        elif pickup_action == 'approach_left':
                                                            button = button | m.BTN_LEFT
                                                            if abs(dx) > 64:
                                                                button = button | m.BTN_B
                                                        elif pickup_action == 'depth_down':
                                                            button = button | m.BTN_DOWN
                                                        elif pickup_action == 'depth_up':
                                                            button = button | m.BTN_UP
                                                        elif pickup_action == 'collect':
                                                            if abs(dx) > 4:
                                                                button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                            if attack_now:
                                                                button = button | m.BTN_Y
                                                    elif prop_action == 'bypass':
                                                        scroll = build.STAGE_CONFIGS[value].get('scroll_direction', 'right')
                                                        button = button | (m.BTN_LEFT if scroll == 'left' else m.BTN_RIGHT if scroll == 'right' else m.BTN_RIGHT if dx >= 0 else m.BTN_LEFT)
                                                        bypass_action = traversal_prop_bypass_action(dy)
                                                        if bypass_action == 'depth_up':
                                                            button = button | m.BTN_UP
                                                        elif bypass_action == 'depth_down':
                                                            button = button | m.BTN_DOWN
                                                    elif prop_action == 'lane':
                                                        button = button | (m.BTN_DOWN if dy > 0 else m.BTN_UP)
                                                        button = button | m.BTN_B
                                                    elif prop_action == 'detour':
                                                        button = button | (m.BTN_DOWN if dy < 0 else m.BTN_UP)
                                                    elif prop_action == 'approach':
                                                        button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                        if abs(dx) > 64:
                                                            button = button | m.BTN_B
                                                    elif prop_action == 'attack':
                                                        button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                        if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                            if not prop_slots_full:
                                                                if traversal_jump_held(elapsed):
                                                                    button = button | m.BTN_A
                                                            elif traversal_attack_held(elapsed):
                                                                button = button | m.BTN_Y
                                                        elif traversal_attack_held(elapsed):
                                                            button = button | m.BTN_Y
                                                    else:
                                                        if mode == symbols['CHAR_INPUT_DRIVEN_BIKER']:
                                                            biker_actor = 8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_ZP_LEN'] * slot
                                                            biker_mobile = u8(biker_actor + symbols['CHAR_SELECTED']) not in (symbols['CHAR_SELECTED_FALL'], symbols['CHAR_SELECTED_RISE'])
                                                            biker_action = traversal_biker_action(dx, dy, elapsed, mobile=biker_mobile, approaching=biker_approaching)
                                                            if biker_action == 'depth_down':
                                                                button = button | m.BTN_DOWN
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                    if traversal_combat_attack_opportunity(dx, dy):
                                                                        if traversal_attack_held(elapsed):
                                                                            button = button | m.BTN_Y
                                                                target = (value, slot, object_num, roster, mode)
                                                                if target != prop_target_last:
                                                                    interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                    if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                        report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                    else:
                                                                        report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                    prop_target_last = target
                                                                if args.two_player:
                                                                    if button2 is None:
                                                                        if traversal_p2_buttons is not None:
                                                                            if not u8(symbols['G13_P2Out']):
                                                                                button2 = traversal_p2_buttons
                                                                if traversal:
                                                                    button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                if traversal:
                                                                    if elapsed % 60 == 0:
                                                                        p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                        actors = []
                                                                        for probe_slot in range(1, 6):
                                                                            actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                            actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                        worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                        worker_player = worker_rows[0:256]
                                                                        spawn_index = u8(legal.SPAWN_INDEX)
                                                                        probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                        report['spawn_traversal']['controller_probe'].append(probe)
                                                                        report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                        controller_probe_path.write_text(json.dumps(probe))
                                                                tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                if traversal:
                                                                    if kind == 'stage':
                                                                        if button is not None:
                                                                            if button & m.BTN_Y:
                                                                                trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                continue
                                                            if biker_action == 'depth_up':
                                                                button = button | m.BTN_UP
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                    if traversal_combat_attack_opportunity(dx, dy):
                                                                        if traversal_attack_held(elapsed):
                                                                            button = button | m.BTN_Y
                                                                target = (value, slot, object_num, roster, mode)
                                                                if target != prop_target_last:
                                                                    interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                    if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                        report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                    else:
                                                                        report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                    prop_target_last = target
                                                                if args.two_player:
                                                                    if button2 is None:
                                                                        if traversal_p2_buttons is not None:
                                                                            if not u8(symbols['G13_P2Out']):
                                                                                button2 = traversal_p2_buttons
                                                                if traversal:
                                                                    button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                if traversal:
                                                                    if elapsed % 60 == 0:
                                                                        p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                        actors = []
                                                                        for probe_slot in range(1, 6):
                                                                            actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                            actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                        worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                        worker_player = worker_rows[0:256]
                                                                        spawn_index = u8(legal.SPAWN_INDEX)
                                                                        probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                        report['spawn_traversal']['controller_probe'].append(probe)
                                                                        report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                        controller_probe_path.write_text(json.dumps(probe))
                                                                tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                if traversal:
                                                                    if kind == 'stage':
                                                                        if button is not None:
                                                                            if button & m.BTN_Y:
                                                                                trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                continue
                                                            if biker_action == 'approach_right':
                                                                button = button | m.BTN_RIGHT
                                                                if abs(dx) > 32:
                                                                    button = button | m.BTN_B
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                    if traversal_combat_attack_opportunity(dx, dy):
                                                                        if traversal_attack_held(elapsed):
                                                                            button = button | m.BTN_Y
                                                                target = (value, slot, object_num, roster, mode)
                                                                if target != prop_target_last:
                                                                    interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                    if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                        report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                    else:
                                                                        report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                    prop_target_last = target
                                                                if args.two_player:
                                                                    if button2 is None:
                                                                        if traversal_p2_buttons is not None:
                                                                            if not u8(symbols['G13_P2Out']):
                                                                                button2 = traversal_p2_buttons
                                                                if traversal:
                                                                    button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                if traversal:
                                                                    if elapsed % 60 == 0:
                                                                        p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                        actors = []
                                                                        for probe_slot in range(1, 6):
                                                                            actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                            actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                        worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                        worker_player = worker_rows[0:256]
                                                                        spawn_index = u8(legal.SPAWN_INDEX)
                                                                        probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                        report['spawn_traversal']['controller_probe'].append(probe)
                                                                        report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                        controller_probe_path.write_text(json.dumps(probe))
                                                                tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                if traversal:
                                                                    if kind == 'stage':
                                                                        if button is not None:
                                                                            if button & m.BTN_Y:
                                                                                trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                continue
                                                            if biker_action == 'approach_left':
                                                                button = button | m.BTN_LEFT
                                                                if abs(dx) > 32:
                                                                    button = button | m.BTN_B
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                    if traversal_combat_attack_opportunity(dx, dy):
                                                                        if traversal_attack_held(elapsed):
                                                                            button = button | m.BTN_Y
                                                                target = (value, slot, object_num, roster, mode)
                                                                if target != prop_target_last:
                                                                    interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                    if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                        report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                    else:
                                                                        report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                    prop_target_last = target
                                                                if args.two_player:
                                                                    if button2 is None:
                                                                        if traversal_p2_buttons is not None:
                                                                            if not u8(symbols['G13_P2Out']):
                                                                                button2 = traversal_p2_buttons
                                                                if traversal:
                                                                    button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                if traversal:
                                                                    if elapsed % 60 == 0:
                                                                        p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                        actors = []
                                                                        for probe_slot in range(1, 6):
                                                                            actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                            actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                        worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                        worker_player = worker_rows[0:256]
                                                                        spawn_index = u8(legal.SPAWN_INDEX)
                                                                        probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                        report['spawn_traversal']['controller_probe'].append(probe)
                                                                        report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                        controller_probe_path.write_text(json.dumps(probe))
                                                                tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                if traversal:
                                                                    if kind == 'stage':
                                                                        if button is not None:
                                                                            if button & m.BTN_Y:
                                                                                trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                continue
                                                            if biker_action.startswith('attack_'):
                                                                button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                button = button | traversal_biker_attack_mask(elapsed, m.BTN_Y, m.BTN_X)
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                    if traversal_combat_attack_opportunity(dx, dy):
                                                                        if traversal_attack_held(elapsed):
                                                                            button = button | m.BTN_Y
                                                                target = (value, slot, object_num, roster, mode)
                                                                if target != prop_target_last:
                                                                    interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                    if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                        report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                    else:
                                                                        report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                    prop_target_last = target
                                                                if args.two_player:
                                                                    if button2 is None:
                                                                        if traversal_p2_buttons is not None:
                                                                            if not u8(symbols['G13_P2Out']):
                                                                                button2 = traversal_p2_buttons
                                                                if traversal:
                                                                    button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                if traversal:
                                                                    if elapsed % 60 == 0:
                                                                        p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                        actors = []
                                                                        for probe_slot in range(1, 6):
                                                                            actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                            actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                        worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                        worker_player = worker_rows[0:256]
                                                                        spawn_index = u8(legal.SPAWN_INDEX)
                                                                        probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                        report['spawn_traversal']['controller_probe'].append(probe)
                                                                        report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                        controller_probe_path.write_text(json.dumps(probe))
                                                                tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                if traversal:
                                                                    if kind == 'stage':
                                                                        if button is not None:
                                                                            if button & m.BTN_Y:
                                                                                trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                continue
                                                            if biker_action.startswith('face_'):
                                                                button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                    if traversal_combat_attack_opportunity(dx, dy):
                                                                        if traversal_attack_held(elapsed):
                                                                            button = button | m.BTN_Y
                                                                target = (value, slot, object_num, roster, mode)
                                                                if target != prop_target_last:
                                                                    interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                    if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                        report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                    else:
                                                                        report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                    prop_target_last = target
                                                                if args.two_player:
                                                                    if button2 is None:
                                                                        if traversal_p2_buttons is not None:
                                                                            if not u8(symbols['G13_P2Out']):
                                                                                button2 = traversal_p2_buttons
                                                                if traversal:
                                                                    button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                if traversal:
                                                                    if elapsed % 60 == 0:
                                                                        p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                        actors = []
                                                                        for probe_slot in range(1, 6):
                                                                            actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                            actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                        worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                        worker_player = worker_rows[0:256]
                                                                        spawn_index = u8(legal.SPAWN_INDEX)
                                                                        probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                        report['spawn_traversal']['controller_probe'].append(probe)
                                                                        report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                        controller_probe_path.write_text(json.dumps(probe))
                                                                tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                if traversal:
                                                                    if kind == 'stage':
                                                                        if button is not None:
                                                                            if button & m.BTN_Y:
                                                                                trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                continue
                                                            if biker_action == 'wait':
                                                                if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                                    if traversal_combat_attack_opportunity(dx, dy):
                                                                        if traversal_attack_held(elapsed):
                                                                            button = button | m.BTN_Y
                                                                target = (value, slot, object_num, roster, mode)
                                                                if target != prop_target_last:
                                                                    interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                                    if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                                        report['spawn_traversal']['prop_interactions'].append(interaction)
                                                                    else:
                                                                        report['spawn_traversal']['combat_interactions'].append(interaction)
                                                                    prop_target_last = target
                                                                if args.two_player:
                                                                    if button2 is None:
                                                                        if traversal_p2_buttons is not None:
                                                                            if not u8(symbols['G13_P2Out']):
                                                                                button2 = traversal_p2_buttons
                                                                if traversal:
                                                                    button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                                                if traversal:
                                                                    if elapsed % 60 == 0:
                                                                        p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                                                        actors = []
                                                                        for probe_slot in range(1, 6):
                                                                            actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                                            actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                                                        worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                                                        worker_player = worker_rows[0:256]
                                                                        spawn_index = u8(legal.SPAWN_INDEX)
                                                                        probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                                                        report['spawn_traversal']['controller_probe'].append(probe)
                                                                        report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                                                        controller_probe_path.write_text(json.dumps(probe))
                                                                tick(button, button2=button2, hold=traversal and kind == 'stage')
                                                                if traversal:
                                                                    if kind == 'stage':
                                                                        if button is not None:
                                                                            if button & m.BTN_Y:
                                                                                trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                                                                report['spawn_traversal']['input_trace'].append(trace_row)
                                                                                report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                                                                continue
                                                            raise AssertionError('unknown Biker traversal action')
                                                        if traversal_chase_axis(dx, dy) == 'x':
                                                            button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                            if abs(dx) > 64:
                                                                button = button | m.BTN_B
                                                        elif traversal_chase_axis(dx, dy) == 'y':
                                                            button = button | (m.BTN_DOWN if dy > 0 else m.BTN_UP)
                                                        else:
                                                            button = button | (m.BTN_RIGHT if dx > 0 else m.BTN_LEFT)
                                                            if traversal_attack_held(elapsed):
                                                                button = button | m.BTN_Y
                                                    if mode == symbols['CHAR_INPUT_DRIVEN_AI']:
                                                        if traversal_combat_attack_opportunity(dx, dy):
                                                            if traversal_attack_held(elapsed):
                                                                button = button | m.BTN_Y
                                                    target = (value, slot, object_num, roster, mode)
                                                    if target != prop_target_last:
                                                        interaction = dict(stage=value, slot=slot, object_num=object_num, roster=roster, mode=mode, hp=hp, worker_owned=worker_owned, biker_approaching=biker_approaching, action='target', dx=dx, dy=dy, field=report['frames_sampled'])
                                                        if mode == symbols['CHAR_INPUT_DRIVEN_PROP']:
                                                            report['spawn_traversal']['prop_interactions'].append(interaction)
                                                        else:
                                                            report['spawn_traversal']['combat_interactions'].append(interaction)
                                                        prop_target_last = target
                                                else:
                                                    prop_target_last = None
                                                    if build.STAGE_CONFIGS[value].get('scroll_direction', 'right') in ('up', 'down'):
                                                        button = button | (m.BTN_LEFT if elapsed % 32 < 16 else m.BTN_RIGHT)
                                                    else:
                                                        button = button | (m.BTN_UP if elapsed % 32 < 16 else m.BTN_DOWN)
                                                    direction = build.STAGE_CONFIGS[value].get('scroll_direction', 'right')
                                                    if traversal_camera_wait(raw_p1x, state['camera_x'], u16(symbols['Screen_SizeX']) if 'Screen_SizeX' in symbols else 256, direction):
                                                        button = traversal_camera_wait_button_value
                                                    vertical_scroll = build.STAGE_CONFIGS[value].get('scroll_direction', 'right') in ('up', 'down')
                                                    for slot in range(1, 6):
                                                        actor = p1 + slot * symbols['CHAR_ZP_LEN']
                                                        mode = u8(actor + symbols['CHAR_INPUT_DRIVEN'])
                                                        if not mode not in (symbols['CHAR_INPUT_DRIVEN_AI'], symbols['CHAR_INPUT_DRIVEN_BIKER']):
                                                            if not u8(actor + symbols['CHAR_HP']):
                                                                continue
                                                            ax = u16(actor + symbols['CHAR_POS_X'])
                                                            ay = u8(actor + symbols['CHAR_POS_Y'])
                                                            if not abs(ax - p1x) > 72:
                                                                if abs(ay - p1y) > 28:
                                                                    continue
                                                                if vertical_scroll:
                                                                    button = button | (m.BTN_LEFT if p1x >= ax else m.BTN_RIGHT)
                                                                else:
                                                                    button = button | (m.BTN_UP if p1y >= ay else m.BTN_DOWN)
                                                            else:
                                                                continue
                                                        else:
                                                            continue
                                                        break
                                    if args.two_player:
                                        if button2 is None:
                                            if traversal_p2_buttons is not None:
                                                if not u8(symbols['G13_P2Out']):
                                                    button2 = traversal_p2_buttons
                                    if traversal:
                                        button = traversal_lifecycle_input(button, u8(symbols['PlayerEntity_Hp']), u8(symbols['G13_P1Out']))
                                    if traversal:
                                        if elapsed % 60 == 0:
                                            p1_base = 8257536 + symbols['PlayerEntity_DpBase']
                                            actors = []
                                            for probe_slot in range(1, 6):
                                                actor = p1_base + probe_slot * symbols['CHAR_ZP_LEN']
                                                actors.append(dict(slot=probe_slot, hp=u8(actor + symbols['CHAR_HP']), mode=u8(actor + symbols['CHAR_INPUT_DRIVEN']), selected=u8(actor + symbols['CHAR_SELECTED']), facing_left=u8(actor + symbols['CHAR_FACING_LEFT']), fall_timer=u8(actor + symbols['CHAR_FALL_STATE_TIMER']), fall_frames=u8(actor + symbols['CHAR_FALL_FCOUNT']), hit_stun=u8(actor + symbols['CHAR_HIT_STUN']), grab_target=u8(actor + symbols['CHAR_GRAB_TARGET']), grabbed_by=u8(actor + symbols['CHAR_GRABBED_BY']), x=u16(actor + symbols['CHAR_POS_X']), y=u8(actor + symbols['CHAR_POS_Y']), object_num=u16(actor + symbols['OOP_SELF_NUM_OFS']), idle=u8(actor + symbols['CHAR_IDLE_FCOUNT']), pickup=u8(actor + symbols['CHAR_PICKUP_TYPE'])))
                                            worker_rows = bytes(read_block(m, 4266240, 1536, mem_type='sa1Memory'))
                                            worker_player = worker_rows[0:256]
                                            spawn_index = u8(legal.SPAWN_INDEX)
                                            probe = dict(*(), **{'field': report['frames_sampled'], 'stage': value, 'nmi_field': u16(symbols['Nmi_FrameCounter']), 'stage_timer_field': u16(symbols.get('StageTimer_FieldCounter', 8280340)), 'stage_timer_last_field': u16(symbols.get('StageTimer_LastField', 8280342)), 'campaign_id': u8(symbols['Game_CampaignId']), 'source_tick': u16(8263484), 'tick_commit': u16(symbols['S6Game_TickCommit']), 'spawn_index': spawn_index, 'spawn_count': u8(legal.SPAWN_COUNT), 'spawn_waiting': u8(symbols['Spawn_Waiting']), 'camera_x': u16(legal.SCREEN_POS_X), 'camera_min_x': u16(8263178), 'camera_max_x': u16(8263182), 'world_max_x': u16(symbols['WorldMaxX']), 'stage_true_max_x': u16(symbols['Stage_TrueMaxX']), 'next_trigger': u16(symbols['SpawnTable_Wram'] + spawn_index * 10) if spawn_index < u8(legal.SPAWN_COUNT) else None, 'spawn_group_min': u8(symbols['Spawn_GroupMin']), 'spawn_group_max': u8(symbols['Spawn_GroupMax']), 'button': button or 0, 'target': target_probe, 'input_press': u16(8258576), 'input_trigger': u16(8258578), 'worker_player': dict(x=int.from_bytes(worker_player[20:22], 'little', signed=True), y=int.from_bytes(worker_player[22:24], 'little', signed=True), selected=worker_player[11], frame=worker_player[9], zpos=int.from_bytes(worker_player[67:69], 'little', signed=True), zvel=int.from_bytes(worker_player[69:71], 'little', signed=True), role=int.from_bytes(worker_player[228:230], 'little', signed=True), error=int.from_bytes(worker_player[252:254], 'little')), 'p1': dict(x=u16(p1_base + symbols['CHAR_POS_X']), y=u8(p1_base + symbols['CHAR_POS_Y']), hp=u8(p1_base + symbols['CHAR_HP']), selected=u8(p1_base + symbols['CHAR_SELECTED']), idle=u8(p1_base + symbols['CHAR_IDLE_FCOUNT']), attack_frames=u8(p1_base + symbols['CHAR_ATTACK_FCOUNT']), attack_variant=u8(p1_base + symbols['CHAR_ATTACK_VARIANT']), hit_applied=u8(p1_base + symbols['CHAR_HIT_APPLIED']), jump_mode=u8(symbols['Player_JumpAnimMode']), jump_fcount=u8(symbols['Player_JumpFCount']), zpos=u16(p1_base + symbols['CHAR_THROW_ZPOS']), zvel=u16(p1_base + symbols['CHAR_THROW_ZVEL'])), 'actors': actors})
                                            report['spawn_traversal']['controller_probe'].append(probe)
                                            report['spawn_traversal']['controller_probe'] = report['spawn_traversal']['controller_probe'][-24:]
                                            controller_probe_path.write_text(json.dumps(probe))
                        elif args.mode == 'skip':
                            if not skip_sent:
                                if u16(o3.SCENE_PRESENTED) >= 1:
                                    button = m.BTN_A
                                    skip_sent = True
                        tick(button, button2=button2, hold=traversal and kind == 'stage')
                        if traversal:
                            if kind == 'stage':
                                if button is not None:
                                    if button & m.BTN_Y:
                                        trace_row = dict(field=report['frames_sampled'], stage=value, spawn_index=u8(legal.SPAWN_INDEX), requested=int(button), input_press=u16(symbols['Input_press']), input_trigger=u16(symbols['Input_trigger']), last_raw=u16(8258588), player_x=u16(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_X']), player_y=u8(8257536 + symbols['PlayerEntity_DpBase'] + symbols['CHAR_POS_Y']), worker_target=int.from_bytes(bytes(read_block(m, 73730, 32, mem_type='snesSaveRam')[:2]), 'little'), worker_completed=int.from_bytes(bytes(read_block(m, 73732, 32, mem_type='snesSaveRam')[:2]), 'little'))
                                        report['spawn_traversal']['input_trace'].append(trace_row)
                                        report['spawn_traversal']['input_trace'] = report['spawn_traversal']['input_trace'][-96:]
                        continue
                    if traversal:
                        if state['state'] == legal.TITLE:
                            if ordinal != len(entries) - 1:
                                row['unexpected_exit'] = state
                                harvest()
                                raise AssertionError('entry ' + str(ordinal) + ' premature TITLE, not campaign progression')
                    break
                else:
                    row['exit_timeout'] = scene_observation() if kind == 'scene' else dict(game=sample())
                    row['exit_timeout']['elapsed_fields'] = budget
                    row['exit_timeout']['runtime'] = runtime_diagnostics()
                    report['last_observation'] = row['exit_timeout']['game']
                    row['timeout_runtime'] = runtime_diagnostics()
                    require('entry ' + str(ordinal) + ' bounded native exit', False)
                if kind == 'scene':
                    row['exit_observation'] = scene_observation()
                    row['exit_observation']['elapsed_fields'] = elapsed
                row['frames'] = elapsed
                row['saw_showcomplete'] = saw_complete
                row['skip_sent'] = skip_sent
                if kind == 'stage':
                    if traversal:
                        harvest()
                        completed = report['spawn_traversal']['completed']
                        require('entry ' + str(ordinal) + ' every packed record consumed natively', sum((r['stage'] == value for r in completed)) == sum((r['stage'] == value for r in plan)))
                        m.release_input(port=0)
                        if args.two_player:
                            m.release_input(port=1)
                    require('entry ' + str(ordinal) + ' completion policy behavior', saw_complete == row['completion_expected'])
                    if saw_complete:
                        require('entry ' + str(ordinal) + ' showcomplete advances exactly once', u16(complete_advances) == 1 and u8(complete_active) == 0)
                else:
                    row['scene'] = dict(presented=u16(o3.SCENE_PRESENTED), transitions=u16(o3.SCENE_TRANSITIONS), completion=u16(o3.SCENE_COMPLETE), skip=u8(o3.SCENE_SKIP), late=u16(o3.SCENE_LATE), retries=u16(o3.SCENE_RETRIES))
                    require(name + ' preserves score/lives/credits', l5.snapshot(m) == scene_before)
                    require(name + ' clean scene transport', row['scene']['late'] == row['scene']['retries'] and row['scene']['retries'] == 0)
                    if args.mode == 'natural':
                        require(name + ' complete natural playback', row['scene']['presented'] == ({'ENDING': 1997, 'RUGAL': 126, 'SEWER': 3}[name]) and (row['scene']['completion'] == 1 and row['scene']['skip'] == 0))
                        if name == 'ENDING':
                            require('ENDING has four clip transitions', row['scene']['transitions'] == 4)
                    else:
                        require(name + ' real input skip exactly once', bool(row.get('immediate_skip_fences')) and row['scene']['skip'] == 1 if not skip_sent else row['scene']['skip'] == 1)
                        require(name + ' no swaps after skip cleanup', u16(o3.SCENE_SKIP_SWAPS) == u16(o3.SCENE_SWAPS))
                expected_ordinal = min(ordinal + 1, len(entries) - 1)
                terminal = ordinal == len(entries) - 1
                next_state = legal.TITLE if terminal else legal.PLAYING if entries[ordinal + 1][0] == 'stage' else o3.SCENE
                wait(lambda: u8(legal.CAMPAIGN_ORDINAL) == expected_ordinal and u16(legal.GAME_STATE) == next_state, 900, 'entry ' + str(ordinal) + ' next dispatch')
                row['end'] = sample()
                row['runtime_end'] = runtime_diagnostics()
            if args.mode == 'easy':
                require('bounded Easy control leaves TimesCompleted unchanged', u32(times) == times_before)
                report['scope'] = 'Easy first three legal clears only; no full Easy completion claim'
            else:
                require('all requested compiler entries consumed in order', len(report['route']) == len(entries) - args.debug_start_ordinal)
                require('completion credited exactly once', u32(times) == times_before + 1 & 4294967295 and u8(credited) == 1)
                require('completion preserves selected source set', u8(selected) == set_index)
                report['selected_source_set_after'] = u8(selected)
                require('authored scene continuations exactly once', u16(l5.ENDS) - ends_before & 65535 == sum(e[0] == 'scene' for e in entries))
                final_swaps = u16(o3.SCENE_SWAPS)
                final_ends = u16(l5.ENDS)
                for _ in range(180):
                    tick()
                    if not u32(times) != times_before + 1 & 4294967295:
                        if not u16(legal.GAME_STATE) != legal.TITLE:
                            if not u8(credited) != 1:
                                if not u16(l5.ENDS) != final_ends:
                                    if u8(legal.CAMPAIGN_ORDINAL) != len(entries) - 1:
                                        require('TITLE dwell retains exactly-once completion', False)
                                else:
                                    require('TITLE dwell retains exactly-once completion', False)
                            else:
                                require('TITLE dwell retains exactly-once completion', False)
                        else:
                            require('TITLE dwell retains exactly-once completion', False)
                    else:
                        require('TITLE dwell retains exactly-once completion', False)
                require('TITLE dwell has no late scene swaps', u16(o3.SCENE_SWAPS) == final_swaps)
            report['times_after'] = u32(times)
            report['final'] = sample()
            report['final']['selected_source_set'] = u8(symbols['BorSet_Selected'])
            report['final']['completion_credited'] = u8(credited)
            require('terminal completion retains selected source set',
                    report['final']['selected_source_set'] == set_index)
            report['runtime_final'] = runtime_diagnostics()
            if traversal:
                harvest()
                require('all authored source spawn identities and every control record observed', len(report['spawn_traversal']['completed']) == len(plan))
                report['spawn_traversal']['status'] = 'PASS'
    require('all gate checks passed', all((ok for _, ok in r.results)))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('natural', 'skip', 'easy'), required=True)
    parser.add_argument('--source-set', choices=('Easy', 'Normal', 'Hard', 'Bonus'), default='Normal')
    parser.add_argument('--report', type=Path, help='JSON path (default: out/game_s8_<mode>.json)')
    parser.add_argument('--screenshots', action='store_true')
    parser.add_argument('--spawn-traversal', action='store_true', help='Observe every real source-world queue admission; never skip Spawn_Index.')
    parser.add_argument('--two-player', action='store_true', help='Use real co-op TITLE/CHARSELECT input and both sequenced worker controls.')
    parser.add_argument('--trace-runtime', action='store_true', help='Enable expensive per-routine runtime trace callbacks (diagnostic only).')
    parser.add_argument('--trace-bind', action='store_true', help='Capture only source-host bind rejection/unbound fault branches.')
    parser.add_argument('--trace-sparse', action='store_true', help='Sample S-CPU PC, stage, source ticks and worker mailbox every 30 fields.')
    parser.add_argument('--trace-pc-only', action='store_true', help='Use the sparse end-of-field trace without per-routine callbacks.')
    parser.add_argument('--trace-player-move', action='store_true', help='Capture a bounded SA-1 player-move entry/exit trace.')
    parser.add_argument('--trace-ownership', action='store_true', help='Trace only Normal worker ownership faults and host-error writes.')
    parser.add_argument('--trace-player-lifecycle', action='store_true', help='Sample player death-animation dispatch counts every 30 fields.')
    parser.add_argument('--stage-fields', type=int, default=6000, help='bounded per-stage observation fields (default 6000; diagnostics only)')
    parser.add_argument('--traversal-step-fields', type=int, choices=range(1, 9), default=1,
                        help='native fields per held gameplay control sample; queue observer still records every admission')
    parser.add_argument('--debug-start-ordinal', type=int, default=0, help='diagnostics only: real campaign resolver entry after initial stage startup')
    args = parser.parse_args()
    if args.two_player:
        if args.mode == 'easy':
            parser.error('--two-player currently applies to Normal campaign validation only')
    output = args.report or ROOT / 'out' / ('game_s8_' + str(args.mode) + str('_traversal' if args.spawn_traversal else '') + '.json')
    report = dict(mode=args.mode, verdict='FAIL', route=[], frames_sampled=0,
                  traversal_step_fields=args.traversal_step_fields,
                  sampling='frames_sampled counts controller observations; native admissions are observed independently',
                  scope='accelerated native progression with real input-driven initial-actor/prop interactions; not full combat balance or manual visual acceptance')
    if args.debug_start_ordinal:
        report['scope'] = 'DIAGNOSTIC_ONLY: initial campaign ordinal injected to isolate a segment; not a complete authored traversal certificate'
        report['debug_start_ordinal'] = args.debug_start_ordinal
    try:
        try:
            run(args, report)
            report['verdict'] = 'PASS'
        except Exception as error:
            report['error'] = f'{type(error).__name__}: {error}'
            if isinstance(error, TimeoutError) or 'bounded native exit' in str(error):
                report['verdict'] = 'UNKNOWN'
            print(report['error'], file=sys.stderr)
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('S8 ' + str(args.mode) + ': ' + str(report['verdict']) + ' (' + str(output) + ')')
    if report['verdict'] == 'PASS':
        return 0
    return 1
if __name__ == '__main__':
    raise SystemExit(main())
