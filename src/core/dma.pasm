; ============================================================================
; core/dma.pasm — budget-capped DMA transfer queue, drained during NMI
;
; Ported (heavily trimmed and redesigned) from SNES-SuperBossGaiden
; (src/core/dma.65816 + dma.h), used with the original author's permission.
; The idea: routines that want to update VRAM/OAM/CGRAM register a transfer
; here instead of firing DMA immediately, so nothing has to block waiting
; for vblank. Core_Dma_ProcessQueue (call once per frame, during NMI/forced
; blank) fires everything that's pending. A running per-frame byte budget
; (Core_Dma_CheckLength/RemainingFree) lets callers avoid registering more
; than fits in one vblank.
;
; Deliberately different from upstream, not just re-syntaxed:
;  - Calling convention: upstream's core.dma.registerTransfer takes its 4
;    parameters (source addr, target addr, length, type|flags) via a `pea`
;    chain immediately before the `jsr`, then reads them back off the stack
;    at hand-computed offsets. That's fast but fragile — get an offset wrong
;    and you silently read the wrong caller's data. This port instead has
;    the caller fill DmaRequest_* WRAM fields, then call with no stack
;    trickery. Slightly slower, much harder to misuse.
;  - Transfer types: upstream supports 6 (VRAM word, 2 tileline variants,
;    32x32 sprite-tile interlace, OAM, CGRAM). The 3 dropped here are tightly
;    coupled to SuperBossGaiden's own VRAM tilemap/interlace layout — they'd
;    be unverifiable dead code in this project. VRAM word transfer, OAM, and
;    CGRAM (the 3 kept) are the general-purpose ones.
;  - No immediateTransfer (upstream's synchronous bypass-the-queue path) —
;    it depends on an NMI-control subsystem (core.nmi.stop/start) that
;    hasn't been ported. Queue-only for now.
;  - Fixed to hardware DMA channel 7 rather than dynamically allocating one
;    via core/dma_channel.pasm — simpler, and this is the only DMA queue in
;    the project so far, so there's nothing to contend with for the channel.
;  - Target addresses for VRAM/CGRAM are BYTE addresses (matching upstream's
;    convention) — Core_Dma_TransferVram/Cgram divide by 2 internally to get
;    the VRAM word address / CGRAM color index. OAM target addresses are
;    used as-is.
;
; Uses global (not @-local) labels throughout — see core/random.pasm's header
; comment for why.
;
; Indexed WRAM access uses `.l`, never `.w` — see core/dma_channel.pasm's
; header note for why `.w` on an indexed bank-$7E symbol silently corrupts
; the instruction stream in this Poppy build. The one STZ site (no long
; addressing mode exists for it at all) is `lda #0`/`sta.l` instead.
;
; `@Core_Error_Trigger` is never invoked directly below, same reason as
; core/dma_channel.pasm: this Poppy build's forward address-estimation pass
; counts a macro invocation as 0 bytes, so any branch skipping over one
; (every validation check here needs exactly that shape) gets a wrong
; offset. `pea`+`jsr Core_Error_Handler` inlined by hand instead.
; ============================================================================

DMA_QUEUE_SLOTS = 8              ; must be a power of two
DMA_QUEUE_SLOT_SIZE = 8          ; bytes per slot
DMA_TRANSFER_MAX_BYTES = $0b00   ; per-frame budget cap, matches upstream's default

DMA_TYPE_VRAM  = 0
DMA_TYPE_OAM   = 1
DMA_TYPE_CGRAM = 2
DMA_TYPE_MAX   = 3

DMA_OPT_REVERSE      = $20   ; PPU-to-CPU instead of CPU-to-PPU (readback)
DMA_OPT_ACTIVE       = $40   ; slot occupied / transfer pending
DMA_OPT_FIXED_SOURCE = $80   ; don't advance source address (fill-style transfer)
DMA_OPT_MASK = DMA_OPT_REVERSE | DMA_OPT_ACTIVE | DMA_OPT_FIXED_SOURCE

; --- Caller-filled request staging area ---
DmaRequest_SourceAddrLow = $7E0470   ; .dw — source address, low+mid byte
DmaRequest_SourceBank    = $7E0472   ; .db — source address, bank byte
DmaRequest_TargetAddr    = $7E0473   ; .dw — see "Target addresses" note above
DmaRequest_Length        = $7E0475   ; .dw — must be nonzero
DmaRequest_TypeFlags     = $7E0477   ; .db — DMA_TYPE_* | optional DMA_OPT_FIXED_SOURCE/REVERSE

; --- Queue state ---
DmaQueue_CurrentSlot = $7E0478   ; .dw — byte offset into DmaQueue, wraps at SLOTS*SIZE
DmaQueue_BudgetTotal = $7E047A   ; .dw — bytes registered so far this frame
DmaQueue_ProcessRemaining = $7E047E ; .dw — bounded NMI ring-scan count

; --- Queue storage: 8 slots x 8 bytes = 64 bytes ($7E0480-$7E04BF) ---
; Per-slot layout (offsets from the slot's own base):
;   +0,+1  transferLength   (dw)
;   +2,+3  targetAddress    (dw)
;   +4     transferType     (db, DMA_TYPE_* | DMA_OPT_* packed together)
;   +5,+6  sourceAddressLow (dw)
;   +7     sourceBank       (db)
DmaQueue = $7E0480
; Zero means no producer-specific completion fence.  Source-sized visual
; publication uses tokens 1..6 here without changing the public eight-byte
; queue-slot ABI.
DmaQueue_Owner = $7E4600

Core_Dma_Init:
	rep #$31
.a16
	lda #0
	sta DmaQueue_CurrentSlot
	sta DmaQueue_BudgetTotal
	sep #$20
.a8
	ldx #0
	lda #0
Core_Dma_Init__owner_clear:
.i16
	sta.l DmaQueue_Owner,x
	inx
	cpx #DMA_QUEUE_SLOTS
	bcc Core_Dma_Init__owner_clear
	rep #$31
.a16
	ldx #0
Core_Dma_Init__clear_loop:
	sta.l DmaQueue,x
	inx
	inx
	cpx #DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE
	bcc Core_Dma_Init__clear_loop
	rts

; Fill DmaRequest_* above, then call this. Does not touch DmaQueue_CurrentSlot
; (that's only advanced by Core_Dma_ProcessQueue) — always starts scanning
; from wherever draining last left off.
; @return carry<bool>  set if the transfer was queued
Core_Dma_Enqueue:
	php
	sei
	rep #$31
.a16
	lda DmaRequest_TypeFlags
	and #$00ff
	cmp #DMA_TYPE_MAX
	bcc Core_Dma_Enqueue__valid_type
	; Inlined instead of `@Core_Error_Trigger` — see header note.
	pea Error_InvalidDmaTransferType
	jsr Core_Error_Handler

Core_Dma_Enqueue__valid_type:
	lda DmaRequest_Length
	bne Core_Dma_Enqueue__valid_length
	pea Error_InvalidDmaTransferLength
	jsr Core_Error_Handler

Core_Dma_Enqueue__valid_length:
	lda DmaQueue_CurrentSlot
	and #(DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE) - 1
	tax
	ldy #DMA_QUEUE_SLOTS

Core_Dma_Enqueue__scan:
	sep #$20
.a8
	lda.l DmaQueue+4,x
	bit #DMA_OPT_ACTIVE
	beq Core_Dma_Enqueue__found_slot
	rep #$31
.a16
	txa
	clc
	adc #DMA_QUEUE_SLOT_SIZE
	and #(DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE) - 1
	tax
	dey
	bne Core_Dma_Enqueue__scan

	; queue full
	rep #$31
.a16
	plp
	clc
	rts

Core_Dma_Enqueue__found_slot:
	rep #$31
.a16
	lda DmaRequest_SourceAddrLow
	sta.l DmaQueue+5,x
	lda DmaRequest_TargetAddr
	sta.l DmaQueue+2,x
	lda DmaRequest_Length
	sta.l DmaQueue+0,x

	clc
	adc DmaQueue_BudgetTotal
	sta DmaQueue_BudgetTotal

	sep #$20
.a8
	lda DmaRequest_SourceBank
	sta.l DmaQueue+7,x

	; only mark active after everything else is written — if ProcessQueue
	; runs (e.g. via NMI) partway through this routine, a half-written slot
	; must not look like a real pending transfer.
	lda DmaRequest_TypeFlags
	ora #DMA_OPT_ACTIVE
	sta.l DmaQueue+4,x

	rep #$31
.a16
	plp
	sec
	rts

; Non-mutating peek: does Core_Dma_Enqueue currently have a free slot to
; scan into? Callers that must commit other state (e.g. a stream cache's
; Tile2Slot/Slot2Tile tables) BEFORE they know a DMA source/target, need to
; know enqueue will succeed before committing that state -- committing it
; and then having Enqueue fail on a full queue leaves the cache believing a
; tile occupies a slot whose physical VRAM content was never written,
; producing silent, permanent corruption until the slot is next evicted.
; Nothing can insert into the queue between this check and the caller's own
; Enqueue call in this single-threaded main-loop flow (NMI only drains,
; never fills), so a free slot found here is guaranteed still free then.
; @return carry<bool>  set if at least one inactive slot exists
Core_Dma_HasFreeSlot:
	php
	sei
	rep #$31
.a16
	lda DmaQueue_CurrentSlot
	and #(DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE) - 1
	tax
	ldy #DMA_QUEUE_SLOTS
Core_Dma_HasFreeSlot__scan:
	sep #$20
.a8
	lda.l DmaQueue+4,x
	bit #DMA_OPT_ACTIVE
	beq Core_Dma_HasFreeSlot__found
	rep #$31
.a16
	txa
	clc
	adc #DMA_QUEUE_SLOT_SIZE
	and #(DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE) - 1
	tax
	dey
	bne Core_Dma_HasFreeSlot__scan

	rep #$31
.a16
	plp
	clc
	rts

Core_Dma_HasFreeSlot__found:
	rep #$31
.a16
	plp
	sec
	rts

; @param a<16-bit>  size of a transfer you're considering registering
; @return carry<bool>  set if it would still fit in this frame's budget
Core_Dma_CheckLength:
	rep #$31
.a16
	clc
	adc DmaQueue_BudgetTotal
	cmp #DMA_TRANSFER_MAX_BYTES
	bcs Core_Dma_CheckLength__wont_fit
	sec
	rts
Core_Dma_CheckLength__wont_fit:
	clc
	rts

; @return a<16-bit>  bytes still free in this frame's DMA budget (0 if over)
Core_Dma_RemainingFree:
	rep #$31
.a16
	lda #DMA_TRANSFER_MAX_BYTES
	sec
	sbc DmaQueue_BudgetTotal
	bcs Core_Dma_RemainingFree__done
	lda #0
Core_Dma_RemainingFree__done:
	rts

; Fires every pending transfer. Screen must be in forced blank (or actual
; vblank) when this runs, same requirement as upstream, or VRAM/CGRAM writes
; will be ignored/corrupted by hardware.
Core_Dma_ProcessQueue:
	rep #$31
.a16
	lda DmaQueue_CurrentSlot
	lda #DMA_QUEUE_SLOTS
	sta DmaQueue_ProcessRemaining
	lda DmaQueue_CurrentSlot

Core_Dma_ProcessQueue__loop:
	and #(DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE) - 1
	sta DmaQueue_CurrentSlot
	tax

	sep #$20
.a8
	lda.l DmaQueue+4,x
	bit #DMA_OPT_ACTIVE
	beq Core_Dma_ProcessQueue__skip

	and #~DMA_OPT_MASK
	cmp #DMA_TYPE_VRAM
	bne Core_Dma_ProcessQueue__try_oam
	jsr Core_Dma_TransferVram
	bra Core_Dma_ProcessQueue__next

Core_Dma_ProcessQueue__try_oam:
	cmp #DMA_TYPE_OAM
	bne Core_Dma_ProcessQueue__try_cgram
	jsr Core_Dma_TransferOam
	bra Core_Dma_ProcessQueue__next

Core_Dma_ProcessQueue__try_cgram:
	cmp #DMA_TYPE_CGRAM
	bne Core_Dma_ProcessQueue__bad_type
	jsr Core_Dma_TransferCgram
	bra Core_Dma_ProcessQueue__next

Core_Dma_ProcessQueue__bad_type:
	rep #$31
.a16
	; Inlined instead of `@Core_Error_Trigger` — see header note. This one
	; matters beyond itself: the three `bra Core_Dma_ProcessQueue__next`
	; above all jump forward across this same macro invocation, so an
	; uncounted-macro-size bug here also breaks all three of those branches.
	pea Error_InvalidDmaTransferType
	jsr Core_Error_Handler

Core_Dma_ProcessQueue__next:
	; STZ has no long addressing mode on 65816 — `.l` on it doesn't error,
	; it silently emits a malformed instruction (see header note). lda #0 /
	; sta.l is the correct equivalent. Explicit sep #$20 here too: A was left
	; 16-bit by the transfer handler this came from, and a 16-bit stz/sta at
	; +4,x would clobber the low byte of the slot's sourceAddressLow (+5) as
	; well as the transferType/active byte we actually mean to clear.
	sep #$20
.a8
	lda #0
	sta.l DmaQueue+4,x
	; Clear the optional owner token at the same queue slot.
	pha
	txa
	lsr a
	lsr a
	lsr a
	tay
	tya
	tax
	pla
	sep #$20
.a8
	lda #0
	sta.l DmaQueue_Owner,x
	rep #$31
.a16
	lda.l DmaQueue_ProcessRemaining
	dec a
	sta.l DmaQueue_ProcessRemaining
	beq Core_Dma_ProcessQueue__done
	lda DmaQueue_CurrentSlot
	clc
	adc #DMA_QUEUE_SLOT_SIZE
	bra Core_Dma_ProcessQueue__loop

Core_Dma_ProcessQueue__skip:
	; Empty slots do not terminate the ring scan.  Other producers may have
	; occupied later slots while the rotating cursor is being serviced.
	rep #$31
.a16
	lda.l DmaQueue_ProcessRemaining
	dec a
	sta.l DmaQueue_ProcessRemaining
	beq Core_Dma_ProcessQueue__done
	lda DmaQueue_CurrentSlot
	clc
	adc #DMA_QUEUE_SLOT_SIZE
	bra Core_Dma_ProcessQueue__loop

Core_Dma_ProcessQueue__done:
	rep #$31
.a16
; --- Poppy-fork migration: low16 aliases for STZ/INC/DEC/STX/STY/LDX/LDY/BIT/
; TSB/TRB/CPX/CPY/ASL/LSR/ROL/ROR/indirect-indexed JSR(,x)/JMP(,x) sites below.
; Real 65816 has no absolute-long encoding for these mnemonics. Old Poppy
; silently truncated a $7Exxxx operand to its low 16 bits (2-byte absolute,
; DBR-relative); new Poppy correctly refuses to do this truncation implicitly.
; This project confines all code+data to ROM bank 0 (see CLAUDE.md), and DBR
; is never set outside {$00-$3F,$7E,$7F} at runtime, so for any symbol whose
; offset is <$2000 the WRAM mirror at $0000-$1FFF (present in every bank
; $00-$3F/$80-$BF) makes the plain 2-byte absolute form land on the exact
; same physical byte as the canonical $7Exxxx symbol, regardless of DBR's
; exact value. These _Lo aliases reproduce that byte-identical encoding
; explicitly. Use ONLY at a site with no long-addressing alternative --
; never as a general substitute for the canonical long-addressed symbol.
DmaQueue_BudgetTotal_Lo = $047A

	stz.w DmaQueue_BudgetTotal_Lo
	rts

; --- Transfer handlers. Entered with x = current slot's byte offset. ---
; All use hardware DMA channel 7 ($4370-$4376 / MDMAEN bit 7).

Core_Dma_TransferVram:
	rep #$31
.a16
	lda.l DmaQueue+5,x
	sta $4372              ; A1T7L/H: source address low+high
	lda.l DmaQueue+2,x
	lsr a                    ; byte address -> VRAM word address
	sta $2116               ; VMADDL/H
	lda.l DmaQueue+0,x
	sta $4375                ; DAS7L/H: transfer size

	sep #$20
.a8
	lda #$80                 ; VMAIN: increment by 1 word after $2119 write
	sta $2115
	lda.l DmaQueue+7,x
	sta $4374                ; A1T7B: source bank
	lda #$01                 ; DMAP7: 2 regs write once (word mode)
	sta $4370
	lda #$18                 ; BBAD7: low byte of $2118 (VMDATAL)
	sta $4371
	lda #$80                 ; MDMAEN bit 7
	sta $420b

	rep #$31
.a16
	rts

Core_Dma_TransferOam:
	rep #$31
.a16
	lda.l DmaQueue+5,x
	sta $4372
	lda.l DmaQueue+2,x
	sta $2102               ; OAMADDL+OAMADDH (16-bit store spans both)
	lda.l DmaQueue+0,x
	sta $4375

	sep #$20
.a8
	lda.l DmaQueue+7,x
	sta $4374
	lda #$00                 ; DMAP7: 1 reg write once
	sta $4370
	lda #$04                 ; BBAD7: low byte of $2104 (OAMDATA)
	sta $4371
	lda #$80
	sta $420b

	rep #$31
.a16
	rts

Core_Dma_TransferCgram:
	rep #$31
.a16
	lda.l DmaQueue+5,x
	sta $4372
	lda.l DmaQueue+0,x
	sta $4375
	lda.l DmaQueue+2,x
	lsr a                    ; byte address -> CGRAM color index

	sep #$20
.a8
	sta $2121                ; CGADD
	lda.l DmaQueue+7,x
	sta $4374
	lda #$00                 ; DMAP7: 1 reg write once
	sta $4370
	lda #$22                 ; BBAD7: low byte of $2122 (CGDATA)
	sta $4371
	lda #$80
	sta $420b

	rep #$31
.a16
	rts
