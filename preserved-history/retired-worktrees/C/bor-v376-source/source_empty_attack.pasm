; Exact lowest-empty selection, scoped only for timing to the first attack.
; No cursor, summary, resource policy or ownership change. Ordinary full scan
; and victim fallback remain in their original code and original bank.
SourceEmpty_Dispatch:
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockScan
    lda.l SourceVisual_Key
    cmp #$0216
    bne SourceEmpty_Original
    lda.l SourceVisual_EntryIndexSaved
    cmp #781
    bne SourceEmpty_Original
    jml SourceEmpty_Row0
SourceEmpty_Original:
.a16
.i16
    jml SourceVisual_AllocateBlock__empty
SourceEmpty_Row0:
.a16
.i16
    lda.l SourceVisual_BlockCache+2
    bne SourceEmpty_Row1
    lda #0
    sta.l SourceVisual_BlockScan
    ldx #0
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row1:
.a16
.i16
    lda.l SourceVisual_BlockCache+10
    bne SourceEmpty_Row2
    lda #1
    sta.l SourceVisual_BlockScan
    ldx #8
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row2:
.a16
.i16
    lda.l SourceVisual_BlockCache+18
    bne SourceEmpty_Row3
    lda #2
    sta.l SourceVisual_BlockScan
    ldx #16
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row3:
.a16
.i16
    lda.l SourceVisual_BlockCache+26
    bne SourceEmpty_Row4
    lda #3
    sta.l SourceVisual_BlockScan
    ldx #24
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row4:
.a16
.i16
    lda.l SourceVisual_BlockCache+34
    bne SourceEmpty_Row5
    lda #4
    sta.l SourceVisual_BlockScan
    ldx #32
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row5:
.a16
.i16
    lda.l SourceVisual_BlockCache+42
    bne SourceEmpty_Row6
    lda #5
    sta.l SourceVisual_BlockScan
    ldx #40
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row6:
.a16
.i16
    lda.l SourceVisual_BlockCache+50
    bne SourceEmpty_Row7
    lda #6
    sta.l SourceVisual_BlockScan
    ldx #48
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row7:
.a16
.i16
    lda.l SourceVisual_BlockCache+58
    bne SourceEmpty_Row8
    lda #7
    sta.l SourceVisual_BlockScan
    ldx #56
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row8:
.a16
.i16
    lda.l SourceVisual_BlockCache+66
    bne SourceEmpty_Row9
    lda #8
    sta.l SourceVisual_BlockScan
    ldx #64
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row9:
.a16
.i16
    lda.l SourceVisual_BlockCache+74
    bne SourceEmpty_Row10
    lda #9
    sta.l SourceVisual_BlockScan
    ldx #72
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row10:
.a16
.i16
    lda.l SourceVisual_BlockCache+82
    bne SourceEmpty_Row11
    lda #10
    sta.l SourceVisual_BlockScan
    ldx #80
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row11:
.a16
.i16
    lda.l SourceVisual_BlockCache+90
    bne SourceEmpty_Row12
    lda #11
    sta.l SourceVisual_BlockScan
    ldx #88
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row12:
.a16
.i16
    lda.l SourceVisual_BlockCache+98
    bne SourceEmpty_Row13
    lda #12
    sta.l SourceVisual_BlockScan
    ldx #96
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row13:
.a16
.i16
    lda.l SourceVisual_BlockCache+106
    bne SourceEmpty_Row14
    lda #13
    sta.l SourceVisual_BlockScan
    ldx #104
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row14:
.a16
.i16
    lda.l SourceVisual_BlockCache+114
    bne SourceEmpty_Row15
    lda #14
    sta.l SourceVisual_BlockScan
    ldx #112
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row15:
.a16
.i16
    lda.l SourceVisual_BlockCache+122
    bne SourceEmpty_Row16
    lda #15
    sta.l SourceVisual_BlockScan
    ldx #120
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row16:
.a16
.i16
    lda.l SourceVisual_BlockCache+130
    bne SourceEmpty_Row17
    lda #16
    sta.l SourceVisual_BlockScan
    ldx #128
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row17:
.a16
.i16
    lda.l SourceVisual_BlockCache+138
    bne SourceEmpty_Row18
    lda #17
    sta.l SourceVisual_BlockScan
    ldx #136
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row18:
.a16
.i16
    lda.l SourceVisual_BlockCache+146
    bne SourceEmpty_Row19
    lda #18
    sta.l SourceVisual_BlockScan
    ldx #144
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row19:
.a16
.i16
    lda.l SourceVisual_BlockCache+154
    bne SourceEmpty_Row20
    lda #19
    sta.l SourceVisual_BlockScan
    ldx #152
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row20:
.a16
.i16
    lda.l SourceVisual_BlockCache+162
    bne SourceEmpty_Row21
    lda #20
    sta.l SourceVisual_BlockScan
    ldx #160
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row21:
.a16
.i16
    lda.l SourceVisual_BlockCache+170
    bne SourceEmpty_Row22
    lda #21
    sta.l SourceVisual_BlockScan
    ldx #168
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row22:
.a16
.i16
    lda.l SourceVisual_BlockCache+178
    bne SourceEmpty_Row23
    lda #22
    sta.l SourceVisual_BlockScan
    ldx #176
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row23:
.a16
.i16
    lda.l SourceVisual_BlockCache+186
    bne SourceEmpty_Row24
    lda #23
    sta.l SourceVisual_BlockScan
    ldx #184
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row24:
.a16
.i16
    lda.l SourceVisual_BlockCache+194
    bne SourceEmpty_Row25
    lda #24
    sta.l SourceVisual_BlockScan
    ldx #192
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row25:
.a16
.i16
    lda.l SourceVisual_BlockCache+202
    bne SourceEmpty_Row26
    lda #25
    sta.l SourceVisual_BlockScan
    ldx #200
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row26:
.a16
.i16
    lda.l SourceVisual_BlockCache+210
    bne SourceEmpty_Row27
    lda #26
    sta.l SourceVisual_BlockScan
    ldx #208
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row27:
.a16
.i16
    lda.l SourceVisual_BlockCache+218
    bne SourceEmpty_Row28
    lda #27
    sta.l SourceVisual_BlockScan
    ldx #216
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row28:
.a16
.i16
    lda.l SourceVisual_BlockCache+226
    bne SourceEmpty_Row29
    lda #28
    sta.l SourceVisual_BlockScan
    ldx #224
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row29:
.a16
.i16
    lda.l SourceVisual_BlockCache+234
    bne SourceEmpty_Row30
    lda #29
    sta.l SourceVisual_BlockScan
    ldx #232
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row30:
.a16
.i16
    lda.l SourceVisual_BlockCache+242
    bne SourceEmpty_Row31
    lda #30
    sta.l SourceVisual_BlockScan
    ldx #240
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row31:
.a16
.i16
    lda.l SourceVisual_BlockCache+250
    bne SourceEmpty_Row32
    lda #31
    sta.l SourceVisual_BlockScan
    ldx #248
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row32:
.a16
.i16
    lda.l SourceVisual_BlockCache+258
    bne SourceEmpty_Row33
    lda #32
    sta.l SourceVisual_BlockScan
    ldx #256
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row33:
.a16
.i16
    lda.l SourceVisual_BlockCache+266
    bne SourceEmpty_Row34
    lda #33
    sta.l SourceVisual_BlockScan
    ldx #264
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row34:
.a16
.i16
    lda.l SourceVisual_BlockCache+274
    bne SourceEmpty_Row35
    lda #34
    sta.l SourceVisual_BlockScan
    ldx #272
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row35:
.a16
.i16
    lda.l SourceVisual_BlockCache+282
    bne SourceEmpty_Row36
    lda #35
    sta.l SourceVisual_BlockScan
    ldx #280
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row36:
.a16
.i16
    lda.l SourceVisual_BlockCache+290
    bne SourceEmpty_Row37
    lda #36
    sta.l SourceVisual_BlockScan
    ldx #288
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row37:
.a16
.i16
    lda.l SourceVisual_BlockCache+298
    bne SourceEmpty_Row38
    lda #37
    sta.l SourceVisual_BlockScan
    ldx #296
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row38:
.a16
.i16
    lda.l SourceVisual_BlockCache+306
    bne SourceEmpty_Row39
    lda #38
    sta.l SourceVisual_BlockScan
    ldx #304
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row39:
.a16
.i16
    lda.l SourceVisual_BlockCache+314
    bne SourceEmpty_Row40
    lda #39
    sta.l SourceVisual_BlockScan
    ldx #312
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row40:
.a16
.i16
    lda.l SourceVisual_BlockCache+322
    bne SourceEmpty_Row41
    lda #40
    sta.l SourceVisual_BlockScan
    ldx #320
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row41:
.a16
.i16
    lda.l SourceVisual_BlockCache+330
    bne SourceEmpty_Row42
    lda #41
    sta.l SourceVisual_BlockScan
    ldx #328
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row42:
.a16
.i16
    lda.l SourceVisual_BlockCache+338
    bne SourceEmpty_Row43
    lda #42
    sta.l SourceVisual_BlockScan
    ldx #336
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row43:
.a16
.i16
    lda.l SourceVisual_BlockCache+346
    bne SourceEmpty_Row44
    lda #43
    sta.l SourceVisual_BlockScan
    ldx #344
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row44:
.a16
.i16
    lda.l SourceVisual_BlockCache+354
    bne SourceEmpty_Row45
    lda #44
    sta.l SourceVisual_BlockScan
    ldx #352
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row45:
.a16
.i16
    lda.l SourceVisual_BlockCache+362
    bne SourceEmpty_Row46
    lda #45
    sta.l SourceVisual_BlockScan
    ldx #360
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row46:
.a16
.i16
    lda.l SourceVisual_BlockCache+370
    bne SourceEmpty_Row47
    lda #46
    sta.l SourceVisual_BlockScan
    ldx #368
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row47:
.a16
.i16
    lda.l SourceVisual_BlockCache+378
    bne SourceEmpty_Row48
    lda #47
    sta.l SourceVisual_BlockScan
    ldx #376
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row48:
.a16
.i16
    lda.l SourceVisual_BlockCache+386
    bne SourceEmpty_Row49
    lda #48
    sta.l SourceVisual_BlockScan
    ldx #384
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row49:
.a16
.i16
    lda.l SourceVisual_BlockCache+394
    bne SourceEmpty_Row50
    lda #49
    sta.l SourceVisual_BlockScan
    ldx #392
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row50:
.a16
.i16
    lda.l SourceVisual_BlockCache+402
    bne SourceEmpty_Row51
    lda #50
    sta.l SourceVisual_BlockScan
    ldx #400
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row51:
.a16
.i16
    lda.l SourceVisual_BlockCache+410
    bne SourceEmpty_Row52
    lda #51
    sta.l SourceVisual_BlockScan
    ldx #408
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row52:
.a16
.i16
    lda.l SourceVisual_BlockCache+418
    bne SourceEmpty_Row53
    lda #52
    sta.l SourceVisual_BlockScan
    ldx #416
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row53:
.a16
.i16
    lda.l SourceVisual_BlockCache+426
    bne SourceEmpty_Row54
    lda #53
    sta.l SourceVisual_BlockScan
    ldx #424
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row54:
.a16
.i16
    lda.l SourceVisual_BlockCache+434
    bne SourceEmpty_Row55
    lda #54
    sta.l SourceVisual_BlockScan
    ldx #432
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row55:
.a16
.i16
    lda.l SourceVisual_BlockCache+442
    bne SourceEmpty_Row56
    lda #55
    sta.l SourceVisual_BlockScan
    ldx #440
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row56:
.a16
.i16
    lda.l SourceVisual_BlockCache+450
    bne SourceEmpty_Row57
    lda #56
    sta.l SourceVisual_BlockScan
    ldx #448
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row57:
.a16
.i16
    lda.l SourceVisual_BlockCache+458
    bne SourceEmpty_Row58
    lda #57
    sta.l SourceVisual_BlockScan
    ldx #456
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row58:
.a16
.i16
    lda.l SourceVisual_BlockCache+466
    bne SourceEmpty_Row59
    lda #58
    sta.l SourceVisual_BlockScan
    ldx #464
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row59:
.a16
.i16
    lda.l SourceVisual_BlockCache+474
    bne SourceEmpty_Row60
    lda #59
    sta.l SourceVisual_BlockScan
    ldx #472
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row60:
.a16
.i16
    lda.l SourceVisual_BlockCache+482
    bne SourceEmpty_Row61
    lda #60
    sta.l SourceVisual_BlockScan
    ldx #480
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row61:
.a16
.i16
    lda.l SourceVisual_BlockCache+490
    bne SourceEmpty_Row62
    lda #61
    sta.l SourceVisual_BlockScan
    ldx #488
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row62:
.a16
.i16
    lda.l SourceVisual_BlockCache+498
    bne SourceEmpty_Row63
    lda #62
    sta.l SourceVisual_BlockScan
    ldx #496
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row63:
.a16
.i16
    lda.l SourceVisual_BlockCache+506
    bne SourceEmpty_Row64
    lda #63
    sta.l SourceVisual_BlockScan
    ldx #504
    clc
    lda #0
    jml SourceVisual_AllocateBlock__claim
SourceEmpty_Row64:
.a16
.i16
    lda #64
    sta.l SourceVisual_BlockScan
    ldx #504
    cmp #64
    jml SourceEmpty_OriginalFullScan
SourceEmpty_End:
