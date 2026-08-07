; ============================================================================
; Beats of Rage SNES — SA-1 + CC-DMA + MSU-1 + Terrific Audio Driver (TAD)
; Poppy assembler, LoROM + SA-1 (map mode $23, cart type $35)
; ============================================================================

.snes

BW_CANVAS   = $606000   ; canvas: 128x96 4bpp linear at SA-1 BW-RAM $60:6000

; Per-frame CC-DMA canvas pump state (S-CPU side, see Scpu_CcdmaPump in the
; SA-1 region below):
CanvasChunkOffset = $7E2340   ; .dw -- next 32-byte tile offset into the
                                 ;        48-tile canvas (0..$05E0)
Sa1LoopCounter    = $7E2342   ; .db -- SA-1 recomposite cycle counter,
                                 ;        mirrored from I-RAM $3000 every frame
PumpScratch       = $7E2344   ; .db[32] -- 32-byte tile staging for the pump's
                                 ;        forced-blank bracket (see Scpu_CcdmaPump)

; --- Blob symbols for LoROM TAD build ---
; Generated from tad-compiler ca65-export output.
.include "../soundwork/tad/build/tad_blob_syms.pasm"

; SPC700 IPL reset is a hardware-side operation. TAD_Init must only run after
; the S-SMP has been reset and has reached its IPL ready handshake ($BBAA).
; $2140-$2143 are data ports, not a reset control register.
APU_RESET = $2140

.bank 0

; ============================================================================
; SA-1 entry (CRV=$8000). Reached by SA-1 at $00:8000 = file $0000.
; ============================================================================
.org $8000

sa1_main:
    clc
    xce                     ; native mode
    sep #$20
.a8
    lda #$FF
    sta $222A               ; CIWP: SA-1 enables its OWN IRAM writes
    lda #$80
    sta $2227               ; CBWE: SA-1 enables its OWN BW-RAM writes

    rep #$30
.a16
.i16

    ; --- Clear canvas: $1800 bytes at $60:6000 ---
    ldx #$0000
    txa                     ; A = 0
sa1_clear:
    sta.l BW_CANVAS,x
    inx
    inx
    cpx #$1800
    bcc sa1_clear

    ; --- DBR = 0, where TestSprite32x48 lives ---
    ; The blit's source read is plain absolute (not .l) indexed by Y -- the
    ; 65816 has no indexed-long addressing mode with Y at all (only X
    ; supports addr24,X); writing `.l ...,y` doesn't error in this Poppy
    ; build, it silently falls back to 3-byte absolute,Y while still
    ; apparently budgeting 4 bytes internally, which shifts every following
    ; byte by one and corrupts the next instruction. Explicit DB=0 here so
    ; the plain-absolute Y-indexed read is guaranteed correct
    ; (TestSprite32x48 lives in this same bank) rather than assuming SA-1's
    ; default DB happens to still be 0.
    sep #$20
.a8
    lda #0
    pha
    plb                     ; DBR = 0
    rep #$30
.a16
.i16

; ============================================================================
; Persistent SA-1 recomposite loop
; ============================================================================
; The smallest real step toward the spec's SA-1 software-sprite compositor
; (SNES-BOR-Engine-Prompt.md §3): prove the SA-1 runs a persistent loop that
; recomposites the shared BW-RAM canvas and RE-ARMS CC-DMA live, more than
; the single boot-time shot the old sa1_spin offered. Each iteration:
;
;   1. Re-draws two static 32x48 blits into the canvas (blit A at
;      BW_CANVAS+0, blit B at BW_CANVAS+$600), pixel-by-pixel through the
;      $60-6F "always bitmap mode" window. $600 window bytes = $300 real
;      bytes = 24 tiles, so blit B lands at real BW-RAM offset $3300,
;      contiguous with blit A's tiles 0-23 at real $3000: the canvas is one
;      48-tile (1536-byte) region, tiles 0-47.
;   2. Re-arms CC-DMA Type 1 (the full register sequence, same as the old
;      boot code -- it is cheap and self-documenting). Conversion itself
;      stays READ-TRIGGERED: the $2236 write only re-sets CharConvDmaActive
;      and CharConvIrqFlag (SFR $2300 bit 5, readable by BOTH CPUs -- Mesen2
;      Sa1RegisterRead 0x2300), and no bytes move until the S-CPU reads the
;      $40-4F window.
;   3. Waits for the S-CPU to consume the whole canvas, then redraws. The
;      release is an I-RAM mailbox: the pump writes $AA to $3025 once all
;      48 tiles are in VRAM (Scpu_CcdmaPump) and the SA-1 polls that byte.
;      The S-CPU gates its pump on SFR bit 5 (which IT can read); the SA-1
;      cannot read SFR $2300 at all (its own register window has no 0x2300
;      case -- Mesen2 Sa1RegisterRead -- so that read is open bus, and the
;      old SFR-wait never released), which is exactly why the release must
;      be a byte the SA-1 can see. This lock-step is the proto-mailbox from
;      spec §3.8 (RENDER_START / CANVAS_READY) in its smallest form: the
;      S-CPU's pump never reads a half-redrawn canvas, so it generalizes to
;      dynamic content without a redraw-vs-conversion race.
;
; DP scratch $00/$02/$04/$06 lives in I-RAM $0000-$00FF, which CC-DMA's
; converted-tile staging ALSO writes (DDA=0 -> each converted tile lands at
; I-RAM $0000-$001F). That only happens while the S-CPU pumps (flag set,
; this loop waiting), and every DP cell here is re-initialized before each
; draw, so no stale value ever crosses a wait boundary. I-RAM $20/$21 are
; above that staging band: $20 = phase canary (1..5, see below), $21 = the
; recomposite cycle counter (the old `inc $3000` aliased DP $00 through the
; I-RAM window's & $7FF mapping AND got stomped by the staging every tile;
; $21 is outside both hazards).
sa1_loop:
    rep #$30                ; re-assert 16-bit A/X: reached via `bra sa1_loop`
.a16                        ; from the 8-bit wait loop below (same fix family
.i16                        ; as poppy bug #10 -- width on a branch path)
    ; --- phase canary 1: entered the loop ---
    sep #$20
.a8
    lda #$01
    sta $20
    rep #$20
.a16
    ; --- blit A: TestSprite32x48 at BW_CANVAS+0 ---
    stz $06                 ; blit base offset = 0
    jsr sa1_draw_blit

    ; --- phase canary 2: blit A done ---
    sep #$20
.a8
    lda #$02
    sta $20
    rep #$20
.a16
    ; --- blit B: same sprite at BW_CANVAS+$600 ---
    lda #$0600
    sta $06
    jsr sa1_draw_blit

    ; --- phase canary 3: blit B done, about to arm ---
    sep #$20
.a8
    lda #$03
    sta $20
    rep #$20
.a16
    ; --- Configure SA-1 CC-DMA Type 1 (Auto Mode) FROM SA-1 CPU SIDE ---
    sep #$20
.a8
    ; width=2 (SSS bits) -> 2^2 = 4 tiles/line, matching the sprite's own
    ; 4-tile width exactly. CC-DMA's source row pitch is derived from this
    ; field, not from anything else -- a wider setting than the source
    ; data's real width reads each row from the wrong offset (this is what
    ; silently broke the first attempt, which used width=4/16-tiles-per-
    ; line against a 128px-wide padded canvas with a 24-tile sprite
    ; occupying a fraction of it -- source pitch didn't match draw pitch).
    ;
    ; SDA is NOT simply "BW-RAM offset $6000". CC-DMA Type 1 is READ-
    ; TRIGGERED: writing $2236 only arms CharConvDmaActive -- no bytes move
    ; until something reads through the $40-4F (S-CPU) / $40-5F (SA-1)
    ; linear BW-RAM window, at which point the read is intercepted and the
    ; source bytes get converted to VRAM-format bitplanes on the fly (see
    ; Mesen2 core: CpuBwRamHandler::Read -> Sa1::ReadCharConvertType1). The
    ; conversion is stateless per read -- the trigger condition is
    ; (addr & 31) == 0 and the tile is derived purely from
    ; (addr - DmaSrcAddr) -- so re-arming and re-pumping is free, which is
    ; what makes this persistent loop possible at all.
    ;
    ; Our sprites are drawn via `sta.l BW_CANVAS,x` where BW_CANVAS=$606000
    ; -- the $60-6F bank range is hard-wired "always bitmap mode" (see
    ; Sa1BwRamHandler::WriteBitmapMode), which auto-packs each byte we
    ; write (low nibble = one pixel's color) two-per-real-byte at HALF the
    ; window offset, with the $600000 bank component subtracted first:
    ; real bwRam offset = ((BW_CANVAS & $1FFFFF) + x) >> 1 = ($6000+x) >> 1,
    ; i.e. our packed sprite bytes actually live at real BW-RAM offset
    ; $3000, not $6000 and not $0. SDA must equal that real offset ($3000)
    ; for CC-DMA's tile/address math to land on our data; reading the
    ; converted bytes back out then requires reading through $40:3000+ (see
    ; Scpu_CcdmaPump below), NOT the $3000 S-CPU I-RAM window (a read from
    ; the I-RAM window never touches this handler and triggers nothing --
    ; this was the root cause of the noise/garbage seen before this fix).
    lda #$09
    sta $2231               ; 4bpp, width=4 tiles/line
    stz $2232               ; source = real BW-RAM offset $3000 (low)
    lda #$30
    sta $2233               ; (mid)
    stz $2234               ; (high)
    stz $2235               ; dest = IRAM offset 0
    lda #$B1
    sta $2230               ; enable | charconv | auto | src=BW-RAM (SA-1 ONLY!)
    stz $2236               ; write dest mid byte -> arms CharConvDmaActive +
                             ; sets CharConvIrqFlag (SFR bit 5) = "canvas ready"
                             ; (conversion itself still hasn't run yet -- see above)

    ; --- Re-composite cycle counter (debug/verification) ---
    ; I-RAM $3000: incremented once per completed cycle. The S-CPU mirrors
    ; it to WRAM Sa1LoopCounter every frame (Scpu_CcdmaPump) so a Mesen2
    ; harness read proves the SA-1 loop is live and the handshake is
    ; cycling -- never trust "probably running" without a ground-truth read.
    ; I-RAM $21, not $3000: $3000 maps (via the I-RAM window's & $7FF) to
    ; I-RAM $0000 = SA-1 DP byte $00 AND is overwritten every tile by CC-DMA
    ; staging; $21 sits above the staging band and below the stack.
    lda #$04                ; phase canary 4: armed, about to wait
    sta $20
    inc $21

    ; --- Wait for the S-CPU to consume this canvas ---
    ; Mailbox handshake (NOT the SFR): the SA-1's own read of $2300 never
    ; returns the S-CPU's SFR -- Mesen's Sa1RegisterRead has no 0x2300 case
    ; (that register belongs to CpuRegisterRead), so `lda $2300` on the
    ; SA-1 falls through to open bus, and bit 5 of that value reads stuck
    ; set here. The S-CPU can see the flag (it pumps on it), but the SA-1
    ; physically cannot, so the old SFR-wait could never release the loop.
    ; Instead: the S-CPU's pump writes $AA to I-RAM $3025 once all 48 tiles
    ; are in VRAM (see Scpu_CcdmaPump), and the SA-1 polls that byte -- the
    ; proto-mailbox from spec §3.8 (RENDER_START / CANVAS_READY) in its
    ; smallest form. The SA-1 clears the mailbox before redrawing, so the
    ; pump's next completion (48 frames later) cannot be mistaken for this
    ; one, and the pump still gates on SFR bit 5 for its own start signal.
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
sa1_wait:
    lda $3025               ; I-RAM mailbox: $AA = S-CPU has consumed canvas
    cmp #$AA
    bne sa1_wait
    stz $25                 ; acknowledge: clear the mailbox (own I-RAM
                            ; window; CIWP $FF set at boot permits it)
    lda #$05                ; phase canary 5: wait exited, loop will re-arm
    sta $20
    bra sa1_loop

; --- Draw one 32x48 blit of TestSprite32x48 into the canvas ---
; Caller (sa1_loop) sets $06 = blit base offset in window units (0 or $600)
; and must be in .a16/.i16; exits .a16/.i16. Source data is byte-per-pixel
; (one byte = one pixel, color index in the low nibble); the bitmap window
; auto-packs two pixels per real byte at HALF the window offset, so drawing
; window offset X puts the packed sprite bytes at real BW-RAM offset
; (($600000 & $1FFFFF) + X) >> 1 -- exactly the layout CC-DMA's tile math
; expects for SDA=$3000 (see the CC-DMA comments above).
;
; The blit source is a 32x48 real sprite frame, extracted and converted
; from the game's own asset pack (not hand-authored/synthetic): source
; DATA\CHARS\RALF\IDLE1.GIF inside "Beats of Rage Original [v.3.0 Build
; 4086].pak" (an indexed-color GIF, magenta $FC00FF background/transparency
; marker per BOR convention), cropped to its real bounding box,
; nearest-neighbor scaled to fit 32x48 (feet-aligned to the bottom,
; matching BOR's hotspot convention), then quantized to 15 colors +
; reserved index 0 (mapped to black, this canvas's real backdrop) via
; tools/bor_converter/convert_real_sprite.py. See that script's header for
; the PAK archive format (reverse-engineered from OpenBOR's own
; packfile.c: `PACK`+version header, file data, then a directory table at
; the END of the file with a trailing 4-byte offset pointing back to it --
; there is no compression or real encryption, despite "encrypted archive"
; being the common description).
sa1_draw_blit:
    stz $00                 ; row = 0..47
    stz $02                 ; source offset into TestSprite32x48, 0..1535
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
sa1_draw_row_loop:
    lda $00
    asl
    asl
    asl
    asl
    asl                     ; row * 32 (byte-per-pixel source: 32 px/row)
    clc
    adc $06                 ; + blit base offset
    tax                     ; X = dest byte offset into BW_CANVAS this row
    ldy $02                 ; Y = source byte offset, carried across rows
    stz $04                 ; col = 0..31 (bytes this row)
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
sa1_draw_col_loop:
    sep #$20
.a8
    lda TestSprite32x48,y
    sta.l BW_CANVAS,x
    rep #$20
.a16
    inx
    iny
    inc $04
    lda $04
    cmp #$0020
    bcc sa1_draw_col_loop

    sty $02                 ; persist source offset for next row

    inc $00
    lda $00
    cmp #$0030              ; 48 rows
    bcc sa1_draw_row_loop
    rts

; ============================================================================
; S-CPU side: per-frame CC-DMA canvas pump -- Scpu_CcdmaPump
; ============================================================================
; jsr'd once per frame from scpu_main_loop, immediately after
; Core_Nmi_WaitFrame, so its VRAM writes land in the vblank tail rather than
; mid-active-display. Converts and copies ONE 32-byte tile per frame while
; the SA-1's canvas-ready flag is set (SFR $2300 bit 5 = CharConvIrqFlag),
; and clears that flag (SIC $2202 bit 5) once the full 48-tile canvas
; (1536 bytes, both 4x6 windows) is in VRAM -- releasing the SA-1 to
; recomposite the next canvas. Full refresh therefore takes 48 frames;
; a one-tile-per-frame chunk keeps this inside the vblank tail (16 word-
; reads + 16 word-writes ~= 400 cycles), which a full 1536-byte pump would
; blow out by an order of magnitude.
;
; The conversion is stateless per read (Mesen2 core: CpuBwRamHandler::Read
; -> Sa1::ReadCharConvertType1: trigger on (addr & 31) == 0, tile derived
; from (addr - DmaSrcAddr)), so pumping a 32-byte slice at any
; 32-byte-aligned offset converts exactly that tile -- no conversion-side
; chunk state to keep. The read itself returns the already-converted
; VRAM-format bytes, staged by the hardware in I-RAM at DDA=0.
;
; Entry/exit convention: .a16/.i16 (scpu_main_loop's). Wrapped in php/sei ..
; plp as a defensive convention matching Core_Dma_Enqueue's, but note sei
; only masks IRQ, not NMI -- it cannot protect the X/Y loop counters below
; from an NMI landing mid-loop. That protection instead comes from
; Core_Nmi_Play itself (core/nmi.pasm): it pha/phx/phy/phb/phd at entry and
; restores them before returning, so X/Y here survive an NMI intact
; regardless of this wrapper. Verified empirically byte-perfect across a
; live NMI-interrupted run; see the ccdma_validated_nmi_timing_bug and
; nmi-handler-no-register-save-reentrancy project memories.
Scpu_CcdmaPump:
    php
    sei
    sep #$20
.a8
    lda $3021               ; SA-1 recomposite cycle counter (I-RAM $21;
                            ; the old $3000 mirror read the CC-DMA staging
                            ; band, not the counter)
    sta.l Sa1LoopCounter    ; debug mirror: proves the SA-1 loop is live
    lda $2300               ; SFR
    and #$20                ; CharConvIrqFlag set -> a fresh canvas is armed
    beq Scpu_CcdmaPump_Done
    rep #$20
.a16
.i16
    lda.l CanvasChunkOffset
    tax
    ldy #$0010              ; 16 words per 32-byte tile
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
Scpu_CcdmaPump_Read:
    lda.l $403000,x         ; read+trigger-convert via S-CPU BW-RAM window ($40-4F)
    sta.l PumpScratch,x     ; stage in WRAM -- deliberately OUTSIDE the forced-
                            ; blank bracket: BW-RAM reads are not PPU accesses,
                            ; and they can stall for many cycles on SA-1 BW-RAM
                            ; arbitration, so keeping them out of the bracket
                            ; keeps the bracket itself short and bounded. (A
                            ; separate, pre-existing black band at the top of
                            ; every frame was investigated this session and
                            ; confirmed present even with this pump's jsr
                            ; disabled entirely and at the branch's committed
                            ; HEAD before this pump existed -- it comes from
                            ; Core_Nmi_Play's own commit bracket in nmi.pasm
                            ; being outpaced by this branch's larger per-
                            ; vblank DMA/shadow-commit workload, not from
                            ; anything in this routine. See the
                            ; ccdma_validated_nmi_timing_bug project memory.)
    inx
    inx
    dey
    bne Scpu_CcdmaPump_Read

    ; --- forced-blank bracket: only the $2116/$2118 writes need it ---
    sep #$20
.a8
    lda #$80
    sta $2100               ; INIDISP: force blank so the tile writes land
                            ; regardless of vblank-tail timing (CanAccessVram
                            ; only admits $2116/$2118 during forced blank or
                            ; past the NMI scanline, and the pump runs after
                            ; the NMI handler, in the vblank tail)
    rep #$20
.a16
    lda.l CanvasChunkOffset
    lsr                     ; byte offset -> VRAM word offset (32 bytes = 16 words)
    clc
    adc #$2010              ; VRAM dest word (BG2 char base $2000, tile 1)
    sta $2116
    lda.l CanvasChunkOffset
    tax
    ldy #$0010              ; 16 words per 32-byte tile
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
Scpu_CcdmaPump_Write:
    lda.l PumpScratch,x     ; WRAM reads only -- no BW-RAM access inside the
                            ; bracket, so it cannot stall on SA-1 arbitration
                            ; (bounded, ~350 cycles for the 16-word loop)
    sta $2118               ; write to VRAM $2118/$2119
    inx
    inx
    dey
    bne Scpu_CcdmaPump_Write
    sep #$20
.a8
    lda.l Nmi_ScreenBrightness
    sta $2100               ; restore the screen brightness ($0F, set in boot)
    rep #$20
.a16
    txa
    cmp #$0600              ; 1536 bytes = 48 tiles (both 4x6 windows)
    bcc Scpu_CcdmaPump_Keep
    sep #$20
.a8
    lda #$AA
    sta $3025               ; I-RAM mailbox -> releases the SA-1's wait loop
                            ; (the SA-1 cannot read SFR $2300 -- its own
                            ; register window has no 0x2300 case, it reads
                            ; open bus there -- so the release has to be a
                            ; byte it CAN see; SIWP $FF set in scpu_boot
                            ; permits this S-CPU I-RAM write)
    lda #$20
    sta $2202               ; SIC: clear CharConvIrqFlag -> pump's own next
                            ; frame check skips until the SA-1 re-arms
    rep #$20
.a16
    lda #$0000
    sta.l CanvasChunkOffset
    bra Scpu_CcdmaPump_Done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Scpu_CcdmaPump_Keep:
    sta.l CanvasChunkOffset
Scpu_CcdmaPump_Done:
    plp
    rep #$31
.a16
.i16
    rts

; ============================================================================
; TAD Audio Driver Module (Ported from ca65 to Poppy .pasm)
; ============================================================================
; NOTE: the 32x48 sprite blob lives HERE, immediately before this .org, not
; after the pump code above -- the SA-1 loop grew into that spot once
; (canaries + mailbox handshake) and silently clobbered the blob (Poppy's
; fixed-.org truncation; the blob's .incbin sat at the old location and the
; pump overran it, corrupting the source pixels with no build error). This
; placement pins the blob to the $8800 boundary with all the code's growth
; room on the other side.
;
; 32x48 4bpp linear-packed test sprite (768 bytes), hand-authored to
; validate the CC-DMA pipeline end-to-end -- see gen_sprite_bin.py-style
; generation notes: 24 uniquely-colored 8x8 tiles plus a white/black X
; overlay across the whole sprite, so both per-tile addressing AND
; within-tile multi-color nibble packing get exercised, not just a
; uniform test block.
TestSprite32x48:
    .incbin "assets/test_sprite_32x48.bin"
.org $8800
; Converted from CA65 to PASM by Poppy
; Original file: tad-audio.s
; Conversion date: 2026-07-07 00:53:22 UTC

;; Terrific Audio Driver ca65 API

; This file MUST be recompiled if the memory map changes.
;
; SPDX-FileCopyrightText: © 2024 Marcus Rowe <undisbeliever@gmail.com>
; SPDX-License-Identifier: Zlib
;
; Copyright © 2024 Marcus Rowe <undisbeliever@gmail.com>
;
; This software is provided 'as-is', without any express or implied warranty.  In
; no event will the authors be held liable for any damages arising from the use of
; this software.
;
; Permission is granted to anyone to use this software for any purpose, including
; commercial applications, and to alter it and redistribute it freely, subject to
; the following restrictions:
;
;      1. The origin of this software must not be misrepresented; you must not
;         claim that you wrote the original software. If you use this software in
;         a product, an acknowledgment in the product documentation would be
;         appreciated but is not required.
;
;      2. Altered source versions must be plainly marked as such, and must not be
;         misrepresented as being the original software.
;
;      3. This notice may not be removed or altered from any source distribution.


; [linker] setcpu "65816"
; [linker] smart

; Ensure autoimport is disabled
; UNSUPPORTED: .autoimport -


; [linker] export Tad_Init : far, Tad_Process : far, Tad_FinishLoadingData : far
; [linker] export Tad_QueueCommand, Tad_QueueCommandOverride
; [linker] export Tad_QueuePannedSoundEffect, Tad_QueueSoundEffect
; [linker] export Tad_LoadSong, Tad_LoadSongIfChanged, Tad_GetSong, Tad_ReloadCommonAudioData
; [linker] export Tad_SongsStartImmediately, Tad_SongsStartPaused
; [linker] export Tad_GlobalVolumesResetOnSongStart, Tad_GlobalVolumesPersist
; [linker] export Tad_SetTransferSize
; [linker] export Tad_IsLoaderActive, Tad_IsSongLoaded, Tad_IsSfxPlaying, Tad_IsSongPlaying

; [linker] exportzp Tad_sfxQueue_sfx, Tad_sfxQueue_pan
; [linker] export Tad_flags, Tad_audioMode


;; =======
;; DEFINES
;; =======

;; Memory Map
;; ----------
;;
;; `tad-audio.s` requires either a `LOROM` or `HIROM` symbol to determine the memory map used by the ROM.



;; Segments
;; --------
;;
;; The following optional defines are used to determine the segment to place the code in.
;;
;;  * `TAD_PROCESS_SEGMENT` defines the segment to store the subroutines that processes the queues
;;     and loads data into Audio-RAM (`Tad_Init`, `Tad_Process`, `Tad_FinishLoadingData`).
;;      * The exported subroutines in this segment are called using `JSL` long addressing.
;;      * If `TAD_PROCESS_SEGMENT` is undefined, `TAD_CODE_SEGMENT` is used.
;;
;;  * `TAD_CODE_SEGMENT` defines the segment to store the remaining subroutines.
;;      * The subroutines in this segment are called using `JSR` absolute addressing.
;;      * If `TAD_CODE_SEGMENT` is undefined, "CODE" will be used.
;;
;;
;; NOTE: Because ca65 only allows numbers in `-D name=value` command line arguments, the only
;; way to set these defines is to create a new source file that defines `TAD_CODE_SEGMENT`
;; and/or `TAD_PROCESS_SEGMENT` and then includes `tad-audio.s`.
;;
;; For example:
;;
;;      .define TAD_CODE_SEGMENT "CODE1"
;;      .define TAD_PROCESS_SEGMENT "CODE3"
;;
;;      .include "../terrific-audio-driver/audio-driver/ca65-api/tad-audio.s"
;;






;; ===========
;; Binary Data
;; ===========
;;
;; These 3 files MUST be embedded (using `.incbin`) into the ROM if the developer uses a custom
;; `LoadAudioData` callback.
;;

;; Terrific Audio Driver spc700 Loader (loader.bin)
; [linker] import Tad_Loader_Bin
; [linker] importzp Tad_Loader_SIZE

;; Terrific Audio Driver spc700 driver (audio-driver.bin)
; [linker] import Tad_AudioDriver_Bin, Tad_AudioDriver_SIZE


; [assert] assert Tad_Loader_SIZE > 64 && Tad_Loader_SIZE < 128, lderror, "Invalid Tad_Loader_Bin size"
; [assert] assert .bankbyte(Tad_Loader_Bin) = .bankbyte(Tad_Loader_Bin + Tad_Loader_SIZE), lderror, "Tad_Loader_Bin does not fit inside a single bank"

; [assert] assert Tad_AudioDriver_SIZE > $600 && Tad_AudioDriver_SIZE < $d00, lderror, "Invalid Tad_AudioDriver_Bin size"
; `Tad_AudioDriver_Bin` can cross bank boundaries



;; =========
;; CALLBACKS
;; =========


;; LoadAudioData callback
;;
;; IN: A = 0 - Common audio data (MUST return carry set)
;; IN: A >= 1 - Song data (might be invalid)
;; OUT: Carry set if input (`A`) was valid
;; OUT: A:X = far address
;; OUT: Y = size
;;
;; Called with JSL long addressing (returns with RTL).
.a8
.i16
;; DB access registers
; [linker] import LoadAudioData: Far


;; =========
;; CONSTANTS
;; =========


;; Address to store the loader (in Audio-RAM).
;; Address (in Audio-RAM) to execute after loading the Loader.
;; MUST match LOADER_ADDR in `audio-driver/src/common-memmap.inc`
TAD_LOADER_ARAM_ADDR = $0200


;; Minimum transfer size accepted by `Tad_SetTransferSize`
;;
;; MUST BE > 0
TAD_MIN_TRANSFER_PER_FRAME = 32

;; Maximum transfer size accepted by `Tad_SetTransferSize`
;;
;; The loader can transfer ~849 bytes per 60Hz frame SlowROM or FastROM
TAD_MAX_TRANSFER_PER_FRAME = 800



;; ========
;; IO Ports
;; ========

;; IO communication protocol version.
;;
;; Used by `tad-compiler ca65-export` to verify the IO protocol in `tad-audio.s` matches the audio-driver.
;;
;; This constant MUST be increased if `LOADER_ADDR` or the IO Communication protocol changes.
TAD_IO_VERSION = 20


; MUST match `audio-driver/src/io-commands.inc`
; enum TadCommand
    PAUSE = 0
    PAUSE_MUSIC_PLAY_SFX = 2
    UNPAUSE = 4
    PLAY_SOUND_EFFECT = 6
    STOP_SOUND_EFFECTS = 8
    SET_MAIN_VOLUME = 10
    SET_MUSIC_CHANNELS = 12
    SET_SONG_TIMER = 14
    SET_GLOBAL_MUSIC_VOLUME = 16
    SET_GLOBAL_SFX_VOLUME = 18
    SET_GLOBAL_VOLUMES = 20
; endenum

TAD_MAX_PAN = 128
TAD_CENTER_PAN = TAD_MAX_PAN / 2


;; MUST match `audio-driver/src/io-commands.inc`
; scope TadIO_ToDriver
    ;; The command to execute.
    ;;
    ;;      iiicccci
    ;;         cccc = command
    ;;            i = command id, MUST be different on every command.
    ;;                Used to detect when a new command has been sent to the driver.
    ;;
    ;; NOTES:
    ;;  * The command will only be execute if the `command` byte has changed.
    ;;  * This value MUST be written last.
    ;;  * The command and parameter bytes MUST NOT change unless the previous command
    ;;    has been acknowledged.
    COMMAND_PORT = $2140 ; APUIO0

    COMMAND_MASK = %00011110
    COMMAND_I_MASK = %11100001

    ;; The first command parameter port
    PARAMETER0_PORT = $2141 ; APUIO1

    ;; The second command parameter port
    PARAMETER1_PORT = $2142 ; APUIO2


    ;; Writing `SWITCH_TO_LOADER` to this port should stop execution and start the loader.
    ;;
    ;; If the audio-driver is running; if the `SWITCH_TO_LOADER_BIT` is set,
    ;; the audio driver will stop and execute the loader.
    ;;
    ;; If the loader is in the middle of a transfer and both the `SWITCH_TO_LOADER_BIT`
    ;; and MSB (bit 7) bits are set, the loader will restart.
    SWITCH_TO_LOADER_PORT = $2143 ; APUIO3

    SWITCH_TO_LOADER_BIT = 5
    SWITCH_TO_LOADER = $80 | (1 << SWITCH_TO_LOADER_BIT)
; endscope


;; MUST match `audio-driver/src/io-commands.inc`
; scope TadIO_ToScpu
    ;; Audio driver command acknowledgment.
    ;;
    ;; Acknowledgment of the `ToDriver.command` byte.  Not used in the loader.
    ;;
    ;; After the command has been processed, the `IO.ToDriver.command` value will be written to this port.
    COMMAND_ACK_PORT = $2140 ; APUIO0


    ;; The mode the S-SMP is currently executing.
    ;;
    ;; Used by both the loader and the audio-driver.
    ;;
    ;; NOTE: The IPL sets this value after at has cleared the zero-page.
    ;;       Do not read this value immediately after reset.
    ;;       Make sure enough time has passed for the IPL to set IO Port 1
    ;;       to $bb before reading this port.
    MODE_PORT = $2141 ; APUIO1

    ;; The S-SMP is at the start of the IPL, waiting for the ready signal.
    MODE_IPL = $bb

    ;; The S-SMP is running the loader.
    MODE_LOADER = $4c ; 'L', Loader.LOADER_READY_L

    ;; The S-SMP is running the audio-driver.
    MODE_AUDIO_DRIVER = $61 ; 'a'
; endscope


;; MUST match `audio-driver/src/io-commands.inc`
; scope TadLoaderDataType
    CODE = 0
    COMMON_DATA = 1

    SONG_DATA_FLAG = 1 << 7
    PLAY_SONG_FLAG = 1 << 6
    RESET_GLOBAL_VOLUMES_FLAG = 1 << 5

    STEREO_FLAG = 1 << 1
    SURROUND_FLAG = 1 << 0
; endscope


;; MUST match `audio-driver/src/io-commands.inc`
; scope TadIO_Loader_Init
    LOADER_DATA_TYPE_PORT = $2141 ; APUIO1
    READY_PORT_L = $2142 ; APUIO2
    READY_PORT_H = $2143 ; APUIO3

    READY_PORT_HL = $2142 ; APUIO2 & APUIO3

    LOADER_READY_L = %01001100 ; 'L'
    LOADER_READY_H = %01000100 ; 'D'
    LOADER_READY_HL = LOADER_READY_L | (LOADER_READY_H << 8)
; endscope


;; MUST match `audio-driver/src/io-commands.inc`
; scope TadIO_Loader
    DATA_PORT_L = $2141 ; APUIO1
    DATA_PORT_H = $2142 ; APUIO2
    SPINLOCK_PORT = $2143 ; APUIO3

    ;; The spinlock value when the audio driver starts playing a song
    SPINLOCK_INIT_VALUE = 0

    ;; Only the lower 4 bits of the spinlock should be set while sending data to the loader
    SPINLOCK_MASK = $0f

    ;; Signal to the loader that the transfer has completed.
    SPINLOCK_COMPLETE = $80

    ;; If this value is written to the spinlock, the loader will restart;
    SPINLOCK_SWITCH_TO_LOADER = SWITCH_TO_LOADER
; endscope


; enum TadState
    NULL = $00
    ;; Waiting for loader to send the ready signal before loading common-audio-data
    WAITING_FOR_LOADER_COMMON = $7b
    ;; Waiting for loader to send the ready signal before loading song data
    WAITING_FOR_LOADER_SONG = $7c
    ;; Loading common audio data.
    LOADING_COMMON_AUDIO_DATA = $7d
    ;; Loading a song and the PLAY_SONG_FLAG was clear.
    LOADING_SONG_DATA_PAUSED = $7e
    ;; Loading a song and the PLAY_SONG_FLAG was set.
    LOADING_SONG_DATA_PLAY = $7f
    ;; Song is loaded into Audio-RAM and the audio driver is paused.
    ;; No play-sound-effect commands will be sent when the driver is paused.
    PAUSED = $80
    ;; Song is loaded into Audio-RAM and the audio driver is playing sfx (song paused).
    PLAYING_SFX = $81
    ;; Song is loaded into Audio-RAM and the audio driver is playing the song.
    PLAYING = $82
; endenum
TAD__FIRST_WAITING_STATE = WAITING_FOR_LOADER_COMMON
TAD__FIRST_LOADING_STATE = LOADING_COMMON_AUDIO_DATA
TAD__FIRST_LOADING_SONG_STATE = LOADING_SONG_DATA_PAUSED


; scope TadFlags
    RELOAD_COMMON_AUDIO_DATA = 1 << 7
    PLAY_SONG_IMMEDIATELY = 1 << 6
    RESET_GLOBAL_VOLUMES_ON_SONG_START = 1 << 5

    ;; A mask for the flags that are sent to the loader
    _ALL_FLAGS = RELOAD_COMMON_AUDIO_DATA | PLAY_SONG_IMMEDIATELY | RESET_GLOBAL_VOLUMES_ON_SONG_START
; endscope

; enum TadAudioMode
    MONO = 0
    STEREO = 1
    SURROUND = 2
; endenum

TAD_N_AUDIO_MODES = 3


;; Default values
;; ==============

; Using a single symbol to enable custom defaults as I am unable to detect if a `.define`
; exists using an if statement.
;
; I recommend using a `.define` for custom defaults so `TadFlags` and `TadAudioMode` values
; can be referenced before they are defined.
    ;; Default TAD flags
    ;; MUST NOT set RELOAD_COMMON_AUDIO_DATA
    TAD_DEFAULT_FLAGS = PLAY_SONG_IMMEDIATELY

    ;; Starting audio mode
    TAD_DEFAULT_AUDIO_MODE = MONO

    ;; Default number of bytes to transfer to Audio-RAM per `Tad_Process` call.
    ;;
    ;; MUST be between the TAD_MIN_TRANSFER_PER_FRAME and TAD_MAX_TRANSFER_PER_FRAME
    TAD_DEFAULT_TRANSFER_PER_FRAME = 256



;; =========
;; Variables
;; =========


; [segment BSS -> re-homed]

; ----------------
; Public variables
; ----------------
    ;; `TadFlags` bitfield
    ;; (see `TadFlags` namespace)
Tad_flags = $7E0030

    ;; Mono/Stereo/Surround audio mode
    ;; (`TadAudioMode` enum)
Tad_audioMode = $7E0031

; -----------------
; Private variables
; -----------------
    ;; The current audio driver state
    ;; (`TadState` enum)
TadPrivate_state = $7E0032

    ;; Number of bytes to transfer per `Tad_Process` call
    ;;
    ;; MUST be > 0
TadPrivate_bytesToTransferPerFrame = $7E0033

    ;; The previous `COMMAND_PORT` sent to the S-SMP audio driver.
TadPrivate_previousCommand = $7E0035


;; ---------------------------------------------------
;; Queue 1 - remaining data to transfer into Audio-RAM
;; ---------------------------------------------------
; [segment BSS -> re-homed]
    ;; A far pointer to the remaining data to transfer
TadPrivate_dataToTransfer_addr = $7E0036
TadPrivate_dataToTransfer_bank = $7E0038

    ;; The remaining number of bytes to transfer
TadPrivate_dataToTransfer_size = $7E0039

    ;; The previous value written to the loader spinLock
TadPrivate_dataToTransfer_prevSpinLock = $7E003B


;; ----------------------------------------------
;; Queue 2 - The next song to load into Audio-RAM
;; ----------------------------------------------
; [segment BSS -> re-homed]
    ;; The next song to load into Audio-RAM
    ;; Used by the `WAITING_FOR_LOADER_*` states
    ;; If this value is 0 or an invalid song, a blank silent song will be loaded instead.
TadPrivate_nextSong = $7E003C


;; ------------------------------------------------------
;; Queue 3 - The next command to send to the audio driver
;; ------------------------------------------------------
; [segment BSS -> re-homed]
    ;; The next `TadCommand` to send to the audio driver.
    ;; If this value is negative, the queue is empty.
TadPrivate_nextCommand_id = $7E003D

    ;; The two parameters of the next command (if any)
TadPrivate_nextCommand_parameter0 = $7E003E
TadPrivate_nextCommand_parameter1 = $7E003F


;; ---------------------------------------
;; Queue 4 - The next sound effect to play
;; ---------------------------------------
; [segment ZEROPAGE -> re-homed]
    ;; see tad-audio.inc
Tad_sfxQueue_sfx = $20
Tad_sfxQueue_pan = $21


;; Memory Map Asserts
;; ==================
; [segment BSS -> re-homed]
; [assert] assert ((* > $100) && (* < $2000)) || ((* > $7e0100) && (* < $7e2000)), lderror, ".bss is not in lowram"



;; ==================
;; Loader subroutines
;; ==================

; [segment TAD_PROCESS_SEGMENT -> re-homed]


;; Transfer and execute Loader using the IPL
;;
;; REQUIRES: S-SMP reset and no data has been written to it yet
;;
;; This macro MUST only be called once.  There is no way to reset the S-SMP and restart the IPL.
;;
;; A8
;; I16
;; DB access registers



;; Sends a TadLoaderDataType byte to the loader if the loader is ready
;;
;; Assumes loader just started OR a `SWITCH_TO_LOADER` message was sent to the audio driver/loader.
;;
;; IN: A = TadLoaderDataType value
;; OUT: carry = loader is ready and TadLoaderDataType sent
;;
.a8
.i16
;; DB access registers
TadPrivate_Loader_CheckReadyAndSendLoaderDataType:
    ; Test if the loader is ready
    ldx #LOADER_READY_HL
    cpx READY_PORT_HL
    bne TadPrivate_Loader_CheckReadyAndSendLoaderDataType__ReturnFalse
        ; Send the ready signal and the TadLoaderDataType
        sta LOADER_DATA_TYPE_PORT

        lda #LOADER_READY_L
        sta READY_PORT_L

        lda #LOADER_READY_H
        sta READY_PORT_H

        ; The S-CPU must wait for the loader to write 0 to the spinlock before transferring data.
        stz TadPrivate_dataToTransfer_prevSpinLock

        ; return true
        sec
        rts

TadPrivate_Loader_CheckReadyAndSendLoaderDataType__ReturnFalse:
    clc
    rts



;; Set the data transfer queue
;;
;; IN: A:X = far address
;; IN: Y = size
.a8
.i16
;; DB access registers
TadPrivate_Loader_SetDataToTransfer:
    stx TadPrivate_dataToTransfer_addr
    sta TadPrivate_dataToTransfer_bank
    sty TadPrivate_dataToTransfer_size

    rts



;; Transfer data to the audio loader.
;;
;; ASSUMES: `check_ready_and_send_loader_data_type` and `set_data_to_transfer` were previously called.
;;
;; NOTE: This function may read one byte past the end of the transfer queue.
;;
;; OUT: carry set if all data in the transfer queue was sent to Audio-RAM.
;;
.a8
.i16
;; DB access lowram
TadPrivate_Loader_TransferData:
    ; Early exit if the loader is not ready
    ;
    ; This test doubles as a lock for the previous transfer.
    ;
    ; This also prevents a freeze in `process()` if the loader has crashed/glitched.
    ; (`finish_loading_data()` will freeze if the loader has crashed/glitched.
    lda TadPrivate_dataToTransfer_prevSpinLock
    cmp.l SPINLOCK_PORT
    bne TadPrivate_Loader_TransferData__ReturnFalse

    phd
    phb

    rep #$30
.a16

    ; Calculate number of words to read
    lda TadPrivate_dataToTransfer_size
    cmp TadPrivate_bytesToTransferPerFrame
    bcc __anon0
        lda TadPrivate_bytesToTransferPerFrame
    __anon0:
    inc ; required
    lsr

    ; Prevent corrupting all of Audio-RAM if number of words == 0
    bne __anon1
        inc
    __anon1:
    ; Store word to read in X
    tax

    ; Reverse subtract TadPrivate_dataToTransfer_size (with clamping)
    asl ; convert number of words to number of bytes
    eor #$ffff
    sec
    adc TadPrivate_dataToTransfer_size
    bcs __anon2
        lda #0
    __anon2:
    sta TadPrivate_dataToTransfer_size


    lda #$2100
    tcd
; D = $2100

    sep #$20
.a8

    lda TadPrivate_dataToTransfer_bank
    ldy TadPrivate_dataToTransfer_addr

    pha
    plb
; DB = TadPrivate_dataToTransfer_bank

    TadPrivate_Loader_TransferData__Loop:
        ; x = number of words remaining
        ; y = data address (using y to force addr,y addressing mode)

        lda 0,y
        sta.b <(DATA_PORT_L)

        ; The bank overflow test must be done here as `TadPrivate_dataToTransfer_addr` might point to an odd memory address.
        iny
        beq TadPrivate_Loader_TransferData__BankOverflow_1
    TadPrivate_Loader_TransferData__BankOverflow_1_Resume:

        lda 0,y
        sta.b <(DATA_PORT_H)

        ; Increment this spinloack value
        ;
        ; The upper 4 bits of the spinlock must be clear'
        ; Cannot be 0.  Zero is used to spinlock the loader init before this TadPrivate_Loader_TransferData__Loop starts
        ;               (see Loader Step 3 in `audio-driver/src/io-commands.inc`)

; [assert] assert ($ffff & 7) + 1 < TadIO_Loader::SPINLOCK_MASK, error
        tya ; y = address of data, it should always increment by 2
        and #7
        inc
        sta.b <(SPINLOCK_PORT)

        iny
        beq TadPrivate_Loader_TransferData__BankOverflow_2
    TadPrivate_Loader_TransferData__BankOverflow_2_Resume:

        dex
        beq TadPrivate_Loader_TransferData__EndLoop

        ; Spinloop until the S-SMP has acknowledged the data
        __anon3:
            cmp.b <(SPINLOCK_PORT)
            bne __anon3

        bra TadPrivate_Loader_TransferData__Loop
TadPrivate_Loader_TransferData__EndLoop:

    plb
    pld
; DB restored
; D = 0

    sty TadPrivate_dataToTransfer_addr
    sta TadPrivate_dataToTransfer_prevSpinLock


    ldy TadPrivate_dataToTransfer_size
    bne TadPrivate_Loader_TransferData__ReturnFalse
        ; End of data transfer

        ; Wait for Loader to acknowledge the last write
        __anon4:
            cmp.l SPINLOCK_PORT
            bne __anon4

        ; No more data to transfer
        lda #SPINLOCK_COMPLETE
        sta.l SPINLOCK_PORT

        sec
        rts

TadPrivate_Loader_TransferData__ReturnFalse:
    clc
    rts


TadPrivate_Loader_TransferData__BankOverflow_1:
    jsr TadPrivate_Loader_GotoNextBank
    bra TadPrivate_Loader_TransferData__BankOverflow_1_Resume

TadPrivate_Loader_TransferData__BankOverflow_2:
    ; Must save/restore A, it holds the spinlock
    pha
        jsr TadPrivate_Loader_GotoNextBank
    pla
    bra TadPrivate_Loader_TransferData__BankOverflow_2_Resume


;; Advance to the next bank
;;
;; MUST only be called to TadPrivate_Loader_TransferData
;;
;; ASSUMES: Y = 0 (Y addr overflowed to 0)
;;
;; IN: Y = 0
;; IN: DB = TadPrivate_dataToTransfer_bank
;;
;; OUT: Y = new address
;; OUT: DB = new bank
;;
;; KEEP: X
.a8
.i16
; DB = TadPrivate_dataToTransfer_bank
TadPrivate_Loader_GotoNextBank:
    phb
    pla

    inc
    sta.l TadPrivate_dataToTransfer_bank

    pha
    plb
; DB = new TadPrivate_dataToTransfer_bank value

    ; MUST NOT CHANGE X

    ; Y = 0
    and #$fe
    cmp #$7e
    beq __anon5
        ; Bank is not Work-RAM
        ldy #$8000
    __anon5:

    ; Y = 0 or $8000
        rts


    ;; OUT: carry set if state is LOADING_*


;; ==========
;; Public API
;; ==========

;; -------------------------------
;; TAD_PROCESS_SEGMENT subroutines
;; -------------------------------

; [segment TAD_PROCESS_SEGMENT -> re-homed]


; JSL/RTL subroutine
.a8
.i16
; DB unknown
Tad_Init:
    phb

    lda #$80
    pha
    plb
; DB = $80

; [assert] assert .asize = 8, error
; [assert] assert .isize = 16, error

APUIO0 = $2140
APUIO1 = $2141
APUIO2 = $2142
APUIO3 = $2143

    ; Clear start command port (just in case APUIO0 has $cc in it)
    ; SOURCE: `blarggapu.s` from lorom-template, originally written by blargg (Shay Green)
    stz APUIO0

    ; Wait for ready signal
    ldy #$bbaa
    __anon6:
        cpy APUIO0
        bne __anon6

    ldx #TAD_LOADER_ARAM_ADDR
    lda #$cc
    stx APUIO2 ; destination ARAM address
    sta APUIO1 ; non-zero = write data to address
    sta APUIO0 ; New data command (non-zero and APUIO0 + more than 2, or $cc on the first transfer)

    ; Wait for a response from the IPL
    __anon7:
        cmp APUIO0
        bne __anon7


    ; Transfer the data
; [assert] assert Tad_Loader_SIZE < $ff, error, "Cannot fit Tad_Loader_SIZE in an 8 bit index"

    sep #$30
.i8
    ldx #0
    Tad_Init__IplLoop:
        ; Send the next byte to the IPL
        lda.l Tad_Loader_Bin,x
        sta APUIO1

        ; Tell the IPL the next byte is ready
        stx APUIO0

        ; Wait for a response form the IPL
        __anon8:
            cpx APUIO0
            bne __anon8

        inx
        cpx #Tad_Loader_SIZE
        bcc Tad_Init__IplLoop

    rep #$10
.i16

    ; Send an execute program command to the IPL
    ldx #TAD_LOADER_ARAM_ADDR
    stx APUIO2 ; A-RAM address
    stz APUIO1 ; zero = execute program at A-RAM address
    lda #Tad_Loader_SIZE + 2
    sta APUIO0 ; New data command (must be +2 the previous APUIO0 write)


    ; Set default settings
; [assert] assert (TAD_DEFAULT_FLAGS) & TadFlags::RELOAD_COMMON_AUDIO_DATA = 0, error, "RELOAD_COMMON_AUDIO_DATA flag must not be use in TAD_DEFAULT_FLAGS"
; [assert] assert (TAD_DEFAULT_FLAGS) & TadFlags::_ALL_FLAGS = (TAD_DEFAULT_FLAGS), error, "Invalid TAD_DEFAULT_FLAGS"
; [assert] assert (TAD_DEFAULT_AUDIO_MODE) >= 0 && (TAD_DEFAULT_AUDIO_MODE) < TAD_N_AUDIO_MODES, error, "Invalid TAD_DEFAULT_AUDIO_MODE"

; [assert] assert Tad_flags + 1 = Tad_audioMode, error
    ldx #(TAD_DEFAULT_FLAGS) | ((TAD_DEFAULT_AUDIO_MODE) << 8)
    stx Tad_flags

    ldx #TAD_DEFAULT_TRANSFER_PER_FRAME
    stx TadPrivate_bytesToTransferPerFrame


    lda #^(Tad_AudioDriver_Bin)
    ldx #((Tad_AudioDriver_Bin)&$ffff)
    ldy #Tad_AudioDriver_SIZE
    jsr TadPrivate_Loader_SetDataToTransfer

    lda #$ff
    sta TadPrivate_nextCommand_id
    sta Tad_sfxQueue_sfx

    stz TadPrivate_nextSong

    Tad_Init__DataTypeLoop:
        lda #CODE
        jsr TadPrivate_Loader_CheckReadyAndSendLoaderDataType
        bcc Tad_Init__DataTypeLoop

    Tad_Init__TransferLoop:
        jsr TadPrivate_Loader_TransferData
        bcc Tad_Init__TransferLoop

    lda #WAITING_FOR_LOADER_COMMON
    sta TadPrivate_state

    plb
; DB restored
    rtl


;; Sends a command to the audio driver.
;;
;; REQUIRES: state == PAUSED or state == PLAYING.
;; REQUIRES: The previous command has been processed by the audio-driver.
;; REQUIRES: `TadPrivate_nextCommand_id` is not a play-sound-effect command.
;; REQUIRES: `TadPrivate_nextCommand_id` is a valid comma.
;;
;; IN: Y = TadPrivate_nextCommand_id
.a8
.i8
;; DB access lowram



;; Send a play-sound-effect command to the audio driver.
;;
;; REQUIRES: state == PLAYING
;; REQUIRES: The previous command has been processed by the audio-driver.
;;
;; IN: A = Tad_sfxQueue_sfx
;;
;; A8
;; I8
;; DB access lowram



; JSL/RTL subroutine
.a8
.i16
; DB access lowram
Tad_Process:
; [assert] assert TadState::PAUSED = $80, error
; [assert] assert TadState::PLAYING > $80, error
    lda TadPrivate_state
    bmi __TadProc_Loaded
    jmp Tad_Process__NotLoaded
__TadProc_Loaded:
        ; Playing or paused state
        sep #$10
    .i8
        tax

        lda TadPrivate_previousCommand
        cmp.l COMMAND_ACK_PORT
        bne Tad_Process__Return_I8
            ; Previous command has been processed

            ; Check command queue
            ldy TadPrivate_nextCommand_id
            bpl Tad_Process__SendCommand

            ; X = TadPrivate_state
; [assert] assert TadState::PAUSED < $81, error
; [assert] assert TadState::PLAYING >= $81, error
; [assert] assert TadState::PLAYING_SFX >= $81, error
            dex
            bpl Tad_Process__Return_I8
                ; Playing state
                lda Tad_sfxQueue_sfx
                cmp #$ff
                beq Tad_Process__Return_I8
; [assert] assert .asize = 8, error
; [assert] assert .isize = 8, error

    ; parameter 0 = sfx_id
    sta.l PARAMETER0_PORT

    ; parameter 1 = pan
    lda Tad_sfxQueue_pan
    cmp #TAD_MAX_PAN + 1
    bcc __anon9
        lda #TAD_CENTER_PAN
    __anon9:
    sta.l PARAMETER1_PORT

    ; Send play-sound-effect command
    lda TadPrivate_previousCommand
    and #COMMAND_I_MASK ; Clear the non i bits of the command
    eor #COMMAND_I_MASK ; Flip the i bits
    ora #PLAY_SOUND_EFFECT ; Set the c bits

    sta.l COMMAND_PORT
    sta TadPrivate_previousCommand

    ; Reset the SFX queue
    ldy #$ff
    sty Tad_sfxQueue_sfx
    sty Tad_sfxQueue_pan

        Tad_Process__Return_I8:
            rep #$10
        .i16
            rtl

        .a8
        .i8
        Tad_Process__SendCommand:
; [assert] assert .asize = 8, error
; [assert] assert .isize = 8, error

    lda TadPrivate_nextCommand_parameter0
    sta.l PARAMETER0_PORT

    lda TadPrivate_nextCommand_parameter1
    sta.l PARAMETER1_PORT

    lda TadPrivate_previousCommand
    and #COMMAND_I_MASK ; Clear the non i bits of the command
    eor #COMMAND_I_MASK ; Flip the i bits
    ora TadPrivate_nextCommand_id ; Set the c bits
    sta.l COMMAND_PORT
    sta TadPrivate_previousCommand

    cpy #UNPAUSE + 1
    bcs Tad_Process__NotPauseOrPlay
        ; Change state if the command is a pause or play command
; [assert] assert TadCommand::PAUSE = 0, error
; [assert] assert TadCommand::PAUSE_MUSIC_PLAY_SFX = 2, error
; [assert] assert TadCommand::UNPAUSE = 4, error
; [assert] assert (TadCommand::PAUSE >> 1) & 3 | $80 = TadState::PAUSED, error
; [assert] assert (TadCommand::PAUSE_MUSIC_PLAY_SFX >> 1) & 3 | $80 = TadState::PLAYING_SFX, error
; [assert] assert (TadCommand::UNPAUSE >> 1) & 3 | $80 = TadState::PLAYING, error
        lsr
        and #3
        ora #$80
        sta TadPrivate_state
Tad_Process__NotPauseOrPlay:

    ; Reset command queue
    lda #$ff
    sta TadPrivate_nextCommand_id
            rep #$10
        .i16
            rtl

    Tad_Process__NotLoaded:
        ; Song is not loaded into Audio-RAM

        ; Test if state is WAITING_FOR_LOADER_* or LOADING_*
; [assert] assert TAD__FIRST_LOADING_STATE > TAD__FIRST_WAITING_STATE, error
; [assert] assert TAD__FIRST_LOADING_STATE = TadState::WAITING_FOR_LOADER_SONG + 1, error
        cmp #TAD__FIRST_LOADING_STATE
        bcs TadPrivate_Process_Loading
        cmp #TAD__FIRST_WAITING_STATE
        bcs TadPrivate_Process_WaitingForLoader

    ; TadState is null
    rtl



;; Process the WAITING_FOR_LOADER_* states
;;
;; return using RTL
.a8
.i16
;; DB access lowram
TadPrivate_Process_WaitingForLoader:
    phb

    ; Setting DB to access registers as it:
    ;  * Simplifies `TadPrivate_Loader_CheckReadyAndSendLoaderDataType`
    ;  * Ensures `LoadAudioData` is called with a fixed data bank
    ;    (NOTE: `LoadAudioData` is tagged `DB access registers`)
    lda #$80
    pha
    plb
; DB = $80

    lda TadPrivate_state
    cmp #WAITING_FOR_LOADER_COMMON
    bne TadPrivate_Process_WaitingForLoader__SongData
        ; Common audio data
        lda #COMMON_DATA
        jsr TadPrivate_Loader_CheckReadyAndSendLoaderDataType
        bcc TadPrivate_Process_WaitingForLoader__Return

        lda #LOADING_COMMON_AUDIO_DATA
        pha

        lda #0
        bra TadPrivate_Process_WaitingForLoader__LoadData

    TadPrivate_Process_WaitingForLoader__SongData:
        ; Songs

        ; Tad_flags MUST NOT have the stereo/surround loader flag set
; [assert] assert TadFlags::_ALL_FLAGS & TadLoaderDataType::STEREO_FLAG = 0, error
; [assert] assert TadFlags::_ALL_FLAGS & TadLoaderDataType::SURROUND_FLAG = 0, error

        ; SONG_DATA_FLAG must always be sent and it also masks the RELOAD_COMMON_AUDIO_DATA flag in TadLoaderDataType
; [assert] assert TadFlags::RELOAD_COMMON_AUDIO_DATA = TadLoaderDataType::SONG_DATA_FLAG, error, "Cannot hide RELOAD_COMMON_AUDIO_DATA TadFlag with SONG_DATA_FLAG"

; [assert] assert TadFlags::PLAY_SONG_IMMEDIATELY = TadLoaderDataType::PLAY_SONG_FLAG, error
; [assert] assert TadFlags::RESET_GLOBAL_VOLUMES_ON_SONG_START = TadLoaderDataType::RESET_GLOBAL_VOLUMES_FLAG, error

        ; Clear unused TAD flags
        lda #$ff ^ _ALL_FLAGS
        trb Tad_flags

        ; Convert `Tad_audioMode` to TadLoaderDataType and combine with TadFlags
; [assert] assert ((0 + 1) & 3) = TadLoaderDataType::SURROUND_FLAG, error ; mono
; [assert] assert ((1 + 1) & 3) = TadLoaderDataType::STEREO_FLAG, error ; stereo
; [assert] assert ((2 + 1) & 3) = TadLoaderDataType::STEREO_FLAG | TadLoaderDataType::SURROUND_FLAG, error ; surround
        lda Tad_audioMode
        inc
        and #3

        ora Tad_flags
        ora #SONG_DATA_FLAG
        jsr TadPrivate_Loader_CheckReadyAndSendLoaderDataType
        bcc TadPrivate_Process_WaitingForLoader__Return

        ; Determine next state
; [assert] assert TadFlags::PLAY_SONG_IMMEDIATELY = $40, error
; [assert] assert TadState::LOADING_SONG_DATA_PAUSED + 1 = TadState::LOADING_SONG_DATA_PLAY, error
        lda Tad_flags
        asl
        asl
        lda #0
        ; carry = PLAY_SONG_IMMEDIATELY flag
        adc #LOADING_SONG_DATA_PAUSED
        pha

        ; Load next song
        lda TadPrivate_nextSong
        beq TadPrivate_Process_WaitingForLoader__UseBlankSong

TadPrivate_Process_WaitingForLoader__LoadData:
    jsl LoadAudioData
    bcs __anon10
        ; LoadAudioData returned false
    TadPrivate_Process_WaitingForLoader__UseBlankSong:
        ; The blank song is a single zero byte.
        ; ::HACK use the 3rd byte of `ldy #1` (which is `0x00`) for the blank song 
        ldy #1
        TadPrivate_Process_WaitingForLoader___blanksongdata = * - 1
        lda #^(TadPrivate_Process_WaitingForLoader___blanksongdata)
        ldx #((TadPrivate_Process_WaitingForLoader___blanksongdata)&$ffff)
    __anon10:

    ; STACK holds next state
    ; A:X = data address
    ; Y = data size
    jsr TadPrivate_Loader_SetDataToTransfer

    ; Must set state AFTER the `LoadAudioData` call.
    ; `LoadAudioData` might call `Tad_FinishLoadingData`.
    pla
    sta TadPrivate_state

TadPrivate_Process_WaitingForLoader__Return:
    plb
; DB restored
    rtl



;; Process the LOADING_* states
;;
;; return using RTL
.a8
.i16
;; DB access lowram
TadPrivate_Process_Loading:
    jsr TadPrivate_Loader_TransferData
    bcc TadPrivate_Process_Loading__Return
        ; Data loaded successfully
        lda TadPrivate_state
        cmp #LOADING_COMMON_AUDIO_DATA
        bne TadPrivate_Process_Loading__Song
            ; Common audio data was just transferred
            ; Loader is still active
            lda #WAITING_FOR_LOADER_SONG
            bra TadPrivate_Process_Loading__EndIf

        TadPrivate_Process_Loading__Song:
            ; TadPrivate_Process_Loading__Song data was loaded into Audio-RAM
            ; Loader has finished, audio driver is now active

            stz TadPrivate_previousCommand

            ; Reset command and SFX queues
            lda #$ff
            sta TadPrivate_nextCommand_id
            sta Tad_sfxQueue_sfx
            sta Tad_sfxQueue_pan

            ; Use `TadPrivate_state` to determine if the TadPrivate_Process_Loading__Song is playing or paused.
            ; Cannot use `Tad_flags` as it may have changed after the `TadLoaderDataType` was sent to
            ; the loader (while the TadPrivate_Process_Loading__Song was loaded).
; [assert] assert ((TadState::LOADING_SONG_DATA_PAUSED & 1) << 1) | $80 = TadState::PAUSED, error
; [assert] assert ((TadState::LOADING_SONG_DATA_PLAY & 1) << 1) | $80 = TadState::PLAYING, error
            lda TadPrivate_state
            and #1
            asl
            ora #$80

        ; A = new state
    TadPrivate_Process_Loading__EndIf:
        sta TadPrivate_state

TadPrivate_Process_Loading__Return:
    rtl



; JSL/RTL subroutine
.a8
.i16
; DB access lowram
Tad_FinishLoadingData:
    Tad_FinishLoadingData__Loop:
; [assert] assert .asize = 8, error

; [assert] assert TadState::NULL < TAD__FIRST_LOADING_STATE, error
; [assert] assert TadState::WAITING_FOR_LOADER_COMMON < TAD__FIRST_LOADING_STATE, error
; [assert] assert TadState::WAITING_FOR_LOADER_SONG < TAD__FIRST_LOADING_STATE, error
; [assert] assert (TadState::PAUSED & $7f) < TAD__FIRST_LOADING_STATE, error
; [assert] assert (TadState::PLAYING & $7f) < TAD__FIRST_LOADING_STATE, error

    lda TadPrivate_state
    and #$7f
    cmp #TAD__FIRST_LOADING_STATE
        bcc Tad_FinishLoadingData__EndLoop
            jsl TadPrivate_Process_Loading
        bra Tad_FinishLoadingData__Loop
    Tad_FinishLoadingData__EndLoop:

    rtl


;; ----------------------------
;; TAD_CODE_SEGMENT subroutines
;; ----------------------------

; [segment TAD_CODE_SEGMENT -> re-homed]


; IN: A = command
; IN: X = first parameter
; IN: Y = second parameter
; OUT: Carry set if command added to queue
.a8
; I unknown
; DB access lowram
Tad_QueueCommand:
    bit TadPrivate_nextCommand_id
    bpl Tad_QueueCommand__ReturnFalse
        ; command queue is empty
    Tad_QueueCommand__WriteCommand:
        and #COMMAND_MASK
        sta TadPrivate_nextCommand_id

        txa
        sta TadPrivate_nextCommand_parameter0

        tya
        sta TadPrivate_nextCommand_parameter1

        ; return true
        sec
        rts

Tad_QueueCommand__ReturnFalse:
    clc
    rts


; IN: A = command
; IN: X = first parameter
; IN: Y = second parameter
.a8
; I unknown
; DB access lowram
Tad_QueueCommandOverride = WriteCommand



; IN: A = sfx id
; IN: X = pan
.a8
; I unknown
; DB access lowram
; KEEP: X, Y
Tad_QueuePannedSoundEffect:
    cmp Tad_sfxQueue_sfx
    bcs Tad_QueuePannedSoundEffect__EndIf
        sta Tad_sfxQueue_sfx

        txa
        sta Tad_sfxQueue_pan

Tad_QueuePannedSoundEffect__EndIf:
    rts



; IN: A = sfx_id
.a8
; I unknown
; DB access lowram
; KEEP: X, Y
Tad_QueueSoundEffect:
    cmp Tad_sfxQueue_sfx
    bcs Tad_QueueSoundEffect__EndIf
        sta Tad_sfxQueue_sfx

        lda #TAD_CENTER_PAN
        sta Tad_sfxQueue_pan
Tad_QueueSoundEffect__EndIf:
    rts



; JSL/RTL subroutine
; IN: A = song_id
.a8
; I unknown
; DB access lowram
Tad_LoadSong:
; [assert] assert TAD__FIRST_LOADING_SONG_STATE > TadState::NULL, error
; [assert] assert TAD__FIRST_LOADING_SONG_STATE > TadState::WAITING_FOR_LOADER_COMMON, error
; [assert] assert TAD__FIRST_LOADING_SONG_STATE > TadState::WAITING_FOR_LOADER_SONG, error
; [assert] assert TAD__FIRST_LOADING_SONG_STATE > TadState::LOADING_COMMON_AUDIO_DATA, error


    sta TadPrivate_nextSong

    lda #RELOAD_COMMON_AUDIO_DATA
    trb Tad_flags
    beq Tad_LoadSong__SongRequested
        ; Common audio data requested
        lda #WAITING_FOR_LOADER_COMMON
        bra Tad_LoadSong__SetStateAndSwitchToLoader

Tad_LoadSong__SongRequested:
    lda TadPrivate_state
    cmp #TAD__FIRST_LOADING_SONG_STATE
    bcc Tad_LoadSong__Return
        ; TadState is not NULL, WAITING_FOR_LOADER_* or LOADING_COMMON_AUDIO_DATA

        lda #WAITING_FOR_LOADER_SONG

    Tad_LoadSong__SetStateAndSwitchToLoader:
        sta TadPrivate_state

        ; Assert it is safe to send a switch-to-loader command when the loader is waiting for a READY signal
; [assert] assert TadIO_ToDriver::SWITCH_TO_LOADER <> TadIO_Loader_Init::LOADER_READY_H, error
; [assert] assert TadIO_ToDriver::SWITCH_TO_LOADER_PORT = TadIO_Loader_Init::READY_PORT_H, error

        ; Send a *switch-to-loader* command to the audio-driver or loader
        lda #SWITCH_TO_LOADER
        sta.l SWITCH_TO_LOADER_PORT
Tad_LoadSong__Return:
    rtl


; IN: A = song_id
; OUT: carry set if `Tad_LoadSong` was called
.a8
; I unknown
; DB access lowram
Tad_LoadSongIfChanged:
    cmp TadPrivate_nextSong
    beq __anon11
        jsl Tad_LoadSong
        sec
        rts
    __anon11:
    clc
    rts


;; OUT: A = The song_id used in the last `Tad_LoadSong` call.
.a8
; I unknown
; DB access lowram
Tad_GetSong:
    ; `TadPrivate_nextSong` is only written to in `Tad_Init` and `Tad_LoadSong`.
    lda TadPrivate_nextSong
    rts


.a8
; I unknown
; DB access lowram
Tad_ReloadCommonAudioData:
    lda #RELOAD_COMMON_AUDIO_DATA
    tsb Tad_flags
    rts


.a8
; I unknown
; DB access lowram
Tad_SongsStartImmediately:
    lda #PLAY_SONG_IMMEDIATELY
    tsb Tad_flags
    rts


.a8
; I unknown
; DB access lowram
Tad_SongsStartPaused:
    lda #PLAY_SONG_IMMEDIATELY
    trb Tad_flags
    rts


.a8
; I unknown
; DB access lowram
Tad_GlobalVolumesResetOnSongStart:
    lda #RESET_GLOBAL_VOLUMES_ON_SONG_START
    tsb Tad_flags
    rts


.a8
; I unknown
; DB access lowram
Tad_GlobalVolumesPersist:
    lda #RESET_GLOBAL_VOLUMES_ON_SONG_START
    trb Tad_flags
    rts


; IN: X = new `TadPrivate_bytesToTransferPerFrame` value
; A unknown
.i16
; DB access lowram
Tad_SetTransferSize:
    cpx #TAD_MAX_TRANSFER_PER_FRAME
    bcc __anon12
        ldx #TAD_MAX_TRANSFER_PER_FRAME
    __anon12:
    cpx #TAD_MIN_TRANSFER_PER_FRAME
    bcs __anon13
        ldx #TAD_MIN_TRANSFER_PER_FRAME
    __anon13:
    stx TadPrivate_bytesToTransferPerFrame

    rts



; OUT: carry set if state is LOADING_*
.a8
; I unknown
; DB access lowram
Tad_IsLoaderActive:
; [assert] assert .asize = 8, error

; [assert] assert TadState::NULL < TAD__FIRST_LOADING_STATE, error
; [assert] assert TadState::WAITING_FOR_LOADER_COMMON < TAD__FIRST_LOADING_STATE, error
; [assert] assert TadState::WAITING_FOR_LOADER_SONG < TAD__FIRST_LOADING_STATE, error
; [assert] assert (TadState::PAUSED & $7f) < TAD__FIRST_LOADING_STATE, error
; [assert] assert (TadState::PLAYING & $7f) < TAD__FIRST_LOADING_STATE, error

    lda TadPrivate_state
    and #$7f
    cmp #TAD__FIRST_LOADING_STATE
    rts



; OUT: carry set if state is PAUSED, PLAYING_SFX or PLAYING
.a8
; I unknown
; DB access lowram
Tad_IsSongLoaded:
; [assert] assert TadState::PLAYING_SFX > TadState::PAUSED, error
; [assert] assert TadState::PLAYING > TadState::PAUSED, error
    ; Assumes PLAYING is the last state

    lda TadPrivate_state
    cmp #PAUSED
    rts



; OUT: carry set if state is PLAYING_SFX or PLAYING
.a8
; I unknown
; DB access lowram
Tad_IsSfxPlaying:
; [assert] assert TadState::PLAYING > TadState::PLAYING_SFX, error
    ; Assumes PLAYING is the last state

    lda TadPrivate_state
    cmp #PLAYING_SFX
    rts



; OUT: carry set if state is PLAYING
.a8
; I unknown
; DB access lowram
Tad_IsSongPlaying:
    ; Assumes PLAYING is the last state

    lda TadPrivate_state
    cmp #PLAYING
    rts



; ============================================================================
; Walk animation + facing-flip tilemap data, relocated into TAD S-CPU-
; management slack (real Tad_IsSongPlaying body ends around $8B25 -- see
; raw-byte check below -- leaving ~8400 free bytes before the fixed
; .org $AC00). A PRIOR attempt to reuse this gap (see Anim_Play's header
; comment further below) moved a whole ROUTINE+blob here and crashed at
; runtime: a JSR to a label placed right after the insertion point resolved
; 13 bytes early. Direct raw-byte inspection this session also found
; Tad_IsSfxPlaying/Tad_IsSongPlaying's OWN exported symbol addresses drift
; +4 bytes (LATE, not early -- a different sign/magnitude than every other
; documented Poppy label-address bug) from their real code -- i.e. this
; specific $8800 region's label-address estimation is independently known
; to be unreliable, for reasons not root-caused. This relocation sidesteps
; that problem category entirely rather than trying to characterize it:
; NO code and NO Poppy-estimated label is placed/referenced here. `.org` is
; documented (and independently verified by tools/rom_audit/verify_layout.py)
; to reset CurrentAddress to its literal operand in BOTH Poppy's address-
; estimation pass and its real code-generation pass, so a fixed `.org`
; directive's target address cannot be wrong regardless of what estimation
; drift happened earlier in the file. Every reference to this blob elsewhere
; in main.pasm uses the literal hex constants below (ANIM_WALK_BASE /
; ANIM_TILEMAP_RIGHT_BASE / ANIM_TILEMAP_LEFT_BASE), never a label defined
; here -- so there is no address for Poppy to estimate wrong in the first
; place. Verify after any change: raw-byte-compare src/main.bin at file
; offset (this .org value - $8000) against the source .bin files directly
; (see build.md's Testing section), same method already proven for bugs
; 4/5/7/8 elsewhere in this project.
; ============================================================================
.org $8C00
    ; Walk's old pixel-data blob (8 frames * 768 = 6144 bytes) used to sit
    ; here, before the tilemap blocks -- gone now that walk streams from the
    ; MSU-1 roster instead (see ANIM_WALK_BASE's definition comment). Only
    ; the two generic facing-flip tilemap blocks remain.
    .incbin "assets/anim_tilemap_right.bin"    ; 48 bytes
    .incbin "assets/anim_tilemap_left.bin"     ; 48 bytes
    ; ends at $8C00 + 96 = $8C60, leaving ~8096 bytes free before $AC00.

; ============================================================================
; LoadAudioData Callback (LoROM mapping)
; ============================================================================
.org $AC00
.a8
.i16
LoadAudioData:
    cmp #N_DATA_ITEMS
    bcc .valid
        clc
        rtl
.valid:
    rep #$30
.a16
    and #$00FF
    pha
    asl
    adc 1,s
    tax

    ; Calculate data size
    lda.l Tad_DataTable+3,x
    sec
    sbc.l Tad_DataTable,x
    tay

    lda.l Tad_DataTable,x
    cmp #$8000
    ora #$8000
    sta 1,s

    sep #$20
.a8
    lda.l Tad_DataTable+2,x
    rol
    clc
    adc #AUDIO_DATA_BANK

    plx
    sec
    rtl

; ============================================================================
; Audio Data Blob ($B000 = file offset $3000)
; ============================================================================
.org $B000
    ; The compiler's --output-bin is already a combined blob:
    ; [loader 116][audio driver 3221][DataTable][common/song data].
    ; The 43-byte callback precedes that blob, matching ca65-export.
    .db $00, $00, $00, $00, $00, $00, $00, $00, $00, $00
    .db $00, $00, $00, $00, $00, $00, $00, $00, $00, $00
    .db $00, $00, $00, $00, $00, $00, $00, $00, $00, $00
    .db $00, $00, $00, $00, $00, $00, $00, $00, $00, $00
    .db $00, $00, $00
__Tad_AudioData_0:
    .incbin "../soundwork/tad/build/audio-data.bin"

; ============================================================================
; Core utility modules (ported from SNES-SuperBossGaiden, see src/core/)
; ============================================================================
.org $C100
.include "core/random.pasm"
.include "core/input.pasm"
.include "core/math.pasm"
.include "core/error.pasm"
.include "core/dma_channel.pasm"
.include "core/dma.pasm"
.include "core/allocate_wram.pasm"
.include "core/allocate_vram.pasm"
.include "core/allocate_cgram.pasm"
.include "core/oop.pasm"
.include "core/screen.pasm"
.include "core/nmi.pasm"
.include "core/oam.pasm"

; ============================================================================
; Ralf idle/walk animation: precomputed VRAM-format tile data ("Option B"
; from handoff.md -- CC-DMA still runs once at SA-1 boot to convert the
; static test sprite; animation frame swaps are plain VRAM DMA blits of
; frame data baked at CONVERT time, not more runtime CC-DMA passes). This
; sidesteps a second SA-1/S-CPU handshake protocol entirely, and reuses
; conversion math already validated byte-for-byte against this ROM's own
; boot-time CC-DMA output (see tools/bor_converter/bake_vram_frames.py's
; header -- it's a from-scratch reimplementation of Mesen2's
; Sa1::ReadCharConvertType1, verified against this ROM's real VRAM contents
; before being trusted for new frames).
;
; Each frame is exactly 768 bytes (24 tiles x 32 bytes, 4bpp) -- the same
; 4x6-tile BG2 window (tiles 1..24 at char base $2000) the static sprite
; already renders into, so no tilemap changes are needed to animate it.
; Frame counts/delays are no longer fixed per-character constants baked at
; build time -- they're per-character values read from the MSU-1 roster's
; directory record at load time (Anim_IdleFrameCount/Delay etc., see
; Anim_LoadCharacter). Ralf's own source data (out/ralf_{idle,walk,attack}/
; manifest.json) is idle=6/walk=8 (full cycle, loop=1)/attack=5 (full
; "attack1" cycle, loop=0), packed into bor.msu by pack_msu_roster.py.
; All hardcoded below (ANIM_*/WALK_*/ATTACK_*) rather than read from a ROM
; data table: standalone .dw tables resolve to garbage in this Poppy build
; regardless of placement (poppy_assembler_bugs memory), so small fixed
; tables get inlined as immediates/branches instead, same as the CGRAM
; palette load and Anim_Play_Idle/Anim_Play_Walk/Anim_Play_Attack's frame
; dispatch below.
;
; A first attempt (an earlier session) at putting the attack animation's
; ROUTINE+blob in the $8800-$AC00 TAD S-CPU-management region's apparent
; slack built with no assembler errors and passed a byte-level immediate-
; address check, but crashed at runtime -- Mesen showed forced blank stuck
; on and totally uninitialized WRAM even with the dispatcher untouched
; (attack never called), isolating the corruption to the TAD-gap insertion
; itself, not the dispatcher. Root cause not fully chased down (a JSR to a
; label right after the insertion point was found to resolve 13 bytes
; early, landing inside the *previous* routine's still-live tail code -- a
; bigger drift than the well-known 0-2 byte "label resolves early" class
; this project's nop-padding convention is built for), but the empirical
; result was unambiguous: large new CODE inserted into that gap silently
; broke something even without assembler errors. That attempt was reverted.
;
; A LATER session reused this same gap successfully, but for DATA only, and
; specifically NOT via a Poppy-estimated label: see the large comment above
; Tad_IsSongPlaying's `.org $8C00` block. That session also found, by direct
; raw-byte inspection, that Tad_IsSfxPlaying/Tad_IsSongPlaying's own
; exported symbol addresses drift +4 bytes (late, a different sign/
; magnitude than every other documented Poppy label bug) from their real
; code -- independent confirmation that this specific region's label-
; address ESTIMATION is unreliable for reasons still not root-caused. The
; fix that worked: never let Poppy estimate a label's address in this
; region at all -- use a literal `.org` value and literal hex constants
; derived from it (verified: `.org` resets CurrentAddress to its literal
; operand identically in both Poppy's estimation pass and its real codegen
; pass, so a fixed `.org` target cannot itself drift), and put no branches/
; JSRs/code here, only `.incbin`. Do not reuse this region for new CODE (JSR/
; branch targets, anything needing an estimated label address) without a
; much more thorough verification pass (checking every such label's true
; landing byte) than either session has done -- the underlying mechanism
; behind both the +13 and +4 byte drifts observed here is still unidentified.
; Idle's blob (and now attack's) still live in the $C100-$FC00 window,
; matching the originally validated-safe pattern (blobs after all branching
; code); walk's blob and the facing-flip tilemap blobs live in the TAD gap.
;
; Anim_Selected picks which animation Anim_Play advances/dispatches to:
; attack (Y button, edge-triggered) takes priority over dpad movement and
; latches until it finishes on its own; otherwise dpad Left/Right held ->
; walk, else idle (see Anim_Play below). All three animations share the
; same Anim_FrameIndex/Anim_TickCounter WRAM state -- safe because only one
; of Anim_Play_Idle/Anim_Play_Walk/Anim_Play_Attack ever runs per call,
; gated on Anim_Selected, so the shared counters are only ever mutated by
; whichever animation is currently active.
; ============================================================================
ANIM_FRAME_BYTES = 768       ; 24 tiles * 32 bytes/tile, 4bpp (all three anims)
ANIM_VRAM_DEST_BYTE = $4020  ; = word $2010 * 2 -- same BG2 window the
                              ; static sprite already occupies (tiles 1..24)
; Attack button: Y (bit14 overall = bit6 of Input_trigger's high byte, per
; core/input.pasm's $4218 layout comment "B Y Sel Start U D L R | A X L R
; 0000"). Edge-triggered (Input_trigger, not Input_press) so holding Y
; doesn't re-trigger every frame -- checked in Anim_Play's dispatcher below.
ANIM_ATTACK_BUTTON_MASK = $40
; Frame counts/delays (idle/walk/attack) used to be compile-time constants
; here (ANIM_FRAME_COUNT/DELAY, WALK_FRAME_COUNT/DELAY, ATTACK_FRAME_COUNT/
; DELAY), baked for the one character shipped in ROM. Now runtime WRAM
; values (Anim_IdleFrameCount/Delay, Anim_WalkFrameCount/Delay,
; Anim_AttackFrameCount/Delay, declared below), populated per-character by
; Anim_LoadCharacter from the MSU-1 roster's directory record -- see
; Anim_Play_Idle/Walk/Attack.
;
; The old AnimCharIdleFrames/AnimCharAttackFrames ROM .incbin blobs (and
; their ANIM_LABEL_FIXUP/ANIM_ATTACK_BASE_OFFSET address-workaround
; constants) are gone for the same reason: frame data now streams from the
; MSU-1 roster at runtime (Msu1_LoadFrame) instead of being baked into ROM
; at build time, so there's no ROM data label left to work around.
;
; ANIM_WALK_BASE / ANIM_TILEMAP_RIGHT_BASE / ANIM_TILEMAP_LEFT_BASE: the
; walk pixel-data blob that used to sit at ANIM_WALK_BASE ($8C00, in the TAD
; S-CPU-management gap -- see the large comment above Tad_IsSongPlaying's
; `.org $8C00` block) is gone for the same MSU-streaming reason above; only
; the two facing-flip tilemap blocks (generic column-order/hflip patterns,
; not character pixel data, so they stay ROM-resident) remain there now,
; starting right at ANIM_WALK_BASE itself. Deliberately a literal hex
; constant, not an expression involving a Poppy-estimated label address:
; `.org` is documented (and independently verified by
; tools/rom_audit/verify_layout.py) to reset Poppy's CurrentAddress to
; exactly its operand value in BOTH the address-estimation pass and the real
; code-generation pass, so a literal `.org` target can't drift the way an
; estimated label can.
ANIM_WALK_BASE = $8C00
; Facing flip: BG2 tilemap entries carry their own h-flip bit (bit14) plus
; tile index, so mirroring the whole 4x6 sprite means BOTH setting that bit
; per tile AND reversing the tiles' column order (tx -> 3-tx) -- flipping
; each tile's own pixels without also swapping column order would scramble
; the image, not mirror it. Two small precomputed 48-byte tilemap blocks
; (24 entries x 2 bytes, one per facing) are baked and DMA'd over the
; active 4x6 region's entries (6 rows of 4 columns each) whenever facing
; changes -- see Anim_UpdateFacing below.
ANIM_TILEMAP_ROW_BYTES = 8          ; 4 columns * 2 bytes/entry
ANIM_TILEMAP_ROW_STRIDE = $40       ; byte distance between rows in the 32-
                                     ; column-wide tilemap ($5C00 base, word
                                     ; stride 32 -> byte stride 64 = $40)
ANIM_TILEMAP_ROW0_BYTE_ADDR = $B800  ; = word $5C00 * 2 (row 0, column 0)
ANIM_TILEMAP_RIGHT_BASE = ANIM_WALK_BASE   ; walk's old pixel-data blob (which used to
                              ; sit before this) is gone -- see the comment above
                              ; ANIM_WALK_BASE's own definition
ANIM_TILEMAP_LEFT_BASE = ANIM_TILEMAP_RIGHT_BASE + (6 * ANIM_TILEMAP_ROW_BYTES)

Anim_FrameIndex  = $7E53B0   ; .db -- current frame of the active animation
Anim_TickCounter = $7E53B1   ; .db -- frames remaining until next advance
Anim_Selected    = $7E53B2   ; .db -- 0 = idle, 1 = walk, 2 = attack (which anim is live)
Anim_FacingLeft  = $7E53B3   ; .db -- 0 = facing right (boot default), 1 = facing left

; Player_PlayFrame's own state for the second, dpad-driven test sprite -- see
; that routine's header, below TestSprite_PlayFrame. Now 2-axis:
; X moves on held Left/Right, Y moves on held Up/Down, independently
; clamped, both read from Input_press+1 as two separate masks (not one
; shared accumulator threaded across both axes' branches -- see the
; routine body for why).
Player_X = $7E53B4 ; .db -- sprite 1's current X, clamped to MIN/MAX_X
Player_Y = $7E53B5 ; .db -- sprite 1's current Y, clamped to MIN/MAX_Y
                              ;        (was TestSprite2_DirLeft, deleted -- no more
                              ;        autonomous bounce direction to track once
                              ;        movement is input-driven and clamped instead
                              ;        of bounced; reused here for the Y axis)
PLAYER_MIN_X = 8
PLAYER_MAX_X = 216         ; 16px sprite, keeps it fully on the 256px screen
PLAYER_MIN_Y = 8
PLAYER_MAX_Y = 208         ; 16px sprite, 224-line visible screen: 208+16=224
PLAYER_SPEED = 2           ; shared between axes
; Clamp-wrap safety invariant (both axes): SPEED <= MIN (sbc side) and
; MAX + SPEED <= 255 (adc side), or the add/subtract can wrap past the
; clamp and teleport to the opposite edge instead of stopping there.
; Holds today: X (2/8/216), Y (2/8/208).

; --- Runtime character selection (MSU-1 streaming), see the plan at
; temporal-swinging-hartmanis.md. Last cell any core/*.pasm file defines is
; OamSetSprite_Hi = $7E53AF; main.pasm's own Anim_FrameIndex..Player_Y run
; $7E53B0-$7E53B5 -- new cells start at $7E53B6, verified collision-free.
Msu1Present = $7E0330   ; .db -- named alias for scpu_boot's existing MSU-1
                          ; success flag (was a bare address there; set to
                          ; 1/0 by the S-MSU1 presence check, unchanged)

CharSelect_Index       = $7E53B6   ; .db -- current roster slot, 0..RosterCount-1
CharSelect_RosterCount = $7E53B7   ; .db -- from file header byte 0x09, read every load
CharSelect_Loaded      = $7E53B8   ; .db -- 0 while a (re)load is in progress or MSU/slot
                                     ;        is unusable; gates Anim_Play (Phase 3)
Anim_IdleFrameCount   = $7E53B9   ; .db
Anim_WalkFrameCount   = $7E53BA   ; .db
Anim_AttackFrameCount = $7E53BB   ; .db
Anim_IdleDelay        = $7E53BC   ; .db
Anim_WalkDelay        = $7E53BD   ; .db
Anim_AttackDelay      = $7E53BE   ; .db
; 24-bit (lo16+hi8) MSU byte offsets of this character's idle/walk/attack
; frame data, computed once per load from the directory record's data_offset
; -- see Anim_LoadCharacter. 24-bit, not 16-bit: a real multi-character
; roster pushes data_offset past 65536 well before 8 slots fill (confirmed
; in Phase 1 -- a single ~70KB character does it), and idle_frame_count*768
; alone can exceed 16 bits for large frame counts, so every add here uses
; explicit adc-with-carry-propagation, never a bare 16-bit add.
Anim_IdleMsuBaseLo   = $7E53BF   ; .dw
Anim_IdleMsuBaseHi   = $7E53C1   ; .db
Anim_WalkMsuBaseLo   = $7E53C2   ; .dw
Anim_WalkMsuBaseHi   = $7E53C4   ; .db
Anim_AttackMsuBaseLo = $7E53C5   ; .dw
Anim_AttackMsuBaseHi = $7E53C7   ; .db

; Hand-picked fixed offsets inside WramBuffer (core/allocate_wram.pasm,
; $7E2000-$7E4FFF, 12KB) -- deliberately NOT routed through
; Core_Wram_Allocate (zero call sites anywhere in this codebase today; same
; untested-code-in-a-new-critical-path risk this project avoids elsewhere,
; e.g. Core_Math_Mul). Safe as long as nothing else starts using the
; allocator later; if that ever happens these must move to an allocated
; block instead of silently colliding.
AnimFrameStaging   = $7E2000   ; 768B -- one streamed frame, pre-DMA
AnimPaletteStaging = $7E2300   ; 32B  -- one streamed palette
AnimHeaderStaging  = $7E2320   ; 16B  -- raw directory/file-header record,
                                 ;        before parsing into the cells above

; Picks idle/walk/attack and dispatches to whichever per-animation advance/
; DMA-enqueue routine is currently selected. Reads Input_press/Input_trigger
; fresh off Core_Input_Poll, which scpu_main_loop already calls earlier in
; the same iteration. Only the high byte of each 16-bit word is read: per
; core/input.pasm's documented $4218 bit layout (B Y Sel Start U D L R |
; A X L R 0 0 0 0), Right is bit8 and Left is bit9 (bits 0/1 of the high
; byte), and Y is bit14 (bit6 of the high byte) -- so an 8-bit read of that
; one byte is enough in each case, no 16-bit accumulator needed here.
;
; Attack takes priority over dpad movement and, once started, latches
; until the non-looping attack animation finishes on its own
; (Anim_Play_Attack reverts Anim_Selected to 0 itself -- see its header
; comment): checked first, and if already attacking, skips straight to
; dispatch via `brl` without re-reading input at all -- a plain `beq`/`bra`
; can't reach Anim_Play__dispatch from here (too far, matching every other
; "too far for an 8-bit bne" spot in this file that already uses brl), and
; deliberately using an explicit brl rather than tuning a short branch's
; range keeps this immune to the exact class of silent-drift bug that bit
; the abandoned TAD-gap attempt above.
;
; Caller must be in .a16/.i16 (scpu_main_loop's convention after Core_Oam_
; Play returns) -- this routine exits in the same state, matching that
; convention, rather than saving/restoring via php/plp like Core_Dma_Enqueue
; does internally.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4 note --
                             ; confirmed by raw-byte inspection: without this nop, JSR Anim_Play
                             ; landed 1 byte early, on the previous routine's trailing RTS, and
                             ; Anim_Play's body never ran)
Anim_Play:
    sep #$20
.a8
    ; Live character reselect: Select button, edge-triggered (Input_trigger,
    ; not Input_press, per core/input.pasm's $4218 layout comment "B Y Sel
    ; Start U D L R | A X L R 0000" -- Select is bit13 overall = bit5 of the
    ; high byte) so holding it doesn't re-trigger every frame, same
    ; convention as the Y-button attack trigger below. Checked before the
    ; CharSelect_Loaded gate so a slot that failed to load (e.g. MSU absent,
    ; or this slot's data invalid) can still be retried via a different
    ; slot rather than getting stuck.
    lda.l Input_trigger+1
    and #$20
    beq Anim_Play__no_reselect
    lda.l CharSelect_Index
    inc a
    cmp.l CharSelect_RosterCount
    bcc Anim_Play__reselect_ok
    lda #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__reselect_ok:
    sta.l CharSelect_Index
    jsr Anim_LoadCharacter        ; sets/restores its own widths, see its header
    sep #$20
.a8
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__no_reselect:
    ; Nothing loaded (MSU-1 absent, or the current slot's data is invalid --
    ; see Anim_LoadCharacter) -- skip the whole dispatch below rather than
    ; streaming from a zeroed/garbage MSU base every tick.
    lda.l CharSelect_Loaded
    bne Anim_Play__loaded
    rep #$31
.a16
.i16
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__loaded:
    ; Reached via the `bne` above, which jumps AROUND the `rep #$31`/.a16/
    ; .i16 a few lines up -- so M is still 1 (8-bit) here at runtime, but
    ; Poppy's linear (non-control-flow-aware) width tracker has already
    ; "seen" that rep textually and would otherwise mis-size the next
    ; immediate (cmp #2) as a 3-byte 16-bit form the real 8-bit CPU only
    ; half-consumes, leaving a stray byte to be mis-decoded as a BRK --
    ; exact same bug and same fix as Anim_LoadCharacter__msu_ok (poppy bug
    ; #10; confirmed here the same way, via Mesen2's trace disassembler
    ; showing a phantom `BRK #$D0` right after a 2-byte `CMP #$02`). This
    ; sep is a harmless no-op at runtime but re-syncs Poppy's tracker.
    sep #$20
.a8
    lda.l Anim_Selected
    cmp #2
    bne Anim_Play__check_attack_trigger
    brl Anim_Play__dispatch     ; already attacking -- ignore input, let it finish
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__check_attack_trigger:
    lda.l Input_trigger+1
    and #ANIM_ATTACK_BUTTON_MASK
    beq Anim_Play__no_attack_trigger
    lda #2
    sta.l Anim_Selected
    lda #$FF
    sta.l Anim_FrameIndex
    lda #1
    sta.l Anim_TickCounter
    brl Anim_Play__dispatch
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__no_attack_trigger:
    lda.l Input_press+1
    and #$03
    beq Anim_Play__want_idle
    lda #1
    bra Anim_Play__want_got
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__want_idle:
    lda #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__want_got:
    cmp.l Anim_Selected
    beq Anim_Play__dispatch
    sta.l Anim_Selected
    ; Switching animations: reset to frame -1 (wraps to 0 on the forced
    ; advance below, via 8-bit inc a) and force an immediate advance this
    ; same call, rather than waiting up to a full *_FRAME_DELAY ticks to
    ; show the new animation. Unlike the boot-time cosmetic pop (handoff.md,
    ; "What's NOT done yet"), this is new code with no prior verified
    ; behavior to preserve, so there's no reason to carry the same
    ; frame-skips-0 quirk into it.
    lda #$FF
    sta.l Anim_FrameIndex
    lda #1
    sta.l Anim_TickCounter
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__dispatch:
    jsr Anim_UpdateFacing
    ; Anim_UpdateFacing exits in .a16/.i16 (its own external convention,
    ; matching Anim_Play's) -- but everything below here was written
    ; assuming .a8 (inherited from Anim_Play's own top). Re-assert it
    ; explicitly rather than relying on whatever state happened to precede
    ; this call; omitting this turned `lda.l Anim_Selected` into a 16-bit
    ; read spanning Anim_Selected+Anim_FacingLeft, and `cmp #2`/`cmp #1`
    ; into 16-bit compares that silently stopped matching -- confirmed by
    ; Mesen: attack triggered once then never re-dispatched, Anim_FrameIndex
    ; free-ran 0-5 like idle while Anim_Selected stayed stuck at 2 in WRAM.
    sep #$20
.a8
    lda.l Anim_Selected
    cmp #2
    beq Anim_Play__attack
    cmp #1
    beq Anim_Play__walk
    jsr Anim_Play_Idle
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__walk:
    jsr Anim_Play_Walk
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__attack:
    jsr Anim_Play_Attack
    rts

; Checks currently-held dpad Left/Right (Input_press, not Input_trigger --
; facing should track the held direction continuously, not just its first
; press) and, if it differs from Anim_FacingLeft, DMAs the matching
; precomputed tilemap block over the active 4x6 BG2 region (6 rows of 4
; tile entries) and updates Anim_FacingLeft. Neither direction held ->
; keep the last facing (matches how real games hold facing through
; idle/attack). Called once per Anim_Play invocation, regardless of which
; animation is active -- facing is independent of Anim_Selected. Exits in
; .a16/.i16, same convention as its caller.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_UpdateFacing:
    sep #$20
.a8
    lda.l Input_press+1
    and #$03
    bne Anim_UpdateFacing__have_input
    brl Anim_UpdateFacing__done   ; neither held -- keep current facing (too far for an 8-bit beq from here)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_UpdateFacing__have_input:
    and #$02                       ; bit9 (Left) of the word = bit1 of this byte
    beq Anim_UpdateFacing__want_right
    lda #1
    bra Anim_UpdateFacing__want_got
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_UpdateFacing__want_right:
    lda #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_UpdateFacing__want_got:
    cmp.l Anim_FacingLeft
    bne Anim_UpdateFacing__facing_changed
    brl Anim_UpdateFacing__done   ; too far for an 8-bit beq from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_UpdateFacing__facing_changed:
    sta.l Anim_FacingLeft
    cmp #0
    beq Anim_UpdateFacing__to_right
    brl Anim_UpdateFacing__to_left
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_UpdateFacing__to_right:
    rep #$20
.a16
    lda #ANIM_TILEMAP_ROW0_BYTE_ADDR
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_ROW_BYTES
    sta.l DmaRequest_Length
    lda #ANIM_TILEMAP_RIGHT_BASE
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_RIGHT_BASE + ANIM_TILEMAP_ROW_BYTES
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_RIGHT_BASE + ANIM_TILEMAP_ROW_BYTES*2
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_RIGHT_BASE + ANIM_TILEMAP_ROW_BYTES*3
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_RIGHT_BASE + ANIM_TILEMAP_ROW_BYTES*4
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_RIGHT_BASE + ANIM_TILEMAP_ROW_BYTES*5
    jsr Anim_EnqueueTilemapRow
    brl Anim_UpdateFacing__done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_UpdateFacing__to_left:
    rep #$20
.a16
    lda #ANIM_TILEMAP_ROW0_BYTE_ADDR
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_ROW_BYTES
    sta.l DmaRequest_Length
    lda #ANIM_TILEMAP_LEFT_BASE
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_LEFT_BASE + ANIM_TILEMAP_ROW_BYTES
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_LEFT_BASE + ANIM_TILEMAP_ROW_BYTES*2
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_LEFT_BASE + ANIM_TILEMAP_ROW_BYTES*3
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_LEFT_BASE + ANIM_TILEMAP_ROW_BYTES*4
    jsr Anim_EnqueueTilemapRow
    lda.l DmaRequest_TargetAddr
    clc
    adc #ANIM_TILEMAP_ROW_STRIDE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_TILEMAP_LEFT_BASE + ANIM_TILEMAP_ROW_BYTES*5
    jsr Anim_EnqueueTilemapRow
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_UpdateFacing__done:
    rep #$31
.a16
.i16
    rts

; Shared tail for Anim_UpdateFacing's 12 row-transfer sites above: caller
; sets DmaRequest_TargetAddr/Length (Length is constant across all of them,
; set once), passes the row's source address in the (16-bit) accumulator.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_EnqueueTilemapRow:
    sta.l DmaRequest_SourceAddrLow
    sep #$20
.a8
    lda #0
    sta.l DmaRequest_SourceBank   ; both tilemap blobs live in bank 0
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsr Core_Dma_Enqueue
    rts

; Advances the loaded character's idle animation by one tick per call and,
; on frame-change, streams the new frame from the MSU-1 roster into VRAM via
; Msu1_LoadFrame -- see that routine's header for the streaming mechanism.
; Frame count/delay/MSU base now come from WRAM (Anim_IdleFrameCount/Delay/
; Anim_IdleMsuBaseLo/Hi, populated by Anim_LoadCharacter), not compile-time
; constants -- this replaced the old per-frame-index unrolled dispatch chain
; (a "no data table, no indexed ROM read" workaround for the frames' old
; ROM-.incbin storage), since streaming's source is a runtime WRAM value,
; not a ROM label, so that workaround no longer applies. Only called while
; Anim_Selected == 0 (see Anim_Play above); exits in .a16/.i16, same
; convention as Anim_Play.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_Play_Idle:
    sep #$20
.a8
    lda.l Anim_TickCounter
    dec a
    sta.l Anim_TickCounter
    beq Anim_Play_Idle__advance
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__advance:

    lda.l Anim_IdleDelay
    sta.l Anim_TickCounter

    lda.l Anim_FrameIndex
    inc a
    sta.l Anim_FrameIndex
    cmp.l Anim_IdleFrameCount
    bcc Anim_Play_Idle__frame_ok
    lda #0
    sta.l Anim_FrameIndex        ; wrap (manifest loop=1)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__frame_ok:
    ; Copy this animation's 24-bit MSU base into AnimHeaderStaging+0/1/2 for
    ; Msu1_LoadFrame (see that routine's header for why this scratch reuse
    ; is safe), then stream frame_index.
    rep #$31
.a16
.i16
    lda.l Anim_IdleMsuBaseLo
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda.l Anim_IdleMsuBaseHi
    sta.l AnimHeaderStaging+2
    lda.l Anim_FrameIndex
    jsr Msu1_LoadFrame
    rts

; Same structure as Anim_Play_Idle above, using Anim_WalkFrameCount/Delay/
; MsuBase. Only called while Anim_Selected == 1 (see Anim_Play above).
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_Play_Walk:
    sep #$20
.a8
    lda.l Anim_TickCounter
    dec a
    sta.l Anim_TickCounter
    beq Anim_Play_Walk__advance
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__advance:

    lda.l Anim_WalkDelay
    sta.l Anim_TickCounter

    lda.l Anim_FrameIndex
    inc a
    sta.l Anim_FrameIndex
    cmp.l Anim_WalkFrameCount
    bcc Anim_Play_Walk__frame_ok
    lda #0
    sta.l Anim_FrameIndex        ; wrap (manifest loop=1)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__frame_ok:
    rep #$31
.a16
.i16
    lda.l Anim_WalkMsuBaseLo
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda.l Anim_WalkMsuBaseHi
    sta.l AnimHeaderStaging+2
    lda.l Anim_FrameIndex
    jsr Msu1_LoadFrame
    rts

; Same structure as Anim_Play_Idle/Walk above, using Anim_AttackFrameCount/
; Delay/MsuBase. Only called while Anim_Selected == 2 (see Anim_Play above).
; Non-looping (manifest loop=0): on reaching the last frame, reverts
; Anim_Selected to 0 (idle) and forces an immediate frame-0 idle render next
; call -- same "frame -1 forces immediate advance" trick Anim_Play's
; top-level selection-change path uses -- rather than wrapping back to
; frame 0 of the attack cycle.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_Play_Attack:
    sep #$20
.a8
    lda.l Anim_TickCounter
    dec a
    sta.l Anim_TickCounter
    beq Anim_Play_Attack__advance
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__advance:

    lda.l Anim_FrameIndex
    inc a
    cmp.l Anim_AttackFrameCount
    bcc Anim_Play_Attack__frame_ok
    ; Animation finished -- revert to idle instead of wrapping.
    lda #0
    sta.l Anim_Selected
    lda #$FF
    sta.l Anim_FrameIndex
    lda #1
    sta.l Anim_TickCounter
    brl Anim_Done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__frame_ok:
    sta.l Anim_FrameIndex
    lda.l Anim_AttackDelay
    sta.l Anim_TickCounter
    rep #$31
.a16
.i16
    lda.l Anim_AttackMsuBaseLo
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda.l Anim_AttackMsuBaseHi
    sta.l AnimHeaderStaging+2
    lda.l Anim_FrameIndex
    jsr Msu1_LoadFrame
    rts

; Msu1_LoadFrame -- streams one 768-byte animation frame from the MSU-1
; data port into AnimFrameStaging and enqueues a WRAM($7E)-sourced VRAM DMA
; blit of it (Phase 0 validated a WRAM-sourced VRAM DMA end-to-end before
; this was written), replacing the old Anim_CommitFrame's ROM-.incbin-
; sourced role. Entry: A (any width; low byte used, per the same "no caller
; convention assumed" pattern as Anim_LoadCharacter) = frame_index
; (0-based); caller must have already copied this animation's 24-bit MSU
; base offset into AnimHeaderStaging+0 (.dw, lo16) / +2 (.db, hi8).
; AnimHeaderStaging is otherwise unused during Anim_Play -- only
; Anim_LoadCharacter touches it, and only at (re)load time -- so reusing it
; here as scratch (both for the caller-supplied base above and for this
; routine's own +8..+15 working bytes below) is safe, same reuse pattern
; Anim_LoadCharacter's own walk_base/attack_base computation already uses.
; Computes base + frame_index*768 into AnimHeaderStaging+8 (.dw)/+10 (.db)
; via the same n*768 = ((n<<1)+n)<<8 shift-add idiom Anim_LoadCharacter
; uses (product's low byte is always 0), using +12..+15 as further scratch
; for the multiply itself -- deliberately not factored into its own
; sub-routine shared with Anim_LoadCharacter: the two call sites' base
; storage differs (WRAM cell pairs there, this fixed scratch pair here) and
; duplicating ~20 bytes of shift-add here is cheaper and less bug-prone
; than a generic parameterized version. Exits in .a16/.i16, matching
; Anim_CommitFrame's old contract -- every Anim_Play_* caller just `rts`
; immediately after this returns.
;
; php/sei at entry, plp before the final width-reassert/rts: unlike
; Anim_LoadCharacter's boot-time seek+read loops (which run before NMITIMEN
; is ever turned on, so can't be interrupted), this runs from Anim_Play
; during real gameplay with NMI active every frame -- and nmi_handler
; (`jsr Core_Nmi_Play` / `rti`) does NOT save/restore A/X/Y. Confirmed by
; direct observation: without this protection, an NMI landing mid-routine
; (most dangerously during the 768-byte read loop below, which carries the
; byte count in X across many iterations) clobbers A/X/Y out from under
; this routine and corrupts whatever WRAM it writes next -- reproduced in
; Mesen2 as Anim_Selected/Anim_FrameIndex/Anim_TickCounter taking on
; garbage values unrelated to any real animation state. `php`/`sei` here
; (not a bare `sei`/`cli` pair) matches Core_Dma_Enqueue's own established
; convention so this nests safely if ever called from an already-`sei`'d
; context; `plp` restores the caller's original interrupt-enable state, but
; also clobbers M/X back to whatever they were at entry (irrelevant to
; program correctness here, but not this routine's own .a16/.i16 exit
; contract) -- hence the explicit `rep #$31`/.a16/.i16 re-assert
; immediately after `plp`, not relying on `plp` alone for the exit state.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Msu1_LoadFrame:
    php
    sei
    rep #$31
.a16
.i16
    and #$00FF                  ; zero-extend frame_index
    sta.l AnimHeaderStaging+12  ; scratch = n
    asl a
    clc
    adc.l AnimHeaderStaging+12  ; a = n*3
    sta.l AnimHeaderStaging+14  ; scratch16 = n*3

    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12  ; product_lo low byte = 0
    lda.l AnimHeaderStaging+14  ; (n*3)'s low byte
    sta.l AnimHeaderStaging+13  ; product_lo high byte
                                  ; product_hi = (n*3)'s high byte, +15

    rep #$31
.a16
.i16
    lda.l AnimHeaderStaging+0   ; base lo16
    clc
    adc.l AnimHeaderStaging+12  ; + product_lo16
    sta.l AnimHeaderStaging+8   ; offset lo16
    sep #$20
.a8
    lda.l AnimHeaderStaging+2   ; base hi8
    adc.l AnimHeaderStaging+15  ; + product_hi + carry
    sta.l AnimHeaderStaging+10  ; offset hi8

    ; --- seek MSU-1 to the 24-bit offset (AnimHeaderStaging+8/9/10) ---
    lda.l AnimHeaderStaging+8
    sta $2000
    lda.l AnimHeaderStaging+9
    sta $2001
    lda.l AnimHeaderStaging+10
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Msu1_LoadFrame__busy:
    lda $2000
    bmi Msu1_LoadFrame__busy

    ; --- stream ANIM_FRAME_BYTES (768) bytes into AnimFrameStaging ---
    rep #$31
.a16
.i16
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Msu1_LoadFrame__read:
    sep #$20
.a8
    lda $2001
    sta.l AnimFrameStaging,x
    rep #$31
.a16
.i16
    inx
    cpx #ANIM_FRAME_BYTES
    bcc Msu1_LoadFrame__read

    ; --- enqueue WRAM($7E)->VRAM DMA of the streamed frame ---
    lda #AnimFrameStaging
    sta.l DmaRequest_SourceAddrLow
    lda #ANIM_VRAM_DEST_BYTE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_FRAME_BYTES
    sta.l DmaRequest_Length

    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags

    rep #$31
.a16
.i16
    jsr Core_Dma_Enqueue
    plp
    rep #$31
.a16
.i16
    rts

; Shared "nothing changed this call" tail for Anim_Play_Idle/Walk/Attack
; above -- reached via `brl` (too far for an 8-bit bne from any of them).
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_Done:
    rep #$31
.a16
.i16
    rts

; ============================================================================
; TestSprite_Init -- one-time real-OAM bring-up: a 16x16 solid-color test
; sprite, proving the OAM/OBJ rendering path end-to-end (actual hardware
; sprite via OBSEL/OAM, not a BG2 tile window like Ralf's idle/walk/attack
; animations). Not a player entity -- no input, no movement, just visibility.
; Called once from scpu_boot, right after Core_Oam_Init, still under forced
; blank (same window the raw BG1/BG2 VRAM writes earlier in scpu_boot use).
;
; Tile data is generated here, not `.incbin`'d -- a uniform solid color only
; needs plane0 set (see below), so there's no separate data blob to place.
;
; Upgraded from 8x8 to a real 16x16 sprite (nonzero "size" hi-table bit) as a
; focused follow-up to the session that rewrote core/oam.pasm's
; Core_Oam_TransformHiOam -- that rewrite was verified only via a synthetic
; WRAM injection test, never through an actual shipped sprite. This is that
; end-to-end proof: sprite 0's Oam_ExpandedHi byte is set to $02 (size bit
; set, X-high clear) below, so Core_Oam_Play's per-frame call into
; Core_Oam_TransformHiOam packs a real nonzero hi-table bit for the first
; time in the shipped ROM (previously only Core_Oam_TransformHiOam's own
; synthetic test ever exercised a nonzero bit).
;
; A 16x16 OBJ is hardware-composed from four 8x8 tiles automatically fetched
; from the OAM entry's base tile index N, N+1, N+$10, N+$11 (tile numbers
; are row-major in a 16-tile-wide sheet, so +1 moves right, +$10 moves down
; one tile row) -- NOT four separate OAM entries. Base tile index stays 0 in
; the OAM entry below; the four tiles' pixel data are written to VRAM words
; $4000/$4010/$4100/$4110 (OBJ base $4000 + tile_index*16 words/tile) by
; four calls to TestSprite_WriteSolidTile.
;
; OBJ tile base: Core_Oam_Init sets Nmi_ObjSel so OBSEL's base field is 2
; (-> VRAM word $4000, see its comment for the real, Mesen2-source-verified
; bit layout -- the OLD comment/value here was flat wrong, found in the
; session that first brought this sprite up) and size mode 0 (8x8 small /
; 16x16 large -- this sprite now uses the large half of that pair via its
; hi-table size bit). Tile data written below directly at $4000-relative
; word addresses, no wrap-address guessing needed since they're all already
; in VRAM's valid 15-bit range.
;
; IMPORTANT, easy to trip over later: this routine only writes sprite 0
; ONCE, at boot -- it is TestSprite_PlayFrame (below TestSprite_WriteSolidTile,
; called every frame from scpu_main_loop before Player_PlayFrame and
; Core_Oam_Play) that keeps sprite 0 alive going forward. That's not optional
; decoration: Core_Nmi_Play wipes the *shadow* Oam_Buffer/Oam_ExpandedHi back
; to "every sprite hidden" after every successful upload (see
; Core_Oam_ClearAll and oam.pasm's Core_Oam_Play header), but leaves real
; hardware OAM itself untouched. So the instant anything else calls
; Core_Oam_Play with a nonzero Oam_CurrentSlot -- which Player_PlayFrame's
; own Core_Oam_SetSprite call does, every frame -- that DMA will overwrite
; sprite 0's slot with the shadow's cleared state (Y=$F0, size bit back to 0)
; unless sprite 0's entry gets re-written into the shadow buffer first.
; TestSprite_PlayFrame re-asserts sprite 0's identical literal values (X=120,
; Y=100, tile=0, attr=$30, hi=$02) every frame for exactly this reason --
; don't remove it while only meaning to touch sprite 1 (now Player_PlayFrame).
; ============================================================================
    ; workaround: Poppy label address off-by-one (see poppy bug #4) -- padded
    ; wider than 1 nop; this project's usual single-nop guard was measured
    ; insufficient here after an unrelated edit elsewhere in the file shifted
    ; cumulative address-estimation drift (raw-byte-verify, don't assume).
    nop
    nop
    nop
    nop
TestSprite_Init:
    rep #$20
.a16
    lda #$4000                ; tile 0 (top-left quadrant), OBJ base
    sta $2116
    jsr TestSprite_WriteSolidTile
    lda #$4010                ; tile 1 (top-right quadrant): base + 1*16 words
    sta $2116
    jsr TestSprite_WriteSolidTile
    lda #$4100                ; tile $10 (bottom-left quadrant): base + 16*16 words
    sta $2116
    jsr TestSprite_WriteSolidTile
    lda #$4110                ; tile $11 (bottom-right quadrant): base + 17*16 words
    sta $2116
    jsr TestSprite_WriteSolidTile

    ; --- OBJ palette: CGRAM color 128 (pixel value 0, unused/transparent,
    ; left black) + color 129 (pixel value 1, bright red: R=31 G=0 B=0) ---
    sep #$20
.a8
    lda #$80
    sta $2121                ; CGRAM address = color 128 (OBJ palette 0)
    lda #0
    sta $2122                 ; color 128 low byte
    sta $2122                 ; color 128 high byte
    lda #$1F
    sta $2122                 ; color 129 low byte ($001F = pure red)
    lda #0
    sta $2122                 ; color 129 high byte

    ; --- OAM entry 0: X=120, Y=100, tile=0 (OBJ base), attr = priority 3 /
    ; palette 0. One 8-bit store per field (not a 16-bit store spanning two
    ; fields) -- avoids clobbering sprite 1's byte the way
    ; Core_Oam_ClearAll's paired stores deliberately do (that pattern relies
    ; on sprite 1 being off-screen/don't-care; this single-sprite init has
    ; no such guarantee once slot 1 is used by something else later). Hi-
    ; table size bit is set explicitly below (see the header comment above)
    ; rather than left at Core_Oam_ClearAll's zeroed default. ---
    lda #120
    sta.l Oam_Buffer          ; sprite 0 X-low
    lda #100
    sta.l Oam_Buffer+1        ; sprite 0 Y
    lda #0
    sta.l Oam_Buffer+2        ; sprite 0 base tile index (OBJ base + 0); hardware
                               ; auto-fetches +1/+$10/+$11 for the other 3 quadrants
    lda #$30                  ; priority 3, palette 0, name table 0, no flip
    sta.l Oam_Buffer+3

    ; Sprite 0's hi-table byte: bit1 (size) = 1 selects the "large" half of
    ; OBSEL's (8x8,16x16) size pair set by Core_Oam_Init; bit0 (X-high) stays
    ; 0 since X=120 fits in the low table's 8 bits. Packed into real hardware
    ; OAM2 format by Core_Oam_Play's call into Core_Oam_TransformHiOam.
    lda #$02
    sta.l Oam_ExpandedHi      ; sprite 0's hi-table byte

    rep #$31
.a16
    lda #4                    ; one sprite written -> cursor = 4 bytes
    sta.l Oam_CurrentSlot
    rts

; Writes the 32-byte solid-color-index-1 tile pattern to whatever VRAM
; address is already latched in $2116 (word-increment-on-$2119 mode, set
; once earlier in scpu_boot via $2115=$80 and never changed since). SNES
; 4bpp tile format: 8 words of interleaved plane0/plane1 (one word per
; pixel row), then 8 words of interleaved plane2/plane3. Solid color index
; 1 (binary 0001) needs only plane0 set -- word = $00FF (low byte/plane0 =
; $FF, high byte/plane1 = $00) for the first 8 words, $0000 for the last 8.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
    nop
    nop
    nop
TestSprite_WriteSolidTile:
    rep #$31
.a16
.i16
    ldx #8
    lda #$00FF
    nop
TestSprite_WriteSolidTile__plane01:
    sta $2118
    dex
    bne TestSprite_WriteSolidTile__plane01

    ldx #8
    lda #$0000
    nop
TestSprite_WriteSolidTile__plane23:
    sta $2118
    dex
    bne TestSprite_WriteSolidTile__plane23
    rts

; Sole per-frame writer for sprite 0 (the static test sprite), called once/
; frame from scpu_main_loop, immediately before Player_PlayFrame and
; Core_Oam_Play. Because Core_Nmi_Play wipes the ENTIRE OAM shadow back to
; "all hidden" after every successful upload (see Core_Oam_ClearAll and
; TestSprite_Init's own header comment above), the instant anything makes a
; second Core_Oam_Play call happen with a nonzero cursor -- which
; Player_PlayFrame's own Core_Oam_SetSprite call does, every frame -- sprite
; 0's slot would get stomped with the shadow's cleared state unless it's
; re-written here too. Forces Oam_CurrentSlot to 0 up front rather than
; trusting its leftover value, making this routine idempotent regardless of
; Core_Nmi_Play/ClearAll timing (its very first call happens before any NMI
; has run ClearAll, so the cursor is still 4 from TestSprite_Init otherwise).
;
; MUST run before Player_PlayFrame every frame: Player_PlayFrame does not
; reset Oam_CurrentSlot itself -- it relies on this routine having already
; zeroed it and advanced it 0 -> 4 via the Core_Oam_SetSprite call below, so
; Player_PlayFrame's own Core_Oam_SetSprite call lands in slot 1. Must be
; called in .a16/.i16 and returns the same way, matching scpu_main_loop's
; convention.
    nop
    nop
    nop
    nop
TestSprite_PlayFrame:
    rep #$31
.a16
    lda #0
    sta Oam_CurrentSlot

    ; --- sprite 0: re-assert TestSprite_Init's original static values ---
    sep #$20
.a8
    lda #120
    sta.l OamSetSprite_X
    lda #100
    sta.l OamSetSprite_Y
    lda #0
    sta.l OamSetSprite_Tile
    lda #$30
    sta.l OamSetSprite_Attr
    lda #$02
    sta.l OamSetSprite_Hi
    rep #$31
.a16
    jsr Core_Oam_SetSprite        ; slot 0, cursor -> 4
    rts

; Sole per-frame writer for sprite 1 (the dpad-driven player square), called
; once/frame from scpu_main_loop right after TestSprite_PlayFrame and before
; Core_Oam_Play. Reuses the same solid-red 16x16 tile (OBJ base tile 0)
; TestSprite_Init already wrote -- no new VRAM/CGRAM data needed. Moves on
; both axes while the dpad is held -- X on Left/Right, Y on Up/Down -- each
; independently clamped at the screen edges.
;
; Depends on TestSprite_PlayFrame having already run this frame: this
; routine does NOT reset Oam_CurrentSlot itself, relying on
; TestSprite_PlayFrame's zero + Core_Oam_SetSprite call having already
; advanced the cursor to 4, so this routine's own Core_Oam_SetSprite call
; lands in slot 1. Must be called in .a16/.i16 and returns the same way,
; matching scpu_main_loop's convention.
;
; workaround: Poppy label address off-by-one (see poppy bug #4 / poppy bug
; #5's more general form -- this is a `jsr` target, not a branch target, so
; it isn't the exact documented case, but the same estimation-vs-emit drift
; still applies here) -- raw-byte-verified this session: without this
; padding, the label resolved 1 byte early and landed on
; TestSprite_PlayFrame's preceding `rts` opcode instead of this routine's
; real first instruction, so every `jsr Player_PlayFrame` immediately hit
; that stray `rts` and returned without running the body (Player_X/Y and
; Oam_CurrentSlot never advanced past slot 0 -- confirmed both in Mesen2 and
; via a raw hex dump of the assembled bytes at this address).
    nop
    nop
    nop
    nop
Player_PlayFrame:
    ; --- X: held-dpad Left/Right movement. Reads Input_press+1 using the
    ; exact same bit-check convention as Anim_UpdateFacing (see that
    ; routine, above) -- and MUST resolve Left+Right-held-together the same
    ; way Anim_UpdateFacing does (Left wins), or sprite 1 could move right
    ; on a frame where Ralf's facing flips left off the same read of
    ; Input_press. Unsigned cmp/bcc/bcs on purpose -- PLAYER_MAX_X
    ; (216) has bit7 set, so a signed bmi/bpl branch would misfire near the
    ; boundary. Clamped, not bounced: holding a direction into the wall
    ; just stops moving, no direction-flip state needed anymore (that's
    ; why TestSprite2_DirLeft is gone -- see WRAM decl above, now reused for
    ; Player_Y). Wrap-safety invariant for this clamp documented next
    ; to PLAYER_SPEED above; the Y block below has its own identical
    ; block mirrored right after this one, with its own independent read of
    ; Input_press+1 (deliberately not threaded through this block's
    ; accumulator state across its three-way branch). ---
    sep #$20
.a8
    lda.l Input_press+1
    and #$03
    beq Player_PlayFrame__hold
    lda.l Input_press+1
    and #$02                       ; bit9 (Left) of the word = bit1 of this byte -- Left wins
    beq Player_PlayFrame__right
    bra Player_PlayFrame__left
    nop
Player_PlayFrame__right:
    lda.l Player_X
    clc
    adc #PLAYER_SPEED
    cmp #PLAYER_MAX_X + 1
    bcc Player_PlayFrame__store_x
    lda #PLAYER_MAX_X
    bra Player_PlayFrame__store_x
    nop
Player_PlayFrame__left:
    lda.l Player_X
    sec
    sbc #PLAYER_SPEED
    cmp #PLAYER_MIN_X
    bcs Player_PlayFrame__store_x
    lda #PLAYER_MIN_X
    bra Player_PlayFrame__store_x
    nop
Player_PlayFrame__hold:
    lda.l Player_X
    nop
Player_PlayFrame__store_x:
    sta.l Player_X
    sta.l OamSetSprite_X

    ; --- Y: held-dpad Up/Down movement, mirroring the X block above
    ; exactly in structure. Independent read of Input_press+1 (not
    ; threaded through the X block's accumulator/branches -- see WRAM decl
    ; comment above for why). Per core/input.pasm's documented $4218 bit
    ; layout, Down is bit10 of the word and Up is bit11 -- bits 2/3 of this
    ; byte. Up wins when both held, same "higher bit wins" convention as
    ; X's Left-over-Right (bit3 > bit2, matching bit1 > bit0). Up decreases
    ; Y (sbc) and Down increases Y (adc) -- opposite of X's Left/Right-to-
    ; sbc/adc mapping, since Y grows downward on screen. Unsigned cmp/bcc/
    ; bcs and the same wrap-safety invariant as X apply here too (see the
    ; PLAYER_SPEED comment above). ---
    lda.l Input_press+1
    and #$0C
    beq Player_PlayFrame__hold_y
    lda.l Input_press+1
    and #$08                       ; bit11 (Up) of the word = bit3 of this byte -- Up wins
    beq Player_PlayFrame__down
    bra Player_PlayFrame__up
    nop
Player_PlayFrame__down:
    lda.l Player_Y
    clc
    adc #PLAYER_SPEED
    cmp #PLAYER_MAX_Y + 1
    bcc Player_PlayFrame__store_y
    lda #PLAYER_MAX_Y
    bra Player_PlayFrame__store_y
    nop
Player_PlayFrame__up:
    lda.l Player_Y
    sec
    sbc #PLAYER_SPEED
    cmp #PLAYER_MIN_Y
    bcs Player_PlayFrame__store_y
    lda #PLAYER_MIN_Y
    bra Player_PlayFrame__store_y
    nop
Player_PlayFrame__hold_y:
    lda.l Player_Y
    nop
Player_PlayFrame__store_y:
    sta.l Player_Y
    sta.l OamSetSprite_Y
    lda #0
    sta.l OamSetSprite_Tile
    lda #$30
    sta.l OamSetSprite_Attr
    lda #$02
    sta.l OamSetSprite_Hi
    rep #$31
.a16
    jsr Core_Oam_SetSprite        ; slot 1, cursor -> 8
    rts

; ============================================================================
; Anim_LoadCharacter -- boot-time and live Select-button character (re)load
; from the runtime MSU-1 roster (see the plan at
; temporal-swinging-hartmanis.md). Called with CharSelect_Index already set
; to the desired roster slot. Placed here, ahead of any large ROM data blob
; in this window -- an earlier attempt to place a similar routine after a
; large .incbin produced real "Branch target out of range" errors from
; Poppy at every branch in that routine, confirming (empirically, not just
; by re-reading the existing comment) that large data ahead of branching
; code perturbs Poppy's branch-range estimation in this build; see
; poppy_assembler_bugs.md for the original report of this class of bug.
;
; Phase 2 step 1 did only the file-header/directory-record seek+read+parse
; and the 24-bit idle/walk/attack MSU base-offset computation. Step 2 (this
; version) adds palette streaming + the CGRAM DMA enqueue at the end, and
; sets CharSelect_Loaded=1 there on success (0 still means "MSU-1 absent or
; this slot's data is invalid" -- see the zero-idle-frame-count bail below
; -- not "load still in progress"; there's no async phase here, the whole
; routine runs to completion or bails before touching CharSelect_Loaded).
;
; This routine's own first seek+read, called from scpu_boot right after
; audio track-select, is also the real (not improvised-probe) test of
; whether MSU-1 track-select writes ($2004-$2007) disturb a later data seek
; ($2000-$2003) -- two earlier isolated probes left that genuinely
; unresolved; see the msu-track-select-seek-ordering-risk memory.
;
; No caller convention assumed on entry (sets its own widths); every known
; caller re-asserts its own widths immediately after the call, same pattern
; Anim_Play/Anim_UpdateFacing document above.
;
; The scpu_boot "hang" once suspected here was a false alarm: it was caused
; by a Mesen2 test harness pointed at the main checkout's stale ROM instead
; of this worktree's own build output (CLAUDE.md's testing snippet
; hardcodes a bare `distribution/bor.sfc` path that resolves to whichever
; checkout you happen to be in). Against the correct ROM, scpu_boot reaches
; Player_X/Y init fine and the display renders normally. See the
; boot-hang-before-player-init memory for the corrected account.
;
; FIXED (was "KNOWN REAL BUG, still open"): the header seek+read used to
; not reliably return the real file header -- root cause was never the
; MSU-1 hardware/seek mechanism at all (NMI masking and track-select
; sharing were correctly ruled out below). It was a Poppy silent miscompile
; at the Anim_LoadCharacter__msu_ok label just below: see that label's own
; comment for the full byte-level account. CharSelect_RosterCount now
; reads the real roster_count (2) every run; verified via raw ROM bytes,
; the three rom_audit tools, and Mesen2 (roster_count=2, CharSelect_Loaded
; a clean 0, OAM sprite0/sprite1 byte-exact unaffected).
;
; Isolation steps that got here (kept for the next time this class of bug
; shows up): an isolated probe running the *exact same* seek+read pattern,
; called as its own jsr both immediately after the legacy 46-byte read and
; again immediately after track-select, worked perfectly both times --
; which ruled out "any second seek is broken" and "track-select disturbs
; the data port" empirically, not just by reading Mesen2's source. That
; narrowed the bug to something specific to this routine's own code, which
; a raw hex dump of the assembled ROM (not Mesen2's disassembler) then
; pinned down directly.
; ============================================================================
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_LoadCharacter:
    ; php/sei here, plp before each of this routine's two rts below: this
    ; runs at boot (before NMITIMEN is ever enabled, so unprotected was
    ; fine there) but ALSO from Anim_Play on live Select-button reselect,
    ; during real gameplay with NMI active every frame. Its several
    ; register-carrying read loops (header/record/palette, all using X as a
    ; running byte count across many iterations) are exactly the shape that
    ; bit Msu1_LoadFrame when unprotected -- nmi_handler doesn't save/
    ; restore A/X/Y, so an NMI landing mid-loop would clobber the count and
    ; corrupt WRAM. Same fix, same convention as Msu1_LoadFrame/
    ; Core_Dma_Enqueue: plp restores the caller's original interrupt-enable
    ; state but also clobbers M/X back to entry's, hence the explicit
    ; rep #$31/.a16/.i16 re-assert after each plp, not relying on plp alone.
    php
    sei
    sep #$20
.a8
    lda.l Msu1Present
    bne Anim_LoadCharacter__msu_ok
    lda #0
    sta.l CharSelect_Loaded
    plp
    rep #$31
.a16
.i16
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_LoadCharacter__msu_ok:
    ; ROOT CAUSE FIX (confirmed via raw-byte ROM inspection, not just a
    ; hunch): reached via the `bne` above, which jumps AROUND the
    ; `rep #$31`/.a16/.i16 a few lines up -- so the CPU is still 8-bit-
    ; accumulator (M=1) here at runtime. But Poppy's `.a8`/`.a16` width
    ; tracking is purely textual/linear, not control-flow-aware: by the
    ; time it reaches this label it has already seen that `rep #$31`/.a16
    ; (even though the branch skips it at runtime), so it assembled the
    ; very next `lda #0` as a 3-byte 16-bit immediate (A9 00 00) instead of
    ; the 2-byte 8-bit form (A9 00). At runtime, with M actually still 1,
    ; the CPU only consumes the first immediate byte (A9 00) and then
    ; decodes the leftover 00 as a stray BRK, which eats the next real
    ; opcode byte (8F, the `sta.l CharSelect_Loaded` that should have run)
    ; as its signature byte.
    ;
    ; This does NOT hang or skip the seek, and it is not a generic "A gets
    ; clobbered" story either -- traced byte-for-byte against the pre-fix
    ; ROM (git tag/commit a53f0a2's assembled `main.bin`): BRK vectors
    ; through the native BRK vector ($FFE6), which `build_rom.py` points at
    ; `irq_handler` ($FF10) -- and `irq_handler` is a single bare `rti`. RTI
    ; pulls P and PC straight back off the stack, so execution resumes
    ; exactly at the byte after the consumed 8F: `B8 53 7E` (`clv` /
    ; `eor ($7E,S),Y`), which clobbers A with a stack-relative read (no
    ; memory write), then falls straight into the four `sta $2000..$2003`
    ; seek-trigger writes a few lines below with that clobbered A --
    ; re-issuing the seek, but to a garbage address instead of offset 0,
    ; using whatever value the stack-relative EOR produced (same value for
    ; all four bytes, since nothing reloads A in between). `CharSelect_Loaded`
    ; is what's actually skipped (never reached), matching the garbage
    ; observed there pre-fix; the busy-wait poll and 16-byte read loop
    ; after this are untouched code and still execute normally against the
    ; (wrong) seeked offset, which is why boot never visibly crashed and
    ; `AnimHeaderStaging` held plausible-looking (just wrong-offset) bytes.
    ; Confirmed via a direct hex dump of the assembled ROM at this label's
    ; address plus `build_rom.py`'s vector table; see the
    ; boot-hang-before-player-init memory. This `sep #$20` is a harmless
    ; no-op at runtime (M is already 1) but re-syncs Poppy's width tracker
    ; so the `lda #0` below assembles correctly. Same root-cause class as
    ; the documented branch-skipped-macro-sizing bug, just for width-
    ; tracking instead of macro byte-counts -- watch for this anywhere a
    ; `rep`/`sep` sits on a conditionally-skipped path before a branch-
    ; target label whose own code goes straight into a width-dependent
    ; immediate without its own preceding `rep`/`sep`. (Swept every other
    ; forward-branch-over-rep/sep site in this file after finding this one:
    ; all of them -- Anim_Play_Idle/Walk/Attack's __fN dispatch,
    ; Anim_UpdateFacing__to_left/__done, Anim_LoadCharacter__slot_ok,
    ; TadPrivate_Loader_TransferData__ReturnFalse -- land on labels that
    ; either re-execute their own rep/sep before any width-dependent
    ; immediate, or have no width-dependent immediate at all. This was the
    ; only live instance.)
    sep #$20
.a8
    lda #0
    sta.l CharSelect_Loaded

    ; --- Seek to file header (offset 0), read 16 bytes, extract
    ; roster_count (byte 9) ---
    sta $2000
    sta $2001
    sta $2002
    sta $2003                 ; A is still 0 here -- triggers seek to offset 0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_LoadCharacter__header_busy:
    lda $2000
    bmi Anim_LoadCharacter__header_busy

    rep #$31
.a16
.i16
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_LoadCharacter__header_read:
    sep #$20
.a8
    lda $2001
    sta.l AnimHeaderStaging,x
    rep #$31
.a16
.i16
    inx
    cpx #$0010
    bcc Anim_LoadCharacter__header_read

    sep #$20
.a8
    lda.l AnimHeaderStaging+9
    sta.l CharSelect_RosterCount

    ; --- Seek to this slot's directory record: offset = 0x10 + (index<<4).
    ; Fits in one byte (index 0-7 -> max offset 0x80) -- no carry needed. ---
    lda.l CharSelect_Index
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$10
    sta $2000
    lda #0
    sta $2001
    sta $2002
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_LoadCharacter__record_busy:
    lda $2000
    bmi Anim_LoadCharacter__record_busy

    rep #$31
.a16
.i16
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_LoadCharacter__record_read:
    sep #$20
.a8
    lda $2001
    sta.l AnimHeaderStaging,x
    rep #$31
.a16
.i16
    inx
    cpx #$0010
    bcc Anim_LoadCharacter__record_read

    ; --- Parse record into WRAM cells ---
    sep #$20
.a8
    lda.l AnimHeaderStaging+0
    sta.l Anim_IdleFrameCount
    lda.l AnimHeaderStaging+1
    sta.l Anim_WalkFrameCount
    lda.l AnimHeaderStaging+2
    sta.l Anim_AttackFrameCount
    lda.l AnimHeaderStaging+3
    sta.l Anim_IdleDelay
    lda.l AnimHeaderStaging+4
    sta.l Anim_WalkDelay
    lda.l AnimHeaderStaging+5
    sta.l Anim_AttackDelay

    ; Packer leaves unused slots fully zeroed -- a zero idle_frame_count is
    ; a cheap free validity check (see the plan's Phase 5). Nothing to
    ; compute in that case; leave CharSelect_Loaded=0 and bail.
    lda.l Anim_IdleFrameCount
    bne Anim_LoadCharacter__slot_ok
    plp
    rep #$31
.a16
.i16
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_LoadCharacter__slot_ok:

    ; idle_base (24-bit) = data_offset (24-bit, record bytes 8,9,10) + 32
    ; (the palette). Record byte 11 (data_offset's top byte) is assumed 0 --
    ; pack_msu_roster.py's rosters stay well under 16MB.
    rep #$31
.a16
.i16
    lda.l AnimHeaderStaging+8
    clc
    adc #32
    sta.l Anim_IdleMsuBaseLo
    sep #$20
.a8
    lda.l AnimHeaderStaging+10
    adc #0                    ; carry-in only, from the 16-bit add above
    sta.l Anim_IdleMsuBaseHi

    ; --- walk_base (24-bit) = idle_base + idle_frame_count*768 ---
    ; n*768 = ((n<<1)+n) << 8 -- the <<8 means the product's low byte is
    ; always 0 and its own high byte becomes the 24-bit product's hi8, so no
    ; separate multiply routine is needed (Core_Math_Mul is deliberately
    ; unused here, see the plan -- zero prior call sites anywhere).
    ; AnimHeaderStaging+12..+15 are reserved/unused bytes of the
    ; already-parsed record, reused here as scratch.
    lda.l Anim_IdleFrameCount
    rep #$31
.a16
.i16
    and #$00FF                 ; zero-extend n into 16-bit A
    sta.l AnimHeaderStaging+12 ; scratch = n
    asl a
    clc
    adc.l AnimHeaderStaging+12 ; a = n*2 + n = n*3
    sta.l AnimHeaderStaging+14 ; scratch16 = n*3

    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12 ; product_lo low byte = 0
    lda.l AnimHeaderStaging+14 ; (n*3)'s low byte
    sta.l AnimHeaderStaging+13 ; product_lo high byte = (n*3)'s low byte
                                ; product_hi = (n*3)'s high byte, at
                                ; AnimHeaderStaging+15 -- used directly below

    rep #$31
.a16
.i16
    lda.l Anim_IdleMsuBaseLo
    clc
    adc.l AnimHeaderStaging+12
    sta.l Anim_WalkMsuBaseLo
    sep #$20
.a8
    lda.l Anim_IdleMsuBaseHi
    adc.l AnimHeaderStaging+15 ; += product_hi + carry from the 16-bit add
    sta.l Anim_WalkMsuBaseHi

    ; --- attack_base (24-bit) = walk_base + walk_frame_count*768 ---
    ; Same shift-add pattern as walk_base above.
    lda.l Anim_WalkFrameCount
    rep #$31
.a16
.i16
    and #$00FF
    sta.l AnimHeaderStaging+12
    asl a
    clc
    adc.l AnimHeaderStaging+12
    sta.l AnimHeaderStaging+14

    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12
    lda.l AnimHeaderStaging+14
    sta.l AnimHeaderStaging+13

    rep #$31
.a16
.i16
    lda.l Anim_WalkMsuBaseLo
    clc
    adc.l AnimHeaderStaging+12
    sta.l Anim_AttackMsuBaseLo
    sep #$20
.a8
    lda.l Anim_WalkMsuBaseHi
    adc.l AnimHeaderStaging+15
    sta.l Anim_AttackMsuBaseHi

    ; --- Palette (Phase 2 step 2): seek to this character's data_offset
    ; (AnimHeaderStaging+8/9/10 -- still the raw record bytes here, untouched
    ; since idle_base's own read above only computed idle_base = data_offset
    ; + 32 into separate WRAM cells, never writing back into +8/9/10) and
    ; stream the 32-byte palette (16 BGR555 colors) into AnimPaletteStaging.
    ; Same seek+busy-poll+read-loop shape as the header/record reads above,
    ; just a different length/destination. Replaces the old hardcoded
    ; 16-immediate CGRAM block scpu_boot used to have (see msu1_done). ---
    sep #$20
.a8
    lda.l AnimHeaderStaging+8
    sta $2000
    lda.l AnimHeaderStaging+9
    sta $2001
    lda.l AnimHeaderStaging+10
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_LoadCharacter__palette_busy:
    lda $2000
    bmi Anim_LoadCharacter__palette_busy

    rep #$31
.a16
.i16
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_LoadCharacter__palette_read:
    sep #$20
.a8
    lda $2001
    sta.l AnimPaletteStaging,x
    rep #$31
.a16
.i16
    inx
    cpx #$0020
    bcc Anim_LoadCharacter__palette_read

    ; --- Enqueue a queued CGRAM DMA of the streamed palette (color 0, 32
    ; bytes = 16 colors) -- queued (not direct $2122 writes) so the exact
    ; same code path works at boot (flushed synchronously right after this
    ; call via Core_Dma_ProcessQueue, see msu1_done) and at live reselect
    ; (drained normally by Core_Nmi_Play during vblank, see Anim_Play). Same
    ; DmaRequest_* field shape Anim_CommitFrame/Msu1_LoadFrame use, just
    ; DMA_TYPE_CGRAM instead of DMA_TYPE_VRAM. ---
    lda #AnimPaletteStaging
    sta.l DmaRequest_SourceAddrLow
    lda #0
    sta.l DmaRequest_TargetAddr    ; CGRAM byte address 0 = color 0
    lda #32
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_CGRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsr Core_Dma_Enqueue

    ; --- Load succeeded: mark loaded, reset to idle, and force an
    ; immediate frame-0 render (frame -1 wraps to 0 via the 8-bit inc in
    ; Anim_Play_Idle, same "force immediate advance" trick Anim_Play's own
    ; animation-switch path uses) rather than showing stale/blank VRAM for
    ; up to a full Anim_IdleDelay ticks after a (re)load. ---
    sep #$20
.a8
    lda #1
    sta.l CharSelect_Loaded
    lda #0
    sta.l Anim_Selected
    lda #$FF
    sta.l Anim_FrameIndex
    lda #1
    sta.l Anim_TickCounter

    plp
    rep #$31
.a16
.i16
    rts

; Ralf's idle/attack pixel data used to be baked here as ROM .incbin blobs
; (AnimCharIdleFrames/AnimCharAttackFrames) -- gone now that all three
; animations stream from the MSU-1 roster at runtime instead (see
; Msu1_LoadFrame and Anim_LoadCharacter). This was also where Poppy's
; "large data blob ahead of branching code perturbs branch-range
; estimation" lesson was first hit in this project (still real, still
; documented in poppy_assembler_bugs.md -- see e.g. TestSprite32x48's own
; placement-after-branches comment -- just no longer relevant to this exact
; spot since there's no blob here anymore).

; ============================================================================
; S-CPU entry (reset vector $FC00). Emulation mode on entry.
; ============================================================================
.org $FC00

scpu_boot:
    sei
    clc
    xce                     ; native mode
    rep #$30
.a16
.i16
    ldx #$1FFF
    txs

    ; --- Core utility init (random, input, dma, wram alloc; see src/core/) ---
    jsr Core_Random_Init
    jsr Core_Input_Init
    jsr Core_DmaChannel_Init
    jsr Core_Dma_Init
    jsr Core_Wram_Init
    jsr Core_Vram_Init
    jsr Core_Cgram_Init
    jsr Core_Oop_Init
    jsr Core_Screen_Init

    sep #$20
.a8

    ; --- SA-1 bringup ---
    lda #$FF
    sta $2229               ; SIWP: S-CPU IRAM writes enabled
    lda #$80
    sta $2226               ; SBWE: S-CPU BW-RAM writes enabled
    stz $2228               ; BWPA: no BW-RAM write protect
    stz $2224               ; BMAPS: S-CPU BW-RAM window $00:6000 = BW-RAM bank 0
    stz $2203               ; CRV low
    lda #$80
    sta $2204               ; CRV high -> SA-1 reset vector $8000
    lda #$20
    sta $2200               ; assert SA-1 reset (explicit edge)
    stz $2200               ; release -> SA-1 runs sa1_main

    ; --- MSU-1 Check & Data Load ---
    ; Compared against immediate byte constants, not a `symbol,x`-indexed ROM
    ; data label: that indexed form silently computed the wrong base address
    ; here (a Poppy address-estimation bug distinct from the documented
    ; symbol+N one — the referencing instruction's own computed address was a
    ; constant few bytes off, independent of where the label itself sits, so
    ; padding at the label site could not fix it). See poppy bug #4/#5 notes.
    sep #$20
.a8
    lda $2002
    cmp #$53                ; 'S'
    bne msu1_missing
    lda $2003
    cmp #$2D                ; '-'
    bne msu1_missing
    lda $2004
    cmp #$4D                ; 'M'
    bne msu1_missing
    lda $2005
    cmp #$53                ; 'S'
    bne msu1_missing
    lda $2006
    cmp #$55                ; 'U'
    bne msu1_missing
    lda $2007
    cmp #$31                ; '1'
    bne msu1_missing

    ; MSU-1 present: set data address 0 ($2000-$2003)
    stz $2000               ; addr byte 0 = 0
    stz $2001               ; addr byte 1 = 0
    stz $2002               ; addr byte 2 = 0
    stz $2003               ; addr byte 3 = 0 (triggers seek)

    ; Wait for data busy ($2000 bit 7) to clear
msu1_busy_loop:
    lda $2000
    bmi msu1_busy_loop

    ; Read 46 bytes from MSU_DATA ($2001) to WRAM $7E:0300
    ldx #$0000
    nop
msu1_read_loop:
    lda $2001               ; read byte from MSU-1 data stream
    sta.l $7E0300,x         ; store in WRAM $7E:0300
    inx
    cpx #$002E              ; 46 bytes
    bcc msu1_read_loop

    lda #$01
    sta.l $7E0330           ; MSU-1 success flag = 1

    ; --- MSU-1: start audio track 1 playback (bor-1.pcm) ---
    lda #$01
    sta $2004               ; track select low byte = 1
    stz $2005               ; track select high byte = 0 -> triggers LoadTrack
    lda #$FF
    sta $2006               ; volume = max
    lda #$03
    sta $2007               ; bit0=play, bit1=repeat

    bra msu1_done

msu1_missing:
    lda #0
    sta.l $7E0330           ; MSU-1 success flag = 0 (stz has no long addr mode; see poppy bug #2)

msu1_done:
    ; --- Runtime character selection: load roster slot 0 at boot. See
    ; Anim_LoadCharacter's header for why this call site (right after
    ; track-select) matters. ---
    lda #0
    sta.l CharSelect_Index
    jsr Anim_LoadCharacter

    ; --- Initialize TAD Audio Driver ---
    ; IMPORTANT: TAD_Init requires the SPC700 to be at IPL reset. The SNES
    ; reset already provides that condition; do not write APUIO0 here as a
    ; substitute for an SPC reset. TAD_Init itself first waits for $BBAA.
    sei
    sep #$20
.a8
    rep #$10
.i16
    jsl Tad_Init

    ; --- PPU init (forced blank) ---
    lda #$80
    sta $2100               ; INIDISP forced blank
    stz $4200               ; NMITIMEN off

    ldx #$2100
    nop
scpu_clear_ppu:
    stz $00,x
    inx
    cpx #$2140
    bne scpu_clear_ppu
    lda #$80
    sta $2100               ; keep forced blank

    lda #$01
    sta $2105               ; BGMODE = 1
    lda #$04
    sta $2107               ; BG1SC: tilemap at word $0400
    lda #$5C
    sta $2108               ; BG2SC: tilemap at word $5C00
    lda #$20
    sta $210B               ; BG12NBA: BG1 tiles $0000, BG2 tiles $2000
    stz $210C               ; BG34NBA: $0000
    lda #$03
    sta $212C               ; TM: BG1 + BG2 on main screen
    stz $212D               ; TS: nothing on subscreen
    lda #$80
    sta $420D               ; MEMSEL: FastROM

    ; --- CGRAM palette row 0 ---
    ; Was 16 hardcoded lda #imm/$2122 immediates (no ROM data table -- see
    ; poppy_assembler_bugs.md for why a standalone .dw table wasn't an
    ; option). Now streamed from the MSU-1 roster instead: Anim_LoadCharacter
    ; (called earlier, at msu1_done, right after track-select) already
    ; queued this character's palette as a DMA_TYPE_CGRAM transfer via
    ; Core_Dma_Enqueue. Flushed synchronously here (not left for the first
    ; real NMI) because forced blank is guaranteed active at this exact
    ; point (just asserted a few lines up) and nothing else is queued yet
    ; this boot -- Core_Dma_ProcessQueue itself has no NMI-context
    ; dependency (see its header), so calling it directly is safe. Live
    ; reselect (Anim_Play, Select button) reuses the exact same
    ; Anim_LoadCharacter enqueue path and lets Core_Nmi_Play drain it
    ; normally instead, since forced blank isn't guaranteed there.
    jsr Core_Dma_ProcessQueue
    rep #$20
.a16

    ; --- VRAM: word increment on $2119 write ---
    sep #$20
.a8
    lda #$80
    sta $2115

    ; --- BG1 tile 0: blank black 4bpp tile at VRAM word $0000 ---
    rep #$20
.a16
    stz $2116
    ldx #$0010
    lda #$0000
    nop
scpu_bg1_tile:
    sta $2118
    dex
    bne scpu_bg1_tile

    ; --- BG1 tilemap at word $0400: all tile 0 ---
    lda #$0400
    sta $2116
    ldx #$0400              ; 1024 entries
    lda #$0000
    nop
scpu_bg1_map:
    sta $2118
    dex
    bne scpu_bg1_map

    ; --- BG2 blank tile (index 0) at VRAM word $2000: 16 zero words ---
    ; BG12NBA ($210B) = $20 -> BG2 char base = WORD $2000. Mesen2's actual
    ; PPU implementation (SnesPpu.cpp, $210B write handler) computes
    ; ChrAddress = (value & 0x70) << 8 for BG2 -- for value=$20 that's
    ; ($20 & $70) << 8 = $2000, a WORD address used directly (tileStart =
    ; ChrAddress + tileIndex*4*bpp, itself in words). An earlier pass at
    ; this file moved the tile-data destination to word $1000 based on
    ; get_ppu_state()'s reported chrAddr=8192 -- that field reports the
    ; raw internal ChrAddress value (word units) unconverted, i.e. 8192
    ; decimal == $2000 hex, not "8192 bytes". Confirmed empirically: VRAM
    ; at byte 16384 (word $2000) held real non-blank data while our sprite
    ; sat unread at word $1000, and BG2 was rendering that stale garbage
    ; -- as tile 0 for every blank tilemap entry -- across the whole
    ; screen, which is what actually produced the full-screen noise.
    lda #$2000
    sta $2116
    ldx #$0010
    lda #$0000
    nop
scpu_bg2_blank:
    sta $2118
    dex
    bne scpu_bg2_blank

    ; --- CC-DMA canvas pump: moved out of boot into Scpu_CcdmaPump, called
    ; once per frame from scpu_main_loop right after Core_Nmi_WaitFrame
    ; (vblank tail). The boot-time one-shot pump is gone deliberately: the
    ; SA-1 now runs a PERSISTENT recomposite loop (sa1_loop, $8000+) that
    ; re-arms CC-DMA for every fresh canvas and waits for the S-CPU to
    ; consume it, so the pump must be re-runnable every frame -- one 32-
    ; byte tile per frame, clearing SIC $2202 bit 5 (CharConvIrqFlag)
    ; once all 48 tiles of both 4x6 windows are in VRAM, releasing the
    ; SA-1 to recomposite. A boot-time pump would also deadlock the new
    ; loop: it clears nothing, and the SA-1's first wait would hang on a
    ; flag only the per-frame pump consumes. The first main-loop frame
    ; simply pumps the canvas sa1_main armed at boot (flag set at boot).

    ; --- BG2 tilemap at word $5C00: two 4x6 sprite windows (rest blank) ---
    ; Entries (ty<6, tx<8): window A (tx<4) = tile ty*4+tx+1; window B
    ; (tx>=4) = tile ty*4+tx+21 -- +20 = the 24 tiles window A occupies
    ; (tiles 0-23 at real BW-RAM $3000), so window B's tiles 24-47 at
    ; real BW-RAM $3300 are contiguous. Both windows priority 1 ($2000
    ; bit). Matches the 48-tile canvas the SA-1 recomposite loop now
    ; produces (see the blit layout comments at sa1_loop above).
    rep #$20
.a16
    lda #$5C00
    sta $2116
    ldy #$0000              ; ty = 0..31
    nop
scpu_tm_row:
    ldx #$0000              ; tx = 0..31
    nop
scpu_tm_col:
    cpy #$0006
    bcs scpu_tm_blank
    cpx #$0008
    bcs scpu_tm_blank
    tya
    asl
    asl                     ; ty * 4
    sta $00                 ; DP scratch
    txa
    clc
    adc $00
    inc a                   ; tile index + 1
    cpx #$0004
    bcc scpu_tm_win_a
    clc
    adc #$0014              ; window B: +20 tiles (see comment above)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
scpu_tm_win_a:
    ora #$2000              ; priority 1
    bra scpu_tm_write
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
scpu_tm_blank:
    lda #$0000
    nop
scpu_tm_write:
    sta $2118
    inx
    cpx #$0020
    bcc scpu_tm_col
    iny
    cpy #$0020
    bcc scpu_tm_row

    ; --- OAM + NMI shadow-register bring-up ---
    ; Core_Nmi_Init must run FIRST -- its clear loop zeroes the entire
    ; NmiShadow_Start..NmiShadow_End range, so any shadow value set before
    ; it runs (brightness, screen mode, BG registers, OBSEL) gets wiped
    ; right back out. Core_Oam_Init writes Nmi_ObjSel (also inside that
    ; shadow range), so it must run after Core_Nmi_Init too. Sync the
    ; shadow copies of what boot already configured directly above only
    ; after both inits, so the first real NMI (which commits shadows
    ; unconditionally) doesn't stomp BGMODE/BG1SC/BG12NBA/TM/brightness
    ; back to 0. Brightness is NOT written directly here -- the shadow is
    ; set and the first vblank commits it, same as upstream's own
    ; core.nmi.init/core.nmi.play split.
    jsr Core_Nmi_Init
    jsr Core_Oam_Init
    jsr TestSprite_Init

    sep #$20
.a8
    lda #$01
    sta.l Nmi_ScreenMode
    lda #$04
    sta.l Nmi_Bg1TilemapVram
    lda #$20
    sta.l Nmi_BgTilesVram12
    lda #$13             ; TM: BG1 + BG2 + OBJ ($01 | $02 | $10) on main screen
    sta.l Nmi_MainScreen
    lda #$0F
    sta.l Nmi_ScreenBrightness

    ; Character animation state (FrameIndex/Selected/TickCounter) is no
    ; longer initialized here -- Anim_LoadCharacter (already called earlier,
    ; at msu1_done) sets it as part of its own force-immediate-frame-0-
    ; render trick; re-initializing it here would stomp that with stale
    ; values (FrameIndex=0/TickCounter=ANIM_FRAME_DELAY instead of the
    ; forced-refresh $FF/1) and bring back the old boot-time cosmetic pop
    ; Anim_LoadCharacter's version was written to avoid.

    ; --- TestSprite_PlayFrame's sprite-1 dpad-movement state ---
    lda #120                        ; mid-screen; was PLAYER_MIN_X, which sits
                                     ; exactly on the left clamp
    sta.l Player_X
    lda #150                        ; matches this build's previous Y-fixed value
    sta.l Player_Y
    rep #$31
.a16

    ; --- Load Song 1 (s02_coin) ---
    ; Every Tad_* entry point is a JSL/RTL routine declared `.a8` (8-bit
    ; accumulator) -- Core_Nmi_Init above returns in 16-bit (rep #$31) mode,
    ; so a bare `jsl Tad_LoadSong` here executes the driver's 8-bit-encoded
    ; immediates and stores as 16-bit ones, corrupting both TadPrivate_nextSong
    ; (writes 2 bytes where 1 was meant) and every instruction decoded after
    ; it -- the CPU falls out of alignment with the assembled opcode stream
    ; and eventually runs off into unrelated/dead ROM. sep #$20 before every
    ; jsl into the TAD driver (matching the sep #$20 already done before
    ; jsl Tad_Init) is required, not optional.
    sep #$20
.a8
    lda #$01
    jsl Tad_LoadSong
    rep #$31
.a16
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
    nop

scpu_main_loop:
    ; Core_Nmi_WaitFrame paces this loop to real vblank (60Hz) -- without it,
    ; the S-CPU runs this body as fast as the CPU allows (thousands of times
    ; per real frame, since nothing else here blocks), and Core_Oam_Play
    ; below unconditionally enqueues a fresh 544-byte OAM DMA request on
    ; every single call. With an 8-slot queue that fills instantly and stays
    ; full, Core_Nmi_Play's per-vblank Core_Dma_ProcessQueue call ends up
    ; draining a queue full of redundant duplicate OAM uploads every frame --
    ; real hardware-DMA time that pushes its forced-blank commit bracket
    ; (INIDISP=$80 ... restore) past the end of vblank and into active
    ; display. That is what produced a black band across the top ~45
    ; scanlines of every captured screenshot, regardless of BG1/BG2 tilemap
    ; content (confirmed by disabling BG1 and by force-filling BG2's whole
    ; tilemap -- the band didn't move either way). Core_Nmi_WaitFrame
    ; already existed in core/nmi.pasm for exactly this purpose; it was
    ; simply never called from here.
    jsr Core_Nmi_WaitFrame

    ; One 32-byte CC-DMA canvas tile per frame, in the vblank tail -- the
    ; SA-1's persistent recomposite loop (sa1_loop) waits for this pump to
    ; clear its canvas-ready flag before redrawing, and the pump never
    ; reads a half-redrawn canvas (see Scpu_CcdmaPump's header comment).
    jsr Scpu_CcdmaPump

    sep #$20
.a8
    jsl Tad_Process
    ; Drain active transfers each frame (from proven SM reference)
    sep #$20
.a8
    jsl Tad_FinishLoadingData
    rep #$31
.a16
    jsr Core_Input_Poll
    jsr Core_Oop_Play
    jsr Core_Screen_Play
    jsr TestSprite_PlayFrame
    jsr Player_PlayFrame
    jsr Core_Oam_Play
    jsr Anim_Play
    bra scpu_main_loop

; NMI/IRQ pushed from $FE00/$FE10 to $FE20/$FE30, to $FF00/$FF10, then to
; $FF20/$FF30 -- scpu_boot's body keeps growing (most recently: the CC-DMA
; sprite/pump/tilemap code, then the unrolled CGRAM palette load) and each
; time it grows past whatever budget was left before these fixed .org
; addresses, Poppy silently truncates/corrupts whatever ran into them
; instead of erroring (see poppy_assembler_bugs.md). The $FF00 push was not
; enough headroom for scpu_main_loop's own growth either: once its jsr list
; grew to include jsr Anim_Play, the loop body's compiled length reached
; exactly $FF00 with zero bytes free, silently truncating `jsr Anim_Play`
; and the trailing `bra scpu_main_loop` entirely -- execution just fell
; through into nmi_handler's `jsr Core_Nmi_Play`/`rti` every iteration
; instead. Confirmed via Mesen's trace-based disassembler (Anim_Play's
; address was never marked as executed) and by live-disassembling
; scpu_main_loop's actual tail, which showed the last traced instruction
; landing exactly at $FF00. build_rom.py's NMI/IRQ vector constants were
; updated to match -- these addresses are load-bearing, keep them in sync.
; Still comfortably below $FFE4 (native vector table).
.org $FF20
nmi_handler:
    jsr Core_Nmi_Play
    rti

.org $FF30
irq_handler:
    rti
