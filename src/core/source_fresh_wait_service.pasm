; Move the existing single priority visit after the wait observes fresh input.
; Existing service preserves A/X/Y/D/DB/P, including the old counter in A.
; Compare against the current counter AFTER service, as required by wait ABI.
SourceFreshWait_ServiceReturn:
.a16
.i16
    jsl SVActor_ServiceFirstNpcDuringWait
    cmp.l Nmi_FrameCounter
    jml Core_Nmi_WaitFrame__return
SourceFreshWait_End:
