;; Song and Sound Effect ca65 enums for 02_coin.terrificaudio.
;;
;; Automatically generated using `tad-compiler ca65-enums` or `tad-compiler ca65-export`.
;;
;; This file MUST BE recreated if song list or sound effect export order changes.
;;


LAST_SONG_ID = 1
N_SOUND_EFFECTS = 13

;; Song enum.
;; Input argument for `Tad_LoadSong`
.enum Song
  BLANK = 0 ; blank (silent) song
  blank_sfx_only = 1
.endenum


;; Sound Effects enum.
;; Input argument for `Tad_QueueSoundEffect` and `Tad_QueuePannedSoundEffect`
.enum SFX
  ; normal-priority sound effects
  sfx_hit = 0
  sfx_fall = 1
  sfx_jump = 2
  sfx_get = 3
  sfx_money = 4
  sfx_punch = 5
  sfx_oneup = 6
  sfx_beep = 7
  sfx_beep2 = 8
  sfx_spin = 9
  sfx_dash = 10
  sfx_metal = 11
  sfx_timeover = 12
.endenum
