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
hold it across source ticks. Its native storage/constructor/model owner and
the complete DO_JUMP continuation remain required. No color reduction or
gameplay completion is claimed.
