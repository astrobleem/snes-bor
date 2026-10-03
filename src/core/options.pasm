; ============================================================================
; core/options.pasm -- Phase G5 (plan_game.md 5): real SRAM-backed options.
; Own bank (like core/spawn.pasm/charselect.pasm/hud_boss.pasm/pausemenu.pasm
; before it), purely for $C100-$FC00 ROM budget. Entered via `jsl` from bank
; 0 (Options_Init, once at boot) and from core/pausemenu.pasm's bank
; (Options_VolumeUp/Down, on Left/Right while the volume row is selected);
; every exit is a local `rtl`.
;
; Real-OpenBOR-sourced scope: engine/openbor.c's savedata struct persists
; several player-facing settings (keys/gamma/brightness/soundvol/usemusic/
; musicvol/effectvol -- see savedata_defaults() and menu_options_sound()).
; This project ships exactly ONE of them: music volume. Everything else has
; no real content to attach to here, same closure logic plan_game.md 8a
; already used for settime/maxenemy ("no real content to verify against"):
;   - no control remapping infrastructure exists (out of scope, real gap)
;   - gamma/brightness are a CRT/output concept, meaningless on a fixed-
;     palette SNES cart
;   - SFX volume would control zero real SFX content (G11 blocked, sfx_stub
;     only placeholder)
;   - difficulty (menu_difficulty()) picks between mod-defined content
;     *sets*; this project has only ever converted the EASY variant of any
;     level, so there is nothing real for a difficulty option to switch to
;
; Real command: soundwork/tad/vendor/tad-audio.inc's SET_GLOBAL_MUSIC_VOLUME
; (=16), an unsigned i8 (0-255, 255 = no attenuation), queued through the
; existing Tad_QueueCommand. NOT SET_MAIN_VOLUME (=10) -- that command's own
; doc says it resets whenever a new song loads, which would silently revert
; a saved setting; SET_GLOBAL_MUSIC_VOLUME only resets on song load if
; TadFlags::RESET_GLOBAL_VOLUMES_ON_SONG_START is set, and this project's
; TAD_DEFAULT_FLAGS (main.pasm) is just PLAY_SONG_IMMEDIATELY -- that flag
; is never set, so a persisted volume survives a song (re)load with no
; special-casing needed (also moot in practice: this project boots exactly
; one song, once, at scpu_boot, and nothing ever reloads it).
;
; Real hardware fact this whole file depends on (verified 2026-08-23 from
; Mesen2's own C++ core, same "read the emulator's C++ core, not just
; register-bit docs" methodology this project already used for CC-DMA --
; see build.md): SA-1's classic S-CPU SRAM window, bank $00 (mirrors at
; $01-$3F/$80-$BF), address $6000-$7FFF, is battery-backed cartridge save
; RAM -- Mesen2's Sa1::UpdateSaveRamMappings() backs it with the same
; _cart->DebugGetSaveRam() buffer BaseCartridge persists to a .srm file on
; clean shutdown (BatteryManager::SaveBattery, called from Emulator's power-
; off/new-ROM-load paths). It is a COMPLETELY SEPARATE physical region from
; the CC-DMA sprite canvas (BW_CANVAS = $606000, real BW-RAM offset $3000,
; reached through the SEPARATE bitmap-mode $60-$6F linear window) -- no
; collision on the underlying storage. Already fully write-enabled by this
; project's existing boot code (main.pasm, scpu_boot: `lda #$80 / sta $2226`
; SBWE, `stz $2228` BWPA=0, `stz $2224` BMAPS=bank 0) -- nothing new to
; enable here.
;
; CORRECTION (found 2026-08-23 debugging a real persistence-gate failure,
; re-read from Mesen2's own C++ core -- an earlier draft of this comment
; claimed the classic $6000-$7FFF window is NOT CharConv-diverted; that was
; WRONG, and is the reason this feature didn't work on the first attempt):
; Sa1::UpdateSaveRamMappings() registers $6000-$7FFF using the SAME
; CpuBwRamHandler class as the $40-$4F CC-DMA window, and
; CpuBwRamHandler::Read unconditionally diverts through
; Sa1::ReadCharConvertType1() whenever CharConvDmaActive is set -- for ANY
; address reached through that handler, not just the CC-DMA range. This
; project's persistent SA-1 recomposite loop (sa1_loop, main.pasm) arms
; CharConvDmaActive once, early in boot, and never clears it again (no
; write to $2231 with bit 7 set ever happens in steady state) -- so by the
; time Options_Init's lazy call runs, EVERY read from $6000-$7FFF returns
; bogus converted-tile bytes, not real SRAM content. Writes are NOT
; diverted (CpuBwRamHandler::Write has no CharConvDmaActive check at all),
; which is exactly why the write/persist-to-disk half of this feature
; worked from the very first attempt while every read-back silently saw
; zeros. Fix: Options_Init briefly ends character conversion (shared
; register $2231, which either CPU may write -- see WriteSharedRegisters)
; around its 4-byte read, then restores it and re-arms via $2236 exactly
; like sa1_loop's own steady-state re-arm. This is safe against the SA-1's
; own loop stepping on it: sa1_loop writes $2231 only once, in its one-time
; pre-loop setup, never per-iteration -- only $2236 is touched every cycle,
; and re-arming via $2236=0 here is byte-identical to what that loop
; already does. Options_VolumeUp/Down need no such dance: they only WRITE
; SRAM, which was never diverted.
;
; Layout (8 bytes, offset $0000-$0007 of the physical save RAM, i.e. S-CPU
; $006000-$006007 -- the first four bytes retain their old meaning):
;   $006000 = magic byte 0 (OPTIONS_MAGIC0_VALUE)
;   $006001 = magic byte 1 (OPTIONS_MAGIC1_VALUE)
;   $006002 = format version (OPTIONS_VERSION_CURRENT)
;   $006003 = music volume (0-255)
;   $006004-$006007 = little-endian BOR savedata.times_completed
; A blank/erased chip reads all $00 or all $FF -- the two-byte magic is
; chosen to be neither, so first-boot-ever is detected reliably and
; defaults get written instead of treating garbage as a real save.
; ============================================================================

OPTIONS_SRAM_BASE = $006000

OPTIONS_MAGIC0_VALUE     = $5A
OPTIONS_MAGIC1_VALUE     = $B0
OPTIONS_VERSION_CURRENT  = 2
OPTIONS_VERSION_LEGACY   = 1
OPTIONS_MUSICVOL_DEFAULT = 200   ; real BOR's own savedata_defaults() default
                                   ; is 100 out of ITS OWN 0-200 scale (half);
                                   ; TAD's SET_GLOBAL_MUSIC_VOLUME scale is
                                   ; 0-255 (255=no attenuation) -- 200 sits at
                                   ; the same "most of the way up, room to see
                                   ; a decrease" position on this scale.
OPTIONS_MUSICVOL_STEP    = 32

Options_MusicVolume = $7E27B0   ; .db -- current value, WRAM working copy of
                                  ; the SRAM byte at OPTIONS_SRAM_BASE+3;
                                  ; loaded once by Options_Init, applied to
                                  ; TAD by the bank-0 trampoline
                                  ; Options_ApplyMusicVolume_Long (main.pasm)

; Scratch latches for Options_Init's disarmed SRAM read (see the CORRECTION
; comment above) -- read while CharConvDmaActive is momentarily cleared,
; then the char-conv state is restored BEFORE these are examined, so the
; disarmed window is exactly the 4 loads below and nothing else.
Options_ScratchMagic0  = $7E27B2   ; .db
Options_ScratchMagic1  = $7E27B3   ; .db
Options_ScratchVersion = $7E27B4   ; .db
Options_ScratchVolume  = $7E27B5   ; .db
Options_ScratchTimes0   = $7E2900   ; .db, little-endian global BOR count
Options_ScratchTimes1   = $7E2901
Options_ScratchTimes2   = $7E2902
Options_ScratchTimes3   = $7E2903

; Source BOR stores savedata.times_completed as a C int.  Keep the SNES
; representation explicitly 32-bit so unlock thresholds remain a count and
; not a one-bit approximation.
Bor_TimesCompleted      = $7E2904   ; .db x4, little endian

; main.pasm's sa1_loop configures character conversion once with
; `lda #$09 / sta $2231` (format=4bpp, width=4 tiles/line) before entering
; its persistent loop, and never rewrites $2231 again in steady state --
; only re-arms via $2236 each cycle. This constant must match that value
; (re-derive by hand if sa1_loop's CC-DMA format ever changes).
SA1_LOOP_CDMA_FORMAT = $09

; ----------------------------------------------------------------------
; Options_Init -- called once from scpu_boot (main.pasm), right after the
; SBWE/BWPA/BMAPS pokes that make $6000-$7FFF real and writable. Reads the
; magic+version; on a match, loads the saved volume into Options_MusicVolume;
; on a mismatch (first boot ever, or a version bump), writes fresh defaults
; to SRAM and to Options_MusicVolume. Entry: .a8 (matches scpu_boot's width
; at the call site). Exit: .a8. Clobbers A.
; ----------------------------------------------------------------------
Options_Init:
.a8
    ; End character conversion (bit7), keeping sa1_loop's own format bits
    ; intact, so this read hits real SRAM instead of converted-tile bytes.
    lda #(SA1_LOOP_CDMA_FORMAT | $80)
    sta $2231
    lda.l OPTIONS_SRAM_BASE
    sta.l Options_ScratchMagic0
    lda.l OPTIONS_SRAM_BASE+1
    sta.l Options_ScratchMagic1
    lda.l OPTIONS_SRAM_BASE+2
    sta.l Options_ScratchVersion
    lda.l OPTIONS_SRAM_BASE+3
    sta.l Options_ScratchVolume
    lda.l OPTIONS_SRAM_BASE+4
    sta.l Options_ScratchTimes0
    lda.l OPTIONS_SRAM_BASE+5
    sta.l Options_ScratchTimes1
    lda.l OPTIONS_SRAM_BASE+6
    sta.l Options_ScratchTimes2
    lda.l OPTIONS_SRAM_BASE+7
    sta.l Options_ScratchTimes3
    ; Restore format (bit7 clear) and re-arm exactly like sa1_loop's own
    ; steady-state re-arm (stz $2236 -- dest mid byte 0).
    lda #SA1_LOOP_CDMA_FORMAT
    sta $2231
    stz $2236

    lda.l Options_ScratchMagic0
    cmp #OPTIONS_MAGIC0_VALUE
    bne Options_Init_defaults
    lda.l Options_ScratchMagic1
    cmp #OPTIONS_MAGIC1_VALUE
    bne Options_Init_defaults
    lda.l Options_ScratchVersion
    cmp #OPTIONS_VERSION_LEGACY
    beq Options_Init_legacy
    cmp #OPTIONS_VERSION_CURRENT
    bne Options_Init_defaults
    lda.l Options_ScratchVolume
    sta.l Options_MusicVolume
    lda.l Options_ScratchTimes0
    sta.l Bor_TimesCompleted
    lda.l Options_ScratchTimes1
    sta.l Bor_TimesCompleted+1
    lda.l Options_ScratchTimes2
    sta.l Bor_TimesCompleted+2
    lda.l Options_ScratchTimes3
    sta.l Bor_TimesCompleted+3
    rtl
Options_Init_legacy:
.a8
    ; Version 1 had no completion field. Preserve its valid volume and
    ; upgrade in place with a zero 32-bit count.
    lda.l Options_ScratchVolume
    sta.l Options_MusicVolume
    lda #0
    sta.l Bor_TimesCompleted
    sta.l Bor_TimesCompleted+1
    sta.l Bor_TimesCompleted+2
    sta.l Bor_TimesCompleted+3
    jsl Options_SaveBorCompletion
    rtl
Options_Init_defaults:
.a8
    lda #OPTIONS_MAGIC0_VALUE
    sta.l OPTIONS_SRAM_BASE
    lda #OPTIONS_MAGIC1_VALUE
    sta.l OPTIONS_SRAM_BASE+1
    lda #OPTIONS_VERSION_CURRENT
    sta.l OPTIONS_SRAM_BASE+2
    lda #OPTIONS_MUSICVOL_DEFAULT
    sta.l OPTIONS_SRAM_BASE+3
    sta.l Options_MusicVolume
    lda #0
    sta.l Bor_TimesCompleted
    sta.l Bor_TimesCompleted+1
    sta.l Bor_TimesCompleted+2
    sta.l Bor_TimesCompleted+3
    jsl Options_SaveBorCompletion
    rtl

; Persist the current options header and the 32-bit BOR completion count.
; This is deliberately a small append-only SRAM format extension: a valid
; version-1 record is upgraded without losing its volume byte.
Options_SaveBorCompletion:
.a8
    lda #OPTIONS_MAGIC0_VALUE
    sta.l OPTIONS_SRAM_BASE
    lda #OPTIONS_MAGIC1_VALUE
    sta.l OPTIONS_SRAM_BASE+1
    lda #OPTIONS_VERSION_CURRENT
    sta.l OPTIONS_SRAM_BASE+2
    lda.l Options_MusicVolume
    sta.l OPTIONS_SRAM_BASE+3
    lda.l Bor_TimesCompleted
    sta.l OPTIONS_SRAM_BASE+4
    lda.l Bor_TimesCompleted+1
    sta.l OPTIONS_SRAM_BASE+5
    lda.l Bor_TimesCompleted+2
    sta.l OPTIONS_SRAM_BASE+6
    lda.l Bor_TimesCompleted+3
    sta.l OPTIONS_SRAM_BASE+7
    rtl

; ----------------------------------------------------------------------
; Options_VolumeUp/Down -- called from core/pausemenu.pasm on Right/Left
; while the volume row is selected. Saturating +-32 (255/32 and 0/32 both
; land cleanly without a separate clamp branch: an unsigned 8-bit add/sub
; can only carry/borrow out exactly when the true result would leave
; 0-255, which is this scale's own real min/max, so the carry/borrow flag
; alone is the clamp check). Persists to SRAM immediately -- real BOR's own
; menu_options_sound() applies+shows the new value the same frame it's
; changed, with no separate "save" step. Entry/exit: .a8. Clobbers A.
; ----------------------------------------------------------------------
Options_VolumeUp:
.a8
    lda.l Options_MusicVolume
    clc
    adc #OPTIONS_MUSICVOL_STEP
    bcc Options_VolumeUp_store
    lda #$FF
Options_VolumeUp_store:
    sta.l Options_MusicVolume
    sta.l OPTIONS_SRAM_BASE+3
    rtl

Options_VolumeDown:
.a8
    lda.l Options_MusicVolume
    sec
    sbc #OPTIONS_MUSICVOL_STEP
    bcs Options_VolumeDown_store
    lda #0
Options_VolumeDown_store:
    sta.l Options_MusicVolume
    sta.l OPTIONS_SRAM_BASE+3
    rtl
