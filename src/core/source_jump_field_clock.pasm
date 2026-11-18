; The preceding CMP #120 flags describe the cap comparison, not elapsed
; time. Test the stored due value explicitly: zero never advances native
; physics, while exactly120 still receives the established bounded catchup.
SourceJumpClock_Due:
.a16
.i16
    sta.l SourceVisual_JumpDue
    cmp #0
    beq SourceJumpClock_Zero
    jml SourceVisual_PlayerFields__due_continue
SourceJumpClock_Zero:
.a16
.i16
    jml SourceVisual_PlayerFields__done
SourceJumpClock_End:
