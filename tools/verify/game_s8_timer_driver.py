"""Opt-in accelerated native Normal5A fixture. Imported only by --run.

No timer callback injection, synthetic Time actor, or source queue byte writes.
Every fixture memory write and real input edge is journaled. Native retirement
and timeout are never implemented in Python; the ROM must perform them.
"""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from game_s8_timer_probe import ROOT, prepare, gates, parse, digest


def pressure_record(spec):
    """Additional admission-pressure record, NOT the required retired-slot case.

    Identified-enemy kind/subtype establishes identity; roster0 is valid.
    Required reuse is independently selected by source ordinary_reuse_case.
    """
    queue = bytes.fromhex(spec['queue'])
    return next(i for i in spec['spawn_indices']
                if i > spec['time_indices'][0] and queue[i*10:i*10+2] == b'\0\0'
                and queue[i*10+6] & 7 == 5 and queue[i*10+6] >> 5 == 2)


def await_native_retirement(snapshot, tick, require, budget=360):
    """Observe callback completion, not just its preceding pending decrement.

    A frame stop/SDK read can see pending=0 before Host_Retire clears HP.
    This is NOT a timing allowance: the independent native log gate requires
    both retirement and cleared actor at collect_tick+600 exactly.
    """
    settling = 0
    for step in range(budget + 1):
        state = snapshot()
        if state['pending'] == 0:
            if state['hp'] == 0:
                return True
            settling += 1
            require('retirement callback completes after zero observation', settling <= 4)
        else:
            require('reserved slot retains identity and HP', state['roster'] == 46
                    and state['hp'] > 0 and state['kind'] == 0)
        if step < budget:
            tick()
    return False


def select_normal(m, startup, read, tick, wait, require):
    """Same real prompt sequence as game_s8_normal_campaign; no state writes."""
    tick(m.BTN_START)
    wait(lambda: read(startup.STATE, 2) == startup.CHARSELECT
         and read(startup.DIFFICULTY) == 1, 360, 'TITLE START reaches difficulty prompt')
    tick(m.BTN_RIGHT)
    wait(lambda: read(startup.SELECTED) == 1, 120, 'difficulty RIGHT selects available Normal')
    require('Normal selected in difficulty prompt', read(startup.STATE, 2) == startup.CHARSELECT
            and read(startup.DIFFICULTY) == 1)
    tick()
    tick(m.BTN_START)
    wait(lambda: read(startup.DIFFICULTY) == 3 and read(startup.CHAR_STEP) == 3,
         360, 'Normal confirmation reaches player selector')
    require('player selector retains Normal', read(startup.SELECTED) == 1
            and read(startup.STATE, 2) == startup.CHARSELECT)
    tick()
    tick(m.BTN_START)
    wait(lambda: read(startup.STATE, 2) == startup.PLAYING, 600, 'character select reaches PLAYING')


def run_native(args):
    # Fail before loading emulator support if artifacts are not fully linked.
    spec, lua = prepare(args.linked)
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=False)  # never overwrite an earlier run
    (folder / 'spec.json').write_text(json.dumps(spec, indent=2))
    script = folder / 'observer.lua'
    script.write_text(lua, encoding='utf-8')
    log = folder / 'mesen.log'
    report = dict(status='FAIL', scope='real selected Normal startup; accelerated 5A source-queue fixture, NOT campaign progression proof',
                  writes=[], inputs=[], checks={}, screenshots=[], frames=0)
    try:
        import _harness as h
        import game_bor_startup_select as startup
        import sys
        sys.path.insert(0, str(ROOT))
        import build_rom as build
        import mesen_mcp.session as session_module
        s = spec['symbols']
        queue = bytes.fromhex(spec['queue'])
        stride = spec['stride']
        playing, paused = spec['playing'], spec['paused']
        entries = build.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']
        ordinal = next(i for i, e in enumerate(entries) if e[0] == 'stage' and e[1] == spec['stage'])
        if ordinal < 1 or entries[ordinal-1][0] != 'stage':
            raise AssertionError('fixture requires authored preceding stage')

        def launch(argv, **kwargs):
            return subprocess.Popen([*argv, str(script)], **kwargs)
        proxy = SimpleNamespace(Popen=launch, DEVNULL=subprocess.DEVNULL, PIPE=subprocess.PIPE,
                                TimeoutExpired=subprocess.TimeoutExpired)
        # Same repository launch-time Lua attachment used by S6 probes.
        # Scoped ROM-path override also supports old _harness versions while
        # main's BOR_TEST_ROM support lands; no shared harness edits.
        with patch.object(h, 'rom_path', lambda _: spec['paths']['distribution/bor.sfc']), \
             patch.object(session_module, 'subprocess', proxy), \
             h.open_session(__file__, stderr_log=log) as m:
            def read(address, size=1):
                return int.from_bytes(bytes(h.read_block(m, address, 32)[:size]), 'little')
            def get(name, size=1):
                return read(s[name], size)
            def write(name, value, size=1, reason='fixture precondition'):
                address = s[name] if isinstance(name, str) else name
                report['writes'].append(dict(frame=report['frames'], target=name, address=address, value=value, size=size, reason=reason))
                (m.write_u16 if size == 2 else m.write_u8)(address, value)
            def tick(button=None):
                if button is None:
                    h.run_frames_exact(m, 1)
                else:
                    report['inputs'].append(dict(frame=report['frames'], button=button, port=0))
                    h.exact_input_edge(m, button, 1, port=0)
                report['frames'] += 1
            def wait(predicate, limit, label):
                for _ in range(limit):
                    if predicate():
                        return
                    tick()
                raise AssertionError(label)
            def require(label, condition):
                report['checks'][label] = bool(condition)
                if not condition:
                    raise AssertionError(label)
            def shot(label):
                from capture_presentation_state import capture_presentation
                captured = capture_presentation(m, s, folder/'presentation', label,
                                                context=dict(driver_frame=report['frames'], artifacts=spec['artifacts']))
                report['screenshots'].append(dict(label=label, result=captured['screenshot'],
                                                 presentation_capture=captured['path'], capture_errors=captured['errors']))
            def actor(slot, field):
                return 0x7E0A00 + slot*stride + s[field]
            def find_time():
                return next((i for i in range(1, 6) if read(actor(i, 'CHAR_ROSTER_INDEX')) == 46
                             and read(actor(i, 'CHAR_PICKUP_TYPE')) == 6 and read(actor(i, 'CHAR_HP')) > 0), None)

            boot = h.Reporter('S8-TIMER-STARTUP')
            # Fresh launch is already reset; resetting here unloads Lua.
            with patch.object(m, 'reset_emulator', lambda: None):
                startup.cold_to_title(m, boot)
            require('real cold startup', all(ok for _, ok in boot.results))
            prompt = SimpleNamespace(STATE=startup.STATE, CHARSELECT=startup.CHARSELECT,
                                     DIFFICULTY=startup.DIFFICULTY, CHAR_STEP=startup.CHAR_STEP,
                                     PLAYING=startup.PLAYING, SELECTED=s['BorSet_Selected'])
            select_normal(m, prompt, read, tick, wait, require)
            require('real selected Normal session', get('Game_CampaignId') == 3)

            # Explicit stage-route acceleration only. Production dispatcher
            # consumes the authored predecessor and loads the real 5A catalog.
            write('Game_CampaignOrdinal', ordinal-1, reason='5A fixture preceding typed entry')
            write('Game_StageIndex', entries[ordinal-1][1], 2, 'matching predecessor identity')
            write('Stage_LoadPending', 1, reason='native typed stage handoff fixture')
            write('Game_State', s['GAME_STATE_STAGECLEAR'], 2, 'native typed stage handoff fixture')
            wait(lambda: get('Game_StageIndex', 2) == spec['stage'] and get('Game_State', 2) == playing,
                 1200, 'native 5A load failed')
            require('loaded source queue exact', bytes(h.read_block(m, s['SpawnTable_Wram'], max(32,len(queue))))[:len(queue)] == queue)
            wait(lambda: find_time() is not None, 300, 'authored trigger0 Time did not spawn')
            slot = find_time()
            report['time_slot'] = slot
            # Suspend subsequent records, not Time production or queue contents.
            write('Spawn_Index', get('Spawn_Count'), reason='isolate early organic Time')
            item_x, item_y = read(actor(slot,'CHAR_POS_X'),2), read(actor(slot,'CHAR_POS_Y'))
            write(actor(0,'CHAR_POS_X'), item_x, 2, 'neutral overlap geometry')
            write(actor(0,'CHAR_POS_Y'), item_y, reason='neutral overlap geometry')
            for _ in range(65):
                tick()
                require('neutral overlap leaves Time live', read(actor(slot,'CHAR_PICKUP_TYPE')) == 6
                        and read(actor(slot,'CHAR_HP')) > 0 and read(s['StageTimer_Pending']+2*slot,2) == 0)
            shot('neutral-Time-countdown')
            tick(m.BTN_Y)
            wait(lambda: read(s['StageTimer_Pending']+2*slot,2) > 0, 30, 'real attack did not collect Time')
            require('native pickup reset', get('StageTimer_Left',2) > 39600)
            shot('collected-Time-hidden')
            # Use an authored trigger0 actor, not record4's trigger80 which
            # vertical camera easing can move below before Spawn_Play runs.
            pressure = pressure_record(spec)
            write('Spawn_Index', pressure, reason='real source admission while Time slot reserved')
            write('Screen_PosY', int.from_bytes(queue[pressure*10:pressure*10+2],'little'), 2,
                  'authored reservation-pressure trigger')
            for _ in range(12):
                tick()
                if get('Spawn_Index') != pressure:
                    break
            require('source pressure record actually admitted', get('Spawn_Index') != pressure)
            write('Spawn_Index', get('Spawn_Count'), reason='end reservation-pressure admission')
            for i in range(1,6):
                if i != slot:
                    write(actor(i,'CHAR_POS_X'),400,2,'keep pressure actors away from collector')
            # Exact600 is checked by Lua at native BeginTick/Retire hooks;
            # field polling alone cannot certify the subfield tick boundary.
            def retirement_snapshot():
                return dict(pending=read(s['StageTimer_Pending']+2*slot,2),
                            hp=read(actor(slot,'CHAR_HP')), roster=read(actor(slot,'CHAR_ROSTER_INDEX')),
                            kind=read(actor(slot,'CHAR_PICKUP_TYPE')))
            require('native delayed retirement', await_native_retirement(retirement_snapshot, tick, require))

            # First-free allocation may fill earlier slots before the retired
            # slot. Re-offer the REQUIRED ordinary SOURCE enemy record,
            # up to twice the available actor count; never inject HP or slot.
            # Expected roster comes from source binding, never current byte9.
            # An unfixed legacy retain-art encoding must FAIL this test.
            report['reuse_admissions'] = []
            ordinary = spec['ordinary_reuse_case']
            report['required_ordinary_reuse'] = ordinary
            for attempt in range((s['CHARACTER_ACTOR_COUNT']-1)*2):
                index = ordinary['index']
                before = [(read(actor(i,'CHAR_HP')), read(actor(i,'CHAR_ROSTER_INDEX'))) for i in range(1,6)]
                write('Spawn_Index', index, reason='required ordinary-source identity re-admission after retirement')
                for _ in range(60):
                    tick()
                    if get('Spawn_Index') != index:
                        break
                admitted = get('Spawn_Index') != index
                report['reuse_admissions'].append(dict(attempt=attempt, record=index, admitted=admitted,
                    frame=report['frames'], before=before,
                    after=[(read(actor(i,'CHAR_HP')), read(actor(i,'CHAR_ROSTER_INDEX'))) for i in range(1,6)]))
                write('Spawn_Index', get('Spawn_Count'), reason='end source-record allocation step')
                require('ordinary source reuse admission completed', admitted)
                if read(actor(slot,'CHAR_HP')) > 0:
                    break
            require('native ordinary-source physical slot reuse', read(actor(slot,'CHAR_HP')) > 0
                    and read(actor(slot,'CHAR_ROSTER_INDEX')) == ordinary['expected_roster'])
            # Keep test geometry away from newly admitted combatants. These
            # are fixture positions, not actor lifecycle/damage mutations.
            for i in range(1,6):
                write(actor(i,'CHAR_POS_X'), 400, 2, 'timeout isolation geometry')
            write(actor(0,'CHAR_POS_X'), 100, 2, 'timeout isolation geometry')
            write('Screen_PosY', 0, 2, 'avoid terminal stage clear during timeout fixture')
            tick(m.BTN_START)
            wait(lambda: get('Game_State',2) == paused,120,'pause input failed')
            frozen = get('StageTimer_Left',2)
            for _ in range(65):
                tick()
                require('paused timer fixed', get('StageTimer_Left',2) == frozen)
            shot('pause')
            tick(m.BTN_START)
            wait(lambda: get('Game_State',2) == playing,120,'resume input failed')
            for _ in range(130):
                tick()
            shot('countdown-after-resume')
            lives = get('Game_Lives',2)
            require('timeout setup has living P1 and spare stock', lives >= 2 and read(actor(0,'CHAR_HP')) > 0)
            write('StageTimer_Left',2,2,'bounded timeout threshold, not damage/reset injection')
            wait(lambda: get('StageTimer_ShowTimeOver',2) == 1,30,'timeout did not execute')
            tick(); shot('TIME-OVER')
            wait(lambda: get('Game_Lives',2) == lives-1 and read(actor(0,'CHAR_HP')) > 0,900,'native death stock/respawn failed')
            shot('native-respawn')
        observed = gates(spec, parse(log.read_text(errors='replace')))
        report['native_gates'] = observed
        report['status'] = 'OBSERVED_GATES_PASS_VISUAL_REVIEW_REQUIRED' if all(observed.values()) else 'FAIL'
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    finally:
        if log.exists():
            report['log_sha256'] = digest(log)
        (folder / 'report.json').write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(dict(status=report['status'], report=str(folder/'report.json'))))
    return 0 if report['status'].startswith('OBSERVED_GATES_PASS') else 1
