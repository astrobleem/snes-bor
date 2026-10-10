# Native post-constructor spawn recovery

`SpawnRecovery_Apply` binds the portion of pinned `spawnplayer` that assigns
player index, resets input history, and applies saved health and MP. It accepts
a canonical player index and foreign generation, verifies the actual global
self against the installed player role and active canonical entity, and checks
the model-core and player-global leases. Rush policy zero is supported; other
policies explicitly require their additional body.

The helper uses the real `SpawnHistory_Reset` routine. Nonzero saved health adds
5 and nonzero saved MP adds 2; zero preserves the constructed value. Both use a
signed upper clamp against the entity's model maxima. Negative recovery values
are preserved. Additions outside the defined signed 32-bit domain fail before
history, index, health or MP changes. It adds no arena or tail storage.

The isolated native proof passes 86 cases: 72 index/slot/recovery combinations,
13 guard failures, and a final valid case. Slots 0, 1 and 127 are exercised.
Expected recovery values come from running the previously certified literal C
`spawnplayer` fixture with these inputs. The observer compares the foreign tail,
current entity view/core and all four input-history rows, including decimal
mode and caller register/stack preservation. Calls are repeated to test
idempotence. The maximum two-call wrapper cost is 152010 master clocks.

The C constructor provides maxima 150/80 in this bounded authority fixture;
the native fixture supplies the same canonical constructed state. This does not
prove the constructor chain, terrain search, weapon service, complete respawn,
production memory ownership, full world tick or MOTU gameplay. The wrapper cost
is not a full spawn/frame-budget admission. All added native code resides in the
private proof bank; production bank 0 is byte-identical. No PCM copies or color
reduction were applied.

[Native receipt](receipts/byor-motu-player-spawn-recovery-native.json).
