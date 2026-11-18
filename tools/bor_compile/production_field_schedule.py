"""Bound the original-BOR production clock/presentation seam.

Only the persistent original-BOR compiler calls this transform. Standalone
fixtures keep their historical catch-up and presentation behavior.
"""

SOURCE_FIELDS_PER_DISPATCH = 120


def bound_production_schedule(fixture: str) -> str:
    # Keep ordered source-time catch-up at its existing bounded ceiling.
    # A two-field quota was native-tested and rejected: it accumulated debt
    # faster than the main loop could consume it. Field service belongs in
    # relay waits, not in a reduced simulation-time budget.
    expected = "    cmp #120\n    bcc S6Game_PlayRender__field\n    lda #120\n"
    if fixture.count(expected) != 1:
        raise ValueError("PRODUCTION_FIELD_BUDGET_SEAM_DRIFT")
    old = "    lda.l Nmi_FrameCounter\n    and #1\n    bne S6Game_ShouldPresent__no\n"
    if fixture.count(old) != 1:
        raise ValueError("PRODUCTION_PRESENTATION_SEAM_DRIFT")
    # Keep the complete elapsed source debt. LastField advances by the bounded
    # batch only; input polling and loader/publication get control before the
    # next batch. Never replace ordered source ticks with a timestamp jump.
    jump = "    jsl Jump_PlayerInputGate\n"
    if fixture.count(jump) != 2:
        raise ValueError("PRODUCTION_NATIVE_JUMP_SEAM_DRIFT")
    fixture = fixture.replace(jump, "    jsl SourceVisual_PlayerFields\n")
    fixture = fixture.replace(old,
        "    lda.l StageTimer_FieldCounter\n"
        "    sec\n"
        "    sbc.l S6Normal_LastPresentationField\n"
        "    cmp #S6Game_PresentationDivisor\n"
        "    bcc S6Game_ShouldPresent__no\n"
        "    lda.l StageTimer_FieldCounter\n"
        "    sta.l S6Normal_LastPresentationField\n")

    return _with_nmi_clock(fixture)


def add_relay_field_service(relay: str, symbols: dict) -> str:
    # Historical immutable control ROMs lack this loader seam. They remain
    # usable; freshly linked production main always exports it.
    if "SourceVisual_ServiceCurrent" not in symbols:
        return relay
    tick = "    beq Relay_Request_Snapshot\n"
    snapshot = "    beq Relay_Snapshot_Ready\n"
    if relay.count(tick) != 1 or relay.count(snapshot) != 1:
        raise ValueError("PRODUCTION_RELAY_WAIT_SEAM_DRIFT")
    # Poll the actual completion flag first. A short worker transaction is
    # commonly done before a full visual admission would finish; launching
    # that admission on the first spin delays snapshot acceptance needlessly.
    # Y remains the original bounded timeout. Longer waits retain one-field
    # cooperative loading and the journal remains sampled by unconditional NMI.
    def wait_service(label):
        return f"""    rep #$20
    .a16
    tya
    and #$0000
    bne {label}
    jsl Relay_ServiceField
{label}:
    sep #$20
    .a8
"""
    relay = relay.replace(tick, tick + wait_service('Relay_Wait_Ticks__no_service'), 1)
    relay = relay.replace(snapshot, snapshot + wait_service('Relay_Wait_Snapshot__no_service'), 1)
    # Preserve the caller's A/X/Y/P, DBR and DP, including its timeout counter.
    # Poll into independent field histories. Never mutate the main-loop
    # Input_press/Input_old/Input_trigger while gameplay is using them.
    # Both source mailboxes and native edge latches retain each real edge.
    startup_gate = ('    lda.l $' + format(symbols['SourceVisual_CompletedValid'], '06X') + '\n    beq Relay_ServiceField__load_startup\n    jml Relay_ServiceField__return\nRelay_ServiceField__load_startup:\n    .a16\n    .i16') if 'SourceVisual_CompletedValid' in symbols else ''
    # A native jump has a physical landing deadline. Continue full P1 media
    # admission in the existing once-per-field relay opportunity while it is
    # airborne, instead of treating an old completed grounded pose as ready.
    if 'SourceVisual_CompletedValid' in symbols:
        startup_gate = (f"    lda.l ${symbols['PlayerEntity_DpBase'] + symbols['CHAR_SELECTED']:06X}\n"
                        "    and #$00FF\n    cmp #5\n    beq Relay_ServiceField__load_startup\n" + startup_gate)
    pending_service = (f"    jsl ${symbols['SourceVisual_ServicePending']:06X}\n"
                       if 'SourceVisual_ServicePending' in symbols else '')
    p1_dead_target = 'Relay_ServiceField__return'
    p2_service = ''
    if 'SVActor_ServiceP2' in symbols:
        p1_dead_target = 'Relay_ServiceField__p2_media'
        startup_gate = startup_gate.replace('jml Relay_ServiceField__return',
                                             'jml Relay_ServiceField__p2_media')
        p2_service = ("Relay_ServiceField__p2_media:\n    .a16\n    .i16\n"
                      f"    jsl ${symbols['SVActor_ServiceP2']:06X}\n")
    rendered = relay + f"""
Relay_ServiceField:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l ${symbols['Game_CampaignId']:06X}
    and #$00FF
    cmp #3
    beq Relay_ServiceField__campaign
    jml Relay_ServiceField__return
Relay_ServiceField__campaign:
    .a16
    .i16
    lda.l $7E1760
    cmp #1
    beq Relay_ServiceField__active
    jml Relay_ServiceField__return
Relay_ServiceField__active:
    .a16
    .i16
    lda.l ${symbols['StageTimer_FieldCounter']:06X}
    cmp.l ${symbols['SourceVisual_ServiceField']:06X}
    bne Relay_ServiceField__new_field
    jml Relay_ServiceField__return
Relay_ServiceField__new_field:
    .a16
    .i16
    sta.l ${symbols['SourceVisual_ServiceField']:06X}
Relay_ServiceField__joy_busy:
    .a16
    .i16
    lda $4212
    and #1
    bne Relay_ServiceField__joy_busy
    lda $4218
    bit #$000F
    beq Relay_ServiceField__p1_valid
    lda #0
Relay_ServiceField__p1_valid:
    .a16
    .i16
    sta.l ${symbols['SourceVisual_FieldRaw1']:06X}
    lda.l ${symbols['SourceVisual_FieldPress1']:06X}
    eor #$FFFF
    and.l ${symbols['SourceVisual_FieldRaw1']:06X}
    sta.l ${symbols['SourceVisual_FieldEdge1']:06X}
    ora.l $412016
    sta.l $412016
    lda.l ${symbols['SourceVisual_FieldEdge1']:06X}
    ora.l ${symbols['SourceVisual_LatchedInput']:06X}
    sta.l ${symbols['SourceVisual_LatchedInput']:06X}
    lda.l ${symbols['SourceVisual_FieldRaw1']:06X}
    sta.l ${symbols['SourceVisual_FieldPress1']:06X}
    sta.l $412014
    lda $421A
    bit #$000F
    beq Relay_ServiceField__p2_valid
    lda #0
Relay_ServiceField__p2_valid:
    .a16
    .i16
    sta.l ${symbols['SourceVisual_FieldRaw2']:06X}
    lda.l ${symbols['SourceVisual_FieldPress2']:06X}
    eor #$FFFF
    and.l ${symbols['SourceVisual_FieldRaw2']:06X}
    sta.l ${symbols['SourceVisual_FieldEdge2']:06X}
    ora.l $41201A
    sta.l $41201A
    lda.l ${symbols['SourceVisual_FieldEdge2']:06X}
    ora.l ${symbols['SourceVisual_LatchedInput2']:06X}
    sta.l ${symbols['SourceVisual_LatchedInput2']:06X}
    lda.l ${symbols['SourceVisual_FieldRaw2']:06X}
    sta.l ${symbols['SourceVisual_FieldPress2']:06X}
    sta.l $412018
{pending_service}    lda.l ${symbols['PlayerEntity_DpBase'] + symbols['CHAR_HP']:06X}
    and #$00FF
    beq {p1_dead_target}
    lda #${symbols['PlayerEntity_DpBase']:04X}
    tcd
{startup_gate}
    jsl ${symbols['SourceVisual_ServiceCurrent']:06X}
    lda.l ${symbols['SourceVisual_ServiceCount']:06X}
    inc a
    sta.l ${symbols['SourceVisual_ServiceCount']:06X}
{p2_service}Relay_ServiceField__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
"""
    # Only the production journal owns hardware sampling in fresh images.
    # Historical immutable controls retain the previous inline sampler.
    if "SourceInput_NmiGate" in symbols:
        start = rendered.index("Relay_ServiceField__joy_busy:\n")
        end = rendered.index("    sta.l $412018\n", start) + len("    sta.l $412018\n")
        rendered = rendered[:start] + f"    jsl ${symbols['SourceVisual_SampleInput']:06X}\n" + rendered[end:]
    return rendered


def _with_nmi_clock(fixture: str) -> str:
    """One source-clock producer: bootstrap/catch-up main, bounded armed NMI."""
    start='S6Game_PlayRender__measure:\n';flush='S6Game_PlayRender__flush:\n';post='S6Game_PlayRender__post_flush:\n';gate='S6Game_ShouldPresent:\n'
    if any(fixture.count(k)!=1 for k in (start,flush,post,gate)):
        raise ValueError('NMI_CLOCK_FIXTURE_SEAM_DRIFT')
    a,b=fixture.index(start),fixture.index(flush)
    body=fixture[a:b];back='    jmp S6Game_PlayRender__return\n'
    if body.count(back)!=2:raise ValueError('NMI_CLOCK_RETURN_SEAM_DRIFT')
    body=body.replace(start,'S6Normal_DispatchElapsed:\n',1)
    body=body.replace(back,'    jmp S6Normal_DispatchElapsed__none\n',1).replace(back,'    jmp S6Normal_DispatchElapsed__fault\n',1)
    limit='    cmp #120\n    bcc S6Game_PlayRender__field\n    lda #120\n'
    if body.count(limit)!=1:raise ValueError('NMI_CLOCK_BOUND_SEAM_DRIFT')
    body=body.replace(limit,'''    ; Parity was derived from the FULL gap. Limit only this dispatch's work.
    pha
    lda.l S6Normal_NmiContext
    beq S6Normal_DispatchElapsed__foreground_limit
    pla
    cmp #2
    bcc S6Game_PlayRender__field
    lda #2
    bra S6Game_PlayRender__field
S6Normal_DispatchElapsed__foreground_limit:
.a16
.i16
    pla
'''+limit)
    body+='''    lda #1
    clc
    rtl
S6Normal_DispatchElapsed__none:
.a16
.i16
    lda #0
    clc
    rtl
S6Normal_DispatchElapsed__fault:
.a16
.i16
    lda #2
    sec
    rtl

'''
    replacement=start+'''    .a16
    .i16
    lda.l S6Normal_NmiArm
    cmp #1
    bne S6Game_PlayRender__foreground_clock
    ; Temporarily hand the clock to foreground before reading both stamps.
    ; An intervening NMI may sample inputs, but cannot change LastField.
    lda #0
    sta.l S6Normal_NmiArm
    lda.l StageTimer_FieldCounter
    sec
    sbc.l S6Game_LastField
    cmp #9
    bcs S6Game_PlayRender__foreground_clock
    lda #1
    sta.l S6Normal_NmiArm
    bra S6Game_PlayRender__clock_dispatched
S6Game_PlayRender__foreground_clock:
.a16
.i16
    jsl S6Normal_DispatchElapsed
    bcc S6Game_PlayRender__clock_valid
    jmp S6Game_PlayRender__return
S6Game_PlayRender__clock_valid:
.a16
.i16
    cmp #0
    bne S6Game_PlayRender__clock_dispatched
    jmp S6Game_PlayRender__return
S6Game_PlayRender__clock_dispatched:
.a16
.i16
'''
    def scope(name,armed):
        checks=[]
        if armed:checks.append(('    lda.l S6Normal_NmiArm\n    cmp #1\n'))
        checks += ['    lda.l Game_CampaignId\n    and #$00FF\n    cmp #3\n',
                   '    lda.l SourceInput_Magic\n    cmp #$1A60\n',
                   '    lda.l SourceInput_BaseReady\n    cmp #1\n',
                   '    lda.l S6Host_Mode\n    cmp #1\n',
                   '    lda.l S6Host_Error\n    cmp #0\n',
                   '    lda.l $7E175C\n    cmp #1\n',
                   '    lda.l S7Resident_Owner\n    cmp #S7Resident_Enabled\n',
                   '    lda.l Game_State\n    cmp #0\n',
                   '    lda.l Game_StageIndex\n    cmp.l S6Normal_LastStage\n',
                   '    lda.l $41200C\n    and #$00FF\n    cmp #0\n']
        out=''
        for i,check in enumerate(checks):
            label=f'{name}__scope_{i}'
            out+=check+f'    beq {label}\n    brl {name}__done\n{label}:\n.a16\n.i16\n'
        return out
    helpers='''; Called only at the existing post-PPU input-tail seam.
S6Normal_NmiClockTail:
.a16
.i16
    jsl SourceInput_NmiSample
    jsl S6Normal_NmiClock
    rtl
S6Normal_NmiClock:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
'''+scope('S6Normal_NmiClock',True)+'''    lda #1
    sta.l S6Normal_NmiContext
    jsl S6Normal_DispatchElapsed
    lda #0
    sta.l S6Normal_NmiContext
S6Normal_NmiClock__done:
    rep #$30
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

S6Normal_ArmNmiClock:
.a16
.i16
'''+scope('S6Normal_ArmNmiClock',False)+'''    lda #1
    sta.l S6Normal_NmiArm
S6Normal_ArmNmiClock__done:
.a16
.i16
    rtl

'''
    fixture=fixture[:a]+replacement+fixture[b:]
    fixture=fixture.replace(post,post+'    jsl S6Normal_ArmNmiClock\n',1)
    return fixture.replace(gate,body+helpers+gate,1)
