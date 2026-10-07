; ASAD1 source namespace capability. Table and payload are compiler-owned;
; absent/malformed namespace admission fails without a legacy source alias.
; E-bank ROM data is byte-addressed and may cross 64 KiB boundaries.
SourceAudio_Table          = $3CC000
SourceAudio_BaseLo         = $7E28E4 ; .dw
SourceAudio_BaseBank       = $7E28E6 ; .db
SourceAudio_ReadBank       = $7E28E7 ; .db
SourceAudio_OffsetHi       = $7E28E8 ; .dw
SourceAudio_PendingHi      = $7E28EA ; .dw
SourceAudio_LengthHi       = $7E28EC ; .dw
SourceAudio_ReadTemp       = $7E28EE ; .db
SourceAudio_Status         = $7E28F0 ; .dw, 1=requested, 2=invalid, 3=busy, 4=DSP completed
SourceAudio_Index          = $7E28F2 ; .dw source namespace identity
SourceAudio_RequestIndex   = $7E28F4 ; .dw pending admission; never replaces active identity on rejection
SourceAudio_EnvelopeSeen   = $7E28F8 ; .dw nonzero DSP ENVX observed this epoch
SourceAudio_PacketLo       = $7E28F6 ; .dw packet-local pointer / output cursor

; A16 source sound index; C clear=request accepted, C set=explicit fault.
; Caller preserves the source event until accepted. No silent preemption.
SourceAudio_Start:
.a16
.i16
    php
    rep #$31
    pha
    phx
    phy
    sta.l SourceAudio_RequestIndex
    lda.l AudioSemantic_FootDieStreamActive
    and #$00ff
    beq SourceAudio_Start__idle
    lda #3
    jmp SourceAudio_Start__bad_status
SourceAudio_Start__idle:
.a16
.i16
    lda.l SourceAudio_Table
    cmp #$5341
    beq SourceAudio_Start__validated1
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated1:
.a16
.i16
    lda.l SourceAudio_Table+2
    cmp #$4441
    beq SourceAudio_Start__validated2
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated2:
.a16
.i16
    lda.l SourceAudio_Table+4
    cmp #1
    beq SourceAudio_Start__validated3
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated3:
.a16
.i16
    lda.l SourceAudio_Table+6
    bne SourceAudio_Start__validated4
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated4:
.a16
.i16
    cmp #2048 ; $3C:C000..FFFF: header plus at most 2047 rows
    bcc SourceAudio_Start__validated5
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated5:
.a16
.i16
    lda.l SourceAudio_RequestIndex
    cmp.l SourceAudio_Table+6
    bcc SourceAudio_Start__validated6
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated6:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceAudio_Table+10,x
    and #$00ff
    cmp #$e0
    bcs SourceAudio_Start__validated7
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated7:
.a16
.i16
    cmp #$f0
    bcc SourceAudio_Start__validated8
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated8:
.a16
.i16
    lda.l SourceAudio_Table+13,x
    and #$00ff
    cmp #16
    bcc SourceAudio_Start__validated9
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated9:
.a16
.i16
    sta.l SourceAudio_LengthHi
    lda.l SourceAudio_Table+8,x
    sta.l SourceAudio_BaseLo
    lda.l SourceAudio_Table+11,x
    sta.l AudioStream_SourceLength
    lda.l SourceAudio_Table+14,x
    bne SourceAudio_Start__validated10
    jmp SourceAudio_Start__bad
SourceAudio_Start__validated10:
.a16
.i16
    sta.l AudioStream_SourceChunks
    lda.l SourceAudio_RequestIndex
    sta.l SourceAudio_Index
    sep #$20
.a8
    lda.l SourceAudio_Table+10,x
    sta.l SourceAudio_BaseBank
    lda #$ff
    sta.l AudioStream_SourceId
    jsl SourceAudio_StartPreparedNear
    rep #$20
.a16
    lda.l AudioSemantic_StreamRequestCount
    inc a
    sta.l AudioSemantic_StreamRequestCount
    lda #1
    sta.l SourceAudio_Status
    ply
    plx
    pla
    plp
    clc
    rtl
SourceAudio_Start__bad:
.a16
.i16
    lda #2
SourceAudio_Start__bad_status:
.a16
.i16
    sta.l SourceAudio_Status
    ply
    plx
    pla
    plp
    sec
    rtl

; Bridge the bank-12 prepared-state RTS entry through its existing RTL relay.
SourceAudio_StartRelay = (Tad_ProcessMaybeStream__return & $ffff)-1
SourceAudio_StartTarget = (Tad_StreamStartPreparedSource & $ffff)-1
SourceAudio_StartPreparedNear:
.a8
.i16
    pea SourceAudio_StartRelay
    lda #^Tad_StreamStartPreparedSource
    pha
    pea SourceAudio_StartTarget
    rtl

SourceAudio_PrepareRead:
.a16
.i16
    php
    pha
    lda.l AudioStream_SourceId
    and #$00ff
    cmp #$ff
    bne SourceAudio_PrepareRead__done
    lda.l SourceAudio_BaseBank
    and #$00ff
    clc
    adc.l SourceAudio_OffsetHi
    sep #$20
.a8
    sta.l SourceAudio_ReadBank
    rep #$20
.a16
SourceAudio_PrepareRead__done:
.a16
.i16
    pla
    plp
    rtl

; A8 byte, X16 logical low offset. Preserve X/Y/D/P. The 24-bit pointer is
; constructed on the CPU stack, which is in real low WRAM. A direct-page
; pointer at $28xx would instead read unmapped bank-0 memory.
SourceAudio_ReadByte:
.a8
.i16
    php
    phd
    phy
    lda.l SourceAudio_ReadBank
    pha
    rep #$20
.a16
    lda.l SourceAudio_BaseLo
    pha
    tsc
    inc a
    tcd
    sep #$20
.a8
    txy
    lda [$00],y
    sta.l SourceAudio_ReadTemp
    rep #$20
.a16
    tsc
    clc
    adc #3
    tcs
    ply
    pld
    sep #$20
.a8
    lda.l SourceAudio_ReadTemp
    plp
    rtl

SourceAudio_ReadCarry:
.a8
.i16
    php
    pha
    lda.l AudioStream_SourceId
    cmp #$ff
    bne SourceAudio_ReadCarry__done
    lda.l SourceAudio_ReadBank
    inc a
    sta.l SourceAudio_ReadBank
SourceAudio_ReadCarry__done:
.a8
.i16
    pla
    plp
    rtl

; A16/I16, C=set when acknowledged source cursor has reached its full length.
SourceAudio_IsDone:
.a16
.i16
    lda.l AudioStream_SourceId
    and #$00ff
    cmp #$ff
    bne SourceAudio_IsDone__low
    lda.l SourceAudio_OffsetHi
    cmp.l SourceAudio_LengthHi
    bcc SourceAudio_IsDone__no
    bne SourceAudio_IsDone__yes
SourceAudio_IsDone__low:
.a16
.i16
    lda.l TadPrivate_stream_source_offset
    cmp.l AudioStream_SourceLength
    rtl
SourceAudio_IsDone__no:
.a16
.i16
    clc
    rtl
SourceAudio_IsDone__yes:
.a16
.i16
    sec
    rtl

; Entry A16/I16 after X has advanced through 144 transfer bytes. C clear
; leaves A16 for the unchanged legacy accounting; C set returns A8 and fully
; publishes generic pending accounting. Offset high changes only after ACK.
SourceAudio_Account:
.a16
.i16
    lda.l AudioStream_SourceId
    and #$00ff
    cmp #$ff
    beq SourceAudio_Account__generic
    clc
    rtl
SourceAudio_Account__generic:
.a16
.i16
    txa
    sta.l TadPrivate_stream_pending_source_offset
    sep #$20
.a8
    lda.l SourceAudio_ReadBank
    sec
    sbc.l SourceAudio_BaseBank
    rep #$20
.a16
    and #$00ff
    sta.l SourceAudio_PendingHi
    cmp.l SourceAudio_LengthHi
    bcc SourceAudio_Account__more
    bne SourceAudio_Account__end
    txa
    cmp.l AudioStream_SourceLength
    bcc SourceAudio_Account__more
SourceAudio_Account__end:
.a16
.i16
    lda.l SourceAudio_LengthHi
    sta.l SourceAudio_PendingHi
    lda.l AudioStream_SourceLength
    sta.l TadPrivate_stream_pending_source_offset
    sep #$20
.a8
    sec
    sbc.l TadPrivate_stream_source_offset
    sta.l TadPrivate_stream_pending_payload
    lda #1
    sta.l TadPrivate_stream_pending_done
    sec
    rtl
SourceAudio_Account__more:
.a16
.i16
    sep #$20
.a8
    lda #144
    sta.l TadPrivate_stream_pending_payload
    lda #0
    sta.l TadPrivate_stream_pending_done
    sec
    rtl

; A8/X16 logical source offset/Y16 output cursor. Build one long pointer
; for the complete packet. IRQ/NMI remain enabled and preserve D/stack.
; Return X=next logical offset, Y=next table cursor, original D/P.
; Same mode-4 rows and loop-header location as the existing transport.
SourceAudio_FillHdmaRows:
.a8
.i16
    php
    rep #$38
.a16
.i16
    phx
    phy
    phd
    txa
    clc
    adc.l SourceAudio_BaseLo
    sta.l SourceAudio_PacketLo
    lda.l SourceAudio_ReadBank
    and #$00ff
    adc #0
    sep #$20
.a8
    pha
    rep #$20
.a16
    lda.l SourceAudio_PacketLo
    pha
    tsc
    inc a
    tcd
    lda 6,s
    tax
    ldy #0
    sep #$20
.a8
SourceAudio_FillHdmaRows__row:
.a8
.i16
    lda #1
    sta.l $7E0000+TAD_STREAM_HDMA_TABLE,x
    inx
    lda.l TadPrivate_stream_command
    sta.l $7E0000+TAD_STREAM_HDMA_TABLE,x
    inx
    lda [$00],y
    sta.l $7E0000+TAD_STREAM_HDMA_TABLE,x
    inx
    iny
    lda [$00],y
    sta.l $7E0000+TAD_STREAM_HDMA_TABLE,x
    inx
    iny
    lda.l TadPrivate_stream_row_token
    sta.l $7E0000+TAD_STREAM_HDMA_TABLE,x
    inx
    inc a
    and #$1f
    sta.l TadPrivate_stream_row_token
    cpy #144
    bne SourceAudio_FillHdmaRows__row
    lda #0
    sta.l TadPrivate_stream_state
    rep #$20
.a16
    txa
    sta.l SourceAudio_PacketLo
    tsc
    clc
    adc #3
    tcs
    pld
    ply
    plx
    txa
    clc
    adc #144
    tax
    bcc SourceAudio_FillHdmaRows__no_logical_carry
    sep #$20
.a8
    lda.l SourceAudio_ReadBank
    inc a
    sta.l SourceAudio_ReadBank
    rep #$20
.a16
SourceAudio_FillHdmaRows__no_logical_carry:
.a16
.i16
    lda.l SourceAudio_PacketLo
    tay
    plp
    rtl

; Foreground-only DSP lifecycle observation. APUIO2 input/output are separate.
; Require nonzero ENVX before zero: delayed KON/prefill cannot finish an epoch.
; Legacy streams retain their existing lifecycle pending their own migration.
SourceAudio_PollCompletion:
.a8
.i16
    php
    pha
    lda.l AudioStream_SourceId
    cmp #$ff
    bne SourceAudio_PollCompletion__done
    lda.l TadPrivate_stream_consumer_started
    beq SourceAudio_PollCompletion__done
    lda.l PARAMETER1_PORT
    beq SourceAudio_PollCompletion__zero
    sta.l SourceAudio_EnvelopeSeen
    bra SourceAudio_PollCompletion__done
SourceAudio_PollCompletion__zero:
.a8
.i16
    lda.l SourceAudio_EnvelopeSeen
    beq SourceAudio_PollCompletion__done
    lda.l TadPrivate_stream_producer_done
    beq SourceAudio_PollCompletion__done
    lda.l TadPrivate_stream_pending
    bne SourceAudio_PollCompletion__done
    lda #0
    sta.l AudioSemantic_FootDieStreamActive
    rep #$20
.a16
    lda #4 ; actual DSP completion; retain namespace identity
    sta.l SourceAudio_Status
    sep #$20
.a8
SourceAudio_PollCompletion__done:
.a8
.i16
    pla
    plp
    rtl
