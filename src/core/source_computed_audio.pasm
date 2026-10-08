; Generic completed-BRR offer. This is consumer admission, not acquisition of
; the source CHR workspace. The producer must already hold that workspace and
; disable character conversion before publishing Ready/State/Generation.
; It must retain the immutable payload through State=4 (actual DSP completion).
; No production producer currently publishes this capability.
;
; The verified gap after SOURCE_PLAYER_STATS_END and before VmSlots_Wram is
; $7FBFC0..$7FBFFF. All fields below belong to this one consumer protocol.
SourceComputedAudio_Ready = $7FBFC0
SourceComputedAudio_Generation = $7FBFC2 ; .dd workspace generation
SourceComputedAudio_State = $7FBFC6 ; .dw 1=writing, 2=published, 3=reading, 4=retired
SourceComputedAudio_Offset = $7FBFC8 ; .dw offset in bank 42
SourceComputedAudio_Bytes = $7FBFCA ; .dw meaningful BRR bytes
SourceComputedAudio_Blocks = $7FBFCC ; .dw, each block is nine bytes
SourceComputedAudio_Chunks = $7FBFCE ; .dw, each transport packet is 144 bytes
SourceComputedAudio_ConsumerGeneration = $7FBFD0 ; .dd admitted generation
SourceComputedAudio_Status = $7FBFD4 ; .dw 1=accepted, 2=invalid, 3=busy, 4=retired
SourceComputedAudio_Temp = $7FBFD6 ; .dw admission arithmetic scratch
SourceComputedAudio_TransferEnd = $7FBFD8 ; .dw padded exclusive end
SourceComputedAudio_End = $7FBFDA

; A16/X16 = expected generation low/high. Preserve caller registers and P.
; Carry clear accepts the completed offer; carry set leaves active identity
; and consumer generation untouched. Generation zero is never a valid lease.
SourceComputedAudio_Start:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phy
 lda.l AudioSemantic_FootDieStreamActive
 and #$00FF
 beq SourceComputedAudio_Start__idle
 lda #3
 jmp SourceComputedAudio_Start__reject
SourceComputedAudio_Start__idle:
.a16
.i16
 lda.l SourceComputedAudio_Ready
 cmp #$B66C
 beq SourceComputedAudio_Start__ready
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__ready:
.a16
.i16
 lda.l SourceComputedAudio_State
 cmp #2
 beq SourceComputedAudio_Start__published
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__published:
.a16
.i16
 lda.l SourceComputedAudio_Generation
 ora.l SourceComputedAudio_Generation+2
 bne SourceComputedAudio_Start__nonzero
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__nonzero:
.a16
.i16
 lda 5,s
 cmp.l SourceComputedAudio_Generation
 beq SourceComputedAudio_Start__low
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__low:
.a16
.i16
 lda 3,s
 cmp.l SourceComputedAudio_Generation+2
 beq SourceComputedAudio_Start__epoch
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__epoch:
.a16
.i16
 lda.l SourceComputedAudio_Blocks
 bne SourceComputedAudio_Start__validation_0
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_0:
.a16
.i16
 cmp #6145
 bcc SourceComputedAudio_Start__validation_1
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_1:
.a16
.i16
 sta.l SourceComputedAudio_Temp
 asl a
 asl a
 asl a
 clc
 adc.l SourceComputedAudio_Temp
 cmp.l SourceComputedAudio_Bytes
 beq SourceComputedAudio_Start__validation_2
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_2:
.a16
.i16
 lda.l SourceComputedAudio_Offset
 clc
 adc.l SourceComputedAudio_Bytes
 bcc SourceComputedAudio_Start__validation_3
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_3:
.a16
.i16
 cmp #$D801
 bcc SourceComputedAudio_Start__validation_4
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_4:
.a16
.i16
 lda.l SourceComputedAudio_Chunks
 bne SourceComputedAudio_Start__validation_5
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_5:
.a16
.i16
 cmp #385
 bcc SourceComputedAudio_Start__validation_6
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_6:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 sta.l SourceComputedAudio_Temp
 asl a
 asl a
 asl a
 clc
 adc.l SourceComputedAudio_Temp
 cmp.l SourceComputedAudio_Bytes
 bcs SourceComputedAudio_Start__validation_7
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_7:
.a16
.i16
 sta.l SourceComputedAudio_Temp
 clc
 adc.l SourceComputedAudio_Offset
 bcs SourceComputedAudio_Start__padding_bad
 cmp #$D801
 bcc SourceComputedAudio_Start__padding_bounds
SourceComputedAudio_Start__padding_bad:
.a16
.i16
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__padding_bounds:
.a16
.i16
 sta.l SourceComputedAudio_TransferEnd
 lda.l SourceComputedAudio_Temp
 sec
 sbc #144
 cmp.l SourceComputedAudio_Bytes
 bcc SourceComputedAudio_Start__validation_8
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_8:
.a16
.i16
 ; Every intermediate block must lack END/LOOP; the final block has END
 ; alone. The caller's complete payload remains immutable during this walk.
 lda.l SourceComputedAudio_Offset
 tax
 ldy #1
SourceComputedAudio_Start__block:
.a16
.i16
 lda.l $420000,x
 and #3
 sta.l SourceComputedAudio_Temp
 tya
 cmp.l SourceComputedAudio_Blocks
 beq SourceComputedAudio_Start__last
 lda.l SourceComputedAudio_Temp
 cmp #0
 beq SourceComputedAudio_Start__validation_9
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__validation_9:
.a16
.i16
 txa
 clc
 adc #9
 tax
 iny
 bra SourceComputedAudio_Start__block
SourceComputedAudio_Start__last:
.a16
.i16
 lda.l SourceComputedAudio_Temp
 cmp #1
 beq SourceComputedAudio_Start__padding
 jmp SourceComputedAudio_Start__invalid
SourceComputedAudio_Start__padding:
.a16
.i16
 txa
 clc
 adc #9
 tax
SourceComputedAudio_Start__padding_byte:
.a16
.i16
 txa
 cmp.l SourceComputedAudio_TransferEnd
 beq SourceComputedAudio_Start__accept
 lda.l $420000,x
 and #$00FF
 bne SourceComputedAudio_Start__invalid
 inx
 bra SourceComputedAudio_Start__padding_byte
SourceComputedAudio_Start__invalid:
.a16
.i16
 lda #2
SourceComputedAudio_Start__reject:
.a16
.i16
 sta.l SourceComputedAudio_Status
 ply
 plx
 pla
 plp
 sec
 rtl
SourceComputedAudio_Start__accept:
.a16
.i16
 lda.l SourceComputedAudio_Offset
 sta.l SourceAudio_BaseLo
 lda.l SourceComputedAudio_Bytes
 sta.l AudioStream_SourceLength
 lda.l SourceComputedAudio_Chunks
 sta.l AudioStream_SourceChunks
 lda #0
 sta.l SourceAudio_LengthHi
 lda #$FFFF ; explicit computed identity, outside the ASAD namespace
 sta.l SourceAudio_Index
 sep #$20
.a8
 lda #$42
 sta.l SourceAudio_BaseBank
 lda #$FF
 sta.l AudioStream_SourceId
 jsl SourceAudio_StartPreparedNear
 rep #$30
.a16
.i16
 lda 5,s
 sta.l SourceComputedAudio_ConsumerGeneration
 lda 3,s
 sta.l SourceComputedAudio_ConsumerGeneration+2
 lda #3
 sta.l SourceComputedAudio_State
 lda #1
 sta.l SourceComputedAudio_Status
 sta.l SourceAudio_Status
 lda.l AudioSemantic_StreamRequestCount
 inc a
 sta.l AudioSemantic_StreamRequestCount
 ply
 plx
 pla
 plp
 clc
 rtl

; Called only after the production completion observer has seen ENVX>0,
; ENVX=0, producer_done and no pending packet. Static namespace streams do
; not select this identity and cannot retire a computed offer.
SourceComputedAudio_OnCompleted:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceAudio_Index
 cmp #$FFFF
 bne SourceComputedAudio_OnCompleted__done
 lda.l SourceComputedAudio_Ready
 cmp #$B66C
 bne SourceComputedAudio_OnCompleted__done
 lda.l SourceComputedAudio_State
 cmp #3
 bne SourceComputedAudio_OnCompleted__done
 lda.l SourceComputedAudio_Generation
 cmp.l SourceComputedAudio_ConsumerGeneration
 bne SourceComputedAudio_OnCompleted__done
 lda.l SourceComputedAudio_Generation+2
 cmp.l SourceComputedAudio_ConsumerGeneration+2
 bne SourceComputedAudio_OnCompleted__done
 lda #4
 sta.l SourceComputedAudio_State
 sta.l SourceComputedAudio_Status
SourceComputedAudio_OnCompleted__done:
.a16
.i16
 pla
 plp
 rtl
