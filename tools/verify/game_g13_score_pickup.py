#!/usr/bin/env python3
"""Focused G13 score, pickup-owner, GET-pose, and fresh-reset gate.

The fixture changes only legal item metadata/geometry and session-owned
preconditions.  Collection, reward dispatch, score saturation/life extension,
and P2 GET selection remain production code.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, exact_input_edge, open_session, pasm_constant,
                      pasm_constant_in, read_block, run_frames_exact)
from game_g13_two_player_input import clear_inputs, select_two_player

ZP = pasm_constant('CHAR_ZP_LEN')
P1 = 0x7E0A00; P2 = P1 + ZP; ITEM = P1 + 2 * ZP
POS_X = pasm_constant('CHAR_POS_X'); POS_Y = pasm_constant('CHAR_POS_Y')
HP = pasm_constant('CHAR_HP'); HP_MAX = pasm_constant('CHAR_HP_MAX')
SELECTED = pasm_constant('CHAR_SELECTED'); INPUT = pasm_constant('CHAR_INPUT_DRIVEN')
PICKUP = pasm_constant('CHAR_PICKUP_TYPE'); VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
GET_FCOUNT = pasm_constant('CHAR_GET_FCOUNT')
PROP = pasm_constant('CHAR_INPUT_DRIVEN_PROP')
PT_APPLE = pasm_constant('PICKUP_TYPE_APPLE'); PT_MEAT = pasm_constant('PICKUP_TYPE_MEAT')
PT_MONEY = pasm_constant('PICKUP_TYPE_MONEY'); PT_ONEUP = pasm_constant('PICKUP_TYPE_ONEUP')
PT_GOLD = pasm_constant('PICKUP_TYPE_GOLD'); GET_VARIANT = pasm_constant('GET_MOVE_VARIANT')
HEAL_APPLE = pasm_constant('PICKUP_HEAL_APPLE'); HEAL_MEAT = pasm_constant('PICKUP_HEAL_MEAT')
SCORE_MONEY = pasm_constant('PICKUP_SCORE_MONEY'); SCORE_GOLD = pasm_constant('PICKUP_SCORE_GOLD')
EXTEND = pasm_constant('EXTEND_LIFE_SCORE')
GS = pasm_constant_in('src/core/game_state.pasm', 'Game_Score')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
P2S = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Score')
P2L = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
MODE = pasm_constant('G13_TwoPlayerEnabled')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
TITLE_STEP = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
ITEM_IDX = pasm_constant_in('src/core/spawn.pasm', 'Entity2_ItemRosterIdx')

def u8(m, a): return read_block(m, a, 32)[0]
def u16(m, a):
    b = read_block(m, a, 32); return b[0] | b[1] << 8

def setup(m):
    m.reset_emulator(); run_frames_exact(m, 180); clear_inputs(m)
    # Use the real fixed-session production entry.  The title boundary is
    # arranged as in the authoritative session verifier; P2 is loaded as
    # fixed LEO by production, rather than by writing roster/jump fields.
    m.write_u16(GAME_STATE, GAME_STATE_TITLE)
    m.write_u16(GAME_STATE + 2, GAME_STATE_TITLE)
    m.write_u8(TITLE_STEP, 2)
    exact_input_edge(m, m.BTN_START, 1, port=1)
    run_frames_exact(m, 2)
    m.write_u16(GAME_STATE, 0); m.write_u16(GAME_STATE + 2, 0)
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    for b, x in ((P1, 120), (P2, 180)):
        m.write_u16(b + POS_X, x); m.write_u8(b + POS_Y, 150)
        m.write_u8(b + HP, HP_MAX); m.write_u8(b + SELECTED, 0)
    for i in range(3, 6):
        b = P1 + i * ZP; m.write_u8(b + HP, 0); m.write_u8(b + INPUT, 2)
    m.write_u8(ITEM + INPUT, PROP); m.write_u8(ITEM + HP, 1)
    m.write_u8(ITEM_IDX, 0); m.write_u16(ITEM + POS_X, 180); m.write_u8(ITEM + POS_Y, 150)
    clear_inputs(m)
    print('SETUP', {'mode': u8(m, MODE), 'p2_input': u8(m, P2 + INPUT),
                    'p2_hp': u8(m, P2 + HP), 'p2_get': u8(m, P2 + GET_FCOUNT),
                    'game_state': u8(m, GAME_STATE), 'item_input': u8(m, ITEM + INPUT)}, flush=True)

def collect(m, owner, kind, score=0, lives=0):
    b = P1 if owner == 0 else P2
    m.write_u16(b + POS_X, 100); m.write_u8(b + POS_Y, 150)
    m.write_u8(b + SELECTED, 0); m.write_u8(b + HP, 10 if kind in (PT_APPLE, PT_MEAT) else HP_MAX)
    for player in (P1, P2):
        m.write_u8(player + SELECTED, 0)
        m.write_u8(player + VARIANT, 0)
        m.write_u8(player + pasm_constant('CHAR_HIT_STUN'), 0)
        m.write_u8(player + pasm_constant('CHAR_FRAME_INDEX'), 0xFF)
        m.write_u8(player + pasm_constant('CHAR_TICK_COUNTER'), 1)
    m.write_u8(ITEM + INPUT, PROP); m.write_u8(ITEM + HP, 1); m.write_u8(ITEM + PICKUP, kind)
    m.write_u8(ITEM_IDX, 0); m.write_u16(ITEM + POS_X, 100); m.write_u8(ITEM + POS_Y, 150)
    # Keep the non-collector outside the hitbox without relying on a large
    # out-of-viewport coordinate that the production tether may clamp back
    # into the item.  The collector remains at the item, the partner is at
    # the opposite side of the bounded viewport.
    m.write_u16((P2 if owner == 0 else P1) + POS_X, 400)
    before = {'p1_hp':u8(m,P1+HP),'p2_hp':u8(m,P2+HP),'score':u16(m,GS),'p2_score':u16(m,P2S),
              'lives':u8(m,LIVES),'p2_lives':u8(m,P2L),'item':u8(m,ITEM+PICKUP)}
    before.update({'mode':u8(m,MODE),'p2_input':u8(m,P2+INPUT),'p2_x':u16(m,P2+POS_X),
                   'p1_x':u16(m,P1+POS_X),'item_x':u16(m,ITEM+POS_X),
                   'item_input':u8(m,ITEM+INPUT)})
    hp1_hook = m.add_write_hook(P1 + HP, P1 + HP)
    hp2_hook = m.add_write_hook(P2 + HP, P2 + HP)
    owner_hook = m.add_write_hook(pasm_constant('G13_PickupForP2'), pasm_constant('G13_PickupForP2'))
    run_frames_exact(m, 1)
    events = m.drain_notifications()
    after = {'p1_hp':u8(m,P1+HP),'p2_hp':u8(m,P2+HP),'score':u16(m,GS),'p2_score':u16(m,P2S),
             'lives':u8(m,LIVES),'p2_lives':u8(m,P2L),'item':u8(m,ITEM+PICKUP),
             'p1_selected':u8(m,P1+SELECTED),'p2_selected':u8(m,P2+SELECTED),
             'p1_variant':u8(m,P1+VARIANT),'p2_variant':u8(m,P2+VARIANT),
             'owner':u8(m,pasm_constant('G13_PickupForP2'))}
    after['mode'] = u8(m, MODE)
    after['writes'] = [{'address':e.get('params',{}).get('address'), 'value':e.get('params',{}).get('value'), 'handle':e.get('params',{}).get('handle')} for e in events if e.get('params',{}).get('handle') in (hp1_hook,hp2_hook,owner_hook)]
    for h in (hp1_hook, hp2_hook, owner_hook): m.remove_hook(h)
    return before, after

def main():
    r = Reporter('G13-SCORE-PICKUP', kind='GATE'); results = {}
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
        setup(m); b,a=collect(m,0,PT_MONEY); m.write_u16(P2+POS_X,100); run_frames_exact(m,1)
        results['tie']={'before':b,'after':a,'final_score':u16(m,GS),'final_p2_score':u16(m,P2S)}
        r.check('same-frame pickup cannot double reward', u8(m,ITEM+PICKUP)==0)
    for owner, label in ((0, 'p1'), (1, 'p2')):
        with open_session(__file__) as m:
            setup(m)
            m.write_u16(GS if owner == 0 else P2S, EXTEND - 500)
            m.write_u8(LIVES if owner == 0 else P2L, 7)
            b,a = collect(m, owner, PT_MONEY)
            results[label + '_threshold'] = {'before':b,'after':a}
            r.check(label + ' money threshold adds exactly one life',
                    (a['lives'] == (8 if owner == 0 else 20) and
                     a['p2_lives'] == (8 if owner == 1 else 20)))
    with open_session(__file__) as m:
        setup(m); m.write_u16(P2S, 0xFFFA); b,a=collect(m,1,PT_MONEY)
        results['p2_saturation']={'before':b,'after':a}
        r.check('P2 money saturates score without wrap', a['p2_score'] == 0xFFFF)
    with open(os.path.join(os.path.dirname(__file__),'..','..','out','g13_score_pickup.json'),'w') as f: json.dump(results,f,indent=2); f.write('\n')
    return r.finish()
if __name__ == '__main__': raise SystemExit(main())
