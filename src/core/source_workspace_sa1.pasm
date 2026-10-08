; Cooperative SA-1 execution lease. Compiler opt-in only: an installed worker
; replaces its four-byte mutation-fence read with JSL SourceWorkspaceSA1_Poll.
; This routine returns the original A8 fence value and flags. No reset, world
; acquisition, stack replacement or resident-world copy occurs.
;
; $412028..$41202F is the verified gap after the sequenced input records
; ($412020..$412027), before source host fields at $412100.
; Magic/epoch are published before state. The caller retains completed audio
; payload ownership separately through SourceComputedAudio_State=4.
SourceWorkspaceSA1_Magic = $412028 ; .dw compiler capability $B66D
SourceWorkspaceSA1_Generation = $41202A ; .dd nonzero execution epoch
SourceWorkspaceSA1_State = $41202E ; .dw 0 idle,1 request,2 parked,3 run,4 done,5 release

SourceWorkspaceSA1_Poll:
.a8
.i16
 php
 rep #$30
.a16
.i16
 pha
 lda.l SourceWorkspaceSA1_Magic
 cmp #$B66D
 bne SourceWorkspaceSA1_Poll__done
 lda.l SourceWorkspaceSA1_State
 cmp #1
 bne SourceWorkspaceSA1_Poll__done
 lda.l SourceWorkspaceSA1_Generation
 ora.l SourceWorkspaceSA1_Generation+2
 beq SourceWorkspaceSA1_Poll__done
 ; Do not acknowledge a competing birth/retire mutation fence.
 lda.l $41200C
 and #$00FF
 bne SourceWorkspaceSA1_Poll__done
 phx
 phy
 phb
 phd
 lda #2
 sta.l SourceWorkspaceSA1_State
SourceWorkspaceSA1_Poll__park:
.a16
.i16
 lda.l SourceWorkspaceSA1_State
 cmp #5
 beq SourceWorkspaceSA1_Poll__release
 cmp #3
 bne SourceWorkspaceSA1_Poll__park
 ; The compiler-installed job has a returning ABI. It may use high IRAM
 ; scratch and normal DMA, but must retain this stack and leave world RAM
 ; and the legacy mailbox untouched. Producer/encoder chaining ends RTL.
 jsl $003500
 rep #$30
.a16
.i16
 lda #4
 sta.l SourceWorkspaceSA1_State
 bra SourceWorkspaceSA1_Poll__park
SourceWorkspaceSA1_Poll__release:
.a16
.i16
 pld
 plb
 ply
 plx
 lda #0
 sta.l SourceWorkspaceSA1_State
SourceWorkspaceSA1_Poll__done:
.a16
.i16
 pla
 plp
 lda.l $41200C
 rtl
