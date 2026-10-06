"""Pinned playerkeys masks and an explicitly owned source-tick snapshot ABI.

The world owner supplies BOR key flags, not SNES button bits. Controller
mapping and the native owner remain separate capabilities. Positions in the
snapshot are player slots, never actor IDs. No model-name policy exists.
"""
import json
from pathlib import Path
import struct

AUTHORITY=Path(__file__).with_name('authority')/'4086_playerkeys.json'
MAGIC=0xb4c2
ADDRESS=0x7ff8a0
MAX_PLAYERS=4
HEADER=8
STRIDE=12
FIRST_UNUSED=ADDRESS+HEADER+MAX_PLAYERS*STRIDE


def authority():
    data=json.loads(AUTHORITY.read_text())
    if data['engine_commit']!='af23dc9c2316bb7853bb266ccf40986aa9765aeb':
        raise ValueError('SOURCE_INPUT_UNPINNED_AUTHORITY')
    if [r['selector'] for r in data['keys']]!=list(range(14)):
        raise ValueError('SOURCE_INPUT_SELECTOR_AUTHORITY')
    return data


def snapshot(rows,tick):
    if not 1<=len(rows)<=MAX_PLAYERS or not 0<=tick<=0xffffffff:
        raise ValueError('SOURCE_INPUT_SNAPSHOT_DOMAIN')
    if any(len(r)!=3 or any(not isinstance(v,int) or not 0<=v<=0xffffffff for v in r) for r in rows):
        raise ValueError('SOURCE_INPUT_MASK_DOMAIN')
    return struct.pack('<HHI',MAGIC,len(rows),tick)+b''.join(struct.pack('<III',*r) for r in rows)


def query(rows,index,mode,*selectors):
    """Source mask-result oracle, after ScriptVariant integer conversion.

    The pinned engine does not bounds-check player[index]. The native target
    must reject that undefined domain explicitly. Multiple requested keys
    stop at the first absent mask and otherwise return the last mask value.
    """
    if not isinstance(index,int) or not 0<=index<len(rows):
        raise ValueError('SOURCE_INPUT_PLAYER_INDEX_UNDEFINED')
    if not selectors:raise ValueError('SOURCE_INPUT_KEY_REQUIRED')
    keys=rows[index][mode if mode in (1,2) else 0]
    mapping=authority()['keys']
    for selector in selectors:
        row=next((r for r in mapping if (r['name']==selector.lower() if isinstance(selector,str)
                                        else isinstance(selector,int) and r['selector']==selector)),None)
        value=(keys&row['mask']) if row is not None else 0
        if not value:break
    return value


def emit_names(label='Vm_SourceInputNames'):
    lines=[label+':']
    for row in authority()['keys']:
        raw=row['name'].encode('ascii')
        if len(raw)>13 or row['mask']>65535:raise ValueError('SOURCE_INPUT_NATIVE_NAME_CAPACITY')
        data=bytes([len(raw)])+raw+bytes(13-len(raw))+struct.pack('<H',row['mask'])
        lines.append('    .db '+','.join('$%02X'%v for v in data))
    return '\n'.join(lines)+'\n'
