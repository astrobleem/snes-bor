"""Bounded native ground slice. Closed empty environment; no full world tick.

One real constructor persists across requests. Native hardware input, source
history, ground/frame services, velocity and check_move own all movement.
The host may request a step and read the sealed snapshot; it never writes keys,
poses, velocities or animation frames. Snapshot composition is host-side.
"""
from source_player_input_native import emit as emit_history

REQUEST = 0x7ffb80
EPOCH = 0x7ffb90
SNAPSHOT = 0x7fba00


def bind(asm, regions, sy,display=False):
    g=regions['ground_controls']; history=regions['input_history']
    needle=' lda.l REQUEST\n cmp #$B4E7'
    if asm.count(needle)!=1:raise ValueError('LIVE_GROUND_GATE')
    asm=asm.replace(needle,' lda.l REQUEST\n cmp #$B4E8\n bne LiveGroundNotStep\n jmp LiveGroundStart\nLiveGroundNotStep:\n.a16\n.i16\n'+needle)
    # This isolated service test withdraws legacy NMI/audio writers while its
    # borrowed source control arena is active. It makes no timing/debt claim.
    asm=asm.replace('CallbackFixture_Init:\n.a16\n.i16\n nop',
        'LiveGroundAcquire:\n.a16\n.i16\n sep #$20\n.a8\n lda #0\n sta.l $004200\n sta.l $002228\n lda #$80\n sta.l $002226\n sta.l $002231\n rep #$20\n.a16\nCallbackFixture_Init:\n.a16\n.i16\n nop')
    asm=asm.replace('CallbackFixture_Return:\n.a16\n.i16\n',
        'CallbackFixture_Return:\n.a16\n.i16\n sep #$20\n.a8\n lda #$81\n sta.l $004200\n rep #$20\n.a16\n')
    needle='CallbackFixture_GroundPrepare:\n.a16\n.i16\n nop'
    if asm.count(needle)!=1:raise ValueError('LIVE_GROUND_CONSTRUCTOR_GATE')
    asm=asm.replace(needle,needle+'\n jmp LiveGroundBoot\nLiveGroundExecute:\n.a16\n.i16')
    needle='CallbackFixture_GroundDone:\n.a16\n.i16\n nop'
    asm=asm.replace(needle,needle+'\n jmp LiveGroundPost')
    lines=['LiveGroundBoot:', '.a16','.i16']
    def store(addr,value):lines.extend([f' lda #{value}',f' sta.l {addr}'])
    for name,size,magic in [('ground_controls',128,0xb679),('ground_binding_controls',32,0xb67c),
                           ('find_here_empty_controls',24,0xb67d),('ground_services_controls',32,0xb67e),
                           ('common_idle_controls',24,0xb680),('run_binding_controls',32,0xb681),
                           ('run_cancel_controls',48,0xb677),('input_history',1024,0)]:
        lines+=[' lda #0',' ldx #0',f'LiveGroundClear_{name}:','.a16','.i16',
                f' sta.l {regions[name]},x',' inx',' inx',f' cpx #{size}',f' bne LiveGroundClear_{name}']
        if magic:store(regions[name],magic)
    store(regions['input_owner'],0xb674)
    for off,value in ((20,1),(22,1),(76,1),(80,0),(82,2)):store(g+off,value)
    settings=dict(VmSourceWorld_Level=1,SourceDefaultPlayer4086_Ready=0xb503,SourceDefaultPlayer4086_Status=0,
        SourceLifecycle4086_Ready=0xb4fb,SourceLifecycle4086_Status=2,
        SourceFreeze4086_Ready=0xb5df,SourceVelocity4086_Ready=0xb5de,
        SourceCheckMove4086_Ready=0xb617,SourceEmptyInitEnvironment4086_Ready=0xb504,
        SourceEmptyInitEnvironment4086_Models=16,SourceEmptyInitEnvironment4086_Stage=1,
        SourceEmptyInitEnvironment4086_Status=0,SourceEnvironment4086_Ready=0xb4d1,
        SourceEnvironment4086_Stage=1,SourceEnvironment4086_WallCount=0,
        SourceWorldTick4086_Ready=0xb4d5,SourceWorldTick4086_State=1,
        SourceWorldTick4086_Pending=1,SourceWorldTick4086_Fault=0,SourceWorldTick4086_Slot=0,
        SourceWorldTick4086_TimeHi=0,
        SourceSelf4086_Ready=0xb4f6,SourceSelf4086_Active=0,SourceSelf4086_Fault=0,
        SourceSelf4086_GlobalLow=0x4000,SourceSelf4086_GlobalHigh=0x41)
    for name,value in settings.items():store(sy[name],value)
    store(0x43eb00,1);store(0x43eb02,0) # walking allowed in this closed ground slice
    for off in range(0,40,2):store(0x42e000+off,0)
    for off in range(0,8,2):store(0x43fd94+off,0)
    store(EPOCH,0)
    lines+=[' jsl LiveGroundSeal',' jmp CallbackFixture_Return',
            'LiveGroundStart:','.a16','.i16']
    store(REQUEST,0)
    # arrange_ents starts a fresh movement-mark epoch before POST_UPDATE.
    store(0x42e024,0);store(0x42e026,0)
    lines += [f' lda.l {EPOCH}',' clc',' adc #49',f' sta.l {sy["VmSourceWorld_Time"]}',
              f' sta.l {sy["SourceWorldTick4086_TimeLo"]}',f' sta.l {g+40}',
              ' tax',' ldy #0',' lda #1',f' jsl {sy["SourceInputController_Refresh"]}',
              ' bcs CallbackFixture_Bad']
    lines += [' sep #$20','.a8',' lda #0',' sta.l $004200',' lda #$80',' sta.l $002231',' rep #$20','.a16']
    for off in range(0,20,2):
        lines += [f' lda.l {0x7ff8a0+off}',f' sta.l {regions["input_snapshot"]+off}']
    lines += [' jsl PlayerHistory_Refresh',' bcs CallbackFixture_Bad']
    for off in (0,2):lines += [f' lda.l {history+216+off}',f' sta.l {g+16+off}']
    # Directional keys only. Other commands require the complete controller.
    lines += [f' lda.l {history+216}',' and #$FFFC',' cmp #$003C',
              ' bcc LiveGroundKeysOK',' jmp CallbackFixture_Bad','LiveGroundKeysOK:','.a16','.i16']
    store(sy['SourceWorldTick4086_Phase'],6)
    lines += [' jmp LiveGroundExecute','LiveGroundPost:','.a16','.i16']
    for off in (0,2,4,6):store(0x41f500+off,0)
    store(sy['SourceWorldTick4086_Phase'],10);store(sy['SourceVelocity4086_Status'],0)
    lines += [f' jsl {sy["SourceVelocity4086_Apply"]}',' bcs CallbackFixture_Bad']
    store(sy['SourceWorldTick4086_Phase'],11);store(sy['SourceCheckMove4086_Status'],0)
    lines += [f' jsl {sy["SourceCheckMove4086_Execute"]}',' bcs CallbackFixture_Bad',
              f' lda.l {EPOCH}',' inc a',f' sta.l {EPOCH}',' jsl LiveGroundSeal',
              ' jmp CallbackFixture_Return','LiveGroundSeal:','.a16','.i16',' php',' rep #$30',' phx']
    # Epoch published LAST, after canonical view and sidecar are copied.
    for source,count,target in ((0x414000,80,SNAPSHOT),(0x416800,64,SNAPSHOT+80)):
        label=f'LiveGroundCopy_{source:x}'
        lines += [' ldx #0',label+':','.a16','.i16',f' lda.l {source},x',f' sta.l {target},x',
                  ' inx',' inx',f' cpx #{count}',f' bne {label}']
    lines += [f' lda.l {EPOCH}',f' sta.l {SNAPSHOT+144}',' plx',' plp',' rtl']
    if display:
        joined='\n'.join(lines)
        joined=joined.replace(' jsl LiveGroundSeal\n jmp CallbackFixture_Return',
            ' jsl LiveGroundSeal\n jsl $398000\n bcs CallbackFixture_Bad\n jmp LiveGroundIdle')
        joined+='\nLiveGroundIdle:\n.a16\n.i16\n sep #$20\n.a8\n lda #$81\n sta.l $004200\n rep #$20\n.a16\nLiveGroundIdlePoll:\n.a16\n.i16\n lda.l REQUEST\n cmp #$B4E8\n bne LiveGroundIdlePoll\n jmp LiveGroundStart\n'
        lines=joined.splitlines()
    return asm+'\n'+'\n'.join(lines)+'\n'+emit_history(history,regions['input_scratch'],regions['input_snapshot'],
                       regions['combo_sequence'],regions['input_owner'],0xb674)
