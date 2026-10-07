; Restore a completed child's parent frame row and retained VM row.
SourceNativeSnapshot4086_PopPair:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceNativeSnapshot4086_CheckPair
 bcc SourceNativeSnapshot4086_PairChecked
 jmp SourceNativeSnapshot4086_PopBad
SourceNativeSnapshot4086_PairChecked:
.a16
.i16
 lda.l SourceFrameStack4086_Depth
 dec a
 sta.l SourceFrameStack4086_Depth
 jsl SourceFrameStack4086_Pop
 bcc SourceNativeSnapshot4086_ParentRestored
 lda.l SourceFrameStack4086_Depth
 inc a
 sta.l SourceFrameStack4086_Depth
 jmp SourceNativeSnapshot4086_PopBad
SourceNativeSnapshot4086_ParentRestored:
.a16
.i16
 jsl SourceNativeSnapshot4086_Restore
 bcs SourceNativeSnapshot4086_PopBad
 ply
 plx
 plp
 clc
 rtl
SourceNativeSnapshot4086_PopBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
