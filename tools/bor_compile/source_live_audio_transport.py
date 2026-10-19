"""Private TAD IRQ/NMI transport helpers for a root-owned live-audio lease.

The caller owns installation, physical enable, audio admission, and clock
publication.  This module only emits the transport-side interrupt leaves; it
does not acknowledge audio, acquire channel 0, or write the NMITIMEN shadow.

Control row ABI (32 bytes at ``control_base``):
  +0 word  B6D8 when the root has published an initialized control row
  +2 byte  1 only after the cold publisher has returned and audio is physical
  +4 byte  IRQ stage (0=idle, 1=first VIRQ at 128, 2=second VIRQ at 200)
  +6 word  count of owned VIRQ callbacks (diagnostic only)
  +8 byte  nonzero if an unexpected non-audio HDMA bit blocks this owner

The fixed root lease remains $7FFB88 == $B6D0.  The root must install the
owned NMI path so this service increments Nmi_FrameCounter exactly once per
physical field; it must not also run the Core_Nmi_Play counter increment.
"""

from __future__ import annotations


LEASE_ADDRESS = 0x7FFB88
LEASE_MAGIC = 0xB6D0
READY_MAGIC = 0xB6D8
CONTROL_BYTES = 32


def emit(sy, control_base, *, include_pump=False, audio_control=0x7E8120,
         channels=0x7E8140, metadata_table=0x33A000, metadata_samples=30):
    """Emit ``LiveAudio_NmiService`` and ``LiveAudio_Irq``.

    ``sy`` is the parsed main.sym mapping (symbol -> 24-bit CPU address), and
    ``control_base`` is an integer address in WRAM for the 32-byte ABI above.
    Both helpers preserve P/A/X/Y/DP/DBR. NMI returns with RTL; IRQ returns
    with RTI or tail-delegates to ``irq_handler`` while retaining the hardware
    interrupt frame.
    """
    required = (
        "Nmi_FrameCounter", "Nmi_HdmaEnable", "Nmi_HdmaEnableCurrent",
        "Nmi_InterruptFlags", "Tad_StreamOneShotHdmaFence",
        "Tad_StreamLatePump", "irq_handler",
    )
    if include_pump:
        required += (
            "AudioSemantic_FootDieStreamActive", "TadPrivate_stream_pending",
            "TadPrivate_stream_chunks_accepted", "AudioStream_SourceChunks",
            "AudioStream_TransportOnly", "AudioStream_SerialPermit",
            "SourceAudio_Status",
        )
    missing = [name for name in required if name not in sy]
    if missing:
        raise ValueError("LIVE_AUDIO_TRANSPORT_MISSING_SYMBOLS:" + ",".join(missing))
    if not isinstance(control_base, int) or not 0 <= control_base <= 0xFFFFFF - CONTROL_BYTES:
        raise ValueError("LIVE_AUDIO_TRANSPORT_CONTROL_BASE")

    owner = LEASE_ADDRESS
    ready = control_base
    physical = control_base + 2
    stage = control_base + 4
    irq_count = control_base + 6
    if include_pump:
        if (not isinstance(metadata_samples, int) or metadata_samples <= 0 or
                metadata_samples > 0x7FF):
            raise ValueError("LIVE_AUDIO_TRANSPORT_METADATA_SAMPLES")
        for value, name in ((audio_control, "audio_control"), (channels, "channels"),
                            (metadata_table, "metadata_table")):
            if not isinstance(value, int) or not 0 <= value <= 0xFFFFFF:
                raise ValueError("LIVE_AUDIO_TRANSPORT_" + name.upper())
    pump_call = "jsl LiveAudio_Pump" if include_pump else f'jsl ${sy["Tad_StreamLatePump"]:06X}'
    return f'''.snes
; LiveAudio transport ABI. Root owns NMITIMEN ($4200), TAD start/ACK,
; lease admission, and renderer-bank allocation. This owner permits only
; TAD HDMA channel 0 and then runs the existing one-shot fence.
LiveAudio_ControlReady = ${ready:06X}
LiveAudio_PhysicalEnabled = ${physical:06X}
LiveAudio_IrqStage = ${stage:06X}
LiveAudio_IrqCount = ${irq_count:06X}
LiveAudio_HdmaMaskFault = ${control_base + 8:06X}

LiveAudio_NmiService:
    php
    rep #$38
.a16
.i16
    pha
    phx
    phy
    phd
    phb
    ; TAD arithmetic is decimal-sensitive and its backend expects the normal
    ; source leaf ABI: D=0, DP=0, DBR=0. All interrupted values are on stack.
    lda #0
    tcd
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$38
.a16
.i16
    ; This is the actual source frame counter used by TAD's one-credit-per-
    ; field logic. Do not invoke Core_Nmi_Play's increment in the same owner.
    lda.l ${sy["Nmi_FrameCounter"]:06X}
    inc a
    sta.l ${sy["Nmi_FrameCounter"]:06X}
    ; Stay inert until the root's cold publisher has returned and explicitly
    ; published physical enable. No automatic IRQ/NMITIMEN enable occurs here.
    lda.l ${owner:06X}
    cmp #${LEASE_MAGIC:04X}
    beq LiveAudio_NmiOwnerOk
    brl LiveAudio_NmiDone
LiveAudio_NmiOwnerOk:
    lda.l LiveAudio_ControlReady
    cmp #${READY_MAGIC:04X}
    beq LiveAudio_NmiReadyOk
    brl LiveAudio_NmiDone
LiveAudio_NmiReadyOk:
    sep #$20
.a8
    lda.l LiveAudio_PhysicalEnabled
    cmp #1
    beq LiveAudio_NmiPhysicalOk
    brl LiveAudio_NmiDone
LiveAudio_NmiPhysicalOk:
    ; The lease admits audio channel 0 only. Reject any unexpected bit in
    ; either the live HDMAEN value or its shadow before touching hardware.
    lda.l ${sy["Nmi_HdmaEnableCurrent"]:06X}
    and #$FE
    beq LiveAudio_NmiCurrentMaskOk
    brl LiveAudio_NmiHdmaMaskFault
LiveAudio_NmiCurrentMaskOk:
    lda.l ${sy["Nmi_HdmaEnable"]:06X}
    and #$FE
    beq LiveAudio_NmiShadowMaskOk
    brl LiveAudio_NmiHdmaMaskFault
LiveAudio_NmiShadowMaskOk:
    lda.l ${sy["Nmi_HdmaEnableCurrent"]:06X}
    and #$01
    bne LiveAudio_NmiVerifyAudioDma
    lda.l ${sy["Nmi_HdmaEnable"]:06X}
    and #$01
    beq LiveAudio_NmiHdmaCommit
LiveAudio_NmiVerifyAudioDma:
    ; When channel 0 is armed in either source, verify the real TAD DMA
    ; descriptor rather than treating an arbitrary channel-0 user as audio.
    sep #$20
.a8
    lda.l $004300
    cmp #$04
    beq LiveAudio_NmiDmaModeOk
    brl LiveAudio_NmiHdmaMaskFault
LiveAudio_NmiDmaModeOk:
    lda.l $004301
    cmp #$40
    beq LiveAudio_NmiDmaDestOk
    brl LiveAudio_NmiHdmaMaskFault
LiveAudio_NmiDmaDestOk:
    rep #$20
.a16
    lda.l $004302
    cmp #$3C00
    beq LiveAudio_NmiDmaSourceOk
    brl LiveAudio_NmiHdmaMaskFault
LiveAudio_NmiDmaSourceOk:
    sep #$20
.a8
    lda.l $004304
    cmp #$7E
    beq LiveAudio_NmiDmaBankOk
    brl LiveAudio_NmiHdmaMaskFault
LiveAudio_NmiDmaBankOk:
LiveAudio_NmiHdmaCommit:
    lda.l ${sy["Nmi_HdmaEnable"]:06X}
    and #$01
    sta.l ${sy["Nmi_HdmaEnableCurrent"]:06X}
    sta.l $00420C
    jsl ${sy["Tad_StreamOneShotHdmaFence"]:06X}
    ; Start each field's two-stage VIRQ schedule at scanline 128. The root
    ; must have enabled VIRQ in $4200 (A1) before setting physical-enabled.
    lda.l ${sy["Nmi_InterruptFlags"]:06X}
    and #$20
    bne LiveAudio_NmiVirqEnabled
    brl LiveAudio_NmiDone
LiveAudio_NmiVirqEnabled:
    lda #1
    sta.l LiveAudio_IrqStage
    lda #128
    sta.l $004209
    lda #0
    sta.l $00420A
    bra LiveAudio_NmiDone
LiveAudio_NmiHdmaMaskFault:
    sep #$20
.a8
    lda #1
    sta.l LiveAudio_HdmaMaskFault
LiveAudio_NmiDone:
    rep #$30
.a16
.i16
    plb
    pld
    ply
    plx
    pla
    plp
LiveAudio_NmiRtl:
    rtl

LiveAudio_Irq:
    php
    rep #$38
.a16
.i16
    pha
    phx
    phy
    phd
    phb
    lda #0
    tcd
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$38
.a16
.i16
    sep #$20
.a8
    lda.l $004211                  ; acknowledge TIMEUP before either path
    rep #$20
.a16
    lda.l ${owner:06X}
    cmp #${LEASE_MAGIC:04X}
    bne LiveAudio_IrqDelegate
    lda.l LiveAudio_ControlReady
    cmp #${READY_MAGIC:04X}
    bne LiveAudio_IrqDelegate
    sep #$20
.a8
    lda.l LiveAudio_PhysicalEnabled
    cmp #1
    bne LiveAudio_IrqDelegate
    lda.l ${sy["Nmi_InterruptFlags"]:06X}
    and #$20
    beq LiveAudio_IrqDelegate
    lda.l LiveAudio_IrqStage
    cmp #1
    beq LiveAudio_IrqFirst
    cmp #2
    beq LiveAudio_IrqSecond
    bra LiveAudio_IrqReturn

LiveAudio_IrqFirst:
    ; First real VIRQ: 128. This is the existing stream-only late pump, not
    ; ordinary foreground TAD processing and not an audio ACK.
    {pump_call}
    rep #$20
.a16
    lda.l LiveAudio_IrqCount
    inc a
    sta.l LiveAudio_IrqCount
    sep #$20
.a8
    lda #200
    sta.l $004209
    lda #0
    sta.l $00420A
    lda #2
    sta.l LiveAudio_IrqStage
    bra LiveAudio_IrqReturn

LiveAudio_IrqSecond:
    ; Second real VIRQ: 200. LatePump is frame-idempotent in the TAD driver;
    ; this second opportunity lets an SPC ACK arrive after the first pump.
    {pump_call}
    rep #$20
.a16
    lda.l LiveAudio_IrqCount
    inc a
    sta.l LiveAudio_IrqCount
    sep #$20
.a8
    lda #0
    sta.l LiveAudio_IrqStage
    bra LiveAudio_IrqReturn

LiveAudio_IrqDelegate:
    ; Restore the exact interrupted CPU context, then leave the hardware IRQ
    ; frame untouched for the pre-existing vector owner.
    rep #$30
.a16
.i16
    plb
    pld
    ply
    plx
    pla
    plp
    jml ${sy["irq_handler"]:06X}

LiveAudio_IrqReturn:
    rep #$30
.a16
.i16
    plb
    pld
    ply
    plx
    pla
    plp
LiveAudio_IrqRti:
    rti
''' + (emit_pump(sy, control_base, audio_control, channels, metadata_table, metadata_samples,
                    control_base + 10)
       if include_pump else "")


def emit_pump(sy, transport_control, audio_control, channels, metadata_table,
              metadata_samples, prefill_target):
    """Emit opt-in serial-prefill and durable-completion wrapper.

    The wrapper observes the source driver's accepted/pending/status fields;
    it never synthesizes an ACK or DSP completion.  The immutable metadata
    table supplies channel 11's terminal phase only after the backend reports
    durable completion.
    """
    active = sy["AudioSemantic_FootDieStreamActive"]
    pending = sy["TadPrivate_stream_pending"]
    accepted = sy["TadPrivate_stream_chunks_accepted"]
    source_chunks = sy["AudioStream_SourceChunks"]
    transport_only = sy["AudioStream_TransportOnly"]
    permit = sy["AudioStream_SerialPermit"]
    status = sy["SourceAudio_Status"]
    channel11 = channels + 11 * 40
    compact_active = 0x7EFF8E + 11 * 8
    row_offset = audio_control + 18
    terminal_base = metadata_table + 12 + 16
    max_bytes = metadata_samples * 32
    return f'''
; Optional owned TAD pump wrapper. Audio CONTROL+2 is root-owned ticket/ACK
; state: preserve it and observe the immutable CONTROL tag plus real status.
LiveAudio_Pump:
    php
    rep #$38
.a16
.i16
    pha
    phx
    phy
    phd
    phb
    lda #0
    tcd
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$38
.a16
.i16
    lda.l ${LEASE_ADDRESS:06X}
    cmp #${LEASE_MAGIC:04X}
    beq LiveAudio_PumpOwnerOk
    brl LiveAudio_PumpDone
LiveAudio_PumpOwnerOk:
    lda.l ${transport_control:06X}
    cmp #${READY_MAGIC:04X}
    beq LiveAudio_PumpReadyOk
    brl LiveAudio_PumpDone
LiveAudio_PumpReadyOk:
    sep #$20
.a8
    lda.l ${transport_control + 2:06X}
    cmp #1
    beq LiveAudio_PumpPhysicalOk
    brl LiveAudio_PumpDone
LiveAudio_PumpPhysicalOk:
    sep #$20
.a8
    lda.l ${active:06X}
    bne LiveAudio_PumpStreamActive
    brl LiveAudio_PumpCheckCompletion
LiveAudio_PumpStreamActive:
    jsl LiveAudio_PrefillUpdate
    jsl ${sy['Tad_StreamLatePump']:06X}
    rep #$38
.a16
.i16
    lda #0
    tcd
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$38
.a16
.i16
    jsl LiveAudio_PrefillUpdate
LiveAudio_PumpCheckCompletion:
    ; The inactive-source branch arrives directly from the A8 active-byte
    ; test. Establish the word ABI on every edge into this shared join.
    rep #$20
.a16
    ; Retirement requires the actual backend completion, inactive physical
    ; source, and no outstanding transfer. No status write occurs here.
    lda.l ${status:06X}
    cmp #4
    beq LiveAudio_PumpStatusOk
    brl LiveAudio_PumpDone
LiveAudio_PumpStatusOk:
    lda.l ${audio_control:06X}
    cmp #$B6D9
    beq LiveAudio_PumpAudioTicketOk
    brl LiveAudio_PumpDone
LiveAudio_PumpAudioTicketOk:
    sep #$20
.a8
    lda.l ${active:06X}
    beq LiveAudio_PumpInactive
    brl LiveAudio_PumpDone
LiveAudio_PumpInactive:
    lda.l ${pending:06X}
    beq LiveAudio_PumpNoPending
    brl LiveAudio_PumpDone
LiveAudio_PumpNoPending:
    rep #$20
.a16
    lda.l ${channel11:06X}
    ora.l ${channel11 + 2:06X}
    bne LiveAudio_PumpChannelActive
    brl LiveAudio_PumpDone
LiveAudio_PumpChannelActive:
    ; Validate row offset (32-byte aligned and within immutable table) before
    ; reading the terminal phase. Invalid metadata leaves the row untouched.
    lda.l ${row_offset:06X}
    and #$001F
    beq LiveAudio_PumpOffsetAligned
    brl LiveAudio_PumpDone
LiveAudio_PumpOffsetAligned:
    lda.l ${row_offset:06X}
    cmp #${max_bytes:04X}
    bcc LiveAudio_PumpOffsetValid
    brl LiveAudio_PumpDone
LiveAudio_PumpOffsetValid:
    tax
    lda.l ${terminal_base:06X},x
    sta.l ${channel11 + 32:06X}
    lda.l ${terminal_base + 2:06X},x
    sta.l ${channel11 + 34:06X}
    lda #0
    sta.l ${channel11:06X}
    sta.l ${channel11 + 2:06X}
    sta.l ${compact_active:06X}
LiveAudio_PumpDone:
    rep #$30
.a16
.i16
    plb
    pld
    ply
    plx
    pla
    plp
    rtl

; During the first seven real ACKed chunks, keep the stream in its serial
; transport mode. Permit one submission only when no transfer is pending.
LiveAudio_PrefillUpdate:
    php
    rep #$38
.a16
.i16
    pha
    phx
    sep #$20
.a8
    lda.l ${active:06X}
    beq LiveAudio_PrefillDone
    rep #$20
.a16
    lda.l ${source_chunks:06X}
    cmp #7
    bcc LiveAudio_PrefillTargetReady
    lda #7
LiveAudio_PrefillTargetReady:
    sta.l ${prefill_target:06X}
    lda.l ${accepted:06X}
    cmp.l ${prefill_target:06X}
    bcs LiveAudio_PrefillComplete
    sep #$20
.a8
    lda #2
    sta.l ${transport_only:06X}
    lda.l ${pending:06X}
    bne LiveAudio_PrefillNoPermit
    lda #1
    sta.l ${permit:06X}
    bra LiveAudio_PrefillDone
LiveAudio_PrefillNoPermit:
    lda #0
    sta.l ${permit:06X}
    bra LiveAudio_PrefillDone
LiveAudio_PrefillComplete:
    sep #$20
.a8
    lda #0
    sta.l ${transport_only:06X}
    sta.l ${permit:06X}
LiveAudio_PrefillDone:
    rep #$30
.a16
.i16
    plx
    pla
    plp
    rtl

'''
