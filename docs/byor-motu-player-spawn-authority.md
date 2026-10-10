# Pinned player respawn constructor authority

The source player_die plan requests spawnplayer as a child. Its mutation plan is
now checked against the literal spawnplayer body at BOR 4086 commit
`af23dc9c2316bb7853bb266ccf40986aa9765aeb`. The C fixture instruments checkwall,
checkhole, smartspawn and set_weapon. It proves the caller's placement, mutation
and child-query ordering; it does not prove terrain geometry, constructor
internals, actual native respawn or live gameplay.

5,634 cases compare the complete captured placement/recovery state and a 32-bit
FNV fingerprint of the ordered terrain/constructor/weapon calls. Index aliases,
left and inward/outward directions, 256/320 widths, authored/default coordinates,
single-Z and narrow-Z ranges, low/high wall thresholds, holes, exhaustion,
negative/zero/upper recovery values, weapon fallback and rush policy are covered.
The source wraps X one width per search iteration, not with a general modulo.
A low wall can accept the location without checking a hole. Single-Z and
ranged-Z branches have different query ordering. A Z interval shorter than
three can exhaust X search without issuing terrain queries; this is preserved.

After construction, player index and rush count are set. All 27 combo keys and
27 input times are cleared, then combostep resets. Nonzero spawnhealth adds 5;
nonzero spawnmp adds 2. Both clamp only above model limits. Negative values are
not silently clamped upward. Nonzero weapnum wins, otherwise level setweap is
sent to the actual weapon child with keep zero. Two focused tests also check
negative recovery/index aliasing and an explicit null-constructor fatal boundary.
The literal C fixture uses a successful constructor; the null test is a Python
boundary test, not an initialized native smartspawn proof.

The 27-element input arrays are a remaining native memory/ownership requirement;
the existing player-global descriptor does not by itself establish their lease.
No native code or bank-zero capacity is consumed. All 17 protected tracked hashes
match. MOTU remains unregistered and uncertified.
[Authority receipt](receipts/byor-motu-player-spawn-authority.json).
