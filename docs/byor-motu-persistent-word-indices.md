# Fixed word indices: measured restriction and joint construction

The lossless seventeen-write encoding does not support a constant physical
index for every RGB555 word under its existing bank assignments. Independent
color-conflict solves prove that bank 1 requires exactly sixteen distinct
persistent indices and bank 7 requires exactly seventeen. A bank offers only
fifteen opaque slots. Source rows themselves never exceed that capacity: equal
words can instead use different indices on different source rows, as the
verified raster encoding already does. This rejects persistent indices for
these fixed banks, not the raster approach.

The generic joint bank constructor now has an optional persistent-word-index
family. It selects each word's eligible bank and physical index together,
checks shared geometry and rolling unions, and can compile a timing-free exact
slot template. Every emitted index lies in slots 1--15 of its selected bank.
The template installs each slot's earliest word during VBlank, retains it, and
changes it on its next required source row. Opaque RGB555 zero occupies a real
nonzero index. This template deliberately has no transfer or native admission;
it is an input for later physical liveness search.

The authored peak trial at a two-row union and 34-sliver ceiling returns
UNKNOWN after sixty seconds. It does not prove that rebanking cannot satisfy
persistent indices. The existing row-dependent-index compiler remains the
default. Nine focused global-bank/constructor tests pass, including a sixteen
color conflict graph whose rows all fit fifteen slots, and exact slot reuse
after an unused-row gap. Source pixels and colors remain unquantized.

Bounds and trial hashes are retained in
`docs/receipts/byor-motu-persistent-word-indices.json`. Physical transfer,
concurrent gameplay and MOTU Demo certification remain open.
