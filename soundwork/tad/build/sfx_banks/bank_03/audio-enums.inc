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
  bank03_fx00 = 0
  bank03_fx01 = 1
  bank03_fx02 = 2
  bank03_fx03 = 3
  bank03_fx04 = 4
  bank03_fx05 = 5
  bank03_fx06 = 6
  bank03_fx07 = 7
  bank03_fx08 = 8
  bank03_fx09 = 9
  bank03_fx10 = 10
  bank03_fx11 = 11
  bank03_fx12 = 12
.endenum
