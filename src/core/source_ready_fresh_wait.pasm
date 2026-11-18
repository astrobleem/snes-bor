; REP #$31 before the wait's PHP guarantees saved carry is initially zero.
; Final CMP overwrites carry, so that saved bit can identify this wait's
; deferred service without globals, another local or changed stack offsets.
; Entry JSL adds3 bytes: saved P is13,s and old counter is4,s.
SourceReadyWait_Start:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceReadyWait_Startup
    lda.l Game_State
    bne SourceReadyWait_Startup
    lda.l $7E175E
    cmp #2
    bne SourceReadyWait_Startup
    lda.l $7E1760
    cmp #1
    bne SourceReadyWait_Startup
    lda.l $7E46DC
    cmp #1
    bne SourceReadyWait_Startup
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    bne SourceReadyWait_Startup
    lda.l SourceVisual_CompletedValid
    cmp #1
    bne SourceReadyWait_Startup
    ; BW-RAM follows the WRAM ownership/ready guards above.
    lda.l SVActor_Magic
    cmp #$AC19
    bne SourceReadyWait_Startup
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    bne SourceReadyWait_Startup
    sep #$20
.a8
    lda.l Msu1_StreamBusy
    bne SourceReadyWait_Startup
    lda 13,s
    ora #1
    sta 13,s
    rep #$30
.a16
.i16
    clc
    lda 4,s
    rtl
SourceReadyWait_Startup:
    rep #$30
.a16
.i16
    clc
    lda 4,s
    jml SVActor_ServiceFirstNpcDuringWait
SourceReadyWait_End:
.a16
.i16
    bcc SourceReadyWait_Compare
    jsl SVActor_ServiceFirstNpcDuringWait
SourceReadyWait_Compare:
.a16
.i16
    cmp.l Nmi_FrameCounter
    jml Core_Nmi_WaitFrame__return
SourceReadyWait_ModuleEnd:
