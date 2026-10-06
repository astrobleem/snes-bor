SourceInputController_Map:
.a16
.i16
    sta.l SourceInputController_Raw
    lda #0
    sta.l SourceInputController_Mapped
    lda.l SourceInputController_Raw
    and #$4000
    beq SourceInputController_Map__next_0
    lda.l SourceInputController_Mapped
    ora #$0040
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_0:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$8000
    beq SourceInputController_Map__next_1
    lda.l SourceInputController_Mapped
    ora #$0400
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_1:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$0080
    beq SourceInputController_Map__next_2
    lda.l SourceInputController_Mapped
    ora #$0080
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_2:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$0040
    beq SourceInputController_Map__next_3
    lda.l SourceInputController_Mapped
    ora #$0100
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_3:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$0020
    beq SourceInputController_Map__next_4
    lda.l SourceInputController_Mapped
    ora #$0800
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_4:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$0010
    beq SourceInputController_Map__next_5
    lda.l SourceInputController_Mapped
    ora #$1000
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_5:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$2000
    beq SourceInputController_Map__next_6
    lda.l SourceInputController_Mapped
    ora #$0001
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_6:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$1000
    beq SourceInputController_Map__next_7
    lda.l SourceInputController_Mapped
    ora #$0002
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_7:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$0800
    beq SourceInputController_Map__next_8
    lda.l SourceInputController_Mapped
    ora #$0010
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_8:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$0400
    beq SourceInputController_Map__next_9
    lda.l SourceInputController_Mapped
    ora #$0020
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_9:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$0200
    beq SourceInputController_Map__next_10
    lda.l SourceInputController_Mapped
    ora #$0004
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_10:
.a16
.i16
    lda.l SourceInputController_Raw
    and #$0100
    beq SourceInputController_Map__next_11
    lda.l SourceInputController_Mapped
    ora #$0008
    sta.l SourceInputController_Mapped
SourceInputController_Map__next_11:
.a16
.i16
    lda.l SourceInputController_Mapped
    rts
