; UNHOOKED RAM-only pose handoff. No DMA/PPU/input/world/cache writes.
; Apply requires the coherent prepared frame and original physical readiness.
; A pending image retains next pins. Abort restores both base and projected
; buffers, preserving the neighboring actor's independent packed-high bits.
SourceNextCommit_State = $437C10
SourceNextCommit_Slot = $437C12
SourceNextCommit_Low = $437C14
SourceNextCommit_High = $437C16
SourceNextCommit_Begin = $437C18
SourceNextCommit_End = $437C1A
SourceNextCommit_Span = $437C1C
SourceNextCommit_Dirty = $437C1E
SourceNextCommit_BaseBody = $437C40
SourceNextCommit_BufferBody = $437C80
SourceNextCommit_BaseHigh = $437CC0
SourceNextCommit_BufferHigh = $437CE0
SourceNextCommit_Meta = $437D00
SourceNextCommit_Signed = $437D20
SourceNextCommit_Mode = $437D60
SourceNextCommit_Cursor = $437D62
SourceNextCommit_Mask = $437D64
SourceNextCommit_Inverse = $437D66
SourceNextCommit_BaseBits = $437D68
SourceNextCommit_BufferBits = $437D6A
SourceNextCommit_FrameOffset = $437D6C
SourceNextCommit_Apply:
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
bcs SourceNextCommit_Long1
brl SourceNextCommit_ApplySlot
SourceNextCommit_Long1:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNoEarly
SourceNextCommit_ApplySlot:
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
txa
sta 1,s
xba
asl a
asl a
sta 3,s
lda 1,s
asl a
asl a
asl a
asl a
asl a
sta 5,s
lda.l SourceNextCommit_State
bne SourceNextCommit_Long2
brl SourceNextCommit_Guard1
SourceNextCommit_Long2:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard1:
.a16
.i16
lda.l $434E7C
sta 7,s
lda 1,s
jsl SourceNextLive_Check
bcc SourceNextCommit_Long3
brl SourceNextCommit_Guard2
SourceNextCommit_Long3:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard2:
.a16
.i16
lda 1,s
jsl SourceNextCompact_Ready
bcc SourceNextCommit_Long4
brl SourceNextCommit_Guard3
SourceNextCommit_Long4:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard3:
.a16
.i16
lda.l $434E7C
cmp 7,s
bne SourceNextCommit_Long5
brl SourceNextCommit_Guard4
SourceNextCommit_Long5:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard4:
.a16
.i16
lda 3,s
tax
lda.l SourceNextFrame_Base,x
cmp #$4E46
bne SourceNextCommit_Long6
brl SourceNextCommit_Guard5
SourceNextCommit_Long6:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard5:
.a16
.i16
lda.l SourceNextFrame_Base+740,x
cmp.l SourceNextScene_Magic
bne SourceNextCommit_Long7
brl SourceNextCommit_Guard6
SourceNextCommit_Long7:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard6:
.a16
.i16
lda.l SourceNextFrame_Base+742,x
cmp.l SourceNextScene_Low
bne SourceNextCommit_Long8
brl SourceNextCommit_Guard7
SourceNextCommit_Long8:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard7:
.a16
.i16
lda.l SourceNextFrame_Base+744,x
cmp.l SourceNextScene_High
bne SourceNextCommit_Long9
brl SourceNextCommit_Guard8
SourceNextCommit_Long9:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard8:
.a16
.i16
jsr SourceNextCommit_QueueClear
bcc SourceNextCommit_Long10
brl SourceNextCommit_Guard9
SourceNextCommit_Long10:
.a16
.i16
.a16
.i16
brl SourceNextCommit_ApplyNo
SourceNextCommit_Guard9:
.a16
.i16
lda 3,s
tax
lda.l SourceNextFrame_Base+608,x
sta 9,s
lda.l SourceNextFrame_Base+610,x
sta 13,s
lda 9,s
eor #$FFFF
inc a
clc
adc 13,s
sta 11,s
sep #$20
.a8
lda #$43
pha
plb
rep #$20
.a16
lda #1
sta.l SourcePacket_CopyBusy
lda #0
sta.l SourcePacket_NmiPending
lda 1,s
sta.l SourceNextCommit_Slot
lda 9,s
sta.l SourceNextCommit_Begin
lda 13,s
sta.l SourceNextCommit_End
lda 11,s
sta.l SourceNextCommit_Span
lda.l SourceNextScene_Low
sta.l SourceNextCommit_Low
lda.l SourceNextScene_High
sta.l SourceNextCommit_High
lda 9,s
clc
adc #((SOURCE_PACKET_BASE) & $FFFF)
tax
ldy #((SourceNextCommit_BaseBody) & $FFFF)
lda 11,s
dec a
mvn $43,$43
lda 9,s
clc
adc #((SOURCE_PACKET_BUFFER) & $FFFF)
tax
ldy #((SourceNextCommit_BufferBody) & $FFFF)
lda 11,s
dec a
mvn $43,$43
ldx #((SOURCE_PACKET_BASE+512) & $FFFF)
ldy #((SourceNextCommit_BaseHigh) & $FFFF)
lda #31
mvn $43,$43
ldx #((SOURCE_PACKET_BUFFER+512) & $FFFF)
ldy #((SourceNextCommit_BufferHigh) & $FFFF)
lda #31
mvn $43,$43
lda 5,s
clc
adc #((SOURCE_PACKET_ACTIVE_META) & $FFFF)
tax
ldy #((SourceNextCommit_Meta) & $FFFF)
lda #31
mvn $43,$43
lda 9,s
clc
adc #((SOURCE_PACKET_SIGNED_X) & $FFFF)
tax
ldy #((SourceNextCommit_Signed) & $FFFF)
lda 11,s
dec a
mvn $43,$43
lda 9,s
clc
adc 3,s
clc
adc #((SourceNextFrame_Base+32) & $FFFF)
tax
lda 9,s
clc
adc #((SOURCE_PACKET_BASE) & $FFFF)
tay
lda 11,s
dec a
mvn $43,$43
lda 9,s
clc
adc 3,s
clc
adc #((SourceNextFrame_Base+32) & $FFFF)
tax
lda 9,s
clc
adc #((SOURCE_PACKET_BUFFER) & $FFFF)
tay
lda 11,s
dec a
mvn $43,$43
lda 3,s
clc
adc #((SourceNextFrame_Base+608) & $FFFF)
tax
lda 5,s
clc
adc #((SOURCE_PACKET_ACTIVE_META) & $FFFF)
tay
lda #31
mvn $43,$43
lda #0
sta.l SourceNextCommit_Mode
jsr SourceNextCommit_HighBits
jsr SourceNextCommit_SeedSigned
lda.l $434E7C
cmp 7,s
bne SourceNextCommit_Long11
brl SourceNextCommit_ApplyStable
SourceNextCommit_Long11:
.a16
.i16
.a16
.i16
jsr SourceNextCommit_RestoreOwned
lda #0
sta.l SourcePacket_CopyBusy
sta.l SourceNextCommit_State
lda #1
sta.l SourceNextCommit_Dirty
lda #$FFFF
sta.l SourcePacket_ReadSeq
brl SourceNextCommit_ApplyNo
SourceNextCommit_ApplyStable:
.a16
.i16
lda 3,s
tax
lda #$4E47
sta.l SourceNextFrame_Base,x
lda #1
sta.l SourceNextCommit_State
sta.l SourceNextCommit_Dirty
lda #$FFFF
sta.l SourcePacket_ReadSeq
lda #0
sta.l SourcePacket_CopyBusy
brl SourceNextCommit_ApplyYes
SourceNextCommit_ApplyNo:
.a16
.i16
pla
pla
pla
pla
pla
pla
pla
SourceNextCommit_ApplyNoEarly:
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
SourceNextCommit_ApplyYes:
.a16
.i16
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
SourceNextCommit_QueueClear:
.a16
.i16
ldx #0
SourceNextCommit_QueueLoop:
.a16
.i16
lda.l DmaQueue+4,x
and #$40
bne SourceNextCommit_Long12
brl SourceNextCommit_QueueNext
SourceNextCommit_Long12:
.a16
.i16
.a16
.i16
lda.l DmaQueue+7,x
and #255
cmp #$43
bne SourceNextCommit_Long13
brl SourceNextCommit_QueueNo
SourceNextCommit_Long13:
.a16
.i16
.a16
.i16
lda.l DmaQueue+4,x
and #$1F
cmp #DMA_TYPE_OAM
bne SourceNextCommit_Long14
brl SourceNextCommit_QueueNo
SourceNextCommit_Long14:
.a16
.i16
.a16
.i16
SourceNextCommit_QueueNext:
.a16
.i16
inx
inx
inx
inx
inx
inx
inx
inx
cpx #64
bcs SourceNextCommit_Long15
brl SourceNextCommit_QueueLoop
SourceNextCommit_Long15:
.a16
.i16
.a16
.i16
sec
rts
SourceNextCommit_QueueNo:
.a16
.i16
clc
rts
; Restore only the target's body, metadata, signed coordinates and high bits.
; Caller owns CopyBusy and supplies the original validated header.
SourceNextCommit_RestoreOwned:
.a16
.i16
ldx #((SourceNextCommit_BaseBody) & $FFFF)
lda.l SourceNextCommit_Begin
clc
adc #((SOURCE_PACKET_BASE) & $FFFF)
tay
lda.l SourceNextCommit_Span
dec a
mvn $43,$43
ldx #((SourceNextCommit_BufferBody) & $FFFF)
lda.l SourceNextCommit_Begin
clc
adc #((SOURCE_PACKET_BUFFER) & $FFFF)
tay
lda.l SourceNextCommit_Span
dec a
mvn $43,$43
ldx #((SourceNextCommit_Meta) & $FFFF)
lda.l SourceNextCommit_Slot
asl a
asl a
asl a
asl a
asl a
clc
adc #((SOURCE_PACKET_ACTIVE_META) & $FFFF)
tay
lda #31
mvn $43,$43
ldx #((SourceNextCommit_Signed) & $FFFF)
lda.l SourceNextCommit_Begin
clc
adc #((SOURCE_PACKET_SIGNED_X) & $FFFF)
tay
lda.l SourceNextCommit_Span
dec a
mvn $43,$43
lda #1
sta.l SourceNextCommit_Mode
jsr SourceNextCommit_HighBits
rts
SourceNextCommit_HighBits:
.a16
.i16
lda.l SourceNextCommit_Slot
xba
asl a
asl a
sta.l SourceNextCommit_FrameOffset
lda.l SourceNextCommit_Begin
sta.l SourceNextCommit_Cursor
SourceNextCommit_HighLoop:
.a16
.i16
lda.l SourceNextCommit_Cursor
lsr a
lsr a
lsr a
lsr a
tay
lda.l SourceNextCommit_Cursor
and #15
lsr a
lsr a
tax
lda.l SourceNextCommit_HighMasks,x
and #255
sta.l SourceNextCommit_Mask
eor #$FFFF
sta.l SourceNextCommit_Inverse
lda.l SourceNextCommit_Mode
beq SourceNextCommit_Long16
brl SourceNextCommit_HighRestore
SourceNextCommit_Long16:
.a16
.i16
.a16
.i16
tya
clc
adc.l SourceNextCommit_FrameOffset
tax
lda.l SourceNextFrame_Base+544,x
and.l SourceNextCommit_Mask
sta.l SourceNextCommit_BaseBits
sta.l SourceNextCommit_BufferBits
brl SourceNextCommit_HighWrite
SourceNextCommit_HighRestore:
.a16
.i16
lda.w $7CC0,y
and.l SourceNextCommit_Mask
sta.l SourceNextCommit_BaseBits
lda.w $7CE0,y
and.l SourceNextCommit_Mask
sta.l SourceNextCommit_BufferBits
SourceNextCommit_HighWrite:
.a16
.i16
sep #$20
.a8
lda.w $5320,y
and.l SourceNextCommit_Inverse
ora.l SourceNextCommit_BaseBits
sta.w $5320,y
lda.w $5100,y
and.l SourceNextCommit_Inverse
ora.l SourceNextCommit_BufferBits
sta.w $5100,y
rep #$20
.a16
lda.l SourceNextCommit_Cursor
clc
adc #4
sta.l SourceNextCommit_Cursor
cmp.l SourceNextCommit_End
bcs SourceNextCommit_Long17
brl SourceNextCommit_HighLoop
SourceNextCommit_Long17:
.a16
.i16
.a16
.i16
rts
SourceNextCommit_SeedSigned:
.a16
.i16
lda.l SourceNextCommit_Begin
sta.l SourceNextCommit_Cursor
SourceNextCommit_SignedLoop:
.a16
.i16
lda.l SourceNextCommit_Cursor
lsr a
lsr a
lsr a
lsr a
tay
lda.l SourceNextCommit_Cursor
and #15
lsr a
lsr a
tax
lda.l SourcePacket_XMasks,x
and #255
sta.l SourceNextCommit_Mask
lda.w $5320,y
and.l SourceNextCommit_Mask
bne SourceNextCommit_Long18
brl SourceNextCommit_SignedPositive
SourceNextCommit_Long18:
.a16
.i16
.a16
.i16
lda.l SourceNextCommit_Cursor
tax
lda.w $5120,x
and #255
ora #$FF00
brl SourceNextCommit_SignedStore
SourceNextCommit_SignedPositive:
.a16
.i16
lda.l SourceNextCommit_Cursor
tax
lda.w $5120,x
and #255
SourceNextCommit_SignedStore:
.a16
.i16
sta.w $5600,x
lda.l SourceNextCommit_Cursor
clc
adc #4
sta.l SourceNextCommit_Cursor
cmp.l SourceNextCommit_End
bcs SourceNextCommit_Long19
brl SourceNextCommit_SignedLoop
SourceNextCommit_Long19:
.a16
.i16
.a16
.i16
rts
SourceNextCommit_HighMasks:
.a16
.i16
.db 3,12,48,192
; Abort a RAM-only pending image. A different main generation detaches
; it without restoring stale bytes. Neither path releases any resource pin.
SourceNextCommit_Abort:
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
lda.l SourceNextCommit_State
cmp #1
bne SourceNextCommit_Long20
brl SourceNextCommit_Guard10
SourceNextCommit_Long20:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard10:
.a16
.i16
lda.l SourceNextCommit_Slot
cmp #2
bcs SourceNextCommit_Long21
brl SourceNextCommit_Guard11
SourceNextCommit_Long21:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard11:
.a16
.i16
xba
asl a
asl a
tax
lda.l SourceNextFrame_Base,x
cmp #$4E47
bne SourceNextCommit_Long22
brl SourceNextCommit_Guard12
SourceNextCommit_Long22:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard12:
.a16
.i16
lda.l SourceNextScene_Magic
cmp #$5343
beq SourceNextCommit_Long23
brl SourceNextCommit_Detach
SourceNextCommit_Long23:
.a16
.i16
.a16
.i16
lda.l SourceNextScene_Low
cmp.l SourceNextCommit_Low
beq SourceNextCommit_Long24
brl SourceNextCommit_Detach
SourceNextCommit_Long24:
.a16
.i16
.a16
.i16
lda.l SourceNextScene_High
cmp.l SourceNextCommit_High
beq SourceNextCommit_Long25
brl SourceNextCommit_Detach
SourceNextCommit_Long25:
.a16
.i16
.a16
.i16
lda.l SourcePacket_ActiveValid
cmp #1
beq SourceNextCommit_Long26
brl SourceNextCommit_Detach
SourceNextCommit_Long26:
.a16
.i16
.a16
.i16
lda.l SourcePacket_CopyBusy
bne SourceNextCommit_Long27
brl SourceNextCommit_Guard13
SourceNextCommit_Long27:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard13:
.a16
.i16
jsr SourceNextCommit_QueueClear
bcc SourceNextCommit_Long28
brl SourceNextCommit_Guard14
SourceNextCommit_Long28:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard14:
.a16
.i16
lda.l SourceNextCommit_Begin
and #3
bne SourceNextCommit_Long29
brl SourceNextCommit_Guard15
SourceNextCommit_Long29:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard15:
.a16
.i16
lda.l SourceNextCommit_End
and #3
bne SourceNextCommit_Long30
brl SourceNextCommit_Guard16
SourceNextCommit_Long30:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard16:
.a16
.i16
lda.l SourceNextCommit_End
cmp #513
bcs SourceNextCommit_Long31
brl SourceNextCommit_Guard17
SourceNextCommit_Long31:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard17:
.a16
.i16
lda.l SourceNextCommit_Begin
eor #$FFFF
inc a
clc
adc.l SourceNextCommit_End
cmp.l SourceNextCommit_Span
bne SourceNextCommit_Long32
brl SourceNextCommit_Guard18
SourceNextCommit_Long32:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard18:
.a16
.i16
cmp #1
bcc SourceNextCommit_Long33
brl SourceNextCommit_Guard19
SourceNextCommit_Long33:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard19:
.a16
.i16
cmp #65
bcs SourceNextCommit_Long34
brl SourceNextCommit_Guard20
SourceNextCommit_Long34:
.a16
.i16
.a16
.i16
brl SourceNextCommit_AbortNo
SourceNextCommit_Guard20:
.a16
.i16
sep #$20
.a8
lda #$43
pha
plb
rep #$20
.a16
lda #1
sta.l SourcePacket_CopyBusy
lda #0
sta.l SourcePacket_NmiPending
jsr SourceNextCommit_RestoreOwned
lda #$FFFF
sta.l SourcePacket_ReadSeq
lda #1
sta.l SourceNextCommit_Dirty
lda #0
sta.l SourcePacket_CopyBusy
SourceNextCommit_Detach:
.a16
.i16
lda.l SourceNextCommit_Slot
xba
asl a
asl a
tax
lda #$4E46
sta.l SourceNextFrame_Base,x
lda #1
sta.l SourceNextFrame_Base+750,x
lda #0
sta.l SourceNextCommit_State
brl SourceNextCommit_AbortYes
SourceNextCommit_AbortNo:
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
SourceNextCommit_AbortYes:
.a16
.i16
pld
plb
ply
plx
pla
plp
sec
rtl
; Call ONLY at the original NmiPublish post-$420B seam, after channel
; register restoration. This reproduces the old pending-clear instruction.
; It never increments the original completed-generation acknowledgement.
SourceNextCommit_Physical:
.a16
.i16
lda #0
sta.l SourcePacket_NmiPending
php
rep #$30
pha
phx
phy
lda #0
sta.l SourceNextCommit_Dirty
lda.l SourceNextCommit_State
cmp #1
beq SourceNextCommit_Long35
brl SourceNextCommit_PhysicalDone
SourceNextCommit_Long35:
.a16
.i16
.a16
.i16
lda.l SourceNextCommit_Slot
cmp #2
bcc SourceNextCommit_Long36
brl SourceNextCommit_PhysicalDone
SourceNextCommit_Long36:
.a16
.i16
.a16
.i16
xba
asl a
asl a
tax
lda.l SourceNextFrame_Base,x
cmp #$4E47
beq SourceNextCommit_Long37
brl SourceNextCommit_PhysicalDone
SourceNextCommit_Long37:
.a16
.i16
.a16
.i16
lda.l SourceNextScene_Magic
cmp #$5343
beq SourceNextCommit_Long38
brl SourceNextCommit_PhysicalDone
SourceNextCommit_Long38:
.a16
.i16
.a16
.i16
lda.l SourceNextScene_Low
cmp.l SourceNextCommit_Low
beq SourceNextCommit_Long39
brl SourceNextCommit_PhysicalDone
SourceNextCommit_Long39:
.a16
.i16
.a16
.i16
lda.l SourceNextScene_High
cmp.l SourceNextCommit_High
beq SourceNextCommit_Long40
brl SourceNextCommit_PhysicalDone
SourceNextCommit_Long40:
.a16
.i16
.a16
.i16
lda #$4E48
sta.l SourceNextFrame_Base,x
lda.l SourceVisual_CompletedAcks
sta.l SourceNextFrame_Base+746,x
lda.l $434E7C
sta.l SourceNextFrame_Base+748,x
lda #0
sta.l SourceNextFrame_Base+750,x
sta.l SourceNextCommit_State
SourceNextCommit_PhysicalDone:
.a16
.i16
ply
plx
pla
plp
rtl
SourceNextCommit_End:
.a16
.i16
