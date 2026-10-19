"""Checked check_move operator joined to real flat callbacks and contact state.

The static production operator is retained. This emitted capability admits
non-null common/player callbacks; linked grabwalking still requires an owner.
"""
from pathlib import Path
import re
from source_move_contact_layout import layout
from source_foreign_state_layout import layout as arena
from source_hit_state_layout import layout as hits
from source_trymove_flat_native import emit as flat
from source_move_contact_native import emit as movement
from source_hit_state_native import emit as identities


def emit(req,plan,sy,*,flat_work=None,include_identities=True):
    if plan.get('storage_profile')=='RETIRED_SCENE_VIDEO_STAGING':
        from source_move_contact_layout import rehost
        from source_hit_state_layout import rehost as hit_rehost
        expected=rehost(plan['entities'],plan['base']);hp=hit_rehost(plan['entities'])
    else:expected=layout(plan['entities']);hp=hits(plan['entities'])
    if plan!=expected:raise ValueError('CHECK_MOVE_CALLBACK_PLAN')
    region=next(r for r in arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions'] if r['name']=='attack_chain_controls')
    w=region['address'] if flat_work is None else flat_work
    if type(w) is not int or w&1 or not 0<=w<=0x1000000-96:raise ValueError('CHECK_MOVE_CALLBACK_WORK')
    if flat_work is not None:
        for base,size in ((plan['base'],plan['bytes']),(plan['controls'],64),(hp['base'],hp['bytes']),(hp['controls'],64)):
            if w<base+size and base<w+96:raise ValueError('CHECK_MOVE_CALLBACK_WORK_OVERLAP')
    m=plan['controls'];h=hp['controls']
    source=Path('src/core/vm/vm_source_check_move.pasm').read_text(encoding='cp1252')
    code=source[source.index('SourceCheckMove4086_Execute:'):]
    old=' phx\n phy\n lda.l SourceCheckMove4086_Ready'
    if code.count(old)!=1:raise ValueError('CHECK_MOVE_CALLBACK_ENTRY_AUTHORITY')
    code=code.replace(old,f' phx\n phy\n lda #0\n sta.l {w}+28\n lda.l SourceCheckMove4086_Ready')
    old=' lda.l $439000+SOURCE_LIFECYCLE_TRYMOVE,x\n ora.l $439002+SOURCE_LIFECYCLE_TRYMOVE,x\n beq SourceCheckMove4086_Guard28\n jmp SourceCheckMove4086_Bad'
    if code.count(old)!=1:raise ValueError('CHECK_MOVE_CALLBACK_ABI_AUTHORITY')
    code=code.replace(old,old.replace(' jmp SourceCheckMove4086_Bad',
        ' jsl CallbackMove_Run\n bcc SourceCheckMove4086_CallbackReady\n jmp SourceCheckMove4086_Bad\nSourceCheckMove4086_CallbackReady:\n.a16\n.i16'))
    labels=set(re.findall(r'^(SourceCheckMove4086_\w+):',code,re.M))
    for n in sorted(labels,key=len,reverse=True):code=re.sub(r'\b'+n+r'\b',n.replace('SourceCheckMove4086_','CallbackCheckMove_'),code)
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('CallbackMove_'+n+':\n.a16\n.i16')
    def fault(op):
        nonlocal serial
        serial+=1;n='CallbackMove_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {n}\n jmp CallbackMove_Bad\n{n}:\n.a16\n.i16')
    def generation():put(f' lda.l {w}+12\n tax\n lda.l {w}+14\n tay')
    label('Run');put(' php\n rep #$39\n pha\n phx\n phy')
    put(f' lda.l {sy["SourceWorldTick4086_Slot"]}\n sta.l {m}+4\n sta.l {h}+4')
    generation();put(' jsl MoveContact_Read');fault('bcs')
    # Linked grabwalking requires real recursive/link movement, never a null no-op.
    put(f' lda.l {sy["SourceWorldTick4086_Slot"]}\n asl a\n asl a\n asl a\n asl a\n asl a\n sta.l {w}+32\n asl a\n clc\n adc.l {w}+32\n tax\n lda.l $40C050,x\n ora.l $40C052,x\n beq CallbackMove_NotLinked\n lda.l {m}+28\n ora.l {m}+30');fault('bne')
    label('NotLinked');put(f' lda.l {sy["SourceCheckMove4086_View"]}\n tax')
    for field,out in ((52,20),(60,24)):
        for off in (0,2):put(f' lda.l $414000+{field+off},x\n sta.l {w}+{out+off}')
    put(f' lda #0\n sta.l {w}+2');generation();put(' jsl FlatTrymove_Execute');fault('bcs')
    put(f' lda.l {w}+4\n cmp #1\n beq CallbackMove_ResetBlocked\n lda.l {sy["SourceWorldTick4086_Slot"]}\n asl a\n asl a\n asl a\n asl a\n asl a\n tax\n lda.l $43EB00,x\n ora.l $43EB02,x\n beq CallbackMove_ResetBlocked')
    put(f' lda.l {sy["VmSourceWorld_Time"]}\n and #1\n clc\n adc.l {m}+24\n sta.l {m}+24\n lda.l {m}+26\n adc #0\n sta.l {m}+26\n jmp CallbackMove_WriteBlocked')
    label('ResetBlocked');put(f' lda #0\n sta.l {m}+24\n sta.l {m}+26')
    label('WriteBlocked');generation();put(' jsl MoveContact_Write');fault('bcs')
    # Capture actual displacement before the retained operator publishes its timer/mark.
    put(f' lda.l {sy["SourceCheckMove4086_Aux"]}\n tay\n lda.l {sy["SourceCheckMove4086_View"]}\n tax')
    for field,old in ((52,20),(60,24)):
        put(f' sec\n lda.l $414000+{field},x\n sbc.l {w}+{old}\n sta.l {w}+{old+16}\n lda.l $414000+{field+2},x\n sbc.l {w}+{old+2}\n sta.l {w}+{old+18}')
    put(f' lda.l {sy["SourceCheckMove4086_Aux"]}\n tax')
    for out,dp in ((0,36),(4,40)):
        for off in (0,2):put(f' lda.l {w}+{dp+off}\n sta.l $41F500+{out+off},x')
    put(' lda #0')
    for n in ('X','Z'):
        for off in (0,2):put(f' sta.l {sy["SourceCheckMove4086_"+n]}+{off}')
    put(f' lda #1\n sta.l {w}+28\n ply\n plx\n pla\n plp\n clc\n rtl')
    label('Bad');put(' ply\n plx\n pla\n plp\n sec\n rtl')
    code+='\n'+'\n'.join(lines)+'\n'
    for n in sorted(sy,key=len,reverse=True):
        if n.startswith(('Source','VmSourceWorld_','SOURCE_','BOR_')):code=re.sub(r'\b'+n+r'\b',str(sy[n]),code)
    # Shared helpers retain source addresses; only this capability's local labels move.
    return code+(identities(hp,sy) if include_identities else '')+movement(plan,sy)+flat(req,w,sy)
