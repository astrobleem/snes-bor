; Spawn_Index and adjacent Spawn_Count are separate .db fields. Both attack
; admission predicates need the zero-extended index, with original CMP intact.
; Same-size JSL replaces each four-byte LDA; preserves X/Y/D/DB/C and all memory.
SourceSpawnByte_Read:
.a16
.i16
    lda.l Spawn_Index
    and #$00FF
    rtl
