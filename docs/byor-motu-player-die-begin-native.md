# Native player death prefix and no-lives tail

The isolated native proof in `out/byor-motu-player-die-begin-native/report.json`
passes 128 cases. The compiler derives model death policy and the absence of
global death/respawn hooks from the source PAK. This helper admits rush policy
zero and absent global hooks; other requirements fail explicitly.

The helper checks the foreign lease, generation, damage-phase clock, current
self, player role, canonical player type, model identity and retirement
preflight. It decrements lives unless cheats apply, clears first-player and
the original player role, snapshots recovery values, and calls the actual
production no-event retirement helper. Pinned `kill` restores global `self`;
the fixture preserves that behavior even when it points to the retired actor.

When no lives remain, the helper applies the source timer, joining-index,
credits, weapon-loss and rush-reset rules. With lives remaining, it publishes
the required spawn ticket (3). Repeating either completed or pending calls
does not repeat the prefix or kill. No spawn acknowledgement is fabricated.

The observer checks globals, player rows, lives, weapon indices, timer,
relations, role records, script variables, entity views and cores, plus CPU
context preservation. All 128 cases have zero mismatches. The maximum measured
two-call wrapper cost is 337650 master clocks. This is an isolated service cost,
not a production frame-budget admission. Source time stays held at 48 while
the caller's damage-phase lease remains outstanding.

The continuation uses the final 48 bytes of the checked 616-slot foreign tail;
larger layouts fail capacity admission. Native proof code resides in the private
fixture bank; bank 0 is byte-identical to the baseline ROM.

Full spawn, respawn, initialized global hooks, production bootstrap and complete
world-tick dispatch remain unbound. The emitted `nodieblink 3` branch is not
exercised by this proof because the actual MOTU model policies are zero.
Recovery maxima are supplied canonical fixture values, not a constructor-chain
claim. This proof does not certify MOTU gameplay or its presentation renderer.
No color reduction or PCM copies were applied.
