# Joint cache search and ordinary actor coexistence

This checkpoint adds generic fixed-piece bank/cache search, alias-aware word
reuse, cache-guided bank decomposition, and source-derived concurrent palette
measurements. Equal RGB555 words shared by several pieces count once inside
each bank. Objects keep one bank for their complete rectangle. Successful
constructions independently replay operand identities and transparency; they
still need physical slots, transfer descriptors and native timing admission.

The mixed main-screen encoding has a validated class-cache lower bound of
14.857143 writes per line when banks are pooled only within their two hardware
eligibility classes. The existing fixed bank assignment needs 22.428571.
Piece-bank balancing improves the actual fixed-bank lower bound to 22, but
does not produce an admitted transport schedule. The alias-aware joint search
remains UNKNOWN after its bounded 300-second run. Neither UNKNOWN nor the
restricted global-word-mask INFEASIBLE results reject raster generally.

The constant subscreen ADD route preserves the isolated effect, but cannot
represent darker ordinary actor channels over actor-free BG1. Source contexts
contain 1987 unrepresentable pixels for player/effect, 2533 for the explicit
KnightBot/ShockBall pose, and 5649 for the conditional Skeletor pose. Identity
comes from composed source layer order, including occlusion. These reject that
constant routing policy only.

| Explicit context | Visible ordinary source words | Static bank lower bound |
|---|---:|---:|
| Player/effect | 31 | 3 |
| KnightBot/ShockBall/player/effect | 43 | 3 |
| Conditional Skeletor/geysers/player/effect | 65 | 5 |

These are raw ordinary RGB555 identities after visibility, not their full
source-frame union, nor final SCREEN effect colors. The latter KnightBot pose
has 47 ordinary words before occlusion. Source callback timing supports the
individual poses; joint AI synchronization and full-route reachability remain
uncertified. No worst-authored-configuration certification is implied.

Static ordinary words can now be fixed explicitly throughout a cache interval.
This uses residency lower bounds, including when an effect could encode the
same word in the math class. Fractional mode selection cannot release a static
reservation. Integer witnesses independently check the reservation and each
scanline write limit. The validated LP dual includes these nonzero bounds.

With ordinary colors pinned in the lower class, both measured player and
KnightBot contexts need at least 24 writes per line without color windows.
Relaxing all modes and bypass decisions independently per pixel reduces those
necessary bounds to 16.3 and 20.25. The two-window transition relaxation for
the KnightBot context gives 21.75 over scanlines 125 through 139. Its full
interval run reached a solver limit and is not an infeasibility result.

For the DMA-only mechanism, 22 opaque writes need at least 352 clocks between
first and last high-byte commits. Twenty-three need 368; crossing an OBJ bank
includes its transparent entry or a more expensive range setup. Pinned Mesen
source synchronizes DMA to eight master clocks. The safe CGRAM window starts
at horizontal clock 1096 and ends before clock 88 of the following 1364-clock
line. Local DMA phase zero permits at most 352 clocks; phase four permits 344.
The phase alternates across scanlines. This is a necessary upper bound that
relaxes setup, IRQ service and color-control contention, not a native budget.

The existing admitted 344-clock transport observer has 124 packets that agree
with these alignment bounds. Applying alternating limits of 22 and 21 opaque
writes to the critical static-actor cache LP is INFEASIBLE for both parity
choices. Thus this static-lower-class, DMA-only presentation policy fails for
the explicit KnightBot context. CPU-assisted transfers, ordinary actor raster
re-encoding, zero-main clipping and other alpha/layer decompositions remain
outside that rejection. Universal raster failure is **not** proven, and BG
fallback has **not** been selected.

All 66 focused tests pass. The width guard checks 9825 labels with zero new,
baselined or stale violations. All 17 protected fingerprints match. New work
is offline tooling; production bank zero and static presentation are unchanged.
The peak authored native raster, production binding and MOTU Demo completion
gates remain open. **No color reduction has been applied.**

Complete bounded reports, exact input schedules/scenes, native alignment
packet observations and measurement scripts are retained in
`docs/receipts/byor-motu-joint-cache-coexistence.json.gz`.
