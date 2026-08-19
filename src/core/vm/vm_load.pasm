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

VM_MSU_OFFSET   = $027164   ; from build_rom.py's check_vm_constants -- re-sync
                            ; (rerun the build, paste its reported value) any
                            ; time an earlier roster/BG/FP/spawn asset changes
                            ; size, or the shipped level changes.
VM_MODULE_SIZE  = 184       ; tools/verify/vm_fixtures/gate0_module.bin, likewise
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
    bne Vm_ValidateHeader__to_fail
    lda.l VmCode_Wram+1
    cmp #$34                ; '4'
    bne Vm_ValidateHeader__to_fail
    lda.l VmCode_Wram+2
    cmp #$38                ; '8'
    bne Vm_ValidateHeader__to_fail
    lda.l VmCode_Wram+3
    cmp #$53                ; 'S'
    bne Vm_ValidateHeader__to_fail

    lda.l VmCode_Wram+4
    cmp #1                  ; format_version
    bne Vm_ValidateHeader__to_fail
    lda.l VmCode_Wram+5
    cmp #$30                ; opcode_abi -- 48 opcodes
    bne Vm_ValidateHeader__to_fail
    lda.l VmCode_Wram+6
    cmp #0                  ; numeric_profile -- Q16.16 (plan_vm.md §0.3)
    bne Vm_ValidateHeader__to_fail

    rep #$31
.a16
.i16
    lda.l VmCode_Wram+8     ; instruction_count (u16)
    cmp #(VM_INSTR_MAX+1)
    bcs Vm_ValidateHeader__to_fail
    sta.l VmState_InstrCount

    lda.l VmCode_Wram+10    ; slot_count (u16)
    cmp #(VM_SLOT_MAX+1)
    bcs Vm_ValidateHeader__to_fail
    sta.l VmState_SlotCount

    lda.l VmCode_Wram+$34   ; module_size low 16 bits
    cmp #VM_MODULE_SIZE
    bne Vm_ValidateHeader__to_fail
    lda.l VmCode_Wram+$36   ; module_size high 16 bits
    cmp #0
    bne Vm_ValidateHeader__to_fail

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

; TODO(Gate 1): verify crc32 at header +$38 over bytes $40..module_size
