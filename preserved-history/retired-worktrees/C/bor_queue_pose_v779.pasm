
; Foreground queue snapshot owns CopyBusy and has no live overlapping row.
; Replace only the already-adopted twenty player sprites, not NPCs. Thus
; the actual normal queued image, metadata and existing normal ACK agree.
.bank 39
.org $A000
SourceQueuePose_Prepare:
.a16
.i16
    jsl SourcePacket_PrepareGeometry
    php
    jsl SourceQueuePose_Graft
    plp
    rtl
SourceQueuePose_Graft:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    cld
    lda.l SourcePacket_CopyBusy
    cmp #1
    beq SourceQueuePose_Scope0
    brl SourceQueuePose_No
SourceQueuePose_Scope0:
.a16
.i16
    lda.l SourcePacket_MainRetryNeeded
    cmp #0
    beq SourceQueuePose_Scope1
    brl SourceQueuePose_No
SourceQueuePose_Scope1:
.a16
.i16
    lda.l Game_CampaignId
    cmp #3
    beq SourceQueuePose_Scope2
    brl SourceQueuePose_No
SourceQueuePose_Scope2:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceQueuePose_Scope3
    brl SourceQueuePose_No
SourceQueuePose_Scope3:
.a16
.i16
    lda.l Screen_PosX
    cmp #0
    beq SourceQueuePose_Scope4
    brl SourceQueuePose_No
SourceQueuePose_Scope4:
.a16
.i16
    lda.l SourceAttackOwned_InitMagic
    cmp #45175
    beq SourceQueuePose_Scope5
    brl SourceQueuePose_No
SourceQueuePose_Scope5:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    cmp #0
    beq SourceQueuePose_Scope6
    brl SourceQueuePose_No
SourceQueuePose_Scope6:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #2
    beq SourceQueuePose_Scope7
    brl SourceQueuePose_No
SourceQueuePose_Scope7:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    cmp #1
    beq SourceQueuePose_Scope8
    brl SourceQueuePose_No
SourceQueuePose_Scope8:
.a16
.i16
    lda.l $437A96
    cmp #3
    beq SourceQueuePose_Scope9
    brl SourceQueuePose_No
SourceQueuePose_Scope9:
.a16
.i16
    lda.l $437A9A
    cmp #3
    beq SourceQueuePose_Scope10
    brl SourceQueuePose_No
SourceQueuePose_Scope10:
.a16
.i16
    lda.l $437A9C
    cmp #3
    beq SourceQueuePose_Scope11
    brl SourceQueuePose_No
SourceQueuePose_Scope11:
.a16
.i16
    lda.l $437BC0
    cmp #30248
    beq SourceQueuePose_Scope12
    brl SourceQueuePose_No
SourceQueuePose_Scope12:
.a16
.i16
    lda.l $434E7E
    cmp #19792
    beq SourceQueuePose_Scope13
    brl SourceQueuePose_No
SourceQueuePose_Scope13:
.a16
.i16
    lda.l $434E9A
    cmp #0
    beq SourceQueuePose_Scope14
    brl SourceQueuePose_No
SourceQueuePose_Scope14:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceQueuePose_Scope15
    brl SourceQueuePose_No
SourceQueuePose_Scope15:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceQueuePose_Scope16
    brl SourceQueuePose_No
SourceQueuePose_Scope16:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceQueuePose_Scope17
    brl SourceQueuePose_No
SourceQueuePose_Scope17:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceQueuePose_Scope18
    brl SourceQueuePose_No
SourceQueuePose_Scope18:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceQueuePose_Scope19
    brl SourceQueuePose_No
SourceQueuePose_Scope19:
.a16
.i16
    lda.l SourceVisual_CompletedCommitRetire
    cmp #0
    beq SourceQueuePose_Scope20
    brl SourceQueuePose_No
SourceQueuePose_Scope20:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    cmp #534
    beq SourceQueuePose_Scope21
    brl SourceQueuePose_No
SourceQueuePose_Scope21:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+2
    cmp #0
    beq SourceQueuePose_Scope22
    brl SourceQueuePose_No
SourceQueuePose_Scope22:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceQueuePose_Scope23
    brl SourceQueuePose_No
SourceQueuePose_Scope23:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceQueuePose_Scope24
    brl SourceQueuePose_No
SourceQueuePose_Scope24:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceQueuePose_Scope25
    brl SourceQueuePose_No
SourceQueuePose_Scope25:
.a16
.i16
    lda.l SVActor_Data
    cmp #534
    beq SourceQueuePose_Scope26
    brl SourceQueuePose_No
SourceQueuePose_Scope26:
.a16
.i16
    lda.l SVActor_Data+2
    cmp #0
    beq SourceQueuePose_Scope27
    brl SourceQueuePose_No
SourceQueuePose_Scope27:
.a16
.i16
    lda.l $435380
    cmp #0
    beq SourceQueuePose_Scope28
    brl SourceQueuePose_No
SourceQueuePose_Scope28:
.a16
.i16
    lda.l $4353A2
    cmp #80
    beq SourceQueuePose_Scope29
    brl SourceQueuePose_No
SourceQueuePose_Scope29:
.a16
.i16
    lda.l $435390
    cmp #1
    beq SourceQueuePose_Scope30
    brl SourceQueuePose_No
SourceQueuePose_Scope30:
.a16
.i16
    lda.l $4353B0
    cmp #1
    beq SourceQueuePose_Scope31
    brl SourceQueuePose_No
SourceQueuePose_Scope31:
.a16
.i16
    lda.l $435382
    cmp.l $4353A0
    beq SourceQueuePose_Contiguous
    brl SourceQueuePose_No
SourceQueuePose_Contiguous:
    cmp #4
    bcs SourceQueuePose_Nonempty
    brl SourceQueuePose_No
SourceQueuePose_Nonempty:
    cmp #77
    bcc SourceQueuePose_Bounded
    brl SourceQueuePose_No
SourceQueuePose_Bounded:
    and #3
    beq SourceQueuePose_Aligned
    brl SourceQueuePose_No
SourceQueuePose_Aligned:
    lda.l $43538C
    cmp #$716
    beq SourceQueuePose_Stale
    lda.l $4353AC
    cmp #$716
    beq SourceQueuePose_Stale
    brl SourceQueuePose_No
SourceQueuePose_Stale:
    lda.l $434E7C
    pha
    and #1
    beq SourceQueuePose_Even
    brl SourceQueuePose_PopNo
SourceQueuePose_Even:
    lda.l $434E3C
    cmp #0
    beq SourceQueuePose_Live0
    brl SourceQueuePose_PopNo
SourceQueuePose_Live0:
.a16
.i16
    lda.l $434E60
    cmp #0
    beq SourceQueuePose_Live1
    brl SourceQueuePose_PopNo
SourceQueuePose_Live1:
.a16
.i16
    lda.l $7E0A0B
    and #255
    cmp #0
    beq SourceQueuePose_Live2
    brl SourceQueuePose_PopNo
SourceQueuePose_Live2:
.a16
.i16
    lda.l $7E0A43
    cmp #0
    beq SourceQueuePose_Live3
    brl SourceQueuePose_PopNo
SourceQueuePose_Live3:
.a16
.i16
    lda.l $7E0A23
    and #255
    cmp #0
    bne SourceQueuePose_Live4
    brl SourceQueuePose_PopNo
SourceQueuePose_Live4:
.a16
.i16
    lda.l $7E0A0F
    and #255
    cmp #1
    beq SourceQueuePose_Live5
    brl SourceQueuePose_PopNo
SourceQueuePose_Live5:
.a16
.i16
    lda.l $7E0A0C
    and #255
    cmp #22
    beq SourceQueuePose_Live6
    brl SourceQueuePose_PopNo
SourceQueuePose_Live6:
.a16
.i16
    lda.l $7E0A90
    and #255
    cmp #0
    beq SourceQueuePose_Live7
    brl SourceQueuePose_PopNo
SourceQueuePose_Live7:
.a16
.i16
    lda.l $7E0AC8
    cmp #0
    beq SourceQueuePose_Live8
    brl SourceQueuePose_PopNo
SourceQueuePose_Live8:
.a16
.i16
    lda.l $7E0AA8
    and #255
    cmp #0
    bne SourceQueuePose_Live9
    brl SourceQueuePose_PopNo
SourceQueuePose_Live9:
.a16
.i16
    lda.l $7E0A94
    and #255
    cmp #1
    beq SourceQueuePose_Live10
    brl SourceQueuePose_PopNo
SourceQueuePose_Live10:
.a16
.i16
    lda.l $7E0A91
    and #255
    cmp #22
    beq SourceQueuePose_Live11
    brl SourceQueuePose_PopNo
SourceQueuePose_Live11:
.a16
.i16
    jsl SourceStandby_FaceLive
    bcs SourceQueuePose_Copy
    brl SourceQueuePose_PopNo
SourceQueuePose_Copy:
    lda.l $437600
    sta.l $435120
    sta.l $434F00
    lda.l $437602
    sta.l $435122
    sta.l $434F02
    lda.l $437604
    sta.l $435124
    sta.l $434F04
    lda.l $437606
    sta.l $435126
    sta.l $434F06
    lda.l $437608
    sta.l $435128
    sta.l $434F08
    lda.l $43760A
    sta.l $43512A
    sta.l $434F0A
    lda.l $43760C
    sta.l $43512C
    sta.l $434F0C
    lda.l $43760E
    sta.l $43512E
    sta.l $434F0E
    lda.l $437610
    sta.l $435130
    sta.l $434F10
    lda.l $437612
    sta.l $435132
    sta.l $434F12
    lda.l $437614
    sta.l $435134
    sta.l $434F14
    lda.l $437616
    sta.l $435136
    sta.l $434F16
    lda.l $437618
    sta.l $435138
    sta.l $434F18
    lda.l $43761A
    sta.l $43513A
    sta.l $434F1A
    lda.l $43761C
    sta.l $43513C
    sta.l $434F1C
    lda.l $43761E
    sta.l $43513E
    sta.l $434F1E
    lda.l $437620
    sta.l $435140
    sta.l $434F20
    lda.l $437622
    sta.l $435142
    sta.l $434F22
    lda.l $437624
    sta.l $435144
    sta.l $434F24
    lda.l $437626
    sta.l $435146
    sta.l $434F26
    lda.l $437628
    sta.l $435148
    sta.l $434F28
    lda.l $43762A
    sta.l $43514A
    sta.l $434F2A
    lda.l $43762C
    sta.l $43514C
    sta.l $434F2C
    lda.l $43762E
    sta.l $43514E
    sta.l $434F2E
    lda.l $437630
    sta.l $435150
    sta.l $434F30
    lda.l $437632
    sta.l $435152
    sta.l $434F32
    lda.l $437634
    sta.l $435154
    sta.l $434F34
    lda.l $437636
    sta.l $435156
    sta.l $434F36
    lda.l $437638
    sta.l $435158
    sta.l $434F38
    lda.l $43763A
    sta.l $43515A
    sta.l $434F3A
    lda.l $43763C
    sta.l $43515C
    sta.l $434F3C
    lda.l $43763E
    sta.l $43515E
    sta.l $434F3E
    lda.l $437640
    sta.l $435160
    sta.l $434F40
    lda.l $437642
    sta.l $435162
    sta.l $434F42
    lda.l $437644
    sta.l $435164
    sta.l $434F44
    lda.l $437646
    sta.l $435166
    sta.l $434F46
    lda.l $437648
    sta.l $435168
    sta.l $434F48
    lda.l $43764A
    sta.l $43516A
    sta.l $434F4A
    lda.l $43764C
    sta.l $43516C
    sta.l $434F4C
    lda.l $43764E
    sta.l $43516E
    sta.l $434F4E
    sep #$20
.a8
    lda.l $437800
    sta.l $435320
    sta.l $435100
    lda.l $437801
    sta.l $435321
    sta.l $435101
    lda.l $437802
    sta.l $435322
    sta.l $435102
    lda.l $437803
    sta.l $435323
    sta.l $435103
    lda.l $437804
    sta.l $435324
    sta.l $435104
    rep #$20
.a16
    lda.l $437820
    and #1
    beq SourceQueuePose_Pos0
    lda.l $437600
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed0
SourceQueuePose_Pos0:
.a16
.i16
    lda.l $437600
    and #255
SourceQueuePose_Signed0:
.a16
.i16
    sta.l $435600
    lda.l $437821
    and #1
    beq SourceQueuePose_Pos1
    lda.l $437604
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed1
SourceQueuePose_Pos1:
.a16
.i16
    lda.l $437604
    and #255
SourceQueuePose_Signed1:
.a16
.i16
    sta.l $435604
    lda.l $437822
    and #1
    beq SourceQueuePose_Pos2
    lda.l $437608
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed2
SourceQueuePose_Pos2:
.a16
.i16
    lda.l $437608
    and #255
SourceQueuePose_Signed2:
.a16
.i16
    sta.l $435608
    lda.l $437823
    and #1
    beq SourceQueuePose_Pos3
    lda.l $43760C
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed3
SourceQueuePose_Pos3:
.a16
.i16
    lda.l $43760C
    and #255
SourceQueuePose_Signed3:
.a16
.i16
    sta.l $43560C
    lda.l $437824
    and #1
    beq SourceQueuePose_Pos4
    lda.l $437610
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed4
SourceQueuePose_Pos4:
.a16
.i16
    lda.l $437610
    and #255
SourceQueuePose_Signed4:
.a16
.i16
    sta.l $435610
    lda.l $437825
    and #1
    beq SourceQueuePose_Pos5
    lda.l $437614
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed5
SourceQueuePose_Pos5:
.a16
.i16
    lda.l $437614
    and #255
SourceQueuePose_Signed5:
.a16
.i16
    sta.l $435614
    lda.l $437826
    and #1
    beq SourceQueuePose_Pos6
    lda.l $437618
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed6
SourceQueuePose_Pos6:
.a16
.i16
    lda.l $437618
    and #255
SourceQueuePose_Signed6:
.a16
.i16
    sta.l $435618
    lda.l $437827
    and #1
    beq SourceQueuePose_Pos7
    lda.l $43761C
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed7
SourceQueuePose_Pos7:
.a16
.i16
    lda.l $43761C
    and #255
SourceQueuePose_Signed7:
.a16
.i16
    sta.l $43561C
    lda.l $437828
    and #1
    beq SourceQueuePose_Pos8
    lda.l $437620
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed8
SourceQueuePose_Pos8:
.a16
.i16
    lda.l $437620
    and #255
SourceQueuePose_Signed8:
.a16
.i16
    sta.l $435620
    lda.l $437829
    and #1
    beq SourceQueuePose_Pos9
    lda.l $437624
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed9
SourceQueuePose_Pos9:
.a16
.i16
    lda.l $437624
    and #255
SourceQueuePose_Signed9:
.a16
.i16
    sta.l $435624
    lda.l $43782A
    and #1
    beq SourceQueuePose_Pos10
    lda.l $437628
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed10
SourceQueuePose_Pos10:
.a16
.i16
    lda.l $437628
    and #255
SourceQueuePose_Signed10:
.a16
.i16
    sta.l $435628
    lda.l $43782B
    and #1
    beq SourceQueuePose_Pos11
    lda.l $43762C
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed11
SourceQueuePose_Pos11:
.a16
.i16
    lda.l $43762C
    and #255
SourceQueuePose_Signed11:
.a16
.i16
    sta.l $43562C
    lda.l $43782C
    and #1
    beq SourceQueuePose_Pos12
    lda.l $437630
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed12
SourceQueuePose_Pos12:
.a16
.i16
    lda.l $437630
    and #255
SourceQueuePose_Signed12:
.a16
.i16
    sta.l $435630
    lda.l $43782D
    and #1
    beq SourceQueuePose_Pos13
    lda.l $437634
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed13
SourceQueuePose_Pos13:
.a16
.i16
    lda.l $437634
    and #255
SourceQueuePose_Signed13:
.a16
.i16
    sta.l $435634
    lda.l $43782E
    and #1
    beq SourceQueuePose_Pos14
    lda.l $437638
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed14
SourceQueuePose_Pos14:
.a16
.i16
    lda.l $437638
    and #255
SourceQueuePose_Signed14:
.a16
.i16
    sta.l $435638
    lda.l $43782F
    and #1
    beq SourceQueuePose_Pos15
    lda.l $43763C
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed15
SourceQueuePose_Pos15:
.a16
.i16
    lda.l $43763C
    and #255
SourceQueuePose_Signed15:
.a16
.i16
    sta.l $43563C
    lda.l $437830
    and #1
    beq SourceQueuePose_Pos16
    lda.l $437640
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed16
SourceQueuePose_Pos16:
.a16
.i16
    lda.l $437640
    and #255
SourceQueuePose_Signed16:
.a16
.i16
    sta.l $435640
    lda.l $437831
    and #1
    beq SourceQueuePose_Pos17
    lda.l $437644
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed17
SourceQueuePose_Pos17:
.a16
.i16
    lda.l $437644
    and #255
SourceQueuePose_Signed17:
.a16
.i16
    sta.l $435644
    lda.l $437832
    and #1
    beq SourceQueuePose_Pos18
    lda.l $437648
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed18
SourceQueuePose_Pos18:
.a16
.i16
    lda.l $437648
    and #255
SourceQueuePose_Signed18:
.a16
.i16
    sta.l $435648
    lda.l $437833
    and #1
    beq SourceQueuePose_Pos19
    lda.l $43764C
    and #255
    ora #$FF00
    bra SourceQueuePose_Signed19
SourceQueuePose_Pos19:
.a16
.i16
    lda.l $43764C
    and #255
SourceQueuePose_Signed19:
.a16
.i16
    sta.l $43564C
    lda #0
    sta.l $435380
    sta.l $435340
    lda #40
    sta.l $435382
    sta.l $435342
    lda.l $43740E
    clc
    adc.l SourceAttackOwned_Delta0
    sta.l $435384
    sta.l $435344
    lda.l $437410
    sta.l $435386
    sta.l $435346
    lda #22
    sta.l $435388
    sta.l $435348
    lda #0
    sta.l $43538A
    sta.l $43534A
    lda #$216
    sta.l $43538C
    sta.l $43534C
    lda #0
    sta.l $43538E
    sta.l $43534E
    lda #1
    sta.l $435390
    sta.l $435350
    lda.l $437414
    sta.l $435392
    sta.l $435352
    lda.l SourceVisual_CompletedEntry+4
    sta.l $435394
    sta.l $435354
    lda.l SourceVisual_CompletedEntry+8
    sta.l $435396
    sta.l $435356
    lda #0
    sta.l $435398
    sta.l $435358
    lda #0
    sta.l $43539A
    sta.l $43535A
    lda #0
    sta.l $43539C
    sta.l $43535C
    lda #0
    sta.l $43539E
    sta.l $43535E
    lda #40
    sta.l $4353A0
    sta.l $435360
    lda #80
    sta.l $4353A2
    sta.l $435362
    lda.l $43748E
    clc
    adc.l SourceAttackOwned_Delta1
    sta.l $4353A4
    sta.l $435364
    lda.l $437490
    sta.l $4353A6
    sta.l $435366
    lda #22
    sta.l $4353A8
    sta.l $435368
    lda #0
    sta.l $4353AA
    sta.l $43536A
    lda #$216
    sta.l $4353AC
    sta.l $43536C
    lda #0
    sta.l $4353AE
    sta.l $43536E
    lda #1
    sta.l $4353B0
    sta.l $435370
    lda.l $437494
    sta.l $4353B2
    sta.l $435372
    lda.l SVActor_Data+4
    sta.l $4353B4
    sta.l $435374
    lda.l SVActor_Data+8
    sta.l $4353B6
    sta.l $435376
    lda #0
    sta.l $4353B8
    sta.l $435378
    lda #0
    sta.l $4353BA
    sta.l $43537A
    lda #0
    sta.l $4353BC
    sta.l $43537C
    lda #0
    sta.l $4353BE
    sta.l $43537E
    ; Linearization: reject enqueue if producer moved during the copy.
    jsl SourceStandby_FaceLive
    bcc SourceQueuePose_Raced
    lda.l $434E7C
    cmp $01,s
    bne SourceQueuePose_Raced
    pla
    ply
    plx
    pla
    plp
    sec
    rtl
SourceQueuePose_Raced:
    lda #1
    sta.l SourcePacket_MainRetryNeeded
    lda #0
    sta.l SourcePacket_ActiveValid
SourceQueuePose_PopNo:
    pla
SourceQueuePose_No:
    ply
    plx
    pla
    plp
    clc
    rtl
SourceQueuePose_End:
.assert * <= $27C000, "foreground queue pose exceeds blank ROM"
