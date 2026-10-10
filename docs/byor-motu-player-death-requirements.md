# Source player-death requirements

The model policy compiler now derives `nodieblink` through the pinned 4086
loader and its zero-initialized model allocation. The unmodified C loader and
integer helpers match 257 default/declaration cases, including all 16 source
models. All MOTU models have policy zero; the compiler retains a full signed
32-bit policy rather than narrowing it to a Boolean.

`source_player_death_requirements.py` derives the global rush-reset policy from
the discovered model registry and inventories the engine's four death and four
respawn script paths. The pinned loader clears each hook when loading fails;
the execution functions run only initialized hooks. All eight MOTU hooks are
absent, and its rush-reset policy is zero. Present script files are explicit
child dependencies, including empty files whose loader/compile disposition
still needs authority. No actor identity selects these rules.

The packed model policy retains registry IDs and full signed values. Three
tests cover repeated source declarations, case-insensitive script identity,
present-hook dependency/hashes, and lossless signed policy packing.

This supplies requirements for the native player-death continuation. It does
not bind that continuation, the full spawnplayer/respawn services, or MOTU
gameplay. The earlier 7,200-case literal player_die authority remains separate.
Production memory and bank zero are unchanged. NO color reduction applied.

[Loader and requirements receipts](receipts/byor-motu-player-death-requirements.json).
