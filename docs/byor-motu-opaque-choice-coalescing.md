# Exact opaque-choice coalescing

The offline joint scheduler can share opaque bank choices for pixels with the
same final RGB555 word, piece and scanline, even when their additive residuals
differ. `--coalesce-opaque-choices` enables this reduction. If one such pixel
uses an opaque mask, assigning the other matching pixels to that mask adds no
palette color, object, scanline sprite, tile or transfer. Independent pixel
replay still checks the compiled result. Source colors are not reduced.

The regression uses two identical final red pixels over different underlays.
One has an additive representation and the other does not. Opaque choice
variables decrease from eight to four, and both schedules render the same
source RGB555 hash with one OAM entry. The CP-SAT adapter exercises the same
case. The focused joint, coverage, residency, integer-domain, physical-range,
packet and compaction suite passes 61 tests.

Three 1,200-second searches returned UNKNOWN: unrestricted residency with a
soft hint, the concurrent player/enemy/effect scene with pooled residency, and
the isolated scene with coalescing and pooled residency. UNKNOWN is a bounded
search result, not a proof of hardware infeasibility. The isolated coalesced
search used 45,177 variables and 92,755 constraints. Mixed and 16-pixel geometry
searches continue separately.

Production presentation is unchanged. Full native raster HBreath and MOTU Demo
remain unproven. NO color reduction applied.

[Bounded trial receipts](receipts/byor-motu-opaque-choice-coalescing.json).
