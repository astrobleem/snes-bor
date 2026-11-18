
; Existing unrelated-animation rejection only. No extra calls on ordinary
; idle/walk edges, normal geometry entry, input polls or the normal NMI path.
; Replace BRL with same-size JSR; discard that return before jumping to the
; original next-actor path, or revalidate this actor after successful graft.
.bank 16
.org $DEA1
SourceQueuePose_ColdFamily:
.a16
.i16
    jsl SourceQueuePose_TryFamily
    bcc SourceQueuePose_ColdNo
    pla
    jmp SourcePacket_Refresh__actor
SourceQueuePose_ColdNo:
.a16
.i16
    pla
    jmp SourcePacket_LongBranch55
.assert * <= $10DEC0, "cold trampoline overlaps remaining old table gap"
.bank 39
.org $AA00
SourceQueuePose_TryFamily:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #2
    bne SourceQueuePose_FamilyNo
    lda.l SourceAttackOwned_Hold
    cmp #1
    bne SourceQueuePose_FamilyNo
    lda.l $437A96
    cmp #3
    bne SourceQueuePose_FamilyNo
    jml SourceQueuePose_Graft
SourceQueuePose_FamilyNo:
.a16
.i16
    clc
    rtl
.assert * <= $27AB00, "cold selector exceeds unused code"
.org $B000
SourceFirstIdle_MapMasks:
    .dw $000F,$0007,$000F,$000F,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0003,$0001,$0001
    .dw $0001,$0001,$0001,$0001,$0001,$0001,$0003,$0003,$0003,$0003,$0003,$0001,$0003,$003F,$000F,$0003
    .dw $001F,$0001,$0001,$0000,$0001,$0003,$0001,$0001,$0003,$007F,$0003,$0001,$0007,$0001,$0001,$0001
    .dw $003F,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000

; C=1 only for the same unstarted idle lease just proposed by FindEntry.
; This grants entry to the existing DMA-fenced replacement path, never Ready.

.assert * <= $27B200, "relocated idle map table changed size"
