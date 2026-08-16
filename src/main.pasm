; ============================================================================
; Beats of Rage SNES — SA-1 + CC-DMA + MSU-1 + Terrific Audio Driver (TAD)
; Poppy assembler, LoROM + SA-1 (map mode $23, cart type $35)
; ============================================================================

.snes

BW_CANVAS   = $606000   ; canvas: 128x96 4bpp linear at SA-1 BW-RAM $60:6000

; Number of concurrent blit windows the SA-1 compositor draws/recomposites
; per cycle. sa1_loop and the BG2 tilemap generator (scpu_boot) both iterate
; a REAL indexed loop over this count now, rather than N hand-unrolled code
; blocks -- see the sa1_compositor_scaling_limit project memory: unrolling
; hits an 8-bit branch-range assembler wall around N=4, and even past that
; wall a full canvas refresh costs 24*N frames (Scpu_CcdmaPump drains one
; tile/frame), so scaling N usefully needs both this loop AND a faster pump,
; not just more unrolling. This constant is the only thing that needs to
; change to retest a different N (also update Scpu_CcdmaPump's threshold
; comparison below, which stays a hand-computed literal -- see its comment).
COMPOSITOR_BLIT_COUNT = 21   ; VRAM ceiling: BG2 char base $2000, OBJ char
                              ; base $4000, 384 words/window -> 21 windows
                              ; (8064 words) fits, 22 would overrun OBJ's own
                              ; tile graphics -- see sa1_compositor_scaling_limit

; Per-frame CC-DMA canvas pump state (S-CPU side, see Scpu_CcdmaPump in the
; SA-1 region below):
CanvasChunkOffset = $7E2340   ; .dw -- next 32-byte tile offset into the
                                 ;        canvas (0..COMPOSITOR_BLIT_COUNT*768),
                                 ;        i.e. COMPOSITOR_BLIT_COUNT * 24 tiles
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

    ; --- Clear canvas: $7E00 bytes at $60:6000 (COMPOSITOR_BLIT_COUNT=21 *
    ; $600 window bytes; hand-computed literal, not an expression -- see
    ; poppy_assembler_bugs on computed-operand risk) ---
    ldx #$0000
    txa                     ; A = 0
sa1_clear:
    sta.l BW_CANVAS,x
    inx
    inx
    cpx #$7E00              ; 32256 bytes = COMPOSITOR_BLIT_COUNT(21) * $600
                             ; window bytes; hand-computed literal, not an
                             ; expression -- see poppy_assembler_bugs
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
;   1. Re-draws COMPOSITOR_BLIT_COUNT static 32x48 blits into the
;      canvas via a REAL indexed loop (sa1_loop_blits below), not N
;      hand-unrolled copies of the draw call -- an earlier session tried
;      unrolling all the way to N=21 and hit a real 65816 assembler wall
;      (8-bit branch range, ±127 bytes) around N=4, since each unrolled
;      copy grows the loop body's total byte count; a real loop's body
;      stays a fixed size regardless of N (see the
;      sa1_compositor_scaling_limit project memory). Blit i lands at
;      BW_CANVAS + i*$600, pixel-by-pixel through the $60-6F "always bitmap
;      mode" window. $600 window bytes = $300 real bytes = 24 tiles, so
;      blit i's real BW-RAM offset is $3000 + i*$300, each contiguous with
;      the previous blit's tiles: the canvas is one
;      (COMPOSITOR_BLIT_COUNT*24)-tile region. This is the "how many at
;      once" scaling step -- COMPOSITOR_BLIT_COUNT independently-drawn,
;      independently-converted software sprites sharing one recomposite
;      pass and one CC-DMA arm/pump cycle.
;   2. Re-arms CC-DMA Type 1 (the full register sequence, same as the old
;      boot code -- it is cheap and self-documenting). Conversion itself
;      stays READ-TRIGGERED: the $2236 write only re-sets CharConvDmaActive
;      and CharConvIrqFlag (SFR $2300 bit 5, readable by BOTH CPUs -- Mesen2
;      Sa1RegisterRead 0x2300), and no bytes move until the S-CPU reads the
;      $40-4F window.
;   3. Waits for the S-CPU to consume the whole canvas, then redraws. The
;      release is an I-RAM mailbox: the pump writes $AA to $3025 once the
;      whole canvas is in VRAM (Scpu_CcdmaPump) and the SA-1 polls that
;      byte. The S-CPU gates its pump on SFR bit 5 (which IT can read); the
;      SA-1 cannot read SFR $2300 at all (its own register window has no
;      0x2300 case -- Mesen2 Sa1RegisterRead -- so that read is open bus,
;      and the old SFR-wait never released), which is exactly why the
;      release must be a byte the SA-1 can see. This lock-step is the
;      proto-mailbox from spec §3.8 (RENDER_START / CANVAS_READY) in its
;      smallest form: the S-CPU's pump never reads a half-redrawn canvas,
;      so it generalizes to dynamic content without a redraw-vs-conversion
;      race.
;
; DP scratch $00/$02/$04/$06 lives in I-RAM $0000-$00FF, which CC-DMA's
; converted-tile staging ALSO writes (DDA=0 -> each converted tile lands at
; I-RAM $0000-$001F). That only happens while the S-CPU pumps (flag set,
; this loop waiting), and every DP cell here is re-initialized before each
; draw, so no stale value ever crosses a wait boundary. I-RAM $08 is the
; blit loop counter (0..COMPOSITOR_BLIT_COUNT-1), also inside the staging
; band but, like $00-$06, re-initialized every cycle before it's read. I-RAM
; $20/$21 are above that staging band: $20 = phase canary (1 = entered loop,
; 2..COMPOSITOR_BLIT_COUNT+1 = "blit i done", COMPOSITOR_BLIT_COUNT+2 =
; armed, COMPOSITOR_BLIT_COUNT+3 = wait exited), $21 = the recomposite cycle
; counter (the old `inc $3000` aliased DP $00 through the I-RAM window's &
; $7FF mapping AND got stomped by the staging every tile; $21 is outside
; both hazards).
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
    ; --- real indexed loop over COMPOSITOR_BLIT_COUNT blits, base = i*$600 ---
    stz $08                 ; loop counter i = 0
    stz $06                 ; blit base offset = 0
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
sa1_loop_blits:
    jsr sa1_draw_blit

    ; --- phase canary i+2: blit i done ---
    sep #$20
.a8
    lda $08
    clc
    adc #$02
    sta $20
    rep #$20
.a16
    lda $06
    clc
    adc #$0600
    sta $06                 ; next blit base = (i+1)*$600
    inc $08                 ; i++
    lda $08
    cmp #COMPOSITOR_BLIT_COUNT
    bcc sa1_loop_blits

    ; last blit's own phase canary (i+2 = 5 for the 4th blit, i=3) already
    ; doubles as "all blits done, about to arm" -- no separate canary write
    ; needed here, matching the original N=3 code's dual-purpose canary.

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
    lda #$17                ; phase canary N+2=23: armed, about to wait (last
    sta $20                 ; blit's own canary, N+1=22, doubled as "about to
                             ; arm" -- see comment above the CC-DMA config).
                             ; COMPOSITOR_BLIT_COUNT-dependent (armed=N+2) --
                             ; re-derive by hand if N changes.
    inc $21

    ; --- Wait for the S-CPU to consume this canvas ---
    ; Mailbox handshake (NOT the SFR): the SA-1's own read of $2300 never
    ; returns the S-CPU's SFR -- Mesen's Sa1RegisterRead has no 0x2300 case
    ; (that register belongs to CpuRegisterRead), so `lda $2300` on the
    ; SA-1 falls through to open bus, and bit 5 of that value reads stuck
    ; set here. The S-CPU can see the flag (it pumps on it), but the SA-1
    ; physically cannot, so the old SFR-wait could never release the loop.
    ; Instead: the S-CPU's pump writes $AA to I-RAM $3025 once the whole
    ; canvas is in VRAM (see Scpu_CcdmaPump), and the SA-1 polls that byte --
    ; the proto-mailbox from spec §3.8 (RENDER_START / CANVAS_READY) in its
    ; smallest form. The SA-1 clears the mailbox before redrawing, so the
    ; pump's next completion (24*COMPOSITOR_BLIT_COUNT frames later) cannot
    ; be mistaken for this one, and the pump still gates on SFR bit 5 for
    ; its own start signal.
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
sa1_wait:
    lda $3025               ; I-RAM mailbox: $AA = S-CPU has consumed canvas
    cmp #$AA
    bne sa1_wait
    stz $25                 ; acknowledge: clear the mailbox (own I-RAM
                            ; window; CIWP $FF set at boot permits it)
    lda #$07                ; phase canary 7: wait exited, loop will re-arm
    sta $20
    bra sa1_loop

; --- Draw one 32x48 blit of TestSprite32x48 into the canvas ---
; Caller (sa1_loop) sets $06 = blit base offset = i*$600 for i =
; 0..COMPOSITOR_BLIT_COUNT-1 (loop counter i lives in $08), and must be in
; .a16/.i16; exits .a16/.i16. Source data is byte-per-pixel
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
; and clears that flag (SIC $2202 bit 5) once the full
; (COMPOSITOR_BLIT_COUNT*24)-tile canvas (COMPOSITOR_BLIT_COUNT*768 bytes,
; COMPOSITOR_BLIT_COUNT 4x6 windows) is in VRAM -- releasing the SA-1 to
; recomposite the next canvas. Full refresh therefore takes
; 24*COMPOSITOR_BLIT_COUNT frames (96 for the current N=4); a one-tile-
; per-frame chunk keeps this inside the vblank tail (16 word-reads + 16
; word-writes ~= 400 cycles), which a full-canvas-at-once pump would blow
; out by an order of magnitude. NOTE: this cost scales linearly with N and
; does not improve just by fixing the assembler-wall/`.org` problems that
; block unrolling -- see the sa1_compositor_scaling_limit project memory.
; The threshold constant below (Scpu_CcdmaPump_Keep's cmp) is a hand-
; computed literal, not a COMPOSITOR_BLIT_COUNT*768 expression -- kept that
; way deliberately (see the comment at the cmp site).
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
    bne Scpu_CcdmaPump_HasWork
    brl Scpu_CcdmaPump_Done ; too far for an 8-bit beq now that the fixed
                             ; 16-word unroll below grew this routine past
                             ; the +-127 byte range -- see poppy_assembler_bugs
    nop
Scpu_CcdmaPump_HasWork:
    rep #$20
.a16
.i16
    ; PumpScratch is a FIXED 32-byte (16-word) staging buffer -- its size
    ; never scales with COMPOSITOR_BLIT_COUNT, unlike CanvasChunkOffset's own
    ; range. It was previously indexed with X (= CanvasChunkOffset, which
    ; grows across the WHOLE canvas), which swept staging writes straight
    ; through the NMI shadow block once CanvasChunkOffset exceeded
    ; $7E5000-PumpScratch ($2CBC), silently corrupting Nmi_InterruptFlags and
    ; killing NMI (only bit at large enough COMPOSITOR_BLIT_COUNT -- N=4
    ; never reached it, N=21 did, reproducibly, at CanvasChunkOffset ~$2CE0;
    ; see sa1_compositor_scaling_limit memory). A ,Y-indexed .l fix was tried
    ; next but 65816 has no long-addressing ,Y indexed mode at all (only
    ; ,X) -- Poppy silently accepted the invalid `sta.l Sym,y` and emitted a
    ; wrong/truncated encoding instead of erroring, corrupting the
    ; instruction stream. Fixed instead by fully unrolling this FIXED
    ; 16-word transfer (it never scales with N, so unrolling here doesn't
    ; reintroduce the branch-range problem the real loops elsewhere in this
    ; file were written to avoid) -- X stays dedicated to the genuinely
    ; runtime-variable BW-RAM source offset (long,X is valid), and
    ; PumpScratch's side uses compile-time `Symbol+K` immediate offsets
    ; instead of indexing at all (same proven-safe pattern as
    ; core/nmi.pasm's `Nmi_Bg1ScrollX+1`).
    lda.l CanvasChunkOffset
    tax                      ; X = BW-RAM source read offset (CanvasChunkOffset-
                             ; relative -- must sweep the real canvas position)
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
Scpu_CcdmaPump_Read:
    lda.l $403000,x         ; read+trigger-convert via S-CPU BW-RAM window ($40-4F)
    sta.l PumpScratch+0     ; stage in WRAM -- deliberately OUTSIDE the forced-
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
    lda.l $403000,x
    sta.l PumpScratch+2
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+4
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+6
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+8
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+10
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+12
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+14
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+16
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+18
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+20
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+22
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+24
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+26
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+28
    inx
    inx
    lda.l $403000,x
    sta.l PumpScratch+30

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
    ; Fully unrolled, same rationale as Scpu_CcdmaPump_Read above -- fixed
    ; 16-word transfer, no indexing needed on either side (source is a
    ; compile-time PumpScratch+K offset, dest is the fixed $2118 port), so X
    ; just holds CanvasChunkOffset untouched for the post-loop wrap check.
    lda.l CanvasChunkOffset
    tax                      ; X = CanvasChunkOffset, held UNTOUCHED across this
                             ; block (only needed below, for the next-offset/
                             ; wrap computation)
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
Scpu_CcdmaPump_Write:
    lda.l PumpScratch+0     ; WRAM reads only -- no BW-RAM access inside the
                            ; bracket, so it cannot stall on SA-1 arbitration
                            ; (bounded, ~350 cycles for the 16-word transfer)
    sta $2118               ; write to VRAM $2118/$2119
    lda.l PumpScratch+2
    sta $2118
    lda.l PumpScratch+4
    sta $2118
    lda.l PumpScratch+6
    sta $2118
    lda.l PumpScratch+8
    sta $2118
    lda.l PumpScratch+10
    sta $2118
    lda.l PumpScratch+12
    sta $2118
    lda.l PumpScratch+14
    sta $2118
    lda.l PumpScratch+16
    sta $2118
    lda.l PumpScratch+18
    sta $2118
    lda.l PumpScratch+20
    sta $2118
    lda.l PumpScratch+22
    sta $2118
    lda.l PumpScratch+24
    sta $2118
    lda.l PumpScratch+26
    sta $2118
    lda.l PumpScratch+28
    sta $2118
    lda.l PumpScratch+30
    sta $2118
    sep #$20
.a8
    lda.l Nmi_ScreenBrightness
    sta $2100               ; restore the screen brightness ($0F, set in boot)
    rep #$20
.a16
    txa                      ; A = CanvasChunkOffset (X untouched by the loop above)
    clc
    adc #$0020               ; + 32 bytes just pumped = next offset
    cmp #$3F00              ; 16128 bytes = 504 tiles (COMPOSITOR_BLIT_COUNT=21 *
                             ; 24 tiles); hand-computed literal, not a
                             ; COMPOSITOR_BLIT_COUNT*768 expression -- see
                             ; poppy_assembler_bugs on computed-operand risk.
                             ; Re-derive by hand if COMPOSITOR_BLIT_COUNT
                             ; changes (N*768, in hex).
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
TadPrivate_bytesToTransferPerFrame_Lo = $0033
TadPrivate_dataToTransfer_addr_Lo = $0036
TadPrivate_dataToTransfer_prevSpinLock_Lo = $003B
TadPrivate_dataToTransfer_size_Lo = $0039
TadPrivate_nextCommand_id_Lo = $003D
TadPrivate_nextSong_Lo = $003C
TadPrivate_previousCommand_Lo = $0035
Tad_flags_Lo = $0030

        stz.w TadPrivate_dataToTransfer_prevSpinLock_Lo

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
    stx.w TadPrivate_dataToTransfer_addr_Lo
    sta TadPrivate_dataToTransfer_bank
    sty.w TadPrivate_dataToTransfer_size_Lo

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
    ldy.w TadPrivate_dataToTransfer_addr_Lo

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

    sty.w TadPrivate_dataToTransfer_addr_Lo
    sta TadPrivate_dataToTransfer_prevSpinLock


    ldy.w TadPrivate_dataToTransfer_size_Lo
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
    stx.w Tad_flags_Lo

    ldx #TAD_DEFAULT_TRANSFER_PER_FRAME
    stx.w TadPrivate_bytesToTransferPerFrame_Lo


    lda #^(Tad_AudioDriver_Bin)
    ldx #((Tad_AudioDriver_Bin)&$ffff)
    ldy #Tad_AudioDriver_SIZE
    jsr TadPrivate_Loader_SetDataToTransfer

    lda #$ff
    sta TadPrivate_nextCommand_id
    sta Tad_sfxQueue_sfx

    stz.w TadPrivate_nextSong_Lo

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
            ldy.w TadPrivate_nextCommand_id_Lo
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
        trb.w Tad_flags_Lo

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

; Two separate Poppy miscompiles lived in the six lines below, and together they
; were the *second* Phase 7 blocker (the first was the dropped `bcc` in
; LoadAudioData at $AC00). Both come from the same root cause: Poppy sizes
; `ldx #`/`ldy #` immediates as 2 bytes during its address-estimation pass but
; emits 3 in .i16, so every label and every `*` after one of them resolves short.
;
;  1. `__anon10` resolved to $8A29 while the real `jsr` sits at $8A2A. $8A29 is
;     the high byte of `ldx #$8A23`, i.e. `$8A` = TXA. So the *success* path --
;     the one taken every time a real song loads -- fell through TXA, which
;     copies X (the data address, $8F35) into an 8-bit A. SetDataToTransfer then
;     stored $35 as the data BANK. Observed live as bank=$35 while addr=$8F35 and
;     size=341 were both correct: the giveaway was that "bank" was exactly the
;     low byte of "addr". The song transfer then read from bank $35 (ROM garbage)
;     and the SPC loader never completed it. Two nops give the early-landing
;     branch somewhere harmless to fall through from.
;
;  2. `blanksongdata = * - 1` was a ::HACK from the upstream ca65 source that
;     borrowed the third byte of `ldy #1` (a known $00) as the one-byte blank
;     song. With `*` estimated short it resolved to $8A23 -- the *$01* byte --
;     so the "blank song" was a $01, not a $00. Replaced with a real label on
;     the zero padding at the head of the audio blob: same guarantee, no
;     dependence on Poppy's estimation pass at all.
TadPrivate_Process_WaitingForLoader__LoadData:
    jsl LoadAudioData
    bcs __anon10
        ; LoadAudioData returned false
    nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
    TadPrivate_Process_WaitingForLoader__UseBlankSong:
        ; The blank song is a single zero byte.
        ldy #1
        lda #^(Tad_BlankSongByte)
        ldx #((Tad_BlankSongByte)&$ffff)
        nop                 ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
        nop
    __anon10:

    ; STACK holds next state
    ; A:X = data address
    ; Y = data size
    jsr TadPrivate_Loader_SetDataToTransfer

    ; Must set state AFTER the `LoadAudioData` call.
    ; `LoadAudioData` might call `Tad_FinishLoadingData`.
    pla
    sta TadPrivate_state

nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
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
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
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

        nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
        TadPrivate_Process_Loading__Song:
            ; TadPrivate_Process_Loading__Song data was loaded into Audio-RAM
            ; Loader has finished, audio driver is now active

            stz.w TadPrivate_previousCommand_Lo

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
    nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
    TadPrivate_Process_Loading__EndIf:
        sta TadPrivate_state

nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
TadPrivate_Process_Loading__Return:
    rtl



; JSL/RTL subroutine
.a8
.i16
; DB access lowram
    nop                     ; workaround: Poppy label address off-by-N (see poppy bug #4)
    nop
    nop
    nop
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
    nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
    nop                     ; address estimation, so every label after one drifts
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
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
Tad_QueueCommand:
    bit.w TadPrivate_nextCommand_id_Lo
    bpl Tad_QueueCommand__ReturnFalse
        ; command queue is empty
    nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
    nop                     ; address estimation, so every label after one drifts
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

nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
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
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
Tad_QueuePannedSoundEffect:
    cmp Tad_sfxQueue_sfx
    bcs Tad_QueuePannedSoundEffect__EndIf
        sta Tad_sfxQueue_sfx

        txa
        sta Tad_sfxQueue_pan

nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
Tad_QueuePannedSoundEffect__EndIf:
    rts



; IN: A = sfx_id
.a8
; I unknown
; DB access lowram
; KEEP: X, Y
    nop                     ; workaround: Poppy label address off-by-N (see poppy bug #4)
    nop
    nop
    nop
Tad_QueueSoundEffect:
    cmp Tad_sfxQueue_sfx
    bcs Tad_QueueSoundEffect__EndIf
        sta Tad_sfxQueue_sfx

        lda #TAD_CENTER_PAN
        sta Tad_sfxQueue_pan
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
Tad_QueueSoundEffect__EndIf:
    rts



; JSL/RTL subroutine
; IN: A = song_id
.a8
; I unknown
; DB access lowram
;
; Second half of the Phase 7 blocker. This label resolved TWO bytes early
; (Poppy bug #4), so `jsl Tad_LoadSong` from scpu_boot landed mid-instruction:
; the assembled bytes at the exported address read `21 60` = `AND ($60,X)`,
; which ran BEFORE the real `sta.l TadPrivate_nextSong` two bytes later. The
; stray AND clobbered the song id (A=1) to 0, so `nextSong` was stored as 0 --
; making the state machine take the blank-song path forever (observed:
; nextSong=0, size=32, addr=$8A23 pointing into this routine's own
; neighbourhood, stuck in LOADING_SONG_DATA_PLAY, S-DSP never leaving
; reset+mute). Verified by disassembling src/main.bin at the exported address,
; not inferred. Padding guards the call target so it falls through to the real
; first instruction -- re-verify the raw bytes here if surrounding code shifts.
    nop                     ; workaround: Poppy label address off-by-N (see poppy bug #4)
    nop
    nop
    nop
Tad_LoadSong:
; [assert] assert TAD__FIRST_LOADING_SONG_STATE > TadState::NULL, error
; [assert] assert TAD__FIRST_LOADING_SONG_STATE > TadState::WAITING_FOR_LOADER_COMMON, error
; [assert] assert TAD__FIRST_LOADING_SONG_STATE > TadState::WAITING_FOR_LOADER_SONG, error
; [assert] assert TAD__FIRST_LOADING_SONG_STATE > TadState::LOADING_COMMON_AUDIO_DATA, error


    sta TadPrivate_nextSong

    lda #RELOAD_COMMON_AUDIO_DATA
    trb.w Tad_flags_Lo
    beq Tad_LoadSong__SongRequested
        ; Common audio data requested
        lda #WAITING_FOR_LOADER_COMMON
        bra Tad_LoadSong__SetStateAndSwitchToLoader

; The -2 label drift documented above is uniform across this whole routine, not
; just its entry point, and the two interior labels were the ACTUAL Phase 7
; blocker (the entry-point fix above only exposed them).
;
; `beq Tad_LoadSong__SongRequested` landed on $8ABA -- the `bra` belonging to
; the common-data path two bytes earlier -- so it jumped straight to
; SetStateAndSwitchToLoader and the `cmp #TAD__FIRST_LOADING_SONG_STATE / bcc`
; guard below was DEAD CODE that never executed once. Result: every
; Tad_LoadSong call forced TadPrivate_state to WAITING_FOR_LOADER_SONG,
; including the very first one at boot while the state was still
; WAITING_FOR_LOADER_COMMON. The common audio data was therefore never
; transferred at all (traced live: state $7B -> $7C in one frame with the
; transfer queue untouched at size=0), and the SPC loader -- correctly --
; refused a song it had no common data for, so it never zeroed the spinlock
; and TadPrivate_Loader_TransferData returned false forever.
;
; SetStateAndSwitchToLoader was drifted the same 2 bytes, landing on
; `lda #WAITING_FOR_LOADER_SONG`, so the common-data path's own
; `lda #WAITING_FOR_LOADER_COMMON` was overwritten with $7C too -- i.e. this
; routine could not reach state $7B by any path.
    nop                     ; workaround: Poppy label address off-by-N (see poppy bug #4)
    nop
Tad_LoadSong__SongRequested:
    lda TadPrivate_state
    cmp #TAD__FIRST_LOADING_SONG_STATE
    bcc Tad_LoadSong__Return
        ; TadState is not NULL, WAITING_FOR_LOADER_* or LOADING_COMMON_AUDIO_DATA

        lda #WAITING_FOR_LOADER_SONG

    nop                     ; workaround: Poppy label address off-by-N (see poppy bug #4)
    nop
    Tad_LoadSong__SetStateAndSwitchToLoader:
        sta TadPrivate_state

        ; Assert it is safe to send a switch-to-loader command when the loader is waiting for a READY signal
; [assert] assert TadIO_ToDriver::SWITCH_TO_LOADER <> TadIO_Loader_Init::LOADER_READY_H, error
; [assert] assert TadIO_ToDriver::SWITCH_TO_LOADER_PORT = TadIO_Loader_Init::READY_PORT_H, error

        ; Send a *switch-to-loader* command to the audio-driver or loader
        lda #SWITCH_TO_LOADER
        sta.l SWITCH_TO_LOADER_PORT
    nop                     ; workaround: Poppy label address off-by-N (see poppy bug #4)
    nop
Tad_LoadSong__Return:
    rtl


; IN: A = song_id
; OUT: carry set if `Tad_LoadSong` was called
.a8
; I unknown
; DB access lowram
    nop                     ; workaround: Poppy label drift (bug #4). Without
    nop                     ; these the symbol lands on the tail of
                            ; Tad_LoadSong__Return's own guard and resolves onto
                            ; that routine's `rtl`. Inert today -- nothing in
                            ; this ROM calls Tad_LoadSongIfChanged, it is only
                            ; an exported TAD API -- but a caller added later
                            ; would return instantly and silently.
Tad_LoadSongIfChanged:
    cmp TadPrivate_nextSong
    beq __anon11
        jsl Tad_LoadSong
        sec
        rts
    nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
    nop                     ; address estimation, so every label after one drifts
    nop                     ; early (poppy bug #4). Guard absorbs the early landing.
    __anon11:
    clc
    rts


;; OUT: A = The song_id used in the last `Tad_LoadSong` call.
.a8
; I unknown
; DB access lowram
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
Tad_GetSong:
    ; `TadPrivate_nextSong` is only written to in `Tad_Init` and `Tad_LoadSong`.
    lda TadPrivate_nextSong
    rts


.a8
; I unknown
; DB access lowram
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
Tad_ReloadCommonAudioData:
    lda #RELOAD_COMMON_AUDIO_DATA
    tsb.w Tad_flags_Lo
    rts


.a8
; I unknown
; DB access lowram
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
Tad_SongsStartImmediately:
    lda #PLAY_SONG_IMMEDIATELY
    tsb.w Tad_flags_Lo
    rts


.a8
; I unknown
; DB access lowram
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
Tad_SongsStartPaused:
    lda #PLAY_SONG_IMMEDIATELY
    trb.w Tad_flags_Lo
    rts


.a8
; I unknown
; DB access lowram
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
Tad_GlobalVolumesResetOnSongStart:
    lda #RESET_GLOBAL_VOLUMES_ON_SONG_START
    tsb.w Tad_flags_Lo
    rts


.a8
; I unknown
; DB access lowram
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
Tad_GlobalVolumesPersist:
    lda #RESET_GLOBAL_VOLUMES_ON_SONG_START
    trb.w Tad_flags_Lo
    rts


; IN: X = new `TadPrivate_bytesToTransferPerFrame` value
; A unknown
.i16
; DB access lowram
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
Tad_SetTransferSize:
    cpx #TAD_MAX_TRANSFER_PER_FRAME
    bcc __anon12
        ldx #TAD_MAX_TRANSFER_PER_FRAME
    nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
    nop                     ; address estimation, so every label after one drifts
    nop                     ; early (poppy bug #4). Guard absorbs the early landing.
    __anon12:
    cpx #TAD_MIN_TRANSFER_PER_FRAME
    bcs __anon13
        ldx #TAD_MIN_TRANSFER_PER_FRAME
    nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
    nop                     ; address estimation, so every label after one drifts
    nop                     ; early (poppy bug #4). Guard absorbs the early landing.
    __anon13:
    stx.w TadPrivate_bytesToTransferPerFrame_Lo

    rts



; OUT: carry set if state is LOADING_*
.a8
; I unknown
; DB access lowram
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
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
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
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
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
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
nop                     ; workaround: Poppy sizes `jsl` 1 byte short during
nop                     ; address estimation, so every label after one drifts
nop                     ; early (poppy bug #4). Guard absorbs the early landing.
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
; This was the Phase 7 blocker, and it was invisible in source: the branch
; below was originally written as `bcc .valid` against a dot-prefixed local
; label `.valid:`. **Poppy silently dropped the branch instruction entirely** --
; the assembled bytes at $AC00 read `cmp #$02 / clc / rtl / rep #$30 ...` with
; no `bcc` at all (raw-byte verified in src/main.bin; the label line vanished
; too). So this callback ALWAYS took the invalid-song-id early return, leaving
; A/X/Y as whatever the caller happened to hold. TadPrivate_Loader_SetDataToTransfer
; then stored that garbage as the transfer queue (observed: addr=$8A23, size=1
; instead of the correct addr=$8F35, size=341), and TAD sat in
; LOADING_SONG_DATA_PLAY forever with the S-DSP still in reset+mute.
;
; Same family as CLAUDE.md's documented `@`-local-label rule -- this file's
; standing convention is fully-qualified global labels only, and this was the
; single place in main.pasm that violated it (verified by grep: one dot-label
; definition, one branch to it, both here).
LoadAudioData:
    cmp #N_DATA_ITEMS
    bcc LoadAudioData__valid
        clc
        rtl
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
LoadAudioData__valid:
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

    ; Convert a Tad_DataTable entry into a far address.
    ;
    ; Upstream TAD does this with the standard LoROM dance -- `ora #$8000` for
    ; the address and `bank = (offset >> 15) + AUDIO_DATA_BANK` via the
    ; cmp/rol pair -- because in a normal ca65 build the audio blob is linked
    ; to start at LoROM $8000 of its own bank, which makes a blob-relative
    ; offset and a linear ROM offset the same number.
    ;
    ; That assumption does not hold here. This project is confined to bank 0
    ; (Poppy's .bank N handling is broken), so the blob is .incbin'd at
    ; __Tad_AudioData_0 = $B02B -- mid-bank, not at a bank boundary. The
    ; upstream math therefore produced addresses $302B too low: the common
    ; audio data resolved to $8D44 and song 1 to $8F35, both of which land in
    ; the zero padding ahead of `.org $8C00`. The loader dutifully transferred
    ; 497 and 341 bytes of ZEROS into Audio-RAM, so TAD reached PLAYING with
    ; the S-DSP out of reset and full main volume, and emitted pure silence --
    ; no voice was ever keyed on because there was no song to key one from.
    ; (Verified by byte-comparing both candidate addresses against
    ; soundwork/tad/build/audio-data.bin at the same offsets.)
    ;
    ; The base to add is NOT __Tad_AudioData_0. soundwork/tad/build/audio-data.s
    ; documents the table as "PRG ROM offsets (from the start of the first Audio
    ; Data segment)", and in the ca65 layout that segment opens with the
    ; 51-byte LoadAudioData callback and only then the blob -- so a table offset
    ; is measured from 51 bytes BEFORE __Tad_AudioData_0. main.pasm pads only 43
    ; bytes ahead of the .incbin (its comment claiming "43-byte callback" is
    ; simply wrong; audio-data.s line 117 asserts the callback is 51), so the
    ; segment base here is __Tad_AudioData_0 - 51.
    ;
    ; The arithmetic pins this down with no room for interpretation:
    ;   Tad_DataTable sits at blob offset 3337 and is 8 bytes, so the data
    ;   proper starts at blob offset 3345; entry0 is $0D44 = 3396, and
    ;   3396 - 51 = 3345 exactly. The table's end entry is $108A = 4234, and
    ;   4234 - 51 = 4183 = the exact size of audio-data.bin.
    ; Using __Tad_AudioData_0 itself reads 51 bytes late and runs the last
    ; song 51 bytes past the end of the blob.
    ;
    ; The whole blob is 4183 bytes spanning $B02B-$C082 and never crosses a
    ; bank boundary, so this is a plain 16-bit add with a constant bank. If the
    ; blob ever grows past $FFFF this must carry into the bank byte again.
    lda.l Tad_DataTable,x
    clc
    adc #((__Tad_AudioData_0 - 51) & $ffff)
    sta 1,s

    sep #$20
.a8
    lda #^(__Tad_AudioData_0)

    plx
    sec
    rtl

; ============================================================================
; Audio Data Blob ($B000 = file offset $3000)
; ============================================================================
.org $B000
Tad_BlankSongByte:
    ; A guaranteed-$00 byte in bank 0, used as TAD's one-byte "blank song".
    ; This is the first of the 43 zero pad bytes below; referencing it by label
    ; (rather than the upstream `* - 1` trick) keeps the blank song correct no
    ; matter how Poppy's address-estimation pass sizes the surrounding
    ; immediates -- see TadPrivate_Process_WaitingForLoader__LoadData.
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

; Msu1_LoadFrame's 6 row-DMAs (later in this file) read from the single
; shared AnimFrameStaging buffer asynchronously (fired by
; Core_Dma_ProcessQueue at the next real vblank, not synchronously) -- so a
; second caller streaming a new frame before that vblank has happened would
; overwrite AnimFrameStaging out from under the first caller's still-pending
; DMAs. Msu1_LoadFrame sets this to 1 right after queuing its 6 rows;
; Core_Nmi_Play (core/nmi.pasm, included just below -- this is why the
; declaration has to live here, textually before that .include, rather than
; alongside AnimFrameStaging/AnimHeaderStaging further down this file) clears
; it back to 0 once Core_Dma_ProcessQueue has actually drained that vblank.
; Anim_Play_Idle/Walk/Attack check this *before* decrementing
; Anim_TickCounter (not after it reaches 0 -- see their own comments) so a
; blocked entity's countdown simply pauses for a frame instead of pinning at
; 0 and re-losing the race every frame. See plan.md Phase 0. Placed in the
; free $7E2330-$7E233F gap between AnimHeaderStaging ($7E2320-$232F) and
; CanvasChunkOffset ($7E2340) -- grep-confirmed clear before picking it.
Msu1_StreamBusy = $7E2330   ; .db -- nonzero: a stream's DMAs are still
                              ;        queued/undrained; don't start another
; StreamScroll_ColBuf/HeightTiles/ColPending/ColTargetWord (Phase 9 step 4,
; SyncScroll): declared here, textually before core/nmi.pasm's .include just
; below, for the same reason as Msu1_StreamBusy above -- Core_Nmi_Play's
; forced-blank column-write block reads/clears these. See their full-detail
; comments further down this file (near the rest of the StreamScroll_* WRAM
; block) for what each field means; this early copy exists purely so
; nmi.pasm's textually-earlier .include can see the addresses.
StreamScroll_ColBuf        = $7E255A ; 56B ($7E255A-$7E2591)
StreamScroll_HeightTiles   = $7E2592 ; .dw
StreamScroll_ColPending    = $7E2594 ; .db -- 1 iff ColBuf holds a fully
                              ;        resolved column waiting for
                              ;        Core_Nmi_Play to write it into VRAM.
                              ;        Never touched by a DMA -- VMAIN's
                              ;        32-word-stride mode (DMAP7
                              ;        2-regs-write-once + VMAIN=$81) hung the
                              ;        CPU under Mesen2 when driven from the
                              ;        DMA queue; direct CPU port writes from
                              ;        inside forced blank (the same code
                              ;        shape Bg_LoadScene_Streaming's row loop
                              ;        already uses) replace that attempt
                              ;        entirely -- see core/dma.pasm history.
StreamScroll_ColTargetWord = $7E2595 ; .dw -- VRAM word address of ColBuf
                              ;        row 0 (row N goes at +32*N words)

; Phase 10 Step 2c (plan.md 2.10): the BG3 frontpanel's own per-frame
; streaming resolver needs the SAME early-declared-before-nmi.pasm-include
; handoff shape as StreamScroll_ColBuf/ColPending/ColTargetWord immediately
; above (Core_Nmi_Play's forced-blank column-write block references these
; too) -- distinct cells, not reused, for the same reason Step 2b's
; StreamStageFp_* block exists (see that block's own header comment): BG1's
; ColBuf/ColPending/ColTargetWord are live per-frame state a second
; consumer must never alias onto. Only FP_CONTENT_ROW_COUNT (7) words, not
; StreamScroll_ColBuf's up-to-28 -- see STREAM_FP_TILEMAP_ROW_START's
; declaration (further below) for why the frontpanel only ever needs rows
; 21-27 resolved, never the whole tilemap column.
StreamScrollFp_ColBuf        = $7E2640 ; 14B ($7E2640-$7E264D), word-indexed
                              ;        by row WITHIN the 7 real rows (index 0
                              ;        = tilemap row 21), not an absolute row
StreamScrollFp_ColPending    = $7E264E ; .db
StreamScrollFp_ColTargetWord = $7E264F ; .dw -- VRAM word address of
                              ;        StreamScrollFp_ColBuf row 0 (row N
                              ;        goes at +32*N words, same single-32x32
                              ;        -map stride BG3_TILEMAP_VRAM_WORD uses)

CharacterClassId = $7E2331   ; .db -- 8-bit class id returned by Core_Oop_
                              ;        RegisterClass for the Character class
                              ;        (plan.md Phase 1a). Read only via a
                              ;        16-bit load masked with #$00ff (Core_
                              ;        Oop_Create does this internally too) --
                              ;        the byte just above it is unrelated,
                              ;        don't trust it as a high byte.
Oam_CursorResetDone = $7E2332 ; .db -- plan.md Phase 1b Step 3: per-FRAME (not
                              ;        per-instance -- deliberately a fixed
                              ;        global, not a CHAR_* DP field) flag,
                              ;        cleared once in scpu_main_loop right
                              ;        before jsr Core_Oop_Play. The first
                              ;        entity dispatched each frame sees this
                              ;        clear, resets Oam_CurrentSlot to 0 and
                              ;        sets this; every later entity that same
                              ;        frame sees it set and leaves
                              ;        Oam_CurrentSlot alone so it keeps
                              ;        writing into the next free OAM slot
                              ;        instead of stomping slot 0 again. NOT
                              ;        OopObjIndex -- that's a slot offset
                              ;        into OopObjRam, not dispatch order, and
                              ;        breaks under entity deletion/slot
                              ;        compaction (plan.md's own warning).
; Verified via plan.md Phase 0's forced two-stream collision test (Mesen2,
; 3/3 runs): call A correctly left Msu1_StreamBusy=1, call B correctly
; observed it and was blocked (never overwrote AnimFrameStaging out from
; under A's still-pending DMAs). Test hook removed after confirmation --
; see git history on this file around this comment if it needs to be
; re-run.

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
.include "core/stream_cache.pasm"
.include "core/stream_cache_fp.pasm"

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
PLAYER_MAX_X = 216         ; superseded for X by WORLD_MAX_X below (Phase 8) --
                             ; kept only as WORLD_MAX_X's derivation base and
                             ; because nothing else needs it deleted
PLAYER_MIN_Y = 8
PLAYER_MAX_Y = 208         ; 16px sprite, 224-line visible screen: 208+16=224
PLAYER_SPEED = 2           ; shared between axes
; Phase 8: world-space X clamp for a level wider than one 256px screen.
; PLAYER_MIN_X is unchanged (a left-edge render margin, independent of level
; width). The right-edge margin PLAYER_MAX_X used to give from the SCREEN's
; right edge (256 - 216 = 40px) is preserved here as a margin from the
; LEVEL's real right edge instead. Boss's real content is 336px (42 tiles --
; see out/bg_boss_level/manifest.json's content_width_tiles); hardcoded here
; rather than read from the packed bg_record because there is no general
; "current level" concept yet, matching how PLAYER_MAX_X/Y were already
; per-scene constants, not derived from anything.
WORLD_CONTENT_WIDTH = 336
WORLD_MAX_X = 296          ; WORLD_CONTENT_WIDTH - (256 - PLAYER_MAX_X)
; Runtime WRAM mirror of WORLD_MAX_X, set once at boot (Boot_SetWorldMaxX,
; right after Boot_SetPlayfieldBorder) to WORLD_MAX_X for a BG_MODE_STATIC
; level or to the real streaming level's width-derived max for BG_MODE_
; STREAMING -- same reasoning as StreamScroll's playfield-border deferral:
; without this, Character_PlayFrame's dpad-driven right clamp kept using the
; boss level's hardcoded WORLD_MAX_X even for a much wider streaming level,
; silently stopping the player (and thus the camera, which follows the
; player) at world column ~37 regardless of the real level width.
WorldMaxX = $7E2597        ; .dw
; Clamp-wrap safety invariant (both axes): SPEED <= MIN (sbc side) and
; MAX + SPEED <= 255 for 8-bit axes / <= 65535 for the 16-bit X axis (adc
; side), or the add/subtract can wrap past the clamp and teleport to the
; opposite edge instead of stopping there. Holds today: X (2/8/296, 16-bit),
; Y (2/8/208, 8-bit).

; --- plan.md Phase 3: minimal AI (SNES-BOR-Engine-Prompt.md Sec 6.2 --
; "Enemies walk toward player. When within 30 pixels, play punch
; animation. No damage system for PoC."). CHAR_INPUT_DRIVEN=2 means "seek
; toward Entity #0's position" -- Entity #0 (the player) is always the
; first object `Core_Oop_Create`d and never deleted, so its DP window is
; always at a fixed, known address: OopObjRam+0 (plan.md's own "player is
; always slot 0" shortcut, explicitly endorsed there over building a
; general entity-lookup mechanism for a single-player game). These are
; ABSOLUTE addresses (not CHAR_* DP-relative offsets) -- used from inside
; a DIFFERENT entity's own DP window to read the player's position, so
; they must NOT get `.l`/bare-DP treatment; always read via `lda.l`. ---
PlayerEntity_PosX = $7E0a00 + 4   ; Entity #0's CHAR_POS_X (low byte valid)
PlayerEntity_PosY = $7E0a00 + 6   ; Entity #0's CHAR_POS_Y (low byte valid)
ANIM_AI_ATTACK_RANGE = 30         ; pixels, per-axis (Chebyshev) -- "roughly
                                   ; 30 pixels" per the spec's own wording,
                                   ; doesn't need to be exact/circular

; --- plan.md Phase 4/5: collision + hit reaction (AABB-only, no HP/damage
; tracking, matching the spec's explicit PoC scope). Same "player is always
; slot 0, fixed DP window" shortcut as Phase 3's PlayerEntity_PosX/Y above,
; extended to every other entity's window so any entity's Character_HitApply
; can read/write the OTHER entity's position and hit-stun cell directly
; instead of building a general entity-lookup mechanism. This is
; deliberately NOT a runtime "compute base from slot number" routine --
; Character_HitApply never needs to know its OWN slot (it always runs
; inside the dispatched instance's own DP window), only the fixed target's
; address, and both directions are compile-time-known: the player (mode 1)
; always tests against slots 1/2/3, and every AI (mode 2) always tests
; against slot 0. So a fixed literal per slot, generalizing the same
; pattern Phase 4 already proved correct, is both simpler and safer than
; runtime indexed addressing (which has its own confirmed Poppy traps --
; see the `.l Symbol,y` ban). Plan.md caps this project at exactly 4
; entities (the OBJ tile-sheet budget goes up to 8, but 4 is the current
; target), so 4 hand-written literals is the actual ceiling, not a
; scalability compromise.
;
; Each entity's window starts immediately after the previous one's in
; OopObjRam (core/oop.pasm's bump allocator places objects back-to-back in
; creation order; msu1_done creates Entity #0, #1, #2, #3 in that order) --
; CHAR_ZP_LEN bytes apart. Written as literal multiples of 35 (not
; `N*CHAR_ZP_LEN`) because Poppy's constant evaluator is single-pass and
; CHAR_ZP_LEN isn't defined until further down this file (confirmed via a
; real "Cannot evaluate operand" build error when Entity1_Base first used
; the symbol) -- MUST be kept equal to CHAR_ZP_LEN's real value if that
; ever changes; `tools/rom_audit/audit_all.py` asserts this automatically.
; These are ABSOLUTE addresses, always read/written via `.l`, same caveat
; as PlayerEntity_PosX/Y above. ---
Entity1_Base    = $7E0a00 + 36        ; = $7E0a00 + 1*CHAR_ZP_LEN
Entity1_PosX    = Entity1_Base + 4    ; Entity #1's CHAR_POS_X
Entity1_PosY    = Entity1_Base + 6    ; Entity #1's CHAR_POS_Y
Entity1_HitStun = Entity1_Base + 33   ; Entity #1's CHAR_HIT_STUN
Entity1_Hp      = Entity1_Base + 35   ; Entity #1's CHAR_HP
Entity2_Base    = $7E0a00 + 72        ; = $7E0a00 + 2*CHAR_ZP_LEN
Entity2_PosX    = Entity2_Base + 4    ; Entity #2's CHAR_POS_X
Entity2_PosY    = Entity2_Base + 6    ; Entity #2's CHAR_POS_Y
Entity2_HitStun = Entity2_Base + 33   ; Entity #2's CHAR_HIT_STUN
Entity2_Hp      = Entity2_Base + 35   ; Entity #2's CHAR_HP
Entity3_Base    = $7E0a00 + 108       ; = $7E0a00 + 3*CHAR_ZP_LEN
Entity3_PosX    = Entity3_Base + 4    ; Entity #3's CHAR_POS_X
Entity3_PosY    = Entity3_Base + 6    ; Entity #3's CHAR_POS_Y
Entity3_HitStun = Entity3_Base + 33   ; Entity #3's CHAR_HIT_STUN
Entity3_Hp      = Entity3_Base + 35   ; Entity #3's CHAR_HP
PlayerEntity_HitStun = $7E0a00 + 33   ; Entity #0's CHAR_HIT_STUN
PlayerEntity_Hp      = $7E0a00 + 35   ; Entity #0's CHAR_HP

; Both entities' sprites are 32x64 (OBSEL mode 6 "large" size, see
; Character_PlayFrame's OamSetSprite_Hi comment) -- the AABB hitbox is just
; that same full sprite box; no separate, narrower attack-hitbox data
; exists (matches the spec's "AABB-only, no pixel-perfect" PoC scope). A
; hit registers as soon as the attacker's CHAR_SELECTED reaches 2 (attack)
; while already overlapping, not on some later "active" sub-frame of the
; swing -- there's no per-frame hit-window data to key off of, and at
; ANIM_AI_ATTACK_RANGE=30 the two 32px-wide boxes already overlap by 2px
; the instant the AI's seek logic decides to attack, so this simplification
; doesn't need a separate "walk closer" phase to still look reasonable.
CHAR_HITBOX_W = 32
CHAR_HITBOX_H = 64
CHAR_HIT_STUN_FRAMES = 24   ; ~0.4s @ 60Hz -- long enough to read as a
                              ; deliberate freeze, short enough not to feel
                              ; like a stall

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

; --- plan.md Phase 1b: core/oop.pasm CharacterEntity's per-instance
; direct-page window field layout. These are NOT fixed bank-$7E addresses
; like the Anim_*/Player_* cells above -- they're small byte OFFSETS from
; whatever the D register currently holds, which Core_Oop_Create/Play
; switch (via phd/tcd) to point at this specific object's own window
; inside OopObjRam ($7E0a00-$7E15ff, low-16 $0a00-$15ff, entirely within
; the $0000-$1FFF bank-0/bank-$7E WRAM mirror -- direct-page addressing
; from within a dispatched Init/Play call therefore resolves to the right
; physical byte). Confirmed via raw-byte inspection that a bare reference
; to one of these small constants assembles as 65816 Direct Page mode
; (2-byte opcode+offset, e.g. `A5 0B` for `lda CHAR_SELECTED`), not
; Absolute -- never add `.l` or `.w` to any of these, that would force
; absolute/long addressing at whatever tiny bank-0 address the offset
; number happens to equal, not this object's window.
;
; core/oop.pasm reserves offsets 0-3 (OOP_SELF_HEADER_SIZE) for its own
; self-handle header -- fields start at 4. Converted incrementally
; (handoff.md tracks progress): Step 1 (this commit) moves the Anim_*
; fields below; CHAR_POS_X/Y, CHAR_PALETTE_SLOT, CHAR_TILE_COLUMN,
; CHAR_INPUT_DRIVEN, CHAR_ROSTER_INDEX are declared now (stable offsets
; for later steps) but not yet used by any code -- Player_X/Y and the
; hardcoded palette/tile-column/single-entity assumptions stay as they
; are until their own steps.
CHAR_POS_X          = 4    ; .dw -- world X (Step 2; widened Phase 8)
CHAR_POS_X_HI       = 5    ; high byte of CHAR_POS_X, as its OWN named
                             ; constant rather than a `CHAR_POS_X+1` DP
                             ; expression -- Poppy's address-estimation pass
                             ; and its real encoding pass disagreed on that
                             ; expression's instruction length in a `stz`
                             ; (found via check_label_drift.py: every label
                             ; after CharacterEntity_Init's spawn-position
                             ; zeroing drifted). Matches this project's
                             ; standing rule (see math.pasm's header) to
                             ; avoid `Symbol+N` arithmetic feeding an
                             ; instruction operand for a bank-$7E-adjacent
                             ; symbol -- generalized here to a DP offset too.
CHAR_POS_Y           = 6    ; .dw -- screen Y (Step 2)
CHAR_FACING_LEFT    = 8    ; .db
CHAR_FRAME_INDEX    = 9    ; .db
CHAR_TICK_COUNTER   = 10   ; .db
CHAR_SELECTED       = 11   ; .db -- 0=idle/1=walk/2=attack, mirrors old Anim_Selected
CHAR_ROSTER_INDEX   = 12   ; .db -- which bor.msu slot this instance loaded (Step 4)
CHAR_PALETTE_SLOT   = 13   ; .db -- 0-7, this instance's OBJ palette (Step 3)
CHAR_TILE_COLUMN    = 14   ; .db -- 0-3, this instance's OBJ tile-block-0 column slice (Step 3)
CHAR_INPUT_DRIVEN   = 15   ; .db -- nonzero = read dpad (Step 2/3)
CHAR_IDLE_FCOUNT    = 16   ; .db
CHAR_WALK_FCOUNT    = 17   ; .db
CHAR_ATTACK_FCOUNT  = 18   ; .db
CHAR_IDLE_DELAY     = 19   ; .db
CHAR_WALK_DELAY     = 20   ; .db
CHAR_ATTACK_DELAY   = 21   ; .db
CHAR_IDLE_BASE_LO   = 22   ; .dw
CHAR_IDLE_BASE_HI   = 24   ; .db
CHAR_WALK_BASE_LO   = 25   ; .dw
CHAR_WALK_BASE_HI   = 27   ; .db
CHAR_ATTACK_BASE_LO = 28   ; .dw
CHAR_ATTACK_BASE_HI = 30   ; .db
CHAR_TILE_BYTE_OFFSET = 31 ; .dw -- CHAR_TILE_COLUMN*128, recomputed at the
                            ; top of every Msu1_LoadFrame call (Step 3); not
                            ; loaded directly by name elsewhere, just scratch
; --- plan.md Phase 4: minimal collision + hit reaction. CHAR_HIT_STUN is a
; simple frames-remaining countdown; nonzero forces this entity to idle and
; suppresses its movement (see Anim_Play/Character_PlayFrame's stun checks)
; -- the visible "hit reaction," reusing the idle animation rather than
; adding new art (no hit/fall frame data exists in the MSU roster format;
; plan.md explicitly allows reusing an existing state). CHAR_HIT_APPLIED
; is a same-attack-cycle latch so a multi-frame attack animation registers
; at most one hit instead of one every frame it stays overlapping; see
; Character_HitApply. ---
CHAR_HIT_STUN       = 33   ; .db -- frames remaining in hit-reaction freeze, 0 = not stunned
CHAR_HIT_APPLIED    = 34   ; .db -- 1 once this attack cycle already landed a hit
; Phase 6: CHAR_HP exists so the BG3 HUD has something real to display. It is
; deliberately NOT a damage system -- nothing dies, respawns, or changes
; behaviour at 0; the value just clamps there. Decremented in the same place
; CHAR_HIT_STUN is stamped, so it tracks landed hits exactly.
CHAR_HP             = 35   ; .db -- 0..CHAR_HP_MAX, drives the HUD bars
CHAR_ZP_LEN         = 36   ; total -- pass as OopRegStaging_ZpLen

CHAR_HP_MAX         = 64   ; = HUD_BAR_TILES(8) * 8 px, so one pixel of bar per
                            ; HP; keep in sync with make_hud_tiles.py's max_hp
CHAR_HP_PER_HIT     = 4    ; 16 hits to empty a bar

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

; --- Phase 6 BG section staging (Bg_LoadScene). Only the 16-byte header and
; the 16-byte BG directory record are staged in WRAM; the ~16KB of actual
; pixel/tilemap data is streamed straight from the MSU-1 data port into the
; PPU and never lands in WRAM at all. ---
BgHeaderStaging    = $7E2330   ; 16B  -- bor.msu file header (bg_count at +10,
                                 ;        bg_directory_offset at +12..15)
BgRecordStaging    = $7E2340   ; 32B  -- one BG directory record (v4, was 20B/16B)
; No word-count cell: the streaming loops count DOWN in X instead. An earlier
; version kept the count in WRAM and ended each loop with `cpx.l BgWordCount`
; -- but CPX has NO long addressing mode on the 65816, and Poppy assembles it
; silently anyway (same class as the documented `stz.l` and `.l,y` traps),
; emitting an encoding that desynced the instruction stream and scribbled over
; CGRAM. Counting down needs no memory operand at all.

; --- Phase 6 VRAM map (see Bg_LoadScene's header for the full picture) ---
BG1_TILES_VRAM_WORD   = $0000  ; <=512 4bpp tiles, i.e. up to word $1FFF
BG1_TILEMAP_VRAM_WORD = $6000  ; 32x32 map; only the top 32x28 is written
BG1_TILEMAP_WORDS     = 896    ; 32 * 28 entries actually streamed (narrow map,
                                 ; bg_record width_tiles == 32)
BG1_TILEMAP_WORDS_WIDE = 2048  ; two concatenated 32x32 pages (bg_record
                                 ; width_tiles == 64): page A = words $6000-$63FF
                                 ; (cols 0-31, all 32 rows -- rows 28-31 are
                                 ; zero-padded even though never displayed,
                                 ; because SNES 64x32 BG addressing requires
                                 ; page B to start exactly 1024 words after page
                                 ; A, not after 28 rows), page B = $6400-$67FF
                                 ; (cols 32-63). This is why BG3's tilemap had to
                                 ; move to $6800 first -- see BG3_TILEMAP_VRAM_WORD.
BG3_TILES_VRAM_WORD   = $5000  ; 2bpp HUD tiles
BG3_TILEMAP_VRAM_WORD = $6800  ; 32x32 map. Was $6400 (Phase 6); moved here in
                                 ; Phase 8 (plan.md 2.7) to free $6400-$67FF so
                                 ; BG1's tilemap can grow to a real 64x32 map
                                 ; ($6000-$67FF) for horizontal scrolling.
                                 ; Bg_LoadScene now reads bg_record width_tiles
                                 ; (32 or 64) and picks the narrow/wide tilemap
                                 ; DMA loop and BG1SC value at runtime -- see
                                 ; Bg_LoadScene__tilemap_wide.
BG3_TILEMAP_WORDS     = 1024

; --- Phase 10 (plan.md 2.10) BG3 frontpanel foreground layer ---
FP_TILES_VRAM_WORD = $5100     ; 2bpp streaming-cache tiles: 256 slots * 8
                                 ; words/tile (see STREAM_FP_CACHE_USABLE) =
                                 ; 2048 words, $5100-$58FF. HUD's 12 tiles
                                 ; occupy $5000-$505F (see BG3_TILES_VRAM_WORD)
                                 ; -- $5100 leaves headroom, ends well short of
                                 ; BG1's tilemap at $6000.
FP_TILE_INDEX_BASE = 32        ; (FP_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) / 8.
                                 ; The tilemap word's character-number field is
                                 ; PPU-relative to BG3_TILES_VRAM_WORD (its CHR
                                 ; base), NOT to FP_TILES_VRAM_WORD -- a bare
                                 ; cache slot number written as the character
                                 ; field silently points 32 tiles too early
                                 ; (into/before HUD's own 12 tiles), rendering
                                 ; garbage VRAM as pixel data. Add this to the
                                 ; slot before OR'ing in palette/priority bits.
; STREAM_FP_TILEMAP_ROW_START -- NOT used by Bg_LoadSceneFp_Streaming itself
; (that boot loader writes tilemap row = RowIndex directly across all 28
; rows -- see its write-target comment for why adding this as an offset
; there was a real bug). Measured directly from out/fp_stage1a/tilemap.bin
; via decode_tilemap_column_major, and confirmed to hold across the FULL
; 192-column level width, not just the boot-time window: rows 0-20 are
; 100% blank (tile id 0) at every column, rows 21-27 hold the fence -- BOR's
; frontpanel is a bottom rail, not a full-height overlay. Never visibly
; collides with HUD's own BG3 tilemap rows 0-3 (HUD_STAGING_BYTES /
; Hud_Play) -- see Bg_LoadSceneFp_Streaming's write-target comment for why
; the boot-time overwrite of those rows is harmless.
;
; Step 2c's runtime resolver (Core_StreamScrollFp_*, further below) DOES use
; this in real address arithmetic: since it's true for every column, not
; just the boot window, the resolver only ever needs to seek/read/write
; these 7 rows per newly-exposed column, never the other 21 -- a real,
; load-bearing simplification versus mirroring BG1's full-height resolver,
; not just an optimization.
STREAM_FP_TILEMAP_ROW_START = 21
FP_CONTENT_ROW_COUNT = 7               ; 28 - STREAM_FP_TILEMAP_ROW_START

; --- dedicated scratch for Bg_LoadSceneFp_Streaming, NOT shared with
; StreamStage_* (used for BG1's own boot loader above). Reuse was tried
; first and was a real bug, caught by direct VRAM verification (see
; plan.md 2.10 Step 2b): StreamStage_SeekLo/TilesBaseLo etc. are not
; boot-only -- Core_StreamScroll_SeekColumn (further below) reuses them
; every frame for BG1's own runtime scroll repairs, and assumes
; TilesBaseLo/Hi holds BG1's tiles_offset for the entire level.
; Bg_LoadSceneFp_Streaming running after BG1's own boot loader and
; overwriting those cells with FP's values silently broke BG1's live
; scrolling from that point on. ---
StreamStageFp_SeekLo      = $7E25C0   ; .dw
StreamStageFp_SeekHi      = $7E25C2   ; .db
StreamStageFp_ColStrideLo = $7E25C3   ; .dw
StreamStageFp_TilesBaseLo = $7E25C5   ; .dw
StreamStageFp_TilesBaseHi = $7E25C7   ; .db
StreamStageFp_TileOffLo   = $7E25C8   ; .dw
StreamStageFp_TileOffHi   = $7E25CA   ; .db
StreamStageFp_SeekTmpLo   = $7E25CB   ; .dw
StreamStageFp_SeekTmpHi   = $7E25CD   ; .db
StreamStageFp_ColIndex    = $7E25CE   ; .dw
StreamStageFp_RowIndex    = $7E25D0   ; .dw
StreamStageFp_TileId      = $7E25D2   ; .dw
StreamStageFp_Attr        = $7E25D4   ; .db
StreamStageFp_Slot        = $7E25D5   ; .dw
StreamStageFp_Word        = $7E25D7   ; .dw
StreamStageFp_Entries     = $7E25E0   ; 84B ($7E25E0-$7E2633)

; Step 2c's runtime resolver reuses StreamStageFp_ColStrideLo/TilesBaseLo/
; TilesBaseHi/TileOffLo/TileOffHi/SeekLo/SeekHi/SeekTmpLo/SeekTmpHi/TileId/
; Attr/Slot/Word/Entries above as its own scratch, exactly the way BG1's own
; Core_StreamScroll_SeekColumn/ResolveRows already reuse Bg_LoadScene_
; Streaming's StreamStage_* cells (see that comment block, further below,
; for the precedent) -- safe because the boot loader and the resolver never
; run concurrently, and ColStrideLo/TilesBaseLo/TilesBaseHi are written once
; at boot and never touched again by anything. The ONE value the boot loop
; does NOT preserve is the tilemap's own base MSU offset: StreamStageFp_
; SeekLo/Hi hold it only transiently before Bg_LoadSceneFp_Streaming's
; column loop repeatedly advances them past it (mirrors StreamScroll_
; TilemapOffLo/Hi's own reason for existing, further below) -- so a
; dedicated preserved copy is captured once at boot into StreamScrollFp_
; TilemapOffLo/Hi below, right alongside the mutable copy, before that loop
; ever runs.
; --- Phase 10 Step 2c (plan.md 2.10): BG3 frontpanel per-frame streaming
; resolver state. Tracks the SAME world camera (Screen_PosX) as BG1's own
; StreamScroll_* below, against the separate FP cache/tilemap instead.
; Unlike BG1, BG3's tilemap is a single 32x32 map (BG3_TILEMAP_VRAM_WORD) --
; no 64-column two-page ring -- and that size exactly equals
; STREAM_STAGE_VIEWPORT_COLS (32). That leaves NO headroom for a BG1-style
; prefetch margin: the desired window here is always exactly the 32
; onscreen columns (StreamScrollFp_StagedLo..StagedLo+31), not viewport+
; prefetch. Widening it would let vram_col (world_col & 31) alias two
; different world columns onto the same physical tilemap slot and silently
; overwrite a still-visible one -- the same class of bug BG1's own
; PickColumn__repair clamp exists to prevent, just with a smaller ring here.
StreamScrollFp_TilemapOffLo = $7E2634  ; .dw -- tilemap_offset low16,
                              ;        preserved copy (see the comment
                              ;        above StreamStageFp_Entries)
StreamScrollFp_TilemapOffHi = $7E2636  ; .db -- tilemap_offset byte 2
STREAM_SCROLLFP_BUDGET_MAX = 2         ; Deliberately far more conservative
; than STREAM_SCROLL_BUDGET_MAX=6 -- see that constant's own header comment
; for the confirmed-real risk (suspected NMI-reentrancy corruption at higher
; per-call synchronous MSU seek/read work) AND plan.md 2.10's stop-condition
; about a second per-frame streaming consumer competing for the same 8-slot
; DMA queue BG1's own resolver already uses up to 6 of. Start low, verify
; Nmi_FrameCounter still advances under a forced-collision stress test
; (both layers missing the same frame) before ever raising -- do not tune
; this by feel.
StreamScrollFp_Enabled     = $7E2651   ; .db
StreamScrollFp_StagedLo    = $7E2652   ; .dw
StreamScrollFp_StagedHi    = $7E2654   ; .dw
StreamScrollFp_PendCol     = $7E2656   ; .dw -- $FFFF = nothing pending
StreamScrollFp_PendTile    = $7E2658   ; .dw -- 0..FP_CONTENT_ROW_COUNT-1,
                              ;        an index into the 7 real rows, NOT an
                              ;        absolute BG3 tilemap row (add
                              ;        STREAM_FP_TILEMAP_ROW_START to get
                              ;        that back)
StreamScrollFp_ProdHi       = $7E265A  ; .dw -- Core_Math_Mul's high product
                              ;        word (world_col * ColStrideLo)
StreamScrollFp_CameraCol    = $7E265C  ; .dw -- Screen_PosX >> 3
StreamScrollFp_Budget       = $7E265E  ; .db
StreamScrollFp_FetchBufSel  = $7E265F  ; .db -- which of the
                              ;        STREAM_SCROLLFP_BUDGET_MAX
                              ;        StreamScrollFp_TileBufN slots this
                              ;        call's miss should use (see
                              ;        StreamScroll_FetchBufSel's own
                              ;        declaration comment for why this
                              ;        can't be a single shared buffer)
; DesiredLo/DesiredHi/RepairCur mirror BG1's own PickColumn fields exactly
; (same names, same algorithm) -- see Core_StreamScrollFp_PickColumn's own
; header comment for the one real difference: no prefetch margin, so
; DesiredHi-DesiredLo is always exactly STREAM_STAGE_VIEWPORT_COLS-1 (never
; wider), which is also why FP's ResolveRows commit step doesn't need BG1's
; "trim the opposite edge to fit the physical ring" logic -- the window can
; never grow past the ring's own 32-column capacity here.
StreamScrollFp_DesiredLo    = $7E2660  ; .dw
StreamScrollFp_DesiredHi    = $7E2662  ; .dw
StreamScrollFp_RepairCur    = $7E2664  ; .dw
; StreamScrollFp_TileBufN lives in bank $7F, clear of both BG1's own
; StreamScroll_TileBufN ($7F9000-$7F90FF) and the FP cache's own tables
; ($7FA000+, see stream_cache_fp.pasm) -- same "constant source bank, slot =
; base + FetchBufSel*16" shape as BG1's, but 16-byte (2bpp) slots, not 32.
StreamScrollFp_TileBufN     = $7F9100  ; STREAM_SCROLLFP_BUDGET_MAX*16 bytes
                              ;        ($7F9100-$7F911F at MAX=2)

; --- Phase 9 (plan.md 2.7) streaming BG1 initial-viewport load (StageColumn)
; -- see Bg_LoadScene_Streaming's header comment for the two-pass column
; algorithm this scratch supports. Boot-only for now: loads exactly
; STREAM_STAGE_VIEWPORT_COLS columns starting at world column 0 into VRAM
; columns 0..N-1 (identity mapping -- world column == VRAM column, always
; tilemap page A). SyncScroll (plan.md Phase 9 step 4, not yet written) is
; what will replace this with a true ring buffer, page-B addressing, and a
; world-column != VRAM-column mapping.
;
; Every scratch cell below is its OWN named symbol, never accessed via a
; `Symbol+N` offset (except where explicitly `.l`-qualified, matching
; core/math.pasm's proven-safe precedent) -- this project's standing
; caution against computed-offset operands mis-sizing under Poppy.
BG_MODE_STATIC = 0
BG_MODE_STREAMING = 1
STREAM_STAGE_VIEWPORT_COLS = 32   ; one screen's worth; boot-only, see above
STREAM_STAGE_ENTRY_BYTES = 3      ; matches CACHE_ENTRY_BYTES in the Python
                                    ; tools (u16 tile_id + u8 attribute)
; Phase 9 step 4 (SyncScroll): columns of margin kept resident beyond the
; 32-col viewport on each side, so a column is already VRAM-resident by the
; time the camera's edge reaches it at the existing 1px/frame scroll speed
; (a new column becomes visible every 8 frames; budget-capped staging (see
; Core_StreamScroll_ResolveRows) easily finishes one column well within
; that window).
STREAM_SCROLL_PREFETCH = 4
; A running 24-bit MSU byte offset for "this column's tilemap entries start
; here" -- initialized to the record's tilemap_offset (BgRecordStaging+16..18)
; and advanced by StreamStage_ColStrideLo (height_tiles*3) after each column,
; rather than recomputed via a multiply each time (columns are processed in
; strictly increasing order at boot, so a running add is exact and needs no
; runtime multiplication by a variable column index -- see
; pack_msu_roster.py's v4 module docstring for the parallel reasoning behind
; precomputing tilemap_offset/tiles_offset/hud_tiles_offset in Python).
StreamStage_SeekLo      = $7E2380   ; .dw
StreamStage_SeekHi      = $7E2382   ; .db
StreamStage_ColStrideLo = $7E2383   ; .dw -- height_tiles*3, computed once per
                                      ; level load (unrolled add, not a
                                      ; general multiply -- see
                                      ; Bg_LoadScene_Streaming's setup)
StreamStage_TilesBaseLo = $7E2385   ; .dw -- tiles_offset (record +20/21),
StreamStage_TilesBaseHi = $7E2387   ; .db -- read once, byte 2 (record +22)
StreamStage_TileOffLo   = $7E2388   ; .dw -- scratch: tile_id * 32 (also
                                      ; reused as a row*3 temp early in the
                                      ; row loop, before the tile-pixel-fetch
                                      ; use -- see that site's own comment)
StreamStage_TileOffHi   = $7E238A   ; .db -- high byte of the same tile_id*32
                                      ; scratch (StageColumn_FetchTilePixels
                                      ; use only -- NOT reused elsewhere)
StreamStage_SeekTmpLo   = $7E238B   ; .dw -- scratch: this tile-pixel fetch's
StreamStage_SeekTmpHi   = $7E238D   ; .db -- seek address (TilesBase+TileOff)
StreamStage_ColIndex    = $7E238E   ; .dw -- 0..STREAM_STAGE_VIEWPORT_COLS-1
StreamStage_RowIndex    = $7E2390   ; .dw -- 0..height_tiles-1
StreamStage_TileId      = $7E2392   ; .dw -- this row's decoded tile ID
StreamStage_Attr        = $7E2394   ; .db -- this row's decoded attribute byte
StreamStage_Slot        = $7E2395   ; .dw -- this row's resolved VRAM slot
StreamStage_Word        = $7E2397   ; .dw -- the hw tilemap word being built
                                      ; (own dedicated cell -- NOT TileOffHi,
                                      ; which is only 1 byte; an earlier
                                      ; version reused it as a 16-bit word
                                      ; here and silently stomped/misread
                                      ; SeekTmpLo, caught by
                                      ; phase9_stagecolumn_spotcheck.py
                                      ; reporting every tile's palette as 0)
; Decoded entries for the column currently being staged: up to
; STREAM_STAGE_MAX_ROWS rows x 3 bytes (tile_id lo, tile_id hi, attribute).
; Read in one uninterrupted sequential MSU burst (pass 1), then walked again
; (pass 2) to resolve a VRAM slot per tile and fetch any cache-miss tile's
; pixel data -- pass 2's tile fetches need their own seeks (into the tiles
; region), which would corrupt the tilemap region's sequential read position
; if the two passes were interleaved instead of separated like this.
STREAM_STAGE_MAX_ROWS = 28        ; must be >= any real level's height_tiles;
                                    ; BgRecordStaging+4 (height_tiles) drives
                                    ; the actual loop bound at runtime, this
                                    ; is only the buffer's fixed capacity
StreamStage_Entries   = $7E23A0   ; STREAM_STAGE_MAX_ROWS*3 = 84 bytes
                                    ; ($7E23A0-$7E23F3)

; --- Phase 9 step 4: SyncScroll (watermark + repair sweep + stamp walk)
; runtime state. Unlike StreamStage_* above (boot-only: forced blank is on,
; NMI isn't running yet, so Bg_LoadScene_Streaming/StageColumn_FetchTilePixels
; write the VRAM port directly), this runs every scpu_main_loop iteration
; with the screen ON -- every VRAM write here MUST go through
; Core_Dma_Enqueue (drained at the next real vblank by Core_Nmi_Play), never
; a direct $2118/$2119 poke, or it corrupts whatever the PPU is mid-drawing.
;
; Deliberately NOT read from BgRecordStaging at runtime, even though the
; boot-time code above does -- BgRecordStaging ($7E2340-235F) is boot-only
; scratch that CanvasChunkOffset/Sa1LoopCounter/PumpScratch/HudCachedHp (all
; declared elsewhere in this file, all written every frame) alias and
; overwrite almost immediately after boot. The fields SyncScroll needs
; (mode-enabled flag, width_tiles, tilemap_offset) are cached into the
; dedicated cells below by Bg_LoadScene_Streaming, while BgRecordStaging is
; still fresh, instead.
StreamScroll_Enabled     = $7E2521   ; .db -- 1 iff this level is
                                       ; BG_MODE_STREAMING; explicitly zeroed
                                       ; once, unconditionally, right after
                                       ; Core_StreamCache_Init in scpu_boot
                                       ; (WRAM is NOT guaranteed zero at
                                       ; power-on on real hardware) so a
                                       ; BG_MODE_STATIC build (the shipped
                                       ; boss level) never runs SyncScroll at
                                       ; all, since Bg_LoadScene_Streaming --
                                       ; the only place that sets this to 1 --
                                       ; never executes for that mode.
StreamScroll_StagedLo    = $7E2522   ; .dw -- lowest resident world column
StreamScroll_StagedHi    = $7E2524   ; .dw -- highest resident world column
StreamScroll_RepairCur   = $7E2526   ; .dw -- repair-sweep cursor (world
                                       ; column), cycles across
                                       ; [StagedLo, StagedHi]
StreamScroll_PendCol     = $7E2528   ; .dw -- world column currently being
                                       ; resolved, or $FFFF if none
StreamScroll_PendTile    = $7E252A   ; .dw -- next row to resolve within
                                       ; PendCol (0..height_tiles); ==
                                       ; height_tiles means every row
                                       ; resolved, only the commit DMA is
                                       ; still pending (budget spillover)
StreamScroll_WidthTiles  = $7E252C   ; .dw -- level width in tiles, cached
                                       ; from BgRecordStaging+2/3 (u16 LE)
StreamScroll_TilemapOffLo = $7E252E  ; .dw -- tilemap_offset low16, cached
StreamScroll_TilemapOffHi = $7E2530  ; .db -- tilemap_offset byte 2, cached
                                       ; from BgRecordStaging+16/17/18
StreamScroll_ProdHi      = $7E2531   ; .dw -- scratch: Core_Math_Mul's high
                                       ; product word (world_col * ColStride)
StreamScroll_CameraCol   = $7E2533   ; .dw -- scratch: Screen_PosX >> 3
StreamScroll_DesiredLo   = $7E2535   ; .dw -- scratch: watermark low bound
StreamScroll_DesiredHi   = $7E2537   ; .dw -- scratch: watermark high bound
; STREAM_SCROLL_BUDGET_MAX is the single knob for max cache-miss DMA
; enqueues per Core_StreamScroll_Play call. Raising it both loosens the
; Budget cap below AND grows StreamScroll_TileBufN (one more 32B slot per
; unit) -- the two must move together, since each per-call miss needs its
; own slot (see the buffer-aliasing note below), so this is the only place
; to change it. Sized empirically (built against out/bg_warehouse_stream, a
; real 13437-unique-tile streaming level, since the shipped boss level never
; exercises cache misses) by sweeping N and checking
; phase9_syncscroll_test2.py's hard-mismatch count: N=2/4/6 clean (N=6
; verified clean even well past the column where N=7/8 first fail -- see
; below -- ruling out a column-index-dependent cause), N=7/8 produce real
; per-column tilemap attribute (pal/hf/vf) corruption: the wrong tile's
; attributes land at a resident world_col. NOT a vblank-time DMA-drain
; overrun in the CLAUDE.md sense -- Nmi_FrameCounter keeps advancing
; normally at every N tested, including 7 and 8, which is the documented
; overrun's tell and it's absent here. Root cause not confirmed; leading
; candidate is NMI reentrancy corrupting a register (X/Y) carried across
; Core_StreamScroll_FetchTileToBuffer's/ResolveRows' per-miss loop bodies --
; see nmi_handler_no_register_save_reentrancy project memory -- since a
; higher N means more synchronous per-call MSU seek/read work and thus a
; wider window for a real vblank to land mid-loop. 6 is the largest
; confirmed-clean value; do not raise without re-running the sweep AND
; re-verifying Nmi_FrameCounter keeps advancing at the new N.
STREAM_SCROLL_BUDGET_MAX = 6

StreamScroll_Budget      = $7E2539   ; .db -- DMA enqueues issued so far this
                                       ; Core_StreamScroll_Play call (capped
                                       ; at STREAM_SCROLL_BUDGET_MAX)
; Core_Dma_Enqueue only stores the SOURCE ADDRESS, not the bytes -- the
; actual copy happens later, when this frame's NMI drains the queue. A
; single shared tile buffer meant a later miss's FetchTileToBuffer call
; overwrote an earlier miss's still-unDMA'd bytes before the queue ever
; drained, so the earlier miss's VRAM slot silently received the later
; tile's pixels instead of its own -- confirmed via
; phase9_syncscroll_test2.py: Tile2Slot correctly reported the 1st tile
; resident at its slot, yet the slot's VRAM bytes didn't match that tile,
; only the (different) tile fetched right after it in the same call. Fixed
; with STREAM_SCROLL_BUDGET_MAX separate 32B slots, one per possible
; per-call miss, in a single contiguous bank-$7F block (free space, well
; past Tile2Slot/Slot2Tile/SlotStamp) so the source bank is always a
; constant ($7F) and the slot for a given miss is just base +
; FetchBufSel*32 -- see StreamScroll_FetchBufSel.
StreamScroll_TileBufN    = $7F9000   ; STREAM_SCROLL_BUDGET_MAX*32 bytes
                                       ; ($7F9000-$7F90FF at MAX=8)
StreamScroll_FetchBufSel = $7E2599   ; .db -- which of the
                                       ; STREAM_SCROLL_BUDGET_MAX slots the
                                       ; miss currently being resolved should
                                       ; use; set from StreamScroll_Budget's
                                       ; value BEFORE that miss's
                                       ; fetch/enqueue (Budget is
                                       ; only incremented AFTER a successful
                                       ; enqueue, so it's 0 for this call's
                                       ; 1st miss, 1 for its 2nd, etc).
; StreamScroll_ColBuf/HeightTiles/ColPending/ColTargetWord are declared
; earlier, alongside Msu1_StreamBusy, textually before core/nmi.pasm's
; .include -- Core_Nmi_Play's forced-blank column-write block references
; them, same reason Msu1_StreamBusy lives up there.

; --- Phase 6 HUD (Hud_Play). Tile ids must match make_hud_tiles.py's manifest. ---
HUD_TILE_BLANK     = 0
HUD_TILE_FILL_BASE = 1    ; +n = n columns filled, n = 0..8  (tiles 1..9)
HUD_TILE_CAP_LEFT  = 10
HUD_TILE_CAP_RIGHT = 11
HUD_BAR_TILES      = 8    ; body tiles per bar; 8 px each -> CHAR_HP_MAX = 64
HUD_ROWS           = 4    ; one bar per entity, rows 0-3 of the BG3 tilemap
HUD_STAGING_BYTES  = 256  ; HUD_ROWS * 32 entries * 2 bytes -- one DMA covers
                           ; all four bars, so the HUD costs ONE queue slot, not
                           ; four (DMA_QUEUE_SLOTS is only 8 and one entity's
                           ; Msu1_LoadFrame already enqueues 6)
; Tilemap high byte for every HUD entry: palette 0 (the HUD owns CGRAM
; sub-palette 0) with the priority bit (bit 13) set, which is what puts BG3
; above the backdrop given BGMODE's BG3-priority bit.
HUD_ENTRY_HIGH     = $20

HudCachedHp        = $7E2360   ; 4B  -- last HP drawn, per entity (shifted
                                 ; from $7E2350 -> $7E2354 -> $7E2360 as
                                 ; BgRecordStaging grew 16B -> 20B -> 32B
                                 ; across the v3/v4 BG record formats)
HudDirty           = $7E2364   ; .db -- nonzero forces a redraw (set at boot)
HudBarHp           = $7E2365   ; .db -- scratch: HP remaining while drawing a bar
HudBarFilled       = $7E2366   ; .db -- scratch: filled columns for one tile
HudStaging         = $7E2400   ; 256B -- BG3 tilemap rows 0-3, pre-DMA
; Msu1_StreamBusy is declared earlier in this file (before the core/*.pasm
; .include block) -- core/nmi.pasm's Core_Nmi_Play references it, and that
; .include is textually processed before this point, so the constant must
; already exist by then. See that declaration's own comment for what it
; does.

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
    ; --- plan.md Phase 5: Select-button reselect applies to the PLAYER
    ; only (CHAR_INPUT_DRIVEN==1). CharSelect_Index is a single global
    ; cell, not per-instance state, so letting every AI entity react to it
    ; too would make all of them reselect in lockstep on every press --
    ; nonsensical once there's more than one entity. AI roles keep
    ; whatever character CharacterEntity_Init assigned them and ignore
    ; Select entirely; this is the deliberate, smallest-change decision
    ; plan.md settles on rather than building per-instance roster state. ---
    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq Anim_Play__check_reselect
    bra Anim_Play__no_reselect
    nop
Anim_Play__check_reselect:
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
    ; --- plan.md Phase 4: hit-reaction stun takes priority over both the
    ; "already attacking" latch below and any input/AI decision -- a
    ; stunned entity is forced to idle regardless of what it was doing,
    ; and stays there (re-entering here every frame while CHAR_HIT_STUN
    ; is nonzero, since Anim_Play runs once per entity per frame via
    ; CharacterEntity_Play) until the countdown reaches 0. Decremented
    ; here, not in Character_HitApply, so it counts down exactly once per
    ; frame regardless of whether this entity ever attacks. Only forces
    ; the CHAR_SELECTED/CHAR_FRAME_INDEX reset on the FIRST stunned frame
    ; (CHAR_SELECTED already 0) -- otherwise every subsequent stunned
    ; frame would restart idle at frame 0 every tick instead of letting it
    ; loop naturally, which would look like a stutter instead of a held
    ; reaction. ---
    lda CHAR_HIT_STUN
    beq Anim_Play__not_stunned
    dec a
    sta CHAR_HIT_STUN
    lda CHAR_SELECTED
    bne Anim_Play__stunned_reset
    brl Anim_Play__dispatch     ; already idle -- let it keep looping, just hold
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__stunned_reset:
    lda #0
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    brl Anim_Play__dispatch
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__not_stunned:
    lda CHAR_SELECTED
    cmp #2
    bne Anim_Play__check_attack_trigger
    brl Anim_Play__dispatch     ; already attacking -- ignore input, let it finish
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__check_attack_trigger:
    ; --- plan.md Phase 3: route animation-selection by movement source
    ; instead of always reading the real controller -- CHAR_INPUT_DRIVEN
    ; wasn't checked here before this phase, which meant every entity
    ; (including Phase 2's static Entity #1) reacted to real dpad/Y-button
    ; presses for its OWN CHAR_SELECTED even though only Character_
    ; PlayFrame's position-movement code checked the flag; harmless while
    ; Entity #1 stayed idle-only (mode 0 below reproduces that), but would
    ; have broken a mode-2 AI entity, whose CHAR_SELECTED this phase needs
    ; to drive from distance-to-player instead. ---
    lda CHAR_INPUT_DRIVEN
    cmp #2
    beq Anim_Play__ai_seek
    cmp #1
    beq Anim_Play__player_input
    ; --- mode 0: static -- always idle, ignore real controller state. ---
    lda #0
    brl Anim_Play__want_got     ; bra went out of range (Phase 8's AI-seek
                                  ; widening pushed want_got further away);
                                  ; Poppy errors cleanly on this rather than
                                  ; silently miscompiling, unlike a bcc/beq
                                  ; over-range -- brl has full range and is
                                  ; already used elsewhere in this routine
    nop
Anim_Play__player_input:
    lda.l Input_trigger+1
    and #ANIM_ATTACK_BUTTON_MASK
    beq Anim_Play__no_attack_trigger
    lda #2
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
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
    bra Anim_Play__want_got
    nop
    ; --- mode 2: AI seek (plan.md Phase 3) -- walk toward Entity #0
    ; (`PlayerEntity_PosX/Y`, the fixed-slot-0 shortcut) unless within
    ; ANIM_AI_ATTACK_RANGE pixels on BOTH axes, in which case attack
    ; instead. Exact unsigned abs-difference per axis (compare-then-
    ; subtract-the-right-way, no two's-complement wraparound approximation
    ; -- correct across the full 0-255 coordinate range, not just |diff|
    ; <128). Reuses Anim_Play__want_got's existing switch-to-1(walk)
    ; dispatch machinery for the "far" case; the "close" case duplicates
    ; the button-driven attack-trigger block above (same shape, different
    ; trigger condition) since it must set CHAR_SELECTED directly, not
    ; via want_got (which only handles idle/walk toggling, not attack). ---
Anim_Play__ai_seek:
    ; X only (Phase 8: CHAR_POS_X is now a real 16-bit world coordinate,
    ; since a level can be wider than one 256px screen -- Y stays 8-bit,
    ; there is no vertical scroll). Every branch target in this X portion
    ; gets a redundant rep #$20/.a16 resync (poppy bug #10); Y and
    ; Anim_Play__want_got below are still real 8-bit fields (CHAR_POS_Y,
    ; CHAR_SELECTED), so .a8 is restored before either is touched.
    rep #$20
.a16
    lda.l PlayerEntity_PosX
    cmp CHAR_POS_X
    bcs Anim_Play__ai_dx_playerge
    lda CHAR_POS_X
    sec
    sbc.l PlayerEntity_PosX
    bra Anim_Play__ai_dx_have
    nop
Anim_Play__ai_dx_playerge:
    rep #$20
.a16
    sec
    sbc CHAR_POS_X
    nop
Anim_Play__ai_dx_have:
    cmp #ANIM_AI_ATTACK_RANGE+1
    bcc Anim_Play__ai_dx_close
    sep #$20
.a8
    lda #1                          ; farther than range on X alone -- walk,
    bra Anim_Play__want_got         ; no need to also check Y
    nop
Anim_Play__ai_dx_close:
    sep #$20
.a8
    lda.l PlayerEntity_PosY
    cmp CHAR_POS_Y
    bcs Anim_Play__ai_dy_playerge
    lda CHAR_POS_Y
    sec
    sbc.l PlayerEntity_PosY
    bra Anim_Play__ai_dy_have
    nop
Anim_Play__ai_dy_playerge:
    sec
    sbc CHAR_POS_Y
    nop
Anim_Play__ai_dy_have:
    cmp #ANIM_AI_ATTACK_RANGE+1
    bcc Anim_Play__ai_attack
    lda #1
    bra Anim_Play__want_got
    nop
Anim_Play__ai_attack:
    lda #2
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    brl Anim_Play__dispatch
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__want_got:
    cmp CHAR_SELECTED
    beq Anim_Play__dispatch
    sta CHAR_SELECTED
    ; Switching animations: reset to frame -1 (wraps to 0 on the forced
    ; advance below, via 8-bit inc a) and force an immediate advance this
    ; same call, rather than waiting up to a full *_FRAME_DELAY ticks to
    ; show the new animation. Unlike the boot-time cosmetic pop (handoff.md,
    ; "What's NOT done yet"), this is new code with no prior verified
    ; behavior to preserve, so there's no reason to carry the same
    ; frame-skips-0 quirk into it.
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play__dispatch:
    jsr Anim_UpdateFacing
    ; Anim_UpdateFacing exits in .a16/.i16 (its own external convention,
    ; matching Anim_Play's) -- but everything below here was written
    ; assuming .a8 (inherited from Anim_Play's own top). Re-assert it
    ; explicitly rather than relying on whatever state happened to precede
    ; this call; omitting this turned `lda CHAR_SELECTED` into a 16-bit
    ; read spanning Anim_Selected+Anim_FacingLeft, and `cmp #2`/`cmp #1`
    ; into 16-bit compares that silently stopped matching -- confirmed by
    ; Mesen: attack triggered once then never re-dispatched, Anim_FrameIndex
    ; free-ran 0-5 like idle while Anim_Selected stayed stuck at 2 in WRAM.
    sep #$20
.a8
    lda CHAR_SELECTED
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
; press) and updates Anim_FacingLeft if it differs. Neither direction held
; -> keep the last facing (matches how real games hold facing through
; idle/attack). Called once per Anim_Play invocation, regardless of which
; animation is active -- facing is independent of Anim_Selected. Exits in
; .a16/.i16, same convention as its caller.
;
; No longer does any DMA of its own -- now that the character renders as a
; real OAM sprite (see Character_PlayFrame) instead of a BG2 tilemap
; window, facing is just this one WRAM flag; Character_PlayFrame reads it
; each frame and sets the OAM attribute byte's hflip bit, and the hardware
; mirrors the whole 32x64 sprite block for free. This used to DMA two
; precomputed 6-row tilemap blocks (ANIM_TILEMAP_RIGHT_BASE/LEFT_BASE) over
; the BG2 window's active tile entries on every facing change -- that whole
; mechanism (and the 12 Anim_EnqueueTilemapRow calls that drove it) is gone;
; the ANIM_TILEMAP_* constants and Anim_EnqueueTilemapRow itself are now
; unused dead code, left in place rather than torn out along with this
; change (harmless, no per-frame cost).
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
    sta CHAR_FACING_LEFT
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
    ; Msu1_StreamBusy gate (see that cell's own comment) -- checked BEFORE
    ; the tick decrement below, not after it reaches 0, so a blocked
    ; entity's countdown pauses for a frame instead of pinning at 0 and
    ; re-losing the race to a lower-priority caller every single frame.
    lda.l Msu1_StreamBusy
    beq Anim_Play_Idle__not_busy
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__not_busy:
    lda CHAR_TICK_COUNTER
    dec a
    sta CHAR_TICK_COUNTER
    beq Anim_Play_Idle__advance
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__advance:

    lda CHAR_IDLE_DELAY
    sta CHAR_TICK_COUNTER

    lda CHAR_FRAME_INDEX
    inc a
    sta CHAR_FRAME_INDEX
    cmp CHAR_IDLE_FCOUNT
    bcc Anim_Play_Idle__frame_ok
    lda #0
    sta CHAR_FRAME_INDEX        ; wrap (manifest loop=1)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__frame_ok:
    ; Copy this animation's 24-bit MSU base into AnimHeaderStaging+0/1/2 for
    ; Msu1_LoadFrame (see that routine's header for why this scratch reuse
    ; is safe), then stream frame_index.
    rep #$31
.a16
.i16
    lda CHAR_IDLE_BASE_LO
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda CHAR_IDLE_BASE_HI
    sta.l AnimHeaderStaging+2
    lda CHAR_FRAME_INDEX
    jsr Msu1_LoadFrame
    rts

; Same structure as Anim_Play_Idle above, using Anim_WalkFrameCount/Delay/
; MsuBase. Only called while Anim_Selected == 1 (see Anim_Play above).
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_Play_Walk:
    sep #$20
.a8
    ; Msu1_StreamBusy gate -- see Anim_Play_Idle's copy of this same block
    ; for why the check must come before the tick decrement.
    lda.l Msu1_StreamBusy
    beq Anim_Play_Walk__not_busy
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__not_busy:
    lda CHAR_TICK_COUNTER
    dec a
    sta CHAR_TICK_COUNTER
    beq Anim_Play_Walk__advance
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__advance:

    lda CHAR_WALK_DELAY
    sta CHAR_TICK_COUNTER

    lda CHAR_FRAME_INDEX
    inc a
    sta CHAR_FRAME_INDEX
    cmp CHAR_WALK_FCOUNT
    bcc Anim_Play_Walk__frame_ok
    lda #0
    sta CHAR_FRAME_INDEX        ; wrap (manifest loop=1)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__frame_ok:
    rep #$31
.a16
.i16
    lda CHAR_WALK_BASE_LO
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda CHAR_WALK_BASE_HI
    sta.l AnimHeaderStaging+2
    lda CHAR_FRAME_INDEX
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
    ; Msu1_StreamBusy gate -- see Anim_Play_Idle's copy of this same block
    ; for why the check must come before the tick decrement.
    lda.l Msu1_StreamBusy
    beq Anim_Play_Attack__not_busy
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__not_busy:
    lda CHAR_TICK_COUNTER
    dec a
    sta CHAR_TICK_COUNTER
    beq Anim_Play_Attack__advance
    brl Anim_Done   ; too far for an 8-bit bne from here
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__advance:

    lda CHAR_FRAME_INDEX
    inc a
    cmp CHAR_ATTACK_FCOUNT
    bcc Anim_Play_Attack__frame_ok
    ; Animation finished -- revert to idle instead of wrapping.
    lda #0
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    brl Anim_Done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__frame_ok:
    sta CHAR_FRAME_INDEX
    lda CHAR_ATTACK_DELAY
    sta CHAR_TICK_COUNTER
    rep #$31
.a16
.i16
    lda CHAR_ATTACK_BASE_LO
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda CHAR_ATTACK_BASE_HI
    sta.l AnimHeaderStaging+2
    lda CHAR_FRAME_INDEX
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

    ; --- Precompute this instance's row-DMA target byte offset,
    ; CHAR_TILE_COLUMN*128 (plan.md Phase 1b Step 3 -- see the row-DMA
    ; comment below for the *128 derivation). Done here, after the
    ; frame_index parameter above is already safely captured off the
    ; accumulator into WRAM, since A can't be clobbered before that. ---
    sep #$20
.a8
    lda CHAR_TILE_COLUMN
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                       ; a = CHAR_TILE_COLUMN * 128
    sta CHAR_TILE_BYTE_OFFSET

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

    ; --- enqueue 6 strided WRAM($7E)->VRAM row DMAs of the streamed frame,
    ; one per tile-row of the character's real OAM sprite (replaces the old
    ; single flat 768-byte DMA into a fixed BG2 tile window). A real OAM
    ; sprite's tile-fetch hardware indexes tiles as (tileRow<<4)|tileColumn
    ; in a 16-tile-wide sheet (Mesen2-source-verified: SnesPpu.cpp's
    ; GetSpriteTileAddress computes `tileIndex = (row<<4)|((tileColumn+
    ; columnOffset)&0x0F)`) -- so for our 4-tiles-wide character, row r's 4
    ; tiles sit at consecutive VRAM tile indices within that row (contiguous,
    ; one 128-byte DMA each), but consecutive ROWS jump by 16 tile-index
    ; slots (not 4), i.e. word address $4000 + r*256, byte address
    ; $8000 + r*512 -- NOT a flat contiguous 768-byte run the way the old
    ; BG2 window (addressed via a tilemap, not direct hardware tile-block
    ; fetch) could use. AnimFrameStaging's own 768-byte layout (24 tiles,
    ; row-major within its 4-wide source raster) is unchanged and still
    ; correct as the SOURCE for each of these 6 row-slices -- only the
    ; VRAM-side destination stride is new. Base tile index 0 (OBJ base
    ; $4000, tileRow 0, tileCol 0); rows 6-7 of the 32x64 large-sprite block
    ; are pre-blanked once at boot (see Character_BlankPadding) since only
    ; 6 of the 8 rows carry real 32x48 art.
    lda #AnimFrameStaging
    sta.l DmaRequest_SourceAddrLow
    lda #$8000                  ; row 0: word $4000 (tileRow0,col0) * 2
    clc                         ; + this instance's CHAR_TILE_COLUMN*128
    adc CHAR_TILE_BYTE_OFFSET   ; column offset (Step 3; 0 at column 0,
    sta.l DmaRequest_TargetAddr ; reproducing the prior hardcoded address)
    lda #128                    ; 4 tiles/row * 32 bytes/tile
    sta.l DmaRequest_Length
    jsr Msu1_LoadFrame_EnqueueRow

    lda #AnimFrameStaging + 128
    sta.l DmaRequest_SourceAddrLow
    lda #$8200                  ; row 1: word $4100 (tileRow1,col0) * 2
    clc
    adc CHAR_TILE_BYTE_OFFSET
    sta.l DmaRequest_TargetAddr
    jsr Msu1_LoadFrame_EnqueueRow

    lda #AnimFrameStaging + 256
    sta.l DmaRequest_SourceAddrLow
    lda #$8400                  ; row 2: word $4200 * 2
    clc
    adc CHAR_TILE_BYTE_OFFSET
    sta.l DmaRequest_TargetAddr
    jsr Msu1_LoadFrame_EnqueueRow

    lda #AnimFrameStaging + 384
    sta.l DmaRequest_SourceAddrLow
    lda #$8600                  ; row 3: word $4300 * 2
    clc
    adc CHAR_TILE_BYTE_OFFSET
    sta.l DmaRequest_TargetAddr
    jsr Msu1_LoadFrame_EnqueueRow

    lda #AnimFrameStaging + 512
    sta.l DmaRequest_SourceAddrLow
    lda #$8800                  ; row 4: word $4400 * 2
    clc
    adc CHAR_TILE_BYTE_OFFSET
    sta.l DmaRequest_TargetAddr
    jsr Msu1_LoadFrame_EnqueueRow

    lda #AnimFrameStaging + 640
    sta.l DmaRequest_SourceAddrLow
    lda #$8A00                  ; row 5: word $4500 * 2
    clc
    adc CHAR_TILE_BYTE_OFFSET
    sta.l DmaRequest_TargetAddr
    jsr Msu1_LoadFrame_EnqueueRow

    ; All 6 rows are now queued but not yet drained -- Core_Dma_ProcessQueue
    ; only runs at the next real vblank (inside Core_Nmi_Play), and their
    ; source is AnimFrameStaging, a single shared buffer. Hold the busy gate
    ; until that drain is confirmed (Core_Nmi_Play, core/nmi.pasm, clears
    ; this) so no other caller overwrites AnimFrameStaging out from under
    ; these still-pending DMAs. See Msu1_StreamBusy's own comment.
    sep #$20
.a8
    lda #1
    sta.l Msu1_StreamBusy

    plp
    rep #$31
.a16
.i16
    rts

; Shared tail for Msu1_LoadFrame's 6 row-DMA sites above: caller sets
; DmaRequest_SourceAddrLow/TargetAddr (Length is constant across all of
; them, set once before the first call), this fills in the constant
; SourceBank/TypeFlags fields and enqueues. Same shared-tail pattern as
; Anim_EnqueueTilemapRow above. Entry/exit width-agnostic (re-asserts its
; own widths), matching that routine's convention.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Msu1_LoadFrame_EnqueueRow:
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
    bcs Msu1_LoadFrame_EnqueueRow__ok
    ; Queue full. Defense-in-depth, not the primary fix (see
    ; Msu1_StreamBusy) -- with that gate correctly preventing two entities'
    ; streams from overlapping, this should never actually trigger. If it
    ; does, some other source of DMA-queue pressure this project hasn't
    ; accounted for is present; faulting surfaces that immediately instead
    ; of silently dropping this row's VRAM update and leaving a stale-tile
    ; rendering bug to be "discovered" later. Inlined pea/jsr (not the
    ; Core_Error_Trigger macro) -- see core/error.pasm's header for why a
    ; macro invocation skipped by a branch mis-sizes the branch offset in
    ; this Poppy build; core/dma.pasm's own Core_Dma_Enqueue uses the same
    ; inlined shape for the same reason.
    pea Error_DmaQueueFull
    jsr Core_Error_Handler
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Msu1_LoadFrame_EnqueueRow__ok:
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
; Bare $21xx addresses below (and in TestSprite_WriteSolidTile) switched to
; explicit `.l $00xxxx` long addressing while investigating a speckled-noise
; rendering bug -- turned out not to be the actual cause (root cause was a
; missing branch-target nop guard in core/oam.pasm's Core_Oam_Play, see that
; file's Core_Oam_Play__hi_len_done comment). Left in place since it's
; harmless either way, not because DBR was confirmed uncertain here.
TestSprite_Init:
    rep #$20
.a16
    lda #$4000                ; tile 0 (top-left quadrant), OBJ base
    sta.l $002116
    jsr TestSprite_WriteSolidTile
    lda #$4010                ; tile 1 (top-right quadrant): base + 1*16 words
    sta.l $002116
    jsr TestSprite_WriteSolidTile
    lda #$4100                ; tile $10 (bottom-left quadrant): base + 16*16 words
    sta.l $002116
    jsr TestSprite_WriteSolidTile
    lda #$4110                ; tile $11 (bottom-right quadrant): base + 17*16 words
    sta.l $002116
    jsr TestSprite_WriteSolidTile

    ; --- OBJ palette: CGRAM color 192 (pixel value 0, unused/transparent,
    ; left black) + color 193 (pixel value 1, bright red: R=31 G=0 B=0) ---
    ; OBJ palette 4 (colors 192/193), NOT palette 0 -- palette 0 is
    ; CHAR_PALETTE_SLOT=0, the real player entity's palette, and this
    ; routine runs (from scpu_boot, after Core_Oam_Init) AFTER msu1_done's
    ; Anim_LoadCharacter has already DMA'd entity 0's real 16-color palette
    ; into CGRAM colors 128-143. Originally hardcoded to palette 0's colors
    ; 128/129, which silently overwrote entity 0's own color-index-1 with
    ; this test sprite's literal red every boot -- found via byte-exact
    ; comparison against bor.msu's ground truth (see
    ; msu_track_select_seek_ordering_risk memory / handoff.md Phase 5).
    ; Palettes 4-7 are unused by any CharacterEntity (slots 0-3 only).
    sep #$20
.a8
    lda #$C0
    sta.l $002121                ; CGRAM address = color 192 (OBJ palette 4)
    lda #0
    sta.l $002122                 ; color 192 low byte
    sta.l $002122                 ; color 192 high byte
    lda #$1F
    sta.l $002122                 ; color 193 low byte ($001F = pure red)
    lda #0
    sta.l $002122                 ; color 193 high byte

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
    lda #$38                  ; priority 3, palette 4, name table 0, no flip --
                               ; palette 4 (not 0) to match the CGRAM colors
                               ; 192/193 written above, off entity 0's real
                               ; palette 0 (see the CGRAM-write comment above)
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
    sta.l $002118
    dex
    bne TestSprite_WriteSolidTile__plane01

    ldx #8
    lda #$0000
    nop
TestSprite_WriteSolidTile__plane23:
    sta.l $002118
    dex
    bne TestSprite_WriteSolidTile__plane23
    rts

; One-time boot blank of the character sprite's unused padding tiles.
; OBSEL mode 6's "large" size is 32x64 (4 tiles wide x 8 tall, per Mesen2-
; source-verified _oamSizes[6][1] = {4,8}), but our real art is only 32x48
; (4x6 tiles) -- rows 6-7 of the 8-tall block would otherwise show whatever
; garbage was last in that VRAM region. Tile-row addressing is NOT
; contiguous with the previous row's 4 tiles: hardware tile index is
; (tileRow<<4)|tileColumn (16-wide sheet), so row 6's 4 tiles sit at word
; $4000+6*256=$4600..$463F while row 7's sit at $4700..$473F -- a 192-word
; gap between them, same stride Msu1_LoadFrame's row DMAs use. Runs once
; from scpu_boot, still under forced blank (same $2116/$2118 direct-write
; pattern TestSprite_WriteSolidTile above uses), so no DMA needed.
;
; plan.md Phase 5: THIS WAS A LIVE, CONFIRMED BUG until this change -- the
; original version below only blanked tile-column-slice 0 (hardcoded
; $4600/$4700). Every entity in a NON-zero slice (Entity #1 at slice 1 was
; already live before this phase) displayed whatever was last in that VRAM
; region -- confirmed in Mesen2, 3/3 fresh sessions: slice-0's padding read
; 0/128 nonzero, slice-1's read 124-128/128 nonzero with different garbage
; bytes each run (power-on VRAM randomness, never written). Now unrolled
; across all 4 slices this project supports (see Entity1/2/3_Base's own
; comment for why 4 is the real cap) -- fully unrolled with compile-time-
; constant word addresses rather than a runtime loop indexed by slice,
; since this is one-shot boot code with no performance requirement and
; avoiding any indexed addressing here sidesteps this project's several
; confirmed Poppy indexed-addressing miscompile bugs entirely. Per-slice
; word addresses: row 6 = $4600 + slice*$40, row 7 = $4700 + slice*$40
; (slice*$40 words = slice*128 bytes = slice*4 tiles*32 bytes, matching
; CHAR_TILE_BYTE_OFFSET's own CHAR_TILE_COLUMN*128 derivation elsewhere).
    nop
    nop
    nop
    nop
; Every $21xx write below uses explicit `.l $00xxxx` long addressing instead
; of a bare address. This was a first fix attempt (assuming a DBR-uncertainty
; issue, the same class already found in core/oam.pasm's Core_Oam_Init this
; session) while investigating a speckled-noise rendering bug -- turned out
; NOT to be the actual cause. The real bug was a missing branch-target nop
; guard in core/oam.pasm's Core_Oam_Play (see that file's
; Core_Oam_Play__hi_len_done comment) that silently halved the one-shot
; full-table OAM upload's length, leaving most of hardware OAM (both tables)
; at its power-on-random content -- garbage Y/size bits on otherwise-hidden
; sprites rendered as scattered noise, nothing to do with VRAM/CGRAM write
; timing at all. Left as `.l` anyway since it's harmless, just not the fix.
Character_BlankPadding:
    rep #$20
.a16
    lda #$4600                ; slice 0, tileRow 6
    sta.l $002116
    rep #$31
.a16
.i16
    ldx #64                    ; 4 tiles * 16 words/tile
    lda #$0000
    nop
Character_BlankPadding__s0_row6:
    sta.l $002118
    dex
    bne Character_BlankPadding__s0_row6

    rep #$20
.a16
    lda #$4700                ; slice 0, tileRow 7
    sta.l $002116
    rep #$31
.a16
.i16
    ldx #64
    lda #$0000
    nop
Character_BlankPadding__s0_row7:
    sta.l $002118
    dex
    bne Character_BlankPadding__s0_row7

    rep #$20
.a16
    lda #$4640                ; slice 1, tileRow 6
    sta.l $002116
    rep #$31
.a16
.i16
    ldx #64
    lda #$0000
    nop
Character_BlankPadding__s1_row6:
    sta.l $002118
    dex
    bne Character_BlankPadding__s1_row6

    rep #$20
.a16
    lda #$4740                ; slice 1, tileRow 7
    sta.l $002116
    rep #$31
.a16
.i16
    ldx #64
    lda #$0000
    nop
Character_BlankPadding__s1_row7:
    sta.l $002118
    dex
    bne Character_BlankPadding__s1_row7

    rep #$20
.a16
    lda #$4680                ; slice 2, tileRow 6
    sta.l $002116
    rep #$31
.a16
.i16
    ldx #64
    lda #$0000
    nop
Character_BlankPadding__s2_row6:
    sta.l $002118
    dex
    bne Character_BlankPadding__s2_row6

    rep #$20
.a16
    lda #$4780                ; slice 2, tileRow 7
    sta.l $002116
    rep #$31
.a16
.i16
    ldx #64
    lda #$0000
    nop
Character_BlankPadding__s2_row7:
    sta.l $002118
    dex
    bne Character_BlankPadding__s2_row7

    rep #$20
.a16
    lda #$46C0                ; slice 3, tileRow 6
    sta.l $002116
    rep #$31
.a16
.i16
    ldx #64
    lda #$0000
    nop
Character_BlankPadding__s3_row6:
    sta.l $002118
    dex
    bne Character_BlankPadding__s3_row6

    rep #$20
.a16
    lda #$47C0                ; slice 3, tileRow 7
    sta.l $002116
    rep #$31
.a16
.i16
    ldx #64
    lda #$0000
    nop
Character_BlankPadding__s3_row7:
    sta.l $002118
    dex
    bne Character_BlankPadding__s3_row7
    rts

; Sole per-frame writer for the real BOR character's OAM sprite (slot 0),
; called once/frame from scpu_main_loop, right before Core_Oam_Play.
; Replaces the old TestSprite_PlayFrame (decorative test square, retired)
; and Player_PlayFrame (dpad-driven test square, merged in here) -- this is
; now the SAME entity: dpad movement (unchanged from the old Player_PlayFrame
; logic below) drives the position of the real, animated character whose
; current frame Anim_Play/Msu1_LoadFrame streams into this sprite's OBJ tile
; slot (base tile 0) every time its animation advances. Facing comes from
; Anim_FacingLeft (still updated by Anim_UpdateFacing, which no longer does
; any tilemap DMA of its own -- see that routine) via the attribute byte's
; hardware hflip bit (bit6, $40) instead of the old per-tile tilemap-swap
; trick a BG2 window needed; hardware mirrors the whole 32x64 block for
; free. Because Core_Nmi_Play wipes the ENTIRE OAM shadow back to "all
; hidden" after every successful upload (see Core_Oam_ClearAll), this
; routine resets Oam_CurrentSlot to 0 itself every call rather than relying
; on a separate routine to have done it first (TestSprite_PlayFrame's old
; role) -- it's now the only sprite writer, so it owns the whole cursor
; sequence. Must be called in .a16/.i16 and returns the same way, matching
; scpu_main_loop's convention.
;
; workaround: Poppy label address off-by-one (see poppy bug #4 / poppy bug
; #5's more general form) -- the old Player_PlayFrame at this same rough
; file position needed this same padding (raw-byte-verified in a prior
; session: without it, the label resolved 1 byte early onto the preceding
; routine's `rts`) -- kept here since nothing about the file position that
; caused it has changed enough to assume it's no longer needed.
    nop
    nop
    nop
    nop
Character_PlayFrame:
    ; --- OAM cursor reset: only the FIRST entity dispatched this frame
    ; resets Oam_CurrentSlot to 0; later entities leave it where the prior
    ; entity's Core_Oam_SetSprite call left it, so they append into the next
    ; free slot instead of overwriting slot 0 (plan.md Phase 1b Step 3; see
    ; Oam_CursorResetDone's own comment). Explicitly NOT keyed on
    ; OopObjIndex. ---
    sep #$20
.a8
    lda.l Oam_CursorResetDone
    bne Character_PlayFrame__cursor_done
    lda #1
    sta.l Oam_CursorResetDone
    rep #$31
.a16
    lda #0
    sta Oam_CurrentSlot
    bra Character_PlayFrame__cursor_next
    nop
Character_PlayFrame__cursor_done:
    rep #$31
.a16
    nop
Character_PlayFrame__cursor_next:

    ; --- X: held-dpad Left/Right movement (mode 1) or AI seek-toward-player
    ; (mode 2, plan.md Phase 3) or hold (mode 0). Unchanged from the old
    ; Player_PlayFrame for mode 1 -- see that routine's original header
    ; comment (now here) for why Left wins on both-held and why the clamp
    ; compares are unsigned. ---
    sep #$20
.a8
    ; --- plan.md Phase 4: hit-stun freezes movement too, same priority as
    ; Anim_Play's stun check (CHAR_HIT_STUN already decremented there this
    ; frame, before Character_PlayFrame runs -- see CharacterEntity_Play's
    ; call order). ---
    lda CHAR_HIT_STUN
    beq Character_PlayFrame__not_stunned_x
    bra Character_PlayFrame__hold
    nop
Character_PlayFrame__not_stunned_x:
    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq Character_PlayFrame__dpad_x
    cmp #2
    beq Character_PlayFrame__ai_x
    bra Character_PlayFrame__hold
    nop
Character_PlayFrame__dpad_x:
    lda.l Input_press+1
    and #$03
    beq Character_PlayFrame__hold
    lda.l Input_press+1
    and #$02                       ; bit9 (Left) of the word = bit1 of this byte -- Left wins
    beq Character_PlayFrame__right
    bra Character_PlayFrame__left
    nop
Character_PlayFrame__ai_x:
    ; Hold if within ANIM_AI_ATTACK_RANGE on X, matching Anim_Play's own
    ; attack-range decision independently -- deliberately NOT keyed off
    ; CHAR_SELECTED==2 (an earlier version did this and read stale/racy
    ; state: Anim_Play_Attack reverts CHAR_SELECTED to 0 on its own last
    ; frame, one call before Anim_Play's AI-seek logic re-evaluates
    ; distance and re-triggers attack next frame -- Character_PlayFrame
    ; runs in between and would see the transient 0, letting exactly one
    ; frame of movement leak through per attack cycle. Confirmed via
    ; Mesen2: X crept from 94 toward the player by ~2px every ~40-50
    ; frames despite CHAR_SELECTED reading 2 at every sampled point).
    ; Recomputing distance directly here is immune to that timing gap.
    ;
    ; Phase 8: this whole X block (through Character_PlayFrame__store_x) is
    ; now 16-bit -- CHAR_POS_X is a real world coordinate, since a level can
    ; be wider than one 256px screen. Every label below gets a redundant
    ; rep #$20/.a16 resync (poppy bug #10), since __right/__left/__hold are
    ; also reached directly from the still-.a8 dpad dispatch above. Y stays
    ; 8-bit unchanged (no vertical scroll).
    rep #$20
.a16
    lda.l PlayerEntity_PosX
    cmp CHAR_POS_X
    beq Character_PlayFrame__hold  ; already X-aligned with the player
    bcs Character_PlayFrame__ai_x_playerge
    ; self > player
    lda CHAR_POS_X
    sec
    sbc.l PlayerEntity_PosX
    cmp #ANIM_AI_ATTACK_RANGE+1
    bcc Character_PlayFrame__hold
    bra Character_PlayFrame__left  ; player is to the left -- reuse __left
    nop
Character_PlayFrame__ai_x_playerge:
    ; A is still playerX (cmp doesn't touch it)
    rep #$20
.a16
    sec
    sbc CHAR_POS_X
    cmp #ANIM_AI_ATTACK_RANGE+1
    bcc Character_PlayFrame__hold
    bra Character_PlayFrame__right ; player is to the right -- reuse __right
    nop
Character_PlayFrame__right:
    rep #$20
.a16
    lda CHAR_POS_X
    clc
    adc #PLAYER_SPEED
    ; WorldMaxX (WRAM, boot-set) replaces the immediate WORLD_MAX_X here --
    ; see its own declaration comment. "newX <= WorldMaxX" via bcc-or-beq
    ; instead of the old ">= WORLD_MAX_X+1" immediate-compare shape, since
    ; there's no "+1" constant to compare against in WRAM without a second
    ; cell.
    cmp.l WorldMaxX
    bcc Character_PlayFrame__store_x
    beq Character_PlayFrame__store_x
    lda.l WorldMaxX
    bra Character_PlayFrame__store_x
    nop
Character_PlayFrame__left:
    rep #$20
.a16
    lda CHAR_POS_X
    sec
    sbc #PLAYER_SPEED
    cmp #PLAYER_MIN_X
    bcs Character_PlayFrame__store_x
    lda #PLAYER_MIN_X
    bra Character_PlayFrame__store_x
    nop
Character_PlayFrame__hold:
    rep #$20
.a16
    lda CHAR_POS_X
    nop
Character_PlayFrame__store_x:
    sta CHAR_POS_X
    ; Screen-relative X for OAM = world X - camera scroll. Uses Screen_PosX
    ; as of the END of last frame (Core_Screen_Play, which re-eases it from
    ; THIS frame's just-stored CHAR_POS_X, runs later in scpu_main_loop,
    ; after Core_Oop_Play finishes every entity) -- a one-frame lag between
    ; camera and sprite render position that is not visible at this scroll
    ; speed. See plan.md Phase 8.
    sec
    sbc Screen_PosX
    and #$00ff
    sep #$20
.a8
    sta.l OamSetSprite_X

    ; --- Y: held-dpad Up/Down movement, mirroring the X block (same three
    ; CHAR_INPUT_DRIVEN modes, plus the same Phase 4 hit-stun check). ---
    lda CHAR_HIT_STUN
    beq Character_PlayFrame__not_stunned_y
    bra Character_PlayFrame__hold_y
    nop
Character_PlayFrame__not_stunned_y:
    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq Character_PlayFrame__dpad_y
    cmp #2
    beq Character_PlayFrame__ai_y
    bra Character_PlayFrame__hold_y
    nop
Character_PlayFrame__dpad_y:
    lda.l Input_press+1
    and #$0C
    beq Character_PlayFrame__hold_y
    lda.l Input_press+1
    and #$08                       ; bit11 (Up) of the word = bit3 of this byte -- Up wins
    beq Character_PlayFrame__down
    bra Character_PlayFrame__up
    nop
Character_PlayFrame__ai_y:
    ; Same distance-recompute fix as __ai_x -- see its comment.
    lda.l PlayerEntity_PosY
    cmp CHAR_POS_Y
    beq Character_PlayFrame__hold_y
    bcs Character_PlayFrame__ai_y_playerge
    lda CHAR_POS_Y
    sec
    sbc.l PlayerEntity_PosY
    cmp #ANIM_AI_ATTACK_RANGE+1
    bcc Character_PlayFrame__hold_y
    bra Character_PlayFrame__up    ; player is above -- reuse __up
    nop
Character_PlayFrame__ai_y_playerge:
    sec
    sbc CHAR_POS_Y
    cmp #ANIM_AI_ATTACK_RANGE+1
    bcc Character_PlayFrame__hold_y
    bra Character_PlayFrame__down  ; player is below -- reuse __down
    nop
Character_PlayFrame__down:
    lda CHAR_POS_Y
    clc
    adc #PLAYER_SPEED
    cmp #PLAYER_MAX_Y + 1
    bcc Character_PlayFrame__store_y
    lda #PLAYER_MAX_Y
    bra Character_PlayFrame__store_y
    nop
Character_PlayFrame__up:
    lda CHAR_POS_Y
    sec
    sbc #PLAYER_SPEED
    cmp #PLAYER_MIN_Y
    bcs Character_PlayFrame__store_y
    lda #PLAYER_MIN_Y
    bra Character_PlayFrame__store_y
    nop
Character_PlayFrame__hold_y:
    lda CHAR_POS_Y
    nop
Character_PlayFrame__store_y:
    sta CHAR_POS_Y
    sta.l OamSetSprite_Y

    ; --- OBJ base tile: this instance's CHAR_TILE_COLUMN*4 (each entity
    ; occupies a 4-tile-wide column slice of the 16-tile-wide OBJ sheet --
    ; see Msu1_LoadFrame's row-DMA comment for the (tileRow<<4)|tileColumn
    ; hardware layout this must match). Column 0 -> tile 0, matching the
    ; hardcoded value this replaces (plan.md Phase 1b Step 3). ---
    lda CHAR_TILE_COLUMN
    asl a
    asl a
    sta.l OamSetSprite_Tile

    ; --- Attribute byte: priority 3 / palette = CHAR_PALETTE_SLOT (bits 3-1
    ; of the attribute byte -- palette N is $30 | (N<<1); CHAR_PALETTE_SLOT=0
    ; reproduces the old hardcoded $30/$70 exactly) / hflip from
    ; Anim_FacingLeft. Real art faces right by default (FacingLeft=0, no
    ; flip); hardware mirrors the whole 32x64 block when hflip is set,
    ; replacing the old BG2-window tilemap-swap trick entirely. Tested via
    ; its own lda (not ldx/ldy -- index width is still 16-bit here, only
    ; the accumulator was narrowed by the sep #$20 above, so an indexed
    ; read of this 1-byte cell would silently read 2 bytes instead). ---
    lda CHAR_PALETTE_SLOT
    asl a
    ora #$30
    sta.l OamSetSprite_Attr
    lda CHAR_FACING_LEFT
    beq Character_PlayFrame__no_flip
    lda.l OamSetSprite_Attr
    ora #$40                     ; hflip
    sta.l OamSetSprite_Attr
    nop
Character_PlayFrame__no_flip:
    nop

    ; hi-table: size bit set (large = 32x64 under OBSEL mode 6) always;
    ; X-high (bit0) set when this entity's screen-relative X (world X minus
    ; camera scroll, recomputed here rather than carried from
    ; Character_PlayFrame__store_x -- cheaper than threading a scratch
    ; value through the tile/attr block above) is >= 256. Phase 8: this is
    ; the first time this bit has ever needed to be anything but 0.
    rep #$20
.a16
    lda CHAR_POS_X
    sec
    sbc Screen_PosX
    and #$0100
    beq Character_PlayFrame__hi_xlow   ; still 16-bit here -- beq itself is
                                        ; width-independent, only immediate
                                        ; operand SIZING would matter, and
                                        ; there is none on this branch
    sep #$20
.a8
    lda #$03
    bra Character_PlayFrame__hi_store
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_PlayFrame__hi_xlow:
    sep #$20
.a8
    lda #$02
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_PlayFrame__hi_store:
    sta.l OamSetSprite_Hi
    rep #$31
.a16
.i16
    jsr Core_Oam_SetSprite        ; slot 0, cursor -> 4
    rts

; ============================================================================
; Character_HitApply -- plan.md Phase 4: minimal AABB collision + hit
; reaction (SNES-BOR-Engine-Prompt.md's "AABB-only collision... no damage
; system required for PoC"). Called once per entity per frame from
; CharacterEntity_Play, AFTER Anim_Play/Character_PlayFrame have already
; run for this entity this frame, so CHAR_SELECTED reflects this frame's
; real animation state (including a same-frame transition into attack via
; Anim_Play__ai_attack).
;
; Deliberately split into a tiny dispatcher plus two short leaf subroutines
; (Character_HitApply_VsEntity1/VsPlayer) instead of one long block with
; branches spanning the whole overlap test -- an earlier version had a
; couple of `bcs <label 130+ bytes away>` branches that assembled with no
; Poppy error but produced a genuinely broken jump target at runtime
; (confirmed via Mesen2: WRAM state froze completely, including
; Nmi_FrameCounter, the instant the AI's first attack made CHAR_SELECTED
; reach 2 and this code actually ran its overlap test for the first time --
; this file's own CLAUDE.md/poppy_assembler_bugs.md notes call out exactly
; this class of silent branch-range miscompile repeatedly). Keeping every
; relative branch here short and local (all targets within the same ~20-
; line leaf routine) avoids the whole class of bug rather than trying to
; get one more `brl` distance right by hand.
;
; Not attacking (CHAR_SELECTED != 2): just clears CHAR_HIT_APPLIED, so the
; NEXT attack cycle is free to register a hit again -- this is the only
; place that latch is cleared, making it edge-triggered on "just started
; attacking" the same way Anim_Play_Attack's own revert-to-idle already is.
;
; Attacking with CHAR_HIT_APPLIED already set: nothing to do.
;
; Attacking, no hit yet this cycle: CHAR_INPUT_DRIVEN picks which leaf
; routine(s) to run. Mode 1 (I'm the player) tests against EVERY AI slot in
; turn -- VsEntity1, then VsEntity2, then VsEntity3, each a separate jsr'd
; leaf with no shared "already hit someone" re-check between them, so one
; attack can stun more than one overlapping AI in the same frame (that's
; correct -- CHAR_HIT_APPLIED only ever latches THIS entity, the attacker,
; not the targets). Mode 2 (I'm an AI) only ever tests against the player
; (PlayerEntity_PosX/Y/HitStun) -- every AI's target is always slot 0, so
; no AI-vs-AI leaf exists or is needed. Each leaf runs an unsigned per-axis
; abs-difference AABB overlap test (same compare-then-subtract idiom as
; Anim_Play__ai_seek/Character_PlayFrame__ai_x/ai_y's distance checks, just
; compared against the full sprite box width/height instead of
; ANIM_AI_ATTACK_RANGE) and, on overlap, stamps the other entity's
; CHAR_HIT_STUN and this entity's own CHAR_HIT_APPLIED.
;
; Deliberately three separate leaf routines, not one parameterized by a
; runtime-computed target address or one routine inlined three times --
; plan.md Part Two explicitly rules both out: indexed-by-something-other-
; than-X long addressing has its own confirmed Poppy miscompile risk, and
; inlining three ~70-byte copies into one body risks a shared `__done`
; branch exceeding the ±127-byte range, which assembles with NO error and
; hangs the CPU at runtime (this exact bug already cost a session in
; Phase 4 -- see Character_HitApply_VsEntity1's own header history). Three
; short, independent, jsr'd leaves keeps every branch local and safe.
;
; No caller-convention assumed on entry; exits in .a16/.i16 matching
; CharacterEntity_Play's other two calls (Anim_Play/Character_PlayFrame).
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Character_HitApply:
    sep #$20
.a8
    lda CHAR_SELECTED
    cmp #2
    beq Character_HitApply__attacking
    lda #0
    sta CHAR_HIT_APPLIED
    rep #$31
.a16
.i16
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply__attacking:
    ; Reached via the `beq` above, which jumps AROUND the `rep #$31`/.a16/
    ; .i16 a few lines up -- so M is still 1 (8-bit) here at runtime, but
    ; Poppy's linear (non-control-flow-aware) width tracker has already
    ; "seen" that rep textually and would otherwise mis-size `cmp #1` below
    ; as a 3-byte 16-bit form the real 8-bit CPU only half-consumes,
    ; corrupting every byte after it in this routine (confirmed via Mesen2's
    ; disassembler: a phantom `BRK #$F0` right where `cmp #1`'s second byte
    ; should have been, and Character_HitApply_VsEntity1/VsPlayer's own
    ; symbol addresses landing mid-instruction in the real ROM as a result)
    ; -- exact same bug and same fix as Anim_Play__loaded's own copy of this
    ; comment (poppy bug #10). This sep is a harmless no-op at runtime but
    ; re-syncs Poppy's tracker.
    sep #$20
.a8
    lda CHAR_HIT_APPLIED
    bne Character_HitApply__done   ; already landed a hit this attack cycle
    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq Character_HitApply__do_vs_all_ai
    cmp #2
    beq Character_HitApply__do_vs_player
    bra Character_HitApply__done   ; mode 0 (static) -- no defined "other entity"
    nop
Character_HitApply__do_vs_all_ai:
    jsr Character_HitApply_VsEntity1
    jsr Character_HitApply_VsEntity2
    jsr Character_HitApply_VsEntity3
    bra Character_HitApply__done
    nop
Character_HitApply__do_vs_player:
    jsr Character_HitApply_VsPlayer
    nop
Character_HitApply__done:
    rep #$31
.a16
.i16
    rts

; Leaf: overlap-test this entity (own DP window, CHAR_POS_X/Y) against
; Entity #1's fixed-address box; on overlap, stamps Entity1_HitStun and
; this entity's own CHAR_HIT_APPLIED. Entered and exited in .a8 (caller's
; ambient width, unchanged) -- every branch target below is a handful of
; lines away, well inside 8-bit branch range. No caller-convention assumed
; on entry beyond that; doesn't touch X/Y.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Character_HitApply_VsEntity1:
    ; Explicit re-sync, not just a comment this time -- Poppy's linear
    ; tracker will have "seen" Character_HitApply__done's `rep #$31`
    ; (textually above this routine) by the time it reaches here, even
    ; though every real jsr into this routine happens from code that runs
    ; BEFORE that rep executes (same class of bug as the fix a few dozen
    ; lines up; cheap enough to just always pay for at a leaf entry point
    ; rather than re-derive whether it's needed every time this file
    ; changes around it).
    ; Phase 8: dx is 16-bit (CHAR_POS_X/EntityN_PosX are real world X now);
    ; dy stays 8-bit (no vertical scroll) -- __dx_ok resyncs back to .a8.
    rep #$20
.a16
    lda.l Entity1_PosX
    cmp CHAR_POS_X
    bcs Character_HitApply_VsEntity1__dx_otherge
    lda CHAR_POS_X
    sec
    sbc.l Entity1_PosX
    bra Character_HitApply_VsEntity1__dx_have
    nop
Character_HitApply_VsEntity1__dx_otherge:
    rep #$20
.a16
    sec
    sbc CHAR_POS_X
    nop
Character_HitApply_VsEntity1__dx_have:
    cmp #CHAR_HITBOX_W
    bcc Character_HitApply_VsEntity1__dx_ok
    rts                     ; no overlap on X
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity1__dx_ok:
    sep #$20
.a8
    lda.l Entity1_PosY
    cmp CHAR_POS_Y
    bcs Character_HitApply_VsEntity1__dy_otherge
    lda CHAR_POS_Y
    sec
    sbc.l Entity1_PosY
    bra Character_HitApply_VsEntity1__dy_have
    nop
Character_HitApply_VsEntity1__dy_otherge:
    sec
    sbc CHAR_POS_Y
    nop
Character_HitApply_VsEntity1__dy_have:
    cmp #CHAR_HITBOX_H
    bcc Character_HitApply_VsEntity1__dy_ok
    rts                     ; no overlap on Y
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity1__dy_ok:
    lda #CHAR_HIT_STUN_FRAMES
    sta.l Entity1_HitStun
    ; Phase 6: same landed hit also costs the target HP, clamped at 0.
    ; Not a damage system -- nothing reacts to reaching 0; the HUD just
    ; has a real value to draw.
    lda.l Entity1_Hp
    sec
    sbc #CHAR_HP_PER_HIT
    bcs Character_HitApply_VsEntity1__hp_ok
    lda #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity1__hp_ok:
    sta.l Entity1_Hp
    lda #1
    sta CHAR_HIT_APPLIED
    rts

; Leaf: identical shape to Character_HitApply_VsEntity1 above, checked
; against Entity #2's fixed-address box instead. plan.md Phase 5 (scale to
; 4 entities) -- see Character_HitApply__do_vs_all_ai's header comment for
; why this is 3 separate leaves rather than one parameterized/inlined
; routine.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Character_HitApply_VsEntity2:
    ; Same explicit re-sync as Character_HitApply_VsEntity1's entry, same
    ; reason (poppy bug #10 -- Poppy's linear width tracker has "seen" an
    ; earlier `rep` by the time it reaches here even though every real jsr
    ; into this routine runs before that rep executes). Phase 8: dx is
    ; 16-bit, dy stays 8-bit -- see VsEntity1's comment.
    rep #$20
.a16
    lda.l Entity2_PosX
    cmp CHAR_POS_X
    bcs Character_HitApply_VsEntity2__dx_otherge
    lda CHAR_POS_X
    sec
    sbc.l Entity2_PosX
    bra Character_HitApply_VsEntity2__dx_have
    nop
Character_HitApply_VsEntity2__dx_otherge:
    rep #$20
.a16
    sec
    sbc CHAR_POS_X
    nop
Character_HitApply_VsEntity2__dx_have:
    cmp #CHAR_HITBOX_W
    bcc Character_HitApply_VsEntity2__dx_ok
    rts                     ; no overlap on X
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity2__dx_ok:
    sep #$20
.a8
    lda.l Entity2_PosY
    cmp CHAR_POS_Y
    bcs Character_HitApply_VsEntity2__dy_otherge
    lda CHAR_POS_Y
    sec
    sbc.l Entity2_PosY
    bra Character_HitApply_VsEntity2__dy_have
    nop
Character_HitApply_VsEntity2__dy_otherge:
    sec
    sbc CHAR_POS_Y
    nop
Character_HitApply_VsEntity2__dy_have:
    cmp #CHAR_HITBOX_H
    bcc Character_HitApply_VsEntity2__dy_ok
    rts                     ; no overlap on Y
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity2__dy_ok:
    lda #CHAR_HIT_STUN_FRAMES
    sta.l Entity2_HitStun
    ; Phase 6: same landed hit also costs the target HP, clamped at 0.
    ; Not a damage system -- nothing reacts to reaching 0; the HUD just
    ; has a real value to draw.
    lda.l Entity2_Hp
    sec
    sbc #CHAR_HP_PER_HIT
    bcs Character_HitApply_VsEntity2__hp_ok
    lda #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity2__hp_ok:
    sta.l Entity2_Hp
    lda #1
    sta CHAR_HIT_APPLIED
    rts

; Leaf: identical shape again, checked against Entity #3's fixed-address
; box.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Character_HitApply_VsEntity3:
    ; Phase 8: dx is 16-bit, dy stays 8-bit -- see VsEntity1's comment.
    rep #$20
.a16
    lda.l Entity3_PosX
    cmp CHAR_POS_X
    bcs Character_HitApply_VsEntity3__dx_otherge
    lda CHAR_POS_X
    sec
    sbc.l Entity3_PosX
    bra Character_HitApply_VsEntity3__dx_have
    nop
Character_HitApply_VsEntity3__dx_otherge:
    rep #$20
.a16
    sec
    sbc CHAR_POS_X
    nop
Character_HitApply_VsEntity3__dx_have:
    cmp #CHAR_HITBOX_W
    bcc Character_HitApply_VsEntity3__dx_ok
    rts                     ; no overlap on X
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity3__dx_ok:
    sep #$20
.a8
    lda.l Entity3_PosY
    cmp CHAR_POS_Y
    bcs Character_HitApply_VsEntity3__dy_otherge
    lda CHAR_POS_Y
    sec
    sbc.l Entity3_PosY
    bra Character_HitApply_VsEntity3__dy_have
    nop
Character_HitApply_VsEntity3__dy_otherge:
    sec
    sbc CHAR_POS_Y
    nop
Character_HitApply_VsEntity3__dy_have:
    cmp #CHAR_HITBOX_H
    bcc Character_HitApply_VsEntity3__dy_ok
    rts                     ; no overlap on Y
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity3__dy_ok:
    lda #CHAR_HIT_STUN_FRAMES
    sta.l Entity3_HitStun
    ; Phase 6: same landed hit also costs the target HP, clamped at 0.
    ; Not a damage system -- nothing reacts to reaching 0; the HUD just
    ; has a real value to draw.
    lda.l Entity3_Hp
    sec
    sbc #CHAR_HP_PER_HIT
    bcs Character_HitApply_VsEntity3__hp_ok
    lda #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsEntity3__hp_ok:
    sta.l Entity3_Hp
    lda #1
    sta CHAR_HIT_APPLIED
    rts

; Leaf: same shape as Character_HitApply_VsEntity1 above, but checks
; against PlayerEntity_PosX/Y/HitStun instead -- used by the AI (Entity
; #1) when it's the one attacking.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Character_HitApply_VsPlayer:
    ; Same explicit re-sync as Character_HitApply_VsEntity1's entry, same
    ; reason. Phase 8: dx is 16-bit, dy stays 8-bit -- see its comment.
    rep #$20
.a16
    lda.l PlayerEntity_PosX
    cmp CHAR_POS_X
    bcs Character_HitApply_VsPlayer__dx_otherge
    lda CHAR_POS_X
    sec
    sbc.l PlayerEntity_PosX
    bra Character_HitApply_VsPlayer__dx_have
    nop
Character_HitApply_VsPlayer__dx_otherge:
    rep #$20
.a16
    sec
    sbc CHAR_POS_X
    nop
Character_HitApply_VsPlayer__dx_have:
    cmp #CHAR_HITBOX_W
    bcc Character_HitApply_VsPlayer__dx_ok
    rts                     ; no overlap on X
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsPlayer__dx_ok:
    sep #$20
.a8
    lda.l PlayerEntity_PosY
    cmp CHAR_POS_Y
    bcs Character_HitApply_VsPlayer__dy_otherge
    lda CHAR_POS_Y
    sec
    sbc.l PlayerEntity_PosY
    bra Character_HitApply_VsPlayer__dy_have
    nop
Character_HitApply_VsPlayer__dy_otherge:
    sec
    sbc CHAR_POS_Y
    nop
Character_HitApply_VsPlayer__dy_have:
    cmp #CHAR_HITBOX_H
    bcc Character_HitApply_VsPlayer__dy_ok
    rts                     ; no overlap on Y
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsPlayer__dy_ok:
    lda #CHAR_HIT_STUN_FRAMES
    sta.l PlayerEntity_HitStun
    ; Phase 6: same landed hit also costs the target HP, clamped at 0.
    ; Not a damage system -- nothing reacts to reaching 0; the HUD just
    ; has a real value to draw.
    lda.l PlayerEntity_Hp
    sec
    sbc #CHAR_HP_PER_HIT
    bcs Character_HitApply_VsPlayer__hp_ok
    lda #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Character_HitApply_VsPlayer__hp_ok:
    sta.l PlayerEntity_Hp
    lda #1
    sta CHAR_HIT_APPLIED
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
    sta CHAR_IDLE_FCOUNT
    lda.l AnimHeaderStaging+1
    sta CHAR_WALK_FCOUNT
    lda.l AnimHeaderStaging+2
    sta CHAR_ATTACK_FCOUNT
    lda.l AnimHeaderStaging+3
    sta CHAR_IDLE_DELAY
    lda.l AnimHeaderStaging+4
    sta CHAR_WALK_DELAY
    lda.l AnimHeaderStaging+5
    sta CHAR_ATTACK_DELAY

    ; Packer leaves unused slots fully zeroed -- a zero idle_frame_count is
    ; a cheap free validity check (see the plan's Phase 5). Nothing to
    ; compute in that case; leave CharSelect_Loaded=0 and bail.
    lda CHAR_IDLE_FCOUNT
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
    sta CHAR_IDLE_BASE_LO
    sep #$20
.a8
    lda.l AnimHeaderStaging+10
    adc #0                    ; carry-in only, from the 16-bit add above
    sta CHAR_IDLE_BASE_HI

    ; --- walk_base (24-bit) = idle_base + idle_frame_count*768 ---
    ; n*768 = ((n<<1)+n) << 8 -- the <<8 means the product's low byte is
    ; always 0 and its own high byte becomes the 24-bit product's hi8, so no
    ; separate multiply routine is needed (Core_Math_Mul is deliberately
    ; unused here, see the plan -- zero prior call sites anywhere).
    ; AnimHeaderStaging+12..+15 are reserved/unused bytes of the
    ; already-parsed record, reused here as scratch.
    lda CHAR_IDLE_FCOUNT
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
    lda CHAR_IDLE_BASE_LO
    clc
    adc.l AnimHeaderStaging+12
    sta CHAR_WALK_BASE_LO
    sep #$20
.a8
    lda CHAR_IDLE_BASE_HI
    adc.l AnimHeaderStaging+15 ; += product_hi + carry from the 16-bit add
    sta CHAR_WALK_BASE_HI

    ; --- attack_base (24-bit) = walk_base + walk_frame_count*768 ---
    ; Same shift-add pattern as walk_base above.
    lda CHAR_WALK_FCOUNT
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
    lda CHAR_WALK_BASE_LO
    clc
    adc.l AnimHeaderStaging+12
    sta CHAR_ATTACK_BASE_LO
    sep #$20
.a8
    lda CHAR_WALK_BASE_HI
    adc.l AnimHeaderStaging+15
    sta CHAR_ATTACK_BASE_HI

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

    ; --- Enqueue a queued CGRAM DMA of the streamed palette (color 128, 32
    ; bytes = 16 colors -- OBJ palette 0) -- queued (not direct $2122
    ; writes) so the exact
    ; same code path works at boot (flushed synchronously right after this
    ; call via Core_Dma_ProcessQueue, see msu1_done) and at live reselect
    ; (drained normally by Core_Nmi_Play during vblank, see Anim_Play). Same
    ; DmaRequest_* field shape Anim_CommitFrame/Msu1_LoadFrame use, just
    ; DMA_TYPE_CGRAM instead of DMA_TYPE_VRAM. ---
    lda #AnimPaletteStaging
    sta.l DmaRequest_SourceAddrLow
    ; CGRAM byte address $100 = color 128 = OBJ palette 0 base (was color 0/
    ; BG palette 0 -- the character renders via a real OAM sprite now, not a
    ; BG2 window). Palette N lives at $100 + N*32 (plan.md Phase 2's "OBJ
    ; palette budget") -- this instance's CHAR_PALETTE_SLOT (already set by
    ; CharacterEntity_Init before this call, see its header) picks which
    ; slot, matching Character_PlayFrame's attribute-byte palette-select
    ; bits exactly.
    sep #$20
.a8
    lda CHAR_PALETTE_SLOT
    rep #$31
.a16
.i16
    and #$00ff
    asl a
    asl a
    asl a
    asl a
    asl a                       ; x32
    clc
    adc #$0100
    sta.l DmaRequest_TargetAddr
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
    sta CHAR_SELECTED
    sta CHAR_FACING_LEFT        ; 0 = facing right (boot default) -- never
                                  ; explicitly initialized before this fix;
                                  ; harmless under the old BG2-tilemap-swap
                                  ; approach (only read on a facing *change*),
                                  ; but Character_PlayFrame now reads it every
                                  ; frame for the OAM hflip bit, so power-on
                                  ; WRAM garbage here would render the
                                  ; character hflipped from boot until the
                                  ; first Left/Right press -- confirmed via a
                                  ; fresh-boot Mesen2 read (value 35, not 0)
                                  ; before this fix.
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER

    plp
    rep #$31
.a16
.i16
    rts

; ----------------------------------------------------------------------------
; CharacterEntity -- core/oop.pasm class registered at boot. Phase 1a proved
; Core_Oop_Create/Play's indirect dispatch (jsr (ClassInit,x) / jsr
; (OopCurrent,x), each wrapped in a phd/tcd/pld DP-window switch) works with
; a real registered class -- this project had never exercised that path
; before. Phase 1b (this version) moves the Anim_*-derived state Anim_Play/
; Anim_Play_Idle/Walk/Attack/Anim_UpdateFacing/Character_PlayFrame/
; Anim_LoadCharacter touch into this object's own DP window (CHAR_* offsets,
; declared near Anim_FrameIndex's old declaration above) instead of fixed
; bank-$7E globals -- those routines' bodies were edited in place to use
; DP-relative (bare, no .l/.w) addressing for exactly those fields; step 2
; adds CHAR_POS_X/Y (was Player_X/Y) and CHAR_INPUT_DRIVEN, gating
; Character_PlayFrame's dpad read on the latter -- still global/hardcoded
; for now: CharSelect_*, and the palette/tile-column/single-entity
; assumptions (later steps). Only one entity is ever created today, so
; CHAR_INPUT_DRIVEN is hardcoded to 1 here rather than threaded through
; the init param yet -- Phase 2's second, non-input-driven entity is what
; will force that parameter to actually exist.
; ----------------------------------------------------------------------------

; @param a<16-bit>  init parameter: (role<<8)|roster_index (Phase 2/3 -- role
;                    0 = player-controlled defaults (Phase 1b's original
;                    single-entity behavior, unchanged), role 1 = AI-seeking
;                    NPC defaults (own palette/tile-column, CHAR_INPUT_
;                    DRIVEN=2 -- seeks the player and attacks in range, see
;                    Anim_Play/Character_PlayFrame's mode-2 branches).
;                    Entity #0's existing `lda #0` call site is unaffected
;                    (high byte already 0 = role 0).
; @return a<16-bit>  OBJR_NOERR -- Core_Oop_Create schedules the object for
;                     deletion on the next Play pass if this isn't exactly 0
    nop
    nop
CharacterEntity_Init:
    ; Called with DP already switched to this object's window (see Core_
    ; Oop_Create) and .a16/.i16 (its own internal convention at the jsr
    ; (ClassInit,x) call site) -- CharSelect_Index stays a global cell for
    ; now (not yet per-instance, see CHAR_ROSTER_INDEX's own future step),
    ; same as Anim_LoadCharacter always assumed; only the roster index
    ; itself comes from the init param's low byte.
    ;
    ; CHAR_PALETTE_SLOT/CHAR_TILE_COLUMN/CHAR_INPUT_DRIVEN/CHAR_POS_X/Y are
    ; set from the role (init param's high byte) BEFORE calling
    ; Anim_LoadCharacter, not after -- Anim_LoadCharacter's own CGRAM DMA
    ; enqueue reads CHAR_PALETTE_SLOT to pick this instance's palette
    ; target address (plan.md Phase 2's "OBJ palette budget"); getting this
    ; ordering backwards would stream real 16-color palette data to
    ; whatever CHAR_PALETTE_SLOT happened to be at the time (0, from Core_
    ; Oop_Init's clear) regardless of which slot this instance actually
    ; renders with, leaving every non-zero-palette-slot entity pointing its
    ; OAM attribute bits at CGRAM data nothing ever wrote.
    pha                             ; save full (role<<8)|roster_index --
                                    ; need the roster index back after the
                                    ; role branch below consumes A
    xba                             ; role -> low byte
    and #$00ff                      ; role isolated (xba's high byte, now
                                     ; zeroed here, is a scratch copy only --
                                     ; the real roster index is safe on the
                                     ; stack from the pha above)
    beq CharacterEntity_Init__player
    cmp #1
    beq CharacterEntity_Init__role1
    cmp #2
    beq CharacterEntity_Init__role2
    ; --- role 3 (the only remaining valid value -- plan.md Phase 5 caps
    ; this project at exactly 4 entities, roles 0-3) -- falls through, no
    ; cmp/beq needed. AI-seeking, own palette slot 3 / tile-column-slice 3,
    ; starting position placed clear of every other role's spawn box (see
    ; each role's own box below) so the four don't overlap before any of
    ; them start moving. ---
    nop                             ; workaround: Poppy label drift (bug #4).
    nop                             ; Nothing branches here today -- role 3 is
                                    ; reached only by fall-through -- so this
                                    ; guard is inert at runtime. It is here so
                                    ; check_label_drift.py reports clean; a
                                    ; standing known-DRIFTED line is how a real
                                    ; one later gets waved through.
CharacterEntity_Init__role3:
    sep #$20
.a8
    lda #120                        ; [120,152) x [40,104) -- clear of the
    sta CHAR_POS_X                  ; player's [120,152) x [150,214) (same
    stz CHAR_POS_X_HI                ; CHAR_POS_X is .dw (Phase 8, world X) --
                                     ; OopObjRam is never zeroed before Init
                                     ; runs, so the high byte must be zeroed
                                     ; explicitly or it's power-on WRAM
                                     ; garbage. Same fix at every role branch
                                     ; below and the player's, near CHAR_POS_Y.
    lda #40                         ; X, Y separated by 46px, more than the
    sta CHAR_POS_Y                  ; 64px sprite height)
    lda #2
    sta CHAR_INPUT_DRIVEN
    lda #3
    sta CHAR_PALETTE_SLOT
    sta CHAR_TILE_COLUMN
    bra CharacterEntity_Init__load
    nop
CharacterEntity_Init__role2:
    ; --- role 2: AI-seeking, own palette slot 2 / tile-column-slice 2.
    ; [200,232) x [150,214) -- clear of role 1's [40,72) and the player's
    ; [120,152), same Y row, all three separated by >=48px in X. ---
    sep #$20
.a8
    lda #200
    sta CHAR_POS_X
    stz CHAR_POS_X_HI                ; see role 3's comment
    lda #150
    sta CHAR_POS_Y
    lda #2
    sta CHAR_INPUT_DRIVEN
    lda #2
    sta CHAR_PALETTE_SLOT
    sta CHAR_TILE_COLUMN
    bra CharacterEntity_Init__load
    nop
CharacterEntity_Init__role1:
    ; --- role 1: AI-seeking NPC defaults (plan.md Phase 2 introduced this
    ; entity as static/idle-only; Phase 3 repurposes it to seek the player
    ; instead -- CHAR_INPUT_DRIVEN=2, per plan.md Phase 3's own suggested
    ; encoding, read by Anim_Play/Character_PlayFrame's new mode-2 branches.
    ; Own palette/tile-column unchanged from Phase 2, fixed starting
    ; position clearly separated in X from the player's default 120 (32px-
    ; wide sprite: 40-72 vs 120-152, no overlap) so the visual check isn't
    ; confused by overlap even before it starts walking. ---
    sep #$20
.a8
    lda #40
    sta CHAR_POS_X
    stz CHAR_POS_X_HI                ; see role 3's comment
    lda #150
    sta CHAR_POS_Y
    lda #2
    sta CHAR_INPUT_DRIVEN
    lda #1
    sta CHAR_PALETTE_SLOT
    sta CHAR_TILE_COLUMN
    bra CharacterEntity_Init__load
    nop
CharacterEntity_Init__player:
    ; --- role 0: player-controlled defaults (was scpu_boot's inline
    ; Player_X/Y init, moved here in Phase 1b since DP-relative writes are
    ; only correct with this object's window switched in). Palette 0/
    ; column-slice 0 reproduce the exact hardcoded values Phase 1b Step 3
    ; replaced. ---
    sep #$20
.a8
    lda #120                        ; mid-screen; was PLAYER_MIN_X, which
                                     ; sits exactly on the left clamp
    sta CHAR_POS_X
    stz CHAR_POS_X_HI                ; see role 3's comment
    lda #150                        ; matches this build's previous Y-fixed value
    sta CHAR_POS_Y
    lda #1
    sta CHAR_INPUT_DRIVEN
    lda #0
    sta CHAR_PALETTE_SLOT
    sta CHAR_TILE_COLUMN
    nop
CharacterEntity_Init__load:
    ; --- Now recover the roster index (saved on the stack by the pha
    ; above, since the role branch above clobbered A) and do the actual
    ; MSU-1 load, with CHAR_PALETTE_SLOT already correct for its CGRAM DMA
    ; target. Both role branches above leave .a8 (sep #$20) in effect, but
    ; the pha at entry pushed a full 16-bit value (this routine's own
    ; entry width) -- pla must match that width or the stack unbalances by
    ; a byte, so re-assert .a16 first. ---
    rep #$31
.a16
.i16
    pla                              ; recover (role<<8)|roster_index
    and #$00ff                       ; roster index in low byte
    sep #$20
.a8
    sta.l CharSelect_Index

    ; Phase 6: full HP for every role. Set here, after the role branches have
    ; converged, rather than four times over -- every branch reaches this
    ; point and none of them wants a different starting value.
    pha
    lda #CHAR_HP_MAX
    sta CHAR_HP
    pla

    jsr Anim_LoadCharacter        ; sets/restores its own widths, see its
                                   ; header -- writes this object's CHAR_*
                                   ; fields since DP is still switched here
                                   ; -- exits .a16/.i16 on both its rts paths

    rep #$31
.a16
.i16
    lda #OBJR_NOERR
    rts

; Called from Core_Oop_Play, which is in .a16/.i16 throughout its dispatch
; loop -- matches Anim_Play/Character_PlayFrame's own documented entry
; contract, so no width juggling needed here.
; @return a<16-bit>  OBJR_NOERR -- see CharacterEntity_Init; Core_Oop_Play
;                     reads this the same way, right after the dispatch call
    nop
    nop
CharacterEntity_Play:
    jsr Anim_Play
    jsr Character_PlayFrame
    jsr Character_HitApply   ; plan.md Phase 4: AABB hit check, after this
                               ; frame's real animation/position are known
    lda #OBJR_NOERR
    rts

; core/oop.pasm's generic command dispatch (Core_Oop_Call) reaches this via
; an indirect jsr with D already switched to the CALLED object's own window
; (see Core_Oop_Call's phd/tcd) -- CHAR_POS_X/Y below are bare/DP-relative
; and read whichever entity core/screen.pasm is currently focused on, not
; necessarily entity 0. OopCall_CommandId/ResultX/ResultY are fixed $7Exxxx
; addresses (not DP offsets) and stay bare too, matching every other
; reference to them in core/screen.pasm -- this project keeps DBR=$7E
; throughout, so bare absolute addressing to a $7Exxxx symbol is unaffected
; by D having just been switched.
; Entered in .a16/.i16 (Core_Screen__SetTargetPosition's own ambient width
; when it calls Core_Oop_Call) -- redundant resync anyway per poppy bug #10.
; @return carry<bool>  set if OopCall_CommandId was handled
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
CharacterEntity_OnCommand:
    rep #$31
.a16
.i16
    lda OopCall_CommandId
    cmp #SCREEN_CMD_GET_CAMERA_DATA
    beq CharacterEntity_OnCommand__camera
    clc
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
CharacterEntity_OnCommand__camera:
    ; No jump/airborne state on this entity -- always report grounded, which
    ; keeps Y-axis camera easing live (see screen.pasm's header on why
    ; SCREEN_MODE_AIRBORNE freezes it). Harmless since Y never scrolls here.
    lda CHAR_POS_X
    sta OopCall_ResultX
    lda CHAR_POS_Y
    sta OopCall_ResultY
    lda #SCREEN_MODE_GROUNDED
    sec
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
; Bg_LoadScene -- upload the static BG1 backdrop + BG3 HUD tileset from the
; bor.msu v2 BG section (Phase 6).
;
; Called ONCE from scpu_boot, after msu1_done's character loads, while still
; under forced blank. Nothing here runs per frame -- that is deliberate. Every
; per-frame DMA consumer in this codebase is a candidate for re-triggering the
; vblank-overrun bug (see core/nmi.pasm's Core_Nmi_Play header and plan.md
; 2.4's warning); a boot-time one-shot cannot.
;
; Streams MSU-1 -> PPU directly, with NO WRAM staging buffer. Msu1_LoadFrame
; reads into AnimFrameStaging because it runs live and its destination is a
; queued DMA; this runs under forced blank, so the data port can be pumped
; straight into $2118/$2119 (VRAM) and $2122 (CGRAM). That matters: the BG blob
; is ~16KB and there is no free 16KB WRAM staging region.
;
; The MSU-1 data port auto-increments on every $2001 read, so all four regions
; are read back-to-back from ONE seek -- only the PPU destination changes
; between them. Region order here must match pack_msu_roster.py's blob layout
; exactly: CGRAM image, BG1 tilemap, BG1 tiles, BG3 HUD tiles.
;
; VRAM map this establishes:
;   $0000-$3FFF  BG1 tiles (<=1024 4bpp tiles; word $2000 is BG2's char base,
;                but BG2 is off TM and nothing writes there at runtime -- see
;                Phase 8's removal of the old scpu_bg2_blank boot write)
;   $5000-$505F  BG3 HUD tiles (2bpp)
;   $5100-$58FF  BG3 frontpanel streaming-cache tiles (2bpp, Phase 10, see
;                FP_TILES_VRAM_WORD) -- populated by Bg_LoadSceneFp_Streaming,
;                not this routine
;   $6000-$63FF  BG1 tilemap (32x28 of a 32x32 map; $6400-$67FF is free for a
;                future 64x32 map, see BG3_TILEMAP_VRAM_WORD's own comment)
;   $6800-$6BFF  BG3 tilemap (HUD rows 0-3, frontpanel rows 21-27, see
;                STREAM_FP_TILEMAP_ROW_START)
; ============================================================================
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
    nop
    nop
Bg_LoadScene:
    php
    sei

    ; --- VMAIN: increment by one word AFTER the $2119 (high-byte) write ---
    ; Set here rather than relying on the caller: this routine runs from
    ; msu1_done, which is EARLIER in scpu_boot than the $2115 write that the
    ; rest of the boot VRAM code depends on, and scpu_boot's $2100-$213F clear
    ; loop has already zeroed it. With $2115 = $00 the address would advance on
    ; the $2118 write instead, so every high byte would land in the NEXT word
    ; and the whole upload would shear by one byte. (Found exactly that way:
    ; CGRAM streamed correctly while all three VRAM regions mismatched.)
    sep #$20
.a8
    lda #$80
    sta $2115

    rep #$31
.a16
.i16

    ; --- read bg_count ($0A) and bg_directory_offset ($0C-$0F) from the file
    ; header. Seek to 0 first: this runs after Anim_LoadCharacter has left the
    ; data pointer somewhere arbitrary. ---
    sep #$20
.a8
    lda #0
    sta $2000
    sta $2001
    sta $2002
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__hdr_busy:
    lda $2000
    bmi Bg_LoadScene__hdr_busy

    rep #$31
.a16
.i16
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__hdr_read:
    sep #$20
.a8
    lda $2001
    sta.l BgHeaderStaging,x
    rep #$31
.a16
.i16
    inx
    cpx #$0010
    bcc Bg_LoadScene__hdr_read

    ; bg_count == 0 -> no BG section in this .msu; leave VRAM as-is.
    sep #$20
.a8
    lda.l BgHeaderStaging+10
    bne Bg_LoadScene__have_bg
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__have_bg:

    ; --- seek the BG directory (24 bits of the u32 at +12; a .msu never
    ; reaches 16MB) and read record 0 ---
    lda.l BgHeaderStaging+12
    sta $2000
    lda.l BgHeaderStaging+13
    sta $2001
    lda.l BgHeaderStaging+14
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__dir_busy:
    lda $2000
    bmi Bg_LoadScene__dir_busy

    rep #$31
.a16
.i16
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__dir_read:
    sep #$20
.a8
    lda $2001
    sta.l BgRecordStaging,x
    rep #$31
.a16
.i16
    inx
    cpx #$0020
    bcc Bg_LoadScene__dir_read

    ; --- seek this screen's blob (record +12/13/14 -- v3 data_offset moved
    ; from +8 to +12 when the record grew from 16 to 20 bytes; see
    ; pack_msu_roster.py's BG record docstring) ---
    sep #$20
.a8
    lda.l BgRecordStaging+12
    sta $2000
    lda.l BgRecordStaging+13
    sta $2001
    lda.l BgRecordStaging+14
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__blob_busy:
    lda $2000
    bmi Bg_LoadScene__blob_busy

    ; --- region 1: 256-byte CGRAM image -> colors 0-127 ---
    ; Sub-palette 0 (colors 0-3) is the BG3 HUD's; 1-7 are the backdrop's.
    ; See tools/bg_converter/convert_bg.py's PALETTE_OFFSET note on why BG1
    ; cannot use all 8.
    sep #$20
.a8
    lda #0
    sta $2121               ; CGADD = color 0, auto-increments per pair
    rep #$31
.a16
.i16
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__cgram:
    sep #$20
.a8
    lda $2001
    sta $2122
    rep #$31
.a16
.i16
    inx
    cpx #$0100
    bcc Bg_LoadScene__cgram

    ; --- Phase 9 mode dispatch: STREAMING levels use a completely different
    ; region-2/3/4 loading strategy (Bg_LoadScene_Streaming's two-pass column
    ; algorithm, random-access re-seeks) instead of the single-sequential-
    ; burst static path below. width_tiles for a streaming level (up to 688
    ; for warehouse) does not fit the static path's "cmp #64" width dispatch
    ; either -- mode must be checked first, before width. ---
    sep #$20
.a8
    lda.l BgRecordStaging+0     ; mode (u8)
    cmp #BG_MODE_STREAMING
    beq Bg_LoadScene__dispatch_streaming
    rep #$31
.a16
.i16
    bra Bg_LoadScene__dispatch_static
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__dispatch_streaming:
    rep #$31
.a16
.i16
    jsr Bg_LoadScene_Streaming
    ; Phase 10 (plan.md 2.10) step 2b's BG3 frontpanel load does NOT happen
    ; here -- it's called later from scpu_boot, AFTER scpu_bg3_map's
    ; unconditional 1024-word BG3 tilemap clear (that clear runs once
    ; Bg_LoadScene returns; calling Bg_LoadSceneFp_Streaming from inside
    ; Bg_LoadScene, as an earlier version of this code did, meant every FP
    ; tilemap write got silently wiped moments later -- caught by direct
    ; VRAM verification showing all-zero content despite a WRAM write-
    ; counter proving the write loop ran to completion; see plan.md 2.10
    ; Step 2b and scpu_bg3_map's own comment). BgRecordStaging is still
    ; valid at that later point -- nothing between here and there touches it.
    brl Bg_LoadScene__hud_done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__dispatch_static:

    ; --- region 2: BG1 tilemap -> VRAM word $6000 ---
    ; $2115 was set to $80 (word-increment on $2119) at boot and never
    ; changed, so each low/high byte pair advances one word. width_tiles
    ; (bg_record +2) picks narrow (32-wide, 1792B) vs wide (64-wide, two
    ; paged 32x32 screens, 4096B) -- see BG1_TILEMAP_WORDS_WIDE's comment.
    ; NOTE: the matching BG1SC ($60/$61) value is NOT written to
    ; Nmi_Bg1TilemapVram here, even though this is where width_tiles is
    ; known -- Core_Nmi_Init (called later in scpu_boot) unconditionally
    ; zeroes the whole NmiShadow_Start..End block, which would silently wipe
    ; a write made here. BgRecordStaging+2 is re-read after Core_Nmi_Init
    ; instead (see the shadow-init block below, near Nmi_ScreenMode) --
    ; nothing touches that WRAM in between, so it is still valid there.
    sep #$20
.a8
    lda.l BgRecordStaging+2     ; width_tiles (u8)
    cmp #64
    beq Bg_LoadScene__tilemap_wide

    rep #$31
.a16
.i16
    lda #BG1_TILEMAP_VRAM_WORD
    sta $2116
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__tilemap:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    inx
    cpx #BG1_TILEMAP_WORDS
    bcc Bg_LoadScene__tilemap
    bra Bg_LoadScene__tilemap_done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__tilemap_wide:
    sep #$20
.a8

    rep #$31
.a16
.i16
    lda #BG1_TILEMAP_VRAM_WORD
    sta $2116
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__tilemap_w:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    inx
    cpx #BG1_TILEMAP_WORDS_WIDE
    bcc Bg_LoadScene__tilemap_w
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__tilemap_done:
    sep #$20
.a8
    rep #$31
.a16
.i16

    ; --- region 3: bg_tile_count * 32 bytes of BG1 tiles -> VRAM word $0000 ---
    ; Word count = tile_count * 16, computed with four shifts. tile_count is
    ; capped at 512 by the converter and the packer, so this cannot exceed
    ; $2000 words and cannot run into the compositor's BG2 char base.
    lda #BG1_TILES_VRAM_WORD
    sta $2116
    lda.l BgRecordStaging+8     ; bg_tile_count (u16 LE) -- v3 moved from +0 to +8
    and #$03FF
    asl a
    asl a
    asl a
    asl a                       ; * 16 words per 4bpp tile
    tax                         ; X = words remaining, counted DOWN
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__tiles:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    dex
    bne Bg_LoadScene__tiles

    ; --- region 4: hud_tile_count * 16 bytes of BG3 tiles -> VRAM word $5000 ---
    ; Word count = hud_tile_count * 8 (2bpp tiles are 16 bytes = 8 words).
    lda #BG3_TILES_VRAM_WORD
    sta $2116
    sep #$20
.a8
    lda.l BgRecordStaging+5     ; hud_tile_count (u8) -- v3 moved from +4 to +5
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a                       ; * 8 words per 2bpp tile
    tax                         ; X = words remaining, counted DOWN
    beq Bg_LoadScene__hud_done  ; hud_tile_count 0 -> nothing to stream, and
                                 ; dex/bne would otherwise wrap to 65536 words
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__hud:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    dex
    bne Bg_LoadScene__hud
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene__hud_done:

    plp
    rts

; ============================================================================
; Bg_LoadScene_Streaming -- Phase 9 (plan.md 2.7) step 3: boot-time initial-
; viewport load for a BG_MODE_STREAMING level. Called from Bg_LoadScene once
; it has read mode==STREAMING from BgRecordStaging, in place of the static
; path's single-sequential-burst region 2/3/4 load.
;
; Loads exactly STREAM_STAGE_VIEWPORT_COLS (32) columns starting at world
; column 0 into VRAM tilemap columns 0-31 (page A only -- see
; STREAM_STAGE_VIEWPORT_COLS's own comment for why this is boot-only, no
; scrolling yet). For each column:
;   pass 1 -- seek once to this column's tilemap entries (StreamStage_SeekLo/
;             Hi, advanced by StreamStage_ColStrideLo after each column, not
;             recomputed by a multiply) and read all of them in one
;             uninterrupted sequential MSU-1 burst into StreamStage_Entries.
;   pass 2 -- walk the decoded entries. Each tile ID is looked up in
;             StreamCache_Tile2Slot (core/stream_cache.pasm): a hit reuses
;             the already-resident VRAM slot; a miss calls
;             Core_StreamCache_AllocateSlot and then StageColumn_FetchTilePixels
;             to pull that tile's 32 bytes of pixel data from the tiles
;             region into the newly-assigned slot. Either way, a remapped
;             hardware tilemap word (VRAM slot | palette | flip bits, see
;             encode_tilemap_cache_entry's attribute layout) is written to
;             this row's VRAM tilemap word.
; Pass 2's per-tile pixel fetches are why passes 1/2 are split: a fetch does
; its own MSU-1 seek, which would corrupt pass 1's sequential read position
; if interleaved with it instead of run afterward from decoded WRAM data.
;
; Runs under forced blank from Bg_LoadScene's caller (scpu_boot), same as
; the static path -- direct $2118/$2119/$2116 writes, no DMA queue involved
; (see Bg_LoadScene's own header for why that's safe here but not per-frame).
; ============================================================================
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming:
    php
    sei
    rep #$31
.a16
.i16

    ; --- one-time setup: cache tiles_offset (24-bit) and the column stride ---
    lda.l BgRecordStaging+20    ; tiles_offset low16 (record +20/21)
    sta StreamStage_TilesBaseLo
    sep #$20
.a8
    lda.l BgRecordStaging+22    ; tiles_offset byte 2 (byte 3 assumed 0, same
    sta StreamStage_TilesBaseHi ; as every other 24-bit MSU offset in this file)
    rep #$31
.a16
.i16

    ; column_stride_bytes = height_tiles * STREAM_STAGE_ENTRY_BYTES(3), via
    ; two adds -- height_tiles is a runtime u8 (BgRecordStaging+4), small
    ; enough that unrolled addition beats pulling in a general multiply
    ; routine for a single one-time computation.
    sep #$20
.a8
    lda.l BgRecordStaging+4     ; height_tiles (u8)
    rep #$31
.a16
.i16
    and #$00FF
    sta StreamStage_ColStrideLo
    clc
    adc StreamStage_ColStrideLo
    clc
    adc StreamStage_ColStrideLo
    sta StreamStage_ColStrideLo   ; = height_tiles * 3

    ; StreamStage_SeekLo/Hi start at tilemap_offset (record +16/17/18)
    lda.l BgRecordStaging+16
    sta StreamStage_SeekLo
    sep #$20
.a8
    lda.l BgRecordStaging+18
    sta StreamStage_SeekHi
    rep #$31
.a16
.i16

    lda #0
    sta StreamStage_ColIndex
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__col_loop:
    ; --- seek to this column's tilemap entries ---
    sep #$20
.a8
    lda StreamStage_SeekLo
    sta $2000
    lda.l StreamStage_SeekLo+1
    sta $2001
    lda StreamStage_SeekHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__seek_busy:
    lda $2000
    bmi Bg_LoadScene_Streaming__seek_busy

    ; --- pass 1: read this column's height_tiles*3 bytes sequentially into
    ; StreamStage_Entries ---
    rep #$31
.a16
.i16
    ; X (not Y) indexes StreamStage_Entries below -- the 65816 has no
    ; indexed-LONG addressing mode with Y at all (only `addr24,X` exists);
    ; Poppy silently accepts `.l Symbol,y` anyway and falls back to 3-byte
    ; absolute,Y (DBR-relative, and 1 byte short of what it budgeted),
    ; corrupting every following instruction -- see the DBR=0 SA-1 blit
    ; comment near this file's top for this project's first encounter with
    ; the same bug. X counts UP here (compared against ColStrideLo) instead
    ; of down, since X is now the index, not a spare down-counter.
    ldx #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__read_entry:
    sep #$20
.a8
    lda $2001
    sta.l StreamStage_Entries,x
    rep #$31
.a16
.i16
    inx
    ; CPX, like STZ/INC/DEC/STX/STY/ASL/ROL, has NO absolute-LONG addressing
    ; mode on real 65816 -- Poppy accepted `cpx StreamStage_ColStrideLo` (a
    ; bank-$7E symbol) anyway and silently emitted 3-byte absolute (DBR-
    ; relative) instead of erroring. During boot DBR=$00, so this compared X
    ; against garbage at $002383 instead of the real height*3 bound at
    ; $7E2383, and the loop never terminated at 84 -- it ran for thousands of
    ; iterations, scribbling MSU-streamed bytes across the rest of bank $7E
    ; (confirmed via a Mesen write-hook on $7E2501, which caught this exact
    ; STA mid-runaway with X in the thousands). CMP has a long form and is
    ; confirmed safe elsewhere in this file; TXA doesn't touch X, so the loop
    ; index is unaffected.
    txa
    cmp StreamStage_ColStrideLo
    bcc Bg_LoadScene_Streaming__read_entry

    ; --- advance the running seek to the NEXT column, before pass 2 (pass 2
    ; does its own unrelated seeks for tile-pixel fetches) ---
    lda StreamStage_SeekLo
    clc
    adc StreamStage_ColStrideLo
    sta StreamStage_SeekLo
    sep #$20
.a8
    lda StreamStage_SeekHi
    adc #0                       ; += carry from the 16-bit add above (SEP
    sta StreamStage_SeekHi       ; #$20 does not touch the carry flag)
    rep #$31
.a16
.i16

    ; --- pass 2: walk this column's decoded entries ---
    lda #0
    sta StreamStage_RowIndex
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__row_loop:
    ; X (not Y) = row * 3 (entry offset in StreamStage_Entries) -- same
    ; indexed-long-needs-X constraint as the pass-1 read loop above.
    lda StreamStage_RowIndex
    sta StreamStage_TileOffLo     ; scratch use #1 this iteration: row temp
                                    ; only, not read again until the tile-
                                    ; pixel fetch below re-purposes this cell
    asl a
    clc
    adc StreamStage_TileOffLo
    tax

    lda.l StreamStage_Entries,x   ; 16-bit read: tile_id lo+hi in one load
    sta StreamStage_TileId
    inx
    inx                            ; X = row*3 + 2 (attribute byte)
    sep #$20
.a8
    lda.l StreamStage_Entries,x
    sta StreamStage_Attr
    rep #$31
.a16
.i16

    ; --- Tile2Slot lookup (word-indexed by tile_id*2) ---
    lda StreamStage_TileId
    asl a
    tax
    lda.l StreamCache_Tile2Slot,x
    cmp #$FFFF
    bne Bg_LoadScene_Streaming__row_hit
    ; miss -- allocate a slot, then fetch this tile's pixel data
    lda StreamStage_TileId
    tax
    jsr Core_StreamCache_AllocateSlot   ; A = slot; clobbers X,Y (both
    sta StreamStage_Slot                 ; reloaded from WRAM below, so fine)
    jsr StageColumn_FetchTilePixels
    bra Bg_LoadScene_Streaming__row_resolved
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__row_hit:
    sta StreamStage_Slot            ; A still holds Tile2Slot's value: the slot
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__row_resolved:
    rep #$31
.a16
.i16

    ; --- build the remapped hardware tilemap word: slot | (palette<<10) |
    ; (hflip<<14) | (vflip<<15) -- see snes_tiles.encode_tilemap_cache_entry
    ; for the attribute bit layout this decodes. Uses its own dedicated
    ; StreamStage_Word cell -- an earlier version reused StreamStage_TileOffHi
    ; (only 1 byte) as a 16-bit scratch here, which silently overlapped and
    ; corrupted StreamStage_SeekTmpLo instead; see StreamStage_Word's own
    ; declaration comment. ---
    lda StreamStage_Slot
    sta StreamStage_Word

    sep #$20
.a8
    lda StreamStage_Attr
    and #$07                        ; palette bits 0-2
    rep #$31
.a16
.i16
    and #$00FF                      ; zero-extend (A's high byte is stale
                                      ; after the SEP/REP width round-trip)
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                            ; << 10
    ora StreamStage_Word
    sta StreamStage_Word

    sep #$20
.a8
    lda StreamStage_Attr
    and #$08                        ; hflip bit
    rep #$31
.a16
.i16
    and #$00FF
    beq Bg_LoadScene_Streaming__row_no_hflip
    lda StreamStage_Word
    ora #$4000
    sta StreamStage_Word
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__row_no_hflip:

    sep #$20
.a8
    lda StreamStage_Attr
    and #$10                        ; vflip bit
    rep #$31
.a16
.i16
    and #$00FF
    beq Bg_LoadScene_Streaming__row_no_vflip
    lda StreamStage_Word
    ora #$8000
    sta StreamStage_Word
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__row_no_vflip:

    ; --- write to VRAM tilemap: word = BG1_TILEMAP_VRAM_WORD + col + row*32
    ; (page A only -- col is always < 32 in this boot-only load) ---
    lda StreamStage_RowIndex
    asl a
    asl a
    asl a
    asl a
    asl a                            ; row * 32
    clc
    adc StreamStage_ColIndex
    clc
    adc #BG1_TILEMAP_VRAM_WORD
    sta $2116
    ; word write, low byte then high byte -- shift right 8 in A (not a
    ; Symbol+1 byte-split read) to get the high byte, matching this
    ; project's caution around computed-offset operands.
    sep #$20
.a8
    lda StreamStage_Word
    sta $2118
    rep #$31
.a16
.i16
    lda StreamStage_Word
    xba
    sep #$20
.a8
    sta $2119
    rep #$31
.a16
.i16

    lda StreamStage_RowIndex
    inc a
    sta StreamStage_RowIndex
    sep #$20
.a8
    lda.l BgRecordStaging+4
    rep #$31
.a16
.i16
    and #$00FF
    cmp StreamStage_RowIndex
    beq Bg_LoadScene_Streaming__row_done
    brl Bg_LoadScene_Streaming__row_loop
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__row_done:

    ; --- column done: advance to the next one ---
    lda StreamStage_ColIndex
    inc a
    sta StreamStage_ColIndex
    cmp #STREAM_STAGE_VIEWPORT_COLS
    bcs Bg_LoadScene_Streaming__col_finished
    brl Bg_LoadScene_Streaming__col_loop
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__col_finished:
    rep #$31
.a16
.i16

    ; --- Phase 9 step 4: initialize SyncScroll's runtime state now that the
    ; initial viewport (world columns 0..31) is VRAM-resident, identity-
    ; mapped to VRAM columns 0..31 (ring position == world column for this
    ; boot-time load, which never wraps). Cache the BgRecordStaging fields
    ; SyncScroll needs into dedicated cells HERE, while BgRecordStaging is
    ; still fresh -- see StreamScroll_Enabled's own declaration comment for
    ; why it can't just re-read BgRecordStaging later. ---
    lda #0
    sta StreamScroll_StagedLo
    lda #STREAM_STAGE_VIEWPORT_COLS-1
    sta StreamScroll_StagedHi
    lda #0
    sta StreamScroll_RepairCur
    lda #$FFFF
    sta StreamScroll_PendCol
    lda.l BgRecordStaging+2        ; width_tiles (u16 LE)
    sta StreamScroll_WidthTiles
    lda.l BgRecordStaging+16       ; tilemap_offset low16 (u32 LE, record +16..19)
    sta StreamScroll_TilemapOffLo
    sep #$20
.a8
    lda.l BgRecordStaging+18       ; tilemap_offset byte 2
    sta StreamScroll_TilemapOffHi
    lda.l BgRecordStaging+4        ; height_tiles (u8)
    rep #$31
.a16
.i16
    and #$00FF
    sta StreamScroll_HeightTiles
    ; StreamScroll_Enabled is a .db -- a 16-bit sta here would also write
    ; StreamScroll_StagedLo's low byte (the very next cell). Harmless right
    ; now only because StagedLo was already set to 0 above; fix properly
    ; instead of relying on that coincidence.
    sep #$20
.a8
    lda #1
    sta StreamScroll_Enabled
    rep #$31
.a16
.i16

    ; --- HUD tiles: seek to hud_tiles_offset (record +24/25/26) and stream
    ; hud_tile_count*16 bytes, exactly like the static path's region 4 --
    ; needs its own seek since the port position was left wherever the last
    ; tile-pixel fetch (or this column's tilemap read) put it. ---
    sep #$20
.a8
    lda.l BgRecordStaging+24
    sta $2000
    lda.l BgRecordStaging+25
    sta $2001
    lda.l BgRecordStaging+26
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__hud_seek_busy:
    lda $2000
    bmi Bg_LoadScene_Streaming__hud_seek_busy

    rep #$31
.a16
.i16
    lda #BG3_TILES_VRAM_WORD
    sta $2116
    sep #$20
.a8
    lda.l BgRecordStaging+5     ; hud_tile_count (u8)
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a                       ; * 8 words per 2bpp tile
    tax
    beq Bg_LoadScene_Streaming__hud_done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__hud_loop:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    dex
    bne Bg_LoadScene_Streaming__hud_loop
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadScene_Streaming__hud_done:

    plp
    rep #$31
.a16
.i16
    rts

; ----------------------------------------------------------------------
; StageColumn_FetchTilePixels -- fetches one cache-miss tile's 32 bytes of
; pixel data from the tiles region into its newly-assigned VRAM slot.
; @param StreamStage_TileId<16-bit>  the tile ID to fetch
; @param StreamStage_Slot<16-bit>    the VRAM slot Core_StreamCache_AllocateSlot
;                                     just assigned it
; Clobbers A/X. Entry/exit width-agnostic (re-asserts its own widths).
; ----------------------------------------------------------------------
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
StageColumn_FetchTilePixels:
    rep #$31
.a16
.i16
    ; tile_id * 32 via 5 left-shifts of a 24-bit (lo16+hi8) value -- a
    ; compile-time-constant shift count avoids pulling in a general
    ; multiply routine for what's just "multiply by a power of two".
    lda StreamStage_TileId
    sta StreamStage_TileOffLo
    sep #$20
.a8
    lda #0
    sta StreamStage_TileOffHi
    rep #$31
.a16
.i16
    ; ASL/ROL, like STZ/INC/DEC/STX/STY, have NO absolute-LONG addressing
    ; mode on real 65816 -- Poppy accepts `asl Symbol`/`rol Symbol` for a
    ; bank-$7E symbol anyway and silently emits the 2-byte absolute
    ; (DBR-relative) form instead of erroring, which during boot (DBR != $7E)
    ; silently shifts the WRONG memory, leaving StreamStage_TileOffLo/Hi
    ; unchanged. Same bug class CLAUDE.md documents for STZ; this file's
    ; header note on Core_StreamCache_Init already covers STX/STY/INC/DEC,
    ; now confirmed to extend to ASL/ROL too (found via
    ; phase9_stagecolumn_spotcheck.py: every tile_id except 0 fetched wrong
    ; pixel data, because 0<<5 is 0 regardless of whether the shift actually
    ; ran on the right memory). Fix: shift through the accumulator (LDA/STA
    ; both have long forms and are confirmed to auto-select them) instead of
    ; a direct memory read-modify-write.
    ldx #5
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
StageColumn_FetchTilePixels__shift:
    lda StreamStage_TileOffLo
    asl a
    sta StreamStage_TileOffLo
    sep #$20
.a8
    lda StreamStage_TileOffHi
    rol a
    sta StreamStage_TileOffHi
    rep #$31
.a16
.i16
    dex
    bne StageColumn_FetchTilePixels__shift

    ; seek_addr24 = TilesBase24 + TileOff24
    lda StreamStage_TilesBaseLo
    clc
    adc StreamStage_TileOffLo
    sta StreamStage_SeekTmpLo
    sep #$20
.a8
    lda StreamStage_TilesBaseHi
    adc StreamStage_TileOffHi
    sta StreamStage_SeekTmpHi

    lda StreamStage_SeekTmpLo
    sta $2000
    lda.l StreamStage_SeekTmpLo+1
    sta $2001
    lda StreamStage_SeekTmpHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
StageColumn_FetchTilePixels__seek_busy:
    lda $2000
    bmi StageColumn_FetchTilePixels__seek_busy

    ; VMADD = BG1_TILES_VRAM_WORD + slot*16 words (one 4bpp tile = 16 words)
    rep #$31
.a16
.i16
    lda StreamStage_Slot
    asl a
    asl a
    asl a
    asl a
    clc
    adc #BG1_TILES_VRAM_WORD
    sta $2116

    ldx #16                     ; 16 words = 32 bytes, one tile
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
StageColumn_FetchTilePixels__read:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    dex
    bne StageColumn_FetchTilePixels__read

    rts

; ============================================================================
; Bg_LoadSceneFp_Streaming -- Phase 10 (plan.md 2.10) step 2b: boot-time
; initial-viewport load for the BG3 frontpanel layer (fence/rail foreground),
; parallel to Bg_LoadScene_Streaming above but targeting BG3's 2bpp tile/
; tilemap VRAM instead of BG1's 4bpp. Called from Bg_LoadScene right after
; Bg_LoadScene_Streaming, only when BgRecordStaging+28 (fp_offset) is nonzero
; (not every BG record has a packed frontpanel).
;
; The FP blob is self-describing (see pack_msu_roster.py's build_fp_blob): a
; 16-byte header (width_tiles, height_tiles, tile_count, tilemap_offset,
; tiles_offset -- the last two are ABSOLUTE file offsets, already computed in
; Python, same "compute offsets in Python" convention as the BG record's own
; v4 fields) immediately followed by a 32-byte CGRAM palette (4 sub-palettes
; x 4 colors; sub-palette 0 is a zero-filled dummy -- BG3 sub-palette 0
; belongs to the HUD, see HUD_ENTRY_HIGH's comment -- so only the real 24
; bytes, sub-palettes 1-3, get written), then the tilemap, then the tiles.
; Header fields other than tilemap_offset/tiles_offset are read (to advance
; the auto-incrementing MSU port) and discarded -- row count/column stride
; reuse BgRecordStaging+4 (the owning BG's height_tiles), exactly like
; Bg_LoadScene_Streaming already does for BG1, since the converter enforces
; width_tiles match and this level's FP/BG height always agree.
;
; Row placement: STREAM_FP_TILEMAP_ROW_START (measured, see its own comment)
; -- the frontpanel never collides with HUD's BG3 tilemap rows, so this lands
; as a real (not staged/inert) tilemap write in the same step that packed the
; data, rather than needing a separate "resolve the collision" step.
;
; Every written tilemap word gets HUD_ENTRY_HIGH's same priority bit ($2000 --
; BGMODE's BG3-priority bit renders a BG3 tile with this bit set above OBJ in
; Mode 1) -- that's what puts characters behind the fence, the whole point of
; Phase 10. Unconditional on every FP tile, not data-driven.
; ============================================================================
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming:
    php
    sei

    ; --- seek to fp_offset (BgRecordStaging+28, 24-bit: byte 31 assumed 0,
    ; same convention as every other MSU offset in this file) ---
    sep #$20
.a8
    lda.l BgRecordStaging+28
    sta $2000
    lda.l BgRecordStaging+29
    sta $2001
    lda.l BgRecordStaging+30
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__seek_busy:
    lda $2000
    bmi Bg_LoadSceneFp_Streaming__seek_busy

    ; --- read the 16-byte FP header sequentially into StreamStageFp_Entries
    ; (reused as scratch -- BG1's own column loop hasn't started yet, and this
    ; is only 16 of its 84 bytes), then pull tilemap_offset/tiles_offset out
    ; via plain (non-indexed) .l reads, same pattern as the BgRecordStaging+N
    ; reads above. Deliberately NOT built up via Symbol+1 byte-split writes --
    ; see Bg_LoadScene_Streaming's own VRAM-word-write comment on why this
    ; project avoids that on computed operands. ---
    rep #$31
.a16
.i16
    ldx #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__hdr_read:
    sep #$20
.a8
    lda $2001
    sta.l StreamStageFp_Entries,x
    rep #$31
.a16
.i16
    inx
    cpx #16
    bcc Bg_LoadSceneFp_Streaming__hdr_read

    lda.l StreamStageFp_Entries+8     ; tilemap_offset low16 (header +8/9)
    sta StreamStageFp_SeekLo
    ; Step 2c's own preserved copy (see StreamScrollFp_TilemapOffLo's own
    ; declaration comment) folds in the STREAM_FP_TILEMAP_ROW_START*3(63)
    ; row-start byte offset HERE, once, rather than adding it again on every
    ; Core_StreamScrollFp_SeekColumn call. Real bug found via Mesen2 (a
    ; scripted scroll test produced garbage tilemap words that traced back
    ; to a wrong computed seek address): chaining two ADCs into the SAME
    ; 16-bit word (`adc TilemapOffLo` then `adc #63`, no clc between them,
    ; intending the carry to propagate through) does NOT correctly compute
    ; a combined carry-out for a 3-term sum -- the second ADC's carry-out
    ; only reflects whether ITS OWN addition overflowed, not whether the
    ; true mathematical total (product+TilemapOffLo+63) exceeded 65535, so
    ; the byte that carries into the Hi-word add was wrong by exactly the
    ; cases where the two adds' overflow outcomes disagreed. Folding +63
    ; into the preserved base here means the runtime add is a clean 2-term
    ; sum (product + adjusted-base), the same proven single-carry shape
    ; BG1's own Core_StreamScroll_SeekColumn already uses.
    clc
    adc #63
    sta StreamScrollFp_TilemapOffLo
    sep #$20
.a8
    lda.l StreamStageFp_Entries+10    ; tilemap_offset byte 2 (header +10)
    sta StreamStageFp_SeekHi
    adc #0                       ; propagate the 16-bit add's carry above
    sta StreamScrollFp_TilemapOffHi
    rep #$31
.a16
.i16
    lda.l StreamStageFp_Entries+12    ; tiles_offset low16 (header +12/13)
    sta StreamStageFp_TilesBaseLo
    sep #$20
.a8
    lda.l StreamStageFp_Entries+14    ; tiles_offset byte 2 (header +14)
    sta StreamStageFp_TilesBaseHi
    rep #$31
.a16
.i16

    ; --- palette: 8 dummy bytes (sub-palette 0), then 24 real bytes
    ; (sub-palettes 1-3) straight to CGRAM color 4 -- no reseek needed, the
    ; MSU port is already positioned right after the header from the
    ; sequential reads above. ---
    sep #$20
.a8
    lda $2001
    lda $2001
    lda $2001
    lda $2001
    lda $2001
    lda $2001
    lda $2001
    lda $2001

    lda #4
    sta $2121               ; CGADD = color 4 (BG3 sub-palette 1)
    rep #$31
.a16
.i16
    ldx #24
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__pal_loop:
    sep #$20
.a8
    lda $2001
    sta $2122
    rep #$31
.a16
.i16
    dex
    bne Bg_LoadSceneFp_Streaming__pal_loop

    ; --- column_stride_bytes = height_tiles * 3, same one-time computation
    ; as Bg_LoadScene_Streaming (BgRecordStaging+4 reused, see header) ---
    sep #$20
.a8
    lda.l BgRecordStaging+4     ; height_tiles (u8)
    rep #$31
.a16
.i16
    and #$00FF
    sta StreamStageFp_ColStrideLo
    clc
    adc StreamStageFp_ColStrideLo
    clc
    adc StreamStageFp_ColStrideLo
    sta StreamStageFp_ColStrideLo   ; = height_tiles * 3

    lda #0
    sta StreamStageFp_ColIndex
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__col_loop:
    ; --- seek to this column's tilemap entries ---
    sep #$20
.a8
    lda StreamStageFp_SeekLo
    sta $2000
    lda.l StreamStageFp_SeekLo+1
    sta $2001
    lda StreamStageFp_SeekHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__seek_busy2:
    lda $2000
    bmi Bg_LoadSceneFp_Streaming__seek_busy2

    ; --- pass 1: read this column's height_tiles*3 bytes sequentially ---
    rep #$31
.a16
.i16
    ldx #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__read_entry:
    sep #$20
.a8
    lda $2001
    sta.l StreamStageFp_Entries,x
    rep #$31
.a16
.i16
    inx
    txa
    cmp StreamStageFp_ColStrideLo
    bcc Bg_LoadSceneFp_Streaming__read_entry

    ; --- advance the running seek to the NEXT column ---
    lda StreamStageFp_SeekLo
    clc
    adc StreamStageFp_ColStrideLo
    sta StreamStageFp_SeekLo
    sep #$20
.a8
    lda StreamStageFp_SeekHi
    adc #0                       ; += carry from the 16-bit add above
    sta StreamStageFp_SeekHi
    rep #$31
.a16
.i16

    ; --- pass 2: walk this column's decoded entries ---
    lda #0
    sta StreamStageFp_RowIndex
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__row_loop:
    lda StreamStageFp_RowIndex
    sta StreamStageFp_TileOffLo     ; scratch use #1: row temp only, re-purposed
                                    ; by StageColumnFp_FetchTilePixels below
    asl a
    clc
    adc StreamStageFp_TileOffLo
    tax

    lda.l StreamStageFp_Entries,x   ; 16-bit read: tile_id lo+hi in one load
    sta StreamStageFp_TileId
    inx
    inx                            ; X = row*3 + 2 (attribute byte)
    sep #$20
.a8
    lda.l StreamStageFp_Entries,x
    sta StreamStageFp_Attr
    rep #$31
.a16
.i16

    ; --- Tile2Slot lookup (FP's own cache table, word-indexed by tile_id*2) ---
    lda StreamStageFp_TileId
    asl a
    tax
    lda.l StreamCacheFp_Tile2Slot,x
    cmp #$FFFF
    bne Bg_LoadSceneFp_Streaming__row_hit
    ; miss -- allocate a slot, then fetch this tile's pixel data
    lda StreamStageFp_TileId
    tax
    jsr Core_StreamCacheFp_AllocateSlot   ; A = slot; clobbers X,Y
    sta StreamStageFp_Slot
    jsr StageColumnFp_FetchTilePixels
    bra Bg_LoadSceneFp_Streaming__row_resolved
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__row_hit:
    sta StreamStageFp_Slot            ; A still holds Tile2Slot's value: the slot
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__row_resolved:
    rep #$31
.a16
.i16

    ; --- build the remapped hardware tilemap word: slot | (palette<<10) |
    ; (hflip<<14) | (vflip<<15) -- see snes_tiles.encode_tilemap_cache_entry
    ; for the attribute bit layout this decodes. ---
    lda StreamStageFp_Slot
    clc
    adc #FP_TILE_INDEX_BASE        ; slot -> PPU character number (see
                                     ; FP_TILE_INDEX_BASE's definition)
    sta StreamStageFp_Word

    sep #$20
.a8
    lda StreamStageFp_Attr
    and #$07                        ; palette bits 0-2 (already absolute,
                                      ; 1-3 -- see PALETTE_OFFSET in
                                      ; convert_frontpanel.py)
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                            ; << 10
    ora StreamStageFp_Word
    sta StreamStageFp_Word

    sep #$20
.a8
    lda StreamStageFp_Attr
    and #$08                        ; hflip bit
    rep #$31
.a16
.i16
    and #$00FF
    beq Bg_LoadSceneFp_Streaming__row_no_hflip
    lda StreamStageFp_Word
    ora #$4000
    sta StreamStageFp_Word
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__row_no_hflip:

    sep #$20
.a8
    lda StreamStageFp_Attr
    and #$10                        ; vflip bit
    rep #$31
.a16
.i16
    and #$00FF
    beq Bg_LoadSceneFp_Streaming__row_no_vflip
    lda StreamStageFp_Word
    ora #$8000
    sta StreamStageFp_Word
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__row_no_vflip:

    ; --- priority bit: same as HUD_ENTRY_HIGH -- renders this FP tile above
    ; OBJ under BGMODE's BG3-priority bit (see this routine's header). ---
    lda StreamStageFp_Word
    ora #$2000
    sta StreamStageFp_Word

    ; --- write to VRAM tilemap: word = BG3_TILEMAP_VRAM_WORD + row*32 + col.
    ; row is written DIRECTLY (0..height_tiles-1), same convention as
    ; Bg_LoadScene_Streaming's own BG1 write -- STREAM_FP_TILEMAP_ROW_START
    ; is NOT an offset added here: the converter's tilemap.bin already
    ; encodes the full height_tiles rows, with rows 0..ROW_START-1 baked in
    ; as blank (tile id 0) entries. Rows 0-3 of this range do briefly
    ; overwrite the HUD's own BG3 tilemap rows during this boot-time call --
    ; harmless, since HudDirty starts nonzero and Hud_Play's first
    ; scpu_main_loop call unconditionally rebuilds them before any frame is
    ; ever displayed (forced blank is still on here; see this routine's
    ; header). Adding ROW_START here was a real bug caught by direct VRAM
    ; verification (see plan.md 2.10 Step 2b): it wrote rows 21-48, past the
    ; tilemap's 32-row extent. ---
    lda StreamStageFp_RowIndex
    asl a
    asl a
    asl a
    asl a
    asl a                            ; row * 32
    clc
    adc StreamStageFp_ColIndex
    clc
    adc #BG3_TILEMAP_VRAM_WORD
    sta $2116
    sep #$20
.a8
    lda StreamStageFp_Word
    sta $2118
    rep #$31
.a16
.i16
    lda StreamStageFp_Word
    xba
    sep #$20
.a8
    sta $2119
    rep #$31
.a16
.i16

    lda StreamStageFp_RowIndex
    inc a
    sta StreamStageFp_RowIndex
    sep #$20
.a8
    lda.l BgRecordStaging+4
    rep #$31
.a16
.i16
    and #$00FF
    cmp StreamStageFp_RowIndex
    beq Bg_LoadSceneFp_Streaming__row_done
    brl Bg_LoadSceneFp_Streaming__row_loop
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__row_done:

    ; --- column done: advance to the next one ---
    lda StreamStageFp_ColIndex
    inc a
    sta StreamStageFp_ColIndex
    cmp #STREAM_STAGE_VIEWPORT_COLS
    bcs Bg_LoadSceneFp_Streaming__col_finished
    brl Bg_LoadSceneFp_Streaming__col_loop
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Bg_LoadSceneFp_Streaming__col_finished:
    rep #$31
.a16
.i16

    ; --- Phase 10 Step 2c: initialize the runtime resolver's state now that
    ; the initial viewport (world columns 0..31) is VRAM-resident,
    ; identity-mapped to BG3 tilemap columns 0..31 (vram_col == world_col
    ; for this boot-time load, which never wraps) -- same shape as BG1's own
    ; Phase 9 step 4 init block (Bg_LoadScene_Streaming__col_finished, see
    ; its comment for the precedent this mirrors). ---
    lda #0
    sta StreamScrollFp_StagedLo
    sta StreamScrollFp_RepairCur
    lda #STREAM_STAGE_VIEWPORT_COLS-1
    sta StreamScrollFp_StagedHi
    lda #$FFFF
    sta StreamScrollFp_PendCol
    sep #$20
.a8
    lda #1
    sta StreamScrollFp_Enabled
    rep #$31
.a16
.i16

    plp
    rts

; ----------------------------------------------------------------------
; StageColumnFp_FetchTilePixels -- StageColumn_FetchTilePixels's twin for the
; FP cache: 2bpp tiles (16 bytes/8 words, not 32 bytes/16 words) fetched into
; FP_TILES_VRAM_WORD-based slots instead of BG1_TILES_VRAM_WORD ones. The
; *8-not-*16 shift count is the one line a copy-paste of the BG1 routine
; would get silently wrong.
; @param StreamStageFp_TileId<16-bit>  the tile ID to fetch
; @param StreamStageFp_Slot<16-bit>    the VRAM slot just assigned to it
; Clobbers A/X. Entry/exit width-agnostic (re-asserts its own widths).
; ----------------------------------------------------------------------
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
StageColumnFp_FetchTilePixels:
    rep #$31
.a16
.i16
    ; tile_id * 16 (2bpp tile = 16 bytes) via 4 left-shifts, shift-through-
    ; accumulator (ASL/ROL have no absolute-long addressing mode -- see
    ; StageColumn_FetchTilePixels's own comment).
    lda StreamStageFp_TileId
    sta StreamStageFp_TileOffLo
    sep #$20
.a8
    lda #0
    sta StreamStageFp_TileOffHi
    rep #$31
.a16
.i16
    ldx #4
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
StageColumnFp_FetchTilePixels__shift:
    lda StreamStageFp_TileOffLo
    asl a
    sta StreamStageFp_TileOffLo
    sep #$20
.a8
    lda StreamStageFp_TileOffHi
    rol a
    sta StreamStageFp_TileOffHi
    rep #$31
.a16
.i16
    dex
    bne StageColumnFp_FetchTilePixels__shift

    ; seek_addr24 = TilesBase24 + TileOff24
    lda StreamStageFp_TilesBaseLo
    clc
    adc StreamStageFp_TileOffLo
    sta StreamStageFp_SeekTmpLo
    sep #$20
.a8
    lda StreamStageFp_TilesBaseHi
    adc StreamStageFp_TileOffHi
    sta StreamStageFp_SeekTmpHi

    lda StreamStageFp_SeekTmpLo
    sta $2000
    lda.l StreamStageFp_SeekTmpLo+1
    sta $2001
    lda StreamStageFp_SeekTmpHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
StageColumnFp_FetchTilePixels__seek_busy:
    lda $2000
    bmi StageColumnFp_FetchTilePixels__seek_busy

    ; VMADD = FP_TILES_VRAM_WORD + slot*8 words (one 2bpp tile = 8 words)
    rep #$31
.a16
.i16
    lda StreamStageFp_Slot
    asl a
    asl a
    asl a
    clc
    adc #FP_TILES_VRAM_WORD
    sta $2116

    ldx #8                      ; 8 words = 16 bytes, one 2bpp tile
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
StageColumnFp_FetchTilePixels__read:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    dex
    bne StageColumnFp_FetchTilePixels__read

    rts

; ============================================================================
; Phase 9 step 4: SyncScroll -- keeps the VRAM ring buffer in sync with
; wherever the camera (already eased/committed by Core_Screen_Play, see
; scpu_main_loop) currently is. Ported (redesigned for snes-bor's DMA-queue
; budget, not a literal port) from SNES-SuperMonkeyIsland's watermark +
; repair-sweep + stamp-walk mechanism -- see plan.md Phase 9's Design
; section. No-ops entirely for a BG_MODE_STATIC level (StreamScroll_Enabled
; stays 0, set only by Bg_LoadScene_Streaming).
; ============================================================================

; Seeks the MSU-1 port to world column X's tilemap cache entries and reads
; them sequentially into StreamStage_Entries -- like Bg_LoadScene_Streaming's
; pass 1, but for an ARBITRARY column (the watermark can jump either
; direction, so a running add from the previous column doesn't work here)
; via a real multiply: seek = tilemap_offset24 + world_col * ColStrideLo.
; @param X<16-bit>  world column index
; Clobbers A, X, Y.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_SeekColumn:
    php
    sei
    rep #$31
.a16
.i16
    ; LDX has no absolute-LONG addressing mode on real 65816 (only LDA does)
    ; -- `ldx StreamStage_ColStrideLo` (a bank-$7E symbol) used to sit here,
    ; and Poppy silently accepted it, emitting a DBR-relative 2-byte
    ; absolute instead of erroring (same failure class CLAUDE.md's Poppy
    ; checklist documents for CPX -- see Bg_LoadScene_Streaming's own read
    ; loop comment). This routine runs with DBR=0 (SEI'd, called from
    ; scpu_main_loop, same context as everything else that needs .l here),
    ; so that LDX read $002383 instead of the real ColStrideLo at $7E2383,
    ; multiplying world_col by garbage and seeking to nonsense -- confirmed
    ; via entries_probe.py: computed seek 0x1F6D1 vs the correct 0x77EC for
    ; world_col=11, and StreamStage_Entries full of garbage tile ids/attrs
    ; (every sampled row a mismatch) as a direct result. Load via LDA.l
    ; (which does support long addressing) into a scratch cell, then TAX.
    phx                          ; save world_col (the @param X)
    lda.l StreamStage_ColStrideLo
    tax
    pla                           ; world_col back into A
    jsr Core_Math_Mul            ; a = product lo16, x = product hi16
    pha
    txa
    sta StreamScroll_ProdHi
    pla

    clc
    adc StreamScroll_TilemapOffLo
    sta StreamStage_SeekLo

    sep #$20
.a8
    lda StreamScroll_TilemapOffHi
    adc StreamScroll_ProdHi        ; carry survives the SEP above unaffected
    sta StreamStage_SeekHi

    lda StreamStage_SeekLo
    sta $2000
    lda.l StreamStage_SeekLo+1
    sta $2001
    lda StreamStage_SeekHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_SeekColumn__seek_busy:
    lda $2000
    bmi Core_StreamScroll_SeekColumn__seek_busy

    rep #$31
.a16
.i16
    ldx #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_SeekColumn__read_entry:
    sep #$20
.a8
    lda $2001
    sta.l StreamStage_Entries,x
    rep #$31
.a16
.i16
    inx
    txa
    cmp StreamStage_ColStrideLo
    bcc Core_StreamScroll_SeekColumn__read_entry

    plp
    rep #$31
.a16
.i16
    rts

; Like StageColumn_FetchTilePixels, but stages the tile's 32 bytes into
; StreamScroll_TileBufN (WRAM) instead of writing the VRAM port directly --
; runtime-safe, because Core_Dma_Enqueue needs a WRAM/ROM source address and
; a direct port write here (screen ON, not forced blank) would corrupt the
; frame the PPU is mid-drawing.
; @param StreamStage_TileId<16-bit>  the tile ID to fetch
; Clobbers A/X.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_FetchTileToBuffer:
    rep #$31
.a16
.i16
    lda StreamStage_TileId
    sta StreamStage_TileOffLo
    sep #$20
.a8
    lda #0
    sta StreamStage_TileOffHi
    rep #$31
.a16
.i16
    ldx #5
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_FetchTileToBuffer__shift:
    lda StreamStage_TileOffLo
    asl a
    sta StreamStage_TileOffLo
    sep #$20
.a8
    lda StreamStage_TileOffHi
    rol a
    sta StreamStage_TileOffHi
    rep #$31
.a16
.i16
    dex
    bne Core_StreamScroll_FetchTileToBuffer__shift

    lda StreamStage_TilesBaseLo
    clc
    adc StreamStage_TileOffLo
    sta StreamStage_SeekTmpLo
    sep #$20
.a8
    lda StreamStage_TilesBaseHi
    adc StreamStage_TileOffHi
    sta StreamStage_SeekTmpHi

    lda StreamStage_SeekTmpLo
    sta $2000
    lda.l StreamStage_SeekTmpLo+1
    sta $2001
    lda StreamStage_SeekTmpHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_FetchTileToBuffer__seek_busy:
    lda $2000
    bmi Core_StreamScroll_FetchTileToBuffer__seek_busy

    rep #$31
.a16
.i16
    ; Which of the STREAM_SCROLL_BUDGET_MAX per-call slots to fill -- see
    ; StreamScroll_FetchBufSel's declaration comment for why this can't be a
    ; single shared buffer. X = FetchBufSel*32, the slot's byte offset from
    ; StreamScroll_TileBufN; Y is the plain 0..31 byte counter.
    sep #$20
.a8
    lda StreamScroll_FetchBufSel
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a                   ; A = FetchBufSel * 32
    tax
    ldy #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_FetchTileToBuffer__read:
    sep #$20
.a8
    lda $2001
    sta.l StreamScroll_TileBufN,x
    rep #$31
.a16
.i16
    inx
    iny
    cpy #32
    bcc Core_StreamScroll_FetchTileToBuffer__read

    rts

; Picks which world column to (re)stage this tick: extends the resident
; window toward the camera if the desired range has fallen outside
; [StagedLo, StagedHi] (watermark), otherwise re-syncs one column from a
; cycling repair-sweep cursor (protects against a stale tile surviving an
; eviction + scroll reversal).
; @return A<16-bit>  world column to stage this tick
; Clobbers A, X.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_PickColumn:
    rep #$31
.a16
.i16
    lda Screen_PosX
    lsr a
    lsr a
    lsr a                         ; cameraCol = Screen_PosX >> 3
    sta StreamScroll_CameraCol

    sec
    sbc #STREAM_SCROLL_PREFETCH
    bcs Core_StreamScroll_PickColumn__lo_ok
    lda #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_PickColumn__lo_ok:
    sta StreamScroll_DesiredLo

    ; NEWLY FOUND POPPY BUG (add to poppy_assembler_bugs.md): a single `adc
    ; #(A-1+B)` immediate combining two symbolic constants via subtraction
    ; THEN addition silently assembled to ZERO BYTES -- confirmed via raw
    ; main.bin comparison, not just disassembly text (CLC was immediately
    ; followed by PHA with no ADC opcode in between at all). This made
    ; DesiredHi = CameraCol (the missing +35 dropped entirely) instead of
    ; CameraCol+35, silently disabling the prefetch margin -- dormant for
    ; a long time because ordinary continuous camera movement still
    ; eventually made raw CameraCol alone exceed StagedHi (just later, with
    ; zero margin instead of the intended 4), until
    ; Core_StreamScroll_ClampCamera's introduction made that impossible
    ; (camera pinned so CameraCol can never exceed StagedHi at all),
    ; deadlocking SyncScroll's resolver permanently at its initial
    ; boot-load window. Split into two single-term ADCs instead, matching
    ; the pattern Core_StreamScroll_ClampCamera already uses successfully
    ; (confirmed correct via the same raw-byte check).
    lda StreamScroll_CameraCol
    clc
    adc #(STREAM_STAGE_VIEWPORT_COLS-1)
    clc
    adc #STREAM_SCROLL_PREFETCH
    ; `ldx StreamScroll_WidthTiles` used to sit here -- same LDX-has-no-
    ; absolute-long-addressing bug as Core_StreamScroll_SeekColumn (see its
    ; header comment for the full mechanism); it read garbage from bank 0
    ; instead of the real width at $7E252C, which is why desired_hi was
    ; observed clamped to a small garbage value instead of width-1. Preserve
    ; desired_hi_raw on the stack while computing width-1 via LDA.l.
    pha
    lda.l StreamScroll_WidthTiles
    dec a
    tax
    pla
    jsr Core_Math_Min              ; a = min(desired_hi_raw, width-1)
    sta StreamScroll_DesiredHi

    lda StreamScroll_DesiredLo
    cmp StreamScroll_StagedLo
    bcs Core_StreamScroll_PickColumn__check_hi
    lda StreamScroll_StagedLo
    dec a
    rts                             ; extend left
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_PickColumn__check_hi:
    lda StreamScroll_DesiredHi
    cmp StreamScroll_StagedHi
    beq Core_StreamScroll_PickColumn__repair
    bcc Core_StreamScroll_PickColumn__repair
    lda StreamScroll_StagedHi
    inc a
    rts                             ; extend right
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_PickColumn__repair:
    ; clamp the cursor into [DesiredLo, DesiredHi] -- NOT [StagedLo,
    ; StagedHi] -- so the repair sweep only ever revisits the camera-
    ; relevant window (viewport +/- STREAM_SCROLL_PREFETCH), not the whole
    ; wider ring retained up to the VRAM ring's 64-column cap. Reaching
    ; this label already proves DesiredLo>=StagedLo and DesiredHi<=StagedHi
    ; this call (both extend checks above fell through), so this is always
    ; a subset of the old clamp range, never out of bounds.
    ;
    ; Root cause this fixes (Phase 9 SyncScroll "pending_repair never
    ; converges" investigation): the retained [StagedLo,StagedHi] window
    ; grows to the full 64-column VRAM ring capacity, but the level's
    ; distinct-tile count over any 64-column span (up to 1568 measured on
    ; the warehouse asset) routinely exceeds the 1022-slot cache, which is
    ; mathematically impossible to keep fully resident no matter the
    ; eviction/protect-window policy. The round-robin repair cursor used to
    ; spend equal effort on those doomed-to-thrash far columns as on the
    ; ~40-column actually-desired window, so eviction pressure from
    ; resolving neglected trailing columns kept knocking newly-resolved,
    ; currently-VISIBLE columns back out of cache (confirmed via
    ; tools/verify's pending-mismatch histogram: solid blocks of 100%-
    ; pending columns inside the live viewport, not just the stale tail
    ; near StagedLo). The desired window's own worst-case distinct-tile
    ; count (measured 872 for the bare 32-col viewport, up to ~1080 for the
    ; full 40-col prefetch margin at some level positions) fits the 1022
    ; slot budget far more reliably, so narrowing repair's scope to it lets
    ; the sweep actually converge instead of chasing a permanently
    ; oversubscribed range.
    lda StreamScroll_RepairCur
    cmp StreamScroll_DesiredLo
    bcs Core_StreamScroll_PickColumn__repair_lo_ok
    lda StreamScroll_DesiredLo
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_PickColumn__repair_lo_ok:
    cmp StreamScroll_DesiredHi
    bcc Core_StreamScroll_PickColumn__repair_hi_ok
    beq Core_StreamScroll_PickColumn__repair_hi_ok
    lda StreamScroll_DesiredHi
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_PickColumn__repair_hi_ok:
    pha
    inc a
    cmp StreamScroll_DesiredHi
    bcc Core_StreamScroll_PickColumn__repair_adv_ok
    lda StreamScroll_DesiredLo
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_PickColumn__repair_adv_ok:
    sta StreamScroll_RepairCur
    pla
    rts

; Resolves StreamScroll_PendCol's rows starting at StreamScroll_PendTile,
; budget-capped at 2 new DMA enqueues (StreamScroll_Budget) per call. Cache
; hits cost no budget and resolve eagerly within one call; a cache miss
; beyond budget (or a full DMA queue) stops the loop exactly at that row so
; a later eligible call resumes it -- AllocateSlot is only invoked for a row
; actually processed this call, so nothing double-allocates across resumes.
; @return carry<bool>  set if PendCol fully committed (its DMA enqueued,
;         PendCol reset to $FFFF); clear if still in progress
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows:
    rep #$31
.a16
.i16
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__row:
    lda StreamScroll_PendTile
    cmp StreamScroll_HeightTiles
    bcc Core_StreamScroll_ResolveRows__have_row
    brl Core_StreamScroll_ResolveRows__commit
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__have_row:

    lda StreamScroll_PendTile
    sta StreamStage_TileOffLo     ; row temp only (matches boot's own reuse)
    asl a
    clc
    adc StreamStage_TileOffLo
    tax                            ; x = row*3

    lda.l StreamStage_Entries,x
    sta StreamStage_TileId
    inx
    inx
    sep #$20
.a8
    lda.l StreamStage_Entries,x
    sta StreamStage_Attr
    rep #$31
.a16
.i16

    lda StreamStage_TileId
    asl a
    tax
    lda.l StreamCache_Tile2Slot,x
    cmp #$FFFF
    beq Core_StreamScroll_ResolveRows__is_miss
    ; __hit is too far below for a plain BNE -- Poppy assembles an
    ; out-of-range conditional branch with NO error and it hangs the CPU at
    ; runtime (see CLAUDE.md's Poppy checklist); invert + brl instead.
    brl Core_StreamScroll_ResolveRows__hit
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__is_miss:
    ; StreamScroll_Budget is a .db -- a 16-bit lda/cmp here would silently
    ; fold whatever byte follows it in WRAM into A's high byte, corrupting
    ; the comparison. Decide the branch in 8-bit mode (like
    ; Core_StreamCache_AllocateSlot's own protection-window check does, for
    ; the same "rep #$31 clears carry" reason -- see that routine's header
    ; comment) instead of switching back to 16-bit first.
    sep #$20
.a8
    lda StreamScroll_Budget
    cmp #STREAM_SCROLL_BUDGET_MAX
    bcc Core_StreamScroll_ResolveRows__miss_ok
    rep #$31
.a16
.i16
    clc
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__miss_ok:
    ; Must not commit Core_StreamCache_AllocateSlot's Tile2Slot/Slot2Tile
    ; mapping unless Core_Dma_Enqueue below is guaranteed to succeed -- see
    ; Core_Dma_HasFreeSlot's header for why (a committed-but-never-DMA'd
    ; slot corrupts silently and permanently). Check first, bail like a
    ; normal queue-full retry if not.
    jsr Core_Dma_HasFreeSlot
    bcs Core_StreamScroll_ResolveRows__queue_ok
    rep #$31
.a16
.i16
    clc
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__queue_ok:
    ; Still 8-bit accumulator here (from the Budget cmp above) -- capture
    ; Budget's CURRENT value (0 for this call's 1st miss, 1 for its 2nd,
    ; since Budget is only incremented AFTER a successful enqueue below) as
    ; the double-buffer selector, before FetchTileToBuffer uses it. See
    ; StreamScroll_FetchBufSel's declaration comment for why this buffer
    ; can't be shared between the two possible per-call misses.
    sep #$20
.a8
    lda StreamScroll_Budget
    sta StreamScroll_FetchBufSel
    rep #$31
.a16
.i16
    lda StreamStage_TileId
    tax
    jsr Core_StreamCache_AllocateSlot
    sta StreamStage_Slot
    jsr Core_StreamScroll_FetchTileToBuffer

    lda StreamScroll_FetchBufSel
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a                   ; A = FetchBufSel * 32
    clc
    adc #StreamScroll_TileBufN
    sta DmaRequest_SourceAddrLow
    sep #$20
.a8
    lda #$7F
    sta DmaRequest_SourceBank
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__src_done:
    rep #$31
.a16
.i16
    lda StreamStage_Slot
    asl a
    asl a
    asl a
    asl a                          ; slot*16 words
    clc
    adc #BG1_TILES_VRAM_WORD
    asl a                          ; word address -> byte address
    sta DmaRequest_TargetAddr
    lda #32
    sta DmaRequest_Length
    sep #$20
.a8
    lda #DMA_TYPE_VRAM
    sta DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsr Core_Dma_Enqueue
    bcs Core_StreamScroll_ResolveRows__enqueued
    clc                             ; queue full -- retry this row later
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__enqueued:
    sep #$20
.a8
    lda StreamScroll_Budget
    inc a
    sta StreamScroll_Budget
    rep #$31
.a16
.i16
    brl Core_StreamScroll_ResolveRows__resolved
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__hit:
    sta StreamStage_Slot
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__resolved:

    ; --- build the remapped hw tilemap word (identical bit layout to
    ; Bg_LoadScene_Streaming's row loop -- see its comment for the encoding
    ; this decodes) ---
    lda StreamStage_Slot
    sta StreamStage_Word

    sep #$20
.a8
    lda StreamStage_Attr
    and #$07
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                            ; << 10
    ora StreamStage_Word
    sta StreamStage_Word

    sep #$20
.a8
    lda StreamStage_Attr
    and #$08
    rep #$31
.a16
.i16
    and #$00FF
    beq Core_StreamScroll_ResolveRows__no_hflip
    lda StreamStage_Word
    ora #$4000
    sta StreamStage_Word
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__no_hflip:

    sep #$20
.a8
    lda StreamStage_Attr
    and #$10
    rep #$31
.a16
.i16
    and #$00FF
    beq Core_StreamScroll_ResolveRows__no_vflip
    lda StreamStage_Word
    ora #$8000
    sta StreamStage_Word
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__no_vflip:

    ; --- store into StreamScroll_ColBuf[row] (word-indexed) ---
    lda StreamScroll_PendTile
    asl a
    tax
    lda StreamStage_Word
    sta.l StreamScroll_ColBuf,x

    lda StreamScroll_PendTile
    inc a
    sta StreamScroll_PendTile
    brl Core_StreamScroll_ResolveRows__row
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__commit:
    ; every row resolved -- hand ColBuf (2*height_tiles bytes) off to
    ; Core_Nmi_Play's forced-blank column-write block, which writes it into
    ; VRAM at its ring position via direct $2116/$2118/$2119 port writes (NOT
    ; a DMA -- see StreamScroll_ColPending's declaration comment for why).
    ; vram_col = world_col & 63 (ring is 64 columns == two concatenated 32x32
    ; pages); bit 5 selects page A ($6000-$63FF) vs page B ($6400-$67FF, see
    ; BG1_TILEMAP_WORDS_WIDE's own comment), bits 0-4 are the column within
    ; that page.
    lda StreamScroll_ColPending
    and #$00FF
    beq Core_StreamScroll_ResolveRows__col_free
    sec                                ; NMI hasn't drained the previous
    rts                                ; column yet -- retry this commit later,
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__col_free:
    lda StreamScroll_PendCol
    and #$3F
    sta StreamScroll_ProdHi          ; reuse: vram_col scratch, done with the
                                       ; multiply product by this point
    and #$20
    beq Core_StreamScroll_ResolveRows__page_a
    lda StreamScroll_ProdHi
    and #$1F
    clc
    adc #BG1_TILEMAP_VRAM_WORD+1024  ; page B base
    bra Core_StreamScroll_ResolveRows__page_done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__page_a:
    lda StreamScroll_ProdHi
    clc
    adc #BG1_TILEMAP_VRAM_WORD
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__page_done:
    sta StreamScroll_ColTargetWord

    sep #$20
.a8
    lda #1
    sta StreamScroll_ColPending
    rep #$31
.a16
.i16
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__committed:
    ; extend the resident window to include PendCol, wherever it landed.
    ; PickColumn only ever moves ONE edge, by exactly one column, per call
    ; -- so trim the OPPOSITE edge inline in each branch if that pushed the
    ; window over the VRAM ring's physical 64-column capacity (BG1_
    ; TILEMAP_WORDS_WIDE/32 -- vram_col = world_col & 63). Without this,
    ; StagedLo/StagedHi can claim a window wider than 64 columns while the
    ; ring silently wraps and overwrites old columns' tilemap words
    ; underneath them -- confirmed via Phase 9 step 4's ad hoc scroll test:
    ; after scrolling world_col 0..569, column 0's VRAM content no longer
    ; matched ground truth (overwritten by columns 64/128/192/etc.'s
    ; commits) even though StagedLo still claimed 0 was resident. (A first
    ; attempt at this used StagedHi-CameraCol/CameraCol-StagedLo distance to
    ; pick which edge to trim -- wrong, because StagedHi can be BELOW
    ; CameraCol mid-catch-up, and that subtraction underflows as an
    ; unsigned 16-bit value, which made the trim undo the extension it was
    ; supposed to be capping and infinite-looped on one column forever.)
    lda StreamScroll_PendCol
    cmp StreamScroll_StagedLo
    bcs Core_StreamScroll_ResolveRows__not_new_lo
    sta StreamScroll_StagedLo
    lda StreamScroll_StagedHi
    sec
    sbc StreamScroll_StagedLo
    cmp #64
    bcc Core_StreamScroll_ResolveRows__not_new_lo
    lda StreamScroll_StagedLo
    clc
    adc #63
    sta StreamScroll_StagedHi
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__not_new_lo:
    lda StreamScroll_PendCol
    cmp StreamScroll_StagedHi
    bcc Core_StreamScroll_ResolveRows__not_new_hi
    sta StreamScroll_StagedHi
    lda StreamScroll_StagedHi
    sec
    sbc StreamScroll_StagedLo
    cmp #64
    bcc Core_StreamScroll_ResolveRows__not_new_hi
    lda StreamScroll_StagedHi
    sec
    sbc #63
    sta StreamScroll_StagedLo
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ResolveRows__not_new_hi:

    sep #$20
.a8
    lda StreamCache_CurrentStamp
    inc a
    sta StreamCache_CurrentStamp
    rep #$31
.a16
.i16

    lda #$FFFF
    sta StreamScroll_PendCol
    sec
    rts

; Called from Core_Nmi_Play (core/nmi.pasm), still inside its forced-blank
; bracket, right after Core_Dma_ProcessQueue. Writes StreamScroll_ColBuf into
; VRAM at StreamScroll_ColTargetWord via direct $2116/$2118/$2119 port
; writes -- not a DMA (DMA_OPT_STRIDE32, VMAIN=$81 2-regs-write-once, hung
; the CPU under Mesen2; see StreamScroll_ColPending's declaration comment).
; A no-op unless Core_StreamScroll_ResolveRows set ColPending this frame.
; Entered/left in whatever width Core_Nmi_Play's caller was in (rep #$31);
; explicitly resyncs to that on every exit path since it freely switches
; width internally.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_CommitColumn:
    ; Called from core/nmi.pasm's Core_Nmi_Play, which forces DBR=0 at its
    ; top ("where all hardware registers live") -- unlike Core_StreamScroll_
    ; Play/ResolveRows (called from scpu_main_loop, where DBR=$7E), every
    ; $7Exxxx access in THIS routine must be explicit .l, not bare .w.
    sep #$20
.a8
    lda.l StreamScroll_ColPending
    bne Core_StreamScroll_CommitColumn__go
    rep #$31
.a16
.i16
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_CommitColumn__go:
    ; VMAIN must be freshly set here, not assumed from some earlier boot-time
    ; write -- Bg_LoadScene hit this exact bug already (see its own header
    ; comment): with $2115=$00, the VRAM address advances on the $2118 (low
    ; byte) write instead of $2119 (high byte), so every row's high byte
    ; shears into the NEXT word instead of landing in its own. Confirmed via
    ; colbuf_probe.py: ColBuf held correct words, but VRAM readback showed
    ; every row's low byte correct and high byte wrong -- exactly that shear.
    sep #$20
.a8
    lda #$80                 ; increment by one word AFTER the $2119 write
    sta $2115
    rep #$31
.a16
.i16
    ldx #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_CommitColumn__row:
    ; CPX has no long-addressing mode, so compare via A instead (TXA doesn't
    ; disturb X).
    txa
    cmp.l StreamScroll_HeightTiles
    bcs Core_StreamScroll_CommitColumn__done
    asl a
    asl a
    asl a
    asl a
    asl a                       ; A = row * 32 (words between rows in VRAM)
    clc
    adc.l StreamScroll_ColTargetWord
    sta $2116
    ; ColBuf index MUST be X, not Y -- the 65816 has no indexed-LONG
    ; addressing mode with Y at all (only `addr24,X` exists). Poppy silently
    ; accepts `.l Symbol,y` anyway and falls back to a 3-byte absolute,Y
    ; (DBR-relative, and 1 byte short of the 4 it budgeted), which both reads
    ; the wrong bank (DBR=0 here, not $7E -- see this routine's header
    ; comment) AND shifts every following instruction in the routine one byte
    ; early per occurrence. Exactly the bug Bg_LoadScene_Streaming's own pass-
    ; 1/pass-2 loops already document (see their header comments) and use X
    ; to avoid -- this routine used Y instead and hit the same class:
    ; confirmed via bisection that row 0 (index 0) happened to decode into
    ; harmless garbage after the shift, but row 1 (index 2) hung the CPU
    ; solid (Nmi_FrameCounter frozen), and the SAME `lda.l StreamScroll_
    ; ColBuf,y` line alone (with every other instruction in the loop body
    ; stripped) reproduced the freeze. X already holds the row counter here,
    ; so stash it around the ColBuf index computation instead of reusing Y.
    phx
    txa
    asl a                       ; A = row * 2 (ColBuf is word-indexed)
    tax
    ; Read the whole 16-bit word via ONE indexed-long load (X unchanged
    ; across the width switch below), then split with XBA -- NOT a second
    ; `StreamScroll_ColBuf+1,x` indexed-long read for the high byte. That
    ; was the original bug here (found by direct comparison against
    ; Bg_LoadScene_Streaming's own row-write loop, which explicitly avoids
    ; exactly this "Symbol+1,y" pattern with the same XBA technique, per its
    ; own comment): ColBuf held correct words start-to-finish (confirmed via
    ; colbuf_probe.py), but VRAM readback showed the low byte landing
    ; correctly and the high byte wrong on nearly every row -- a `+1,y`
    ; indexed-long computed-offset operand, exactly the class of address
    ; CLAUDE.md's Poppy checklist warns can mis-resolve.
    lda.l StreamScroll_ColBuf,x
    sep #$20
.a8
    sta $2118
    rep #$31
.a16
.i16
    lda.l StreamScroll_ColBuf,x
    xba
    sep #$20
.a8
    sta $2119
    rep #$31
.a16
.i16
    plx                          ; restore the row counter
    inx
    bra Core_StreamScroll_CommitColumn__row
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_CommitColumn__done:
    ; Reached via `bcs` jumping OVER this loop body's internal sep/rep pairs
    ; -- redundant resync per CLAUDE.md's Poppy width-tracking checklist.
    sep #$20
.a8
    lda #0
    sta.l StreamScroll_ColPending
    rep #$31
.a16
.i16
    rts

; Call once per scpu_main_loop iteration, right after Core_Screen_Play and
; BEFORE its result is committed to Nmi_Bg1ScrollX/Screen_PosX is read
; anywhere else this frame. Prevents Core_Screen_Play's distance-scaled ease
; (core/screen.pasm's beat-em-up follow camera -- speed scales with distance
; from the focus target, a deliberate "snap back fast after a big jump"
; design) from letting the camera's world column outrun what SyncScroll has
; actually finished resolving. Before this existed, a large camera jump
; could produce visibly garbled BG1 tiles roughly 5 columns past the boot
; window mask's edge (see syncscroll_budget_throughput project memory for
; the repro) -- STREAM_SCROLL_PREFETCH's "a column is already resident by
; the time the camera reaches it" assumption only holds if the camera is
; ALSO prevented from reaching it early, which nothing did until this.
; Real beat-em-up gameplay doesn't need fast scrolling (unlike, say, a
; Sonic-style level) -- clamping the camera to the resolver's actual
; throughput is the intended fix here, not a compromise. No-ops for a
; BG_MODE_STATIC level (StreamScroll_Enabled stays 0, StagedLo/Hi aren't
; meaningful then).
Core_StreamScroll_ClampCamera:
    sep #$20
.a8
    lda StreamScroll_Enabled
    bne Core_StreamScroll_ClampCamera__active
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ClampCamera__active:
    rep #$31
.a16
.i16
    lda Screen_PosX
    lsr a
    lsr a
    lsr a                        ; world_col = leftmost visible column
    tax                           ; keep it in X -- reused by the leftward
                                    ; clamp below without re-deriving it

    ; --- rightward clamp: rightmost visible column can't get ahead of
    ; StreamScroll_StagedHi, the highest column the resolver has actually
    ; finished. ---
    txa
    clc
    adc #(STREAM_STAGE_VIEWPORT_COLS - 1)
    cmp StreamScroll_StagedHi
    bcc Core_StreamScroll_ClampCamera__right_ok
    beq Core_StreamScroll_ClampCamera__right_ok
    lda StreamScroll_StagedHi
    sec
    sbc #(STREAM_STAGE_VIEWPORT_COLS - 1)
    bpl Core_StreamScroll_ClampCamera__have_right_col
    lda #0                        ; before the level's first viewport-worth
                                    ; is even staged -- clamp to column 0
                                    ; rather than a negative/huge column
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ClampCamera__have_right_col:
    tax                           ; X = clamped world_col, feeds the
                                    ; leftward check below too
    asl a
    asl a
    asl a                          ; world_col -> pixels
    sta Screen_PosX
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ClampCamera__right_ok:

    ; --- leftward clamp: leftmost visible column can't fall behind
    ; StreamScroll_StagedLo -- the resolver's ring can evict/repurpose
    ; columns below its own low watermark too. ---
    txa
    cmp StreamScroll_StagedLo
    bcs Core_StreamScroll_ClampCamera__left_ok
    lda StreamScroll_StagedLo
    asl a
    asl a
    asl a
    sta Screen_PosX
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_ClampCamera__left_ok:
    rts

; Call once per scpu_main_loop iteration, right after the camera position
; (Screen_PosX) has been committed for this frame. No-ops immediately for a
; BG_MODE_STATIC level, and whenever an in-flight animation-frame stream
; still has DMAs queued/undrained (Msu1_StreamBusy != 0) -- matches every
; other per-frame DMA-queue-consuming subsystem's gating in this file, so
; SyncScroll never contends with Msu1_LoadFrame for queue slots.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_Play:
    php
    sei
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda StreamScroll_Enabled
    bne Core_StreamScroll_Play__enabled
    rep #$31
.a16
.i16
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_Play__enabled:
    lda.l Msu1_StreamBusy
    beq Core_StreamScroll_Play__msu_free
    rep #$31
.a16
.i16
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_Play__msu_free:
    ; Redundant re-sync -- this label is reached by `beq` from __enabled,
    ; which jumps OVER the rep #$31/.a16 a few lines below __enabled's own
    ; body. Poppy's linear (non-control-flow-aware) width estimation pass
    ; mis-sizes the immediate below without this (confirmed: disassembly
    ; showed a phantom BRK here) -- see CLAUDE.md's Poppy checklist.
    sep #$20
.a8
    lda #0
    sta StreamScroll_Budget
    rep #$31
.a16
.i16

    lda StreamScroll_PendCol
    cmp #$FFFF
    bne Core_StreamScroll_Play__resume

    jsr Core_StreamScroll_PickColumn
    sta StreamScroll_PendCol
    tax
    jsr Core_StreamScroll_SeekColumn
    lda #0
    sta StreamScroll_PendTile
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScroll_Play__resume:
    jsr Core_StreamScroll_ResolveRows

    plp
    rep #$31
.a16
.i16
    rts

; ============================================================================
; Phase 10 Step 2c (plan.md 2.10): BG3 frontpanel per-frame streaming
; resolver. Tracks the same world camera (Screen_PosX) as Core_StreamScroll_*
; above, against the separate FP cache/tilemap. See StreamScrollFp_
; TilemapOffLo's declaration comment for the one real structural difference
; from BG1's version: BG3's tilemap is a single 32x32 map, exactly the size
; of one viewport, so there is no prefetch margin and the resolved window is
; always exactly STREAM_STAGE_VIEWPORT_COLS(32) wide -- simpler than BG1's
; elastic-up-to-64 window, no "trim to fit the ring" step needed.
; ============================================================================

; Twin of Core_StreamScroll_SeekColumn, computing a seek target from
; StreamScrollFp_TilemapOffLo/Hi (the preserved base) instead of
; StreamScroll_TilemapOffLo/Hi, and landing on the FIRST of the
; FP_CONTENT_ROW_COUNT real-content rows (STREAM_FP_TILEMAP_ROW_START), not
; row 0 -- see FP_CONTENT_ROW_COUNT's declaration for why only these 7 rows
; are ever resolved. Reads FP_CONTENT_ROW_COUNT*3 bytes (21), not a full
; height_tiles*3 (84) like the boot loader's own column read.
; @param X<16-bit>  world column to seek to
; Clobbers A, X, Y.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_SeekColumn:
    php
    sei
    rep #$31
.a16
.i16
    ; Same LDX-has-no-absolute-long-addressing-mode workaround as BG1's own
    ; Core_StreamScroll_SeekColumn (see its header comment for the full
    ; mechanism) -- load via LDA.l (matching BG1's own exact original)
    ; into a scratch cell, then TAX.
    phx                          ; save world_col (the @param X)
    lda.l StreamStageFp_ColStrideLo
    tax
    pla                           ; world_col back into A
    jsr Core_Math_Mul            ; a = product lo16, x = product hi16
    pha
    txa
    sta StreamScrollFp_ProdHi
    pla

    ; StreamScrollFp_TilemapOffLo/Hi already has STREAM_FP_TILEMAP_ROW_START*3
    ; (63) folded in (see where it's captured, in Bg_LoadSceneFp_Streaming's
    ; header-read section, for why -- a real bug, found via Mesen2: adding it
    ; here instead, as a second chained ADC into the same 16-bit word, does
    ; NOT correctly propagate a combined carry into the Hi-byte add below).
    ; This is now a clean 2-term add, the same proven single-carry shape
    ; BG1's own Core_StreamScroll_SeekColumn already uses.
    clc
    adc StreamScrollFp_TilemapOffLo
    sta StreamStageFp_SeekLo

    sep #$20
.a8
    lda StreamScrollFp_TilemapOffHi
    adc StreamScrollFp_ProdHi        ; carry survives the SEP above unaffected
    sta StreamStageFp_SeekHi

    lda StreamStageFp_SeekLo
    sta $2000
    lda.l StreamStageFp_SeekLo+1
    sta $2001
    lda StreamStageFp_SeekHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_SeekColumn__seek_busy:
    lda $2000
    bmi Core_StreamScrollFp_SeekColumn__seek_busy

    rep #$31
.a16
.i16
    ldx #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_SeekColumn__read_entry:
    sep #$20
.a8
    lda $2001
    sta.l StreamStageFp_Entries,x
    rep #$31
.a16
.i16
    inx
    cpx #(FP_CONTENT_ROW_COUNT*3)
    bcc Core_StreamScrollFp_SeekColumn__read_entry

    plp
    rep #$31
.a16
.i16
    rts

; Twin of Core_StreamScroll_FetchTileToBuffer for 2bpp tiles: 16 bytes/8
; words, not 32 bytes/16 words, so a 4-shift *16 instead of a 5-shift *32,
; and StreamScrollFp_TileBufN's slots are 16 bytes each, not 32.
; @param StreamStageFp_TileId<16-bit>  the tile ID to fetch
; Clobbers A/X/Y.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_FetchTileToBuffer:
    rep #$31
.a16
.i16
    lda StreamStageFp_TileId
    sta StreamStageFp_TileOffLo
    sep #$20
.a8
    lda #0
    sta StreamStageFp_TileOffHi
    rep #$31
.a16
.i16
    ldx #4                        ; *16 (2bpp 8x8 tile), not BG1's *32
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_FetchTileToBuffer__shift:
    lda StreamStageFp_TileOffLo
    asl a
    sta StreamStageFp_TileOffLo
    sep #$20
.a8
    lda StreamStageFp_TileOffHi
    rol a
    sta StreamStageFp_TileOffHi
    rep #$31
.a16
.i16
    dex
    bne Core_StreamScrollFp_FetchTileToBuffer__shift

    lda StreamStageFp_TilesBaseLo
    clc
    adc StreamStageFp_TileOffLo
    sta StreamStageFp_SeekTmpLo
    sep #$20
.a8
    lda StreamStageFp_TilesBaseHi
    adc StreamStageFp_TileOffHi
    sta StreamStageFp_SeekTmpHi

    lda StreamStageFp_SeekTmpLo
    sta $2000
    lda.l StreamStageFp_SeekTmpLo+1
    sta $2001
    lda StreamStageFp_SeekTmpHi
    sta $2002
    lda #0
    sta $2003
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_FetchTileToBuffer__seek_busy:
    lda $2000
    bmi Core_StreamScrollFp_FetchTileToBuffer__seek_busy

    rep #$31
.a16
.i16
    sep #$20
.a8
    lda StreamScrollFp_FetchBufSel
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a
    asl a                   ; A = FetchBufSel * 16 (2bpp slot size)
    tax
    ldy #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_FetchTileToBuffer__read:
    sep #$20
.a8
    lda $2001
    sta.l StreamScrollFp_TileBufN,x
    rep #$31
.a16
.i16
    inx
    iny
    cpy #16
    bcc Core_StreamScrollFp_FetchTileToBuffer__read

    rts

; Twin of Core_StreamScroll_PickColumn, minus the wide-ring "repair cursor
; clamped into [DesiredLo,DesiredHi]" complexity BG1 needs for its own
; elastic (prefetch-widened) window -- see the header comment above this
; whole Step 2c block for why FP's window can't grow past 32 columns, so a
; plain extend-left/extend-right/repair-one-column-at-a-time shape (same
; overall algorithm BG1 uses, same field names) is enough without ever
; needing to trim an over-wide window afterward.
; @return A<16-bit>  world column to stage this tick
; Clobbers A, X.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_PickColumn:
    rep #$31
.a16
.i16
    lda Screen_PosX
    lsr a
    lsr a
    lsr a                         ; cameraCol = Screen_PosX >> 3
    sta StreamScrollFp_CameraCol
    sta StreamScrollFp_DesiredLo

    clc
    adc #(STREAM_STAGE_VIEWPORT_COLS-1)
    pha
    lda.l StreamScroll_WidthTiles  ; shared level width -- see this field's
                                     ; own declaration for the ordering
                                     ; assumption this relies on (BG1's boot
                                     ; loader runs before FP's, so this is
                                     ; already populated by the time Step 2c
                                     ; ever runs)
    dec a
    tax
    pla
    jsr Core_Math_Min               ; a = min(desired_hi_raw, width-1)
    sta StreamScrollFp_DesiredHi

    lda StreamScrollFp_DesiredLo
    cmp StreamScrollFp_StagedLo
    bcs Core_StreamScrollFp_PickColumn__check_hi
    lda StreamScrollFp_StagedLo
    dec a
    rts                             ; extend left
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_PickColumn__check_hi:
    lda StreamScrollFp_DesiredHi
    cmp StreamScrollFp_StagedHi
    beq Core_StreamScrollFp_PickColumn__repair
    bcc Core_StreamScrollFp_PickColumn__repair
    lda StreamScrollFp_StagedHi
    inc a
    rts                             ; extend right
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_PickColumn__repair:
    lda StreamScrollFp_RepairCur
    cmp StreamScrollFp_DesiredLo
    bcs Core_StreamScrollFp_PickColumn__repair_lo_ok
    lda StreamScrollFp_DesiredLo
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_PickColumn__repair_lo_ok:
    cmp StreamScrollFp_DesiredHi
    bcc Core_StreamScrollFp_PickColumn__repair_hi_ok
    beq Core_StreamScrollFp_PickColumn__repair_hi_ok
    lda StreamScrollFp_DesiredHi
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_PickColumn__repair_hi_ok:
    pha
    inc a
    cmp StreamScrollFp_DesiredHi
    bcc Core_StreamScrollFp_PickColumn__repair_adv_ok
    lda StreamScrollFp_DesiredLo
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_PickColumn__repair_adv_ok:
    sta StreamScrollFp_RepairCur
    pla
    rts

; Twin of Core_StreamScroll_ResolveRows, resolving FP_CONTENT_ROW_COUNT rows
; (not up to 28) budget-capped at STREAM_SCROLLFP_BUDGET_MAX. StreamScrollFp_
; PendTile indexes 0..FP_CONTENT_ROW_COUNT-1 into the 7 real rows fetched by
; Core_StreamScrollFp_SeekColumn -- StreamStageFp_Entries holds exactly
; those 7*3 bytes starting at index 0 (unlike BG1's Entries, which holds a
; full height_tiles*3 and is indexed by absolute row), so no
; STREAM_FP_TILEMAP_ROW_START adjustment is needed when reading it here.
; @return carry<bool>  set if PendCol fully committed (its DMA enqueued,
;         PendCol reset to $FFFF); clear if still in progress
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows:
    rep #$31
.a16
.i16
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__row:
    lda StreamScrollFp_PendTile
    cmp #FP_CONTENT_ROW_COUNT
    bcc Core_StreamScrollFp_ResolveRows__have_row
    brl Core_StreamScrollFp_ResolveRows__commit
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__have_row:

    lda StreamScrollFp_PendTile
    sta StreamStageFp_TileOffLo   ; row temp only (matches boot's own reuse)
    asl a
    clc
    adc StreamStageFp_TileOffLo
    tax                            ; x = row*3

    lda.l StreamStageFp_Entries,x
    sta StreamStageFp_TileId
    inx
    inx
    sep #$20
.a8
    lda.l StreamStageFp_Entries,x
    sta StreamStageFp_Attr
    rep #$31
.a16
.i16

    lda StreamStageFp_TileId
    asl a
    tax
    lda.l StreamCacheFp_Tile2Slot,x
    cmp #$FFFF
    beq Core_StreamScrollFp_ResolveRows__is_miss
    brl Core_StreamScrollFp_ResolveRows__hit
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__is_miss:
    ; StreamScrollFp_Budget is a .db -- an 8-bit compare, same reason as
    ; Core_StreamScroll_ResolveRows' own is_miss (see its comment).
    sep #$20
.a8
    lda StreamScrollFp_Budget
    cmp #STREAM_SCROLLFP_BUDGET_MAX
    bcc Core_StreamScrollFp_ResolveRows__miss_ok
    rep #$31
.a16
.i16
    clc
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__miss_ok:
    ; Must not commit Core_StreamCacheFp_AllocateSlot's Tile2Slot/Slot2Tile
    ; mapping unless Core_Dma_Enqueue below is guaranteed to succeed -- see
    ; Core_Dma_HasFreeSlot's header (same reasoning as
    ; Core_StreamScroll_ResolveRows' identical guard).
    rep #$31
.a16
.i16
    jsr Core_Dma_HasFreeSlot
    bcs Core_StreamScrollFp_ResolveRows__queue_ok
    clc
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__queue_ok:
    sep #$20
.a8
    lda StreamScrollFp_Budget
    sta StreamScrollFp_FetchBufSel
    rep #$31
.a16
.i16
    lda StreamStageFp_TileId
    tax
    jsr Core_StreamCacheFp_AllocateSlot
    sta StreamStageFp_Slot
    jsr Core_StreamScrollFp_FetchTileToBuffer

    sep #$20
.a8
    lda StreamScrollFp_FetchBufSel
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a
    asl a                   ; A = FetchBufSel * 16
    clc
    adc #StreamScrollFp_TileBufN
    sta DmaRequest_SourceAddrLow
    sep #$20
.a8
    lda #$7F
    sta DmaRequest_SourceBank
    rep #$31
.a16
.i16

    lda StreamStageFp_Slot
    asl a
    asl a
    asl a                          ; slot*8 words -- 2bpp tile size, not
                                     ; BG1's slot*16
    clc
    adc #FP_TILES_VRAM_WORD
    asl a                          ; word address -> byte address
    sta DmaRequest_TargetAddr
    lda #16
    sta DmaRequest_Length
    sep #$20
.a8
    lda #DMA_TYPE_VRAM
    sta DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsr Core_Dma_Enqueue
    bcs Core_StreamScrollFp_ResolveRows__enqueued
    clc                             ; queue full -- retry this row later
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__enqueued:
    sep #$20
.a8
    lda StreamScrollFp_Budget
    inc a
    sta StreamScrollFp_Budget
    rep #$31
.a16
.i16
    brl Core_StreamScrollFp_ResolveRows__resolved
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__hit:
    sta StreamStageFp_Slot
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__resolved:

    ; --- build the remapped hw tilemap word -- identical bit layout to
    ; Bg_LoadSceneFp_Streaming's row loop, INCLUDING FP_TILE_INDEX_BASE
    ; (see that constant's own declaration for why a bare slot number is
    ; wrong here -- the same off-by-32-tiles bug it fixes for the boot
    ; loader applies just as much to this runtime resolver). ---
    lda StreamStageFp_Slot
    clc
    adc #FP_TILE_INDEX_BASE
    sta StreamStageFp_Word

    sep #$20
.a8
    lda StreamStageFp_Attr
    and #$07
    rep #$31
.a16
.i16
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                            ; << 10
    ora StreamStageFp_Word
    sta StreamStageFp_Word

    sep #$20
.a8
    lda StreamStageFp_Attr
    and #$08
    rep #$31
.a16
.i16
    and #$00FF
    beq Core_StreamScrollFp_ResolveRows__no_hflip
    lda StreamStageFp_Word
    ora #$4000
    sta StreamStageFp_Word
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__no_hflip:

    sep #$20
.a8
    lda StreamStageFp_Attr
    and #$10
    rep #$31
.a16
.i16
    and #$00FF
    beq Core_StreamScrollFp_ResolveRows__no_vflip
    lda StreamStageFp_Word
    ora #$8000
    sta StreamStageFp_Word
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__no_vflip:

    ; --- priority bit: always set, unconditionally -- every frontpanel
    ; tile needs it (unlike BG1, which never sets it at all), same
    ; convention Bg_LoadSceneFp_Streaming's own boot loader uses. ---
    lda StreamStageFp_Word
    ora #$2000
    sta StreamStageFp_Word

    ; --- store into StreamScrollFp_ColBuf[row] (word-indexed) ---
    lda StreamScrollFp_PendTile
    asl a
    tax
    lda StreamStageFp_Word
    sta.l StreamScrollFp_ColBuf,x

    lda StreamScrollFp_PendTile
    inc a
    sta StreamScrollFp_PendTile
    brl Core_StreamScrollFp_ResolveRows__row
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__commit:
    ; every row resolved -- hand ColBuf off to Core_Nmi_Play's forced-blank
    ; column-write block (Core_StreamScrollFp_CommitColumn), same direct-
    ; port-write handoff BG1 uses and for the same reason (see
    ; StreamScroll_ColPending's declaration comment). vram_col = world_col
    ; & 31 -- BG3's tilemap is a single 32x32 page, no two-page ring like
    ; BG1's, so no page-select bit is needed.
    lda StreamScrollFp_ColPending
    and #$00FF
    beq Core_StreamScrollFp_ResolveRows__col_free
    sec                                ; NMI hasn't drained the previous
    rts                                ; column yet -- retry this commit later
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__col_free:
    lda StreamScrollFp_PendCol
    and #$001F
    clc
    adc #(BG3_TILEMAP_VRAM_WORD + STREAM_FP_TILEMAP_ROW_START*32)
    sta StreamScrollFp_ColTargetWord

    sep #$20
.a8
    lda #1
    sta StreamScrollFp_ColPending
    rep #$31
.a16
.i16

    ; --- extend the resident window to include PendCol, wherever it landed.
    ; UNLIKE the comment that used to sit here claimed, the window does NOT
    ; stay bounded on its own just because PickColumn moves one edge by one
    ; column per call -- confirmed by a real bug caught via Mesen2 (a
    ; scripted 143-column scroll left StagedLo pinned at 0 and StagedHi at
    ; 174, a 175-column "window" against a 32-column physical ring). Moving
    ; one edge must explicitly pull the OPPOSITE edge in in lockstep so the
    ; window never exceeds STREAM_STAGE_VIEWPORT_COLS(32) -- there is no
    ; margin to spare here, unlike BG1's own 64-column ring against its
    ; 32-40-column window, so this can't be left to the repair sweep to
    ; eventually fix (and doesn't need BG1's more general "trim if over
    ; capacity" shape either, since a fixed-width window has an exact
    ; opposite-edge position, not just an upper bound). ---
    lda StreamScrollFp_PendCol
    cmp StreamScrollFp_StagedLo
    bcs Core_StreamScrollFp_ResolveRows__not_below
    sta StreamScrollFp_StagedLo
    clc
    adc #(STREAM_STAGE_VIEWPORT_COLS-1)
    sta StreamScrollFp_StagedHi
    brl Core_StreamScrollFp_ResolveRows__window_done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__not_below:
    lda StreamScrollFp_PendCol
    cmp StreamScrollFp_StagedHi
    bcc Core_StreamScrollFp_ResolveRows__window_done
    sta StreamScrollFp_StagedHi
    sec
    sbc #(STREAM_STAGE_VIEWPORT_COLS-1)
    sta StreamScrollFp_StagedLo
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_ResolveRows__window_done:

    lda #$FFFF
    sta StreamScrollFp_PendCol
    sec
    rts

; Called from Core_Nmi_Play (core/nmi.pasm), still inside its forced-blank
; bracket, right after Core_StreamScroll_CommitColumn. Writes
; StreamScrollFp_ColBuf into VRAM at StreamScrollFp_ColTargetWord via direct
; port writes -- twin of Core_StreamScroll_CommitColumn, see its header
; comment for why this can't be a DMA. Only walks FP_CONTENT_ROW_COUNT rows
; (a fixed constant here, not a variable HeightTiles like BG1's, since FP
; never resolves the other 21 blank rows -- see this block's own header).
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_CommitColumn:
    ; Called from core/nmi.pasm's Core_Nmi_Play, which forces DBR=0 -- every
    ; $7Exxxx access in THIS routine must be explicit .l, not bare .w, same
    ; reason Core_StreamScroll_CommitColumn's own header comment gives.
    sep #$20
.a8
    lda.l StreamScrollFp_ColPending
    bne Core_StreamScrollFp_CommitColumn__go
    rep #$31
.a16
.i16
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_CommitColumn__go:
    ; VMAIN must be freshly set here too, not assumed from Core_StreamScroll_
    ; CommitColumn's own write just above this call in Core_Nmi_Play -- see
    ; that routine's header comment for the exact word-vs-byte shear bug
    ; this guards against. Harmless if it's already $80 (this call runs
    ; right after that one every frame), but re-asserting costs nothing and
    ; removes any ordering assumption between the two.
    sep #$20
.a8
    lda #$80
    sta $2115
    rep #$31
.a16
.i16
    ldx #0
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_CommitColumn__row:
    txa
    cmp #FP_CONTENT_ROW_COUNT
    bcs Core_StreamScrollFp_CommitColumn__done
    asl a
    asl a
    asl a
    asl a
    asl a                       ; A = row * 32 (words between rows in VRAM)
    clc
    adc.l StreamScrollFp_ColTargetWord
    sta $2116
    ; ColBuf index MUST be X, not Y -- see Core_StreamScroll_CommitColumn's
    ; own header comment for the confirmed Poppy bug (`.l Symbol,y` silently
    ; falls back to a wrong-bank, wrong-length absolute,Y) this avoids.
    phx
    txa
    asl a                       ; A = row * 2 (ColBuf is word-indexed)
    tax
    lda.l StreamScrollFp_ColBuf,x
    sep #$20
.a8
    sta $2118
    rep #$31
.a16
.i16
    lda.l StreamScrollFp_ColBuf,x
    xba
    sep #$20
.a8
    sta $2119
    rep #$31
.a16
.i16
    plx                          ; restore the row counter
    inx
    bra Core_StreamScrollFp_CommitColumn__row
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_CommitColumn__done:
    sep #$20
.a8
    lda #0
    sta.l StreamScrollFp_ColPending
    rep #$31
.a16
.i16
    rts

; Call once per scpu_main_loop iteration, right after Core_StreamScroll_Play
; (this file's own convention: BG1 resolves first, FP second, both gated the
; same way). No-ops immediately if FP has no data for this level
; (StreamScrollFp_Enabled stays 0, set by Bg_LoadSceneFp_Streaming iff
; BgRecordStaging+28..30 was nonzero) or while an in-flight animation-frame
; stream still has DMAs queued (Msu1_StreamBusy != 0) -- same gating BG1's
; own Core_StreamScroll_Play uses, so FP never contends with Msu1_LoadFrame
; for queue slots either. Does NOT additionally check StreamScroll_Budget or
; otherwise defer to BG1 finishing first within the same frame -- both may
; enqueue in the same frame, up to STREAM_SCROLL_BUDGET_MAX(6) +
; STREAM_SCROLLFP_BUDGET_MAX(2) = 8 DMAs, exactly DMA_QUEUE_SLOTS' capacity.
; Core_Dma_Enqueue's own queue-full handling (retry next call, never
; corrupts) makes this safe either way -- see STREAM_SCROLLFP_BUDGET_MAX's
; own declaration comment for the real risk this combination carries and
; why it must be stress-tested, not just trusted, before shipping.
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_Play:
    php
    sei
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda StreamScrollFp_Enabled
    bne Core_StreamScrollFp_Play__enabled
    rep #$31
.a16
.i16
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_Play__enabled:
    lda.l Msu1_StreamBusy
    beq Core_StreamScrollFp_Play__msu_free
    rep #$31
.a16
.i16
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_Play__msu_free:
    ; Redundant re-sync -- same reason Core_StreamScroll_Play__msu_free's
    ; own comment gives (this label is reached by a `beq` that jumps over a
    ; rep #$31/.a16 a few lines below __enabled's own body).
    sep #$20
.a8
    lda #0
    sta StreamScrollFp_Budget
    rep #$31
.a16
.i16

    lda StreamScrollFp_PendCol
    cmp #$FFFF
    bne Core_StreamScrollFp_Play__resume

    jsr Core_StreamScrollFp_PickColumn
    sta StreamScrollFp_PendCol
    tax
    jsr Core_StreamScrollFp_SeekColumn
    lda #0
    sta StreamScrollFp_PendTile
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_StreamScrollFp_Play__resume:
    jsr Core_StreamScrollFp_ResolveRows

    plp
    rep #$31
.a16
.i16
    rts

; ============================================================================
; Hud_DrawBar -- render one entity's health bar into HudStaging.
;   A = that entity's CHAR_HP (8-bit), X = byte offset of the bar's tilemap row
; Leaves X past the bar. Clobbers A/X/Y.
;
; Layout per row: column 0 blank, column 1 left cap, columns 2-9 the eight body
; tiles, column 10 right cap. Body tile i shows min(hp - i*8, 8) filled columns,
; so one HP = one pixel of bar and CHAR_HP_MAX(64) exactly fills all eight.
; ============================================================================
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
    nop
    nop
Hud_DrawBar:
    sep #$20
.a8
    sta.l HudBarHp
    inx
    inx                         ; skip column 0

    lda #HUD_TILE_CAP_LEFT
    sta.l HudStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudStaging,x
    inx

    ldy #HUD_BAR_TILES
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Hud_DrawBar__body:
    sep #$20
.a8
    lda.l HudBarHp
    cmp #8
    bcc Hud_DrawBar__partial
    lda #8
    sta.l HudBarFilled
    lda.l HudBarHp
    sec
    sbc #8
    sta.l HudBarHp
    bra Hud_DrawBar__have
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Hud_DrawBar__partial:
    sep #$20
.a8
    sta.l HudBarFilled          ; A is still the remaining HP (< 8)
    lda #0
    sta.l HudBarHp
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Hud_DrawBar__have:
    sep #$20
.a8
    lda.l HudBarFilled
    clc
    adc #HUD_TILE_FILL_BASE
    sta.l HudStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudStaging,x
    inx
    dey
    bne Hud_DrawBar__body

    lda #HUD_TILE_CAP_RIGHT
    sta.l HudStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudStaging,x
    inx
    rts

; ============================================================================
; Hud_Play -- per-frame BG3 health-bar HUD (Phase 6).
;
; Called once per scpu_main_loop iteration, which Core_Nmi_WaitFrame paces to
; one real frame. DIRTY-FLAG GATED: it compares all four entities' CHAR_HP
; against HudCachedHp and returns immediately when nothing changed, so in the
; common frame it enqueues NOTHING.
;
; That gating is the whole point, not an optimization. core/nmi.pasm's header
; and plan.md 2.4 both record that a per-frame subsystem which unconditionally
; enqueues DMA work is exactly what overran Core_Nmi_Play's forced-blank commit
; bracket into active display and corrupted the top of every frame. HP changes
; only on a landed hit, so this redraws a handful of times per second at most.
; ============================================================================
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
    nop
    nop
Hud_Play:
    php
    sep #$20
.a8
    lda.l HudDirty
    bne Hud_Play__rebuild
    lda.l PlayerEntity_Hp
    cmp.l HudCachedHp
    bne Hud_Play__rebuild
    lda.l Entity1_Hp
    cmp.l HudCachedHp+1
    bne Hud_Play__rebuild
    lda.l Entity2_Hp
    cmp.l HudCachedHp+2
    bne Hud_Play__rebuild
    lda.l Entity3_Hp
    cmp.l HudCachedHp+3
    bne Hud_Play__rebuild
    plp
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Hud_Play__rebuild:
    sep #$20
.a8
    lda #0
    sta.l HudDirty
    lda.l PlayerEntity_Hp
    sta.l HudCachedHp
    lda.l Entity1_Hp
    sta.l HudCachedHp+1
    lda.l Entity2_Hp
    sta.l HudCachedHp+2
    lda.l Entity3_Hp
    sta.l HudCachedHp+3

    ; --- blank the whole staging block, then draw the four bars over it ---
    rep #$31
.a16
.i16
    ldx #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Hud_Play__clear:
    lda #$0000
    sta.l HudStaging,x
    inx
    inx
    cpx #HUD_STAGING_BYTES
    bcc Hud_Play__clear

    sep #$20
.a8
    lda.l HudCachedHp
    rep #$10
.i16
    ldx #$0000              ; row 0
    jsr Hud_DrawBar
    sep #$20
.a8
    lda.l HudCachedHp+1
    ldx #$0040              ; row 1 (32 entries * 2 bytes)
    jsr Hud_DrawBar
    sep #$20
.a8
    lda.l HudCachedHp+2
    ldx #$0080              ; row 2
    jsr Hud_DrawBar
    sep #$20
.a8
    lda.l HudCachedHp+3
    ldx #$00C0              ; row 3
    jsr Hud_DrawBar

    ; --- one queued VRAM DMA for all four rows ---
    ; DmaRequest_TargetAddr is a BYTE address (Core_Dma_TransferVram halves it
    ; into $2116), so the BG3 tilemap's word $6800 is byte $D000.
    rep #$31
.a16
.i16
    lda #HudStaging
    sta.l DmaRequest_SourceAddrLow
    lda #BG3_TILEMAP_VRAM_WORD * 2
    sta.l DmaRequest_TargetAddr
    lda #HUD_STAGING_BYTES
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
    rts

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

    ; Core_StreamCache_Init sets up the Tile2Slot/Slot2Tile/SlotStamp tables
    ; for real use by Bg_LoadScene_Streaming (called later, from within
    ; Bg_LoadScene). The step-2 smoke test (Core_StreamCache_Test) that used
    ; to run here has been removed now that step 3 (real content) has
    ; landed -- it allocated 8 slots for synthetic tile IDs 0-7 using the
    ; SAME Tile2Slot table a real streaming level uses, which silently
    ; poisoned the cache: any real level tile whose ID happened to be 0-7
    ; would read back as an already-cached "hit" against a slot the smoke
    ; test never actually populated with pixel data, instead of genuinely
    ; fetching that tile. Found via phase9_stagecolumn_spotcheck.py -- every
    ; mismatch traced back to Tile2Slot[0..7] already holding the smoke
    ; test's own stride-337 allocations. Core_StreamCache_Test itself is
    ; kept in core/stream_cache.pasm for future ad hoc re-verification, just
    ; no longer called from the real boot path.
    jsr Core_StreamCache_Init

    ; Phase 10 (plan.md 2.10) frontpanel cache -- same Init-only-no-test
    ; convention as the BG1 call immediately above (see that call site's
    ; comment for the exact poisoned-cache failure mode this avoids).
    ; Core_StreamCacheFp_AllocateSlot is now called from a real per-frame
    ; path (Step 2c's Core_StreamScrollFp_Play, further below) whenever FP
    ; content is actually shipped.
    jsr Core_StreamCacheFp_Init

    ; StreamScroll_Enabled/StreamScrollFp_Enabled must be explicitly zeroed
    ; here, unconditionally, for every build (including a BG_MODE_STATIC
    ; level, or a level with no FP data at all) -- WRAM is not guaranteed
    ; zero at power-on on real hardware, and Bg_LoadScene_Streaming/
    ; Bg_LoadSceneFp_Streaming (the only places that ever set these to 1)
    ; don't run at all in those cases, so without this an uninitialized byte
    ; could read nonzero and make Core_StreamScroll_Play/Core_StreamScrollFp_
    ; Play act on garbage StreamStage_*/StreamScroll_*/StreamScrollFp_*
    ; state every frame. StreamScrollFp_ColPending is zeroed the same way,
    ; for the same reason StreamScroll_ColPending would need it if BG1 ever
    ; grew an equivalent unconditional-zero requirement -- Core_Nmi_Play's
    ; forced-blank column-write block runs every single frame regardless of
    ; Enabled, gated only on ColPending.
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #0
    sta StreamScroll_Enabled
    sta StreamScrollFp_Enabled
    sta StreamScrollFp_ColPending
    rep #$31
.a16
.i16

    jsr Core_Oop_Init
    jsr Core_Screen_Init

    ; Register the Character entity class (plan.md Phase 1a). Fill the
    ; RegisterClass staging cells (16-bit WRAM fields, see core/oop.pasm)
    ; while still in the ambient .a16/.i16 from the rep #$30 above.
    ; Deliberately NOT calling Core_Oop_Create here too (Phase 1a did) --
    ; Phase 1b's CharacterEntity_Init now does the MSU-1 roster load itself
    ; (DP-relative writes need to land in this object's own window, not
    ; wherever D happens to point at this early boot point), and that load
    ; has a real ordering dependency on SA-1 reset + MSU-1 track-select
    ; having already run (see Anim_LoadCharacter's header) -- both of which
    ; happen well after this point in scpu_boot. Create is called instead
    ; at msu1_done, replacing the old direct jsr Anim_LoadCharacter there.
    lda #0
    sta.l OopRegStaging_Flags
    lda #CHAR_ZP_LEN
    sta.l OopRegStaging_ZpLen
    lda #CharacterEntity_Init
    sta.l OopRegStaging_Init
    lda #CharacterEntity_Play
    sta.l OopRegStaging_Play
    lda #0
    sta.l OopRegStaging_Pause
    lda #CharacterEntity_OnCommand   ; Phase 8: camera queries CHAR_POS_X/Y
    sta.l OopRegStaging_OnCommand

    ; Core_Oop_RegisterClass's own php/plp restores whatever width was live
    ; at the call site, and its documented "@return a<8-bit> new class id"
    ; contract only holds if that's .a8 -- so narrow right before calling it.
    sep #$20
.a8
    jsr Core_Oop_RegisterClass
    sta.l CharacterClassId

    rep #$31
.a16
.i16

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
    ; --- Runtime character selection: create Entity #0 (roster slot 0).
    ; CharacterEntity_Init does the actual MSU-1 load via Anim_LoadCharacter
    ; (DP is already switched to this object's own window by Core_Oop_
    ; Create by the time Init runs) -- see Anim_LoadCharacter's header for
    ; why this call site specifically (right after track-select) matters
    ; for the load itself; that dependency is why Create is called here,
    ; not back where the class was registered (see that comment). ---
    rep #$31
.a16
.i16
    lda.l CharacterClassId  ; LDY/LDX have no absolute-long addressing mode on
    and #$00ff               ; 65816 (only LDA does) -- `ldy.l` silently mis-
    tay                       ; assembles instead of erroring (poppy bug #11).
                              ; Load via LDA (masked) and TAY instead.
    lda #0                   ; init param -- (role<<8)|roster_index = role 0
                              ; (player-controlled), roster slot 0 (Ralf)
    jsr Core_Oop_Create
    ; Core_Oop_Create's plp restores the ambient width from this call site
    ; (.a16/.i16, matching Anim_LoadCharacter's own exit convention) --
    ; TAD_Init below re-asserts its own required width explicitly anyway.
    ;
    ; --- Phase 8: point the camera at this entity (the player, always slot
    ; 0 -- see CLAUDE.md's "player is always slot 0" note) and set the
    ; playfield width to the boss level's real content width
    ; (WORLD_CONTENT_WIDTH, 336px/42 tiles -- out/bg_boss_level's
    ; content_width_tiles). Core_Screen_SetPlayfieldBorder derives
    ; Screen_MaxX = width - Screen_SizeX - 1 from that (336-256-1 = 79) --
    ; the exact max BG1 horizontal scroll this level allows, computed once
    ; here rather than hand-derived. Height/Y bounds are left at Core_
    ; Screen_Init's defaults (effectively unbounded) since nothing writes
    ; BG1VOFS -- no vertical scroll exists, matching plan.md Phase 8's
    ; scope limits. Core_Oop_Create just left OopLastHandle_Num/Id/Slot set
    ; to entity 0's own handle (its own @return contract), so those are
    ; still valid inputs to Core_Screen_Focus here. ---
    ; Playfield border width is set further below, AFTER Bg_LoadScene runs --
    ; for a BG_MODE_STREAMING level, the real content width isn't known until
    ; then (StreamScroll_WidthTiles, cached from the loaded bg_record). Using
    ; the boss level's hardcoded WORLD_CONTENT_WIDTH here unconditionally
    ; clamped Screen_MaxX to 79px for every streaming level too, so the
    ; camera could never scroll past world column ~9 -- Core_Screen_Play's
    ; own MaxX clamp (see core/screen.pasm) silently ate every later
    ; Screen_PosX write. Core_Screen_Init's own default (Screen_MaxX =
    ; $FFFF-SizeX, effectively unbounded) covers this one frame's
    ; FocusImmediate call just fine in the meantime.
    ; OopLastHandle_Id/Slot are documented "low byte valid" -- their high
    ; byte is never explicitly zeroed (Core_Oop__PackHandle writes them via
    ; an 8-bit `sta`, only touching the low byte). A raw 16-bit ldx/ldy of
    ; either silently carries WRAM garbage into the high byte. That garbage
    ; then propagates into Screen_FocusSlot and, from there, straight into
    ; Core_Oop_Call's slot-index arithmetic as an UNMASKED 16-bit index --
    ; found via a real, reproducible bug: entity 0 (the player) stopped
    ; being dispatched by Core_Oop_Play entirely, forever, from the first
    ; frame after this boot code ran (confirmed via Mesen2: CHAR_SELECTED/
    ; CHAR_FRAME_INDEX/CHAR_TICK_COUNTER frozen at their power-on defaults
    ; for the player specifically, while entities 1-3 kept animating
    ; normally). Mask to the valid low byte before use.
    lda OopLastHandle_Id
    and #$00ff
    tax
    lda OopLastHandle_Slot
    and #$00ff
    tay
    lda OopLastHandle_Num
    jsr Core_Screen_FocusImmediate  ; snap immediately -- player spawns at
                                      ; x=120, no reason to ease in from 0
    ;
    ; --- plan.md Phase 5: flush the DMA queue right after EACH entity's
    ; create, not just once after all four (as this code did before Phase
    ; 5). REAL BUG, found and fixed this phase: Anim_LoadCharacter streams
    ; each character's palette into ONE SHARED WRAM buffer
    ; (AnimPaletteStaging, a single fixed $7E2300 location, not per-
    ; instance) and only ENQUEUES a DMA request referencing that buffer's
    ; ADDRESS -- the actual hardware DMA (reading the buffer's CURRENT
    ; bytes) doesn't happen until Core_Dma_ProcessQueue runs. With exactly
    ; 2 entities (Phase 2-4's whole history), flushing once at the very end
    ; happened to always look correct, because the LAST entity loaded was
    ; always also the one whose real data was still sitting in the shared
    ; buffer at flush time -- entity 1's own palette IS whatever's there
    ; when the single flush runs. That coincidence breaks with 3+ entities:
    ; confirmed in Mesen2 that entities 1-3 all read back CGRAM slot 1's
    ; palette (2/JHUN's real colors) once role2/3 also loaded Ralf/JHUN in
    ; between, corrupting entities 1 and 2's own CGRAM writes to whatever
    ; the LAST load (entity 3) had left in the shared buffer -- only entity
    ; 0 (flushed here, before entity 1 ever overwrites the buffer) got its
    ; own correct data. Flushing after every single create instead means
    ; each entity's palette DMA fires while its own data is still the only
    ; thing in the buffer. Safe to call this early: forced blank has been
    ; continuously active since before this routine ran (nothing re-enables
    ; the screen until the explicit "PPU init (forced blank)" section
    ; below), matching the exact justification the original single
    ; end-of-routine call already relied on. ---
    jsr Core_Dma_ProcessQueue

    ; --- Entity #1: a second, simultaneous NPC -- roster slot 1 (JHUN),
    ; role 1 (own palette 1/tile-column 1). Phase 2 introduced it as
    ; static/idle-only to prove simultaneous rendering in isolation; Phase 3
    ; (plan.md, SNES-BOR-Engine-Prompt.md Sec 6.2) repurposed
    ; CharacterEntity_Init's role-1 branch to CHAR_INPUT_DRIVEN=2 instead,
    ; so this same entity now seeks Entity #0's position and attacks within
    ; range -- see Anim_Play/Character_PlayFrame's mode-2 branches. Still
    ; exercises everything Phase 2 proved (a second oop.pasm instance, OBJ
    ; palette, OBJ tile-column, OAM slot via Oam_CursorResetDone, and real
    ; concurrent MSU streaming under the Phase 0 serialization fix) plus
    ; now real per-frame position updates on top. ---
    lda.l CharacterClassId
    and #$00ff
    tay
    lda #$0101               ; init param -- role 1 (high byte), roster
                              ; slot 1 / JHUN (low byte)
    jsr Core_Oop_Create
    jsr Core_Dma_ProcessQueue    ; see Entity #0's create above -- flush
                                  ; per-entity, not once at the end

    ; --- Entity #2 and Entity #3: plan.md Phase 5 (scale to 4 entities).
    ; Only two characters exist in the roster (Ralf = slot 0, JHUN = slot
    ; 1 -- ROSTER_PREFIXES in build_rom.py), so role 2 reuses Ralf and role
    ; 3 reuses JHUN: two Ralfs, two JHUNs. Each instance still gets its own
    ; CGRAM palette slot (CharacterEntity_Init sets CHAR_PALETTE_SLOT before
    ; Anim_LoadCharacter's palette DMA reads it), so this is NOT a shared/
    ; aliased palette -- it's two independent CGRAM writes of the SAME
    ; source colors, which is exactly why two Ralfs render identically to
    ; each other (expected, not a bug -- see plan.md Phase 5 "asset
    ; question"). ---
    lda.l CharacterClassId
    and #$00ff
    tay
    lda #$0200               ; init param -- role 2 (high byte), roster
                              ; slot 0 / Ralf (low byte)
    jsr Core_Oop_Create
    jsr Core_Dma_ProcessQueue

    lda.l CharacterClassId
    and #$00ff
    tay
    lda #$0301               ; init param -- role 3 (high byte), roster
                              ; slot 1 / JHUN (low byte)
    jsr Core_Oop_Create
    jsr Core_Dma_ProcessQueue

    ; --- Phase 6: stream the static BG1 backdrop + BG3 HUD tileset. Runs
    ; AFTER every character load, because it re-seeks the MSU-1 data pointer
    ; for its own reads and would otherwise strand a half-finished character
    ; load. Still under forced blank here, which is what lets it pump the
    ; data port straight into the PPU with no WRAM staging. ---
    rep #$31
.a16
.i16
    jsr Bg_LoadScene

    ; Playfield border width, deferred to here (see the comment left at the
    ; old boot-time call site above) so a BG_MODE_STREAMING level's real
    ; width (StreamScroll_WidthTiles, just cached by Bg_LoadScene_Streaming
    ; above) is known. A BG_MODE_STATIC level (StreamScroll_Enabled stays 0
    ; -- Bg_LoadScene_Streaming never ran) keeps using the boss level's
    ; hardcoded WORLD_CONTENT_WIDTH, unchanged from before.
    sep #$20
.a8
    lda.l StreamScroll_Enabled
    bne Boot_SetPlayfieldBorder__streaming
    rep #$31
.a16
.i16
    ldy #WORLD_CONTENT_WIDTH
    bra Boot_SetPlayfieldBorder__go
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Boot_SetPlayfieldBorder__streaming:
    rep #$31
.a16
.i16
    lda.l StreamScroll_WidthTiles
    asl a
    asl a
    asl a                        ; tiles -> pixels (*8)
    tay
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Boot_SetPlayfieldBorder__go:
    lda #0
    ldx #0
    jsr Core_Screen_SetPlayfieldBorder

    ; WORLD_MAX_X, dynamic for streaming levels -- see WorldMaxX's own
    ; declaration comment for why. Reuses Y (still holding the content width
    ; in pixels, either WORLD_CONTENT_WIDTH or StreamScroll_WidthTiles*8 --
    ; see the branch above) instead of recomputing it: Core_Screen_
    ; SetPlayfieldBorder only ever reads Y via TYA, never clobbers it. This
    ; also keeps the boot code small -- this whole region sits ahead of
    ; nmi_handler's fixed $FF20 .org, which has silently truncated before
    ; when boot code grew past its margin (see CLAUDE.md's ".org truncation"
    ; note).
    tya
    sec
    sbc #(256 - PLAYER_MAX_X)    ; same right-edge margin WORLD_MAX_X uses
    sta.l WorldMaxX

    ; Force Hud_Play's first pass to draw: HudCachedHp is uninitialized WRAM
    ; here and could otherwise coincidentally match the entities' real starting
    ; HP, leaving the bars blank until the first hit landed.
    sep #$20
.a8
    lda #1
    sta.l HudDirty
    rep #$31
.a16
.i16

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

    ; BGMODE 1 + bit3 (BG3 priority): in mode 1, setting bit 3 lifts BG3's
    ; priority-1 tiles above BG1/BG2, which is what makes the BG3 HUD draw
    ; over the backdrop rather than behind it.
    lda #$09
    sta $2105               ; BGMODE = 1, BG3 high priority
    lda #$60
    sta $2107               ; BG1SC: tilemap at word $6000 (moved from $0400 --
                             ; BG1 tiles now occupy $0000-$1FFF, see Bg_LoadScene).
                             ; Placeholder only -- still forced-blank here, and
                             ; Bg_LoadScene (which already ran) set the real
                             ; value into the Nmi_Bg1TilemapVram shadow, which
                             ; overwrites this on the first NMI commit.
    lda #$68
    sta $2109               ; BG3SC: tilemap at word $6800 (Phase 8: moved
                             ; from $6400 to free room for a wider BG1 map)
    lda #$5C
    sta $2108               ; BG2SC: tilemap at word $5C00
    lda #$20
    sta $210B               ; BG12NBA: BG1 tiles $0000, BG2 tiles $2000
    lda #$05
    sta $210C               ; BG34NBA: BG3 tiles at word $5000
    lda #$05
    sta $212C               ; TM: BG1 + BG3 on main screen
    stz $212D               ; TS: nothing on subscreen
    lda #$80
    sta $420D               ; MEMSEL: FastROM

    ; --- CGRAM palette row 0 ---
    ; Was 16 hardcoded lda #imm/$2122 immediates (no ROM data table -- see
    ; poppy_assembler_bugs.md for why a standalone .dw table wasn't an
    ; option). Now streamed from the MSU-1 roster instead: each of
    ; msu1_done's entity creates already flushes its own palette DMA
    ; immediately (plan.md Phase 5 -- see Entity #0's create call site for
    ; why a single end-of-routine flush stopped being safe once 3+ entities
    ; share one staging buffer), so THIS call is now just a defensive no-op
    ; safety net in case anything else ever gets queued between here and
    ; the last per-entity flush -- draining an already-empty queue is a
    ; cheap check-and-return, not worth removing. Live reselect (Anim_Play,
    ; Select button) reuses the exact same Anim_LoadCharacter enqueue path
    ; and lets Core_Nmi_Play drain it normally instead, since forced blank
    ; isn't guaranteed there.
    jsr Core_Dma_ProcessQueue
    rep #$20
.a16

    ; --- VRAM: word increment on $2119 write ---
    sep #$20
.a8
    lda #$80
    sta $2115

    ; BG1's blank-tile-0 write and its all-zero 1024-entry tilemap fill used
    ; to sit here. Both are gone: Bg_LoadScene now streams a real backdrop
    ; (tiles to word $0000, tilemap to $6000) from bor.msu's v2 BG section,
    ; and the old fills would only have been overwritten. The BG3 tilemap is
    ; still cleared below, since the HUD writes only the few entries its bars
    ; occupy and the rest must not be power-on garbage.
    rep #$20
.a16

    ; --- BG3 tilemap at word $6800: clear all 1024 entries to tile 0 (blank,
    ; and blank is genuinely transparent on BG3 since HUD tile 0 is all
    ; color-index 0). ---
    lda #BG3_TILEMAP_VRAM_WORD
    sta $2116
    ldx #BG3_TILEMAP_WORDS
    lda #$0000
    nop
scpu_bg3_map:
    sta $2118
    dex
    bne scpu_bg3_map

    ; --- Phase 10 (plan.md 2.10) step 2b: BG3 frontpanel initial-viewport
    ; load. MUST run after the BG3 tilemap clear directly above -- see
    ; Bg_LoadScene__dispatch_streaming's own comment on why calling this
    ; from inside Bg_LoadScene was a real bug (the clear ran after and wiped
    ; it). Guarded on fp_offset (BgRecordStaging+28..30) being nonzero --
    ; not every BG record has a packed frontpanel. ---
    sep #$20
.a8
    lda.l BgRecordStaging+28
    ora.l BgRecordStaging+29
    ora.l BgRecordStaging+30
    beq Boot_LoadFp__skip
    rep #$31
.a16
.i16
    jsr Bg_LoadSceneFp_Streaming
    bra Boot_LoadFp__done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Boot_LoadFp__skip:
    rep #$31
.a16
.i16
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Boot_LoadFp__done:

    ; --- BG2 blank-tile write REMOVED (Phase 8, plan.md 2.7). It used to
    ; zero 16 words at VRAM word $2000 (BG2's char base, $210B=$20) so a
    ; stray BG2 tilemap reference would render zero instead of garbage --
    ; see git history around this comment for the full incident that write
    ; was fixing (real non-blank data at word $2000 rendering as full-
    ; screen noise, root-caused to a chrAddr unit-conversion mistake, NOT
    ; to this word ever needing blanking on purpose). That incident's fix
    ; is now redundant: BG2 is off the main screen (TM=$15=BG1+BG3+OBJ,
    ; below), and the SA-1 compositor that write was guarding against
    ; (Scpu_CcdmaPump) is dead code -- defined, never called, since the
    ; character moved to real OAM sprites. Keeping the write blocked BG1's
    ; tile budget at 512 (tile 512 sits at word $2000): raising it to 1024
    ; (10-bit tilemap limit, and where OBJ tiles start at $4000) needed
    ; only removing it. See tools/bg_converter/convert_bg.py's docstring.

    ; --- CC-DMA canvas pump: moved out of boot into Scpu_CcdmaPump, called
    ; once per frame from scpu_main_loop right after Core_Nmi_WaitFrame
    ; (vblank tail). The boot-time one-shot pump is gone deliberately: the
    ; SA-1 now runs a PERSISTENT recomposite loop (sa1_loop, $8000+) that
    ; re-arms CC-DMA for every fresh canvas and waits for the S-CPU to
    ; consume it, so the pump must be re-runnable every frame -- one 32-
    ; byte tile per frame, clearing SIC $2202 bit 5 (CharConvIrqFlag)
    ; once all COMPOSITOR_BLIT_COUNT*24 tiles are in VRAM, releasing the
    ; SA-1 to recomposite. A boot-time pump would also deadlock the new
    ; loop: it clears nothing, and the SA-1's first wait would hang on a
    ; flag only the per-frame pump consumes. The first main-loop frame
    ; simply pumps the canvas sa1_main armed at boot (flag set at boot).

    ; --- BG2 tilemap at word $5C00: COMPOSITOR_BLIT_COUNT 4x6 sprite windows
    ; packed in an 8-windows-wide row-major grid (rest blank), generated by
    ; a REAL indexed loop over (tx,ty) rather than one hand-written branch
    ; per window -- an earlier session's attempt to keep hand-unrolling
    ; this same style out to N=21 hit a real 65816 branch-range assembler
    ; wall (see the sa1_compositor_scaling_limit project memory); this
    ; version's code size is fixed regardless of N, so it doesn't.
    ;
    ; row_band = ty / 6 (which 6-tile-tall band of windows this row is in)
    ; and col_band = tx / 4 (which 4-tile-wide window within that band) are
    ; both tracked WITHOUT any divide instruction (65816 has none): col_band
    ; is tx>>2 since 4 is a power of 2, and row_band is an incrementing
    ; counter ($0A) bumped whenever a second counter tracking ty-within-
    ; band ($0C, "row_local") wraps past 5 at the end of a row -- cheaper
    ; and safer than a runtime division routine for a value that only
    ; changes once every 6 rows. window_index = row_band*8 + col_band (row-
    ; major), tile ID = window_index*24 + local_tx + local_ty*4 + 1 (+1
    ; because tile IDs are 1-based, 0 = blank), where local_ty = row_local
    ; and local_tx = tx&3 (tx mod 4, again via the power-of-2 shortcut).
    ; This is a plain arithmetic identity, not a lookup -- reduces to the
    ; old N<=3 hand-written formulas exactly for row_band=0 (window_index=0
    ; gives ty*4+tx+1, window_index=1 gives the old "+20" case) without
    ; spelling either out. A tile is blank whenever window_index >=
    ; COMPOSITOR_BLIT_COUNT -- this alone also correctly blanks every row
    ; entirely past the last real row band, since col_band=0 already pushes
    ; window_index past COMPOSITOR_BLIT_COUNT for a fully-out-of-range band;
    ; no separate "too many rows" check is needed. All real tiles get
    ; priority 1 ($2000 bit).
    rep #$20
.a16
    lda #$5C00
    sta $2116
    ldy #$0000              ; ty = 0..31
    stz $0A                 ; row_band = 0
    stz $0C                 ; row_local = ty within its row band, 0..5
    nop
scpu_tm_row:
    lda $0A
    asl
    asl
    asl                     ; row_band * 8 = this row's window-index base
    sta $0E
    ldx #$0000              ; tx = 0..31
    nop
scpu_tm_col:
    txa
    lsr
    lsr                     ; A = col_band = tx / 4 (window width = 4 tiles)
    clc
    adc $0E                 ; + row_band*8 = window_index
    cmp #COMPOSITOR_BLIT_COUNT
    bcc scpu_tm_win_ok       ; window_index < COMPOSITOR_BLIT_COUNT -> real window
    brl scpu_tm_blank
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
scpu_tm_win_ok:
    sta $02                 ; $02 = window_index
    asl
    asl
    asl
    asl                     ; window_index * 16
    sta $04
    lda $02
    asl
    asl
    asl                     ; window_index * 8
    clc
    adc $04                 ; window_index*16 + window_index*8 = window_index*24
    sta $04                 ; $04 = this window's tile-ID base
    lda $0C                 ; row_local (ty within its row band, 0..5)
    asl
    asl                     ; row_local * 4
    clc
    adc $04                 ; + window base
    sta $00                 ; $00 = window base + row_local*4
    txa
    and #$0003              ; local column = tx & 3 (tx mod 4)
    clc
    adc $00
    inc a                   ; +1 (tile IDs are 1-based)
    ora #$2000               ; priority 1
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
    ; --- row-band bookkeeping: row_local wraps every 6 rows, bumping row_band ---
    inc $0C
    lda $0C
    cmp #$0006
    bcc scpu_tm_row_no_bump
    stz $0C
    inc $0A
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
scpu_tm_row_no_bump:
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
    ;
    ; ROOT CAUSE FIX (found investigating a full-body character sprite
    ; static/noise regression): Core_Nmi_Init enables real hardware NMI
    ; (NMITIMEN=$81) below, but Oam_UploadFlag/Oam_HighWaterSlot aren't
    ; zeroed until Core_Oam_Init runs several instructions later -- and NMI
    ; is non-maskable, so a real vblank landing in that gap is not blocked
    ; by anything here. When it lands, nmi_handler -> Core_Nmi_Play sees
    ; Oam_UploadFlag as Mesen2's power-on-random WRAM garbage (almost
    ; always nonzero), takes the "do OAM reset" branch, and calls
    ; core/oam.pasm's Core_Oam_ClearActive with Oam_HighWaterSlot ALSO
    ; still garbage -- that value (divided by 4) becomes the main-table
    ; clear loop's iteration count, so a large garbage word turns into a
    ; massive out-of-bounds write starting at Oam_Buffer ($7E5100),
    ; stamping the OAM_DEFAULT_Y "hidden sprite" pattern hundreds of bytes
    ; past Oam_Buffer's real 512-byte extent. That overrun lands squarely
    ; on this file's own Anim_FrameIndex..Anim_AttackMsuBaseHi block
    ; ($7E53B0-$7E53C7, immediately after oam.pasm's own WRAM cells),
    ; zeroing CharSelect_Loaded/Anim_IdleFrameCount right after
    ; Anim_LoadCharacter had already populated them correctly at boot --
    ; confirmed via a write-hook trace showing the correct roster values
    ; land first (Core_Oam_Init/Core_Nmi_Init haven't run yet at that
    ; point), then get wiped by an OAM_DEFAULT_Y-shaped write burst spanning
    ; from $7E5100 through past $7E53CF on the very first real NMI. With
    ; CharSelect_Loaded stuck at 0, Anim_Play bails every frame before ever
    ; calling Msu1_LoadFrame, so the character's OBJ tiles in VRAM are never
    ; streamed and stay at raw VRAM garbage -- the observed full-body
    ; static. (Core_Oam_Init's later, correctly-bounded calls repair
    ; Oam_Buffer's own 512-byte range afterward, which is why that specific
    ; range reads clean in a post-boot snapshot even though this bug is
    ; real -- only the untouched-by-anything-else Anim_*/CharSelect_* cells
    ; past it stay corrupted permanently.)
    ;
    ; Fix: zero just the two WRAM cells Core_Oam_ClearActive actually reads
    ; before it can possibly run (the upload-flag gate and the high-water
    ; bound), ahead of enabling NMI. Neither is part of NmiShadow_Start..End
    ; ($7E5003-$7E5024ish) or Core_Oam_Init's own shadow range, so this
    ; doesn't fight the Nmi_ObjSel ordering requirement above -- it just
    ; makes Core_Oam_ClearActive a safe no-op (Oam_UploadFlag==0 skips it
    ; entirely) if a vblank lands before Core_Oam_Init's own full init runs.
    rep #$31
.a16
    lda #0
    sta.l Oam_UploadFlag
    sta.l Oam_HighWaterSlot

    jsr Core_Nmi_Init

    ; Belt-and-suspenders re-write: Core_Nmi_Init itself now sets this shadow
    ; to $80 (forced blank) before enabling NMITIMEN, so the real race this
    ; used to guard against (a vblank landing before this instruction and
    ; committing a stale brightness=0/unblank from the clear loop, corrupting
    ; the direct $2116/$2118/$2121/$2122 writes below) is already closed at
    ; the source. Confirmed load-bearing, not hypothetical: with Poppy's
    ; astrobleem fork (different boot cycle timing than the original
    ; toolchain), this exact race started landing deterministically and
    ; silently dropped Character_BlankPadding's VRAM writes until the
    ; Core_Nmi_Init fix went in. This write is now redundant but kept as
    ; harmless insurance.
    sep #$20
.a8
    lda #$80
    sta.l Nmi_ScreenBrightness
    rep #$20
.a16
    jsr Core_Oam_Init
    jsr TestSprite_Init
    jsr Character_BlankPadding

    sep #$20
.a8
    lda #$09             ; BGMODE 1 + BG3 priority (see the $2105 write above)
    sta.l Nmi_ScreenMode

    ; BG1SC: $60 (32x32) or $61 (64x32), from the bg_record's mode/width_tiles
    ; that Bg_LoadScene already read into BgRecordStaging (still valid --
    ; nothing writes that WRAM in between). Done HERE, after Core_Nmi_Init's
    ; shadow-clear loop, not inside Bg_LoadScene itself -- Bg_LoadScene runs
    ; earlier in scpu_boot, and Core_Nmi_Init unconditionally zeroes the
    ; whole NmiShadow_Start..End block, which silently wiped an earlier
    ; attempt to set this shadow from within Bg_LoadScene.
    ; STREAMING always forces the wide (64x32) map -- SyncScroll's future
    ; ring buffer needs both pages, and a streaming width_tiles (e.g. 688 for
    ; warehouse) would not match the static path's "cmp #64" test anyway
    ; (688 & $FF = $B0, not 64) even though this boot-only load only ever
    ; populates page A.
    lda.l BgRecordStaging+0     ; mode (u8)
    cmp #BG_MODE_STREAMING
    beq scpu_boot__bg1sc_wide
    lda.l BgRecordStaging+2
    cmp #64
    beq scpu_boot__bg1sc_wide
    lda #$60
    bra scpu_boot__bg1sc_done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
scpu_boot__bg1sc_wide:
    sep #$20
.a8
    lda #$61
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
scpu_boot__bg1sc_done:
    sta.l Nmi_Bg1TilemapVram

    lda #$68             ; BG3SC: tilemap at word $6800 (Phase 8: moved from
                          ; $6400 to free room for a wider BG1 map)
    sta.l Nmi_Bg3TilemapVram
    lda #$20
    sta.l Nmi_BgTilesVram12
    lda #$05             ; BG34NBA: BG3 tiles at word $5000
    sta.l Nmi_BgTilesVram34
    lda #$15             ; TM: BG1 + BG3 + OBJ ($01 | $04 | $10) on main screen
                          ; -- BG2 dropped: the BOR character no longer renders
                          ; into a BG2 tilemap window (see Msu1_LoadFrame), so
                          ; its tile content (still written every frame by the
                          ; SA-1 compositor) would sit as an inert visual ghost.
                          ; BG1 is now the real streamed backdrop; BG3 is the HUD.
    sta.l Nmi_MainScreen
    lda #$0F
    sta.l Nmi_ScreenBrightness

    ; Character animation state (FrameIndex/Selected/TickCounter) is no
    ; longer initialized here -- Anim_LoadCharacter (already called earlier,
    ; at msu1_done) sets it as part of its own force-immediate-frame-0-
    ; render trick; re-initializing it here would stomp that with stale
    ; values (FrameIndex=0/TickCounter=ANIM_FRAME_DELAY instead of the
    ; forced-refresh $FF/1) and bring back the old boot-time cosmetic pop
    ; Anim_LoadCharacter's version was written to avoid. CHAR_POS_X/Y (was
    ; Player_X/Y) is no longer initialized here either, same reasoning:
    ; it's DP-relative now (plan.md Phase 1b step 2), only correct when
    ; written with this object's window switched in -- moved into
    ; CharacterEntity_Init, right after the Anim_LoadCharacter call.
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

    ; Scpu_CcdmaPump (the SA-1 software-compositor pump from the "find the
    ; limit" N-scaling experiment) is no longer called here -- it targeted
    ; the same BG2 tile window the character used to render into, and its
    ; per-frame DMA/VRAM-write cost was pure overhead competing for the same
    ; already-tight vblank budget the real character rendering needs now.
    ; That whole compositor line of work was a genuine SA-1/CC-DMA hardware
    ; exploration (see sa1_compositor_scaling_limit project memory) but not
    ; the mechanism this project's actual characters render through -- see
    ; that memory for why (throughput: 24 frames per blit-window refresh,
    ; and BG2 is a single shared layer that can't host independently-moving
    ; actors regardless of pump speed).

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
    ; Anim_Play (updates Anim_FacingLeft via Anim_UpdateFacing, and streams a
    ; new frame into the character's OBJ tile slot on animation advance) and
    ; Character_PlayFrame now run via Core_Oop_Play -> CharacterEntity_Play,
    ; in that order (plan.md Phase 1a) -- no longer called directly here.
    ; Oam_CursorResetDone cleared once per frame right here, before dispatch
    ; -- see its own comment for why this has to be a global flag Character_
    ; PlayFrame checks-and-sets, not an unconditional reset (plan.md Phase 1b
    ; Step 3; single-entity today, but must be right by inspection now since
    ; there's no "renders identically" gate that would catch getting it
    ; backwards until Phase 2's second entity exists).
    sep #$20
.a8
    lda #0
    sta.l Oam_CursorResetDone
    rep #$31
.a16
    jsr Core_Oop_Play
    jsr Core_Screen_Play
    ; Phase 9 step 4 follow-up: clamp the just-eased camera position to what
    ; SyncScroll has actually resolved, BEFORE it's committed below -- see
    ; Core_StreamScroll_ClampCamera's own header comment for why.
    jsr Core_StreamScroll_ClampCamera
    ; Phase 8: commit the eased camera position to BG1's horizontal scroll
    ; shadow -- Core_Nmi_Play writes Nmi_Bg1ScrollX to $210D (write-twice,
    ; low then high byte) every vblank regardless, so this just has to keep
    ; the shadow current. Nmi_Bg1ScrollY is deliberately left untouched: no
    ; vertical scroll exists (see the playfield-height comment at msu1_done).
    lda Screen_PosX
    sta.l Nmi_Bg1ScrollX
    ; Phase 9 step 4: keep the streaming BG1 ring buffer in sync with the
    ; camera position just committed above. No-ops for a BG_MODE_STATIC
    ; level (the shipped boss build) and whenever an animation-frame stream
    ; still has DMAs in flight -- see Core_StreamScroll_Play's own header.
    jsr Core_StreamScroll_Play
    ; Phase 10 Step 2c (plan.md 2.10): same idea, for the BG3 frontpanel's
    ; own cache -- see Core_StreamScrollFp_Play's own header for the DMA-
    ; queue-sharing note (BG1 and FP may both enqueue in the same frame).
    jsr Core_StreamScrollFp_Play
    ; Hud_Play runs AFTER Core_Oop_Play (so it sees this frame's CHAR_HP, which
    ; Character_HitApply may have just changed) and BEFORE Core_Oam_Play. It is
    ; dirty-gated and enqueues nothing on a frame where no HP changed -- see its
    ; header for why that matters to the vblank budget.
    jsr Hud_Play
    jsr Core_Oam_Play
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
; Still comfortably below $FFE4 (native vector table). Pushed again, $FF20/
; $FF30 -> $FF40/$FF50, when Core_StreamScroll_ClampCamera's jsr call site
; grew scpu_main_loop past $FF20 by 2 bytes (build_rom.py's NMI/IRQ vector
; constants updated to match -- keep them in sync, nothing enforces this
; automatically). Pushed AGAIN, $FF40/$FF50 -> $FF60/$FF70, when Phase 10's
; (plan.md 2.10) BG3 frontpanel boot-time load call site grew scpu_boot and
; left only a 2-byte margin (tools/rom_audit/audit_all.py's own margin
; check caught it -- see that script's header for what it verifies).
.org $FF60
nmi_handler:
    jsr Core_Nmi_Play
    rti

.org $FF70
irq_handler:
    rti
