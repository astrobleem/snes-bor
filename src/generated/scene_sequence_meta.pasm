; GENERATED from authored BOR scene declarations; do not edit.
; BORVID1 records are video clip IDs; scenes own ordered clip lists.

SceneSequence_Count = 2

SceneSequence_Record0_SceneId = 1
SceneSequence_Record0_AudioTrack = 7
SceneSequence_Record0_AudioRepeat = 0
SceneSequence_Record0_ClipCount = 1
SceneSequence_Record0_ClipIds:
    .db 1

SceneSequence_Record1_SceneId = 2
SceneSequence_Record1_AudioTrack = 14
SceneSequence_Record1_AudioRepeat = 1
SceneSequence_Record1_ClipCount = 5
SceneSequence_Record1_ClipIds:
    .db 2, 3, 4, 5, 6

; Indexed tables consumed by the generic scene-sequence runtime.
SceneSequence_SceneIds:
    .db 1, 2
SceneSequence_AudioTracks:
    .db 7, 14
SceneSequence_AudioRepeats:
    .db 0, 1
SceneSequence_ClipCounts:
    .db 1, 5
SceneSequence_ClipOffsets:
    .dw 0, 1
SceneSequence_ClipIds:
    .db 1, 2, 3, 4, 5, 6

SceneSequence_Rugal = 1
SceneSequence_Ending = 2
