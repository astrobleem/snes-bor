Jump entry preserves the unchanged BOR 4086 player_think block through a
readonly absent-slide/alternate-jump capability. All 16 MOTU models omit SLIDE,
RUNSLIDE, RUNJUMP and FORWARDJUMP. JUMP and JUMPDELAY remain actual conditional
queries. Left wins when both horizontal held keys are set. Standing jump
returns immediately after tryjump; failed JUMP lookup retains the source's
second JUMP query. Running jump keeps the source binary32 product of jumpspeed
and runjumpdist. Only the JUMP bit is removed from the full input word.

The unchanged entry block, tryjump and common_prejump pass 4608 C comparisons.
The proof includes unsigned high input bits, signed running and animating
values, zero/nonzero jumpmovez, unavailable JUMP/JUMPDELAY, and frame callback
mutation of the pending jump descriptor. common_prejump reads that fresh
descriptor after animating becomes zero. DO_JUMP is an instrumented mandatory
service; this proof does not execute sound, dust birth, toss or a jump frame.

The source model loader defaults, jump commands and negative-jumpspeed fixup
pass 47 C comparisons, including all 16 actual model documents. The source
default jumpspeed is -1; post-load sets it to max(speed,1). He_Man derives
jumpheight 4.5, jumpspeed 1, runjumpheight 4.5 and runjumpdist 2. He_ManB derives
jumpspeed 1.2000000476837158. Both have JUMPDELAY and zero jumpmovez. A jump delay
requires a persistent per-entity y/x/z/id descriptor; controller scratch cannot
hold it across source ticks. The complete DO_JUMP continuation remains required.

The pending-state plan reserves 128 rows of 24 bytes at 42CC00..42D800, directly
before the existing physics rows. Each row retains the source binary32 y/x/z
arguments and int32 animation id, plus snapshot identity, marker and generation.
Native storage passes 1049 cases across all 128 slots, including 22 admission
guards, model-copy generation checks, negative zero, subnormal and nonfinite
bit retention. Numeric execution must still validate its motion domain.

Actual constructor proof clears the descriptor before exists publication with
a poisoned old model id, then binds it after the real model copy and before
script/frame callbacks. Both He_Man directions complete the actual SELECT
frame. The sibling descriptor remains untouched. Birth owns the checked model
input before fresh model copying; ordinary reads/writes require the copied
side model and generation to match.

The smaller serialized CHR window transfers all 65536 output bytes exactly
through three chunks of 52224, 5120 and 8192 bytes. Native observer checks retain
the entire 3072-byte reservation, neighboring physics and source heaps. This
is a bounded transfer/storage proof, not production IRQ/NMI timing admission.
The 64-byte control block appends at 7FB808. The controller address plan now
uses 6216 of 6400 bytes, leaving 184. The real root must enforce reduced CHR
capacity and drain its producers/DMA before leasing persistent state. Live
model-switch hooks, tryjump/dojump execution, physical audio and the production
memory lease remain open. No color reduction or gameplay completion is claimed.
