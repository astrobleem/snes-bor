The native source command selector derives model command order and input masks
from the source profile. It reads the current model from the validated entity
side row, queries that model's real animation cache and source energy table,
and matches the actual 27-entry input ring. Longest matches win; equal lengths
retain source order. Query order is valid animation, MP, conditional HP, then
input match. No actor identity is hard-coded in runtime selection.

The height gate uses canonical side +48 base, separately from auxiliary +8
altbase. Native tests distinguish those stores and cover the exact one-unit
boundary on both sides. The earlier auxiliary-base binding was corrected.

Begin leaves playkeys intact while costmove and its frame-zero work are pending.
Finish runs only after the real callback/effect owner and animation acknowledgment.
It re-reads current playerindex and current playkeys, clearing exactly the pinned
CONTROL mask. High bits and other player rows remain intact.

The current capability explicitly supports models without cancel commands.
Models declaring cancel fail compilation with SOURCE_COMBO_CANCEL_OWNER_REQUIRED;
cancel commands are not silently treated as ordinary commands. All 16 MOTU
models meet this capability, with 11 source commands. Height tests use the
existing documented binary32-to-Q16 scalar ABI, including the source one-unit
ground threshold and explicit subtraction overflow rejection.

Native proof covers all 11 commands at three ring positions, all four player
rows, 15 false/admission cases, and six base/height cases: 54 cases total. Source energy descriptors
remain unmodified. Guard failures preserve actor bytes. A separate He_ManB
freespecial4 proof executes the actual compiled callbacks and native effects.
Its instrumented post-callback playerindex/playkeys change proves that the
finisher clears the fresh row and preserves the other row and high bits.

Controller storage comes from the 5712-byte compiler address plan in the retired
canvas arena. The isolated callback fixture retires ordinary producers; full
production canvas/player ownership has not yet been bound. This capability is
player_preinput, not the complete player_think movement/combat controller.
Sound service remains instrumented in the callback proof. No color reduction.

The native selector also runs every case with decimal mode set on entry and
observes that the caller flag is restored after binary arithmetic.
