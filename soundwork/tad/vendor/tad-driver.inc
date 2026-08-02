; ============================================================================
; tad-driver.inc — Terrific Audio Driver (TAD) WRAM variables + IPL handshake
;
; Poppy port derived from:
;   - /home/chad/supermn-snes/soundwork/tad/port/tad_audio.pasm  (full TAD API)
;   - /home/chad/supermn-snes/soundwork/tad/port/tad_glue.pasm  (LoadAudioData callback)
;   - /home/chad/supermn-snes/soundwork/tad/vendor/tad-audio.inc (header equates)
;   - /home/chad/SNES-SuperMonkeyIsland/src/object/audio/tad_interface.h
;   - /home/chad/SNES-SuperMonkeyIsland/src/object/audio/tad_interface.65816
;
; STATUS: LoROM + SA-1 only; full TAD code in port/tad_audio.pasm is HIROM-specific.
; For LoROM port, use Tad_Init/Tad_Process stubs that drive the IPL handshake
; with the SPC700 and prepare the WRAM variables for TAD operation. The real
; Tad_Process queue logic from supermn-snes works once you wire it to call
; through the JSL target bank.
;
; To complete: regenerate the actual SPC700 loader.bin and audio-driver.bin via
;   /home/chad/terrific-audio-driver/target/release/tad-compiler ca65-export \
;       --hirom --segment RODATA2 \
;       --output-bin build/audio-data.bin \
;       mml_drafts/bor_msu1_poc.terrificaudio
; (tad-compiler is not currently built on this host; build with: cd terrific-audio-driver && cargo build --release)
; ============================================================================

; --- WRAM TAD state (must be in $0000-$1FFF for DB=$80 access) ---
Tad_flags               = $7E0030   ; TadFlags bitfield
Tad_audioMode           = $7E0031   ; TadAudioMode enum
TadPriv_state           = $7E0032   ; TadState
TadPriv_bytesPerFrame   = $7E0033   ; transfer bytes per Tad_Process (word)
TadPriv_previousCommand = $7E0035   ; previous APUIO0 sent to driver
TadPriv_xfer_addr       = $7E0036   ; far pointer low16
TadPriv_xfer_bank       = $7E0038   ; far pointer bank
TadPriv_xfer_size       = $7E0039   ; remaining bytes (word)
TadPriv_xfer_prevSpin   = $7E003B
TadPriv_nextSong        = $7E003C
TadPriv_nextCmd_id      = $7E003D
TadPriv_nextCmd_p0      = $7E003E
TadPriv_nextCmd_p1      = $7E003F
Tad_sfxQueue_sfx        = $7E0040
Tad_sfxQueue_pan        = $7E0041
Tad_loadedGroup         = $7E0042
Tad_globalSong          = $7E0043
TadPriv_grpTableOff     = $7E0044
TadPriv_grpItems        = $7E0046

; --- TAD constants ---
TAD_IO_VERSION          = 20
TAD_LOADER_ARAM_ADDR    = $0200
TAD_MIN_TRANSFER_PER_FRAME = 32
TAD_MAX_TRANSFER_PER_FRAME = 800
TAD_DEFAULT_TRANSFER_PER_FRAME = 256
TAD_MAX_PAN             = 128
TAD_CENTER_PAN          = 64

; --- TAD states (TadPriv_state) ---
TadState_NULL                       = $00
TadState_WAITING_FOR_LOADER_COMMON  = $7b
TadState_WAITING_FOR_LOADER_SONG    = $7c
TadState_LOADING_COMMON_AUDIO_DATA  = $7d
TadState_LOADING_SONG_DATA_PAUSED   = $7e
TadState_LOADING_SONG_DATA_PLAY     = $7f
TadState_PAUSED                     = $80
TadState_PLAYING_SFX                = $81
TadState_PLAYING                    = $82

; --- APU IO ports ---
APUIO0 = $2140
APUIO1 = $2141
APUIO2 = $2142
APUIO3 = $2143

; --- TAD commands (high nybble of APUIO0) ---
PAUSE                = 0
PAUSE_MUSIC_PLAY_SFX = 2
UNPAUSE              = 4
PLAY_SOUND_EFFECT    = 6
STOP_SOUND_EFFECTS   = 8
SET_MAIN_VOLUME      = 10
SET_MUSIC_CHANNELS   = 12
SET_SONG_TIMER       = 14
SET_GLOBAL_MUSIC_VOLUME = 16
SET_GLOBAL_SFX_VOLUME   = 18
SET_GLOBAL_VOLUMES      = 20

; --- TadFlags bits ---
TadFlags_RELOAD_COMMON_AUDIO_DATA = $80
TadFlags_PLAY_SONG_IMMEDIATELY    = $40
TadFlags_RESET_GLOBAL_VOLUMES     = $20

TAD_DEFAULT_FLAGS = (TadFlags_PLAY_SONG_IMMEDIATELY | TadFlags_RESET_GLOBAL_VOLUMES)

TAD_DEFAULT_AUDIO_MODE = 0   ; MONO

; --- Stub blob sizes (replace with real values after running tad-compiler) ---
TAD_LOADER_SIZE      = 116
TAD_AUDIO_DRIVER_SIZE = 3218
