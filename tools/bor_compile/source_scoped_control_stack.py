"""Additional caller-control snapshots below the source CHR staging boundary.

Entity state and process-wide sequences are deliberately not restored.
"""
from source_current_colourmap import layout as palette
from source_move_contact_layout import layout as movement
from source_hit_contact_layout import layout as pain
from source_hit_state_layout import layout as hit
from source_foreign_state_layout import layout as foreign
from sa1_character_conversion import reused_workspace_descriptors


def layout():
    p=palette();regions=[]
    for name,provider in [('current_palette',palette),('movement',movement),('pain',pain),('hit',hit)]:
        r=provider();regions.append(dict(name=name,address=r['controls'],bytes=64))
    f=foreign(0x7fa000,6400)
    excluded={'input_history','attack_identity_sequence'}
    for r in f['regions']:
        if not r['name'].startswith('entity_')and r['name']not in excluded:
            regions.append({k:r[k]for k in ('name','address','bytes')})
    regions.append(dict(name='world_tick',address=0x7ffaec,bytes=52))
    cursor=16
    for r in regions:r['offset']=cursor;cursor+=r['bytes']
    stride=(cursor+63)&~63;capacity=(p['controls']-0x420000-64-8*stride)&~255
    controls=0x420000+capacity;base=controls+64;end=base+8*stride
    assert end<=p['controls']
    jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
    return dict(schema='BYOR_SCOPED_CONTROL_STACK_LAYOUT_V1',controls=controls,base=base,end=end,rows=8,stride=stride,payload_bytes=cursor-16,metadata_bytes=16,bytes=end-controls,regions=regions,chr_capacity=capacity,prior_chr_capacity=p['chr_capacity'],conversion_descriptors=reused_workspace_descriptors(0x420000,capacity,jobs),excluded_persistent=[r['name']for r in f['regions']if r['name'].startswith('entity_')or r['name']in excluded],entity_palette_rows_restored=False,attack_sequence_restored=False,rng_restored=False,all_producers_must_use_reduced_capacity=True,production_memory_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def emit(plan,sy):
    if plan!=layout():raise ValueError('SCOPED_CONTROL_STACK_PLAN')
    w=plan['controls'];base=plan['base'];stride=plan['stride'];lines=[];n=0
    def put(s):lines.append(s)
    def label(s):put(s+':\n.a16\n.i16\n')
    def guard(op):
        nonlocal n
        n+=1;ok=f'ScopedControls_Guard{n}'
        put(f' {op} {ok}\n jmp ScopedControls_Bad');label(ok)
    for op in ('Save','Restore','CheckSave','CheckRestore'):
        label('ScopedControls_'+op)
        put(' php\n rep #$38\n phb\n phx\n phy\n phd\n tsc\n sec\n sbc #8\n tcs\n inc a\n tcd')
        put(f' lda #{1 if "Restore"in op else 0}\n sta $04\n lda #{1 if op.startswith("Check")else 0}\n sta $06\n jmp ScopedControls_Check')
    label('ScopedControls_Check')
    for off,v in ((0,0xb6ae),(16,base&65535),(18,0x42),(20,plan['chr_capacity']),(22,8),(24,stride)):
        put(f' lda.l {w+off}\n cmp #{v}');guard('beq')
    put(f' lda.l {sy["SourceForeignWork_Ready"]}\n cmp #$B671');guard('beq')
    put(f' lda.l {w+8}\n ora.l {w+10}');guard('bne')
    for off in (0,2):
        put(f' lda.l {w+8+off}\n cmp.l {sy["SourceForeignWork_Generation"]+off}');guard('beq')
    put(f' lda.l {w+8}\n tax\n lda.l {w+10}\n tay\n jsl {sy["SourceForeignWork_Check"]}');guard('bcc')
    put(f' lda.l {sy["SourceFrameStack4086_Depth"]}\n sta $02\n lda $04\n beq ScopedControls_SaveDepth\n lda $02');guard('bne')
    put(' cmp #9');guard('bcc');put(' dec a\n sta $02\n bra ScopedControls_Offset');label('ScopedControls_SaveDepth')
    put(' lda $02\n cmp #8');guard('bcc');label('ScopedControls_Offset')
    # Bounded repeated addition avoids a runtime allocator or multiply helper.
    put(f' lda #{base&65535}\n sta $00\n ldx $02');label('ScopedControls_OffsetLoop')
    put(' cpx #0\n beq ScopedControls_OffsetDone\n clc'+f'\n adc #{stride}\n dex\n bra ScopedControls_OffsetLoop');label('ScopedControls_OffsetDone');put(' sta $00\n tax\n lda $04\n beq ScopedControls_Free')
    for off,v in ((0,0xb6af),(2,None),(4,None),(6,None),(8,stride)):
        put(f' lda.l $420000+{off},x')
        put(' cmp $02'if off==2 else f' cmp.l {w+off+4}'if off in (4,6)else f' cmp #{v}');guard('beq')
    put(' bra ScopedControls_AdmissionDone');label('ScopedControls_Free');put(' lda.l $420000,x');guard('beq')
    label('ScopedControls_AdmissionDone');put(' lda $06\n beq ScopedControls_Copy\n jmp ScopedControls_Good');label('ScopedControls_Copy')
    put(' lda $04\n beq ScopedControls_CopySave\n jmp ScopedControls_CopyRestore')
    for op in ('Save','Restore'):
        label('ScopedControls_Copy'+op)
        for r in plan['regions']:
            put(f' lda $00\n clc\n adc #{r["offset"]}\n '+('tay'if op=='Save'else'tax')+f'\n '+('ldx'if op=='Save'else'ldy')+f' #{r["address"]&65535}\n lda #{r["bytes"]-1}\n mvn '+(f'$42,${r["address"]>>16:02X}'if op=='Save'else f'${r["address"]>>16:02X},$42'))
        put(' ldx $00')
        if op=='Save':
            put(' lda #$B6AF\n sta.l $420000,x\n lda $02\n sta.l $420002,x')
            for off in (0,2):put(f' lda.l {w+8+off}\n sta.l $420004+{off},x')
            put(f' lda #{stride}\n sta.l $420008,x')
        else:put(' lda #0\n sta.l $420000,x')
        put(' jmp ScopedControls_Good')
    for name,c in [('Good','clc'),('Bad','sec')]:
        label('ScopedControls_'+name);put(f' tdc\n clc\n adc #7\n tcs\n pld\n ply\n plx\n plb\n plp\n {c}\n rtl')
    return '\n'.join(lines)+'\n'


def emit_frame_owner(plan,sy,path):
    """Extend the actual frame owner after its admission guards, in private code."""
    text=path.read_text(encoding='cp1252')
    old='SourceFrameStack4086_';new='ScopedFrameStack4086_'
    text=text.replace(old,new)
    def hook(anchor,call,tag):
        nonlocal text
        if text.count(anchor)!=1:raise ValueError('SCOPED_FRAME_HOOK_SHAPE:'+tag)
        code=f'    jsl ScopedControls_{call}\n    bcc {new}{tag}\n    jmp {new}Bad\n{new}{tag}:\n.a16\n.i16\n'
        text=text.replace(anchor,code+anchor)
    hook('    jsl SourceSelf4086_Suspend','CheckSave','ControlSaveChecked')
    hook('    lda.l ScopedFrameStack4086_Depth\n    jsr ScopedFrameStack4086_RowOffset','Save','ControlSaved')
    hook('    jsl SourceSelf4086_CheckResume','CheckRestore','ControlRestoreChecked')
    anchor='    mvn $7F,$43\n'
    if text.count(anchor)!=1:raise ValueError('SCOPED_FRAME_RESTORE_SHAPE')
    text=text.replace(anchor,anchor+f'    jsl ScopedControls_Restore\n    bcc {new}ControlRestored\n    jmp {new}Bad\n{new}ControlRestored:\n.a16\n.i16\n')
    # External helpers and VM constants come from the linked source authority.
    import re
    defined=set(re.findall(r'^(\w+)\s*(?::|=)',text,re.M))
    for name,value in sy.items():
        if name not in defined:text=re.sub(r'\b'+re.escape(name)+r'\b',str(value),text)
    return text+'\n'+emit(plan,sy)
