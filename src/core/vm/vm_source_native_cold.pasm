; A16=0. Cold fetch clears the same leases without borrowing the full source bank.
SourceNativeCold4086_Clear:
.a16
.i16
    sta.l SourceOffscreenState4086_Ready
    sta.l SourceNamedKnife4086_Ready
    sta.l SourceNativeContinuation4086_Ready
    sta.l SourceNativeContinuation4086_Request
    sta.l SourceNativeSnapshot4086_Ready
    sta.l SourceMovementState4086_Ready
    sta.l SourceUpdateAnimationPrefix4086_Ready
    sta.l SourceUpdateAnimation4086_Ready
    sta.l SourceAttackRunoff4086_Ready
    sta.l SourceModelEntityCopy4086_Ready
    sta.l SourceAnimationInit4086_Ready
    sta.l SourceFrameStack4086_Ready
    sta.l SourceNativeRequest4086_Ready
    rtl
