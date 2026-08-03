; ============================================================================
; Beats of Rage SNES — SA-1 + CC-DMA + MSU-1 + Terrific Audio Driver (TAD)
; Poppy assembler, LoROM + SA-1 (map mode $23, cart type $35)
; ============================================================================

.snes

BW_CANVAS   = $606000   ; canvas: 128x96 4bpp linear at SA-1 BW-RAM $60:6000

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

    ; --- Draw a 32x48 real sprite frame, extracted and converted from the
    ; game's own asset pack (not hand-authored/synthetic anymore) ---
    ; Source: DATA\CHARS\RALF\IDLE1.GIF inside
    ; "Beats of Rage Original [v.3.0 Build 4086].pak" (an indexed-color GIF,
    ; magenta $FC00FF background/transparency marker per BOR convention).
    ; Cropped to its real bounding box, nearest-neighbor scaled to fit
    ; 32x48 (feet-aligned to the bottom, matching BOR's hotspot
    ; convention), then quantized to 15 colors + reserved index 0 (mapped
    ; to black, this canvas's real backdrop) via
    ; tools/bor_converter/convert_real_sprite.py. See that script's header
    ; for the PAK archive format (reverse-engineered from OpenBOR's own
    ; packfile.c: `PACK`+version header, file data, then a directory table
    ; at the END of the file with a trailing 4-byte offset pointing back to
    ; it -- there is no compression or real encryption, despite "encrypted
    ; archive" being the common description).
    ; Drawn tightly packed at BW_CANVAS+0 (32 bytes/row, no padding).
    ; CC-DMA's BW-RAM source is byte-per-pixel (one byte = one pixel,
    ; color index in the low nibble), NOT nibble-packed 2px/byte --
    ; feeding it a nibble-packed 768-byte buffer made it consume 768
    ; "pixels" (1.5 real rows) instead of the intended 24 tiles, which is
    ; why the converted VRAM output was noise rather than the sprite.
    ; CC-DMA's source row pitch is implicitly SSS (configured tile width
    ; below), so the source data's actual layout must match it exactly or
    ; every row after the first reads from the wrong offset.
    ;
    ; Note: the source read below is plain absolute (not .l) indexed by Y
    ; -- the 65816 has no indexed-long addressing mode with Y at all
    ; (only X supports addr24,X); writing `.l ...,y` doesn't error in
    ; this Poppy build, it silently falls back to 3-byte absolute,Y while
    ; still apparently budgeting 4 bytes internally, which shifts every
    ; following byte by one and corrupts the next instruction. Explicit
    ; DB=0 here so the plain-absolute Y-indexed read is guaranteed
    ; correct (TestSprite32x48 lives in this same bank) rather than
    ; assuming SA-1's default DB happens to still be 0.
    sep #$20
.a8
    lda #0
    pha
    plb                     ; DBR = 0, where TestSprite32x48 lives
    rep #$30
.a16
.i16
    stz $00                 ; row = 0..47
    stz $02                 ; source offset into TestSprite32x48, 0..1535
sa1_sprite_row_loop:
    lda $00
    asl
    asl
    asl
    asl
    asl                     ; row * 32 (byte-per-pixel source: 32 px/row)
    tax                     ; X = dest byte offset into BW_CANVAS this row

    ldy $02                 ; Y = source byte offset, carried across rows
    stz $04                 ; col = 0..31 (bytes this row)
sa1_sprite_col_loop:
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
    bcc sa1_sprite_col_loop

    sty $02                 ; persist source offset for next row

    inc $00
    lda $00
    cmp #$0030              ; 48 rows
    bcc sa1_sprite_row_loop

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
    ; Mesen2 core: CpuBwRamHandler::Read -> Sa1::ReadCharConvertType1).
    ; Our sprite is drawn via `sta.l BW_CANVAS,x` where BW_CANVAS=$606000 --
    ; the $60-6F bank range is hard-wired "always bitmap mode" (see
    ; Sa1BwRamHandler::WriteBitmapMode), which auto-packs each byte we
    ; write (low nibble = one pixel's color) two-per-real-byte at HALF the
    ; window offset, with the $600000 bank component subtracted first:
    ; real bwRam offset = ((BW_CANVAS & $1FFFFF) + x) >> 1 = ($6000+x) >> 1,
    ; i.e. our packed sprite bytes actually live at real BW-RAM offset
    ; $3000, not $6000 and not $0. SDA must equal that real offset ($3000)
    ; for CC-DMA's tile/address math to land on our data; reading the
    ; converted bytes back out then requires reading through $40:3000+ (see
    ; scpu_pump_loop below), NOT the $3000 S-CPU I-RAM window (a read from
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
    stz $2236               ; write dest mid byte -> arms CharConvDmaActive
                             ; (conversion itself still hasn't run yet -- see above)

    ; --- Signal S-CPU: canvas ready ---
    ; No explicit flag write needed: the $2236 write above (CharConv DMA
    ; Auto Mode trigger) makes the SA-1 hardware set CharConvIrqFlag
    ; (SFR bit 5, $2300) automatically. The old BW_READY/READY_MAGIC
    ; flag in BW-RAM bank $41 never worked: that bank is the S-CPU's
    ; paged/BMAPS-relative BW-RAM window, not a direct mirror, so the
    ; S-CPU could never see what SA-1 wrote there. See scpu_poll below.

sa1_spin:
    bra sa1_spin

; 32x48 4bpp linear-packed test sprite (768 bytes), hand-authored to
; validate the CC-DMA pipeline end-to-end -- see gen_sprite_bin.py-style
; generation notes: 24 uniquely-colored 8x8 tiles plus a white/black X
; overlay across the whole sprite, so both per-tile addressing AND
; within-tile multi-color nibble packing get exercised, not just a
; uniform test block.
TestSprite32x48:
    .incbin "assets/test_sprite_32x48.bin"

; ============================================================================
; TAD Audio Driver Module (Ported from ca65 to Poppy .pasm)
; ============================================================================
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
    .incbin "assets/anim_ralf_walk.bin"        ; 8 frames * 768 = 6144 bytes
    .incbin "assets/anim_tilemap_right.bin"    ; 48 bytes
    .incbin "assets/anim_tilemap_left.bin"     ; 48 bytes
    ; ends at $8C00 + 6240 = $A5E0, leaving ~1952 bytes free before $AC00.

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
; Idle has 6 frames (delay 10, loop=1 in out/ralf_idle/manifest.json); walk
; is the full 8-frame source cycle (delay 8, loop=1 in
; out/ralf_walk/manifest.json); attack is the full 5-frame "attack1" cycle
; (loop=0 in out/ralf_attack/manifest.json, non-looping). All three are full
; cycles, not trimmed subsets -- see the WALK_FRAME_COUNT/ATTACK_FRAME_COUNT
; notes below and the TAD-gap relocation comment above Tad_IsSongPlaying's
; `.org $8C00` block for how the ROM-space budget was solved without
; trimming.
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
ANIM_FRAME_COUNT = 6
ANIM_FRAME_DELAY = 10        ; ticks (main-loop frames) per idle frame
ANIM_FRAME_BYTES = 768       ; 24 tiles * 32 bytes/tile, 4bpp (all three anims)
ANIM_VRAM_DEST_BYTE = $4020  ; = word $2010 * 2 -- same BG2 window the
                              ; static sprite already occupies (tiles 1..24)
; Attack button: Y (bit14 overall = bit6 of Input_trigger's high byte, per
; core/input.pasm's $4218 layout comment "B Y Sel Start U D L R | A X L R
; 0000"). Edge-triggered (Input_trigger, not Input_press) so holding Y
; doesn't re-trigger every frame -- checked in Anim_Play's dispatcher below.
ANIM_ATTACK_BUTTON_MASK = $40
; WALK_FRAME_COUNT/ATTACK_FRAME_COUNT: both now the FULL source cycle (8 and
; 5 frames respectively), no longer trimmed subsets. Previously the
; $C100-$FC00 code+data window's fixed 15104-byte budget forced walk down to
; 3 frames and attack to 3 frames (a first attempt at baking all 8 walk
; frames silently truncated the last 768 bytes -- Poppy gives no error for
; .org overflow, see CLAUDE.md's "Fixed .org directives silently truncate").
; This session moved the walk blob (and the facing-flip tilemap blobs) out
; of this window entirely, into TAD S-CPU-management slack at $8C00 (see the
; large comment above Tad_IsSongPlaying's `.org $8C00` block) -- freeing
; enough room here to restore both walk and attack to their full frame
; counts without re-trimming anything. Re-verify actual margin (raw-byte
; diff, not just "the build didn't error") before adding more content to
; either window.
WALK_FRAME_COUNT = 8
WALK_FRAME_DELAY = 8         ; ticks (main-loop frames) per walk frame
ATTACK_FRAME_COUNT = 5
ATTACK_FRAME_DELAY = 10      ; ticks; manifest (out/ralf_attack/manifest.json)
                              ; has per-frame delays 7,7,20,10,10 -- collapsed
                              ; to one fixed value like idle/walk

; AnimRalfIdleFrames's own label value resolves 1 byte EARLY here -- a new
; instance of the same Poppy address-estimation class documented elsewhere
; in this project (poppy_assembler_bugs.md), but this time affecting a data
; label used as an immediate VALUE rather than a branch/jsr target, so the
; usual "pad with nop" trick doesn't apply (a data pointer can't "fall
; through" the way code can). Confirmed by direct raw-byte inspection of
; src/main.bin: Anim_Play_Idle__done's own body (also nop-guarded, so its
; label is ALSO 1 byte early) is exactly 4 bytes (nop/rep #$31/rts) starting
; at Anim_Play_Idle__done's reported symbol address, which puts
; AnimRalfIdleFrames's TRUE first byte 1 byte after where the symbol table
; (and this label used in an expression) reports it. Cross-checked against a
; live Mesen DMA transfer before this fixup was added: frame N's VRAM data
; was a clean 1-byte right-shift of the intended frame, with the extra
; leading byte matching the ROM byte immediately BEFORE AnimRalfIdleFrames's
; true start (frame 0 case) / the previous frame's true last byte (frame 3
; case) -- i.e. every computed source address was exactly 1 too low. If this
; file's layout changes enough to shift this drift, re-verify with the same
; raw-byte method (see build.md's Testing section) rather than assuming +1
; is still correct.
;
; ANIM_ATTACK_BASE_OFFSET (poppy bug #8 workaround, same as before):
; AnimRalfAttackFrames must NEVER be referenced directly in an expression --
; a bare `lda #AnimRalfAttackFrames + N` would silently resolve to the SAME
; address as AnimRalfIdleFrames (the first of two adjacent back-to-back
; .incbin labels), not its own; see poppy_assembler_bugs.md bug #8. Compute
; attack's frame addresses from the known-good AnimRalfIdleFrames label plus
; a compile-time-constant byte offset instead -- attack now follows idle
; directly (walk no longer sits between them; it lives at ANIM_WALK_BASE in
; the TAD gap instead, see below), so the offset is simply idle's own total
; size.
ANIM_LABEL_FIXUP = 1
ANIM_ATTACK_BASE_OFFSET = ANIM_FRAME_COUNT * ANIM_FRAME_BYTES   ; = idle
                              ; blob's total size; AnimRalfAttackFrames's
                              ; .incbin immediately follows AnimRalfIdleFrames's
                              ; with no gap, so this is its exact byte offset

; ANIM_WALK_BASE / ANIM_TILEMAP_RIGHT_BASE / ANIM_TILEMAP_LEFT_BASE: these
; three blobs now live in the TAD S-CPU-management gap at a literal fixed
; `.org $8C00` (see the large comment above Tad_IsSongPlaying's `.org $8C00`
; block, near the top of this file) rather than in this $C100-$FC00 window.
; Deliberately literal hex constants, NOT expressions involving a
; Poppy-estimated label address (unlike AnimRalfIdleFrames/AnimRalfAttackFrames
; above): `.org` is documented (and independently verified by
; tools/rom_audit/verify_layout.py) to reset Poppy's CurrentAddress to
; exactly its operand value in BOTH the address-estimation pass and the real
; code-generation pass, so a literal `.org` target can't drift the way an
; estimated label can -- these constants need no ANIM_LABEL_FIXUP-style
; correction and no bug #8 offset-from-another-label workaround, because
; nothing here asks Poppy to report a label's address at all.
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
ANIM_TILEMAP_RIGHT_BASE = ANIM_WALK_BASE + (WALK_FRAME_COUNT * ANIM_FRAME_BYTES)
ANIM_TILEMAP_LEFT_BASE = ANIM_TILEMAP_RIGHT_BASE + (6 * ANIM_TILEMAP_ROW_BYTES)

Anim_FrameIndex  = $7E53B0   ; .db -- current frame of the active animation
Anim_TickCounter = $7E53B1   ; .db -- frames remaining until next advance
Anim_Selected    = $7E53B2   ; .db -- 0 = idle, 1 = walk, 2 = attack (which anim is live)
Anim_FacingLeft  = $7E53B3   ; .db -- 0 = facing right (boot default), 1 = facing left

; TestSprite_PlayFrame's own state for the second, independently-moving
; test sprite -- see that routine's header, below TestSprite_WriteSolidTile.
TestSprite2_X       = $7E53B4 ; .db -- sprite 1's current X, bounces between MIN/MAX
TestSprite2_DirLeft = $7E53B5 ; .db -- 0 = moving right, 1 = moving left
TESTSPRITE2_MIN_X = 8
TESTSPRITE2_MAX_X = 216         ; 16px sprite, keeps it fully on the 256px screen
TESTSPRITE2_SPEED = 2

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

; Advances Ralf's idle animation by one tick per call and, on frame-change,
; enqueues a VRAM DMA blit of the new frame's precomputed tile data through
; core/dma.pasm's queue -- same mechanism every other VRAM update in this
; project uses, drained during forced-blank/vblank by Core_Nmi_Play. This is
; deliberately queued, not an immediate DMA: an unconditional-every-frame
; immediate transfer is exactly the bug class that broke Core_Oam_Play
; earlier (see the Core_Nmi_WaitFrame comment above scpu_main_loop) --
; queuing means the transfer only ever gets registered once per real
; ANIM_FRAME_DELAY-frame advance, and Core_Dma_ProcessQueue's own budget cap
; (DMA_TRANSFER_MAX_BYTES, comfortably above this transfer's 768 bytes)
; still applies as a backstop. Only called while Anim_Selected == 0 (see
; Anim_Play above); exits in .a16/.i16, same convention as Anim_Play.
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

    lda #ANIM_FRAME_DELAY
    sta.l Anim_TickCounter

    lda.l Anim_FrameIndex
    inc a
    sta.l Anim_FrameIndex
    cmp #ANIM_FRAME_COUNT
    bcc Anim_Play_Idle__frame_ok
    lda #0
    sta.l Anim_FrameIndex        ; wrap (manifest loop=1)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__frame_ok:

    ; frame_index -> source ROM address, via compare chain (no data table,
    ; no indexed-long addressing to a ROM data label -- both silently
    ; miscompile in this Poppy build; see poppy_assembler_bugs.md).
    lda.l Anim_FrameIndex
    cmp #0
    beq Anim_Play_Idle__f0
    cmp #1
    beq Anim_Play_Idle__f1
    cmp #2
    beq Anim_Play_Idle__f2
    cmp #3
    beq Anim_Play_Idle__f3
    cmp #4
    beq Anim_Play_Idle__f4
    bra Anim_Play_Idle__f5
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__f0:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__f1:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_FRAME_BYTES
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__f2:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_FRAME_BYTES*2
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__f3:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_FRAME_BYTES*3
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__f4:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_FRAME_BYTES*4
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Idle__f5:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_FRAME_BYTES*5
    jsr Anim_CommitFrame
    rts

; Same structure as Anim_Play_Idle above, targeting the full 8-frame walk
; cycle (blob relocated to ANIM_WALK_BASE in the TAD gap, see the constant's
; definition above). Only called while Anim_Selected == 1 (see Anim_Play
; above).
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

    lda #WALK_FRAME_DELAY
    sta.l Anim_TickCounter

    lda.l Anim_FrameIndex
    inc a
    sta.l Anim_FrameIndex
    cmp #WALK_FRAME_COUNT
    bcc Anim_Play_Walk__frame_ok
    lda #0
    sta.l Anim_FrameIndex        ; wrap (manifest loop=1)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__frame_ok:

    lda.l Anim_FrameIndex
    cmp #0
    beq Anim_Play_Walk__f0
    cmp #1
    beq Anim_Play_Walk__f1
    cmp #2
    beq Anim_Play_Walk__f2
    cmp #3
    beq Anim_Play_Walk__f3
    cmp #4
    beq Anim_Play_Walk__f4
    cmp #5
    beq Anim_Play_Walk__f5
    cmp #6
    beq Anim_Play_Walk__f6
    bra Anim_Play_Walk__f7
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__f0:
    rep #$20
.a16
    lda #ANIM_WALK_BASE
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__f1:
    rep #$20
.a16
    lda #ANIM_WALK_BASE + ANIM_FRAME_BYTES
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__f2:
    rep #$20
.a16
    lda #ANIM_WALK_BASE + ANIM_FRAME_BYTES*2
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__f3:
    rep #$20
.a16
    lda #ANIM_WALK_BASE + ANIM_FRAME_BYTES*3
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__f4:
    rep #$20
.a16
    lda #ANIM_WALK_BASE + ANIM_FRAME_BYTES*4
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__f5:
    rep #$20
.a16
    lda #ANIM_WALK_BASE + ANIM_FRAME_BYTES*5
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__f6:
    rep #$20
.a16
    lda #ANIM_WALK_BASE + ANIM_FRAME_BYTES*6
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Walk__f7:
    rep #$20
.a16
    lda #ANIM_WALK_BASE + ANIM_FRAME_BYTES*7
    jsr Anim_CommitFrame
    rts

; Same structure as Anim_Play_Idle/Walk above, targeting the full 5-frame
; "attack1" cycle. Only called while Anim_Selected == 2 (see Anim_Play
; above). Non-looping (manifest loop=0):
; on reaching the last frame, reverts Anim_Selected to 0 (idle) and forces
; an immediate frame-0 idle render next call -- same "frame -1 forces
; immediate advance" trick Anim_Play's top-level selection-change path
; uses -- rather than wrapping back to frame 0 of the attack cycle.
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
    cmp #ATTACK_FRAME_COUNT
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
    lda #ATTACK_FRAME_DELAY
    sta.l Anim_TickCounter

    ; frame_index -> source ROM address, via compare chain (no data table,
    ; no indexed-long addressing to a ROM data label -- both silently
    ; miscompile in this Poppy build; see poppy_assembler_bugs.md).
    lda.l Anim_FrameIndex
    cmp #0
    beq Anim_Play_Attack__f0
    cmp #1
    beq Anim_Play_Attack__f1
    cmp #2
    beq Anim_Play_Attack__f2
    cmp #3
    beq Anim_Play_Attack__f3
    bra Anim_Play_Attack__f4
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__f0:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_ATTACK_BASE_OFFSET
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__f1:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_ATTACK_BASE_OFFSET + ANIM_FRAME_BYTES
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__f2:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_ATTACK_BASE_OFFSET + ANIM_FRAME_BYTES*2
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__f3:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_ATTACK_BASE_OFFSET + ANIM_FRAME_BYTES*3
    jsr Anim_CommitFrame
    rts
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Anim_Play_Attack__f4:
    rep #$20
.a16
    lda #AnimRalfIdleFrames + ANIM_LABEL_FIXUP + ANIM_ATTACK_BASE_OFFSET + ANIM_FRAME_BYTES*4
    jsr Anim_CommitFrame
    rts

; Shared DMA-commit tail for Anim_Play_Idle/Walk/Attack above (and any
; future Anim_Play_* routine): enqueues a VRAM DMA blit of the frame whose
; source address is in the (16-bit) accumulator on entry. Extracted from
; three near-identical copies (one per animation) to reclaim ROM space in
; this already-tight $C100-$FC00 window -- every animation added after
; idle+walk needs this same boilerplate, so de-duplicating it here makes
; each new animation cheaper, not just this one. Exits in .a16/.i16,
; matching every Anim_Play_* caller's expected convention; callers just
; `rts` immediately after this returns.
    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)
Anim_CommitFrame:
    sta.l DmaRequest_SourceAddrLow
    lda #ANIM_VRAM_DEST_BYTE
    sta.l DmaRequest_TargetAddr
    lda #ANIM_FRAME_BYTES
    sta.l DmaRequest_Length

    sep #$20
.a8
    lda #0
    sta.l DmaRequest_SourceBank   ; all three anim blobs live in bank 0
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags

    rep #$31
.a16
.i16
    jsr Core_Dma_Enqueue
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
; needs plane0 set (see below), so there's no separate data blob to place
; (and no bug #8 risk from a second .incbin adjacent to
; AnimRalfIdleFrames/AnimRalfAttackFrames below).
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
; called every frame from scpu_main_loop before Core_Oam_Play) that keeps
; sprite 0 alive going forward. That's not optional decoration: Core_Nmi_Play
; wipes the *shadow* Oam_Buffer/Oam_ExpandedHi back to "every sprite hidden"
; after every successful upload (see Core_Oam_ClearAll and oam.pasm's
; Core_Oam_Play header), but leaves real hardware OAM itself untouched. So
; the instant anything else calls Core_Oam_Play with a nonzero
; Oam_CurrentSlot -- which TestSprite_PlayFrame's own sprite 1 now does,
; every frame -- that DMA will overwrite sprite 0's slot with the shadow's
; cleared state (Y=$F0, size bit back to 0) unless sprite 0's entry gets
; re-written into the shadow buffer first. TestSprite_PlayFrame re-asserts
; sprite 0's identical literal values (X=120, Y=100, tile=0, attr=$30,
; hi=$02) every frame for exactly this reason -- don't remove that half of
; it while only meaning to touch sprite 1.
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

; Sole per-frame OAM writer, called once/frame from scpu_main_loop before
; Core_Oam_Play. Because Core_Nmi_Play wipes the ENTIRE OAM shadow back to
; "all hidden" after every successful upload (see Core_Oam_ClearAll and
; TestSprite_Init's own header comment above), the instant this routine
; makes a second Core_Oam_Play call happen with a nonzero cursor, sprite
; 0's slot would get stomped with the shadow's cleared state unless it's
; re-written here too -- so this routine re-asserts BOTH sprites every
; frame, not just the new one. Forces Oam_CurrentSlot to 0 up front rather
; than trusting its leftover value, making this routine idempotent
; regardless of Core_Nmi_Play/ClearAll timing (its very first call happens
; before any NMI has run ClearAll, so the cursor is still 4 from
; TestSprite_Init otherwise). Sprite 1 reuses the same solid-red 16x16 tile
; (OBJ base tile 0) TestSprite_Init already wrote -- no new VRAM/CGRAM data
; needed. Must be called in .a16/.i16 and returns the same way, matching
; scpu_main_loop's convention.
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

    ; --- sprite 1: ping-pong X bounce, Y fixed. Unsigned cmp/bcc/bcs on
    ; purpose -- TESTSPRITE2_MAX_X (216) has bit7 set, so a signed bmi/bpl
    ; branch would misfire near the boundary. ---
    sep #$20
.a8
    lda.l TestSprite2_DirLeft
    bne TestSprite_PlayFrame__moving_left
    bra TestSprite_PlayFrame__moving_right
    nop
TestSprite_PlayFrame__moving_right:
    lda.l TestSprite2_X
    clc
    adc #TESTSPRITE2_SPEED
    cmp #TESTSPRITE2_MAX_X + 1
    bcc TestSprite_PlayFrame__store_x
    lda #1
    sta.l TestSprite2_DirLeft
    lda #TESTSPRITE2_MAX_X
    bra TestSprite_PlayFrame__store_x
    nop
TestSprite_PlayFrame__moving_left:
    lda.l TestSprite2_X
    sec
    sbc #TESTSPRITE2_SPEED
    cmp #TESTSPRITE2_MIN_X
    bcs TestSprite_PlayFrame__store_x
    lda #0
    sta.l TestSprite2_DirLeft
    lda #TESTSPRITE2_MIN_X
    nop
TestSprite_PlayFrame__store_x:
    sta.l TestSprite2_X
    sta.l OamSetSprite_X
    lda #150
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

; Precomputed VRAM-format tile data referenced by Anim_Play_Idle/
; Anim_Play_Attack above (forward immediate-address references only, not
; indexed/branch -- placed AFTER all of their branches deliberately: with a
; blob like this sitting BEFORE the branching code instead, Poppy's
; branch-range check failed every branch with "out of range" errors whose
; reported distances lined up with the blob's size, even though none of the
; real branch targets were more than a few dozen bytes away -- a large
; inline .incbin ahead of branching code perturbs Poppy's address
; estimation. Keep large data blobs after the code that branches, not
; before, matching TestSprite32x48's placement after sa1_spin's last
; branch. Walk's blob (and the facing-flip tilemap blobs) no longer live
; here -- relocated to ANIM_WALK_BASE/ANIM_TILEMAP_RIGHT_BASE/
; ANIM_TILEMAP_LEFT_BASE in the TAD gap (`.org $8C00`, see the comment above
; Tad_IsSongPlaying's block) to free room in this window for full-length
; walk/attack frame counts.
AnimRalfIdleFrames:
    .incbin "assets/anim_ralf_idle.bin"
AnimRalfAttackFrames:
    .incbin "assets/anim_ralf_attack.bin"

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
    ; Inline immediates (16 explicit lda #imm loads) -- no ROM data table
    ; at all this time, not just non-indexed addressing. cgram_table as a
    ; standalone .dw block, placed either at the tail of the file or right
    ; after the .incbin, or before scpu_boot, kept assembling to wrong or
    ; corrupted bytes regardless of placement or of avoiding `,x`-indexed
    ; reads (see poppy_assembler_bugs.md). Baking the 16 BGR555 values
    ; directly into the instruction stream as immediates sidesteps data-
    ; table emission entirely.
    stz $2121               ; CGRAM address = color 0
    rep #$20
.a16
    lda #$0000
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$535F
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$3ADE
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$1DFB
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$1556
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$1DAC
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$1508
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$2107
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$0000
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$00AE
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$0016
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$000D
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$08C8
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$04A4
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$14A3
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
    rep #$20
.a16
    lda #$0000
    sep #$20
.a8
    sta $2122
    xba
    sta $2122
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

    ; --- Wait for SA-1 ready flag: poll SFR CharConvIrqFlag ($2300 bit 5) ---
    sep #$20
.a8
    nop                     ; workaround: Poppy backward-branch label misalignment (see poppy bug #4)
scpu_poll:
    lda $2300
    and #$20
    beq scpu_poll

    ; --- Pump CC-DMA converted tiles straight from the read-triggered ---
    ; conversion window to VRAM. CC-DMA Type 1 does NOT run as a batch copy
    ; on the $2236 trigger -- it converts one tile at a time, lazily, the
    ; instant something reads through the S-CPU's linear BW-RAM window at
    ; banks $40-$4F (Mesen2 core: CpuBwRamHandler::Read, active whenever
    ; CharConvDmaActive is set). Reading the S-CPU I-RAM window at $3000
    ; (tried first) never touches that handler, so nothing ever converts --
    ; that's why VRAM/I-RAM showed only stale leftover bytes before this
    ; fix, unrelated to our sprite and unaffected by source-pixel-format
    ; changes. A straight sequential read of 768 bytes from long address
    ; $40:3000 (matching SDA=$003000 above) hits each tile's 32-byte-
    ; aligned trigger boundary in order and the read itself returns the
    ; already-converted VRAM-format byte -- no separate I-RAM pass needed.
    ; 24 tiles * 16 words/tile = 384 words ($0300 bytes)
    rep #$20
.a16
    rep #$10
.i16
    lda #$2010
    sta $2116               ; VRAM dest = word $2010 (tile 1, BG2 char base $2000)

    ldx #$0000
    nop
scpu_pump_loop:
    lda.l $403000,x         ; Read+trigger-convert via S-CPU BW-RAM window ($40-4F)
    sta $2118               ; Write to VRAM $2118/$2119
    inx
    inx
    cpx #$0300              ; 768 bytes ($0300) = 24 tiles * 32 bytes
    bcc scpu_pump_loop

    ; --- BG2 tilemap at word $5C00: 4x6 sprite window (rest blank) ---
    ; Entries (ty<6, tx<4): tile ty*4+tx+1, priority 1 ($2000 bit).
    ; Matches the 24-tile (4 wide x 6 tall) region CC-DMA actually
    ; converted -- see width=2 (4 tiles/line) config above.
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
    cpx #$0004
    bcs scpu_tm_blank
    tya
    asl
    asl                     ; ty * 4
    sta $00                 ; DP scratch
    txa
    clc
    adc $00
    inc a                   ; tile index + 1
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

    ; --- Ralf animation state (boots into idle; Anim_Play switches to walk
    ; on held dpad Left/Right, see its header comment) ---
    lda #0
    sta.l Anim_FrameIndex
    sta.l Anim_Selected
    lda #ANIM_FRAME_DELAY
    sta.l Anim_TickCounter

    ; --- TestSprite_PlayFrame's sprite-1 bounce state ---
    lda #TESTSPRITE2_MIN_X
    sta.l TestSprite2_X
    lda #0
    sta.l TestSprite2_DirLeft
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
    jsr Core_Oam_Play
    jsr Anim_Play
    bra scpu_main_loop

; NMI/IRQ pushed from $FE00/$FE10 to $FE20/$FE30, then to $FF00/$FF10 --
; scpu_boot's body keeps growing (most recently: the CC-DMA sprite/pump/
; tilemap code, then the unrolled CGRAM palette load) and each time it
; grows past whatever budget was left before these fixed .org addresses,
; Poppy silently truncates/corrupts whatever ran into them instead of
; erroring (see poppy_assembler_bugs.md). build_rom.py's NMI/IRQ vector
; constants were updated to match -- these addresses are load-bearing,
; keep them in sync. Still comfortably below $FFE4 (native vector table).
.org $FF00
nmi_handler:
    jsr Core_Nmi_Play
    rti

.org $FF10
irq_handler:
    rti
