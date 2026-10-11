# Animation-wide source color demand

The capacity tool now reports maxima over every animation frame separately
from the frame selected for greatest full-frame color demand. Current source
PAK measurements preserve every RGB555 identity and use indexed transparency,
including opaque RGB555 black correctly.

HBreath has 40 idle frames. BR12 remains the full-frame peak: 204 opaque
RGB555 colors, 54 on its busiest scanline and 32 newly required between
adjacent scanlines. BR15 has 161 full-frame colors but reaches 58 on one
scanline. The animation-wide adjacent-new maximum remains 32. These are raw
source demands before SCREEN compositing, fixed-bank assignment, residency
and physical transfer scheduling.

Shock has ten idle frames, eight colors across their union, seven in its
full-frame peak and seven on its busiest scanline across all frames. The
selected peak-color frame's scanline maximum is only three. Its
animation-wide adjacent-new maximum is four.

The retained frame requirements include asset hashes and individual counts.
Neither adjacent set difference nor these raw color counts constitute a
CGRAM bandwidth or alpha presentation proof. BR12 alone cannot certify the
complete HBreath animation. No color reduction is applied.
