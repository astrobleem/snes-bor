"""Pinned inputrefresh history and match_combo; separate from player_think.

All key/timestamp operations preserve uint32 source semantics. Input refresh
occurs once per outer control refresh, never once per catch-up world tick.
"""
import copy
import struct
from source_script_input import authority

MAX_PLAYERS=4
MAX_SPECIAL_INPUTS=27
GAME_SPEED=200
FORWARD=0x40000000
BACKWARD=0x80000000
ROW_BYTES=256
KEYS=216
NEWKEYS=220
PLAYKEYS=224
RELEASEKEYS=228
COMBOSTEP=232
MOVETIME=236
PRESENT=240
DIRECTION=244
TOKEN=248


def empty_player():
    return dict(combokey=[0]*MAX_SPECIAL_INPUTS,inputtime=[0]*MAX_SPECIAL_INPUTS,
                keys=0,newkeys=0,playkeys=0,releasekeys=0,combostep=0,
                movetime=0,present=0,direction=0,token=0)


def validate(player):
    for name in ('combokey','inputtime'):
        if len(player[name])!=MAX_SPECIAL_INPUTS or any(not isinstance(n,int)or not 0<=n<=0xffffffff for n in player[name]):
            raise ValueError('SOURCE_INPUT_HISTORY_ARRAY')
    if not isinstance(player['combostep'],int)or not 0<=player['combostep']<MAX_SPECIAL_INPUTS:
        raise ValueError('SOURCE_INPUT_HISTORY_STEP')
    for name in ('keys','newkeys','playkeys','releasekeys','movetime','present','direction','token'):
        if not isinstance(player[name],int)or not 0<=player[name]<=0xffffffff:
            raise ValueError('SOURCE_INPUT_HISTORY_UINT32:'+name)


def refresh(players,controls,time):
    if len(players)!=MAX_PLAYERS or len(controls)!=MAX_PLAYERS or not isinstance(time,int)or not 0<=time<=0xffffffff:
        raise ValueError('SOURCE_INPUT_HISTORY_REFRESH_DOMAIN')
    result=[copy.deepcopy(player)for player in players]
    masks={r['name']:r['mask']for r in authority()['keys']}
    bothkeys=bothnewkeys=0
    for p,(held,new) in zip(result,controls):
        validate(p)
        if any(not isinstance(n,int)or not 0<=n<=0xffffffff for n in (held,new)):
            raise ValueError('SOURCE_INPUT_HISTORY_CONTROL_UINT32')
        p['releasekeys']=((held|p['keys'])-held)&0xffffffff
        p['keys']=held;p['newkeys']=new
        p['playkeys']=(p['playkeys']|new)&held
        if p['present']and p['movetime']<time:
            p['combokey']=[0]*MAX_SPECIAL_INPUTS
            p['inputtime']=[0]*MAX_SPECIAL_INPUTS
            p['combostep']=0
        if new:
            k=new
            if p['present']:
                p['movetime']=(time+GAME_SPEED//4)&0xffffffff
                if k&masks['moveleft']:k|=BACKWARD if p['direction']else FORWARD
                elif k&masks['moveright']:k|=FORWARD if p['direction']else BACKWARD
            p['inputtime'][p['combostep']]=time
            p['combokey'][p['combostep']]=k
            p['combostep']=(p['combostep']+1)%MAX_SPECIAL_INPUTS
        bothkeys|=held;bothnewkeys|=new
    return result,bothkeys,bothnewkeys


def match_combo(sequence,player):
    validate(player)
    if len(sequence)>MAX_SPECIAL_INPUTS or any(not isinstance(n,int)or not 0<=n<=0xffffffff for n in sequence):
        raise ValueError('SOURCE_COMBO_SEQUENCE_DOMAIN')
    for j in range(len(sequence)):
        step=(player['combostep']-1-j+MAX_SPECIAL_INPUTS)%MAX_SPECIAL_INPUTS
        if not(sequence[len(sequence)-1-j]&player['combokey'][step]):return 0
    return 1


def pack_player(player):
    validate(player)
    return struct.pack('<64I',*player['inputtime'],*player['combokey'],
                       *(player[k]for k in ('keys','newkeys','playkeys','releasekeys',
                                           'combostep','movetime','present','direction','token')),0)


def unpack_player(raw):
    if len(raw)!=ROW_BYTES:raise ValueError('SOURCE_INPUT_HISTORY_ROW_BYTES')
    words=struct.unpack('<64I',raw)
    if words[-1]:raise ValueError('SOURCE_INPUT_HISTORY_ROW_RESERVED')
    player=dict(inputtime=list(words[:27]),combokey=list(words[27:54]))
    player.update(zip(('keys','newkeys','playkeys','releasekeys','combostep',
                       'movetime','present','direction','token'),words[54:63]))
    validate(player);return player
