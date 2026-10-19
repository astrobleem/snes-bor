"""Strict per-field diagnostic capture of the warm live-world presentation.

This is a diagnostic harness, not an acceptance claim. It launches the private
warm build under the existing contained Mesen worker, retains one immutable
preconstructor bootstrap, then drives only physical controller input. Native
observer callbacks are read-only. Every requested field uses the repository's
strict exact-frame helper; a stalled/overshot step aborts and preserves its
state rather than accepting a partial capture.

Input script JSON is a list such as
``[{"field": 12, "buttons": ["Right"]}]``. Field indices are zero-based from
the first post-bootstrap field captured by this harness. Each listed button
combination is asserted for exactly one field; every other field is neutral.
The current pinned input bridge mapping is checked against its source mask
table before emulator startup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
VERIFY = Path(__file__).resolve().parent
sys.path.insert(0, str(VERIFY))

DEFAULT_WORK = 0x7E7700
DEFAULT_LATEST = 0x7E7800
RENDER_PIN = 0x7E9600
DISPLAY_PIN = 0x7E9700
COLD_PIN = 0x7FBA00
PIN_BYTES = 148
COLD_PIN_BYTES = 146
ACTOR = 0x414000
ACTOR_BYTES = 80
SIDE = 0x416800
SIDE_BYTES = 64

# These are the physical SNES pad bits bound by source_input_controller.py.
# Mesen MCP's button names have been verified by m4_input_controller_native;
# this harness repeats the source-mask verification without sampling hardware.
BUTTONS = {
    "Y": ("BTN_Y", 0x4000), "B": ("BTN_B", 0x8000),
    "A": ("BTN_A", 0x0080), "X": ("BTN_X", 0x0040),
    "L": ("BTN_L", 0x0020), "R": ("BTN_R", 0x0010),
    "Select": ("BTN_SELECT", 0x2000), "Start": ("BTN_START", 0x1000),
    "Up": ("BTN_UP", 0x0800), "Down": ("BTN_DOWN", 0x0400),
    "Left": ("BTN_LEFT", 0x0200), "Right": ("BTN_RIGHT", 0x0100),
}


def digest(data_or_path):
    if isinstance(data_or_path, (str, Path)):
        data_or_path = Path(data_or_path).read_bytes()
    return hashlib.sha256(data_or_path).hexdigest()


def _word(raw, offset=0):
    return raw[offset] | raw[offset + 1] << 8


def _u16(m, address):
    return int.from_bytes(m.read_memory("SnesMemory", address, 2), "little")


def _u32(m, address):
    return int.from_bytes(m.read_memory("SnesMemory", address, 4), "little")


def _validate_button_binding():
    sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
    from source_input_controller import BINDING, convert
    source = {name.lower(): bit for bit, name in BINDING}
    converted = {}
    source_name = {
        "Y": "attack", "B": "attack2", "A": "jump", "X": "special",
        "L": "attack3", "R": "attack4", "Select": "esc", "Start": "start",
        "Up": "moveup", "Down": "movedown", "Left": "moveleft", "Right": "moveright",
    }
    for name, (_, bit) in BUTTONS.items():
        key = source_name[name]
        if key is None or source[key] != bit:
            raise ValueError("WARM_INPUT_SOURCE_BINDING:" + name)
        converted[name] = convert(bit)
        if converted[name] == 0:
            raise ValueError("WARM_INPUT_EMPTY_BOR_MASK:" + name)
    return dict(source_bits={name: bit for name, (_, bit) in BUTTONS.items()},
                bor_masks=converted,
                source_binding="tools/bor_compile/source_input_controller.py:BINDING+convert")


def load_input_script(path, fields):
    if path is None:
        raw = []
    else:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("WARM_INPUT_SCRIPT_EXPECTED_LIST")
    actions = {}
    occupied = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) - {"field", "buttons", "duration"}:
            raise ValueError(f"WARM_INPUT_SCRIPT_ROW:{index}")
        field = item.get("field")
        names = item.get("buttons")
        duration = item.get("duration", 1)
        if isinstance(field, bool) or not isinstance(field, int) or not 0 <= field < fields:
            raise ValueError(f"WARM_INPUT_SCRIPT_FIELD:{index}")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
            raise ValueError(f"WARM_INPUT_SCRIPT_DURATION:{index}")
        stop = field + duration
        if stop > fields:
            raise ValueError(f"WARM_INPUT_SCRIPT_RANGE:{index}")
        if any(i in occupied for i in range(field, stop)):
            raise ValueError("WARM_INPUT_SCRIPT_OVERLAPPING_RANGE:" + str(field))
        if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
            raise ValueError(f"WARM_INPUT_SCRIPT_BUTTONS:{index}")
        selected = []
        source_mask = 0
        for name in names:
            canonical = next((button for button in BUTTONS if button.lower() == name.lower()), None)
            if canonical is None:
                raise ValueError("WARM_INPUT_UNKNOWN_BUTTON:" + name)
            if canonical in selected:
                raise ValueError("WARM_INPUT_DUPLICATE_BUTTON:" + canonical)
            selected.append(canonical)
            _, source_bit = BUTTONS[canonical]
            source_mask |= source_bit
        action = dict(field=field, duration=duration, buttons=selected,
                      source_snes_mask=source_mask,
                      mcp_names=[BUTTONS[n][0] for n in selected])
        for i in range(field, stop):
            occupied.add(i)
            actions[i] = action
    return actions


def _observer(folder, contract):
    """Extend the established read-only writer/audio observer with warm rows."""
    import m4_live_world_capture as live_capture
    script, base_report = live_capture.observer(folder, contract)
    sy = contract["symbols"]
    cfg = contract["config"]
    warm = cfg["warm"]
    work = int(warm.get("work", cfg.get("work", DEFAULT_WORK)))
    latest = int(warm.get("latest", cfg.get("latest_snapshot", DEFAULT_LATEST)))
    control = int(warm.get("control", 0x7E9400))
    if not ("WarmMain" in sy and "WarmMain_Ready" in sy and "WarmPublish" in sy and "WarmYield" in sy):
        raise ValueError("WARM_REQUIRED_SYMBOLS")
    if "WarmPublished" not in sy or "WarmMain_Ready" not in sy or "LiveTick_SealComplete" not in sy:
        raise ValueError("WARM_COMPLETION_HOOK_REQUIRED")

    renderer_ranges = warm.get("renderer_pc_ranges", warm.get("renderer_range"))
    range_source = "config.warm.renderer_range"
    if renderer_ranges is None:
        for begin_name, end_name in (("WarmRenderer_CodeStart", "WarmRenderer_CodeEnd"),
                                     ("WarmRenderer_Start", "WarmRenderer_End")):
            if begin_name in sy and end_name in sy:
                renderer_ranges = [[sy[begin_name], sy[end_name]]]
                range_source = f"symbols:{begin_name}..{end_name}"
                break
    if renderer_ranges is not None:
        normalized = []
        if (isinstance(renderer_ranges, (list, tuple)) and len(renderer_ranges) == 2 and
                all(isinstance(value, (int, str)) for value in renderer_ranges)):
            renderer_ranges = [renderer_ranges]
        for pair in renderer_ranges:
            lo, hi = (pair.get("start"), pair.get("end")) if isinstance(pair, dict) else pair
            lo = int(lo, 0) if isinstance(lo, str) else int(lo)
            hi = int(hi, 0) if isinstance(hi, str) else int(hi)
            if not (0 <= lo < hi <= 0x1000000):
                raise ValueError("WARM_RENDERER_PC_RANGE")
            normalized.append((lo, hi))
        renderer_ranges = normalized
    else:
        renderer_ranges = []
        range_source = "root-confirmed renderer-only bank 0x2E"

    names = ["WarmMain", "WarmMain_Ready", "WarmPublish", "WarmYield", "WarmPublished", "WarmRenderRetired",
             "LiveTick_Service", "LiveTick_Dispatch", "LiveTick_Commit",
             "LiveTick_ReturnGood", "LiveTick_SealComplete",
             "SourceWorldTick4086_Begin", "SourceWorldTick4086_Commit",
             "SourceClock4086_Observe", "SourceClock4086_Commit",
             "SourceInputController_Refresh", "SourceInputController_Refresh__done"]
    names += [n for n in sy if n.startswith("WarmPublish") and
              any(s in n.lower() for s in ("fault", "bad", "reject", "done", "return"))]
    timing_names = {"WarmRenderer_NbWindowStart", "WarmRenderer_NbPairBegin",
                    "WarmRenderer_NbPairComplete", "WarmRenderer_NbMapCommit",
                    "WarmRenderer_NbMapsComplete", "WarmRenderer_NbVisible",
                    "WarmRenderer_NbQueueHasPending", "WarmRenderer_NbQueueDrainDone",
                    "WarmRenderer_OnlineVblank", "WarmRenderer_NbFreshVblank"}
    names += [n for n in sy if n in timing_names or
              any(part in n.lower() for part in ("vblank", "endfield", "endframe"))]
    names = list(dict.fromkeys(n for n in names if n in sy))
    source = ["\nlocal warmPointCount=0;local warmPublishCount=0;local warmSealCount=0;local warmLogTruncated=false",
              "local function warmPoint(name)",
              " if warmPointCount>=20000 then if not warmLogTruncated then warmLogTruncated=true;emu.log('WARMTRUNCATED|1') end;return end;warmPointCount=warmPointCount+1",
              " local s=emu.getState()",
              " local v={name,s.masterClock,s['ppu.frameCount'],s['cpu.a'],s['cpu.ps'],s['cpu.x'] or -1,s['cpu.y'] or -1,s['cpu.sp'] or -1,s['cpu.d'] or -1,s['cpu.dbr'] or -1,s['cpu.pc'] or -1,s['cpu.k'] or -1}"]
    for expr in (f"word({work})", f"word({work+2})", f"word({work+4})", f"word({work+6})",
                 f"word({work+8})", f"word({work+10})", f"word({work+12})", f"word({work+18})",
                 f"word({work+20})", f"word({sy['SourceClock4086_TimeLo']})",
                 f"word({control+0x100})", f"word({control+0x102})",
                 f"word({control+0x104})", f"word({control+0x106})",
                 f"word({sy['SourceClock4086_TimeLo']+2})", f"word({sy['SourceClock4086_Due']})",
                 f"word({sy['SourceWorldTick4086_State']})", f"word({sy['SourceWorldTick4086_Phase']})",
                 f"word({sy['SourceWorldTick4086_Pending']})", f"word({sy['SourceWorldTick4086_Fault']})"):
        source.append(f" v[#v+1]={expr}")
    source += [" emu.log('WARMPOINT|'..table.concat(v,'|'))", "end"]
    for name in names:
        source.append(f"emu.addMemoryCallback(function()warmPoint('{name}')end,emu.callbackType.exec,{sy[name]},{sy[name]},emu.cpuType.snes,mt)")

    def hexread(base, size):
        return f"local function warmHex{base:06x}()local t={{}};for i=0,{size-1} do t[#t+1]=string.format('%02x',emu.read({base}+i,mt)) end;return table.concat(t) end"
    source += [hexread(RENDER_PIN, PIN_BYTES), hexread(DISPLAY_PIN, PIN_BYTES),
               hexread(latest, PIN_BYTES), hexread(ACTOR, ACTOR_BYTES), hexread(SIDE, SIDE_BYTES),
               hexread(COLD_PIN, COLD_PIN_BYTES),
               f'''emu.addMemoryCallback(function()
 local s=emu.getState();local d=warmHex{DISPLAY_PIN:06x}();local c=warmHex{COLD_PIN:06x}()
 emu.log('WARMMAINREADY|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..word(0x7ffb96)..'|'..
  (word({DISPLAY_PIN+144})+65536*word({DISPLAY_PIN+146}))..'|'..d..'|'..c)
end,emu.callbackType.exec,{sy['WarmMain_Ready']},{sy['WarmMain_Ready']},emu.cpuType.snes,mt)
''',
               f'''emu.addMemoryCallback(function()
 local s=emu.getState();local r=warmHex{RENDER_PIN:06x}();local d=warmHex{DISPLAY_PIN:06x}()
 warmPublishCount=warmPublishCount+1
 emu.log('WARMPUBLISHED|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..(word({DISPLAY_PIN+144})+65536*word({DISPLAY_PIN+146}))..'|'..r..'|'..d)
end,emu.callbackType.exec,{sy['WarmPublished']},{sy['WarmPublished']},emu.cpuType.snes,mt)
''',
               f'''emu.addMemoryCallback(function()
 if word({work+18})~=2 or word({work+20})~=0 then
  emu.log('WARMSEALINVALID|'..word({work+18})..'|'..word({work+20}));return
 end
 local s=emu.getState();warmSealCount=warmSealCount+1
 emu.log('WARMSEAL|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..word({work+8})..'|'..
  word({work+10})..'|'..(word({latest+144})+65536*word({latest+146}))..'|'..warmHex{latest:06x}()..'|'..
  warmHex{ACTOR:06x}()..warmHex{SIDE:06x}())
end,emu.callbackType.exec,{sy['LiveTick_SealComplete']},{sy['LiveTick_SealComplete']},emu.cpuType.snes,mt)
''', f'''emu.addEventCallback(function()
 if word(0x7ffb88)~=0xb6d0 then return end
 local s=emu.getState()
 emu.log('WARMFIELD|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..word(0x7ffb96)..'|'..
  warmHex{DISPLAY_PIN:06x}()..'|'..warmHex{COLD_PIN:06x}())
end,emu.eventType.endFrame)
''']
    if all(n in sy for n in ("SourceInputController_Refresh__done",
                              "SourceInputController_Raw1", "SourceInputController_Raw2")):
        from source_script_input import ADDRESS as input_snapshot
        source.append(f'''emu.addMemoryCallback(function()
 if warmPointCount>=20000 then return end
 local s=emu.getState();local d={{}}
 for i=0,31 do d[#d+1]=string.format('%02x',emu.read({input_snapshot}+i,mt)) end
 emu.log('WARMINPUT|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..
  word({sy['SourceInputController_Raw1']})..'|'..word({sy['SourceInputController_Raw2']})..'|'..table.concat(d))
end,emu.callbackType.exec,{sy['SourceInputController_Refresh__done']},{sy['SourceInputController_Refresh__done']},emu.cpuType.snes,mt)
''')
    target = Path(script)
    base_lua = target.read_text(encoding="utf-8")
    # Keep strict physical-field pauses after the voice retires as well as
    # during cold setup. This observer state never writes emulated memory.
    old_pause="if word(0x7ffb88)==0xb6d0 and word(0x7e8100)==0xb6d8 and emu.read(0x7e8102,mt)==1 then"
    if base_lua.count(old_pause)!=1:raise ValueError('WARM_END_FRAME_PAUSE_SHAPE')
    base_lua=base_lua.replace(old_pause,'if word(0x7ffb88)==0xb6d0 then')
    source.append(f'''local warmMaskCalls=0;local warmColorCalls=0;local warmModeFaults=0
emu.addMemoryCallback(function()
 local mode=word({control+14})
 if mode==1 then warmMaskCalls=warmMaskCalls+1 elseif mode==0 then warmColorCalls=warmColorCalls+1 else warmModeFaults=warmModeFaults+1 end
end,emu.callbackType.exec,{sy['WarmTile_Prepare']},{sy['WarmTile_Prepare']},emu.cpuType.snes,mt)
emu.addEventCallback(function()
 if word(0x7ffb88)==0xb6d0 then local s=emu.getState();emu.log('WARMPLANEMODES|'..s['ppu.frameCount']..'|'..warmMaskCalls..'|'..warmColorCalls..'|'..warmModeFaults) end
end,emu.eventType.endFrame)
''')
    source.append('''emu.addMemoryCallback(function(a,v)
 if word(0x7ffb88)~=0xb6d0 then return end
 local s=emu.getState();emu.log('WARMNMITIMEN|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..v..'|'..(s['cpu.pc'] or -1)..'|'..(s['cpu.k'] or -1))
end,emu.callbackType.write,0x4200,0x4200,emu.cpuType.snes,mt)
''')
    # Read-only interrupt progress distinguishes a live clock from a frozen
    # counter and records the real M flag at the audio completion join.
    source.append('local warmNmiCount=0;local warmClockNmiCount=0;local warmAudioM8=0;local warmAudioM16=0')
    for label,counter in (('LiveWorld_Nmi','warmNmiCount'),('SourceClock4086_NmiGate','warmClockNmiCount')):
        source.append(f'emu.addMemoryCallback(function(){counter}={counter}+1 end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,mt)')
    if 'LiveAudio_PumpCheckCompletion' in sy:
        address=sy['LiveAudio_PumpCheckCompletion']
        source.append(f"emu.addMemoryCallback(function()local s=emu.getState();if (s['cpu.ps']&0x20)~=0 then warmAudioM8=warmAudioM8+1 else warmAudioM16=warmAudioM16+1 end end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)")
    source.append('''emu.addEventCallback(function()
 if word(0x7ffb88)~=0xb6d0 then return end
 local s=emu.getState();emu.log('WARMINTERRUPTS|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..warmNmiCount..'|'..warmClockNmiCount..'|'..warmAudioM8..'|'..warmAudioM16..'|'..(s['cpu.pc'] or -1)..'|'..(s['cpu.k'] or -1)..'|'..(s['cpu.ps'] or -1)..'|'..(s['cpu.sp'] or -1))
 emu.log('WARMPPU|VBLANK_START|'..s.masterClock..'|'..s['ppu.frameCount'])
end,emu.eventType.endFrame)
emu.addEventCallback(function()
 if word(0x7ffb88)~=0xb6d0 then return end
 local s=emu.getState();emu.log('WARMPPU|VBLANK_END|'..s.masterClock..'|'..s['ppu.frameCount'])
end,emu.eventType.startFrame)
''')
    range_lua = "local warmRendererRanges={" + ",".join(
        "{" + str(lo) + "," + str(hi) + "}" for lo, hi in renderer_ranges) + "}\n"
    range_lua += "local function liveAllowed(pc) if not pc then return false end;local bank=(pc>>16);if bank==0x39 then return true end;for _,r in ipairs(warmRendererRanges) do if pc>=r[1] and pc<r[2] then return true end end;"
    if not renderer_ranges:
        range_lua += "if bank==0x2e then return true end;"
    range_lua += "return false end\n"
    marker = "local liveWriteCount=0;local liveWriteChecks=0;local liveTraceEmpty=0"
    if marker not in base_lua or base_lua.count("(pc>>16)~=0x39") != 4:
        raise ValueError("WARM_BASE_WRITER_OBSERVER_SHAPE")
    base_lua = base_lua.replace(marker, range_lua + marker, 1)
    base_lua = base_lua.replace("(pc>>16)~=0x39", "not liveAllowed(pc)")
    base_lua = base_lua.replace("(pc>>16)~=(actual>>16)", "liveAllowed(pc)~=liveAllowed(actual)")
    target.write_text(base_lua, encoding="utf-8")
    with target.open("a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(source) + "\n")
    return target, dict(base=base_report, warm_observer_sha256=digest(target),
                        warm_callbacks=names, event_log_cap=20000,
                        renderer_write_allowlist=dict(cold_ranges=[[0x390000,0x3A0000]],
                            warm_ranges=[[lo, hi] for lo, hi in renderer_ranges] or [[0x2E0000,0x2F0000]],
                            warm_range_source=range_source,
                            declared_renderer_sections=warm.get("renderer_sections"),
                            allowed_cpu="SNES only",
                            rejected_helper_bank="0x2B", rejected_other_writer_banks=True),
                        warm_control=dict(base=control, status=control+0x100,
                            sticky_fault=control+0x102, guard_status=control+0x104,
                            alias_fault=control+0x106),
                        warm_seal_hook=sy["LiveTick_SealComplete"],
                        warm_published_hook=sy["WarmPublished"])


def _parse_events(log_path):
    sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
    text = Path(log_path).read_text(errors="replace")
    warm = []
    published = []
    warm_ready = []
    seals = []
    input_samples = []
    invalid = []
    field_events = []
    for line in text.splitlines():
        if "WARMFIELD|" in line:
            try:
                v=line.split('WARMFIELD|',1)[1].split('|')
                field_events.append(dict(master_clock=int(v[0]),frame=int(v[1]),
                    constructor_ready=int(v[2]),display_pin_hex=v[3],cold_pin_hex=v[4]))
            except (ValueError,IndexError):invalid.append(line)
        elif "WARMMAINREADY|" in line:
            try:
                v = line.split("WARMMAINREADY|", 1)[1].split("|")
                warm_ready.append(dict(master_clock=int(v[0]), frame=int(v[1]),
                    constructor_ready=int(v[2]), display_epoch=int(v[3]),
                    display_pin_hex=v[4], cold_pin_hex=v[5],
                    display_generation=int.from_bytes(bytes.fromhex(v[4])[4:8],'little'),
                    display_matches_cold=v[4] == v[5] + '0000'))
            except (ValueError, IndexError):
                invalid.append(line)
        elif "WARMPOINT|" in line:
            try:
                name, *v = line.split("WARMPOINT|", 1)[1].split("|")
                warm.append(dict(name=name, master_clock=int(v[0]), frame=int(v[1]),
                                 cpu_a=int(v[2]), cpu_p=int(v[3]), cpu_x=int(v[4]),
                                 cpu_y=int(v[5]), cpu_sp=int(v[6]), cpu_dp=int(v[7]),
                                 cpu_dbr=int(v[8]), cpu_pc=int(v[9]), cpu_pb=int(v[10]),
                                 work_owner=int(v[11]), work_state=int(v[12]),
                                 generation_low=int(v[13]), generation_high=int(v[14]),
                                 committed_count=int(v[15]) | int(v[16]) << 16,
                                 pending_phase=int(v[17]), result=int(v[18]),
                                 result_fault=int(v[19]), time_lo=int(v[20]),
                                 warm_status=int(v[21]), sticky_fault=int(v[22]),
                                 guard_status=int(v[23]), alias_fault=int(v[24]),
                                 time_hi=int(v[25]), due=int(v[26]),
                                 world_state=int(v[27]), phase=int(v[28]),
                                 pending=int(v[29]), fault=int(v[30])))
            except (ValueError, IndexError):
                invalid.append(line)
        elif "WARMPUBLISHED|" in line:
            try:
                v = line.split("WARMPUBLISHED|", 1)[1].split("|")
                published.append(dict(master_clock=int(v[0]), frame=int(v[1]), epoch=int(v[2]),
                                       render_pin_hex=v[3], display_pin_hex=v[4],
                                       pins_coherent=v[3] == v[4]))
            except (ValueError, IndexError):
                invalid.append(line)
        elif "WARMSEAL|" in line:
            try:
                v = line.split("WARMSEAL|", 1)[1].split("|")
                seals.append(dict(master_clock=int(v[0]), frame=int(v[1]),
                                   committed_count=int(v[2]) | int(v[3]) << 16,
                                   latest_epoch=int(v[4]), latest_hex=v[5],
                                   actor_side_hex=v[6], coherent=v[5][:288] == v[6]))
            except (ValueError, IndexError):
                invalid.append(line)
        elif "WARMSEALINVALID|" in line:
            invalid.append(line)
        elif "WARMTRUNCATED|" in line:
            pass
        elif "WARMINPUT|" in line:
            try:
                v = line.split("WARMINPUT|", 1)[1].split("|")
                input_samples.append(dict(master_clock=int(v[0]), frame=int(v[1]),
                    raw1=int(v[2]), raw2=int(v[3]), snapshot_hex=v[4]))
            except (ValueError, IndexError):
                invalid.append(line)
    try:
        from source_input_controller import refresh
        # LiveTick_Service explicitly refreshes A=1 for this one-player owner.
        # Port-2 storage is not initialized or owned by that source call.
        old = [0]
        for sample in input_samples:
            raw = [sample["raw1"]]
            expected = refresh(old, raw)
            data = bytes.fromhex(sample["snapshot_hex"])
            ready = int.from_bytes(data[:2], "little")
            count = int.from_bytes(data[2:4], "little")
            tick = int.from_bytes(data[4:8], "little")
            actual = [tuple(int.from_bytes(data[8 + port * 12 + i:8 + port * 12 + i + 4], "little")
                            for i in (0, 4, 8)) for port in range(1)]
            sample["expected_rows"] = expected
            sample["actual_rows"] = actual
            sample["tick"] = tick
            sample["source_players"]=count
            sample["unowned_raw_port2_not_qualified"]=True
            sample["exact"] = ready == 0xB4C2 and count == 1 and actual == expected
            old = [row[0] for row in expected]
    except (ValueError, ImportError) as error:
        invalid.append("WARMINPUT_DECODE:" + repr(error))
    return dict(text=text, warm_points=warm, warm_ready=warm_ready, field_events=field_events, published=published, seals=seals,
                input_samples=input_samples, malformed_events=invalid,
                truncated="LIVETRUNCATED|" in text or "WARMTRUNCATED|" in text)


def _make_oracle(snapshot, source, stage, cache, Image, np):
    key = bytes(snapshot)
    if key not in cache:
        from m4_live_ground_component_native import scene_from_snapshot
        from source_scene_bg import compose_rgb8
        from source_bg_feasibility import rgb555
        # The source compositor consumes its historical 146-byte row. Warm
        # ownership extends the epoch to 32 bits; retain the full epoch in
        # cache identity and pin comparisons without changing raster input.
        if len(key) not in (146,148):raise ValueError('WARM_ORACLE_PIN_EXTENT')
        scene = scene_from_snapshot(key[:146], source)
        pixels, _ = compose_rgb8(source, stage, scene)
        expected = rgb555(pixels).astype("<u2")
        cache[key] = dict(expected=expected,
                          snapshot_sha256=hashlib.sha256(key).hexdigest(),
                          pixel_count=int(expected.size),
                          expected_sha256=hashlib.sha256(expected.tobytes()).hexdigest())
    return cache[key]


def capture(build, folder, fields, input_script=None):
    if os.environ.get("BOR_PROBE_JOB_REQUIRED") != "1":
        raise ValueError("WARM_PROBE_CONTAINED_WORKER_REQUIRED")
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    build = Path(build).resolve()
    contract = json.loads((build / "contract.json").read_text(encoding="utf-8"))
    sy = contract["symbols"]
    cfg = contract["config"]
    warm = cfg.get("warm")
    if not isinstance(warm, dict):
        raise ValueError("WARM_BUILD_CONFIG_REQUIRED")
    for name in ("WarmMain", "WarmMain_Ready", "WarmPublish", "WarmYield", "LiveTick_Service",
                 "LiveTick_Dispatch", "LiveTick_Commit", "LiveTick_ReturnGood"):
        if name not in sy:
            raise ValueError("WARM_SYMBOL_REQUIRED:" + name)
    if digest(build / "bor.sfc") != contract.get("rom_sha256"):
        raise ValueError("WARM_BUILD_ROM_HASH_MISMATCH")
    if not contract.get("renderer_bank_unchanged", False):
        raise ValueError("WARM_ACCEPTED_RENDERER_BANK_CHANGED")
    work = int(warm.get("work", cfg.get("work", DEFAULT_WORK)))
    latest = int(warm.get("latest", cfg.get("latest_snapshot", DEFAULT_LATEST)))
    render_pin = int(warm.get("render_pin", RENDER_PIN))
    display_pin = int(warm.get("display_pin", DISPLAY_PIN))
    cold_pin = int(warm.get("cold_pin", COLD_PIN))
    stage = warm.get("stage", "DATA/LEVELS/GUILE2.TXT")
    binding_report = _validate_button_binding()
    actions = load_input_script(input_script, fields)

    mesen_source = os.environ.get("MESEN_EXE")
    mesen_python = os.environ.get("MESEN_PYTHON_PATH")
    if not mesen_source or not Path(mesen_source).is_file():
        raise ValueError("WARM_CONFIGURE_MESEN_EXE")
    if not mesen_python or not (Path(mesen_python) / "mesen_mcp/session.py").is_file():
        raise ValueError("WARM_CONFIGURE_MESEN_PYTHON_PATH")
    sys.path.insert(0, str(Path(mesen_python).resolve()))
    import m4_eight_pair_native as runtime
    exe = runtime.prepare_capture_runtime(folder / "capture-runtime", mesen_source)
    os.environ["MESEN_EXE"] = str(exe)
    import _harness
    from mesen_mcp.session import McpSession
    import mesen_mcp.session as actual
    assert Path(actual.__file__).resolve() == (Path(mesen_python) / "mesen_mcp/session.py").resolve()
    assert hasattr(McpSession, "hold_input")
    from _harness import Reporter, exact_input_edge, run_frames_exact, _free_tcp_port
    import game_bor_startup_select as startup
    observer_script, observer_report = _observer(folder, contract)
    launches = []

    class Observed(McpSession):
        def __enter__(self):
            import ctypes
            def launch(argv, **kwargs):
                return subprocess.Popen([*argv, "--donotsavesettings", str(observer_script)], **kwargs)
            with patch.object(actual, "subprocess", SimpleNamespace(Popen=launch,
                    DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE)):
                result = super().__enter__()
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            query = kernel.QueryFullProcessImageNameW
            query.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_wchar_p,
                              ctypes.POINTER(ctypes.c_uint32)]
            query.restype = ctypes.c_int
            buffer = ctypes.create_unicode_buffer(32768)
            length = ctypes.c_uint32(len(buffer))
            assert query(ctypes.c_void_p(int(self._proc._handle)), 0, buffer, ctypes.byref(length))
            assert Path(buffer.value).resolve() == exe.resolve()
            launches.append(dict(pid=self._proc.pid, actual_executable=buffer.value,
                                 argv=self._proc.args))
            (folder / "actual-launches.json").write_text(json.dumps(launches, indent=2) + "\n")
            return result

    progress = []
    visible = []
    latest_pin = None
    audio_cfg = cfg.get("audio")
    audio_progress = []
    packets = []
    previous_chunks = 0
    audio_payload = None
    if audio_cfg:
        raw_rom = (build / "bor.sfc").read_bytes()
        audio_payload = raw_rom[audio_cfg["payload_cpu"] - 0xC00000:
                                audio_cfg["payload_cpu"] - 0xC00000 + audio_cfg["payload_bytes"]]
        os.environ.update(MESEN_VOICE_CAPTURE_PATH=str(folder / "voice0.raw"),
                          MESEN_VOICE_CAPTURE_VOICE="0",
                          MESEN_VOICE_CAPTURE_ARM_FILE=str(folder / "voice0.raw.arm"))
    from compiler import Source
    source = Source(ROOT / "Masters of the Universe [v.3.0 Build 4086].pak")
    import numpy as np
    from PIL import Image
    from source_bg_feasibility import rgb555
    from _harness import McpSession as _McpSession  # imported for helper ABI parity

    try:
        with Observed(rom=build / "bor.sfc", mesen=exe, port=_free_tcp_port(),
                      stderr_log=folder / "mesen.log") as m:
            # Existing preconstructor bootstrap and owner acquisition. These
            # are the only debugger writes; after the lease request below all
            # simulation inputs are physical controller edges.
            m.write_u16(0x7FFB96, 0)
            m.write_u16(0x7FFB88, 0)
            reporter = Reporter("MOTU-WARM-WORLD-BOOT", kind="GATE")
            with patch.object(m, "reset_emulator", return_value=None):
                startup.cold_to_title(m, reporter)
            startup.title_to_charselect(m)
            exact_input_edge(m, m.BTN_START, 1, port=0)
            if not startup.wait_state(m, startup.PLAYING, 300):
                raise ValueError("WARM_ORIGINAL_BOOTSTRAP")
            run_frames_exact(m, 12)
            for name in ("StageWater_Enabled", "StageWater_Pending", "StageFp_BG2Loaded",
                         "StageFp_BG2Active", "StageFp_BG2DmaPending", "StageFp_BG2Booting",
                         "StreamScrollFp_ColPending", "StreamScrollFp_Enabled"):
                m.write_u8(sy[name], 0)
            m.hold_input(0, port=0)
            run_frames_exact(m, 2)
            if audio_cfg:
                (folder / "voice0.raw.arm").touch()
                m.record_audio(folder / "source-audio.wav")
            # Request the already-built warm owner only after the real source
            # constructor/bootstrap. Snapshot the cold pin with every field;
            # the pre-constructor contents are never an oracle candidate.
            m.write_u16(0x7FFB80, 0xB4E7)
            for index in range(fields):
                action = actions.get(index)
                mask = 0
                if action:
                    for button in action["buttons"]:
                        mask |= getattr(m, BUTTONS[button][0])
                m.hold_input(mask, port=0)
                frame_result = run_frames_exact(m, 1)
                state = m.get_state()
                actor = m.read_memory("SnesMemory", ACTOR, ACTOR_BYTES)
                side = m.read_memory("SnesMemory", SIDE, SIDE_BYTES)
                latest_raw = m.read_memory("SnesMemory", latest, PIN_BYTES)
                render_raw = m.read_memory("SnesMemory", render_pin, PIN_BYTES)
                display_raw = m.read_memory("SnesMemory", display_pin, PIN_BYTES)
                cold_raw = m.read_memory("SnesMemory", cold_pin, COLD_PIN_BYTES)
                ready_word = _u16(m, 0x7FFB96)
                raw1 = m.read_memory("SnesMemory", sy.get("SourceInputController_Raw1", 0x7FF8F4), 2)
                raw2 = m.read_memory("SnesMemory", sy.get("SourceInputController_Raw2", 0x7FF8F6), 2)
                mapped = m.read_memory("SnesMemory", sy.get("VmSourceInput_Data", 0x7FF8C8), 12)
                control = int(warm.get("control", 0x7E9400))
                progress.append(dict(index=index, frame=state["frameCount"],
                    master_clock=None, master_clock_source="not exposed by MCP get_state; see Lua callback events",
                    mcp_state=state, frames_advanced=frame_result.get("framesAdvanced"),
                    work=m.read_memory("SnesMemory", work, 24).hex(),
                    clock=m.read_memory("SnesMemory", sy["SourceClock4086_Ready"], 64).hex(),
                    world=m.read_memory("SnesMemory", sy["SourceWorldTick4086_Ready"], 64).hex(),
                    source_time=_u32(m, sy["SourceClock4086_TimeLo"]),
                    world_time=_u32(m, sy["VmSourceWorld_Time"]),
                    due=_u16(m, sy["SourceClock4086_Due"]),
                    world_state=_u16(m, sy["SourceWorldTick4086_State"]),
                    phase=_u16(m, sy["SourceWorldTick4086_Phase"]),
                    pending=_u16(m, sy["SourceWorldTick4086_Pending"]),
                    source_fault=_u16(m, sy["SourceWorldTick4086_Fault"]),
                    constructor_ready_word=ready_word, constructor_ready=ready_word == 0xB4B8,
                    warm_status=_u16(m, control + 0x100), sticky_fault=_u16(m, control + 0x102),
                    guard_status=_u16(m, control + 0x104), alias_fault=_u16(m, control + 0x106),
                    actor_hex=actor.hex(), side_hex=side.hex(), latest_hex=latest_raw.hex(),
                    cold_pin_hex=cold_raw.hex(),
                    latest_matches_current=(latest_raw[:144] == actor + side),
                    latest_epoch=int.from_bytes(latest_raw[144:148],'little'),
                    display_epoch=int.from_bytes(display_raw[144:148],'little'),
                    committed_count=_u32(m, work + 8),
                    raw_input1=_word(raw1), raw_input2=_word(raw2), mapped_input_hex=mapped.hex(),
                    render_pin_hex=render_raw.hex(), display_pin_hex=display_raw.hex(),
                    scripted_input=action, actual_mcp_input_mask=mask))

                # Exact image comparison against the last *successful*
                # display-pin publication is completed after callback events
                # are parsed. Retain every screenshot and tuple for that join.
                image_path = folder / f"field-{index:04d}.png"
                shot = m.take_screenshot()
                shutil.copyfile(shot["path"], image_path)
                progress[-1]["png"] = image_path.name
                progress[-1]["png_sha256"] = digest(image_path)

                if audio_cfg:
                    stream_base = sy.get("TadPrivate_stream_frame", 0)
                    accepted_base = sy.get("TadPrivate_stream_chunks_accepted", 0)
                    transport = m.read_memory("SnesMemory", stream_base, 64) if stream_base else b""
                    accepted = _u16(m, accepted_base) if accepted_base else 0
                    for chunk in range(previous_chunks, accepted):
                        aram = sy["TAD_STREAM_RING_ADDR"] + (chunk % 8) * 144
                        actual_packet = m.read_memory("SpcRam", aram, 144)
                        expected_packet = bytearray(audio_payload[chunk * 144:chunk * 144 + 144])
                        if chunk % 8 == 7 and chunk + 1 < audio_cfg["payload_bytes"] // 144:
                            expected_packet[135] |= 3
                        packets.append(dict(chunk=chunk, field=index, aram=aram,
                            observer_gap=accepted - previous_chunks,
                            mismatched_bytes=sum(a != b for a, b in zip(actual_packet, expected_packet)),
                            actual_sha256=hashlib.sha256(actual_packet).hexdigest(),
                            expected_sha256=hashlib.sha256(expected_packet).hexdigest()))
                    previous_chunks = accepted
                    audio_progress.append(dict(index=index, frame=state["frameCount"],
                        transport=transport.hex(), chunks_accepted=accepted,
                        control=m.read_memory("SnesMemory", 0x7E8100, 64).hex(),
                        channel11=m.read_memory("SnesMemory", 0x7E8140 + 440, 40).hex(),
                        compact11=m.read_memory("SnesMemory", 0x7EFF88 + 88, 8).hex(),
                        source_status=_u16(m, sy["SourceAudio_Status"]),
                        channel0_registers=m.read_memory("SnesMemory", 0x4300, 16).hex(),
                        dma=m.read_dma_state(),
                        voice0=next(v for v in m.get_audio_state()["voices"] if v["voice"] == 0)))
                    (folder / "audio-progress.json").write_text(json.dumps(audio_progress, indent=2) + "\n")
                    (folder / "audio-packets.json").write_text(json.dumps(packets, indent=2) + "\n")
                (folder / "progress.json").write_text(json.dumps(progress, indent=2) + "\n")
            for name, at, size in (("latest", latest, PIN_BYTES), ("render-pin", render_pin, PIN_BYTES),
                                   ("display-pin", display_pin, PIN_BYTES), ("cold-pin", cold_pin, COLD_PIN_BYTES),
                                   ("clock", sy["SourceClock4086_Ready"], 64),
                                   ("world", sy["SourceWorldTick4086_Ready"], 64),
                                   ("actor", ACTOR, ACTOR_BYTES), ("side", SIDE, SIDE_BYTES)):
                (folder / (name + ".bin")).write_bytes(m.read_memory("SnesMemory", at, size))
            shot = m.take_screenshot()
            if "path" in shot:
                shutil.copyfile(shot["path"], folder / "last.png")
            (folder / "screenshot-result.json").write_text(json.dumps(shot, indent=2) + "\n")
            m.release_input(port=0)
    except BaseException as error:
        (folder / "capture-error.json").write_text(json.dumps(dict(error=repr(error)), indent=2) + "\n")
        raise

    return analyze(build,folder,fields,input_script)


def analyze(build,folder,fields,input_script=None):
    """Re-evaluate retained raw evidence without launching an emulator."""
    folder=Path(folder);build=Path(build)
    contract=json.loads((build/'contract.json').read_text())
    warm=contract['config']['warm'];audio_cfg=contract['config'].get('audio')
    progress=json.loads((folder/'progress.json').read_text())
    launches=json.loads((folder/'actual-launches.json').read_text())
    observer_report=dict(retained_lua_sha256=digest(folder/'live-world-observer.lua'),
                         reprocessed_from_raw=True,emulator_relaunched=False)
    audio_progress=json.loads((folder/'audio-progress.json').read_text()) if audio_cfg else []
    packets=json.loads((folder/'audio-packets.json').read_text()) if audio_cfg else []
    binding_report=_validate_button_binding();actions=load_input_script(input_script,fields)
    from compiler import Source
    from source_bg_feasibility import rgb555
    from PIL import Image
    import numpy as np
    source=Source(ROOT/'Masters of the Universe [v.3.0 Build 4086].pak')
    stage=warm.get('stage','DATA/LEVELS/GUILE2.TXT');visible=[]
    parsed = _parse_events(folder / "mesen.log")
    publishes = parsed["published"]
    seals = parsed["seals"]
    oracle_cache = {}
    for row in progress:
        field_events=[e for e in parsed['field_events'] if e['frame']+1==row['frame']]
        row['physical_field_event_count']=len(field_events)
        if len(field_events)!=1:
            if not field_events and not row['constructor_ready']:
                row.update(warm_main_ready=False,display_snapshot_valid_generation1=False,
                           display_pin_is_latest_success=None,exact_pixels=False,
                           exact_pixels_reason='pre_owner_no_field_event')
                visible.append(dict(index=row['index'],frame=row['frame'],exact=False,
                                    why='pre_owner_no_field_event',constructor_ready=False))
                continue
            raise ValueError('WARM_PHYSICAL_FIELD_EVENT_JOIN:'+str(row['frame']))
        field_event=field_events[0]
        # endFrame is the authoritative completed picture boundary. Preserve
        # the later MCP values separately; they cannot authorize an earlier PNG.
        row.setdefault('mcp_constructor_ready',row['constructor_ready'])
        row.setdefault('mcp_display_pin_hex',row['display_pin_hex'])
        row.setdefault('mcp_cold_pin_hex',row['cold_pin_hex'])
        row['constructor_ready']=field_event['constructor_ready']==0xb4b8
        row['display_pin_hex']=field_event['display_pin_hex']
        row['cold_pin_hex']=field_event['cold_pin_hex']
        row['mcp_pins_match_end_frame']=(None if row['mcp_display_pin_hex'] is None else
            row['mcp_display_pin_hex']==row['display_pin_hex'] and row['mcp_cold_pin_hex']==row['cold_pin_hex'])
        row['master_clock']=field_event['master_clock']
        row['master_clock_source']='Lua endFrame before frameCount increment; exact +1 join'
        warm_ready_candidates = [e for e in parsed["warm_ready"] if e["master_clock"] < row["master_clock"]]
        row["warm_main_ready"] = bool(warm_ready_candidates)
        row["warm_main_ready_event"] = warm_ready_candidates[-1] if warm_ready_candidates else None
        row["display_snapshot_valid_generation1"] = bool(
            warm_ready_candidates and warm_ready_candidates[0]["constructor_ready"] == 0xB4B8 and
            warm_ready_candidates[0]["display_generation"] == 1)
        published_candidates = [e for e in publishes if e["master_clock"] < row["master_clock"]]
        row["successful_publications_seen"] = len(published_candidates)
        if published_candidates:
            allowed = published_candidates[-1]["display_pin_hex"]
            oracle_source = "latest successful WarmPublished strictly before completed field endFrame"
        else:
            if row["constructor_ready"]:
                allowed = row["cold_pin_hex"] + '0000'
                oracle_source = "per-field post-constructor cold pin before first WarmPublished"
            else:
                allowed = None
                oracle_source = "no constructor-ready oracle snapshot"
        row["oracle_source"] = oracle_source
        observed = bytes.fromhex(row["display_pin_hex"])
        row["display_pin_matches_cold_after_warm_main"] = (
            observed.hex() == row["cold_pin_hex"] + '0000' if row["warm_main_ready"] and not published_candidates else None)
        row["display_pin_is_latest_success"] = (
            observed == bytes.fromhex(allowed) if row['warm_main_ready'] and allowed is not None else None)
        exact = False
        if not row["constructor_ready"]:
            why = "constructor_not_ready"
        elif allowed is None:
            why = "no_valid_oracle_snapshot"
        else:
            try:
                allowed_bytes = bytes.fromhex(allowed)
                image = np.asarray(Image.open(folder / row["png"]).convert("RGB"))
                actual_pixels = rgb555(image)
                expected = _make_oracle(allowed_bytes, source, stage, oracle_cache, Image, np)
                exact = actual_pixels.shape == expected["expected"].shape and np.array_equal(
                    actual_pixels, expected["expected"])
                why = "exact" if exact else "pixel_mismatch"
                row["allowed_display_sha256"] = hashlib.sha256(allowed_bytes).hexdigest()
                row["oracle_tuple_sha256"] = expected["snapshot_sha256"]
                row["oracle_pixel_count"] = expected["pixel_count"]
                row["oracle_expected_sha256"] = expected["expected_sha256"]
            except Exception as error:
                why = "oracle_invalid_snapshot:" + type(error).__name__ + ":" + str(error)
        row["exact_pixels"] = bool(exact)
        row["exact_pixels_reason"] = why
        visible.append(dict(index=row["index"], frame=row["frame"], exact=bool(exact),
                            why=why, constructor_ready=row["constructor_ready"],
                            warm_main_ready=row["warm_main_ready"],
                            display_pin_is_latest_success=row["display_pin_is_latest_success"],
                            display_pin_matches_cold_after_warm_main=row["display_pin_matches_cold_after_warm_main"],
                            oracle_source=oracle_source,
                            oracle_tuple_sha256=row.get("oracle_tuple_sha256"),
                            png_sha256=row["png_sha256"]))
    (folder / "visible-fields.json").write_text(json.dumps(visible, indent=2) + "\n")
    (folder / "progress.json").write_text(json.dumps(progress, indent=2) + "\n")
    (folder / "warm-published.json").write_text(json.dumps(publishes, indent=2) + "\n")
    (folder / "warm-main-ready.json").write_text(json.dumps(parsed["warm_ready"], indent=2) + "\n")
    (folder / "warm-seals.json").write_text(json.dumps(seals, indent=2) + "\n")
    (folder / "input-script.json").write_text(json.dumps(dict(binding=binding_report,
        actions=[actions[k] for k in sorted(actions) if actions[k]["field"] == k],
        observed_samples=parsed["input_samples"]), indent=2) + "\n")
    text = parsed["text"]
    tick_begin = [e for e in parsed["warm_points"] if e["name"] == "SourceWorldTick4086_Begin"]
    tick_commit = [e for e in parsed["warm_points"] if e["name"] == "SourceWorldTick4086_Commit"]
    published_coherent = bool(publishes) and all(e["pins_coherent"] for e in publishes)
    sealed_coherent = bool(seals) and all(e["coherent"] for e in seals)
    eligible=[r for r in progress if r['constructor_ready']]
    warm_eligible=[r for r in eligible if r['warm_main_ready']]
    pin_coherent = bool(warm_eligible) and all(r['display_pin_is_latest_success'] is True for r in warm_eligible)
    pixels_exact = bool(eligible) and all(r.get("exact_pixels", False) for r in eligible)
    input_exact = bool(parsed["input_samples"]) and all(r["exact"] for r in parsed["input_samples"])
    seal_count_matches_commit_count = len(seals) == len(tick_commit)
    alias_fault_zero = bool(warm_eligible) and all(r["alias_fault"] == 0 for r in warm_eligible) and all(e["alias_fault"] == 0 for e in parsed["warm_points"])
    sticky_fault_zero = bool(warm_eligible) and all(r["sticky_fault"] == 0 for r in warm_eligible) and all(e["sticky_fault"] == 0 for e in parsed["warm_points"])
    report = dict(schema="BYOR_WARM_WORLD_NATIVE_DIAGNOSTIC_V1", status="DIAGNOSTIC_ONLY",
        rom_sha256=contract.get("rom_sha256"), renderer_bank_unchanged=contract.get("renderer_bank_unchanged"),
        build_config=warm, observer=observer_report, launches=launches,
        fields_requested=fields, fields_captured=len(progress), strict_one_frame_fields=all(
            r.get("frames_advanced") == 1 for r in progress), progress=progress,
        warm_events=parsed["warm_points"], warm_main_ready=parsed["warm_ready"],
        warm_published=publishes, source_seals=seals,
        source_begin_events=len(tick_begin), source_commit_events=len(tick_commit),
        source_commits_with_coherent_seals=len([e for e in seals if e["coherent"]]),
        display_pin_latest_success=pin_coherent, published_pins_coherent=published_coherent,
        source_seals_coherent=sealed_coherent, exact_pixels_all_fields=pixels_exact,
        oracle_cache=[{k: v for k, v in item.items() if k != "expected"}
                      for item in oracle_cache.values()],
        scripted_input=[actions[k] for k in sorted(actions) if actions[k]["field"] == k], input_samples=parsed["input_samples"],
        malformed_observer_events=parsed["malformed_events"], event_log_truncated=parsed["truncated"],
        physical_input_snapshots_exact=input_exact,
        protected_renderer_write_faults=[line.split("LIVEOWNFAULT|", 1)[1] for line in text.splitlines()
                                         if "LIVEOWNFAULT|" in line],
        protected_renderer_trace_faults=[line.split("LIVEOWNTRACEFAULT|", 1)[1] for line in text.splitlines()
                                         if "LIVEOWNTRACEFAULT|" in line],
        audio_progress_count=len(audio_progress), audio_packets=packets,
        audio_packet_mismatches=sum(p["mismatched_bytes"] for p in packets),
        raw_audio_capture=str(folder / "voice0.raw") if audio_cfg else None,
        checks=dict(field_count=len(progress) == fields,
                    exact_frame_count=all(r.get("frames_advanced") == 1 for r in progress),
                    display_pin_latest_success=pin_coherent, published_pins_coherent=published_coherent,
                    seals_coherent=sealed_coherent,
                    seal_count_matches_commit_count=seal_count_matches_commit_count,
                    physical_input_snapshots_exact=input_exact,
                    ready_generation1_observed=any(r["display_snapshot_valid_generation1"] for r in progress),
                    no_event_log_truncation=not parsed["truncated"], pixels_exact=pixels_exact,
                    alias_fault_zero=alias_fault_zero, sticky_fault_zero=sticky_fault_zero,
                    no_observer_faults=not parsed["malformed_events"],
                    no_owned_renderer_writes=not any("LIVEOWNFAULT|" in line for line in text.splitlines()),
                    no_writer_trace_faults=not any("LIVEOWNTRACEFAULT|" in line for line in text.splitlines())),
        native_capture_performed=True, emulator_relaunched_by_analysis=False,
        actor_time_ack_phase_or_pin_debugger_mutations_after_activation=False,
        cadence_or_gameplay_acceptance_not_claimed=True)
    (folder / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "fields_requested", "fields_captured",
                                             "source_begin_events", "source_commit_events",
                                             "exact_pixels_all_fields")}), flush=True)
    return report


if __name__ == "__main__":
    if os.environ.get("BOR_PROBE_JOB_REQUIRED") == "1":
        print(json.dumps(dict(kind="BOR_PROBE_JOB_HELLO", pid=os.getpid(),
                              parent_pid=os.getppid(), image=sys._base_executable)), flush=True)
        assert sys.stdin.buffer.read(1) == b"G"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fields", type=int, default=100)
    parser.add_argument("--input-script", type=Path)
    args = parser.parse_args()
    if args.fields <= 0:
        parser.error("--fields must be positive")
    capture(args.build, args.output, args.fields, args.input_script)
