; UNHOOKED per-player preparation transaction, no live publication.
; Own next pins persist with the immutable image until explicit cancellation.
; Publication/adoption and actual hardware replacement acknowledgement remain separate.
SourceNextFrame_Base = $436C00
SourceNextFrame_Prepare:
.a16
.i16
php
rep #$30
cld
pha
phx
phy
phb
lda.l SourceVisual_ActorSlot
cmp #2
bcc SourceNextFrame_Guard1
brl SourceNextFrame_NoEarly
SourceNextFrame_Guard1:
.a16
.i16
asl a
asl a
asl a
asl a
asl a
asl a
asl a
asl a
asl a
asl a
tax
lda.l $7E46DE
beq SourceNextFrame_Guard2
brl SourceNextFrame_NoEarly
SourceNextFrame_Guard2:
.a16
.i16
lda.l SourceNextFrame_Base,x
beq SourceNextFrame_Guard3
brl SourceNextFrame_NoEarly
SourceNextFrame_Guard3:
.a16
.i16
txa
lsr a
tax
lda.l SourceNextWitness_Base,x
beq SourceNextFrame_Guard4
brl SourceNextFrame_NoEarly
SourceNextFrame_Guard4:
.a16
.i16
txa
asl a
pha
lda.l SourceVisual_ActorSlot
asl a
asl a
asl a
asl a
asl a
pha
tax
lda.l SourcePacket_ActiveValid
cmp #1
beq SourceNextFrame_Guard5
brl SourceNextFrame_No
SourceNextFrame_Guard5:
.a16
.i16
lda.l SourcePacket_CopyBusy
beq SourceNextFrame_Guard6
brl SourceNextFrame_No
SourceNextFrame_Guard6:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+16,x
cmp #1
beq SourceNextFrame_Guard7
brl SourceNextFrame_No
SourceNextFrame_Guard7:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META,x
and #3
beq SourceNextFrame_Guard8
brl SourceNextFrame_No
SourceNextFrame_Guard8:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META,x
sta.l SourceNextEmit_Cursor
jsl SourceNextPins_Acquire
bcs SourceNextFrame_Guard9
brl SourceNextFrame_No
SourceNextFrame_Guard9:
.a16
.i16
jsl SourceNextEmit_Build
bcs SourceNextFrame_Guard10
brl SourceNextFrame_Cleanup
SourceNextFrame_Guard10:
.a16
.i16
lda 1,s
tax
lda.l SourceNextEmit_Meta+16,x
cmp #1
beq SourceNextFrame_Guard11
brl SourceNextFrame_Cleanup
SourceNextFrame_Guard11:
.a16
.i16
lda.l SourceNextEmit_Meta+0,x
cmp.l SOURCE_PACKET_ACTIVE_META+0,x
beq SourceNextFrame_Guard12
brl SourceNextFrame_Cleanup
SourceNextFrame_Guard12:
.a16
.i16
lda.l SourceNextEmit_Meta+2,x
cmp.l SOURCE_PACKET_ACTIVE_META+2,x
beq SourceNextFrame_Guard13
brl SourceNextFrame_Cleanup
SourceNextFrame_Guard13:
.a16
.i16
lda.l SourceVisual_ActorSlot
jsl SourceNextWitness_Capture
bcs SourceNextFrame_Guard14
brl SourceNextFrame_Cleanup
SourceNextFrame_Guard14:
.a16
.i16
lda 3,s
clc
adc #$6C20
tay
ldx #((SourceNextEmit_Buffer) & $FFFF)
lda #511
mvn $43,$43
lda 3,s
clc
adc #$6E20
tay
ldx #((SourceNextEmit_PackedHi) & $FFFF)
lda #63
mvn $43,$43
lda 3,s
clc
adc #$6C08
tay
ldx #((SourceVisual_EntryScratch) & $FFFF)
lda #23
mvn $43,$7E
lda 3,s
clc
adc #$6EA0
tay
ldx #((SOURCE_PACKET_ACTIVE_META) & $FFFF)
lda #63
mvn $43,$43
lda 1,s
clc
adc #((SourceNextEmit_Meta) & $FFFF)
tax
lda 3,s
clc
adc #$6E60
tay
lda #31
mvn $43,$43
lda 1,s
clc
adc #((SourceVisual_State) & $FFFF)
tax
lda 3,s
clc
adc #$6E80
tay
lda #31
mvn $43,$7E
lda 3,s
tax
lda.l SourceVisual_ActorSlot
sta.l SourceNextFrame_Base+2,x
lda.l SourceVisual_EntryIndexSaved
sta.l SourceNextFrame_Base+4,x
lda.l Screen_PosX
sta.l SourceNextFrame_Base+6,x
lda.l $434E7C
sta.l SourceNextFrame_Base+736,x
tdc
sta.l SourceNextFrame_Base+738,x
lda #$4E46
sta.l SourceNextFrame_Base,x
brl SourceNextFrame_Yes
SourceNextFrame_Cleanup:
.a16
.i16
lda.l SourceVisual_ActorSlot
asl a
xba
tax
lda #0
sta.l SourceNextWitness_Base,x
lda.l SourceVisual_ActorSlot
jsl SourceNextPins_ReleaseUnpublished
SourceNextFrame_No:
.a16
.i16
pla
pla
SourceNextFrame_NoEarly:
.a16
.i16
plb
ply
plx
pla
plp
clc
rtl
SourceNextFrame_Yes:
.a16
.i16
pla
pla
plb
ply
plx
pla
plp
sec
rtl
SourceNextFrame_CancelUnpublished:
.a16
.i16
php
rep #$30
cld
pha
phx
phy
cmp #2
bcc SourceNextFrame_Guard15
brl SourceNextFrame_CancelNoEarly
SourceNextFrame_Guard15:
.a16
.i16
pha
xba
asl a
asl a
tax
lda.l SourceNextFrame_Base,x
cmp #$4E46
beq SourceNextFrame_Guard16
brl SourceNextFrame_CancelNo
SourceNextFrame_Guard16:
.a16
.i16
lda.l $7E46DE
cmp #0
beq SourceNextFrame_Guard17
brl SourceNextFrame_CancelNo
SourceNextFrame_Guard17:
.a16
.i16
lda.l Game_CampaignId
and #255
cmp #3
beq SourceNextFrame_Guard18
brl SourceNextFrame_CancelNo
SourceNextFrame_Guard18:
.a16
.i16
lda.l SourceInput_Magic
cmp #6752
beq SourceNextFrame_Guard19
brl SourceNextFrame_CancelNo
SourceNextFrame_Guard19:
.a16
.i16
lda.l SVActor_Magic
cmp #44057
beq SourceNextFrame_Guard20
brl SourceNextFrame_CancelNo
SourceNextFrame_Guard20:
.a16
.i16
lda #0
sta.l SourceNextFrame_Base,x
lda 1,s
xba
asl a
tax
lda #0
sta.l SourceNextWitness_Base,x
lda 1,s
jsl SourceNextPins_ReleaseUnpublished
bcs SourceNextFrame_CancelYes
; Rejection releases no pins. Restore the private committed stamps.
lda 1,s
xba
asl a
tax
lda #$4E50
sta.l SourceNextWitness_Base,x
txa
asl a
tax
lda #$4E46
sta.l SourceNextFrame_Base,x
SourceNextFrame_CancelNo:
.a16
.i16
pla
SourceNextFrame_CancelNoEarly:
.a16
.i16
ply
plx
pla
plp
clc
rtl
SourceNextFrame_CancelYes:
.a16
.i16
pla
ply
plx
pla
plp
sec
rtl
SourceNextFrame_End:
.a16
.i16
