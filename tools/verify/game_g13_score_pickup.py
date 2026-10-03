#!/usr/bin/env python3
"""Focused G13 score, pickup-owner, GET-pose, and fresh-reset gate.

The fixture changes only legal item metadata/geometry and session-owned
preconditions.  Collection, reward dispatch, score saturation/life extension,
and P2 GET selection remain production code.

Current packed content does not organically produce an alive PROP with both
nonzero PickupType and ItemRosterIdx == 0.  That synthetic state is eligible
for both lethal instant reward and passive pickup, so instant MONEY cases are
reported as not applicable/unmeasured rather than used as gates.  Organic
MONEY break/reveal/collect coverage belongs to the stage-content pickup gate.
"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, exact_input_edge, open_session, pasm_constant,
                      pasm_constant_in, read_block, run_frames_exact, poll_until)
from game_g13_two_player_input import clear_inputs, neutral_joint
import game_bor_startup_select as startup

ZP = pasm_constant('CHAR_ZP_LEN')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYM = os.path.join(ROOT, 'src', 'main.sym')
sys.path.insert(0, ROOT)
import build_rom
from shipped_content import normal_player_entries
BOR_DEFAULT_P2 = normal_player_entries('bor-original')[0][0]
P1 = 0x7E0A00; P2 = P1 + ZP; ITEM = P1 + 2 * ZP
POS_X = pasm_constant('CHAR_POS_X'); POS_Y = pasm_constant('CHAR_POS_Y')
HP = pasm_constant('CHAR_HP'); HP_MAX = pasm_constant('CHAR_HP_MAX')
SELECTED = pasm_constant('CHAR_SELECTED'); INPUT = pasm_constant('CHAR_INPUT_DRIVEN')
FACING_LEFT = pasm_constant('CHAR_FACING_LEFT')
PICKUP = pasm_constant('CHAR_PICKUP_TYPE'); VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
GET_FCOUNT = pasm_constant('CHAR_GET_FCOUNT')
PROP = pasm_constant('CHAR_INPUT_DRIVEN_PROP')
PT_APPLE = pasm_constant('PICKUP_TYPE_APPLE'); PT_MEAT = pasm_constant('PICKUP_TYPE_MEAT')
PT_MONEY = pasm_constant('PICKUP_TYPE_MONEY'); PT_ONEUP = pasm_constant('PICKUP_TYPE_ONEUP')
PT_GOLD = pasm_constant('PICKUP_TYPE_GOLD'); GET_VARIANT = pasm_constant('GET_MOVE_VARIANT')
HEAL_APPLE = pasm_constant('PICKUP_HEAL_APPLE'); HEAL_MEAT = pasm_constant('PICKUP_HEAL_MEAT')
SCORE_MONEY = pasm_constant('PICKUP_SCORE_MONEY'); SCORE_GOLD = pasm_constant('PICKUP_SCORE_GOLD')
GS = pasm_constant_in('src/core/game_state.pasm', 'Game_Score')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
P2S = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Score')
P2L = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
MODE = pasm_constant('G13_TwoPlayerEnabled')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
GAME_STATE_CHARSELECT = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_CHARSELECT')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE_STEP = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
CHARSELECT_STEP = pasm_constant_in('src/core/game_state.pasm', 'CharSelect_Step')
CHARSELECT_WAIT = pasm_constant_in('src/core/game_state.pasm', 'CHARSELECT_STEP_WAIT')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
ITEM_IDX = pasm_constant_in('src/core/spawn.pasm', 'Entity2_ItemRosterIdx')
HITSTUN = pasm_constant('CHAR_HIT_STUN')
FRAME = pasm_constant('CHAR_FRAME_INDEX')
TICK = pasm_constant('CHAR_TICK_COUNTER')
ATTACKED = pasm_constant('CHAR_HIT_APPLIED')
ACTOR_INV = pasm_constant_in('src/core/game_state.pasm', 'Actor_InvulnFrames')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
HIT_SCORE = pasm_constant('HIT_SCORE')

def u8(m, a): return read_block(m, a, 32)[0]
def u16(m, a):
    b = read_block(m, a, 32); return b[0] | b[1] << 8

def u32(m, a):
    b = read_block(m, a, 32)
    return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)

def put32(m, a, value):
    h = f'{value & 0xFFFFFFFF:08x}'
    m.write_hex(a, h[6:8] + h[4:6] + h[2:4] + h[0:2])

def symbol(name):
    rx = re.compile(r'^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4,6})\s+' + re.escape(name) + r'\s*$')
    with open(SYM, encoding='utf-8') as f:
        for line in f:
            hit = rx.match(line.strip())
            if hit:
                return (int(hit.group(1), 16) << 16) | int(hit.group(2), 16)
    raise KeyError(name)


def roster_index(name):
    """Resolve an embedded object identity from the authoritative roster."""
    for index, prefix in enumerate(build_rom.ROSTER_PREFIXES):
        if prefix.rsplit('/', 1)[-1].lower() == name.lower():
            return index
    raise KeyError(name)

def setup(m):
    setup_reporter = Reporter('G13-SCORE-SETUP')
    startup.cold_to_title(m, setup_reporter)
    startup.title_to_charselect(m, two_player=True)
    exact_input_edge(m, m.BTN_START, 1, port=1)
    exact_input_edge(m, 0, 1, port=1)
    exact_input_edge(m, m.BTN_START, 1, port=0)
    assert poll_until(m, lambda mm: u16(mm, GAME_STATE) == GAME_STATE_PLAYING, 240)
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    for b, x in ((P1, 120), (P2, 180)):
        m.write_u16(b + POS_X, x); m.write_u8(b + POS_Y, 150)
        m.write_u8(b + HP, HP_MAX); m.write_u8(b + SELECTED, 0)
    for i in range(3, 6):
        b = P1 + i * ZP; m.write_u8(b + HP, 0); m.write_u8(b + INPUT, 2)
    m.write_u8(ITEM + INPUT, PROP); m.write_u8(ITEM + HP, 1)
    m.write_u8(ITEM_IDX, 0); m.write_u16(ITEM + POS_X, 180); m.write_u8(ITEM + POS_Y, 150)
    clear_inputs(m)
    # 1AEASY has a real trigger-0 1UP that may be collected during the
    # required session-settle frames.  Reset only the session counters used
    # by these focused ownership/threshold assertions after that window.
    m.write_u16(GS, 0); m.write_u16(P2S, 0)
    m.write_u16(LIVES, pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START'))
    m.write_u16(P2L, pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START'))
    print('SETUP', {'mode': u8(m, MODE), 'p2_input': u8(m, P2 + INPUT),
                    'p2_hp': u8(m, P2 + HP), 'p2_get': u8(m, P2 + GET_FCOUNT),
                    'game_state': u8(m, GAME_STATE), 'item_input': u8(m, ITEM + INPUT)}, flush=True)

def collect(m, owner, kind, score=0, lives=0, slot=2, service_frames=1):
    item = P1 + slot * ZP
    item_idx = ITEM_IDX + (slot - 2)
    b = P1 if owner == 0 else P2
    m.write_u16(b + POS_X, 100); m.write_u8(b + POS_Y, 150)
    m.write_u8(b + SELECTED, 0); m.write_u8(b + HP, 10 if kind in (PT_APPLE, PT_MEAT) else HP_MAX)
    for player in (P1, P2):
        m.write_u8(player + SELECTED, 0)
        m.write_u8(player + VARIANT, 0)
        m.write_u8(player + pasm_constant('CHAR_HIT_STUN'), 0)
        m.write_u8(player + pasm_constant('CHAR_FRAME_INDEX'), 0xFF)
        m.write_u8(player + pasm_constant('CHAR_TICK_COUNTER'), 1)
    m.write_u8(item + INPUT, PROP); m.write_u8(item + HP, 1); m.write_u8(item + PICKUP, kind)
    m.write_u8(item_idx, 0); m.write_u16(item + POS_X, 100); m.write_u8(item + POS_Y, 150)
    # Keep the non-collector outside the hitbox without relying on a large
    # out-of-viewport coordinate that the production tether may clamp back
    # into the item.  The collector remains at the item, the partner is at
    # the opposite side of the bounded viewport.
    m.write_u16((P2 if owner == 0 else P1) + POS_X, 400)
    before = {'p1_hp':u8(m,P1+HP),'p2_hp':u8(m,P2+HP),'score':u16(m,GS),'p2_score':u16(m,P2S),
              'lives':u8(m,LIVES),'p2_lives':u8(m,P2L),'item':u8(m,item+PICKUP)}
    before.update({'mode':u8(m,MODE),'p2_input':u8(m,P2+INPUT),'p2_x':u16(m,P2+POS_X),
                   'p1_x':u16(m,P1+POS_X),'item_x':u16(m,item+POS_X),
                   'item_input':u8(m,item+INPUT)})
    hp1_hook = m.add_write_hook(P1 + HP, P1 + HP)
    hp2_hook = m.add_write_hook(P2 + HP, P2 + HP)
    owner_hook = m.add_write_hook(pasm_constant('G13_PickupForP2'), pasm_constant('G13_PickupForP2'))
    run_frames_exact(m, service_frames)
    events = m.drain_notifications()
    after = {'p1_hp':u8(m,P1+HP),'p2_hp':u8(m,P2+HP),'score':u16(m,GS),'p2_score':u16(m,P2S),
             'lives':u8(m,LIVES),'p2_lives':u8(m,P2L),'item':u8(m,item+PICKUP),
             'p1_selected':u8(m,P1+SELECTED),'p2_selected':u8(m,P2+SELECTED),
             'p1_variant':u8(m,P1+VARIANT),'p2_variant':u8(m,P2+VARIANT),
             'owner':u8(m,pasm_constant('G13_PickupForP2'))}
    after['mode'] = u8(m, MODE)
    after['writes'] = [{'address':e.get('params',{}).get('address'), 'value':e.get('params',{}).get('value'), 'handle':e.get('params',{}).get('handle')} for e in events if e.get('params',{}).get('handle') in (hp1_hook,hp2_hook,owner_hook)]
    for h in (hp1_hook, hp2_hook, owner_hook): m.remove_hook(h)
    return before, after

def prepare_item(m, kind, x=100, hp=1):
    """Prepare one legal collectible without touching NPC lifecycle state."""
    m.write_u8(ITEM + INPUT, PROP); m.write_u8(ITEM + HP, hp)
    m.write_u8(ITEM + PICKUP, kind); m.write_u8(ITEM_IDX, 0)
    m.write_u16(ITEM + POS_X, x); m.write_u8(ITEM + POS_Y, 150)

def true_tie(m):
    """Both collectors overlap before the first PLAYING transaction."""
    for b in (P1, P2):
        m.write_u16(b + POS_X, 100); m.write_u8(b + POS_Y, 150)
        m.write_u8(b + HP, HP_MAX); m.write_u8(b + SELECTED, 0)
        m.write_u8(b + HITSTUN, 0); m.write_u8(b + VARIANT, 0)
    m.write_u16(GS, 0); m.write_u16(P2S, 0); m.write_u8(pasm_constant('G13_PickupForP2'), 0)
    prepare_item(m, PT_MONEY, 100)
    hooks = {name: m.add_write_hook(addr, addr) for name, addr in {
        'owner': pasm_constant('G13_PickupForP2'), 'score': GS,
        'p2_score': P2S, 'item_type': ITEM + PICKUP, 'item_hp': ITEM + HP}.items()}
    run_frames_exact(m, 1)
    events = m.drain_notifications()
    first = {'score': u16(m, GS), 'p2_score': u16(m, P2S),
             'item_type': u8(m, ITEM + PICKUP), 'item_hp': u8(m, ITEM + HP),
             'owner': u8(m, pasm_constant('G13_PickupForP2')),
             'writes': [e.get('params', {}) for e in events
                        if e.get('params', {}).get('handle') in hooks.values()]}
    run_frames_exact(m, 1)
    second = {'score': u16(m, GS), 'p2_score': u16(m, P2S),
              'item_type': u8(m, ITEM + PICKUP), 'item_hp': u8(m, ITEM + HP)}
    for h in hooks.values(): m.remove_hook(h)
    return first, second

def owner_leak(m):
    """Two transactions in one session, proving the one-shot owner clears."""
    m.write_u16(GS, 0); m.write_u16(P2S, 0)
    b1, a1 = collect(m, 1, PT_MONEY, slot=2)
    # Clear only action/geometry state between legal independent touches.
    for b in (P1, P2):
        m.write_u8(b + SELECTED, 0); m.write_u8(b + HITSTUN, 0)
    clear_inputs(m); run_frames_exact(m, 2)
    b2, a2 = collect(m, 0, PT_GOLD, slot=3, service_frames=3)
    return {'first': {'before': b1, 'after': a1},
            'second': {'before': b2, 'after': a2},
            'owner_final': u8(m, pasm_constant('G13_PickupForP2'))}

def p2_meat(m, hp):
    m.write_u8(P2 + HP, hp)
    return collect(m, 1, PT_MEAT)

def instant_break(m, owner, kind):
    """Test a real lethal attack with a non-collectible target."""
    attacker = P1 if owner == 0 else P2
    other = P2 if owner == 0 else P1
    for b, x in ((attacker, 120), (other, 400)):
        m.write_u16(b + POS_X, x); m.write_u8(b + POS_Y, 150)
        m.write_u8(b + HP, HP_MAX); m.write_u8(b + SELECTED, 0)
        m.write_u8(b + VARIANT, 0); m.write_u8(b + HITSTUN, 0)
        m.write_u8(b + FACING_LEFT, 0)
        m.write_u8(b + FRAME, 0xFF); m.write_u8(b + TICK, 1)
        m.write_u8(b + ATTACKED, 0)
    # Keep the target non-collectible and non-damageable while the real attack
    # is being established.  The target is armed only between complete frames.
    prepare_item(m, 0, 136, CHAR_HP_PER_HIT)
    m.write_u8(ITEM + HP, 0); m.write_u8(ITEM + SELECTED, 0)
    m.write_u8(ITEM + HITSTUN, 0); m.write_u8(ITEM + VARIANT, 0)
    m.write_u8(ACTOR_INV + 2, 0)
    neutral_joint(m)
    m.hold_input(m.BTN_Y, port=owner)
    attack_ready = False
    try:
        for _ in range(8):
            run_frames_exact(m, 1)
            if (u8(m, attacker + SELECTED) == 2 and
                    u8(m, attacker + ATTACKED) == 0 and
                    u8(m, attacker + VARIANT) != GET_VARIANT):
                attack_ready = True
                break
        if not attack_ready:
            return {'owner': owner, 'kind': kind, 'tooling_limited': True,
                    'attack_state': {'selected': u8(m, attacker + SELECTED),
                                     'hit_applied': u8(m, attacker + ATTACKED),
                                     'variant': u8(m, attacker + VARIANT)},
                    'reason': 'no between-frame active attack boundary within 8 frames'}

        # Keep the target disabled until the owner's real attack hit window.
        # The sampled selected=2 state is established at a frame boundary;
        # P1 and P2 reach their collision service at different offsets in the
        # current production dispatch, so use a bounded owner-local settle
        # window while the target remains HP=0/PickupType=NONE.
        run_frames_exact(m, 3 if owner == 1 else 1)

        # This is a between-frame write: no CPU instruction is paused and no
        # hook callback mutates the invocation under test.
        m.write_u8(ITEM + INPUT, PROP); m.write_u8(ITEM + HP, CHAR_HP_PER_HIT)
        m.write_u8(ITEM + PICKUP, kind); m.write_u8(ITEM_IDX, 0)
        m.write_u8(ACTOR_INV + 2, 0); m.write_u16(ITEM + POS_X, 136)
        m.write_u8(ITEM + POS_Y, 150); m.write_u8(ITEM + SELECTED, 0)
        m.write_u8(ITEM + HITSTUN, 0); m.write_u8(ITEM + VARIANT, 0)
        hooks = [m.add_exec_hook(symbol(name)) for name in (
            'Character_HitApply__ScoreAndFinish',
            'Character_HitApply__RevealOrPickup',
            'Character_HitApply__RevealOrPickup__e2_instant',
            'Character_Pickup_CheckOverlap__vs2_dy_ok')]
        run_frames_exact(m, 1)
        first_frame = {'p1_score': u16(m, GS), 'p2_score': u16(m, P2S),
                       'item': u8(m, ITEM + PICKUP), 'item_hp': u8(m, ITEM + HP)}
        # The attack-selection state is established at a frame boundary; the
        # next complete production service frame owns the collision pass.
        # Keep the fixture mutation-free and observe that frame synchronously.
        run_frames_exact(m, 1)
        events = m.drain_notifications()
        names = {symbol(name): name for name in (
            'Character_HitApply__ScoreAndFinish',
            'Character_HitApply__RevealOrPickup',
            'Character_HitApply__RevealOrPickup__e2_instant',
            'Character_Pickup_CheckOverlap__vs2_dy_ok')}
        observed = [names.get(e.get('params', {}).get('address'),
                              e.get('params', {}).get('address'))
                    for e in events if e.get('method') == 'mesen/hookFired']
        transaction = {'p1_score': u16(m, GS), 'p2_score': u16(m, P2S),
                 'item': u8(m, ITEM + PICKUP),
                 'owner_final': u8(m, pasm_constant('G13_PickupForP2')),
                 'item_hp': u8(m, ITEM + HP), 'observed_hooks': observed}
        run_frames_exact(m, 1)
        after = {'p1_score': u16(m, GS), 'p2_score': u16(m, P2S),
                 'item': u8(m, ITEM + PICKUP)}
    finally:
        m.release_input(port=owner)
        for hook in locals().get('hooks', []):
            m.remove_hook(hook)
    expected = HIT_SCORE + (SCORE_MONEY if kind == PT_MONEY else 0)
    return {'owner': owner, 'kind': kind, 'tooling_limited': False,
            'p1_score': transaction['p1_score'], 'p2_score': transaction['p2_score'],
            'item': transaction['item'], 'owner_final': transaction['owner_final'],
            'item_hp': transaction['item_hp'], 'observed_hooks': transaction['observed_hooks'],
            'first_frame': first_frame, 'after': after, 'expected_total': expected,
            'expected_attacker_score': expected}

def packed_alive_instant_candidates():
    """Find current packed props that would make the instant branch applicable.

    Spawn-table records are the content-level source of truth here.  For a
    prop, record-kind bits 5-7 carry PickupType and byte +8 carries the
    contained-item roster index.  A nonzero pickup with index zero is the
    dual-eligible state that must not silently become untested content.
    """
    candidates = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'out', 'spawn_*', 'spawn_table.bin'))):
        with open(path, 'rb') as f:
            data = f.read()
        for offset in range(0, len(data), 10):
            if offset + 10 > len(data):
                continue
            record_kind = data[offset + 6]
            pickup_type = (record_kind >> 5) & 0x07
            # Current packed standalone items use object roster 0 (no
            # converted identity) or the known 1up identity 16.  They are
            # already collectibles, not wrapped breakable props.  A
            # converted breakable has its own object roster identity; if a
            # future one carries a nonzero pickup with no contained-item
            # roster, fail explicitly and require instant-path review.
            object_roster_idx = data[offset + 9]
            if (record_kind & 0x07) == 1 and pickup_type != 0 and data[offset + 8] == 0 and object_roster_idx not in (0, roster_index('1up')):
                candidates.append({'table': os.path.relpath(path, ROOT),
                                   'record': offset // 10,
                                   'pickup_type': pickup_type,
                                   'item_roster_idx': data[offset + 8],
                                   'object_roster_idx': object_roster_idx,
                                   'spawn_hp': data[offset + 7]})
    return candidates

def real_new_game_reset(m, reporter):
    """Exercise TITLE -> CHARSELECT -> NewGameReset, without calling it."""
    startup.cold_to_title(m, reporter)
    startup.title_to_charselect(m, two_player=True)
    # Source-normal 2P selection requires both independent readiness edges;
    # confirm the default P2 and P1 here before observing NewGameReset.
    exact_input_edge(m, m.BTN_START, 1, port=1)
    exact_input_edge(m, 0, 1, port=1)
    exact_input_edge(m, m.BTN_START, 1, port=0)
    # Dirty session state immediately before the production reset choke point.
    m.write_u16(GS, 12345); m.write_u16(P2S, 23456); m.write_u16(LIVES, 3); m.write_u16(P2L, 7)
    exact_input_edge(m, m.BTN_START, 1, port=0); clear_inputs(m)
    assert poll_until(m, lambda mm: u16(mm, GAME_STATE) == GAME_STATE_PLAYING, 240)
    reset_boundary = {'score': u16(m, GS), 'p2_score': u16(m, P2S),
                      'lives': u16(m, LIVES), 'p2_lives': u16(m, P2L),
                      'stage': u8(m, pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')),
                      'game_state': u16(m, GAME_STATE)}
    run_frames_exact(m, 1)
    first_frame = {'score': u16(m, GS), 'p2_score': u16(m, P2S),
            'lives': u16(m, LIVES), 'p2_lives': u16(m, P2L),
            'stage': u8(m, pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex'))}
    return {'reset_boundary': reset_boundary, 'first_frame': first_frame,
            'score': u16(m, GS), 'p2_score': u16(m, P2S), 'lives': u16(m, LIVES),
            'p2_lives': u16(m, P2L), 'mode': u8(m, MODE), 'p1_hp': u8(m, P1 + HP),
            'p2_hp': u8(m, P2 + HP), 'p2_input': u8(m, P2 + INPUT),
            'p2_roster': u8(m, P2 + pasm_constant('CHAR_ROSTER_INDEX')),
            'stage': u8(m, pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex'))}

def main():
    r = Reporter('G13-SCORE-PICKUP', kind='GATE'); results = {}
    with open_session(__file__) as m:
        reset = real_new_game_reset(m, r); results['real_new_game_reset'] = reset
        rb = reset['reset_boundary']
        r.check('real NewGameReset boundary clears both scores/lives',
                rb['score'] == 0 and rb['p2_score'] == 0 and
                rb['lives'] == pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START') and
                rb['p2_lives'] == pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START'))
        r.check('real reset preserves active P2 ownership',
                reset['mode'] == 1 and reset['p2_input'] == 1 and
                reset['p2_roster'] == BOR_DEFAULT_P2 and reset['stage'] == 0 and
                reset['p1_hp'] == HP_MAX and reset['p2_hp'] == HP_MAX)
    def fresh(owner, kind):
        with open_session(__file__) as m:
            setup(m); return collect(m, owner, kind)
    with open_session(__file__) as m:
        setup(m); p2_get = u8(m, P2 + GET_FCOUNT); b,a = collect(m, 1, PT_APPLE)
    results['p2_apple'] = {'before':b,'after':a,'get_fcount':p2_get}
    r.check('P2 apple heals only P2 and consumes item', a['p2_hp'] == 29 and a['p1_hp'] == 64 and a['item'] == 0)
    r.check('P2 LEO enters its own GET pose', p2_get != 0 and a['p2_selected'] == 2 and a['p2_variant'] == GET_VARIANT)
    b,a = fresh(0, PT_APPLE); results['p1_apple']={'before':b,'after':a}
    r.check('P1 apple heals only P1 and leaves P2 action untouched', a['p1_hp'] == 29 and a['p2_hp'] == 64)
    r.check('pickup owner selector clears after each transaction', a['owner'] == 0)
    for owner, kind, amount, label in ((0,PT_MONEY,SCORE_MONEY,'p1_money'),(1,PT_MONEY,SCORE_MONEY,'p2_money'),
                                            (0,PT_GOLD,SCORE_GOLD,'p1_gold'),(1,PT_GOLD,SCORE_GOLD,'p2_gold'),
                                            (0,PT_ONEUP,1,'p1_oneup'),(1,PT_ONEUP,1,'p2_oneup')):
        b,a=fresh(owner,kind); results[label]={'before':b,'after':a}
        if kind in (PT_MONEY, PT_GOLD): r.check(label+' score owner', (a['score']-b['score'],a['p2_score']-b['p2_score']) == ((amount,0) if owner==0 else (0,amount)))
        else: r.check(label+' life owner', (a['lives']-b['lives'],a['p2_lives']-b['p2_lives']) == ((1,0) if owner==0 else (0,1)))
    with open_session(__file__) as m:
        setup(m)
        first, second = true_tie(m)
        results['tie'] = {'first': first, 'second': second}
        r.check('true simultaneous overlap has one P1-first reward',
                first['score'] == SCORE_MONEY and first['p2_score'] == 0 and
                first['item_type'] == 0 and first['item_hp'] == 0)
        r.check('true tie does not double reward on P2 pass',
                second['score'] == SCORE_MONEY and second['p2_score'] == 0)
        r.check('true tie owner selector clears', first['owner'] == 0)
    for owner, label in ((0, 'p1'), (1, 'p2')):
        with open_session(__file__) as m:
            setup(m)
            m.write_u16(GS if owner == 0 else P2S, 49999)
            m.write_u16(LIVES if owner == 0 else P2L, 7)
            b,a = collect(m, owner, PT_MONEY)
            results[label + '_threshold'] = {'before':b,'after':a}
            r.check(label + ' money crosses source 50000 threshold exactly once',
                    (a['lives'] == (8 if owner == 0 else 3) and
                     a['p2_lives'] == (8 if owner == 1 else 3)))
    with open_session(__file__) as m:
        setup(m); put32(m, P2S, 999999990); b,a=collect(m,1,PT_MONEY)
        results['p2_saturation']={'before':b,'after':a}
        r.check('P2 money reaches source score cap without wrap',
                u32(m, P2S) == 999999999)
    for hp, expected, label in ((10, HP_MAX, 'p2_meat_10'), (HP_MAX - 5, HP_MAX, 'p2_meat_59')):
        with open_session(__file__) as m:
            setup(m); b, a = p2_meat(m, hp)
            results[label] = {'before': b, 'after': a}
            r.check(label + ' heals P2 and clamps at max',
                    a['p2_hp'] == expected and a['p1_hp'] == HP_MAX)
    for owner, label in ((1, 'p2_instant'), (0, 'p1_instant')):
        with open_session(__file__) as m:
            setup(m)
            none = instant_break(m, owner, 0)
            results[label + '_none'] = none
            r.check(label + ' NONE lethal control awards source hit score',
                    not none['tooling_limited'] and
                    (none['p2_score'] if owner else none['p1_score']) == HIT_SCORE and
                    (none['p1_score'] if owner else none['p2_score']) == 0)
    instant_candidates = packed_alive_instant_candidates()
    results['synthetic_instant_money'] = {
        'status': 'NOT_APPLICABLE_UNMEASURED',
        'reason': ('Current packed content has no organically reachable alive '
                   'pickup PROP with PickupType != 0 and ItemRosterIdx == 0; '
                   'manual construction is dual-eligible for instant and '
                   'passive pickup.'),
        'owners': ['P1', 'P2'],
        'content_guard_candidates': instant_candidates}
    r.check('synthetic instant-reward state remains absent from packed content',
            not instant_candidates)
    with open_session(__file__) as m:
        setup(m); results['owner_leak_p2_then_p1'] = owner_leak(m)
        x = results['owner_leak_p2_then_p1']
        r.check('owner leak P2 then P1 remains isolated',
                x['first']['after']['p2_score'] == SCORE_MONEY and
                x['second']['after']['score'] == SCORE_GOLD and
                x['owner_final'] == 0)
    with open_session(__file__) as m:
        setup(m)
        b1, a1 = collect(m, 0, PT_ONEUP, slot=2)
        clear_inputs(m); run_frames_exact(m, 2)
        b2, a2 = collect(m, 1, PT_APPLE, slot=3, service_frames=3)
        results['owner_leak_p1_then_p2'] = {'first': {'before': b1, 'after': a1},
                                            'second': {'before': b2, 'after': a2},
                                            'owner_final': u8(m, pasm_constant('G13_PickupForP2'))}
        x = results['owner_leak_p1_then_p2']
        r.check('owner leak P1 then P2 remains isolated',
                x['first']['after']['lives'] == x['first']['before']['lives'] + 1 and
                x['second']['after']['p2_hp'] == 29 and x['owner_final'] == 0)
    with open(os.path.join(os.path.dirname(__file__),'..','..','out','g13_score_pickup.json'),'w') as f: json.dump(results,f,indent=2); f.write('\n')
    return r.finish()
if __name__ == '__main__': raise SystemExit(main())
