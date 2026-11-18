; Read-only scene/request/source-world coherence gate. No publication.
; A=player0/1. Prepared($4E46) compares saved old scene metadata;
; committed($4E47) compares the candidate metadata already installed.
SourceNextLive_Check:
.a16
.i16
php
rep #$30
cld
pha
phx
phy
phb
phd
cmp #2
bcc SourceNextLive_Slot
brl SourceNextLive_NoEarly
SourceNextLive_Slot:
.a16
.i16
tax
lda #0
pha
pha
pha
pha
pha
pha
pha
pha
pha
txa
sta 11,s
xba
asl a
asl a
sta 1,s
tax
lda.l SourceNextFrame_Base,x
sta 17,s
cmp #$4E46
beq SourceNextLive_Stage
cmp #$4E47
beq SourceNextLive_Guard1
brl SourceNextLive_No
SourceNextLive_Guard1:
.a16
.i16
SourceNextLive_Stage:
.a16
.i16
lda.l SourceNextFrame_Base+2,x
cmp 11,s
beq SourceNextLive_Guard2
brl SourceNextLive_No
SourceNextLive_Guard2:
.a16
.i16
lda.l Game_CampaignId
and #255
cmp #3
beq SourceNextLive_Guard3
brl SourceNextLive_No
SourceNextLive_Guard3:
.a16
.i16
lda.l Game_State
cmp #0
beq SourceNextLive_Guard4
brl SourceNextLive_No
SourceNextLive_Guard4:
.a16
.i16
lda.l Game_StageIndex
cmp #0
beq SourceNextLive_Guard5
brl SourceNextLive_No
SourceNextLive_Guard5:
.a16
.i16
lda.l $7E175E
cmp #2
beq SourceNextLive_Guard6
brl SourceNextLive_No
SourceNextLive_Guard6:
.a16
.i16
lda.l $7E1760
cmp #1
beq SourceNextLive_Guard7
brl SourceNextLive_No
SourceNextLive_Guard7:
.a16
.i16
lda.l $7E46DC
cmp #1
beq SourceNextLive_Guard8
brl SourceNextLive_No
SourceNextLive_Guard8:
.a16
.i16
lda.l SourceInput_Magic
cmp #6752
beq SourceNextLive_Guard9
brl SourceNextLive_No
SourceNextLive_Guard9:
.a16
.i16
lda.l SVActor_Magic
cmp #44057
beq SourceNextLive_Guard10
brl SourceNextLive_No
SourceNextLive_Guard10:
.a16
.i16
lda.l SourceVisual_CompletedMagic
cmp #49229
beq SourceNextLive_Guard11
brl SourceNextLive_No
SourceNextLive_Guard11:
.a16
.i16
lda.l SourcePacket_ActiveValid
cmp #1
beq SourceNextLive_Guard12
brl SourceNextLive_No
SourceNextLive_Guard12:
.a16
.i16
lda.l SourcePacket_CopyBusy
cmp #0
beq SourceNextLive_Guard13
brl SourceNextLive_No
SourceNextLive_Guard13:
.a16
.i16
lda.l SourceVisual_CompletedPending
cmp #0
beq SourceNextLive_Guard14
brl SourceNextLive_No
SourceNextLive_Guard14:
.a16
.i16
lda.l Oam_UploadFlag
cmp #0
beq SourceNextLive_Guard15
brl SourceNextLive_No
SourceNextLive_Guard15:
.a16
.i16
lda.l SourceNextScene_Magic
cmp #21315
beq SourceNextLive_Guard16
brl SourceNextLive_No
SourceNextLive_Guard16:
.a16
.i16
lda.l $434E7E
cmp #19792
beq SourceNextLive_Guard17
brl SourceNextLive_No
SourceNextLive_Guard17:
.a16
.i16
lda.l $434E2C
cmp #0
beq SourceNextLive_Guard18
brl SourceNextLive_No
SourceNextLive_Guard18:
.a16
.i16
lda.l SourceNextFrame_Base+740,x
cmp #$5343
beq SourceNextLive_Guard19
brl SourceNextLive_No
SourceNextLive_Guard19:
.a16
.i16
lda.l SourceNextFrame_Base+742,x
cmp.l SourceNextScene_Low
beq SourceNextLive_Guard20
brl SourceNextLive_No
SourceNextLive_Guard20:
.a16
.i16
lda.l SourceNextFrame_Base+744,x
cmp.l SourceNextScene_High
beq SourceNextLive_Guard21
brl SourceNextLive_No
SourceNextLive_Guard21:
.a16
.i16
lda.l Screen_PosX
cmp.l SourceNextFrame_Base+6,x
beq SourceNextLive_Guard22
brl SourceNextLive_No
SourceNextLive_Guard22:
.a16
.i16
cmp.l SourcePacket_ActiveCamera
beq SourceNextLive_Guard23
brl SourceNextLive_No
SourceNextLive_Guard23:
.a16
.i16
lda.l SourceNextFrame_Base+8,x
cmp #$0116
beq SourceNextLive_Guard24
brl SourceNextLive_No
SourceNextLive_Guard24:
.a16
.i16
lda.l SourceNextFrame_Base+10,x
and #$FF00
beq SourceNextLive_Guard25
brl SourceNextLive_No
SourceNextLive_Guard25:
.a16
.i16
lda.l SourceNextFrame_Base+624,x
cmp #1
beq SourceNextLive_Guard26
brl SourceNextLive_No
SourceNextLive_Guard26:
.a16
.i16
lda.l SourceNextFrame_Base+620,x
cmp.l SourceNextFrame_Base+8,x
beq SourceNextLive_Guard27
brl SourceNextLive_No
SourceNextLive_Guard27:
.a16
.i16
lda.l SourceNextFrame_Base+622,x
cmp.l SourceNextFrame_Base+10,x
beq SourceNextLive_Guard28
brl SourceNextLive_No
SourceNextLive_Guard28:
.a16
.i16
lda.l SourceNextFrame_Base+626,x
sta 13,s
cmp #2
bcc SourceNextLive_Guard29
brl SourceNextLive_No
SourceNextLive_Guard29:
.a16
.i16
lda.l SourceNextFrame_Base+634,x
sta 15,s
cmp #3
bcc SourceNextLive_Guard30
brl SourceNextLive_No
SourceNextLive_Guard30:
.a16
.i16
lda.l SourceNextFrame_Base+608,x
sta 7,s
and #3
beq SourceNextLive_Guard31
brl SourceNextLive_No
SourceNextLive_Guard31:
.a16
.i16
lda.l SourceNextFrame_Base+610,x
sta 9,s
and #3
beq SourceNextLive_Guard32
brl SourceNextLive_No
SourceNextLive_Guard32:
.a16
.i16
lda 9,s
cmp #513
bcc SourceNextLive_Guard33
brl SourceNextLive_No
SourceNextLive_Guard33:
.a16
.i16
lda 9,s
cmp 7,s
bcs SourceNextLive_Guard34
brl SourceNextLive_No
SourceNextLive_Guard34:
.a16
.i16
lda 7,s
eor #$FFFF
inc a
clc
adc 9,s
cmp #1
bcs SourceNextLive_Guard35
brl SourceNextLive_No
SourceNextLive_Guard35:
.a16
.i16
cmp #65
bcc SourceNextLive_Guard36
brl SourceNextLive_No
SourceNextLive_Guard36:
.a16
.i16
lda 11,s
asl a
asl a
asl a
asl a
asl a
sta 3,s
tay
sep #$20
.a8
lda #$43
pha
plb
rep #$20
.a16
lda.w $5390,y
cmp #1
beq SourceNextLive_Guard37
brl SourceNextLive_No
SourceNextLive_Guard37:
.a16
.i16
lda.w $5380,y
cmp 7,s
beq SourceNextLive_Guard38
brl SourceNextLive_No
SourceNextLive_Guard38:
.a16
.i16
lda.w $5382,y
cmp 9,s
beq SourceNextLive_Guard39
brl SourceNextLive_No
SourceNextLive_Guard39:
.a16
.i16
tya
eor #32
tay
lda.w $5390,y
beq SourceNextLive_NeighborDone
cmp #1
beq SourceNextLive_Guard40
brl SourceNextLive_No
SourceNextLive_Guard40:
.a16
.i16
lda.w $5380,y
and #3
beq SourceNextLive_Guard41
brl SourceNextLive_No
SourceNextLive_Guard41:
.a16
.i16
lda.w $5382,y
and #3
beq SourceNextLive_Guard42
brl SourceNextLive_No
SourceNextLive_Guard42:
.a16
.i16
lda.w $5382,y
cmp #513
bcc SourceNextLive_Guard43
brl SourceNextLive_No
SourceNextLive_Guard43:
.a16
.i16
lda.w $5380,y
cmp.w $5382,y
bcc SourceNextLive_Guard44
brl SourceNextLive_No
SourceNextLive_Guard44:
.a16
.i16
lda.w $5382,y
cmp 7,s
bcc SourceNextLive_NeighborDone
beq SourceNextLive_NeighborDone
lda.w $5380,y
cmp 9,s
bcs SourceNextLive_Guard45
brl SourceNextLive_No
SourceNextLive_Guard45:
.a16
.i16
SourceNextLive_NeighborDone:
.a16
.i16
lda 11,s
beq SourceNextLive_NativeP1
ldx #133
bra SourceNextLive_Native
SourceNextLive_NativeP1:
.a16
.i16
ldx #0
SourceNextLive_Native:
.a16
.i16
lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
and #255
cmp #1
beq SourceNextLive_Guard46
brl SourceNextLive_No
SourceNextLive_Guard46:
.a16
.i16
lda.l $7E0A00+CHAR_ROSTER_INDEX,x
and #255
cmp #22
beq SourceNextLive_Guard47
brl SourceNextLive_No
SourceNextLive_Guard47:
.a16
.i16
lda.l $7E0A00+CHAR_MAP_INDEX,x
and #255
cmp #0
beq SourceNextLive_Guard48
brl SourceNextLive_No
SourceNextLive_Guard48:
.a16
.i16
lda.l $7E0A00+CHAR_HP,x
and #255
bne SourceNextLive_Guard49
brl SourceNextLive_No
SourceNextLive_Guard49:
.a16
.i16
lda.l $7E0A00+CHAR_SELECTED,x
and #255
cmp 15,s
beq SourceNextLive_Guard50
brl SourceNextLive_No
SourceNextLive_Guard50:
.a16
.i16
lda.l $7E0A00+CHAR_FACING_LEFT,x
and #255
cmp 13,s
beq SourceNextLive_Guard51
brl SourceNextLive_No
SourceNextLive_Guard51:
.a16
.i16
lda.l $7E0A00+CHAR_POS_Y,x
sta 7,s
txa
clc
adc #$0A00
pha
lda 3,s
tax
pla
cmp.l SourceNextFrame_Base+738,x
beq SourceNextLive_Guard52
brl SourceNextLive_No
SourceNextLive_Guard52:
.a16
.i16
lda 7,s
cmp.l SourceNextFrame_Base+614,x
beq SourceNextLive_Guard53
brl SourceNextLive_No
SourceNextLive_Guard53:
.a16
.i16
lda.l $434E7C
sta 5,s
and #1
beq SourceNextLive_Guard54
brl SourceNextLive_No
SourceNextLive_Guard54:
.a16
.i16
lda.l SourceNextFrame_Base+736,x
and #1
beq SourceNextLive_Guard55
brl SourceNextLive_No
SourceNextLive_Guard55:
.a16
.i16
lda.l SourceNextFrame_Base+736,x
eor #$FFFF
inc a
clc
adc 5,s
cmp #17
bcc SourceNextLive_Guard56
brl SourceNextLive_No
SourceNextLive_Guard56:
.a16
.i16
lda 11,s
asl a
tay
lda.w $4E9C,y
clc
adc #$0A00
cmp.l SourceNextFrame_Base+738,x
beq SourceNextLive_Guard57
brl SourceNextLive_No
SourceNextLive_Guard57:
.a16
.i16
lda 11,s
asl a
asl a
pha
asl a
asl a
asl a
clc
adc 1,s
tay
pla
lda.w $4E38,y
cmp #0
beq SourceNextLive_Guard58
brl SourceNextLive_No
SourceNextLive_Guard58:
.a16
.i16
lda.w $4E3C,y
cmp #18
beq SourceNextLive_Guard59
brl SourceNextLive_No
SourceNextLive_Guard59:
.a16
.i16
lda.w $4E40,y
cmp #1
beq SourceNextLive_Guard60
brl SourceNextLive_No
SourceNextLive_Guard60:
.a16
.i16
lda.w $4E42,y
cmp #0
beq SourceNextLive_Guard61
brl SourceNextLive_No
SourceNextLive_Guard61:
.a16
.i16
lda.w $4E4A,y
and #255
cmp #2
beq SourceNextLive_Guard62
brl SourceNextLive_No
SourceNextLive_Guard62:
.a16
.i16
lda.w $4E50,y
and #255
cmp #1
beq SourceNextLive_Guard63
brl SourceNextLive_No
SourceNextLive_Guard63:
.a16
.i16
lda.w $4E54,y
and #255
cmp #8
beq SourceNextLive_Guard64
brl SourceNextLive_No
SourceNextLive_Guard64:
.a16
.i16
lda.w $4E3A,y
and #255
cmp 13,s
beq SourceNextLive_Guard65
brl SourceNextLive_No
SourceNextLive_Guard65:
.a16
.i16
lda.w $4E44,y
bne SourceNextLive_Guard66
brl SourceNextLive_No
SourceNextLive_Guard66:
.a16
.i16
and #$8000
beq SourceNextLive_Guard67
brl SourceNextLive_No
SourceNextLive_Guard67:
.a16
.i16
lda 3,s
tay
lda 3,s
tax
lda.l SourceVisual_State,x
pha
lda 3,s
tax
pla
cmp.l SourceNextFrame_Base+4,x
beq SourceNextLive_Guard68
brl SourceNextLive_No
SourceNextLive_Guard68:
.a16
.i16
lda 3,s
tax
lda.l SourceVisual_State+29,x
cmp #$0116
beq SourceNextLive_Guard69
brl SourceNextLive_No
SourceNextLive_Guard69:
.a16
.i16
lda 17,s
cmp #$4E46
beq SourceNextLive_Prepared
brl SourceNextLive_Committed
SourceNextLive_Prepared:
.a16
.i16
lda 1,s
clc
adc 3,s
tax
lda 3,s
tay
lda.l SourceNextFrame_Base+672,x
cmp.w $5380,y
beq SourceNextLive_Guard70
brl SourceNextLive_No
SourceNextLive_Guard70:
.a16
.i16
lda.l SourceNextFrame_Base+674,x
cmp.w $5382,y
beq SourceNextLive_Guard71
brl SourceNextLive_No
SourceNextLive_Guard71:
.a16
.i16
lda.l SourceNextFrame_Base+680,x
cmp.w $5388,y
beq SourceNextLive_Guard72
brl SourceNextLive_No
SourceNextLive_Guard72:
.a16
.i16
lda.l SourceNextFrame_Base+682,x
cmp.w $538A,y
beq SourceNextLive_Guard73
brl SourceNextLive_No
SourceNextLive_Guard73:
.a16
.i16
lda.l SourceNextFrame_Base+684,x
cmp.w $538C,y
beq SourceNextLive_Guard74
brl SourceNextLive_No
SourceNextLive_Guard74:
.a16
.i16
lda.l SourceNextFrame_Base+686,x
cmp.w $538E,y
beq SourceNextLive_Guard75
brl SourceNextLive_No
SourceNextLive_Guard75:
.a16
.i16
lda.l SourceNextFrame_Base+688,x
cmp.w $5390,y
beq SourceNextLive_Guard76
brl SourceNextLive_No
SourceNextLive_Guard76:
.a16
.i16
lda.l SourceNextFrame_Base+690,x
cmp.w $5392,y
beq SourceNextLive_Guard77
brl SourceNextLive_No
SourceNextLive_Guard77:
.a16
.i16
lda.l SourceNextFrame_Base+692,x
cmp.w $5394,y
beq SourceNextLive_Guard78
brl SourceNextLive_No
SourceNextLive_Guard78:
.a16
.i16
lda.l SourceNextFrame_Base+694,x
cmp.w $5396,y
beq SourceNextLive_Guard79
brl SourceNextLive_No
SourceNextLive_Guard79:
.a16
.i16
lda.l SourceNextFrame_Base+696,x
cmp.w $5398,y
beq SourceNextLive_Guard80
brl SourceNextLive_No
SourceNextLive_Guard80:
.a16
.i16
lda.l SourceNextFrame_Base+698,x
cmp.w $539A,y
beq SourceNextLive_Guard81
brl SourceNextLive_No
SourceNextLive_Guard81:
.a16
.i16
brl SourceNextLive_MetadataDone
SourceNextLive_Committed:
.a16
.i16
lda 1,s
tax
lda 3,s
tay
lda.l SourceNextFrame_Base+608,x
cmp.w $5380,y
beq SourceNextLive_Guard82
brl SourceNextLive_No
SourceNextLive_Guard82:
.a16
.i16
lda.l SourceNextFrame_Base+610,x
cmp.w $5382,y
beq SourceNextLive_Guard83
brl SourceNextLive_No
SourceNextLive_Guard83:
.a16
.i16
lda.l SourceNextFrame_Base+616,x
cmp.w $5388,y
beq SourceNextLive_Guard84
brl SourceNextLive_No
SourceNextLive_Guard84:
.a16
.i16
lda.l SourceNextFrame_Base+618,x
cmp.w $538A,y
beq SourceNextLive_Guard85
brl SourceNextLive_No
SourceNextLive_Guard85:
.a16
.i16
lda.l SourceNextFrame_Base+620,x
cmp.w $538C,y
beq SourceNextLive_Guard86
brl SourceNextLive_No
SourceNextLive_Guard86:
.a16
.i16
lda.l SourceNextFrame_Base+622,x
cmp.w $538E,y
beq SourceNextLive_Guard87
brl SourceNextLive_No
SourceNextLive_Guard87:
.a16
.i16
lda.l SourceNextFrame_Base+624,x
cmp.w $5390,y
beq SourceNextLive_Guard88
brl SourceNextLive_No
SourceNextLive_Guard88:
.a16
.i16
lda.l SourceNextFrame_Base+626,x
cmp.w $5392,y
beq SourceNextLive_Guard89
brl SourceNextLive_No
SourceNextLive_Guard89:
.a16
.i16
lda.l SourceNextFrame_Base+628,x
cmp.w $5394,y
beq SourceNextLive_Guard90
brl SourceNextLive_No
SourceNextLive_Guard90:
.a16
.i16
lda.l SourceNextFrame_Base+630,x
cmp.w $5396,y
beq SourceNextLive_Guard91
brl SourceNextLive_No
SourceNextLive_Guard91:
.a16
.i16
lda.l SourceNextFrame_Base+632,x
cmp.w $5398,y
beq SourceNextLive_Guard92
brl SourceNextLive_No
SourceNextLive_Guard92:
.a16
.i16
lda.l SourceNextFrame_Base+634,x
cmp.w $539A,y
beq SourceNextLive_Guard93
brl SourceNextLive_No
SourceNextLive_Guard93:
.a16
.i16
SourceNextLive_MetadataDone:
.a16
.i16
lda 1,s
tax
lda.l SourceNextFrame_Base,x
cmp 17,s
beq SourceNextLive_Guard94
brl SourceNextLive_No
SourceNextLive_Guard94:
.a16
.i16
lda.l SourceNextFrame_Base+740,x
cmp.l SourceNextScene_Magic
beq SourceNextLive_Guard95
brl SourceNextLive_No
SourceNextLive_Guard95:
.a16
.i16
lda.l SourceNextFrame_Base+742,x
cmp.l SourceNextScene_Low
beq SourceNextLive_Guard96
brl SourceNextLive_No
SourceNextLive_Guard96:
.a16
.i16
lda.l SourceNextFrame_Base+744,x
cmp.l SourceNextScene_High
beq SourceNextLive_Guard97
brl SourceNextLive_No
SourceNextLive_Guard97:
.a16
.i16
lda.l $434E7C
cmp 5,s
beq SourceNextLive_Guard98
brl SourceNextLive_No
SourceNextLive_Guard98:
.a16
.i16
lda.l $434E7E
cmp #$4D50
beq SourceNextLive_Guard99
brl SourceNextLive_No
SourceNextLive_Guard99:
.a16
.i16
SourceNextLive_Yes:
.a16
.i16
pla
pla
pla
pla
pla
pla
pla
pla
pla
pld
plb
ply
plx
pla
plp
sec
rtl
SourceNextLive_No:
.a16
.i16
pla
pla
pla
pla
pla
pla
pla
pla
pla
SourceNextLive_NoEarly:
.a16
.i16
pld
plb
ply
plx
pla
plp
clc
rtl
SourceNextLive_End:
.a16
.i16
