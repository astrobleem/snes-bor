# Zero initialized stage entries require constructor resolution

BOR 4086's `CMD_LEVEL_AT` commits the pending entry and then clears it with
`memset`. A subsequent `at` retains index 0, a null model pointer and a null
name. `smartspawn` passes those values to `spawn`; its model-resolution prefix
consults `model_cache[0].model`. A resident cache entry therefore reaches the
constructor. An unloaded cache entry returns null. Calling this record a
`noop` prematurely discarded a required runtime decision.

The dialect IR now names these records `zero_initialized` and retains cache
index 0 and the residency requirement. The source loader table still retains
the original empty record. Its closed native spawn-row preparer rejects that
record explicitly; it does not yet implement this constructor path. No live
MOTU queue admission is claimed.

The supplied MOTU registry starts with `load Shock`. Its authored GUILE2
line 244 contains the extra `at 1800`. Actual cache residency at that point,
constructor execution and the resulting effect require production binding;
the declaration alone does not certify them.

The enemy-concurrency audit now retains this conditional non-enemy request
separately. It rejects a zero entry whose cache-zero actor type is outside its
closed non-enemy case. GUILE2 still admits at most three queued enemies;
the additional effect is excluded explicitly from that enemy count. Five
focused concurrency tests pass. Current source measurements find eight
RGB555 colors across Shock's ten idle frames, seven in its peak frame and
seven on its busiest scanline across all frames (three in the selected
peak-color frame). The capacity report now includes animation-wide maxima,
separate from that selected frame. These counts do not prove lifetime, visible
overlap, OAM allocation or a palette lease in gameplay.

`source_spawn_resolution_authority.py` compiles the exact model-resolution
prefix from pinned engine commit af23dc9c2316bb7853bb266ccf40986aa9765aeb.
Twenty-four cases cover null and explicit model pointers, loaded and unloaded
cache index 0, index 1, negative index and name lookup. All match. Allocation
after resolution is outside this bounded probe. Four dialect tests pass, and
the width audit has 9825 labels with zero failures. No color reduction is
applied.
