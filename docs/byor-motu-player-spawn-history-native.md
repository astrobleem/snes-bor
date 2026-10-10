# Native respawn input-history reset

The existing foreign arena already owns four 256-byte source input-history rows,
including 27 DWORD input times and 27 DWORD combo keys. SpawnHistory_Reset uses
that allocation instead of adding storage to the full 6400-byte arena. It checks
the captured foreign generation and canvas exclusion through the real
SourceForeignWork_Check, then clears the two rings (216 bytes) and the four-byte
combostep. Keys/newkeys/playkeys/releasekeys, movetime, entity binding, direction
and reserved bytes remain intact. It accepts the canonical player index 0–3;
the full spawnplayer caller must apply its source index &3 before invoking it.

The native S-CPU fixture passes 38 cases: all four player rows and varied full-byte
patterns, stale/zero generation, bad readiness/canvas/water/frontpanel fences,
and invalid indices. Every byte in all 1024 history bytes is compared. Valid
calls are repeated to verify idempotence. Faults change no history bytes; the
shared ForeignWork checker may publish its existing fault status. Caller A/X/Y,
DP/DBR, stack and status are checked, including decimal-mode preservation. The
worst measured two-call wrapper is 35,516 master clocks; this is not a production
world-tick deadline admission.

All new code resides in the private bank-39 fixture. Production bank-zero bytes
are identical. Zero added foreign arena bytes. A matching MSU hardlink was moved
from exact M4-owned reproducible pointer-control scratch into the fixture after
hash/extent/canonical-link checks, preserving the NTFS link count at its cap.
No PCM copies. All 17 protected tracked hashes match.

This proves a real child mutation and its exclusive fixture lease, not native
smartspawn, terrain geometry, the full player_die/respawn join, production memory
ownership or MOTU gameplay. [Native receipt](receipts/byor-motu-player-spawn-history-native.json).
