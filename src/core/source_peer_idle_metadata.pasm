; Preload only exact immutable peer idle0 metadata; no desired lease or pins.
SourcePeerIdle_AfterCapture:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
tdc
cmp #2560
    beq SourcePeerIdle_G12
    brl SourcePeerIdle_Done
SourcePeerIdle_G12:
.a16
.i16
lda.l Game_CampaignId
and #255
cmp #3
    beq SourcePeerIdle_G19
    brl SourcePeerIdle_Done
SourcePeerIdle_G19:
.a16
.i16
lda.l Game_State
cmp #0
    beq SourcePeerIdle_G27
    brl SourcePeerIdle_Done
SourcePeerIdle_G27:
.a16
.i16
lda.l $7E175E
cmp #2
    beq SourcePeerIdle_G34
    brl SourcePeerIdle_Done
SourcePeerIdle_G34:
.a16
.i16
lda.l $7E1760
cmp #1
    beq SourcePeerIdle_G41
    brl SourcePeerIdle_Done
SourcePeerIdle_G41:
.a16
.i16
lda.l $7E46DC
cmp #1
    beq SourcePeerIdle_G48
    brl SourcePeerIdle_Done
SourcePeerIdle_G48:
.a16
.i16
lda.l $7E46DE
cmp #0
    beq SourcePeerIdle_G55
    brl SourcePeerIdle_Done
SourcePeerIdle_G55:
.a16
.i16
lda.l SourceInput_Magic
cmp #6752
    beq SourcePeerIdle_G62
    brl SourcePeerIdle_Done
SourcePeerIdle_G62:
.a16
.i16
lda.l SourceVisual_CompletedMagic
cmp #49229
    beq SourcePeerIdle_G69
    brl SourcePeerIdle_Done
SourcePeerIdle_G69:
.a16
.i16
lda.l SVActor_Magic
cmp #44057
    beq SourcePeerIdle_G76
    brl SourcePeerIdle_Done
SourcePeerIdle_G76:
.a16
.i16
lda.l Game_StageIndex
cmp #0
    beq SourcePeerIdle_G83
    brl SourcePeerIdle_Done
SourcePeerIdle_G83:
.a16
.i16
lda.l SourceVisual_CompletedValid
cmp #1
    beq SourcePeerIdle_G90
    brl SourcePeerIdle_Done
SourcePeerIdle_G90:
.a16
.i16
lda.l SourceVisual_CompletedEntry
cmp #22
    beq SourcePeerIdle_G97
    brl SourcePeerIdle_Done
SourcePeerIdle_G97:
.a16
.i16
lda.l SourceVisual_CompletedEntry+2
cmp #0
    beq SourcePeerIdle_G104
    brl SourcePeerIdle_Done
SourcePeerIdle_G104:
.a16
.i16
lda.l SVActor_Data+SVActor_Valid
cmp #1
    beq SourcePeerIdle_G111
    brl SourcePeerIdle_Done
SourcePeerIdle_G111:
.a16
.i16
lda.l SVActor_Data
cmp #278
    beq SourcePeerIdle_G118
    brl SourcePeerIdle_Done
SourcePeerIdle_G118:
.a16
.i16
lda.l SVActor_Data+3
and #255
cmp #0
    beq SourcePeerIdle_G125
    brl SourcePeerIdle_Done
SourcePeerIdle_G125:
.a16
.i16
lda.l SVActor_Data+SVActor_Stage
cmp #0
    beq SourcePeerIdle_G133
    brl SourcePeerIdle_Done
SourcePeerIdle_G133:
.a16
.i16
lda.l SourceVisual_Sa1OwnerPolicy+133
and #255
cmp #2
    beq SourcePeerIdle_G140
    brl SourcePeerIdle_Done
SourcePeerIdle_G140:
.a16
.i16
lda.l SourceVisual_Sa1RuntimeRole+133
and #255
cmp #0
    beq SourcePeerIdle_G148
    brl SourcePeerIdle_Done
SourcePeerIdle_G148:
.a16
.i16
lda.l SVActor_MetaData+SVActor_MetaValid
cmp #1
    beq SourcePeerIdle_G156
    brl SourcePeerIdle_Done
SourcePeerIdle_G156:
.a16
.i16
lda.l SVActor_MetaData+SVActor_MetaStage
cmp #0
    beq SourcePeerIdle_G163
    brl SourcePeerIdle_Done
SourcePeerIdle_G163:
.a16
.i16
lda.l SVActor_MetaData
cmp #923
    beq SourcePeerIdle_G170
    brl SourcePeerIdle_Done
SourcePeerIdle_G170:
.a16
.i16
lda.l SVActor_MetaData+2
cmp #10
    beq SourcePeerIdle_G177
    brl SourcePeerIdle_Done
SourcePeerIdle_G177:
.a16
.i16
lda.l SVActor_MetaData+4
cmp #22
    beq SourcePeerIdle_G184
    brl SourcePeerIdle_Done
SourcePeerIdle_G184:
.a16
.i16
lda.l SVActor_MetaData+6
cmp #0
    beq SourcePeerIdle_G191
    brl SourcePeerIdle_Done
SourcePeerIdle_G191:
.a16
.i16
lda.l SVActor_MetaData+1280+SVActor_MetaValid
cmp #1
    beq SourcePeerIdle_G198
    brl SourcePeerIdle_Done
SourcePeerIdle_G198:
.a16
.i16
lda.l SVActor_MetaData+1280+SVActor_MetaStage
cmp #0
    beq SourcePeerIdle_G205
    brl SourcePeerIdle_Done
SourcePeerIdle_G205:
.a16
.i16
lda.l SVActor_MetaData+1280+4
cmp #278
    beq SourcePeerIdle_G212
    brl SourcePeerIdle_Done
SourcePeerIdle_G212:
.a16
.i16
lda.l $7E0A85+CHAR_HP
and #255
cmp #0
    bne SourcePeerIdle_G219
    brl SourcePeerIdle_Done
SourcePeerIdle_G219:
.a16
.i16
lda.l $7E0A85+CHAR_INPUT_DRIVEN
and #255
cmp #1
    beq SourcePeerIdle_G227
    brl SourcePeerIdle_Done
SourcePeerIdle_G227:
.a16
.i16
lda.l $7E0A85+CHAR_ROSTER_INDEX
and #255
cmp #22
    beq SourcePeerIdle_G235
    brl SourcePeerIdle_Done
SourcePeerIdle_G235:
.a16
.i16
lda.l $7E0A85+CHAR_MAP_INDEX
and #255
cmp #0
    beq SourcePeerIdle_G243
    brl SourcePeerIdle_Done
SourcePeerIdle_G243:
.a16
.i16
lda.l $7E0A85+CHAR_SELECTED
and #255
cmp #3
    bcc SourcePeerIdle_G251
    brl SourcePeerIdle_Done
SourcePeerIdle_G251:
.a16
.i16
SourcePeerIdle_Copy:
.a16
.i16
    lda #0
    sta.l SVActor_MetaData+1280+SVActor_MetaValid
    ldx #(SVActor_MetaData & $FFFF)
    ldy #((SVActor_MetaData+1280) & $FFFF)
    lda #187
    mvn $43,$43
    lda #0
    sta.l SVActor_MetaData+1280+SVActor_MetaStage
    lda #1
    sta.l SVActor_MetaData+1280+SVActor_MetaValid
SourcePeerIdle_Copied:
.a16
.i16
SourcePeerIdle_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    jml SourcePeerIdle_CaptureReturn
SourcePeerIdle_End:
