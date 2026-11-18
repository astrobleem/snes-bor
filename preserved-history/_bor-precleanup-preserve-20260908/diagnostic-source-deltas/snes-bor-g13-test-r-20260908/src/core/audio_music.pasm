; Source-driven MSU-1 music selection. The table is generated from authored
; level directives; this routine owns MSU PCM registers, never TAD state.
.include "../../tools/audio/audio_music_ids.pasm"

Music_SelectStageTrack:
Music_MSU_PLAY = $01
Music_MSU_REPEAT = $02
    php
    rep #$31
.a16
.i16
    lda.l Msu1Present
    and #$00FF
    beq Music_SelectStageTrack__done
    lda.l Game_StageIndex
    tax
    cpx #Music_StageTrackCount
    bcs Music_SelectStageTrack__done
    sep #$20
.a8
    lda Music_StageTracks,x
    sta.l Music_LastTrack
    pha
    lda #MUSIC_TRANSITION_STAGE
    sta.l Music_LastTransition
    lda.l Options_MusicVolume
    sta $2006
    pla
    sta $2004
    stz $2005
    lda Music_StageRepeats,x
    asl
    ora #Music_MSU_PLAY
    sta $2007
    lda #1
    sta.l Music_PlayState
Music_SelectStageTrack__done:
    plp
    rts

; OpenBOR starts a level's authored bossmusic when a boss entity is spawned.
; Spawn_Play calls the long trampoline only for SPAWN_KIND_BOSS records; the
; per-stage table preserves stages that do not declare bossmusic with ID 0.
Music_SelectBossTrack:
    php
    rep #$31
.a16
.i16
    lda.l Msu1Present
    and #$00FF
    beq Music_SelectBossTrack__done
    lda.l Game_StageIndex
    tax
    cpx #Music_StageTrackCount
    bcs Music_SelectBossTrack__done
    sep #$20
.a8
    lda Music_StageBossTracks,x
    beq Music_SelectBossTrack__done
    sta.l Music_LastTrack
    pha
    lda #MUSIC_TRANSITION_BOSS
    sta.l Music_LastTransition
    lda.l Options_MusicVolume
    sta $2006
    pla
    sta $2004
    stz $2005
    lda Music_StageBossRepeats,x
    asl
    ora #Music_MSU_PLAY
    sta $2007
    lda #1
    sta.l Music_PlayState
Music_SelectBossTrack__done:
    plp
    rts

; The active campaign's final source scene is ENDING.TXT.  Its authored
; `music ... 1` directive is generated into Music_EndingTrack/Repeat.
Music_SelectEndingTrack:
    php
    rep #$31
.a16
.i16
    lda.l Msu1Present
    and #$00FF
    beq Music_SelectEndingTrack__done
    sep #$20
.a8
    lda #Music_EndingTrack
    sta.l Music_LastTrack
    sta $2004
    stz $2005
    lda #MUSIC_TRANSITION_ENDING
    sta.l Music_LastTransition
    lda.l Options_MusicVolume
    sta $2006
    lda #Music_EndingRepeat
    asl
    ora #Music_MSU_PLAY
    sta $2007
    lda #1
    sta.l Music_PlayState
Music_SelectEndingTrack__done:
    plp
    rts
