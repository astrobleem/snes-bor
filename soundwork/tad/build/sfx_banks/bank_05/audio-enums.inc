;; Song and Sound Effect ca65 enums for 02_coin.terrificaudio.
;;
;; Automatically generated using `tad-compiler ca65-enums` or `tad-compiler ca65-export`.
;;
;; This file MUST BE recreated if song list or sound effect export order changes.
;;


LAST_SONG_ID = 1
N_SOUND_EFFECTS = 9

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
  bank05_fx00 = 0
  bank05_fx01 = 1
  bank05_fx02 = 2
  bank05_fx03 = 3
  bank05_fx04 = 4
  bank05_fx05 = 5
  bank05_fx06 = 6
  bank05_fx07 = 7
  bank05_fx08 = 8
.endenum
