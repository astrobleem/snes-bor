"""Private native join for retiring every legacy water overlay entry point.

The existing ForeignWork lease must hold before the arena is overwritten.
The source water body remains the authority for the ordinary opt-out path.
"""
import re
from pathlib import Path

ENTRIES=('Reset','Begin','OamBegin','ApplyOamY','End','Nmi','ClearGuard')


def emit(sy,path=Path('src/core/stage_water.pasm')):
    text=path.read_text(encoding='cp1252')
    names=set(re.findall(r'^(StageWater_\w+)\s*(?::|=)',text,re.M))
    for name in sorted(names,key=len,reverse=True):text=re.sub(r'\b'+name+r'\b','Foreign'+name,text)
    defined=set(re.findall(r'^(\w+)\s*(?::|=)',text,re.M))
    for name,value in sy.items():
        if name not in defined:text=re.sub(r'\b'+re.escape(name)+r'\b',str(value),text)
    for suffix in ENTRIES:
        text+=f'''\nForeignWaterGate_{suffix}:
.a16
.i16
 php
 rep #$20
 pha
 lda.l $7FF866
 cmp #$B672
 beq ForeignWaterGate_{suffix}_Retired
 lda.l {sy['SourceForeignWork_Ready']}
 cmp #$B671
 bne ForeignWaterGate_{suffix}_Ordinary
ForeignWaterGate_{suffix}_Retired:
.a16
.i16
 pla
 plp
 rtl
ForeignWaterGate_{suffix}_Ordinary:
.a16
.i16
 pla
 plp
 jml ForeignStageWater_{suffix}
'''
    return text


def transform(raw,sy):
    from m4_input_controller_native import offset
    for suffix in ENTRIES:
        at=offset(sy['StageWater_'+suffix]);target=sy['ForeignWaterGate_'+suffix]
        # Each entry begins PHP/REP and a complete five-byte instruction prefix.
        shape='08 c2 30 e2 20'if suffix=='OamBegin'else'08 c2 20 48 d8'if suffix=='ApplyOamY'else'08 c2 30 48 d8'if suffix=='Nmi'else'08 c2 30 48 da'
        if raw[at:at+5]!=bytes.fromhex(shape):raise ValueError('FOREIGN_WATER_ENTRY_SHAPE:'+suffix)
        raw[at:at+5]=b'\x5c'+target.to_bytes(3,'little')+b'\xea'
