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
  bank00_fx00 = 0
  bank00_fx01 = 1
  bank00_fx02 = 2
  bank00_fx03 = 3
  bank00_fx04 = 4
  bank00_fx05 = 5
  bank00_fx06 = 6
  bank00_fx07 = 7
  bank00_fx08 = 8
  bank00_fx09 = 9
  bank00_fx10 = 10
  bank00_fx11 = 11
  bank00_fx12 = 12
.endenum
