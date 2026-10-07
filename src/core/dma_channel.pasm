; ============================================================================
; core/dma_channel.pasm — hardware DMA channel (0-7) allocation tracker
;
; Ported to Poppy syntax from SNES-SuperBossGaiden (src/core/dma_channel.65816
; + dma_channel.h), used with the original author's permission. A simple
; one-byte-per-channel "is this channel in use" bitmap over the SNES's 8
; hardware DMA channels ($43x0-$43x9 x8).
;
; Deviation from upstream: upstream's init permanently reserves channels 1
; and 2 for its own memory-clear and NMI-DMA subsystems, neither of which
; exist in this project. Left unreserved here — all 8 channels start free.
; Reserve specific channels at the call site if a future subsystem needs one
; pinned (core/dma.pasm reserves channel 7 for the transfer queue itself —
; see its header comment).
;
; Uses global (not @-local) labels throughout — see core/random.pasm's header
; comment for why.
;
; Indexed WRAM access below uses `.l` (or, for STZ which has no long
; addressing mode, `lda #0`+`sta.l`), never `.w`. Confirmed by isolated
; repro: `sta.w Symbol,x` on a bank-$7E symbol picks the correct opcode
; (long,X, since the address needs a bank byte) but only emits 2 of its 3
; operand bytes — the missing bank byte gets silently filled at runtime by
; whatever byte follows in the instruction stream (i.e. the next
; instruction's own opcode), corrupting both the target address and eating
; that next instruction. `stz.l Symbol,x` doesn't error either — STZ simply
; has no long addressing mode on real 65816, so it silently emits a
; malformed instruction that doesn't correspond to anything the CPU can
; decode correctly. Plain `.l` on LDA/STA/ADC/etc. (which do have a long
; form) is correct and was verified byte-for-byte against `.w`'s output.
;
; `@Core_Error_Trigger` is never invoked directly below — its `pea`+`jsr`
; are inlined by hand at each call site instead. Confirmed by isolated
; repro: this Poppy build's forward address-estimation pass counts a macro
; invocation as contributing 0 bytes, while the real emit pass correctly
; expands it to its full size. Any branch that skips over a macro
; invocation (exactly the shape every validation check here needs — branch
; past the trigger on the valid path) gets an offset computed short by the
; macro's real size, landing mid-expansion or, worse, looping backward into
; itself. Inlining the two plain instructions sizes correctly.
; ============================================================================

; `.ds N` is not a valid .enum size modifier in this Poppy build (only
; .db/.dw/.dl are — confirmed by isolated repro, it silently drops the symbol
; instead of erroring). Plain constants, matching main.pasm's own convention
; for RAM variables (see e.g. `Tad_flags = $7E0030`), sidestep that entirely.
DMA_CHANNELS_COUNT = 8
DmaChannels = $7E0460   ; 1 byte/channel: 0=free, nonzero=allocated ($7E0460-$7E0467)

Core_DmaChannel_Init:
	rep #$31
.a16
	lda #0
	ldx #0
Core_DmaChannel_Init__clear_loop:
.a16
.i16
	sta.l DmaChannels,x
	inx
	cpx #DMA_CHANNELS_COUNT
	bcc Core_DmaChannel_Init__clear_loop
	rts

; @return carry<bool>  set if a channel was found
; @return a<8-bit>     allocated channel id (only meaningful if carry set)
Core_DmaChannel_Allocate:
	sep #$20
.a8
	ldx #0
Core_DmaChannel_Allocate__scan:
.a8
.i16
	lda.l DmaChannels,x
	beq Core_DmaChannel_Allocate__found
	inx
	cpx #DMA_CHANNELS_COUNT
	bcc Core_DmaChannel_Allocate__scan

	clc
	rts

Core_DmaChannel_Allocate__found:
.a8
.i16
	lda #1
	sta.l DmaChannels,x
	txa
	sec
	rts

; @param a<8-bit>  channel id to release
Core_DmaChannel_Deallocate:
	sep #$20
.a8
	and #$ff
	tax
	cpx #DMA_CHANNELS_COUNT
	bcc Core_DmaChannel_Deallocate__valid_channel
	; Inlined instead of `@Core_Error_Trigger` — see header note: this
	; Poppy build's forward address-estimation pass counts a macro
	; invocation as 0 bytes, so a branch (like the bcc/bne above) that
	; skips over one lands short/wrong. Confirmed by isolated repro.
	pea Error_InvalidDmaChannel
	jsr Core_Error_Handler

Core_DmaChannel_Deallocate__valid_channel:
	lda.l DmaChannels,x
	bne Core_DmaChannel_Deallocate__was_allocated
	pea Error_DmaChannelEmpty
	jsr Core_Error_Handler

Core_DmaChannel_Deallocate__was_allocated:
.a8
.i16
	; STZ has no long addressing mode on 65816 — `.l` on it doesn't error here,
	; it silently emits a malformed encoding (confirmed by isolated repro).
	; lda #0 / sta.l is the correct equivalent.
	lda #0
	sta.l DmaChannels,x
	rts
