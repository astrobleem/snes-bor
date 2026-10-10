# Row-state physical palette scheduling

`tools/bor_compile/raster_row_state.py` searches each bank's fifteen resident
opaque slots directly on every row. Unlike the lifetime-slot formulation, a
color may move slots or be evicted and reloaded between source uses. Every OBJ
piece retains its input bank. Row pixels are remapped offline; transparent
pixels retain index zero, including when an opaque pixel is RGB555 black.

Each changed slot must install a color required within bounded lookahead.
VBlank initialization may preload the frame. Up to four disjoint physical DMA
ranges cover every changed slot, including transparent words and unchanged
bridge words. The existing prepared-transfer span constraint applies. This
is an optimistic necessary timing condition, not a runtime admission.

Successful schedules independently replay every CGRAM word and every visible
piece pixel against the input colors. Four tests cover reload/black identity,
preserved initial preloads, invalid input, and a full-bank replacement that
cannot fit the test transfer window. The related slot-layout, heuristic and
row-state suite passes 21 tests. The width guard remains clean.

The isolated mixed-encoding HBreath witness was searched with a 356-clock
window, seventeen-line lookahead and four ranges. The first search returned
UNKNOWN after 180.81 seconds: 30,544 variables, 77,608 constraints, 2,280,119
branches. That trial preceded redundant full-bank domain propagation. A second
trial additionally fixes the input initial slot contents and includes that
propagation. It returned UNKNOWN after 90.72 seconds, with 77,728 constraints
and 1,969,440 branches. Both retain fixed bank numbering.

Neither trial finds a physical schedule or rejects raster. The authored
concurrent scene, native transfer latency, alpha/layer integration and MOTU
gameplay remain open. No color reduction is applied. The production graphics
path and bank-zero allocation are unchanged.

Bounded statistics, input/report hashes and nonclaims are retained in the
[receipt](receipts/byor-motu-row-state-raster.json).
