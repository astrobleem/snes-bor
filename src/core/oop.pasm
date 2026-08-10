; ============================================================================
; core/oop.pasm — object/entity dispatch engine
;
; Ported (heavily redesigned) from SNES-SuperBossGaiden (src/core/oop.65816 +
; oop.h + src/include/object.include), used with the original author's
; permission. Gives out fixed slots to "objects" (entities), each with its
; own direct-page RAM window, dispatches a per-frame play routine to every
; live object, and reclaims (compacting) an object's RAM when it's killed.
;
; This is NOT a byte-for-byte port — upstream's version is a whole-game
; framework (60+ hand-authored classes registered through a macro DSL,
; interface/mixin routine tables, cross-bank JSL-callable twins of every
; entry point). This project has zero entities and is single-bank, so the
; game-specific class table and the cross-bank "extend.*" duplicates aren't
; ported at all — what's here is the generic dispatch engine upstream's
; game-specific code sits on top of, redesigned where this Poppy build's
; toolchain or this project's toolchain makes upstream's exact mechanism
; impractical (see the specific notes below).
;
; ----------------------------------------------------------------------------
; Key differences from upstream, and why:
;
; - Classes register themselves at RUNTIME (Core_Oop_RegisterClass), not via
;   upstream's compile-time macro-generated `OopClassWordLut`. Poppy has no
;   equivalent of WLA-DX's `.STRUCT`/`.ramsection`/per-class macro system, and
;   this project has no classes yet to generate a table for regardless.
;
; - No `.rept`-unrolled per-slot search (upstream's `extend.oop.seekFreeSlot`
;   etc, `.rept maxNumberOopObjs`). Plain linear scans instead — same
;   reasoning as every other allocator in `src/core/`: much less code, and
;   the unrolled-macro pattern's behavior in this Poppy build (specifically
;   its per-iteration `\@` unique-label counter) has never been verified.
;
; - Object slots and the class table are parallel arrays (OopFlags[],
;   OopClassId[], OopNum[], ...), not an array of upstream's `oopStackObj`
;   structs. Poppy has no struct/sizeof support, and this sidesteps ever
;   needing struct-offset*index arithmetic — every array is indexed by the
;   same plain byte-offset (0, 2, 4, ...), which is also exactly the form
;   `jsr (Table,x)` indirect dispatch needs (see below). The upstream
;   struct-index conversion macros (`HASH_POINTER_TO_INDEX` etc.) don't
;   exist here because there's nothing left for them to convert between.
;
; - Calling into a class's routine uses plain `jsr (Table,x)` (65816 absolute
;   indexed indirect, opcode $FC) instead of upstream's trick of pushing a
;   computed target address plus a separate fixed return address onto the
;   stack and `rts`-ing into it. Both work; the indirect-JSR form doesn't
;   depend on precise manual stack-frame bookkeeping, which matters more
;   than usual in a toolchain that's already shown it miscompiles some
;   addressing-mode choices silently (see core/dma_channel.pasm's header).
;   Verified correct in this Poppy build via an isolated repro (encodes to
;   `$FC` + a plain 2-byte absolute operand — no long/short ambiguity for
;   the assembler to get wrong, unlike the STZ/STA cases documented below).
;
;   `jsr (Table,x)` reads its pointer table from the CURRENT PROGRAM BANK
;   (always bank $00 here — this whole project is `.bank 0`), and then jumps
;   to a plain 16-bit address (bank implied = $00, also always correct here).
;   That's why every routine-pointer array (OopPlay/OopCurrent/ClassInit/
;   etc.) below MUST live inside the $7E0000-$7E1FFF bank-0 WRAM mirror —
;   outside that window, bank $00's own memory is hardware registers/ROM,
;   not the WRAM these arrays actually live in.
;
; - Direct-page addressing has the same $0000-$1FFF-only constraint (DP
;   addressing is always bank-0-relative, regardless of `DB`, by hardware
;   definition) — so every object's private per-instance RAM (`OopObjRam`)
;   also has to live in that same mirror, sharing it with the hardware stack
;   (`scpu_boot` sets `S = $1FFF`) and every other core module's scratch
;   state. See core/allocate_wram.pasm's header for what happens when
;   something in this window collides with the stack — the layout below
;   was sized with a large margin specifically to not repeat that.
;
; - A "handle" (upstream's `oopObjHash`: id + creation-fingerprint + a cached
;   slot pointer, so a stale reference can detect "this isn't the object I
;   remember" even after the slot gets reused, and self-heal by falling back
;   to a full scan) is kept, since that's real, useful behavior — but it's
;   passed and returned BY VALUE across registers/`OopLastHandle_*`, not by
;   passing a pointer for the engine to write through. 65816 pointer
;   dereference into an arbitrary caller-chosen WRAM address needs 24-bit
;   indirect addressing (`[dp]`) with a 3-byte pointer assembled in direct
;   page first — another mode not exercised anywhere in this codebase yet.
;   Avoiding it means callers copy their handle back out after a call that
;   might have moved it (two 16-bit loads/stores — see Core_Oop_Exists'
;   header comment) instead of it happening invisibly; a small, documented
;   convention beats a second unverified addressing mode layered on top of
;   the first one.
;
; - No per-class `rKill` destructor hook — upstream declares one
;   (`OOPR.rKill`) but its own `collectGarbage`/`_setDead` never actually
;   call it anywhere in oop.65816; porting an unused hook forward isn't
;   porting real behavior. `Core_Oop_Call`'s generic command dispatch
;   (`ClassOnCommand`) covers the same need if something ever requires
;   cleanup-on-kill — same generic slot the camera (core/screen.pasm) uses
;   to query the focused object's position, rather than a whole
;   interface/mixin routine-table system.
;
; - Disable/Enable just flip a flag bit; upstream also invokes an
;   `iterator.library.disable/enable` method through its interface-mixin
;   system. Skipped for now (zero consumers of that notification exist yet)
;   — a clearly separable trim, not a cut to the parts of this port the
;   "keep GC/singleton/hash" scope was actually about.
;
; ----------------------------------------------------------------------------
; Handle layout (4 bytes, held by VALUE wherever a caller wants to remember
; an object — e.g. core/screen.pasm's focused-object variable):
;   +0..1  num   (16-bit creation-order fingerprint)
;   +2     id    (8-bit class id)
;   +3     slot  (8-bit cached slot byte-offset — 0, 2, 4, ... — NOT a plain
;                 slot index; using the byte-offset directly as the array
;                 index avoids a multiply/divide by the slot struct size on
;                 every single access)
; `Core_Oop_Create`/singleton-lookup produce a fresh handle in `a`/`y`:
;   a<16-bit> = num, y<16-bit> = id (low byte) | slot (high byte)
; Store it with:  sta MyHandle : sty MyHandle+2
; (`+2` on `MyHandle` is fine — that's the CALLER's own local/global variable
; at a compile-time-fixed address the caller declared, not a computed
; runtime pointer, and not one of the `Symbol+N`-on-a-bank-$7E-symbol sites
; this file avoids — see the note further below on why THIS file never does
; that arithmetic on ITS OWN arrays.)
;
; Functions that consume a handle (Exists/Call/Pause/Resume/...) take it
; back apart into registers instead: `a<16-bit>=num, x<16-bit>=cached slot,
; y<8-bit>=id`. They return `x` = the current slot byte-offset — cheap to
; always re-store back into your handle's `+3` whether it moved or not.
;
; ----------------------------------------------------------------------------
; Indexed WRAM access uses `.l`, never `.w` — see core/dma_channel.pasm's
; header note for why `.w` on an indexed bank-$7E symbol silently corrupts
; the instruction stream in this Poppy build.
;
; Indexed long (`.l`) WRAM access always uses `,x`, never `,y` — real 65816
; has no long-indexed-by-Y addressing mode at all (only `,x`); this Poppy
; build doesn't reject `.l Symbol,y`, it silently emits a plain 3-byte
; absolute,Y instruction instead (bank byte dropped, same failure shape as
; the `.w`-on-indexed-access bug above, but here there's no valid long
; encoding to fall back to in the first place — confirmed by disassembling
; the compiled Core_Oop_Create and finding `LDA $093A,Y` where the source
; said `lda.l ClassPlay,y`). Every class-table lookup below that used to
; index by `y=classOfs` now indexes by `x` instead, stashing whatever `x`
; was already holding (object slot) on the stack or in a scratch var across
; the lookup.
;
; This file never uses `Symbol+N` addressing arithmetic on any of its own
; bank-$7E arrays (only bare `Array,x` with a runtime-incremented x) — see
; core/math.pasm's header for why `Symbol+N` feeding a long-addressable
; instruction (LDA/ADC/STA) can get mis-sized by Poppy's forward
; address-estimation pass. Every place upstream would reach for a
; struct-field offset, this file bumps an index register at runtime instead.
;
; `@Core_Error_Trigger` is never invoked directly below, same reason as
; core/dma_channel.pasm: this Poppy build's forward address-estimation pass
; counts a macro invocation as 0 bytes, so a branch skipping over one gets
; a wrong offset. `pea`+`jsr Core_Error_Handler` inlined by hand instead.
;
; Uses global (not @-local) labels throughout — see core/random.pasm's
; header comment for why.
; ============================================================================

OOP_MAX_OBJECTS  = 24
OOP_MAX_CLASSES  = 16
OOP_OBJ_RAM_SIZE = $0c00   ; 3072 bytes

OBJ_FLAG_PRESENT          = $0001
OBJ_FLAG_DELETE_SCHEDULED = $0002
OBJ_FLAG_PAUSED           = $0004
OBJ_FLAG_DISABLED         = $0008

CLASS_FLAG_SINGLETON = $0001

OBJR_NOERR = 0
OBJR_KILL  = 1

; Offsets within every object's own dp window (self-handle header). Every
; registered class's zpLen must be at least this many bytes.
OOP_SELF_ID_OFS      = 0
OOP_SELF_NUM_OFS     = 1
OOP_SELF_SLOT_OFS    = 3
OOP_SELF_HEADER_SIZE = 4

; --- Bookkeeping scratch (single in-flight call at a time, like every other
; core/*.pasm routine in this codebase — not reentrant). ---
.enum $7E074A
	OopObjIndex       .dw   ; Play()'s current slot byte-offset cursor
	OopObjSlotPtr     .dw   ; exclusive upper bound: 1 + highest slot byte-offset ever used
	OopObjRamPtr      .dw   ; bump offset into OopObjRam (0..OOP_OBJ_RAM_SIZE)
	OopGarbagePresent .dw   ; nonzero: at least one slot is DeleteScheduled
	OopClassCount     .dw   ; classes registered so far (0..OOP_MAX_CLASSES)
	OopCreateCounter  .dw   ; ever-ascending creation-order fingerprint source

	; Core_Oop_Create's own working scratch
	OopCreate_Param    .dw
	OopCreate_ClassId  .dw
	OopCreate_ClassOfs .dw
	OopCreate_Slot     .dw
	OopCreate_ZpLen    .dw
	OopCreate_RamOfs   .dw
	OopCreate_Dp       .dw

	; caller fills these in, then calls Core_Oop_RegisterClass with no params
	OopRegStaging_Flags     .dw
	OopRegStaging_ZpLen     .dw
	OopRegStaging_Init      .dw
	OopRegStaging_Play      .dw
	OopRegStaging_Pause     .dw
	OopRegStaging_OnCommand .dw

	; Core_Oop_Create / singleton-lookup write the produced handle here too
	OopLastHandle_Num  .dw
	OopLastHandle_Id   .dw   ; low byte valid
	OopLastHandle_Slot .dw   ; low byte valid

	; internal seek helpers' scratch
	OopSeek_Key .dw
	OopSeek_Num .dw

	; Core_Oop__ReclaimSlot's own working scratch
	OopGc_DeadOfs .dw
	OopGc_DeadLen .dw
	OopGc_Src     .dw
	OopGc_Dst     .dw

	; caller fills these in, then calls Core_Oop_Call
	OopCall_Param     .dw
	OopCall_CommandId .dw
	OopCall_Slot       .dw
	OopCall_ClassOfs   .dw
.ende

; --- Object slots: parallel arrays, index = slot byte-offset (0,2,4,...) ---
OopFlags   = $7E078a   ; 48B, .dw x24 — 0 = fully free slot
OopClassId = $7E07ba   ; 48B
OopNum     = $7E07ea   ; 48B
OopDp      = $7E081a   ; 48B — absolute low-16 address of this object's ram window
OopPlay    = $7E084a   ; 48B
OopPause   = $7E087a   ; 48B
OopCurrent = $7E08aa   ; 48B — whichever of Play/Pause is presently active; what Play() dispatches through

; --- Class table: parallel arrays, index = class byte-offset (0,2,4,...) ---
ClassFlags     = $7E08da   ; 32B, .dw x16
ClassZpLen     = $7E08fa   ; 32B
ClassInit      = $7E091a   ; 32B
ClassPlay      = $7E093a   ; 32B
ClassPause     = $7E095a   ; 32B
ClassOnCommand = $7E097a   ; 32B — 0 = class doesn't handle any commands

; general-purpose extra output slots for Core_Oop_Call's callee: its own
; return channel is a single 16-bit `a` (plus carry=handled) — most commands
; don't need more than that, so the engine doesn't reserve space for more by
; default. A command whose contract needs multiple values back (e.g.
; core/screen.pasm's camera-position query) can use these two as an
; additional, documented-per-command convention; the engine itself never
; reads or writes them.
;
; Deliberately declared HERE, as their own fixed addresses in the
; $7E099a-$7E0a00 gap between ClassOnCommand's array (ends $7E099a) and
; OopObjRam (starts $7E0a00) -- NOT as the last two fields of the
; OopObjIndex.. .enum block above. They used to be the last two fields of
; that enum, which put them at $7E078a/$7E078c: EXACTLY OopFlags[0] and
; OopFlags[1] (byte offsets 0 and 2 into the OopFlags array right below,
; which the enum's own fixed base address doesn't leave room for). Nothing
; ever wrote OopCall_ResultX/Y before a real Core_Oop_Call consumer existed
; (see core/screen.pasm's own header: this whole path was "boot-verified
; but not exercised end-to-end"), so the collision sat latent until Phase 8
; wired up the first one -- found via a real, reproducible bug: writing an
; entity's CHAR_POS_X/Y into OopCall_ResultX/Y silently cleared
; OBJ_FLAG_PRESENT on whichever object happened to occupy slot 0 (and
; slot 2's low byte via ResultY), so Core_Oop_Play stopped dispatching it
; forever, one frame after the first camera query ran.
OopCall_ResultX = $7E09a0   ; .dw
OopCall_ResultY = $7E09a2   ; .dw

; --- Per-object private RAM pool (bump-allocated, compacted on GC) ---
OopObjRam    = $7E0a00   ; OOP_OBJ_RAM_SIZE bytes, $7E0a00-$7E15ff
OopObjRam_Lo = $0a00     ; low-16 constant for pointer arithmetic — avoids the
                          ; 24-bit-symbol-truncated-in-a-16-bit-immediate pitfall
                          ; documented in core/allocate_wram.pasm's header (WramBuffer_Lo)

Core_Oop_Init:
	php
	rep #$31
.a16
.i16
	; These arrays are parallel .dw (16-bit) arrays indexed by 2-byte
	; stride -- clearing them in .a8 (as this loop used to) only zeroes
	; the LOW byte of each element, leaving the high byte as whatever
	; boot-time WRAM garbage was already there. Harmless today only
	; because every consumer masks the result with a small constant that
	; discards the high byte anyway (see plan.md Phase 1b's own note on
	; this) -- but OopDp is read UNMASKED by Core_Oop_Play (`lda.l OopDp,x
	; / tcd`), so a garbage high byte there means switching to a garbage
	; direct page the moment a slot is read before Core_Oop_Create has
	; fully written it. Fixed by running this loop in .a16 instead, so
	; each sta.l clears the full 16-bit element.
	ldx #0
Core_Oop_Init__clear_objs:
	lda #0
	sta.l OopFlags,x
	sta.l OopClassId,x
	sta.l OopNum,x
	sta.l OopDp,x
	sta.l OopPlay,x
	sta.l OopPause,x
	sta.l OopCurrent,x
	inx
	inx
	cpx #OOP_MAX_OBJECTS*2
	bcc Core_Oop_Init__clear_objs

	ldx #0
Core_Oop_Init__clear_classes:
	lda #0
	sta.l ClassFlags,x
	sta.l ClassZpLen,x
	sta.l ClassInit,x
	sta.l ClassPlay,x
	sta.l ClassPause,x
	sta.l ClassOnCommand,x
	inx
	inx
	cpx #OOP_MAX_CLASSES*2
	bcc Core_Oop_Init__clear_classes

	stz OopObjIndex
	stz OopObjSlotPtr
	stz OopObjRamPtr
	stz OopGarbagePresent
	stz OopClassCount
	stz OopCreateCounter

	plp
	rts

; caller populates OopRegStaging_* first, then calls this with no params.
; @return carry<bool>  success
; @return a<8-bit>     new class id (1-based; 0 means "no class")
Core_Oop_RegisterClass:
	php
	rep #$31
.a16
	lda OopClassCount
	cmp #OOP_MAX_CLASSES
	bcc Core_Oop_RegisterClass__room_ok
		pea Error_OopClassTableFull
		jsr Core_Error_Handler

Core_Oop_RegisterClass__room_ok:
	lda OopRegStaging_ZpLen
	cmp #OOP_SELF_HEADER_SIZE
	bcs Core_Oop_RegisterClass__zplen_ok
		pea Error_BadParameters
		jsr Core_Error_Handler

Core_Oop_RegisterClass__zplen_ok:
	lda OopClassCount
	asl a
	tax

	lda OopRegStaging_Flags
	sta.l ClassFlags,x
	lda OopRegStaging_ZpLen
	sta.l ClassZpLen,x
	lda OopRegStaging_Init
	sta.l ClassInit,x
	lda OopRegStaging_Play
	sta.l ClassPlay,x
	lda OopRegStaging_Pause
	sta.l ClassPause,x
	lda OopRegStaging_OnCommand
	sta.l ClassOnCommand,x

	inc OopClassCount
	lda OopClassCount

	plp
	sec
	rts

; @return carry<bool>  found
; @return x<16-bit>    free slot byte-offset
Core_Oop__SeekFreeSlot:
	ldx #0
Core_Oop__SeekFreeSlot__scan:
	lda.l OopFlags,x
	and #OBJ_FLAG_PRESENT | OBJ_FLAG_DELETE_SCHEDULED
	beq Core_Oop__SeekFreeSlot__found
	inx
	inx
	cpx #OOP_MAX_OBJECTS*2
	bcc Core_Oop__SeekFreeSlot__scan
	clc
	rts
Core_Oop__SeekFreeSlot__found:
	sec
	rts

; @param a<16-bit>  class id (low byte valid)
; @return carry<bool>  found
; @return x<16-bit>    slot byte-offset
Core_Oop__SeekByClassId:
	and #$00ff
	sta OopSeek_Key
	ldx #0
Core_Oop__SeekByClassId__scan:
	lda.l OopClassId,x
	cmp OopSeek_Key
	bne Core_Oop__SeekByClassId__next
	lda.l OopFlags,x
	and #OBJ_FLAG_PRESENT | OBJ_FLAG_DELETE_SCHEDULED
	cmp #OBJ_FLAG_PRESENT
	bne Core_Oop__SeekByClassId__next
	sec
	rts
Core_Oop__SeekByClassId__next:
	inx
	inx
	cpx #OOP_MAX_OBJECTS*2
	bcc Core_Oop__SeekByClassId__scan
	clc
	rts

; @param a<16-bit>  num
; @param y<16-bit>  class id (low byte valid)
; @return carry<bool>  found
; @return x<16-bit>    slot byte-offset
Core_Oop__SeekByIdNum:
	sta OopSeek_Num
	tya
	and #$00ff
	sta OopSeek_Key
	ldx #0
Core_Oop__SeekByIdNum__scan:
	lda.l OopClassId,x
	cmp OopSeek_Key
	bne Core_Oop__SeekByIdNum__next
	lda.l OopNum,x
	cmp OopSeek_Num
	bne Core_Oop__SeekByIdNum__next
	lda.l OopFlags,x
	and #OBJ_FLAG_PRESENT | OBJ_FLAG_DELETE_SCHEDULED
	cmp #OBJ_FLAG_PRESENT
	bne Core_Oop__SeekByIdNum__next
	sec
	rts
Core_Oop__SeekByIdNum__next:
	inx
	inx
	cpx #OOP_MAX_OBJECTS*2
	bcc Core_Oop__SeekByIdNum__scan
	clc
	rts

; @param x<16-bit>  slot byte-offset (preserved)
; writes id/num/slot into OopLastHandle_*
Core_Oop__PackHandle:
	lda.l OopNum,x
	sta OopLastHandle_Num
	lda.l OopClassId,x
	sta OopLastHandle_Id
	sep #$20
.a8
	txa
	sta OopLastHandle_Slot
	rep #$31
.a16
	rts

; @param  OopCreate_RamOfs, OopCreate_ZpLen
Core_Oop__ClearObjRam:
	ldx OopCreate_RamOfs
	ldy OopCreate_ZpLen
Core_Oop__ClearObjRam__loop:
	lda #0
	sta.l OopObjRam,x
	inx
	dey
	bne Core_Oop__ClearObjRam__loop
	rts

; @param a<16-bit>  init parameter, passed to the class's Init routine in A
; @param y<8-bit>   class id (as returned by Core_Oop_RegisterClass)
; @return carry<bool>  set if a slot was allocated (even if Init immediately
;                       killed it) or an existing singleton was found
; @return a<16-bit>    OopLastHandle_Num (mirrors what's now in OopLastHandle_*)
; @return x<16-bit>    the object's dp window base address (bank $7E)
Core_Oop_Create:
	php
	rep #$31
.a16
	sta OopCreate_Param
	tya
	and #$00ff
	sta OopCreate_ClassId
	dec a                    ; class id is 1-based; class array offset is 0-based
	asl a
	tax
	stx OopCreate_ClassOfs

	lda.l ClassFlags,x
	and #CLASS_FLAG_SINGLETON
	beq Core_Oop_Create__not_singleton

	lda OopCreate_ClassId
	jsr Core_Oop__SeekByClassId
	bcc Core_Oop_Create__not_singleton
		jsr Core_Oop__PackHandle
		lda.l OopDp,x
		tax
		lda OopLastHandle_Num
		plp
		sec
		rts

Core_Oop_Create__not_singleton:
	jsr Core_Oop__SeekFreeSlot
	bcs Core_Oop_Create__slot_ok
		pea Error_OopObjListFull
		jsr Core_Error_Handler

Core_Oop_Create__slot_ok:
	stx OopCreate_Slot

	ldx OopCreate_ClassOfs
	lda.l ClassZpLen,x
	and #$00ff
	sta OopCreate_ZpLen

	lda OopObjRamPtr
	clc
	adc OopCreate_ZpLen
	cmp #OOP_OBJ_RAM_SIZE
	bcc Core_Oop_Create__ram_ok
		pea Error_OopObjRamFull
		jsr Core_Error_Handler

Core_Oop_Create__ram_ok:
	lda OopObjRamPtr
	sta OopCreate_RamOfs
	clc
	adc #OopObjRam_Lo
	sta OopCreate_Dp

	lda OopObjRamPtr
	clc
	adc OopCreate_ZpLen
	sta OopObjRamPtr

	ldx OopCreate_Slot
	lda #OBJ_FLAG_PRESENT
	sta.l OopFlags,x
	lda OopCreate_ClassId
	sta.l OopClassId,x

	lda OopCreateCounter
	inc a
	sta OopCreateCounter
	sta.l OopNum,x

	lda OopCreate_Dp
	sta.l OopDp,x

	; 65816 long addressing has no ,Y indexed form (only ,X) — read both
	; class routine pointers via x=classOfs first, stash on the stack, then
	; switch x back to the object's slot to store them.
	ldx OopCreate_ClassOfs
	lda.l ClassPlay,x
	pha
	lda.l ClassPause,x
	pha
	ldx OopCreate_Slot
	pla
	sta.l OopPause,x
	pla
	sta.l OopPlay,x
	sta.l OopCurrent,x

	; track highest-used slot bound (exclusive)
	txa
	clc
	adc #2
	cmp OopObjSlotPtr
	bcc Core_Oop_Create__slotptr_ok
		sta OopObjSlotPtr
Core_Oop_Create__slotptr_ok:

	jsr Core_Oop__ClearObjRam

	; write this object's own self-handle into its dp window: offset 0=id
	; (1B), offset 1-2=num(2B), offset 3=slot(1B). Index via x, bumped at
	; runtime between fields rather than compile-time Symbol+N — see header
	; note on why this file never uses +N on a bank-$7E array symbol.
	ldx OopCreate_RamOfs
	sep #$20
.a8
	lda OopCreate_ClassId
	sta.l OopObjRam,x
	rep #$31
.a16
	inx
	lda OopCreateCounter
	sta.l OopObjRam,x
	inx
	inx
	sep #$20
.a8
	lda OopCreate_Slot
	sta.l OopObjRam,x
	rep #$31
.a16

	; call the class's Init with dp switched to this object's window
	lda OopCreate_Dp
	phd
	tcd
	lda OopCreate_Param
	ldx OopCreate_ClassOfs
	jsr (ClassInit,x)
	pld

	cmp #OBJR_NOERR
	beq Core_Oop_Create__init_ok
		ldx OopCreate_Slot
		lda.l OopFlags,x
		ora #OBJ_FLAG_DELETE_SCHEDULED
		sta.l OopFlags,x
		lda #1
		sta OopGarbagePresent
Core_Oop_Create__init_ok:

	ldx OopCreate_Slot
	jsr Core_Oop__PackHandle
	lda OopCreate_Dp
	tax
	lda OopLastHandle_Num
	plp
	sec
	rts

; @param a<16-bit>  num
; @param x<16-bit>  cached slot byte-offset hint (from your handle's +3)
; @param y<8-bit>   class id (your handle's +2, low byte valid)
; @return carry<bool>  set if the object is still present
; @return x<16-bit>    current slot byte-offset — cheap to always re-store
;                       into your handle's +3 whether it moved or not
Core_Oop_Exists:
	sta OopSeek_Num
	cpx #OOP_MAX_OBJECTS*2
	bcs Core_Oop_Exists__reseek
	tya
	and #$00ff
	sta OopSeek_Key
	lda.l OopClassId,x
	cmp OopSeek_Key
	bne Core_Oop_Exists__reseek
	lda.l OopNum,x
	cmp OopSeek_Num
	bne Core_Oop_Exists__reseek
	lda.l OopFlags,x
	and #OBJ_FLAG_PRESENT
	beq Core_Oop_Exists__reseek
	sec
	rts

Core_Oop_Exists__reseek:
	lda OopSeek_Num
	jsr Core_Oop__SeekByIdNum
	rts

; @param a<16-bit>  num
; @param x<16-bit>  cached slot byte-offset hint
; @param y<8-bit>   class id
; @return carry<bool>  set if found and paused
; @return x<16-bit>    current slot byte-offset
Core_Oop_Pause:
	jsr Core_Oop_Exists
	bcc Core_Oop_Pause__done
	lda.l OopFlags,x
	ora #OBJ_FLAG_PAUSED
	sta.l OopFlags,x
	lda.l OopPause,x
	sta.l OopCurrent,x
	sec
Core_Oop_Pause__done:
	rts

; same params/return as Core_Oop_Pause
Core_Oop_Resume:
	jsr Core_Oop_Exists
	bcc Core_Oop_Resume__done
	lda.l OopFlags,x
	and #$fffb              ; clear OBJ_FLAG_PAUSED ($0004)
	sta.l OopFlags,x
	lda.l OopPlay,x
	sta.l OopCurrent,x
	sec
Core_Oop_Resume__done:
	rts

; same params as Core_Oop_Pause; @return carry set if found AND paused
Core_Oop_IsPaused:
	jsr Core_Oop_Exists
	bcc Core_Oop_IsPaused__done
	lda.l OopFlags,x
	and #OBJ_FLAG_PAUSED
	bne Core_Oop_IsPaused__yes
	clc
	rts
Core_Oop_IsPaused__yes:
	sec
Core_Oop_IsPaused__done:
	rts

; same params/return as Core_Oop_Pause
Core_Oop_Disable:
	jsr Core_Oop_Exists
	bcc Core_Oop_Disable__done
	lda.l OopFlags,x
	ora #OBJ_FLAG_DISABLED
	sta.l OopFlags,x
	sec
Core_Oop_Disable__done:
	rts

; same params/return as Core_Oop_Pause
Core_Oop_Enable:
	jsr Core_Oop_Exists
	bcc Core_Oop_Enable__done
	lda.l OopFlags,x
	and #$fff7              ; clear OBJ_FLAG_DISABLED ($0008)
	sta.l OopFlags,x
	sec
Core_Oop_Enable__done:
	rts

; same params as Core_Oop_Pause; @return carry set if found AND disabled
Core_Oop_IsDisabled:
	jsr Core_Oop_Exists
	bcc Core_Oop_IsDisabled__done
	lda.l OopFlags,x
	and #OBJ_FLAG_DISABLED
	bne Core_Oop_IsDisabled__yes
	clc
	rts
Core_Oop_IsDisabled__yes:
	sec
Core_Oop_IsDisabled__done:
	rts

; externally-callable kill: schedules the object for deletion (collected by
; the next Core_Oop_Play/CollectGarbage pass), same as an object's own
; play/init routine returning OBJR_KILL.
; same params/return as Core_Oop_Pause
Core_Oop_Destroy:
	jsr Core_Oop_Exists
	bcc Core_Oop_Destroy__done
	lda.l OopFlags,x
	ora #OBJ_FLAG_DELETE_SCHEDULED
	sta.l OopFlags,x
	lda #1
	sta OopGarbagePresent
	sec
Core_Oop_Destroy__done:
	rts

; generic message send — used for things like core/screen.pasm's camera
; querying whatever object it's focused on for its position, without the
; engine needing to know that object's concrete class. Caller sets
; OopCall_Param/OopCall_CommandId first; the callee (class's OnCommand
; routine) reads OopCall_CommandId directly (not via a register — A and X
; are already spoken for by the dispatch itself) and returns
; @param a<16-bit>=result, @return carry=handled.
;
; @param a<16-bit>  num
; @param x<16-bit>  cached slot byte-offset hint
; @param y<8-bit>   class id
; @return carry<bool>  set if object found AND its class handles this command
; @return a<16-bit>    the command's result (only meaningful if carry set)
; @return x<16-bit>    current slot byte-offset
Core_Oop_Call:
	jsr Core_Oop_Exists
	bcs Core_Oop_Call__found
	rts
Core_Oop_Call__found:
	; 65816 long addressing has no ,Y indexed form (only ,X) — stash the
	; object's slot first, repurpose x for the classOfs-indexed read, then
	; reload the slot back into x before using it again below.
	stx OopCall_Slot
	lda.l OopClassId,x
	and #$00ff
	dec a                    ; class id is 1-based; class array offset is 0-based
	asl a
	tax
	lda.l ClassOnCommand,x
	beq Core_Oop_Call__unhandled
	stx OopCall_ClassOfs

	ldx OopCall_Slot
	lda.l OopDp,x
	phd
	tcd
	lda OopCall_Param
	ldx OopCall_ClassOfs
	jsr (ClassOnCommand,x)
	pld
	ldx OopCall_Slot
	rts

Core_Oop_Call__unhandled:
	clc
	rts

; called every frame: dispatch every present, non-disabled, non-scheduled
; object's `current` (play or pause) routine, then reclaim any garbage.
Core_Oop_Play:
	php
	rep #$31
.a16
	ldx #0
	cpx OopObjSlotPtr
	bcs Core_Oop_Play__done

Core_Oop_Play__loop:
	stx OopObjIndex
	lda.l OopFlags,x
	and #OBJ_FLAG_PRESENT | OBJ_FLAG_DELETE_SCHEDULED | OBJ_FLAG_DISABLED
	cmp #OBJ_FLAG_PRESENT
	bne Core_Oop_Play__skip

	lda.l OopDp,x
	phd
	tcd
	jsr (OopCurrent,x)
	pld

	cmp #OBJR_NOERR
	beq Core_Oop_Play__skip
		ldx OopObjIndex
		lda.l OopFlags,x
		ora #OBJ_FLAG_DELETE_SCHEDULED
		sta.l OopFlags,x
		lda #1
		sta OopGarbagePresent

Core_Oop_Play__skip:
	ldx OopObjIndex
	inx
	inx
	cpx OopObjSlotPtr
	bcc Core_Oop_Play__loop

Core_Oop_Play__done:
	plp
	jmp Core_Oop_CollectGarbage

; scans for objects scheduled for deletion, reclaims their ram (shifting
; later objects' ram down to close the gap, and adjusting their dp
; pointers), and frees their slot. Callable on its own, and always run at
; the end of Core_Oop_Play.
Core_Oop_CollectGarbage:
	php
	rep #$31
.a16
	lda OopGarbagePresent
	beq Core_Oop_CollectGarbage__done

	; loop cursor lives in memory, not x — Core_Oop__ReclaimSlot below does not
	; preserve x (it has its own internal loops), so a register-only cursor
	; here would get corrupted the moment a reclaim actually happens.
	stz OopObjIndex
	lda OopObjIndex
	cmp OopObjSlotPtr
	bcs Core_Oop_CollectGarbage__reset_flag

Core_Oop_CollectGarbage__loop:
	ldx OopObjIndex
	lda.l OopFlags,x
	and #OBJ_FLAG_DELETE_SCHEDULED
	beq Core_Oop_CollectGarbage__skip
		jsr Core_Oop__ReclaimSlot
Core_Oop_CollectGarbage__skip:
	lda OopObjIndex
	clc
	adc #2
	sta OopObjIndex
	cmp OopObjSlotPtr
	bcc Core_Oop_CollectGarbage__loop

Core_Oop_CollectGarbage__reset_flag:
	stz OopGarbagePresent

Core_Oop_CollectGarbage__done:
	plp
	rts

; @param x<16-bit>  slot byte-offset of the DeleteScheduled object to reclaim
;                    (x is NOT preserved — CollectGarbage's loop reloads it
;                    from its own cursor after this call)
Core_Oop__ReclaimSlot:
	lda.l OopDp,x
	sec
	sbc #OopObjRam_Lo
	sta OopGc_DeadOfs
	lda.l OopClassId,x
	and #$00ff
	dec a                    ; class id is 1-based; class array offset is 0-based
	asl a
	; 65816 long addressing has no ,Y indexed form (only ,X) — stash the
	; slot being reclaimed on the stack, use x for the classOfs-indexed
	; read, then restore it (the clear-bookkeeping block below needs x=slot).
	phx
	tax
	lda.l ClassZpLen,x
	and #$00ff
	sta OopGc_DeadLen
	plx

	; fully clear this slot's bookkeeping
	lda #0
	sta.l OopFlags,x
	sta.l OopClassId,x
	sta.l OopNum,x
	sta.l OopDp,x
	sta.l OopPlay,x
	sta.l OopPause,x
	sta.l OopCurrent,x

	; shift pool-relative [deadOfs+deadLen .. OopObjRamPtr) down by deadLen bytes
	lda OopGc_DeadOfs
	clc
	adc OopGc_DeadLen
	sta OopGc_Src
	lda OopGc_DeadOfs
	sta OopGc_Dst

Core_Oop__ReclaimSlot__shift:
	lda OopGc_Src
	cmp OopObjRamPtr
	bcs Core_Oop__ReclaimSlot__shift_done

	sep #$20
.a8
	ldx OopGc_Src
	lda.l OopObjRam,x
	ldx OopGc_Dst
	sta.l OopObjRam,x
	rep #$31
.a16

	inc OopGc_Src
	inc OopGc_Dst
	bra Core_Oop__ReclaimSlot__shift

Core_Oop__ReclaimSlot__shift_done:
	lda OopObjRamPtr
	sec
	sbc OopGc_DeadLen
	sta OopObjRamPtr

	; adjust every other slot's dp if it pointed at or after the freed block
	ldx #0
	cpx OopObjSlotPtr
	bcs Core_Oop__ReclaimSlot__adjust_done
Core_Oop__ReclaimSlot__adjust_loop:
	lda.l OopFlags,x
	beq Core_Oop__ReclaimSlot__adjust_next
	lda.l OopDp,x
	sec
	sbc #OopObjRam_Lo
	cmp OopGc_DeadOfs
	bcc Core_Oop__ReclaimSlot__adjust_next
	sec
	sbc OopGc_DeadLen
	clc
	adc #OopObjRam_Lo
	sta.l OopDp,x
Core_Oop__ReclaimSlot__adjust_next:
	inx
	inx
	cpx OopObjSlotPtr
	bcc Core_Oop__ReclaimSlot__adjust_loop
Core_Oop__ReclaimSlot__adjust_done:

	; shrink the slot bound while the trailing slot(s) are now fully free
Core_Oop__ReclaimSlot__shrink:
	lda OopObjSlotPtr
	beq Core_Oop__ReclaimSlot__shrink_done
	sec
	sbc #2
	tax
	lda.l OopFlags,x
	bne Core_Oop__ReclaimSlot__shrink_done
	stx OopObjSlotPtr
	bra Core_Oop__ReclaimSlot__shrink
Core_Oop__ReclaimSlot__shrink_done:
	rts
