; Foreground media may return control after a completed piece when the
; exact outstanding worker tick has completed. No work is acknowledged here;
; the original relay rechecks both counters before accepting its snapshot.
; No resource/cache/Ready/input/world/DMA writes. NPCs and final pieces keep
; their original path; unfinished player leases resume through the loader.
SourceMedia_Relay = $7E46EE
SourceMedia_ShouldYield:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    lda.l SourceMedia_Relay
    cmp #1
    beq SourceMedia_Guard1
    brl SourceMedia_No
SourceMedia_Guard1:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceMedia_Guard2
    brl SourceMedia_No
SourceMedia_Guard2:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceMedia_Guard3
    brl SourceMedia_No
SourceMedia_Guard3:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceMedia_Guard4
    brl SourceMedia_No
SourceMedia_Guard4:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceMedia_Guard5
    brl SourceMedia_No
SourceMedia_Guard5:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceMedia_Guard6
    brl SourceMedia_No
SourceMedia_Guard6:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceMedia_Guard7
    brl SourceMedia_No
SourceMedia_Guard7:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceMedia_Guard8
    brl SourceMedia_No
SourceMedia_Guard8:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceMedia_Guard9
    brl SourceMedia_No
SourceMedia_Guard9:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #49229
    beq SourceMedia_Guard10
    brl SourceMedia_No
SourceMedia_Guard10:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceMedia_Player
    brl SourceMedia_No
SourceMedia_Player:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SourceMedia_Record
    brl SourceMedia_No
SourceMedia_Record:
.a16
.i16
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceMedia_Guard11
    brl SourceMedia_No
SourceMedia_Guard11:
.a16
.i16
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceMedia_Remaining
    brl SourceMedia_No
SourceMedia_Remaining:
.a16
.i16
    lda.l $41200A
    and #255
    cmp #0
    beq SourceMedia_Guard12
    brl SourceMedia_No
SourceMedia_Guard12:
.a16
.i16
    lda.l $412002
    cmp.l $412004
    beq SourceMedia_Yes
    brl SourceMedia_No
SourceMedia_Yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceMedia_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceMedia_End:
.a16
.i16
