The source-derived READONLY_DIRECTIONAL_RUN_ONLY capability requires absence of
ATTACKUP, ATTACKDOWN, ATTACKFORWARD and DODGE. All MOTU models meet it. DUCK is
also absent, making the earlier platform-duck body unreachable; this does not
remove the later five-unit landed-platform air threshold.

The unchanged BOR directional fragment and unchanged match_combo pass 4608
comparisons. The native service uses the actual 27-entry ring matcher and
readonly source animation resolver in source order. Successful RUN clears only
its directional key mask, decrements the current history step with wrap and
publishes canonical running=1. It preserves the entry-captured player row and
other key bits. Alternate animations unexpectedly present reject explicitly.

The actual constructor/joined controller fixture passes 84 cases, including
ordinary source-order branches, matching/failed directional sequences, mixed
keys, both directions, history positions 0/1/26, high key bits, two/five-unit air
thresholds and signed coordinate extremes. Query order is separately observed.
RUN starts here; later running cancellation and movement still require joining.
The full player controller, combat and Demo completion remain unbound.

The controller address plan uses 6392 of 6400 bytes, leaving 8. Existing
region addresses are retained; the new 64-byte work region is appended. This is
not a production canvas lease. No color reduction or bank-0 code is introduced.
