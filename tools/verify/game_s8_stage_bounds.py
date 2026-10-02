#!/usr/bin/env python3
"""S8 native bounds proof; default is OFFLINE source/preflight checking.

After main builds: --run-native --rom-sha256 <accepted build hash> --case all.
BOR_TEST_ROM selects the candidate ROM and its same-stem .msu companion;
unset defaults to distribution/bor.sfc, matching the shared session harness.
Uses real TITLE selection, physical actors, and native campaign Stage_Load.
Only ordinary queue/camera/AI-HP clear preconditions are accelerated in transit.
Boundary fixtures set actor x/depth/altitude/velocity and reciprocal grab links
after verified harmless prologues; Lua records pre-instruction CPU flags.
They NEVER write campaign/state/ordinal,
bounds outputs, timer credits, HP/lives of tested actors, or CPU registers.
Loaded-stage save states establish the native stage; checkpoint actor rows are
restored explicitly between probes because Mesen preserves some mutable SNES
RAM across these rapid state reloads. No synthetic actor/model allocation.
Native JSON is fail-closed and retained on failure. No manual visual PASS.
"""
import argparse
from contextlib import contextmanager
from fractions import Fraction as F
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TARGETS = {'blocked': ('Normal', 'data/normal/1c.txt'),
           'pit-p1': ('Normal', 'data/normal/5a.txt'),
           'pit-p2': ('Normal', 'data/normal/5a.txt'),
           'pit-npc': ('Normal', 'data/normal/5a.txt'),
           'easy-blocked': ('Easy', 'data/easy/1ceasy.txt'),
           'easy': ('Easy', 'data/easy/5aeasy.txt')}
BOUNDARIES = ('StageBoundsHost_Clamp', 'StageBoundsHost_Clamp__done',
              'StageBoundsHost_Physics', 'StageBoundsHost_Physics__tick',
              'StageBoundsHost_Physics__next', 'Core_Oop_Play',
              'SourceVisual_PrepareBlocks__pending',
              'SourceVisual_Emit__priority_ready',
              'StageBounds_ApplyPitDamage_Long', 'StageBoundsHost_ApplyPitDamage__done')


def lorom_offset(address):
    """Shared native exec-hook address contract (also for traversal owner)."""
    if address&0xffff<0x8000 or (address>>16)&0x7f in (0x7e,0x7f):
        raise ValueError('exec hook must resolve to LoROM ROM')
    return ((address>>16)&0x7f)*0x8000+(address&0x7fff)


def admission_script(s, path, *, include_controls=False, traversal_fields=False,
                     status_path=None, heartbeat_symbol='Game_State_Play',
                     heartbeat_callback_extra='', identity_debug_path=None):
    """Stable complete-script API; consumers must not rewrite generated Lua.

    Default packet: 21 integer columns (read_admissions). traversal_fields
    appends idle_frames, frame, load_result, nmi, boss for Kuhn's 26-column
    reader. include_controls admits wait/group/hole, never generated children.
    status_path receives READY / TICK count index count / ERROR detail.
    All exec hooks use explicit SNES + normalized PrgRom addressing.
    """
    path=Path(path)
    status_path=Path(status_path) if status_path is not None else path.with_suffix('.status')
    filter_line='if kind==255 then return end' if include_controls else 'if kind==2 or kind==3 or kind==6 or kind==255 then return end'
    extra=''
    if traversal_fields:
        bosses=','.join(str(s[f'Entity{i}_IsBoss']) for i in range(1,6))
        extra=f''' local bosses={{{bosses}}}
 local slot=ofs/{s['CHAR_ZP_LEN']}
 row[#row+1]=rd(b+{s['CHAR_IDLE_FCOUNT']},1)
 row[#row+1]=rd(b+{s['CHAR_FRAME_INDEX']},1)
 row[#row+1]=rd({s['Spawn_RosterLoadResult']},1)
 row[#row+1]=rd({s['Nmi_FrameCounter']},2)
 row[#row+1]=bosses[slot] and rd(bosses[slot],1) or -1
'''
        if identity_debug_path is not None:
            extra += f''' local obj=rd(b+{s['OOP_SELF_SLOT_OFS']},1)
 local debug_values={{rd({s['OopFlags']}+obj,2),rd({s['OopClassId']}+obj,2),
  rd({s['OopNum']}+obj,2),rd({s['OopDp']}+obj,2),
  rd(b+{s['OOP_SELF_ID_OFS']},1),rd(b+{s['OOP_SELF_NUM_OFS']},2),
  rd(b+{s['CHAR_ZP_LEN']-1},1),rd({s['OopFlags']}+obj+1,2),
  rd({s['OopClassId']}+obj+1,2),rd({s['OopNum']}+obj+1,2),
  rd({s['OopDp']}+obj+1,2)}}
 local debug_file=assert(io.open({json.dumps(Path(identity_debug_path).as_posix())},'a'))
 for i=1,#debug_values do debug_values[i]=tostring(debug_values[i]) end
 debug_file:write(table.concat(row,' '),' | ',table.concat(debug_values,' '),'\\n')
 debug_file:close()
'''
    return f'''
local function rd(a,n)
 local v=0;for i=0,n-1 do v=v+emu.read(a+i,emu.memType.snesMemory)*256^i end;return v
end
local function status(text)
 local f=assert(io.open({json.dumps(status_path.as_posix())},'w'));f:write(text);f:close()
end
local pending=nil
local function finalize_pending()
 if not pending then return end
 local p=pending
 local kind=p.kind
 local ofs=p.offset
 local b={0x7e0000+s['PlayerEntity_DpBase']}+ofs
 local obj=rd(b+{s['OOP_SELF_SLOT_OFS']},1)
 local valid=obj<{s['OOP_MAX_OBJECTS']*2} and obj%2==0
 local present=0
 if valid and rd({s['OopFlags']}+obj,2)%2==1
 and rd({s['OopDp']}+obj,2)==b%65536
 and rd({s['OopClassId']}+obj,2)==rd(b+{s['OOP_SELF_ID_OFS']},1)
 and rd({s['OopNum']}+obj,2)==rd(b+{s['OOP_SELF_NUM_OFS']},2) then present=1 end
 local row={{p.campaign,p.stage,p.index,p.offset,p.kind,present,
 rd(b+{s['CHAR_HP']},1),rd(b+{s['CHAR_INPUT_DRIVEN']},1),
 rd(b+{s['CHAR_ROSTER_INDEX']},1),obj,rd(b+{s['OOP_SELF_NUM_OFS']},2)}}
 for i=1,10 do row[#row+1]=p.record[i] end
{extra}
 for i=1,#row do row[i]=string.format('%d',row[i]) end
 local out=assert(io.open({json.dumps(path.as_posix())},'a'))
 out:write(table.concat(row,' '),'\\n');out:close()
 pending=nil
end
local function admission()
 local kind=rd({s['Spawn_B2Kind']},1)
 {filter_line}
 local ofs=rd({s['Spawn_ScratchSlotOfs']},2)
 local idx=rd({s['Spawn_Index']},1)
 local record={{}}
 for i=0,9 do record[i+1]=rd({s['SpawnTable_Wram']}+idx*10+i,1) end
 pending={{campaign=rd({s['Game_CampaignId']},1),stage=rd({s['Game_StageIndex']},2),
  index=idx,offset=ofs,kind=kind,record=record}}
end
local failed=false
emu.addMemoryCallback(function()
 if failed then return end
 local ok,err=pcall(admission)
 if ok then ok,err=pcall(finalize_pending) end
 if not ok then failed=true;status('ERROR '..tostring(err)) end
end,emu.callbackType.exec,{lorom_offset(s['Spawn_Play__environment_done'])},{lorom_offset(s['Spawn_Play__environment_done'])},emu.cpuType.snes,emu.memType.snesPrgRom)
local heartbeat=0
emu.addMemoryCallback(function()
 if failed then return end
 {heartbeat_callback_extra}
 local ok,err=pcall(finalize_pending)
 if not ok then failed=true;status('ERROR '..tostring(err));return end
 heartbeat=heartbeat+1
 local f=assert(io.open({json.dumps(path.as_posix()+'.heartbeat')},'w'))
 f:write(heartbeat);f:close()
 status(string.format('TICK %d %d %d',heartbeat,rd({s['Spawn_Index']},1),rd({s['Spawn_Count']},1)))
end,emu.callbackType.exec,{lorom_offset(s[heartbeat_symbol])},{lorom_offset(s[heartbeat_symbol])},emu.cpuType.snes,emu.memType.snesPrgRom)
status('READY')
'''


def read_admissions(path):
    names=('campaign','stage','index','offset','kind','exists','hp','mode','roster','object_slot','object_num')
    rows=[]
    for line in Path(path).read_text().splitlines():
        values=list(map(int,line.split()))
        if len(values)!=21: raise AssertionError('incomplete spawn admission journal')
        rows.append(dict(zip(names,values[:11]),record=bytes(values[11:]).hex()))
    return rows


def boundary_script(syms, command, result, trace):
    """Lua captures the exact pre-instruction CPU and stops at that boundary.

    Only PHP/PHA/REP are permitted: no actor/OAM/lifecycle memory effects.
    No debugger mailbox is allocated in game WRAM. IO permission is scoped
    to this disposable --mcp process, whose settings are never saved.
    """
    return r'''
local command = COMMAND
local result = RESULT
local trace = TRACE
local seen = -1
local traced = 0
local function boundary(address)
    local f = io.open(command, "r")
    if not f then return end
    local token, pc, dp = f:read("*n", "*n", "*n")
    f:close()
    if not dp or token == seen or address ~= pc then return end
    local s = emu.getState()
    if traced < 32 then
        traced = traced + 1
        local out = assert(io.open(trace, "a"))
        out:write(string.format("%d %06X %04X %04X %04X\n", token, address,
            s["cpu.k"] or 0, s["cpu.pc"] or 0, s["cpu.d"] or 0))
        out:close()
    end
    if dp >= 0 and s["cpu.d"] ~= dp then return end
    seen = token
    local out = assert(io.open(result, "w"))
    out:write(token, " ", address, " ", s["cpu.k"], " ", s["cpu.pc"])
    for _, k in ipairs({"a", "x", "y", "d", "ps", "sp"}) do
        local value = s["cpu." .. k]
        if value == nil then error("missing CPU key " .. k) end
        out:write(" ", value)
    end
    out:close()
    emu.breakExecution()
end
for cpuAddress, romOffset in pairs(ADDRESSES) do
    local address=cpuAddress
    emu.addMemoryCallback(function() boundary(address) end, emu.callbackType.exec,
        romOffset,romOffset,emu.cpuType.snes,emu.memType.snesPrgRom)
end
'''.replace('COMMAND', json.dumps(command.as_posix())).replace(
        'RESULT', json.dumps(result.as_posix())).replace(
        'TRACE', json.dumps(trace.as_posix())).replace(
        'ADDRESSES', '{'+','.join('['+str(syms[n])+']='+str(lorom_offset(syms[n])) for n in BOUNDARIES)+'}')


@contextmanager
def native_session(syms, folder, expected_rom):
    # Reuse the existing validated session/unique-port/cleanup conventions.
    # Its constructor has no CLI-extra argument, so intercept ONLY its spawn.
    from _harness import open_session, rom_path
    from unittest.mock import patch
    if Path(rom_path(__file__)).resolve() != expected_rom:
        raise AssertionError('session ROM differs from the preflight/hash target')
    command, result = folder/'boundary.command', folder/'boundary.result'
    command.write_text('-1 0 -1\n')
    result.write_text('')
    script = folder/'boundary.lua'
    trace = folder/'boundary.trace'
    trace.write_text('')
    admissions=folder/'spawn.admissions'
    admissions.write_text('')
    Path(str(admissions)+'.heartbeat').write_text('0')
    script.write_text(boundary_script(syms, command.resolve(), result.resolve(), trace.resolve())+
                      admission_script(syms, admissions.resolve()))
    original = subprocess.Popen

    def launch(argv, **kwargs):
        if '--mcp' not in argv:
            raise AssertionError('unexpected process in scoped native session launch')
        return original([*argv, '--debug.scriptwindow.allowioosaccess=true', str(script.resolve())], **kwargs)

    session = open_session(__file__,stderr_log=folder/'mesen.log')
    try:
        with patch('subprocess.Popen', launch):
            m = session.__enter__()
        m.bounds_command, m.bounds_result, m.bounds_token = command, result, 0
        m.bounds_admissions=admissions
        # cold_to_title otherwise power-cycles the just-launched process and
        # destroys its debugger/Lua callbacks. Fresh launch is already cold.
        with patch.object(m,'reset_emulator',lambda:None): yield m
    finally:
        session.__exit__(None, None, None)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def key(path):
    return str(path).replace('\\', '/').lower()


def thresholds(width, depth):
    """Independent BOR.C oracle, including checkhole(int,int) truncation."""
    source_z = F(5*depth, 4)
    block = math.floor(F(4, 5)*(width-30-(232-source_z)))
    first_hole = math.ceil(F(4, 5)*(width-232+int(source_z)+1))
    return block, first_hole


def symbols(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        m = re.match(r'\s*([\da-fA-F]{2}):([\da-fA-F]{4,6})\s+(\S+)', line)
        if m:
            bank, raw, name = m.groups()
            value = int(raw, 16)
            result[name] = value if len(raw) > 4 else int(bank, 16)*65536+value
    return result


def source_plan(report):
    sys.path[:0] = [str(ROOT), str(ROOT/'tools/bor_compile')]
    import build_rom as build
    from compiler import Source, project, stage
    from source_actor_numeric import verify_source
    bor_c = ROOT/'out/bor_compile_s6/BOR.C'
    verify_source(bor_c)
    source = Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    sets = {s.name: s for s in project(source).sets}
    model_paths = {d.values[0].lower(): key(source.resolve(d.values[1])).rsplit('/', 1)[0]
                   for d in source.lines('DATA/MODELS.TXT') if d.name in ('load', 'know')}
    plan = {}
    for case, (set_name, path) in TARGETS.items():
        ir = stage(source, path)
        if ir.diagnostics:
            raise AssertionError(ir.diagnostics)
        width = sum(ir.dimensions[ir.panels[ord(c.lower())-97][0]][0] for c in ir.order)
        matches = [i for i, c in enumerate(build.STAGE_CONFIGS)
                   if c.get('family') == 'bor-original' and key(c['source_level']) == path]
        ordinals = [i for i, e in enumerate(sets[set_name].entries) if key(e.source_path) == path]
        if len(matches) != 1 or len(ordinals) != 1:
            raise AssertionError(f'nonunique/unlinked source identity: {path}')
        cfg = build.STAGE_CONFIGS[matches[0]]
        flags = (int(bool(ir.environment.get('blocked', [0])[-1])) |
                 (int(bool(ir.environment.get('endhole', [0])[-1])) << 1))
        plan[case] = dict(source=path, source_sha256=hashlib.sha256(source.read(path)).hexdigest(),
                          set=set_name, campaign=0 if set_name == 'Easy' else 3,
                          set_id=sets[set_name].source_id,
                          physical=matches[0], ordinal=ordinals[0], width=width, flags=flags,
                          spawn_path=cfg['spawn'], depths={str(y): thresholds(width, y) for y in (128, 160, 186)},
                          source_models=sorted({q.character.lower() for q in ir.queue if q.character}))
        plan[case]['source_model_paths'] = sorted({model_paths[n] for n in plan[case]['source_models']})
        plan[case]['source_queue_models'] = [model_paths[q.character.lower()] if q.character else None for q in ir.queue]
    if plan['blocked']['flags'] != 1 or plan['pit-p1']['flags'] != 2 or plan['easy']['flags'] != 2:
        raise AssertionError('source exit directives changed; review proof scope')
    report['source'] = dict(bor_c_sha256=sha(bor_c), plan=plan)
    return build, plan


def selected_rom_path():
    """Mirror _harness.rom_path without importing its emulator client offline."""
    override = os.environ.get('BOR_TEST_ROM')
    if override is None:
        return (ROOT/'distribution/bor.sfc').resolve()
    if not override.strip():
        raise ValueError('BOR_TEST_ROM must name a ROM file')
    path = Path(override).expanduser()
    if not path.is_absolute():
        path = ROOT/path
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError(f'BOR_TEST_ROM is not a file: {path}')
    return path


def assembly_dependencies(entry):
    """Recursive literal include/incbin closure, relative to the owning file.

    Missing dependencies and cycles fail closed. Unincluded work-in-progress
    modules are intentionally not assembly inputs. Conditional includes are
    conservatively included; this does not evaluate assembler expressions.
    """
    dependencies=set()
    directive=re.compile(r'^\s*\.(include|incbin)\s+"([^"]+)"',re.I)
    def visit(path, stack):
        path=path.resolve(strict=True)
        if path in stack: raise AssertionError(f'circular include: {path}')
        dependencies.add(path)
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match=directive.match(line)
            if not match: continue
            child=(path.parent/match[2]).resolve(strict=True)
            dependencies.add(child)
            if match[1].lower()=='include': visit(child,stack+(path,))
    visit(Path(entry),())
    return sorted(dependencies)


def build_preflight(args, report, plan):
    rom = selected_rom_path()
    report['rom_path'] = str(rom)
    report['msu_path'] = str(rom.with_suffix('.msu'))
    if not args.rom_sha256 or sha(rom).lower() != args.rom_sha256.lower():
        raise AssertionError('--run-native requires the exact main-approved built ROM SHA256')
    # Reject a pre-integration build before importing/opening an emulator.
    built = (ROOT/'src/main.bin').stat().st_mtime_ns
    dependencies=assembly_dependencies(ROOT/'src/main.pasm')
    report['assembly_dependencies']=[str(p) for p in dependencies]
    newer = [str(p) for p in dependencies if p.stat().st_mtime_ns > built]
    if newer:
        raise AssertionError('source newer than assembly: '+', '.join(newer[:12]))
    if rom.stat().st_mtime_ns < built:
        raise AssertionError('selected ROM predates current assembly')
    syms = symbols(ROOT/'src/main.sym')
    required = ('StageBounds_Records', 'StageBounds_RecordCount', 'StageBoundsHost_Physics__tick',
                'StageBoundsHost_Physics__next', 'StageBoundsHost_Clamp', 'StageBoundsHost_Clamp__done',
                'StageBoundsHost_Render', 'SourceVisual_Emit__priority_ready',
                'SourceVisual_PrepareBlocks__pending',
                'StageBounds_ApplyPitDamage_Long', 'StageBounds_CacheY',
                'StageBoundsHost_ApplyPitDamage__done', 'Core_Oam_SetSprite',
                'BorSetSelect_Begin', 'BorSetSelect_Play', 'BorSetSelect_Finish',
                'BorSet_BeginSelectedRun', 'BorSet_ContentAvailable', 'BorSet_CampaignMap',
                'BorSet_IfComplete', 'BorSet_Names', 'BOR_SET_NAME_WIDTH')
    for name in required:
        if name not in syms:
            raise AssertionError('built symbol missing: '+name)
    addr = syms['StageBounds_Records']
    if addr & 0xffff < 0x8000:
        raise AssertionError('bounds table is not LoROM ROM')
    offset = ((addr >> 16) & 0x7f)*0x8000+(addr & 0x7fff)
    blob = rom.read_bytes()
    def rom_cell(name, index):
        address = syms[name]
        return blob[((address >> 16) & 0x7f)*0x8000+(address & 0x7fff)+index]
    for case in TARGETS if args.case == 'all' else [args.case]:
        row = plan[case]
        sid = row['set_id']
        if not rom_cell('BorSet_ContentAvailable', sid) or rom_cell('BorSet_CampaignMap', sid) != row['campaign']:
            raise AssertionError(f"{row['set']} is unavailable/unmapped in this ROM; native proof will not bypass the release gate")
        name = bytes(rom_cell('BorSet_Names', sid*syms['BOR_SET_NAME_WIDTH']+i)
                     for i in range(syms['BOR_SET_NAME_WIDTH'])).split(b'\0')[0].decode('ascii')
        if name != row['set']:
            raise AssertionError('built set name differs from source positional identity')
    for name in BOUNDARIES:
        pc = syms[name]
        pos = ((pc >> 16) & 0x7f)*0x8000+(pc & 0x7fff)
        accepted = ((0x08, 0x48, 0xc2, 0xA9, 0xE2)
                    if name in ('SourceVisual_Emit__priority_ready',
                                'SourceVisual_PrepareBlocks__pending')
                    else (0x08, 0x48, 0xc2))
        if blob[pos] not in accepted:
            raise AssertionError('boundary prologue changed; cannot take coherent snapshot: '+name)
    import struct
    for row in plan.values():
        if row['physical'] >= syms['StageBounds_RecordCount']:
            raise AssertionError('built bounds table does not cover physical stage')
        words = struct.unpack_from('<8H', blob, offset+row['physical']*16)
        flags = row['flags'] if row['campaign'] == 3 else 0
        if words[0] != flags:
            raise AssertionError('ROM bounds flags differ from source/Normal release scope')
        if flags:
            for y in range(256):
                clamp, hole = thresholds(row['width'], y)
                if (words[1]+y, words[2+(y & 3)]+y) != (clamp, hole):
                    raise AssertionError('ROM bounds thresholds differ from independent source oracle')
        elif any(words):
            raise AssertionError('Easy control must retain a zero bounds record')
    for path in (rom, rom.with_suffix('.msu'), ROOT/'src/main.bin', ROOT/'src/main.sym',
                 ROOT/'src/generated/stage_bounds_tables.pasm'):
        report.setdefault('artifacts', {})[str(path)] = sha(path)
    return syms


def require_idle_emulator():
    if os.name == 'nt':
        p = subprocess.run(['powershell', '-NoProfile', '-Command',
                            'Get-Process Mesen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'],
                           text=True, capture_output=True, timeout=10)
        if p.stdout.strip():
            raise AssertionError('another Mesen session exists; run this proof serially')
        if p.returncode not in (0, 1):
            raise AssertionError('cannot establish emulator process ownership')


class Proof:
    def __init__(self, m, syms, reporter, report):
        from _harness import read_block, run_frames_exact, exact_input_edge
        self.m, self.s, self.r, self.report = m, syms, reporter, report
        self.read, self.frames, self.edge = read_block, run_frames_exact, exact_input_edge
        self.bases = [0x7e0000+syms['PlayerEntity_DpBase']+i*syms['CHAR_ZP_LEN'] for i in range(6)]
        worker_source = (ROOT/'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        context_match = re.search(r'sta\.l\s+\$(411900),x', worker_source, re.I)
        if not context_match:
            raise AssertionError('persistent Normal context base is not source-resolvable')
        self.sa1_context_base = int(context_match.group(1), 16)

    def need(self, name, condition):
        if not self.r.check(name, condition):
            raise AssertionError(name)

    def val(self, name, size=2):
        return self.mem(self.s[name], size)

    def mem(self, addr, size=2, signed=False):
        return int.from_bytes(self.read(self.m, addr, max(32, size))[:size], 'little', signed=signed)

    def tick(self, count=1):
        self.frames(self.m, count)

    def wait(self, predicate, limit=600):
        for _ in range(limit):
            if predicate():
                return
            self.tick()
        raise AssertionError('bounded wait exhausted')

    @contextmanager
    def hook(self, name):
        yield self.s[name]

    def stop(self, handle, slot=None, attempts=36):
        self.m.bounds_token += 1
        token = self.m.bounds_token
        dp = -1 if slot is None else self.bases[slot] & 0xffff
        self.m.bounds_command.write_text(f'{token} {handle} {dp}\n')
        self.m.resume()
        deadline = time.monotonic()+min(attempts, 60)
        while time.monotonic() < deadline:
            values = self.m.bounds_result.read_text().split()
            if values and int(values[0]) == token and self.m.get_state()['isPaused']:
                token_read, address, k, pc, a, x, y, d, ps, sp = map(int, values)
                cpu = dict(k=k, pc=pc, a=a, x=x, y=y, d=d, ps=ps, sp=sp)
                opcode = self.mem(handle, 1)
                accepted_opcodes = ((0x08, 0x48, 0xC2, 0xA9)
                                    if handle == self.s['SourceVisual_Emit__priority_ready']
                                    else (0x08, 0x48, 0xC2, 0xE2)
                                    if handle == self.s['SourceVisual_PrepareBlocks__pending']
                                    else (0x08, 0x48, 0xC2))
                self.need('exact Lua boundary and physical direct page verified',
                          opcode in accepted_opcodes and address == handle
                          and (cpu['k'] << 16 | cpu['pc']) == handle
                          and cpu['d'] == d and (dp < 0 or dp == d))
                return dict(a=a, x=x, y=y, d=d, ps=ps, sp=sp, pc=address & 0xffff,
                            k=k, stopped_cpu=cpu, token=token_read)
            time.sleep(0.01)
        self.m.pause()
        raise AssertionError('Lua boundary timeout; inspect script loading/CPU keys/target reachability')

    def actor(self, slot):
        base = self.bases[slot]
        row = slot*self.s['CHAR_ZP_LEN']
        values = {n: self.mem(base+self.s['CHAR_'+n], 1 if n in
                            ('HP', 'INPUT_DRIVEN', 'ROSTER_INDEX', 'GRAB_TARGET', 'GRABBED_BY') else 2,
                            signed=n.startswith('THROW_')) for n in
                  ('POS_X', 'POS_Y', 'HP', 'INPUT_DRIVEN', 'ROSTER_INDEX', 'GRAB_TARGET',
                   'GRABBED_BY', 'THROW_ZPOS', 'THROW_ZVEL')}
        for name in ('State', 'Height', 'Velocity', 'DrawY', 'EntryDepth'):
            values[name] = self.mem(self.s['StageBounds_'+name]+row, signed=name in ('Height', 'Velocity', 'DrawY'))
        values['base'] = self.mem(self.s['StageEnv_BaseInteger']+row, signed=True)
        values['base_fraction'] = self.mem(self.s['StageEnv_BaseFraction']+row)
        return dict(slot=slot, address=hex(base), **values)

    def record(self, name, slot, **extra):
        sample = dict(name=name, actor=self.actor(slot),
                      lives=[self.val('Game_Lives'), self.val('G13_P2Lives')],
                      scores=[self.val('Game_Score32', 4), self.val('G13_P2Score32', 4)],
                      timer=self.val('StageTimer_Left'), **extra)
        self.report['snapshots'].append(sample)
        return sample

    def position(self, slot, x, depth, altitude=0):
        for name, value in (('POS_X', x), ('POS_Y', depth), ('THROW_ZPOS', altitude), ('THROW_ZVEL', 0)):
            self.m.write_u16(self.bases[slot]+self.s['CHAR_'+name], value)
        # In the accepted Normal candidate, source combat coordinates are
        # canonical in persistent BW-RAM; writing only the S-CPU mirror lets
        # SA-1 immediately restore its older position over this fixture.
        context = self.m.read_memory('snesSaveRam',
            self.sa1_context_base+slot*256, 256)
        if context[0xE6] in (8, 9) and context[0xF2] == 1:
            self.m.write_u16(self.sa1_context_base+slot*256+20, x, 'snesSaveRam')
            self.m.write_u16(self.sa1_context_base+slot*256+22, depth, 'snesSaveRam')

    def restore_actor(self, slot, baseline):
        """Restore only the actor and environment cells this probe mutates."""
        base = self.bases[slot]
        for name in ('POS_X', 'POS_Y', 'THROW_ZPOS', 'THROW_ZVEL'):
            self.m.write_u16(base+self.s['CHAR_'+name], baseline[name])
        for name in ('HP', 'INPUT_DRIVEN', 'ROSTER_INDEX', 'GRAB_TARGET', 'GRABBED_BY'):
            self.m.write_u8(base+self.s['CHAR_'+name], baseline[name])
        row = slot*self.s['CHAR_ZP_LEN']
        for name in ('State', 'Height', 'Velocity', 'DrawY', 'EntryDepth'):
            self.m.write_u16(self.s['StageBounds_'+name]+row, baseline[name])
        self.m.write_u16(self.s['StageEnv_BaseInteger']+row, baseline['base'])
        self.m.write_u16(self.s['StageEnv_BaseFraction']+row, baseline['base_fraction'])
        context = self.m.read_memory('snesSaveRam',
            self.sa1_context_base+slot*256, 256)
        if context[0xE6] in (8, 9) and context[0xF2] == 1:
            self.m.write_u16(self.sa1_context_base+slot*256+20,
                             baseline['POS_X'], 'snesSaveRam')
            self.m.write_u16(self.sa1_context_base+slot*256+22,
                             baseline['POS_Y'], 'snesSaveRam')

    def restore_checkpoint_actors(self, baselines):
        for slot, baseline in enumerate(baselines):
            self.restore_actor(slot, baseline)

    def native_start(self, target, two_player=False):
        import game_bor_startup_select as startup
        startup.cold_to_title(self.m, self.r)
        self.need('cold native TITLE checks passed', all(ok for _, ok in self.r.results))
        # Do not use title_to_charselect: its legacy contract auto-confirms
        # Easy. TITLE only chooses session mode; set navigation belongs to
        # CHARSELECT phase 1, before either physical player confirms a roster.
        if two_player:
            self.edge(self.m, self.m.BTN_START, 1, port=1)
            self.tick(2)
        self.edge(self.m, self.m.BTN_START, 1, port=0)
        self.wait(lambda: self.val('Game_State') == self.s['GAME_STATE_CHARSELECT']
                  and self.val('BorDifficulty_Chosen', 1) == 1, 360)
        self.need('difficulty begins at source-default Easy', self.val('BorSet_Selected', 1) == 0)
        for sid in range(1, target['set_id']+1):
            self.edge(self.m, self.m.BTN_RIGHT, 1, port=0)
            self.wait(lambda: self.val('BorSet_Selected', 1) == sid, 120)
            self.need('set navigation stays in difficulty prompt',
                      self.val('Game_State') == self.s['GAME_STATE_CHARSELECT']
                      and self.val('BorDifficulty_Chosen', 1) == 1)
        sid = target['set_id']
        self.need('real selected set passes availability, mapping, and full unlock count',
                  self.mem(self.s['BorSet_ContentAvailable']+sid, 1) != 0
                  and self.mem(self.s['BorSet_CampaignMap']+sid, 1) == target['campaign']
                  and self.val('Bor_TimesCompleted', 4) >= self.mem(self.s['BorSet_IfComplete']+sid, 1))
        self.report.setdefault('startup', []).append(dict(set=target['set'], set_id=sid,
                    phase=self.val('BorDifficulty_Chosen', 1), two_player=two_player))
        self.edge(self.m, self.m.BTN_START, 1, port=0)
        self.wait(lambda: self.val('BorDifficulty_Chosen', 1) == 3
                  and self.val('CharSelect_Step', 1) == self.s['CHARSELECT_STEP_WAIT'], 240)
        self.need('difficulty confirmation did not confirm either character',
                  self.val('BorSelect_P1Ready', 1) == 0 and self.val('BorSelect_P2Ready', 1) == 0)
        if two_player:
            self.edge(self.m, self.m.BTN_START, 1, port=1)
            self.wait(lambda: self.val('BorSelect_P2Ready', 1) == 1, 120)
            self.need('P2 character confirmation is independent', self.val('BorSelect_P1Ready', 1) == 0)
        self.edge(self.m, self.m.BTN_START, 1, port=0)
        self.wait(lambda: self.val('Game_State') == self.s['GAME_STATE_PLAYING'])
        self.need('native chosen campaign and physical P2 ownership',
                  self.val('Game_CampaignId', 1) == target['campaign']
                  and self.val('BorSet_Selected', 1) == sid
                  and self.val('Game_CampaignOrdinal', 1) == 0
                  and bool(self.val('G13_TwoPlayerEnabled', 1)) == two_player)

    def reach(self, target, build):
        cid = 'BOR_NORMAL_1A_INTERNAL' if target['campaign'] == 3 else 'BOR_ORIGINAL'
        entries = build.CAMPAIGN_ENTRY_MAPS[cid]
        while self.val('Game_CampaignOrdinal', 1) < target['ordinal']:
            ordinal = self.val('Game_CampaignOrdinal', 1)
            kind, physical, source = entries[ordinal]
            self.need('transit uses native source stage', kind == 'stage' and self.val('Game_StageIndex') == physical)
            skipped = False
            for _ in range(6000):
                if self.val('Game_CampaignOrdinal', 1) != ordinal:
                    break
                if self.val('StageComplete_Active', 1):
                    if not skipped:
                        self.edge(self.m, self.m.BTN_A, 1)
                        skipped = True
                    else:
                        self.tick()
                    continue
                if self.val('Game_State') == self.s['GAME_STATE_PLAYING']:
                    self.m.write_u8(self.s['Spawn_Index'], self.val('Spawn_Count', 1))
                    direction = build.STAGE_CONFIGS[physical].get('scroll_direction', 'right')
                    if direction == 'down':
                        self.m.write_u16(self.s['Screen_PosY'], self.val('Screen_MaxY'))
                    elif direction == 'left':
                        edge = self.val('Screen_MinX')
                        self.need('left edge has valid positive bound', edge > 0)
                        self.m.write_u16(self.s['Screen_PosX'], edge-1)
                    else:
                        self.m.write_u16(self.s['Screen_PosX'], self.val('Stage_TrueMaxX'))
                    for slot in range(1, 6):
                        if slot == 1 and self.val('G13_TwoPlayerEnabled', 1):
                            continue
                        if self.actor(slot)['INPUT_DRIVEN'] == self.s['CHAR_INPUT_DRIVEN_AI']:
                            self.m.write_u8(self.bases[slot]+self.s['CHAR_HP'], 0)
                self.tick()
            else:
                raise AssertionError('native campaign handoff stalled')
            self.wait(lambda: self.val('Game_State') == self.s['GAME_STATE_PLAYING'])
            self.report['route'].append(dict(ordinal=ordinal, source=source, physical=physical))
        self.need('target Stage_Load completed natively', self.val('Game_StageIndex') == target['physical']
                  and self.val('Game_CampaignId', 1) == target['campaign'])
        queue_bytes = (ROOT/target['spawn_path']).stat().st_size
        self.need('real stage queue loaded', self.val('Spawn_Count', 1)*10 == queue_bytes)

    def npc(self, target, admission_start):
        found=[]
        def ready():
            found[:]=[r for r in read_admissions(self.m.bounds_admissions)[admission_start:]
                      if r['stage']==target['physical'] and r['campaign']==target['campaign']
                      and r['kind'] in (0,4,5)]
            return bool(found)
        try:
            if not ready():
                # Queue triggers are compared with Screen_PosX.  Some first
                # records (notably Normal 1C) begin just ahead of the cold
                # camera, so merely polling a live stage never admits them.
                # Use real controller input to cross the authored trigger;
                # do not write Spawn_Index or synthesize an actor.
                self.m.hold_input(self.m.BTN_RIGHT, port=0)
                try:
                    self.wait(ready)
                finally:
                    self.m.release_input(port=0)
        except AssertionError:
            heartbeat=Path(str(self.m.bounds_admissions)+'.heartbeat')
            self.report['admission_wait_failure']=dict(
                heartbeat=heartbeat.read_text() if heartbeat.exists() else None,
                journal_bytes=self.m.bounds_admissions.stat().st_size,
                stage=self.val('Game_StageIndex'),state=self.val('Game_State'),
                index=self.val('Spawn_Index',1),count=self.val('Spawn_Count',1),
                actors=[self.actor(i) for i in range(6)])
            raise
        # FIRST native enemy admission, not first roster which matches an
        # expected answer. Persist evidence before every fail-closed check.
        event=found[0]
        self.report.setdefault('npc_admissions',[]).append(event)
        self.need('completed spawn has a live physical object',event['exists']==1
                  and event['offset']%self.s['CHAR_ZP_LEN']==0)
        slot=event['offset']//self.s['CHAR_ZP_LEN']
        self.need('completed spawn owns an NPC slot',slot in range(2 if self.val('G13_TwoPlayerEnabled',1) else 1,6))
        self.need('completed enemy spawn is live AI',event['hp']>0 and event['mode']==self.s['CHAR_INPUT_DRIVEN_AI'])
        queue=(ROOT/target['spawn_path']).read_bytes()
        record=queue[event['index']*10:event['index']*10+10]
        self.need('completed spawn record equals actual source queue',len(record)==10 and record.hex()==event['record'])
        current=self.actor(slot)
        self.report['npc_admissions'][-1]['current_actor']=current
        obj=event['object_slot']
        self.need('admitted actor identity remains current',current['HP']>0 and current['ROSTER_INDEX']==event['roster']
                  and self.mem(self.bases[slot]+self.s['OOP_SELF_NUM_OFS'],2)==event['object_num']
                  and self.mem(self.s['OopFlags']+obj,2)&1==1
                  and self.mem(self.s['OopNum']+obj,2)==event['object_num']
                  and self.mem(self.s['OopDp']+obj,2)==self.bases[slot]&0xffff)
        return slot


def case_run(case, p, target, build, folder, screenshots):
    heartbeat=Path(str(p.m.bounds_admissions)+'.heartbeat')
    admission_start=len(read_admissions(p.m.bounds_admissions))
    # The ROM exec observer is attached to Game_State_Play, so it cannot
    # advance while the emulator is still in INTRO/TITLE.  Start the native
    # campaign first; `native_start` waits for the real PLAY transition.
    p.native_start(target, two_player=case == 'pit-p2')
    try:
        p.wait(lambda:heartbeat.exists() and int(heartbeat.read_text() or '0')>0,30)
    except AssertionError:
        raise AssertionError('native exec observer not live after PLAY startup; inspect retained mesen.log')
    p.need('actual Game_State_Play ROM exec observer live after startup',int(heartbeat.read_text())>0)
    p.reach(target, build)
    npc = p.npc(target,admission_start)
    roster_id = p.actor(npc)['ROSTER_INDEX']
    admission=p.report['npc_admissions'][-1]
    p.need('physical NPC has a model authored in this actual source stage',
           roster_id < len(build.ROSTER_CONFIGS)
           and build.ROSTER_CONFIGS[roster_id]['family'] == 'bor-original'
           and key(build.ROSTER_CONFIGS[roster_id]['source_character']) == target['source_queue_models'][admission['index']])
    # Real live NPC and player identities are retained. Freeze further queue
    # admission only after observing actual source Stage_Load and actor spawn.
    p.m.write_u8(p.s['Spawn_Index'], p.val('Spawn_Count', 1))
    # Spatial isolation does not grant health or change actor identities. Keep
    # a real NPC alive so the ordinary queue/all-dead clear cannot terminate 5A.
    for i in range(6):
        p.position(i, 64 if i == 0 else 96 if i == 1 and case == 'pit-p2' else 16, 160 if i < 2 else 208)
    checkpoint = folder/(case+'.mst')
    p.m.save_state(checkpoint)
    slot = 1 if case == 'pit-p2' else npc if case in ('pit-npc', 'blocked', 'easy-blocked') else 0
    baseline_actors = [p.actor(i) for i in range(6)]
    baseline_actor = baseline_actors[slot]
    p.record(case+' loaded baseline', slot)

    # Warm one real player packet while the actor is still safely on-screen.
    # A cold source-sized pose may need several serialized 256-byte block
    # uploads; letting a pit actor fall throughout that admission window would
    # retire it before the visual seam can be observed. Keep this same live
    # emulator/cache epoch for the pit check instead of restoring a save state
    # whose MSU/DMA engines are not restored coherently by Mesen.
    with p.hook('SourceVisual_Emit__priority_ready') as warm_emit:
        try:
            warm_cpu = p.stop(warm_emit, slot, attempts=45)
        except AssertionError:
            lease = p.s['SourceVisual_State']+slot*32
            trace = p.s['SourceVisual_DebugTrace']+slot*8
            p.report['source_visual_warm_timeout'] = dict(
                calls=p.val('SourceVisual_CallCount'),
                field=p.val('Nmi_FrameCounter'),
                actor=p.actor(slot),
                key=p.mem(trace, 4), entry=p.mem(trace+4, 2),
                error=p.mem(trace+6, 2),
                lease_entry=p.mem(lease, 2), lease_state=p.mem(lease+6, 2),
                lease_presented=p.mem(lease+28, 1),
                renderer_error=p.val('SourceVisual_Error', 1),
                last_error=p.val('SourceVisual_DebugLastError', 1),
                last_d=p.val('SourceVisual_HostLastD'),
                last_policy=p.val('SourceVisual_HostLastPolicy', 1),
                pending_blocks=[dict(slot=i,
                    block=p.mem(p.s['SourceVisual_BlockCache']+i*8, 2),
                    state=p.mem(p.s['SourceVisual_BlockCache']+i*8+2, 1),
                    owners=p.mem(p.s['SourceVisual_BlockCache']+i*8+4, 1),
                    rows=p.mem(p.s['SourceVisual_BlockCache']+i*8+5, 1))
                    for i in range(64) if p.mem(p.s['SourceVisual_BlockCache']+i*8+2, 1) == 1])
            raise
        warm_actor = p.actor(slot)
        p.record('warmed source-sized production OAM packet', slot,
                 render_cpu=warm_cpu,
                 oam_y=p.val('OamSetSprite_Y', 1),
                 oam_attr=p.val('OamSetSprite_Attr', 1),
                 source_visual_error=p.val('SourceVisual_Error', 1))
        p.need('source-sized Normal packet reached the live player OAM path',
               warm_cpu['d'] == p.bases[slot] & 0xffff
               and warm_actor['HP'] > 0)
    p.restore_checkpoint_actors(baseline_actors)
    with p.hook('StageBoundsHost_Physics__tick') as tick, p.hook('StageBoundsHost_Physics__next') as next_actor:
        p.stop(tick)
        _, first = thresholds(target['width'], 160)
        p.position(slot, first, 160)
        p.stop(next_actor, slot)
        entered_visual = p.record('pit entry before source-sized render', slot)
        p.need('pit state is active before source-sized render',
               entered_visual['actor']['State'] == 1)
    with p.hook('SourceVisual_Emit__priority_ready') as emit:
        try:
            render_cpu = p.stop(emit, slot, attempts=15)
        except AssertionError:
            actor_rows = []
            for actor_slot in range(6):
                trace = p.s['SourceVisual_DebugTrace']+actor_slot*8
                lease = p.s['SourceVisual_State']+actor_slot*32
                actor_rows.append(dict(
                    slot=actor_slot,
                    key=p.mem(trace, 4),
                    entry=p.mem(trace+4, 2),
                    error=p.mem(trace+6, 2),
                    lease_entry=p.mem(lease, 2),
                    lease_chunks=p.mem(lease+2, 2),
                    lease_palette=p.mem(lease+4, 2),
                    lease_state=p.mem(lease+6, 2),
                    lease_presented=p.mem(lease+28, 1)))
            dma_rows = []
            for dma_slot in range(8):
                queue = p.s['DmaQueue']+dma_slot*8
                flags = p.mem(queue+4, 1)
                dma_rows.append(dict(
                    slot=dma_slot, flags=flags,
                    length=p.mem(queue, 2), target=p.mem(queue+2, 2),
                    source=p.mem(queue+5, 2), source_bank=p.mem(queue+7, 1),
                    owner=p.mem(p.s['DmaQueue_Owner']+dma_slot, 1)))
            block_rows = []
            for block_slot in range(64):
                block = p.s['SourceVisual_BlockCache']+block_slot*8
                state = p.mem(block+2, 1)
                if state:
                    block_rows.append(dict(
                        slot=block_slot, index=p.mem(block, 2), state=state,
                        actors=p.mem(block+4, 1), row=p.mem(block+5, 1),
                        payload=p.mem(block+6, 1)))
            p.report['source_visual_wait_diagnostic'] = dict(
                calls=p.val('SourceVisual_CallCount'),
                nmi_field=p.val('Nmi_FrameCounter'),
                host_calls=p.val('SourceVisual_HostCallCount'),
                last_d=p.val('SourceVisual_HostLastD'),
                last_policy=p.val('SourceVisual_HostLastPolicy', 1),
                error=p.val('SourceVisual_Error', 1),
                last_error=p.val('SourceVisual_DebugLastError', 1),
                last_queue_stage=p.val('SourceVisual_DebugQueueStage'),
                current_actor_slot=p.val('SourceVisual_ActorSlot'),
                current_piece_count=p.val('SourceVisual_PieceCount'),
                current_piece_index=p.val('SourceVisual_PieceIndex'),
                current_block_index=p.val('SourceVisual_BlockIndex'),
                current_block_slot=p.val('SourceVisual_BlockSlot'),
                actors=actor_rows, dma=dma_rows, blocks=block_rows,
                dma_cursor=p.val('DmaQueue_CurrentSlot'),
                dma_budget=p.val('DmaQueue_BudgetTotal'))
            raise
        render_actor = p.actor(slot)
        y, attr = p.val('OamSetSprite_Y', 1), p.val('OamSetSprite_Attr', 1)
        piece_y_at = 6 if p.mem(p.bases[slot]+p.s['CHAR_FACING_LEFT'], 1) else 2
        piece_y = p.mem(p.s['SourceVisual_PieceTable']+render_cpu['x']+piece_y_at,
                        1, signed=True)
        p.record('source-sized OAM submission', slot, oam_y=y, oam_attr=attr,
                 render_cpu=render_cpu)
        expected_y = (render_actor['DrawY']+piece_y)&0xFF
        p.need('source-sized catalog packet uses the falling foot and behind-panel priority',
               render_actor['State'] == 1 and render_cpu['d'] == p.bases[slot]&0xffff
               and attr & 0x30 == 0 and y == expected_y)
    p.m.load_state(checkpoint)
    p.restore_checkpoint_actors(baseline_actors)

    if case in ('blocked', 'easy-blocked'):
        clamp_slot = npc
        with p.hook('StageBoundsHost_Clamp') as entry, p.hook('StageBoundsHost_Clamp__done') as done:
            for depth in (128, 160, 186):
                limit, _ = thresholds(target['width'], depth)
                for x in (limit-1, limit, limit+1):
                    p.m.load_state(checkpoint)
                    p.restore_checkpoint_actors(baseline_actors)
                    # Clamp is reached through the native movement path, not
                    # from an idle PLAY field.  Enter the existing hook with
                    # real directional input before setting the test probe's
                    # coordinate at the exact threshold.
                    p.m.hold_input(p.m.BTN_RIGHT, port=0)
                    try:
                        p.stop(entry, clamp_slot)
                    finally:
                        p.m.release_input(port=0)
                    p.position(clamp_slot, x, depth)
                    p.stop(done, 0)
                    expected = x if case == 'easy-blocked' else min(x, limit)
                    snapshot = p.record('blocked threshold', clamp_slot, injected_x=x, injected_depth=depth, expected=expected)
                    p.need('source depth clamp or unaffected Easy control at -1/equal/+1', snapshot['actor']['POS_X'] == expected
                           and snapshot['actor']['POS_Y'] == depth and snapshot['actor']['State'] == 0)
        return

    if case == 'easy':
        # Same source endhole, but Normal-only host must be inert for Easy.
        p.m.load_state(checkpoint)
        p.restore_checkpoint_actors(baseline_actors)
        with p.hook('StageBoundsHost_Physics') as boundary, p.hook('Core_Oop_Play') as done:
            p.stop(boundary)
            _, first = thresholds(target['width'], 160)
            p.position(0, first, 160)
            before = p.record('Easy before same-source threshold', 0)
            p.stop(done)
            after = p.record('Easy after gated physics', 0)
            p.need('Easy source endhole control: no new bounds mutation', after['actor'] == before['actor']
                   and after['lives'] == before['lives'] and after['scores'] == before['scores'])
        return

    # Isolate predicates from ordinary movement at an actual, due physics tick.
    with p.hook('StageBoundsHost_Physics__tick') as tick, p.hook('StageBoundsHost_Physics__next') as next_actor:
        for depth in (128, 129, 130, 131, 160, 186):
            _, first = thresholds(target['width'], depth)
            for x, altitude, expected in ((first-1, 0, 0), (first, 21, 0), (first, -21, 0),
                                         (first, 20, 1), (first, -20, 1), (first, 0, 1)):
                p.m.load_state(checkpoint)
                p.stop(tick)
                pre = p.actor(slot)
                p.report['snapshots'].append(dict(name='pit boundary pre-injection', slot=slot,
                                                  actor=pre, expected_baseline=baseline_actor))
                p.restore_checkpoint_actors(baseline_actors)
                restored = p.actor(slot)
                p.need('probe resets actor and bounds cells to the captured native checkpoint baseline',
                       all(restored[field] == baseline_actor[field] for field in
                           ('POS_X', 'POS_Y', 'THROW_ZPOS', 'THROW_ZVEL', 'State', 'Height',
                            'Velocity', 'DrawY', 'base', 'base_fraction')))
                p.position(slot, x, depth, altitude)
                cpu = p.stop(next_actor, slot)
                snap = p.record('endhole boundary', slot, x=x, depth=depth, altitude_q8=altitude,
                                expected_state=expected, cpu=cpu)
                p.need('strict depth boundary and grounded carry contract', snap['actor']['State'] == expected
                       and (cpu['ps'] & 1) == expected)
                if expected:
                    p.need('entry transforms depth/base and preserves screen position',
                           snap['actor']['POS_Y'] == 123 and snap['actor']['base'] == -800
                           and snap['actor']['base_fraction'] == 0 and snap['actor']['DrawY'] == depth
                           and snap['actor']['Height'] == 3080-25*depth+int(F(25*altitude, 256)))

    # Full lifecycle from a fresh native checkpoint, with real reciprocal links.
    p.m.load_state(checkpoint)
    p.restore_checkpoint_actors(baseline_actors)
    with p.hook('StageBoundsHost_Physics__tick') as tick, p.hook('StageBoundsHost_Physics__next') as next_actor:
        p.stop(tick)
        partner = npc if slot in (0, 1) and case != 'pit-npc' else 0
        _, first = thresholds(target['width'], 160)
        p.position(slot, first, 160)
        p.position(partner, 64, 160)
        p.m.write_u8(p.bases[slot]+p.s['CHAR_GRAB_TARGET'], partner)
        p.m.write_u8(p.bases[partner]+p.s['CHAR_GRABBED_BY'], slot)
        before = p.record('lifecycle before entry', slot)
        p.stop(next_actor, slot)
        entered = p.record('lifecycle entered', slot)
        p.need('both physical grab links released', entered['actor']['GRAB_TARGET'] == 255
               and p.actor(partner)['GRABBED_BY'] == 255)
    with p.hook('StageBounds_ApplyPitDamage_Long') as death, p.hook('StageBoundsHost_ApplyPitDamage__done') as done:
        cpu = p.stop(death, slot, attempts=72)
        falling = p.record('native pit damage callback', slot, cpu=cpu)
        p.need('native gravity crossed strict source PIT_DEPTH', falling['actor']['State'] == 2
               and falling['actor']['Height'] < -5000 and cpu['a'] == 10000)
        p.stop(done, slot)
        after = p.record('canonical lifecycle after callback', slot)
        p.need('pit does not grant pickup/score rewards', after['scores'] == before['scores'])
        if case != 'pit-npc':
            player = 1 if case == 'pit-p2' else 0
            p.need('exactly one stock decrement in physical player owner',
                   after['lives'][player] == before['lives'][player]-1
                   and after['lives'][1-player] == before['lives'][1-player])
            p.need('canonical respawn clears pit state/base', after['actor']['HP'] > 0
                   and after['actor']['State'] == 0 and after['actor']['base'] == 0)
        else:
            p.need('NPC retired without touching player stock', after['actor']['HP'] == 0
                   and after['actor']['State'] == 2 and after['lives'] == before['lives'])
    if screenshots:
        p.report.setdefault('screenshots', []).append(p.m.take_screenshot())
    p.tick(30)
    dwell = p.record('post-death dwell', slot)
    p.need('no duplicate pit life charge', dwell['lives'] == after['lives'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-native', action='store_true')
    parser.add_argument('--rom-sha256')
    parser.add_argument('--case', choices=['all', *TARGETS], default='all')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--screenshots', action='store_true')
    args = parser.parse_args(argv)
    report = dict(verdict='FAIL', native_executed=False, checks=[], route=[], snapshots=[],
                  scope='accelerated native environment proof; no combat or manual visual acceptance')
    report['harness_sha256'] = sha(Path(__file__))
    report['boundary_method'] = 'Lua pre-op CPU capture + single PHP/PHA/REP step; exact PC/physical D verification'
    output = args.report or (ROOT/'out/game_s8_stage_bounds.json' if args.run_native else None)
    try:
        build, plan = source_plan(report)
        if args.run_native:
            syms = build_preflight(args, report, plan)
            sys.path.insert(0, str(ROOT/'tools/verify'))
            from _harness import Reporter
            r = Reporter('S8-STAGE-BOUNDS', kind='GATE')
            report['checks'] = r.results
            folder = output.parent/(output.stem+'_states')
            folder.mkdir(parents=True, exist_ok=True)
            for case in TARGETS if args.case == 'all' else [args.case]:
                require_idle_emulator()
                with native_session(syms, folder, Path(report['rom_path'])) as m:
                    report['native_executed'] = True
                    case_run(case, Proof(m, syms, r, report), plan[case], build, folder, args.screenshots)
            if not all(ok for _, ok in r.results):
                raise AssertionError('one or more native checks failed')
            report['verdict'] = 'PASS'
        else:
            report['verdict'] = 'STATIC_ONLY'
            report['nonclaims'] = ['No ROM freshness/link proof', 'No emulator launched', 'No native PASS']
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        print(report['error'], file=sys.stderr)
    finally:
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report if not args.run_native else dict(verdict=report['verdict'], report=str(output)), indent=2))
    return int(report['verdict'] == 'FAIL')


if __name__ == '__main__':
    raise SystemExit(main())
