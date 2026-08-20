; ============================================================================
; core/vm/vm_load.pasm -- Gate 0a: script-VM module transport (plan_vm.md §1)
;
; Moves the VM's bytecode module from bor.msu into WRAM at boot and validates
; its header. Nothing here interprets anything -- Gate 0 (§2) is the first
; interpreter code. The transport is built and verified first on purpose: an
; interpreter debugged against a module that never loaded is unfalsifiable.
;
; This is core/spawn.pasm with a different destination, a header check and a
; status byte. Same php/sei/sep opening, same $2000-$2003 seek, same
; spin-on-$2000-bit7, same byte-at-a-time $2001 read loop. One blocking
; boot-time read, deliberately outside Msu1_StreamBusy's one-stream-per-frame
; budget exactly as Spawn_Init is -- see main.pasm's call site.
;
; Differences from spawn.pasm that are intentional, not oversights:
;   - No `nop` guards before labels. Those are historical: the Poppy jsl-sizing
;     bug that made labels drift is fixed in the astrobleem fork, and
;     tools/rom_audit/check_label_drift.py is the regression detector for that
;     fix. Copying the guards would spend dead bytes out of a 7168-byte budget
;     (plan_vm.md §0.9 item 5).
;   - An explicit width directive on the first line after every label. That one
;     IS still needed: poppy#386 (M/X width inference is linear, not
;     control-flow-aware) is the single assembler bug still live, and
;     tools/rom_audit/check_width_directives.py enforces this rule.
;
; VM_MSU_OFFSET/VM_MODULE_SIZE below are hand-synced build-time constants, for
; the same reason SPAWN_MSU_OFFSET is: the module's file offset depends on every
; character/BG/FP/spawn blob packed before it, which main.pasm cannot know.
; build_rom.py's check_vm_constants() cross-checks both against what
; pack_msu_roster.py actually computed and aborts the build on mismatch, with
; the corrected values in the message.
;
; Global (not @-local) labels throughout, same convention as every other
; core/*.pasm file.
; ============================================================================

; --- Gate 1 (plan_vm.md 3) CRC32 scratch, private to this file's
; Vm_ValidateHeader. Placed directly after vm_run.pasm's VmPriv_CopyLen
; ($7FE0C1, ends $7FE0C3, as of the Gate 1 WRAM-collision relocation -- see
; vm_consts.pasm's header note above VmSlots_Wram) -- does NOT reuse
; vm_run.pasm's VmPriv_Left*/Right* cells, even though they are free this
; early at boot, because vm_run.pasm's own header says "nothing outside this
; file and vm_slots.pasm should reference these"; this file gets its own
; cells instead.
;
; crc0..crc3 are the accumulator's four BYTES, LSB first (crc0) to MSB
; (crc3) -- not two 16-bit words -- because the table-driven update below is
; a byte-shift (crc >> 8), which is free when the bytes are already
; separate: crc0'=crc1, crc1'=crc2, crc2'=crc3, crc3'=0, each XORed against
; the matching byte of the fetched table entry. Cursor is the byte offset
; into the module (VM_MODULE_SIZE fits in a u16).
;
; NOTE: two separate findings got tangled together while this file was
; being debugged against tools/verify/phase9.py, worth untangling for
; whoever reads this next:
;   1. This whole scratch block (and VmState_*/VmPriv_*/VmTrace_Wram/
;      VmSlots_Wram above it) used to sit inside core/stream_cache.pasm's
;      Tile2Slot table ($7F0000-$7F7FFF) -- a real, independent latent bug,
;      found while investigating phase9.py, now fixed by relocating the
;      whole block (see vm_consts.pasm). It was NOT, in the end, what was
;      causing phase9.py to fail: relocating every address reproduced the
;      identical failure byte-for-byte, which rules out a WRAM collision as
;      the cause (a corrupted table would behave differently once the
;      collision was gone, and it didn't).
;   2. phase9.py's failure was separately root-caused to the test harness
;      itself: a dead-cycle-only busy loop (no WRAM writes, no behavioral
;      change) injected at boot on the pre-Gate-1 base commit reproduced
;      the same stall pattern intermittently. phase9's stall metric has
;      zero margin against real-world (wall-clock) timing jitter in the
;      Mesen automation harness (mesen_set_input_wall_clock project
;      memory), and any added boot-time cost -- from either the WRAM fix
;      above or the CRC work here -- can tip it. See phase9.py's own
;      commit history for the actual fix (widened sample cadence).
; The table-driven CRC32 algorithm was kept regardless (cheaper than
; bit-serial, no functional reason to revert), but speeding it up was never
; what fixed phase9.py either -- see finding 2 above. ---
VmLoad_Crc0    = $7FE0C3   ; .db -- accumulator byte 0 (LSB)
VmLoad_Crc1    = $7FE0C4   ; .db -- accumulator byte 1
VmLoad_Crc2    = $7FE0C5   ; .db -- accumulator byte 2
VmLoad_Crc3    = $7FE0C6   ; .db -- accumulator byte 3 (MSB)
VmLoad_Cursor  = $7FE0C7   ; .dw -- module byte offset being folded in

VM_MSU_OFFSET   = $027164   ; from build_rom.py's check_vm_constants -- re-sync
                            ; (rerun the build, paste its reported value) any
                            ; time an earlier roster/BG/FP/spawn asset changes
                            ; size, or the shipped level changes.
VM_MODULE_SIZE  = 424       ; tools/verify/vm_fixtures/boot_spawn_wave1_module.bin, likewise
                            ; checked at build time. Also cross-checked against
                            ; the module's own header field at +$34 below.

; --- Vm_Init -- zero every VmState_* cell and lay down both guard regions.
; Called by Vm_Load before anything else touches VM WRAM. Leaves
; VmState_Status at VMSTAT_UNINIT (0) on purpose: until the loader reports a
; real outcome, "boot zeroed this" and "the loader ran" must stay
; distinguishable (plan_vm.md §0.8). ---
Vm_Init:
    php
    rep #$31
.a16
.i16
    sep #$20
.a8

    ldx #0
Vm_Init__zero_state:
    sep #$20
.a8
    lda #0
    sta.l VM_STATE_FIRST,x
    inx
    cpx #(VM_STATE_LAST-VM_STATE_FIRST)
    bcc Vm_Init__zero_state

    ldx #0
Vm_Init__guard_lo:
    sep #$20
.a8
    lda #VM_GUARD_LO_FILL
    sta.l VmGuardLo,x
    inx
    cpx #VM_GUARD_LEN
    bcc Vm_Init__guard_lo

    ldx #0
Vm_Init__guard_hi:
    sep #$20
.a8
    lda #VM_GUARD_HI_FILL
    sta.l VmGuardHi,x
    inx
    cpx #VM_GUARD_LEN
    bcc Vm_Init__guard_hi

    plp
    rts

; --- Vm_Load -- call once at boot, after MSU-1 is up and BEFORE NMI is
; enabled. See main.pasm's call site for why both halves of that matter. ---
Vm_Load:
    php
    sei
    sep #$20
.a8

    jsr Vm_Init

    sep #$20
.a8
    lda #<(VM_MSU_OFFSET & $0000FF)
    sta $2000
    lda #<((VM_MSU_OFFSET >> 8) & $0000FF)
    sta $2001
    lda #<((VM_MSU_OFFSET >> 16) & $0000FF)
    sta $2002
    lda #0
    sta $2003
Vm_Load__seek_busy:
    sep #$20
.a8
    lda $2000
    bmi Vm_Load__seek_busy

    rep #$31
.a16
.i16
    ldx #0
Vm_Load__read:
    sep #$20
.a8
    lda $2001
    sta.l VmCode_Wram,x
    rep #$31
.a16
.i16
    inx
    cpx #VM_MODULE_SIZE
    bcc Vm_Load__read

    jsr Vm_ValidateHeader

    plp
    rts

; --- Vm_ValidateHeader -- checks FORMAT.md's 64-byte header, in field order.
; Offsets are from VmCode_Wram. Every check is one load / one compare / one
; near branch to the single trampoline at the bottom, so no conditional branch
; here is ever at risk of the 65816's +-127 limit (plan_vm.md §0.9 item 7).
;
; On success: VmState_Status = VMSTAT_READY, VmState_Error = VMERR_NONE.
; On any failure: VMSTAT_FAULT / VMERR_BAD_MODULE. Never leaves the status at
; VMSTAT_UNINIT on either path -- an unwritten status is indistinguishable from
; a loader that never ran, which is exactly what §0.8 numbers UNINIT = 0 to
; keep distinguishable. ---
Vm_ValidateHeader:
    sep #$20
.a8
    lda.l VmCode_Wram+0
    cmp #$42                ; 'B'
    bne Vm_ValidateHeader__header_fail
    lda.l VmCode_Wram+1
    cmp #$34                ; '4'
    bne Vm_ValidateHeader__header_fail
    lda.l VmCode_Wram+2
    cmp #$38                ; '8'
    bne Vm_ValidateHeader__header_fail
    lda.l VmCode_Wram+3
    cmp #$53                ; 'S'
    bne Vm_ValidateHeader__header_fail

    lda.l VmCode_Wram+4
    cmp #1                  ; format_version
    bne Vm_ValidateHeader__header_fail
    lda.l VmCode_Wram+5
    cmp #$30                ; opcode_abi -- 48 opcodes
    bne Vm_ValidateHeader__header_fail
    lda.l VmCode_Wram+6
    cmp #0                  ; numeric_profile -- Q16.16 (plan_vm.md §0.3)
    bne Vm_ValidateHeader__header_fail

    rep #$31
.a16
.i16
    lda.l VmCode_Wram+8     ; instruction_count (u16)
    cmp #(VM_INSTR_MAX+1)
    bcs Vm_ValidateHeader__header_fail
    sta.l VmState_InstrCount

    lda.l VmCode_Wram+10    ; slot_count (u16)
    cmp #(VM_SLOT_MAX+1)
    bcs Vm_ValidateHeader__header_fail
    sta.l VmState_SlotCount

    lda.l VmCode_Wram+$34   ; module_size low 16 bits
    cmp #VM_MODULE_SIZE
    bne Vm_ValidateHeader__header_fail
    lda.l VmCode_Wram+$36   ; module_size high 16 bits
    cmp #0
    bne Vm_ValidateHeader__header_fail
    bra Vm_ValidateHeader__crc_start

; Near trampoline for the header-field checks above (plan_vm.md 0.9 item 7):
; the CRC32 block below is long enough that a direct `bne
; Vm_ValidateHeader__to_fail` from those checks would exceed the 65816's
; +-127 branch range once it was inserted. This local label keeps every
; check above a short, in-range branch; it alone takes the long hop.
Vm_ValidateHeader__header_fail:
    brl Vm_ValidateHeader__to_fail

Vm_ValidateHeader__crc_start:
.a16
.i16
    ; --- CRC32 (Gate 1, plan_vm.md 3 -- deferred from Gate 0a): zlib/
    ; ISO-HDLC variant (poly $EDB88320 reflected, init/final $FFFFFFFF),
    ; table-driven (Vm_Crc32Table, 256 x 4 bytes, generated at repo-build
    ; time and .incbin'd below -- this region has 5000+ bytes free even
    ; after spending the table, and the bit-serial version this replaced
    ; measurably delayed boot enough to tip phase9.py's held-input
    ; throughput gate past its threshold; confirmed by A/B disabling the
    ; loop entirely and rerunning that gate). Covers
    ; VmCode_Wram+$40..+(VM_MODULE_SIZE-1); module_size is already confirmed
    ; == VM_MODULE_SIZE just above, so the compile-time constant is used
    ; directly instead of re-reading the header field.
    ;
    ; The accumulator is kept as four separate BYTES (Crc0 LSB .. Crc3 MSB),
    ; not two 16-bit words: the per-byte update is `crc = table[(crc^byte)
    ; & $FF] ^ (crc >> 8)`, and >>8 on a byte-split accumulator is free
    ; (crc0'=crc1, crc1'=crc2, crc2'=crc3, crc3'=0) -- no shift instruction
    ; needed at all. X is reused for two different things within one
    ; iteration (the module-byte read, then the table-entry read), which is
    ; why the cursor lives in VmLoad_Cursor rather than staying in X across
    ; the whole loop: 65816 long-indexed addressing (`.l Label,x`) is X-only
    ; -- there is no `,y` form (CLAUDE.md) -- so X is the only register
    ; either lookup can use. ---
    sep #$20
.a8
    lda #$FF
    sta.l VmLoad_Crc0
    sta.l VmLoad_Crc1
    sta.l VmLoad_Crc2
    sta.l VmLoad_Crc3
    rep #$31
.a16
.i16
    lda #$0040
    sta.l VmLoad_Cursor

Vm_ValidateHeader__crc_byte:
.a16
.i16
    lda.l VmLoad_Cursor
    cmp #VM_MODULE_SIZE
    bcs Vm_ValidateHeader__crc_done
    tax
    sep #$20
.a8
    lda.l VmCode_Wram,x
    eor.l VmLoad_Crc0            ; A = table index = (crc0 ^ byte)
    rep #$31
.a16
.i16
    and #$00FF                   ; zero-extend the index (an 8-bit load
                                  ; leaves the high byte stale, not zeroed)
    asl a
    asl a                        ; index * 4 -- byte offset into the table
    tax

    sep #$20
.a8
    lda.l VmLoad_Crc1
    eor.l Vm_Crc32Table+0,x
    sta.l VmLoad_Crc0
    lda.l VmLoad_Crc2
    eor.l Vm_Crc32Table+1,x
    sta.l VmLoad_Crc1
    lda.l VmLoad_Crc3
    eor.l Vm_Crc32Table+2,x
    sta.l VmLoad_Crc2
    lda #0
    eor.l Vm_Crc32Table+3,x
    sta.l VmLoad_Crc3

    rep #$31
.a16
.i16
    lda.l VmLoad_Cursor
    inc a
    sta.l VmLoad_Cursor
    bra Vm_ValidateHeader__crc_byte

Vm_ValidateHeader__crc_done:
.a16
.i16
    sep #$20
.a8
    lda.l VmLoad_Crc0
    eor #$FF
    cmp.l VmCode_Wram+$38        ; stored CRC32, byte 0 (LSB)
    bne Vm_ValidateHeader__crc_fail
    lda.l VmLoad_Crc1
    eor #$FF
    cmp.l VmCode_Wram+$39        ; stored CRC32, byte 1
    bne Vm_ValidateHeader__crc_fail
    lda.l VmLoad_Crc2
    eor #$FF
    cmp.l VmCode_Wram+$3A        ; stored CRC32, byte 2
    bne Vm_ValidateHeader__crc_fail
    lda.l VmLoad_Crc3
    eor #$FF
    cmp.l VmCode_Wram+$3B        ; stored CRC32, byte 3 (MSB)
    beq Vm_ValidateHeader__crc_ok
Vm_ValidateHeader__crc_fail:
    brl Vm_ValidateHeader__to_fail
Vm_ValidateHeader__crc_ok:

    sep #$20
.a8
    lda #VMSTAT_READY
    sta.l VmState_Status
    rep #$31
.a16
.i16
    lda #VMERR_NONE
    sta.l VmState_Error
    rts

Vm_ValidateHeader__to_fail:
    brl Vm_Load__fail       ; ONE trampoline for the whole routine -- every
                            ; branch above stays a short, in-range branch.

; --- Vm_Load__fail -- the single failure exit. Reached only through the
; trampoline above. ---
Vm_Load__fail:
    sep #$20
.a8
    lda #VMSTAT_FAULT
    sta.l VmState_Status
    rep #$31
.a16
.i16
    lda #VMERR_BAD_MODULE
    sta.l VmState_Error
    rts

; --- CRC32 lookup table (Gate 1, plan_vm.md 3): 256 entries x 4 bytes LE,
; standard zlib/ISO-HDLC polynomial ($EDB88320), generated at repo-build
; time (not build_rom.py -- this is a committed, static table, never
; regenerated per-ROM) and verified byte-for-byte against Python's
; zlib.crc32 before being committed. Placed after all of this file's code so
; execution never risks falling into it. ---
Vm_Crc32Table:
    .incbin "vm_crc32_table.bin"
