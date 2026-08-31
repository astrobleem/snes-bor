; Source-driven MSU-1 music selection. The table is generated from authored
; level directives; this routine owns MSU PCM registers, never TAD state.
.include "../../tools/audio/audio_music_ids.pasm"

Music_SelectStageTrack:
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
    sta $2004
    stz $2005
    lda #$03
    sta $2007
Music_SelectStageTrack__done:
    plp
    rts
