# Spawn weapon synchronization input

Spawn weapon selection now forwards the actual native resolver's Sync result
to the model animation owner before model transition Begin. A stale value in
that control could otherwise choose an unrelated animation policy on a model
change. Source weapon metadata and saved-versus-stage selection remain derived
from the source archive.

The actual constructor, authored JUMP frame zero, recovery and same-model
weapon continuation passed both saved -1 and stage-default zero cases. At
the child boundary the observer deliberately poisons the old sync argument
with 65535. The actual native caller must replace it with the resolver's
result, and the observer checks that forwarding alongside the existing view,
side, core, player weapon and metadata comparisons. No observer writes an Ack.

The [receipt](receipts/byor-motu-player-spawn-sync-forward.json) retains hashes
and native child costs. Bank zero is byte-identical. This is a focused
constructor regression, without model-changing spawn services, full spawnplayer
or gameplay certification. No color reduction or PCM copies.
