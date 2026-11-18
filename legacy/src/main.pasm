; ============================================================================
; Beats of Rage SNES — SA-1 + CC-DMA + MSU-1 + Terrific Audio Driver (TAD)
; Poppy assembler, LoROM + SA-1 (map mode $23, cart type $35)
; ============================================================================

.snes

BW_CANVAS   = $606000   ; canvas: 128x96 4bpp linear at SA-1 BW-RAM $60:6000
BW_READY    = $410000   ; ready flag in BW-RAM offset $10000
READY_MAGIC = $5A1A

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

    ; --- Draw 4 "enemy" blocks: 16x48 px each, colors 1-4 ---
    stz $00                 ; row = 0
sa1_row_loop:
    lda $00
    asl
    asl
    asl
    asl
    asl
    asl                     ; row * 64
    clc
    adc #$0600              ; + 24 rows * 64 (0x600) = y base 24
    sta $02                 ; rowbase

    stz $04                 ; t = 0
sa1_thug_loop:
    lda $04
    inc a                   ; color = t+1 (1..4)
    sta $06
    asl
    asl
    asl
    asl                     ; color * 16
    ora $06                 ; color * $11 (byte cc)
    sta $08
    xba
    ora $08                 ; word $cccc
    sta $08

    lda $04
    asl
    asl
    asl
    asl                     ; t * 16 (byte x offset part)
    clc
    adc $02                 ; + rowbase
    clc
    adc #$0008              ; + x byte offset base
    tax
    lda $08
    sta.l BW_CANVAS,x
    sta.l BW_CANVAS+2,x
    sta.l BW_CANVAS+4,x
    sta.l BW_CANVAS+6,x     ; 16 px wide = 8 bytes = 4 words

    inc $04
    lda $04
    cmp #$0004
    bcc sa1_thug_loop

    inc $00
    lda $00
    cmp #$0030              ; 48 rows
    bcc sa1_row_loop

    ; --- Configure SA-1 CC-DMA Type 1 (Auto Mode) FROM SA-1 CPU SIDE ---
    sep #$20
.a8
    lda #$11
    sta $2231               ; 4bpp, width=4 (16 tiles/line)
    stz $2232               ; source = BW-RAM offset $6000
    lda #$60
    sta $2233
    stz $2234
    stz $2235               ; dest = IRAM offset 0
    lda #$B1
    sta $2230               ; enable | charconv | auto | src=BW-RAM (SA-1 ONLY!)
    stz $2236               ; write dest mid byte -> triggers CharConvDmaActive!

    ; --- Signal S-CPU: canvas ready ---
    rep #$20
.a16
    lda #READY_MAGIC
    sta.l BW_READY

sa1_spin:
    bra sa1_spin

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
    lda #((Tad_Loader_SIZE + 2) | $80)
    sta APUIO0 ; New data command (must be +2 the previous APUIO0 write, with bit 7 = execute)


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
    rts


; IN: A = song_id
; OUT: carry set if `Tad_LoadSong` was called
.a8
; I unknown
; DB access lowram
Tad_LoadSongIfChanged:
    cmp TadPrivate_nextSong
    beq __anon11
        jsr Tad_LoadSong
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
    sep #$20
.a8
    ldx #$0000
msu1_check_loop:
    lda $2002,x
    cmp.l msu1_id_str,x
    bne msu1_missing
    inx
    cpx #$0006
    bcc msu1_check_loop

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
msu1_read_loop:
    lda $2001               ; read byte from MSU-1 data stream
    sta.l $7E0300,x         ; store in WRAM $7E:0300
    inx
    cpx #$002E              ; 46 bytes
    bcc msu1_read_loop

    lda #$01
    sta.l $7E0330           ; MSU-1 success flag = 1
    bra msu1_done

msu1_missing:
    stz.l $7E0330           ; MSU-1 success flag = 0

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
    stz $2121               ; CGRAM address = color 0
    rep #$20
.a16
    ldx #$0000
scpu_cgram_loop:
    lda.l cgram_table,x
    sep #$20
.a8
    sta $2122               ; low byte
    xba
    sta $2122               ; high byte
    rep #$20
.a16
    inx
    inx
    cpx #$0020              ; 16 colors * 2 bytes
    bcc scpu_cgram_loop

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
scpu_bg1_tile:
    sta $2118
    dex
    bne scpu_bg1_tile

    ; --- BG1 tilemap at word $0400: all tile 0 ---
    lda #$0400
    sta $2116
    ldx #$0400              ; 1024 entries
    lda #$0000
scpu_bg1_map:
    sta $2118
    dex
    bne scpu_bg1_map

    ; --- BG2 blank tile (index 0) at VRAM word $2000: 16 zero words ---
    lda #$2000
    sta $2116
    ldx #$0010
    lda #$0000
scpu_bg2_blank:
    sta $2118
    dex
    bne scpu_bg2_blank

    ; --- Wait for SA-1 ready flag ($41:0000 = $5A1A) ---
scpu_poll:
    lda.l BW_READY
    cmp #READY_MAGIC
    bne scpu_poll

    ; --- Pump CC-DMA converted tiles from S-CPU window $00:6000 to VRAM word $2010 ---
    ; 192 tiles * 16 words/tile = 3072 words ($0C00 words)
    rep #$20
.a16
    rep #$10
.i16
    lda #$2010
    sta $2116               ; VRAM dest = word $2010 (tile 1)

    ldx #$0000
scpu_pump_loop:
    lda $6000,x             ; Read converted word from S-CPU CC-DMA window
    sta $2118               ; Write to VRAM $2118/$2119
    inx
    inx
    cpx #$1800              ; 6144 bytes ($1800) = 192 tiles * 32 bytes
    bcc scpu_pump_loop

    ; --- BG2 tilemap at word $5C00: 16x12 canvas window ---
    ; Entries (ty<12, tx<16): tile ty*16+tx+1, priority 1 ($2000 bit)
    rep #$20
.a16
    lda #$5C00
    sta $2116
    ldy #$0000              ; ty = 0..31
scpu_tm_row:
    ldx #$0000              ; tx = 0..31
scpu_tm_col:
    cpy #$000C
    bcs scpu_tm_blank
    cpx #$0010
    bcs scpu_tm_blank
    tya
    asl
    asl
    asl
    asl                     ; ty * 16
    sta $00                 ; DP scratch
    txa
    clc
    adc $00
    inc a                   ; tile index + 1
    ora #$2000              ; priority 1
    bra scpu_tm_write
scpu_tm_blank:
    lda #$0000
scpu_tm_write:
    sta $2118
    inx
    cpx #$0020
    bcc scpu_tm_col
    iny
    cpy #$0020
    bcc scpu_tm_row

    ; --- Screen on ---
    sep #$20
.a8
    lda #$0F
    sta $2100               ; full brightness, blank cleared

    ; --- Load Song 1 (s02_coin) ---
    lda #$01
    jsl Tad_LoadSong

scpu_main_loop:
    jsl Tad_Process
    ; Drain active transfers each frame (from proven SM reference)
    jsl Tad_FinishLoadingData
    bra scpu_main_loop

; ============================================================================
; Data
; ============================================================================
.org $FD80
msu1_id_str:
    .db "S-MSU1"

.org $FE00
nmi_handler:
    rti

.org $FE10
irq_handler:
    rti

.org $FE20
cgram_table:
    dw $0000                ; 0: black
    dw $001F                ; 1: red
    dw $03E0                ; 2: green
    dw $7C00                ; 3: blue
    dw $03FF                ; 4: yellow
    dw $1084                ; 5-14: gray ramp
    dw $2108
    dw $318C
    dw $4210
    dw $5294
    dw $6318
    dw $739C
    dw $7BDE
    dw $7FFF
    dw $7FFF
    dw $7FFF                ; 15: white
