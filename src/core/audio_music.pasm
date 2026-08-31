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
    pha
    lda.l Options_MusicVolume
    sta $2006
    pla
    sta $2004
    stz $2005
    lda Music_StageRepeats,x
    asl
    ora #Music_MSU_PLAY
    sta $2007
Music_SelectStageTrack__done:
    plp
    rts
