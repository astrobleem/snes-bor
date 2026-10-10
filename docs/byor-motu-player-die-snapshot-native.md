# Native player-death recovery snapshot

The private native leaf binds `player_die`'s recovery health and MP snapshot.
It accepts the original player index captured before the death script and reads
the current global `self` afterward. It copies the canonical model health/MP
DWORDs into that original player's recovery fields, preserving signed values.
The current entity's player index does not redirect the destination.

Before publishing, it checks the foreign generation, the read-only player-global
lease, loaded VM slot extent, world/damage-phase lease and time, canonical self
pointer/header and model-core owner extent. A failed player-global lease writes
no old-tail status. The snapshot allocates no foreign arena bytes and uses a
16-byte stack frame. All new code is private; production bank zero is identical.

The native snapshot passes 54 cases: all four original indices, current self
slots 0/1/127, full signed health/MP values and 18 rejection conditions. The
current self's player index deliberately differs from the original index. The
observer checks the eight intended recovery bytes, the rest of the VM tail,
the current canonical view/core rows and CPU/decimal preservation. The caller's
damage-phase lease is supplied by the isolated fixture; full death dispatch,
kill, spawnplayer and respawn continuation remain open.

The read-only player-global check and existing global access operations pass
221 native cases. A canonical MSU hardlink alias was moved between M4-owned
fixture folders after SHA/path verification; no MSU or PCM payload was copied.
The snapshot ROM/report remain retained even though its media alias was reused.
NO color reduction applied. MOTU gameplay is not certified.

[Native receipts](receipts/byor-motu-player-die-snapshot-native.json).
