
; Unhooked canonical image-adoption primitive. Caller must already own the
; private image, metadata and exact displayed-base/resource lease. Carry only
; certifies layout preparation; it is NOT ownership, Ready or publication.
; Busy stays set throughout. No image/meta, pin, ACK, input or NMI writes.
.bank 39
.org $8B00
SourceIdleBase_AdoptCanonical:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda.l $7E46DE
    beq SourceIdleBase_G0
    brl SourceIdleBase_Reject
SourceIdleBase_G0:
.a16
.i16
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceIdleBase_G1
    brl SourceIdleBase_Reject
SourceIdleBase_G1:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    cmp #1
    beq SourceIdleBase_G2
    brl SourceIdleBase_Reject
SourceIdleBase_G2:
.a16
.i16
    lda.l SourceAttackOwned_State
    ora.l SourceAttackOwned_Use
    ora.l SourceAttackOwned_Hold
    beq SourceIdleBase_G3
    brl SourceIdleBase_Reject
SourceIdleBase_G3:
.a16
.i16
    lda.l $437840
    beq SourceIdleBase_G4
    brl SourceIdleBase_Reject
SourceIdleBase_G4:
.a16
.i16
    lda.l $437842
    cmp #40
    beq SourceIdleBase_G5
    brl SourceIdleBase_Reject
SourceIdleBase_G5:
.a16
.i16
    lda.l $437860
    cmp #40
    beq SourceIdleBase_G6
    brl SourceIdleBase_Reject
SourceIdleBase_G6:
.a16
.i16
    lda.l $437862
    cmp #80
    beq SourceIdleBase_G7
    brl SourceIdleBase_Reject
SourceIdleBase_G7:
.a16
.i16
    lda.l $43784C
    cmp #$0016
    beq SourceIdleBase_G8
    brl SourceIdleBase_Reject
SourceIdleBase_G8:
.a16
.i16
    lda.l $43786C
    cmp #$0016
    beq SourceIdleBase_G9
    brl SourceIdleBase_Reject
SourceIdleBase_G9:
.a16
.i16
    lda.l $43784E
    ora.l $43786E
    beq SourceIdleBase_G10
    brl SourceIdleBase_Reject
SourceIdleBase_G10:
.a16
.i16
    jsl SourceLayout_Defaults
    jsl SourceAttackMask_SeedHigh
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdleBase_Reject:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceIdleBase_End:
.assert * <= $279000, "idle adoption primitive exceeds verified gap"
