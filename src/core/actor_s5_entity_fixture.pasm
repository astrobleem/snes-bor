; CLONE-ONLY adapter, never include in production. Constants are supplied by
; tools/verify/actor_s5_entity_fixture.py from the copied ROM's symbol file.
; Central entry replaces REP #$31 / PHD at CharacterEntity_Play, before its
; lifecycle/animation gates. A separate legacy hit guard prevents double hits.
; Existing bank-0 JSR caller/RTS stack is retained across far JMPs.
; Unarmed/unselected/profile-0 actors replay the original prologue and resume
; the immutable routine. Source cases are explicit controlled entity tests.
; Context $1900, mailbox $1A00; separate from ActorBehavior's $1800 scratch.
; Bounded clock binding: persistent animation $1B00, rational clock $1C00,
; forty 12-byte CPU trace rows $1D00..$1EDF. Never used by production.
; Host serializes mailbox writes while paused; no interrupt uses this context.
; Mailbox words: magic, armed, attacker DP, target DP, profile, behavior flags,
; source role ID(+reserved), reserved, target role ID(+reserved), reserved, request, ack,
; operation(1 evaluate,2 real loader), desired roster, HP before/after, hit,
; force, drop, observed frame/target frame/selected, service count, reserved,
; reserved, loaded, error. Profile 1=source, 2=explicit compat control, 0=delegate.
; SOURCE coordinate control inverses the accepted 0.8 scale on X and Y.
; The verifier requires multiples of four so source coordinates are integral.
; No source raster equivalence, organic behavior, attack-ID, stats scaling,
; score/SFX, invulnerability, grabs or full takedamage callback is certified.

S5Entity_Entry:
    rep #$30
    .a16
    .i16
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
    lda.l $7E1A3A
    inc a
    sta.l $7E1A3A
    tdc
    sta.l $7E1A3C
    lda.l $7E1A00
    cmp #$53A5
    bne S5Entity_Delegate
    tdc
    cmp.l $7E1A04
    bne S5Entity_Delegate
    lda.l $7E1A02
    beq S5Entity_Unarmed
    lda.l $7E1A1C
    cmp #2
    beq S5Entity_Load
    cmp #3
    bne S5Entity_NotMap
    brl S5Entity_Map
S5Entity_NotMap:
    .a16
    .i16
    cmp #4
    bne S5Entity_NotClock
    brl S5Entity_ClockBegin
S5Entity_NotClock:
    .a16
    .i16
    lda.l $7E1A08
    beq S5Entity_AckDelegate
    brl S5Entity_Evaluate
S5Entity_Unarmed:
    .a16
    .i16
    lda.l $7E1A08
    beq S5Entity_Delegate
    brl S5Entity_Return
S5Entity_AckDelegate:
    .a16
    .i16
    lda.l $7E1A18
    sta.l $7E1A1A
    lda #0
    sta.l $7E1A02
S5Entity_Delegate:
    .a16
    .i16
    pld
    plb
    ; Byte-for-byte displaced central-update prologue.
    rep #$31
    .a16
    phd
    jsl Game_Lifecycle
    jml Game_EntityResume

S5Entity_Load:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $7E1A1E
    sta Game_Roster
    sta.l Game_SelectIndex
    jsl Game_LoadCharacterLong
    sep #$20
    .a8
    lda.l Game_SelectLoaded
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l $7E1A36
    brl S5Entity_Ack

S5Entity_Evaluate:
    .a16
    .i16
    ; Source and compatibility controls use the same descriptor core.
    lda #$1900
    tcd
    ldx #254
S5Entity_Clear:
    .a16
    .i16
    stz $00,x
    dex
    dex
    bpl S5Entity_Clear
    lda.l $7E1A04
    sta $F0
    lda.l $7E1A06
    sta $F4
    cmp $F0
    bne S5Entity_Distinct
    inc $24
S5Entity_Distinct:
    .a16
    .i16
    lda.l $7E1A08
    sta $E0
    cmp #2
    bne S5Entity_SourceMode
    inc $E2
S5Entity_SourceMode:
    .a16
    .i16
    lda.l $7E1A0A
    sta $08
    lda #Catalog_Base & $FFFF
    sta $A0
    lda #Catalog_Base >> 16
    sta $A2
    lda #Catalog_ProjectLo
    sta $A4
    lda #Catalog_ProjectHi
    sta $A6
    ldy #Game_Roster
    lda [$F0],y
    and #$00FF
    sta $A8
    lda.l $7E1A0C
    sta $AA
    lda $E0
    sta $AC
    ldy #Game_Frame
    lda [$F0],y
    and #$00FF
    sta $06
    sta.l $7E1A2A
    sta $AE
    jsl ActorCatalog_Lookup
    lda $B6
    beq S5Entity_AttackerCatalogValid
    brl S5Entity_Bad
S5Entity_AttackerCatalogValid:
    .a16
    .i16
    lda $B8
    sta $00
    lda $BA
    sta $02
    lda $B4
    sta $04
    ldy #Game_Selected
    lda [$F0],y
    and #$00FF
    sta.l $7E1A2E
    ldy #Game_Frame
    lda [$F4],y
    and #$00FF
    sta.l $7E1A2C
    sta $AE
    ldy #Game_Roster
    lda [$F4],y
    and #$00FF
    sta $A8
    lda.l $7E1A12
    sta $AA
    lda #1
    sta $AC
    jsl ActorCatalog_Lookup
    lda $B6
    beq S5Entity_TargetValid
    brl S5Entity_Bad
S5Entity_TargetValid:
    .a16
    .i16
    lda $B0
    sta $26
    lda $B2
    sta $28
    ldy #Game_PosX
    lda [$F0],y
    jsr S5Entity_Coordinate
    sta $14
    lda [$F4],y
    jsr S5Entity_Coordinate
    sta $1C
    ldy #Game_PosY
    lda [$F0],y
    jsr S5Entity_Coordinate
    sta $16
    lda [$F4],y
    jsr S5Entity_Coordinate
    sta $1E
    ldy #Game_Facing
    lda [$F0],y
    and #1
    eor #1
    sta $1A
    lda [$F4],y
    and #1
    eor #1
    sta $22
    jsl S5_LoadFrame
    jsl S5_ActivateAttack
    jsl S5_CheckCollision
    lda $2C
    sta.l $7E1A38
    lda $4C
    sta.l $7E1A26
    lda $4E
    sta.l $7E1A28
    lda $2A
    sta.l $7E1A24
    ldy #Game_Hp
    lda [$F4],y
    and #$00FF
    sta.l $7E1A20
    sta.l $7E1A22
    lda $2A
    beq S5Entity_Ack
    lda.l $7E1A20
    sec
    sbc $4C
    bcs S5Entity_Hp
    lda #0
S5Entity_Hp:
    .a16
    .i16
    sta.l $7E1A22
    sep #$20
    .a8
    sta [$F4],y
    ldy #Game_HitStun
    lda #20
    sta [$F4],y
    ldy #Game_HitApplied
    lda #1
    sta [$F0],y
    rep #$20
    .a16
    lda $4E
    beq S5Entity_Ack
    ; Bounded drop=nonzero reaction control on the actual target entity.
    sep #$20
    .a8
    ldy #Game_Selected
    lda #3
    sta [$F4],y
    ldy #Game_Frame
    lda #0
    sta [$F4],y
    rep #$20
    .a16
    bra S5Entity_Ack
S5Entity_Bad:
    .a16
    .i16
    lda #3
    sta.l $7E1A38
S5Entity_Ack:
    .a16
    .i16
    lda.l $7E1A30
    inc a
    sta.l $7E1A30
    lda.l $7E1A18
    sta.l $7E1A1A
    lda #0
    sta.l $7E1A02
S5Entity_Return:
    .a16
    .i16
    pld
    plb
    rep #$31
    .a16
    phd
    jsl Game_Lifecycle
    jml Game_EntityResume

S5Entity_LegacyHitGuard:
    rep #$30
    .a16
    .i16
    lda.l $7E1A00
    cmp #$53A5
    bne S5Entity_LegacyReplay
    tdc
    cmp.l $7E1A04
    bne S5Entity_LegacyReplay
    lda.l $7E1A08
    beq S5Entity_LegacyReplay
    jml Game_HitDone
S5Entity_LegacyReplay:
    .a16
    .i16
    sep #$20
    .a8
    lda Game_Selected
    jml Game_HitResume

S5Entity_Coordinate:
    .a16
    .i16
    ; Host controls are nonnegative, <=8191, and divisible by four.
    ; Profile 2 compares original accepted pixels, profile 1 source pixels.
    pha
    lda $E0
    cmp #1
    beq S5Entity_CoordinateSource
    pla
    rts
S5Entity_CoordinateSource:
    .a16
    .i16
    pla
    sta $F8
    asl a
    asl a
    clc
    adc $F8
    lsr a
    lsr a
S5Entity_CoordinateDone:
    .a16
    .i16
    rts

S5_HostRandom03:
    rep #$30
    .a16
    .i16
    ; Drift is deliberately not selected by this adapter.
    lda #$FFFF
    sta $BE
    rtl

; Clone-only directory extension: existing slots retain their original seeks.
; The new fixture slot's record is appended after the immutable MSU payload,
; so no accepted directory, actor, background or scene offset has to move.
S5Entity_Directory:
    sep #$20
    .a8
    lda.l Game_SelectIndex
    cmp #Game_ExtendedIndex
    bcc S5Entity_DirectoryReplay
    cmp #Game_ExtendedIndex+Game_ExtendedCount
    bcc S5Entity_DirectoryExtended
S5Entity_DirectoryReplay:
    .a8
    ; Displaced six bytes: SEP #$20 / LDA.l CharDirSeek16.
    lda.l Game_DirectorySeek
    jml Game_DirectoryResume
S5Entity_DirectoryExtended:
    rep #$30
    .a16
    .i16
    phx
    and #$00FF
    sec
    sbc #Game_ExtendedIndex
    asl a
    asl a
    tax
    sep #$20
    .a8
    lda.l Game_ExtDirTable,x
    sta $2000
    inx
    lda.l Game_ExtDirTable,x
    sta $2001
    inx
    lda.l Game_ExtDirTable,x
    sta $2002
    inx
    lda.l Game_ExtDirTable,x
    sta $2003
    plx
    jml Game_DirectoryBusy

; Ordinary S4 spawn-map consumer, invoked by the central entity callback.
; Its generated count byte is bound in the clone; it performs real validation.
S5Entity_Map:
    rep #$30
    .a16
    .i16
    tdc
    sec
    sbc #$0A00
    sta.l Spawn_ScratchSlotOfs
    sep #$20
    .a8
    lda.l $7E1A1E
    sta.l Spawn_ScratchMap
    jsl StageEnv_ApplySpawnMap
    rep #$30
    .a16
    .i16
    brl S5Entity_Ack

S5Entity_GameDiagnostic:
    php
    rep #$31
    .a16
    .i16
    lda.l $7E1AF2
    beq S5Entity_GameGuardDone
    lda.l Game_StateAddress
    bne S5Entity_GameGuardBad
    sep #$20
    .a8
    lda.l SceneVideo_PlayState
    ora.l SceneVideo_SequenceActive
    ora.l SceneVideo_TestActive
    beq S5Entity_GameGuardDone
S5Entity_GameGuardBad:
    rep #$30
    .a16
    .i16
    lda #1
    sta.l $7E1AF0
S5Entity_GameGuardDone:
    rep #$30
    .a16
    .i16
    lda.l $7E1A40
    inc a
    sta.l $7E1A40
    lda.l Game_StateAddress
    sta.l $7E1A42
    jml Game_StateResume

; Operation 4 starts one nonlooping source animation at its actual frame.
; Host chooses role/profile once. All subsequent frame writes are CPU-owned.
S5Entity_ClockBegin:
    rep #$30
    .a16
    .i16
    lda.l $7E1A08
    cmp #1
    beq S5Entity_ClockProfile
    brl S5Entity_Bad
S5Entity_ClockProfile:
    .a16
    .i16
    lda.l $7E1A10
    beq S5Entity_ClockBadLimit
    cmp #41
    bcc S5Entity_ClockLimitValid
S5Entity_ClockBadLimit:
    .a16
    .i16
    brl S5Entity_Bad
S5Entity_ClockLimitValid:
    .a16
    .i16
    lda #$1B00
    tcd
    ldx #254
S5Entity_ClockClearAnimation:
    .a16
    .i16
    stz $00,x
    dex
    dex
    bpl S5Entity_ClockClearAnimation
    lda.l $7E1A04
    sta $F0
    sta.l $7E1AF6
    lda #Catalog_Base & $FFFF
    sta $A0
    lda #Catalog_Base >> 16
    sta $A2
    lda #Catalog_ProjectLo
    sta $A4
    lda #Catalog_ProjectHi
    sta $A6
    ldy #Game_Roster
    lda [$F0],y
    and #$00FF
    sta $A8
    lda.l $7E1A0C
    sta $AA
    lda #1
    sta $AC
    sta $E0
    ldy #Game_Frame
    lda [$F0],y
    and #$00FF
    sta $AE
    sta $06
    lda.l $7E1A0A
    sta $08
    jsl ActorCatalog_Lookup
    lda $B6
    beq S5Entity_ClockResolved
    brl S5Entity_Bad
S5Entity_ClockResolved:
    .a16
    .i16
    lda $B8
    sta $00
    lda $BA
    sta $02
    lda $B4
    sta $04
    ; Lookup scratch and animation deadlines deliberately share D0..D6.
    ; Resolution is complete before this persistent timeline starts.
    stz $D0
    stz $D2
    stz $D4
    stz $D6
    jsl S5_AnimationBegin
    lda #$1C00
    tcd
    ldx #254
S5Entity_ClockClearClock:
    .a16
    .i16
    stz $00,x
    dex
    dex
    bpl S5Entity_ClockClearClock
    lda.l $7E1A10
    sta $34
    lda #21477270 & $FFFF
    sta $08
    lda #21477270 >> 16
    sta $0A
    lda.l Nmi_FrameCounter
    sta $20
    sta.l $7E1AFA
    lda #0
    sta.l $7E1AF8
    ldx #478
S5Entity_ClockClearTrace:
    .a16
    .i16
    sta.l $7E1D00,x
    dex
    dex
    bpl S5Entity_ClockClearTrace
    lda #1
    sta.l $7E1AF4
    brl S5Entity_Ack

; Called only from the private NMI-return trampoline after Core_Nmi_Play.
; Reconstruct alternating NTSC master-clock intervals from NMI delta and
; live $213F parity. No nominal-60Hz clock and no host tick/frame writes.
; Callbacks can batch missed intervals; this does not certify raster cadence.
S5Entity_ClockUpdate:
    rep #$30
    .a16
    .i16
    phd
    lda #$1C00
    tcd
    lda.l Nmi_FrameCounter
    sta $22
    sec
    sbc $20
    bne S5Entity_ClockElapsed
    brl S5Entity_ClockReturn
S5Entity_ClockElapsed:
    .a16
    .i16
    cmp #121
    bcc S5Entity_ClockDeltaValid
    brl S5Entity_ClockError
S5Entity_ClockDeltaValid:
    .a16
    .i16
    sta $24
    lda $22
    sta $20
    sep #$20
    .a8
    lda.l $00213F
    and #$80
    rep #$20
    .a16
    and #$00FF
    sta $26
S5Entity_ClockInterval:
    .a16
    .i16
    lda $24
    and #1
    bne S5Entity_ClockSameParity
    lda $26
    eor #$80
    bra S5Entity_ClockParity
S5Entity_ClockSameParity:
    .a16
    .i16
    lda $26
S5Entity_ClockParity:
    .a16
    .i16
    sta $2E
    bne S5Entity_ClockShort
    lda #(357368*200) & $FFFF
    sta $00
    lda #(357368*200) >> 16
    bra S5Entity_ClockNumerator
S5Entity_ClockShort:
    .a16
    .i16
    lda #(357364*200) & $FFFF
    sta $00
    lda #(357364*200) >> 16
S5Entity_ClockNumerator:
    .a16
    .i16
    sta $02
    lda $28
    cmp #24
    bcc S5Entity_ClockTraceSpace
    brl S5Entity_ClockError
S5Entity_ClockTraceSpace:
    .a16
    .i16
    asl a
    asl a
    asl a
    tax
    lda $22
    sta $40,x
    lda $2E
    sta $42,x
    lda $00
    sta $44,x
    lda $02
    sta $46,x
    lda $30
    clc
    adc $00
    sta $30
    lda $32
    adc $02
    sta $32
    bcc S5Entity_ClockNoOverflow
    brl S5Entity_ClockError
S5Entity_ClockNoOverflow:
    .a16
    .i16
    inc $28
    jsl S5_ClockAdvance
    lda $16
    bne S5Entity_ClockError
    lda.l $7E1AF4
    beq S5Entity_ClockReturn
    dec $24
    beq S5Entity_ClockReturn
    brl S5Entity_ClockInterval
S5Entity_ClockError:
    .a16
    .i16
    lda #0
    sta.l $7E1AF4
    lda #2
    sta.l $7E1AF8
S5Entity_ClockReturn:
    .a16
    .i16
    pld
    rts

S5_HostSourceTick:
    rep #$30
    .a16
    .i16
    phd
    lda.l $7E1AF4
    beq S5Entity_SourceTickReturn
    lda #$1B00
    tcd
    jsl S5_AnimationTick
    ; Publish to the real actor, then independently read back for the trace.
    sep #$20
    .a8
    ldy #Game_Frame
    lda $06
    sta [$F0],y
    rep #$20
    .a16
    lda $D0
    sta $E8
    asl a
    clc
    adc $E8
    asl a
    asl a
    sec
    sbc #12
    tax
    lda $D0
    sta.l $7E1D00,x
    lda $06
    sta.l $7E1D02,x
    lda $0E
    sta.l $7E1D04,x
    lda $10
    sta.l $7E1D06,x
    lda [$F0],y
    and #$00FF
    sta.l $7E1D08,x
    lda.l $7E1C22
    sta.l $7E1D0A,x
    lda $D0
    cmp.l $7E1C34
    bcc S5Entity_SourceTickReturn
    lda #0
    sta.l $7E1AF4
    lda #1
    sta.l $7E1AF8
S5Entity_SourceTickReturn:
    .a16
    .i16
    pld
    rtl

; Clone replaces NMI's final RTI plus three verified padding bytes with JML.
; Core_Nmi_Play has already restored A/X/Y/DBR/D in A16/I16. Preserve them
; around the clock, then RTI consumes the original hardware interrupt frame.
S5Entity_NmiClock:
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
    lda.l $7E1A00
    cmp #$53A5
    bne S5Entity_NmiClockDone
    lda.l $7E1A1C
    cmp #4
    bne S5Entity_NmiClockDone
    lda.l $7E1AF4
    cmp #1
    bne S5Entity_NmiClockDone
    jsr S5Entity_ClockUpdate
S5Entity_NmiClockDone:
    .a16
    .i16
    pld
    plb
    ply
    plx
    pla
    rti
