; ============================================================================
; core/error.pasm — self-contained crash handler
;
; Ported to Poppy syntax from SNES-SuperBossGaiden (src/core/error.65816 +
; error.h), used with the original author's permission. On trigger: captures
; A/X/Y/D/DB/PB/flags/return-address/error-code into fixed WRAM, resets the
; stack and direct page to known-safe values (so a corrupted stack doesn't
; also corrupt the crash report), forces blank, flashes the screen red, and
; halts with STP — leaving state frozen for inspection instead of silently
; hanging or running off into the weeds.
;
; Deliberately simplified from upstream:
;  - No on-screen text. Upstream renders the error name + register dump using
;    its VWF text engine and a DMA'd-in font (build/data/font/fixed8x8.*),
;    neither of which exist in this project. A plain red screen is the
;    trade-off: no font asset needed, still an unmistakable "something broke"
;    signal, and the interesting values are all sitting in WRAM at fixed
;    addresses for Mesen (or this project's MCP tooling) to read afterward.
;  - No excArgs (upstream optionally captures 2 extra 16-bit words when the
;    caller pushes them before the error code, via macros this project
;    doesn't have). Left out rather than ported half-working — it depended on
;    a calling convention that's easy to get subtly wrong without the
;    surrounding macro system to enforce it.
;  - Error codes trimmed to the ones actually relevant given what's ported so
;    far in this project (see below). Add more as needed; the mechanism
;    doesn't care what the code space actually means.
;
; Usage:
;   @Core_Error_Trigger Error_BadInputDevice
; expands to a `pea`+`jsr`, matching upstream's TRIGGER_ERROR macro. (This
; Poppy build's actual macro-invocation sigil is `@`, the same one used for
; local labels — confirmed by reading Parser.cs directly, since the shipped
; docs disagree with each other and neither matches actual behavior: the
; WLA-DX migration guide says `%`, the user manual shows bare invocation with
; no prefix at all, and both silently produce zero expanded bytes in this
; build. `\param` references inside a macro body are also a hard parse
; error here — bare parameter names, as used below, are what actually works.)
;
; DO NOT call this macro from a spot a branch skips over (i.e. the standard
; `validate / bne past-the-trigger / trigger-on-failure / label:` shape).
; This Poppy build's forward address-estimation pass counts a macro
; invocation as contributing 0 bytes, while the real emit pass correctly
; expands it — so a branch spanning one gets an offset short by the macro's
; real size (6 bytes), landing mid-expansion or looping backward into
; itself. Confirmed by isolated repro. Every caller in core/dma_channel.pasm,
; core/dma.pasm, and core/allocate_wram.pasm inlines `pea code`+
; `jsr Core_Error_Handler` by hand instead for exactly this reason — treat
; that as the real usage pattern, this macro as reference/direct-call-only.
; ============================================================================

.enum 10
	Error_ObjNotFound              .db
	Error_BadParameters            .db
	Error_OutOfVram                .db
	Error_OutOfCgram               .db
	Error_OutOfWram                .db
	Error_InvalidException         .db
	Error_DmaQueueFull             .db
	Error_InvalidDmaChannel        .db
	Error_DmaChannelEmpty          .db
	Error_NoDmaChannel             .db
	Error_InvalidDmaTransferType   .db
	Error_InvalidDmaTransferLength .db
	Error_VallocBadStepsize        .db
	Error_VallocInvalidLength      .db
	Error_CGallocBadStepsize       .db
	Error_CGallocInvalidLength     .db
	Error_CGallocInvalidStart      .db
	Error_WallocInvalidLength      .db
	Error_BadInputDevice           .db
	Error_DivisionByZero           .db
	Error_ValueError               .db
	Error_IndexError               .db
	Error_StackOver                .db
	Error_ObjDisabled              .db
	Error_ObjEnabled               .db
	Error_BadRegisterWidth         .db
	Error_OopClassTableFull        .db
	Error_OopObjListFull           .db
	Error_OopObjRamFull            .db
	Error_MaxException             .db
.ende

.enum $7E0440
	ExcStack   .dw
	ExcA       .dw
	ExcY       .dw
	ExcX       .dw
	ExcDp      .dw
	ExcDb      .db
	ExcPb      .db
	ExcFlags   .db
	ExcPc      .dw
	ExcErr     .dw
.ende

CORE_ERROR_STACK_RESET = $1fff   ; matches scpu_boot's own `ldx #$1fff / txs`
CORE_ERROR_DP_RESET    = $0000

.macro Core_Error_Trigger, code
	pea code
	jsr Core_Error_Handler
.endmacro

Core_Error_Handler:
	php
	rep #$31
.a16
	sta ExcA
	lda 2,s              ; return address left by the jsr in the macro
	dec a
	dec a                ; back up to the jsr opcode itself (3-byte instr)
	sta ExcPc
	lda 4,s               ; error code, pushed by `pea code` before the jsr
	and #$00ff
	cmp #Error_MaxException
	bcc Core_Error_Handler__valid_code
	lda #Error_InvalidException
Core_Error_Handler__valid_code:
	and #$00ff
	sta ExcErr

	tsc
	inc a
	inc a
	inc a                 ; skip past the php byte + 2-byte return address
	sta ExcStack

	lda #CORE_ERROR_STACK_RESET
	tcs                    ; stack may be corrupted; start fresh before we push again
	phb
	phk

	phd
	phx
	phy
	pea 0
	pea CORE_ERROR_DP_RESET
	pld
	plb
	plb

	sei
	sep #$20
.a8
	lda #$80
	sta $2100             ; INIDISP: force blank
	stz $4200              ; NMITIMEN off

	rep #$31
.a16
	pla
	sta ExcY
	pla
	sta ExcX
	pla
	sta ExcDp

	sep #$20
.a8
	pla
	sta ExcPb
	pla
	sta ExcDb
	pla
	sta ExcFlags

	; --- Flash the screen red: no font/string engine here, see header note ---
	stz $2121              ; CGRAM address = color 0 (backdrop)
	lda #$1f
	sta $2122               ; low byte: R=31 G=0 B=0 -> full red
	stz $2122               ; high byte
	lda #$0f
	sta $2100               ; screen on, full brightness

	stp                     ; halt; ExcA/X/Y/Dp/Db/Pb/Flags/Pc/Err/Stack now
	                        ; sit frozen at $7E0440+ for post-mortem inspection
