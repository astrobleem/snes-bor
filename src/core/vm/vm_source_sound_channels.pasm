; B63A twelve-channel source admission component, not a DSP playback owner.
; Compact state: unsigned priority32, admitted namespace16, active16 (0/1/2).
; Offer is readonly over channel state. No source event/voice is committed here.
; Returns Status0 offer,1 source priority rejection,2 fault,3 undefined source
; all-UINT_MAX corner. Physical projection, phase and playback remain required.
SOURCE_SOUND_CHANNELS = $7EFF88 ; 12*8, exclusive end $7EFFE8
SourceSoundChannels4086_Ready = $7EFFE8
SourceSoundChannels4086_Selected = $7EFFEA
SourceSoundChannels4086_Status = $7EFFEC
SourceSoundChannels4086_Sample = $7EFFEE
SourceSoundChannels4086_Cursor = $7EFFF0
SourceSoundChannels4086_Priority = $7EFFF2
SourceSoundChannels4086_Count = $7EFFF6
SourceSoundChannels4086_Lowest = $7EFFF8
SourceSoundChannels4086_Best = $7EFFFC
SourceSoundChannels4086_BackendReady = $7EFFFE
SourceSoundChannels4086_Offer:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceSoundChannels4086_Ready
 cmp #$B63A
 beq SourceSoundChannels4086_Lease
 jmp SourceSoundChannels4086_Bad
SourceSoundChannels4086_Lease:
.a16
.i16
 lda.l SourceSoundChannels4086_Count
 cmp #12
 beq SourceSoundChannels4086_CountGood
 jmp SourceSoundChannels4086_Bad
SourceSoundChannels4086_CountGood:
.a16
.i16
 lda #$FFFF
 sta.l SourceSoundChannels4086_Selected
 sta.l SourceSoundChannels4086_Best
 sta.l SourceSoundChannels4086_Lowest
 sta.l SourceSoundChannels4086_Lowest+2
 lda #0
 sta.l SourceSoundChannels4086_Cursor
SourceSoundChannels4086_Scan:
.a16
.i16
 lda.l SourceSoundChannels4086_Cursor
 tax
 lda.l SOURCE_SOUND_CHANNELS+6,x
 beq SourceSoundChannels4086_Free
 cmp #3
 bcc SourceSoundChannels4086_Active
 jmp SourceSoundChannels4086_Bad
SourceSoundChannels4086_Active:
.a16
.i16
 lda.l SOURCE_SOUND_CHANNELS+2,x
 cmp.l SourceSoundChannels4086_Lowest+2
 bcc SourceSoundChannels4086_Lower
 bne SourceSoundChannels4086_Next
 lda.l SOURCE_SOUND_CHANNELS,x
 cmp.l SourceSoundChannels4086_Lowest
 bcs SourceSoundChannels4086_Next
SourceSoundChannels4086_Lower:
.a16
.i16
 lda.l SOURCE_SOUND_CHANNELS,x
 sta.l SourceSoundChannels4086_Lowest
 lda.l SOURCE_SOUND_CHANNELS+2,x
 sta.l SourceSoundChannels4086_Lowest+2
 txa
 lsr a
 lsr a
 lsr a
 sta.l SourceSoundChannels4086_Best
 bra SourceSoundChannels4086_Next
SourceSoundChannels4086_Free:
.a16
.i16
 txa
 lsr a
 lsr a
 lsr a
 sta.l SourceSoundChannels4086_Selected
SourceSoundChannels4086_Next:
.a16
.i16
 lda.l SourceSoundChannels4086_Cursor
 clc
 adc #8
 sta.l SourceSoundChannels4086_Cursor
 cmp #96
 bcs SourceSoundChannels4086_Scanned
 jmp SourceSoundChannels4086_Scan
SourceSoundChannels4086_Scanned:
.a16
.i16
 lda.l SourceSoundChannels4086_Selected
 cmp #$FFFF
 bne SourceSoundChannels4086_Offered
 lda.l SourceSoundChannels4086_Lowest+2
 cmp.l SourceSoundChannels4086_Priority+2
 bcc SourceSoundChannels4086_PriorityAllows
 bne SourceSoundChannels4086_Rejected
 lda.l SourceSoundChannels4086_Lowest
 cmp.l SourceSoundChannels4086_Priority
 bcc SourceSoundChannels4086_PriorityAllows
 bne SourceSoundChannels4086_Rejected
SourceSoundChannels4086_PriorityAllows:
.a16
.i16
 lda.l SourceSoundChannels4086_Best
 cmp #$FFFF
 beq SourceSoundChannels4086_Undefined
 sta.l SourceSoundChannels4086_Selected
SourceSoundChannels4086_Offered:
.a16
.i16
 lda #0
 bra SourceSoundChannels4086_Return
SourceSoundChannels4086_Rejected:
.a16
.i16
 lda #1
 bra SourceSoundChannels4086_Return
SourceSoundChannels4086_Undefined:
.a16
.i16
 lda #3
SourceSoundChannels4086_Return:
.a16
.i16
 sta.l SourceSoundChannels4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceSoundChannels4086_Bad:
.a16
.i16
 lda #2
 sta.l SourceSoundChannels4086_Status
 ply
 plx
 plp
 sec
 rtl
