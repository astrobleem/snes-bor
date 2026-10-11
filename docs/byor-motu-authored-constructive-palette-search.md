# Authored constructive palette search

Moving prefetch timing around the verified 472-clock physical witness returns
UNKNOWN after 180.092 seconds at the 344-clock target. Its rectangle lifetime
model has 20,126 variables and 47,372 constraints. No rejection follows.

Constructive cache searches can evict, reload and repack colors without fixed
lifetime grouping. Beam 32/global 8 with twelve-line lookahead stops at line
127. An eligible permutation with beam 48/global 16 and 24-line lookahead also
stops at 127. Beam 64/global 32, another permutation and 55-line lookahead
reaches 128. All are bounded search failures, not hardware impossibility.

The constructive path now preserves declared per-piece bank domains during
permutation. It rejects a seed outside those domains, and finds an eligible
bijection if a random shuffle violates them. The default grouping still
preserves color-math bank classes. Successful schedules replay every source
operand and CGRAM packet; bank assignment stays fixed across all piece rows.

A new initial-residency policy can use the validated input schedule's VBlank
colors instead of first-use ordering. Its placement may change, but source
identity and all transfers remain checked. The authored cache initially fills
all 120 opaque slots. Using this seed with beam 48/global 16, 24-line lookahead
and an eligible permutation stops at line 128. No admission or rejection is
claimed. Defaults stay unchanged; no production source presentation is edited.

NO color reduction or alpha adaptation is applied. Peak authored native proof,
concurrent actors, live leases and MOTU gameplay remain open.

All 63 focused scheduler and native-compiler tests pass. A fixed slot
permutation with movable four-line timing neighborhoods returns UNKNOWN
after 90.056 seconds, with 13,677 variables and 27,175 constraints. It rejects
no raster family.
