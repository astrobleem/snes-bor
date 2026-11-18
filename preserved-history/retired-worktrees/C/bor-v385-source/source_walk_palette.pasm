; Admit only a matching physical-player walking palette through the existing
; allocation, queue, staging, first-NPC and post-tile publication fences.
; The original caller owns/saves A/X/Y/P; no new scratch or resource writes.
SourceWalkPalette_Entry:
.a16
.i16
    cmp #1
    beq SourceWalkPalette_EntryYes
    jml SourceVisual_PrewarmAttackPalette__done
SourceWalkPalette_EntryYes:
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #1
    beq SourceWalkPalette_EntryMatched
    jml SourceVisual_PrewarmAttackPalette__done
SourceWalkPalette_EntryMatched:
    jml SourceVisual_PrewarmAttackPalette__guard14
SourceWalkPalette_State:
.a16
.i16
    cmp #1
    bne SourceWalkPalette_StateNo
    lda.l SourceVisual_EntryScratch+1
    and #$00FF
    cmp #1
    beq SourceWalkPalette_StateYes
SourceWalkPalette_StateNo:
    jml SourceVisual_PrewarmAttackPalette__done
SourceWalkPalette_StateYes:
    jml SourceVisual_PrewarmAttackPalette__guard20
