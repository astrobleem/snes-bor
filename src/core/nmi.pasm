; ============================================================================
; core/nmi.pasm — NMI (vblank) handler: shadow-register PPU sync.
;
; Ported (adapted, not literal) from SNES-SuperBossGaiden (src/core/nmi.65816
; + nmi.h), used with the original author's permission — see
; [[license-authorization-superbossgaiden]].
;
; Pattern: game code never writes PPU registers that change during gameplay
; (BG scroll, brightness, windowing, color math, screen/tilemap select,
; HDMA-channel-enable) directly — it writes the shadow copies below instead.
; Core_Nmi_Play, run once per vblank, commits every shadow register to
; hardware in one pass, drains core/dma.pasm's transfer queue (including any
; OAM upload core/oam.pasm queued this frame), and resets the OAM shadow
; buffer for the next frame. This is how register writes stay glitch-free
; without every call site having to reason about vblank timing itself.
;
; Deliberately smaller than upstream in one place: upstream's nmi.65816 also
; carries an 8-channel DMA_BUFFER + WRITE_DMA_BUFFER macro mechanism for
; retargeting an HDMA table's source mid-frame. Nothing in this project
; produces an HDMA effect yet (no hdma.*.pasm has been ported), so that
; mechanism would be unverifiable dead code — trimmed, same rationale
; core/dma.pasm's header gives for dropping 3 of upstream's 6 transfer types.
; HDMA-channel *enable* bits (which channels run at all, not what feeds them)
; are still shadowed below, ready for whenever the first HDMA effect exists.
;
; This project's Poppy build has no long (3-byte) addressing mode for INC or
; DEC, matching the already-documented absence of one for STZ (see
; core/dma_channel.pasm's header) — it doesn't error on `inc.l`/`dec.l`, it
; silently mis-encodes. Every counter here uses `lda.l` / `inc a` or `dec a`
; / `sta.l` instead. Indexed WRAM access is always `.l`, never `.w` (same
; project-wide rule as everywhere else). Every label used as a branch target
; gets a `nop` immediately before it, guarding against this Poppy build's
; branch-target address misresolution bug (see poppy_assembler_bugs.md
; project memory) — verify via the raw-byte alignment check after building,
; don't just trust that the guard was enough.
; ============================================================================

; --- Shadow registers, committed to hardware once per vblank ---
Nmi_FrameBusy         = $7E5000  ; .db — nonzero: main loop still working, skip visual commit
Nmi_Busy              = $7E5001  ; .db — nonzero: Core_Nmi_Play is already running (nested-NMI guard)
Nmi_FrameOver         = $7E5002  ; .db — set when a busy frame is detected, counts down
Nmi_InterruptFlags    = $7E5003  ; .db — shadow of NMITIMEN ($4200)
Nmi_ScreenBrightness  = $7E5004  ; .db — shadow of INIDISP ($2100)
Nmi_HdmaEnable        = $7E5005  ; .db — HDMA channels that SHOULD be active
Nmi_HdmaEnableCurrent = $7E5006  ; .db — HDMA channels actually written last commit
Nmi_Window12Sel       = $7E5007  ; .db — W12SEL ($2123)
Nmi_WindowObjSel      = $7E5008  ; .db — WOBJSEL ($2125)
Nmi_Window1L          = $7E5009  ; .db — WH0 ($2126)
Nmi_Window2L          = $7E500A  ; .db — WH2 ($2128)
Nmi_WindowBgLogic     = $7E500B  ; .db — WBGLOG ($212A)
Nmi_MainScreen        = $7E500C  ; .db — TM ($212C)
Nmi_WindowMainScreen  = $7E500D  ; .db — TMW ($212E)
Nmi_ColorMathControl  = $7E500E  ; .db — CGWSEL ($2130)
Nmi_ScreenMode        = $7E500F  ; .db — BGMODE ($2105)
Nmi_Bg1TilemapVram    = $7E5010  ; .db — BG1SC ($2107)
Nmi_Bg3TilemapVram    = $7E5011  ; .db — BG3SC ($2109)
Nmi_BgTilesVram12     = $7E5012  ; .db — BG12NBA ($210B)
Nmi_FixedColorR       = $7E5013  ; .db — 0-31, COLDATA red component
Nmi_FixedColorG       = $7E5014  ; .db — 0-31, COLDATA green component
Nmi_FixedColorB       = $7E5015  ; .db — 0-31, COLDATA blue component
Nmi_ObjSel            = $7E5016  ; .db — OBSEL ($2101)
Nmi_Bg1ScrollX        = $7E5017  ; .dw
Nmi_Bg1ScrollY        = $7E5019  ; .dw
Nmi_Bg2ScrollX        = $7E501B  ; .dw
Nmi_Bg2ScrollY        = $7E501D  ; .dw
Nmi_Bg3ScrollX        = $7E501F  ; .dw
Nmi_Bg3ScrollY        = $7E5021  ; .dw
Nmi_FrameCounter      = $7E5023  ; .dw — incremented every real (non-skipped) NMI

NmiShadow_Start = Nmi_FrameBusy
NmiShadow_End   = $7E5025

Core_Nmi_Init:
    php
    sep #$20
.a8
    lda #$80                 ; INIDISP: force blank while we set everything up
    ; Long addressing (bank $00 explicit) instead of a bare `sta $2100`:
    ; Core_Nmi_Init runs at the very start of scpu_boot's PPU setup, before
    ; anything in this project has ever established DBR=0 -- unlike
    ; Core_Nmi_Play (which forces DBR=0 itself every call, since it's
    ; reached from a real NMI with no guarantee either) this write had
    ; never been verified to actually land. Found via a real, visible bug:
    ; Core_Oam_Init's later one-time full-OAM-clear DMA (see oam.pasm)
    ; landed only partially/inconsistently until this was fixed too --
    ; consistent with forced blank never actually having been engaged, so
    ; whether an OAM write took effect depended on real scanline timing
    ; instead of being unconditionally safe.
    sta.l $002100

    rep #$31
.a16
    lda #0
    ldx #0
    nop
Core_Nmi_Init__clear_loop:
    sta.l NmiShadow_Start,x
    inx
    inx
    cpx #NmiShadow_End - NmiShadow_Start
    bcc Core_Nmi_Init__clear_loop

    sep #$20
.a8
    lda #$81                 ; NMITIMEN: NMI enable + auto-joypad-read
    sta.l Nmi_InterruptFlags
    sta.l $004200

    lda.l $004210              ; RDNMI: clear any pending nmi flag
    lda.l $004211              ; TIMEUP: clear any pending irq flag

    ; --- One-time commit of the window/color-math/fixed-color registers,
    ; moved out of Core_Nmi_Play's per-frame commit. Nothing in this
    ; codebase ever sets Nmi_Window12Sel/WindowObjSel/Window1L/Window2L/
    ; WindowBgLogic/WindowMainScreen/ColorMathControl/FixedColorR/G/B to
    ; anything but their zeroed shadow default (confirmed via a project-wide
    ; grep -- zero call sites write any of them, at all, anywhere), so
    ; re-writing them to hardware every single vblank was pure dead weight.
    ; Measured (via a temporary HVBJOY probe) to be a real contributor to a
    ; vblank-budget overrun once a per-frame OAM sprite (Character_PlayFrame)
    ; made the commit's steady-state cost much higher than when this
    ; register block was written. If a future feature ever needs windowing
    ; or color math, it should write these shadows directly AND go back to
    ; committing them every frame in Core_Nmi_Play (or add a dirty-flag
    ; gate) -- writing them here once is only correct as long as they truly
    ; never change after boot. ---
    stz $2123
    stz $2125
    stz $2126
    stz $2128
    stz $212A
    stz $212E
    stz $2130
    lda #$20                  ; COLDATA red-select bit, value 0
    sta $2132
    lda #$40                  ; COLDATA green-select bit, value 0
    sta $2132
    lda #$80                  ; COLDATA blue-select bit, value 0
    sta $2132

    rep #$31
.a16
    plp
    cli
    rts

; Run once per vblank (called from main.pasm's nmi_handler). Commits every
; shadow register above to hardware, drains the DMA queue, and resets the
; OAM shadow buffer if this frame uploaded one.
Core_Nmi_Play:
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd

    sep #$20
.a8
    lda #0
    pha
    plb                       ; DBR = 0, where all hardware registers live

    lda.l Nmi_FrameBusy
    ora.l Nmi_Busy
    beq Core_Nmi_Play__do_commit
    bra Core_Nmi_Play__frame_skipped
    nop
Core_Nmi_Play__frame_skipped:
    ; previous frame's processing isn't done yet — skip the visual commit,
    ; but keep whatever HDMA channels were already running going
    lda #2
    sta.l Nmi_FrameOver
    lda.l Nmi_HdmaEnableCurrent
    sta $420C                 ; HDMAEN
    brl Core_Nmi_Play__done   ; too far for an 8-bit bra from here
    nop

Core_Nmi_Play__do_commit:
    lda #0
    sta $420C                 ; HDMAEN: disable all while we update things
    sta.l Nmi_HdmaEnableCurrent

    lda #$80                  ; INIDISP: force blank for the duration of the commit
    sta $2100

    rep #$31
.a16
    jsr Core_Dma_ProcessQueue

    sep #$20
.a8
    lda.l Oam_UploadFlag
    beq Core_Nmi_Play__skip_oam_reset
    bra Core_Nmi_Play__do_oam_reset
    nop
Core_Nmi_Play__do_oam_reset:
    jsr Core_Oam_ClearActive
    ; Core_Oam_ClearActive does `rep #$31` internally and never restores
    ; 8-bit mode before its rts (same calling convention as
    ; Core_Oam_ClearAll, its full-table counterpart used only by
    ; Core_Oam_Init at boot) -- so this call site, which needs 8-bit to
    ; continue, must re-assert it itself rather than assume the width it
    ; had before the call still holds.
    sep #$20
.a8
    lda #0
    sta.l Oam_UploadFlag
    nop                       ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Core_Nmi_Play__skip_oam_reset:

    lda #1
    sta.l Nmi_Busy

    lda.l Nmi_ScreenBrightness
    sta $2100

    lda.l Nmi_HdmaEnable
    sta $420C
    sta.l Nmi_HdmaEnableCurrent

    ; Window regs (W12SEL/WOBJSEL/WH0/WH2/WBGLOG/WOBJLOG/CGWSEL) and the
    ; fixed color (COLDATA) are committed once, at boot, by Core_Nmi_Init --
    ; nothing in this codebase ever changes their shadows away from 0, so
    ; re-writing them here every vblank was pure dead weight that ate into
    ; the frame's vblank budget. See Core_Nmi_Init for the one-time commit.
    lda.l Nmi_MainScreen
    sta $212C
    lda.l Nmi_ScreenMode
    sta $2105
    lda.l Nmi_Bg1TilemapVram
    sta $2107
    lda.l Nmi_Bg3TilemapVram
    sta $2109
    lda.l Nmi_BgTilesVram12
    sta $210B
    lda.l Nmi_ObjSel
    sta $2101

    ; BGnHOFS/VOFS are write-twice registers: low byte then high byte, same
    ; address, latched internally by the PPU.
    lda.l Nmi_Bg1ScrollX
    sta $210D
    lda.l Nmi_Bg1ScrollX+1
    sta $210D
    lda.l Nmi_Bg1ScrollY
    sta $210E
    lda.l Nmi_Bg1ScrollY+1
    sta $210E
    lda.l Nmi_Bg2ScrollX
    sta $210F
    lda.l Nmi_Bg2ScrollX+1
    sta $210F
    lda.l Nmi_Bg2ScrollY
    sta $2110
    lda.l Nmi_Bg2ScrollY+1
    sta $2110
    lda.l Nmi_Bg3ScrollX
    sta $2111
    lda.l Nmi_Bg3ScrollX+1
    sta $2111
    lda.l Nmi_Bg3ScrollY
    sta $2112
    lda.l Nmi_Bg3ScrollY+1
    sta $2112

    rep #$31
.a16
    lda.l Nmi_FrameCounter
    inc a
    sta.l Nmi_FrameCounter

    sep #$20
.a8
    lda.l Nmi_InterruptFlags
    sta $4200                 ; NMITIMEN

    lda #0
    sta.l Nmi_Busy

    lda.l Nmi_FrameOver
    beq Core_Nmi_Play__done
    dec a
    sta.l Nmi_FrameOver

Core_Nmi_Play__done:
    lda $4210                  ; RDNMI: acknowledge the nmi flag
    rep #$30
.a16
    pld
    plb
    ply
    plx
    pla
    rts

; Temporarily disables NMI. Re-enable with Core_Nmi_Start. Useful around a
; sequence that would be corrupted by an NMI firing mid-way through.
Core_Nmi_Stop:
    php
    sep #$20
.a8
    lda.l Nmi_InterruptFlags
    and #$7F                  ; clear NMI-enable bit, leave auto-joy-read alone
    sta $4200
    plp
    rts

Core_Nmi_Start:
    php
    sep #$20
.a8
    lda.l Nmi_InterruptFlags
    sta $4200
    plp
    rts

Core_Nmi_BlankScreen:
    php
    sep #$20
.a8
    lda #0
    sta $420C                  ; HDMAEN: disable all channels
    sta.l Nmi_HdmaEnableCurrent

    lda #$80
    sta $2100                  ; INIDISP: force blank
    plp
    rts

; Busy-waits for the next real NMI. Dangerous if NMI is ever stopped
; (Core_Nmi_Stop) without a matching Core_Nmi_Start — hangs forever.
Core_Nmi_WaitFrame:
    rep #$31
.a16
    lda.l Nmi_FrameCounter
    nop
Core_Nmi_WaitFrame__loop:
    cmp.l Nmi_FrameCounter
    beq Core_Nmi_WaitFrame__loop
    rts
