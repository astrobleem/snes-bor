; One additional foreground admission opportunity at the completed physics
; boundary, before composition starts. Existing accepted-snapshot reader,
; actor/NPC/jump exclusions and authoritative loader retain all ownership,
; queue, palette and physical readiness checks. Never emits OAM here.
SourceEarlyAttack_Tail:
.a16
.i16
    lda.l $7E46DE
    bne SourceEarlyAttack_Pop
    lda.l SourceReserve_Valid
    cmp #$1D1F
    bne SourceEarlyAttack_Pop
    ; Cheap hint only. The original reader below authenticates the complete
    ; sequence, stage, physical actor binding, role, family and frame.
    lda.l $434E50
    and #$00FF
    cmp #2
    beq SourceEarlyAttack_Check
    lda.l $434E74
    and #$00FF
    cmp #2
    bne SourceEarlyAttack_Pop
SourceEarlyAttack_Check:
.a16
.i16
    lda #0
    jsl SourceWarm_ReadAttack
    bcs SourceEarlyAttack_Service
    lda #1
    jsl SourceWarm_ReadAttack
    bcc SourceEarlyAttack_Pop
SourceEarlyAttack_Service:
.a16
.i16
    jsl SVActor_ServiceFirstNpcDuringWait
SourceEarlyAttack_Pop:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceEarlyAttack_End:
