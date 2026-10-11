# Joint exact operand and bank search

The joint source renderer retains valid hinted palette operands in its exact
color-math cover. Dominance may prefer another operand with identical output;
discarding the hinted operand can otherwise prevent a valid warm start or a
requested fixed-word replay. A saturated-channel test proves this case with
operand 17, background red 31 and exact source red 31. No color is approximated.
The authored peak cover already retains all 396 valid operands; 171 hinted
operands are among them. The retention fix does not enlarge that particular
cover.

The bounded integer backend now accepts a selectable SAT strategy. Its default
portfolio behavior remains unchanged. SAT mode disables linear relaxation while
preserving the integer constraints, soft hints and independent source replay.

For authored BR12, a joint trial keeps the 101 source-exact 8-by-8 objects and
their banks, allows new exact operands, and enforces 21 writes, 16-line
lookahead and a strict 345-clock optimistic partition limit. It proves this
restricted fixed-bank encoding INFEASIBLE in 9.893 seconds. This rejects that
encoding and transfer family, not raster generally.

Allowing the object banks to change returns UNKNOWN after 60 seconds under
both portfolio and SAT strategies. SAT explores 1,026,775 branches with zero
LP iterations. Allowing one additional fixed-bank mask per hinted rectangle,
with all global OBJ limits retained, also returns UNKNOWN after 120 seconds
and 2,165,210 branches. These bounded searches supply no universal failure
proof. Physical slots, authored peak native presentation and gameplay remain
unadmitted.

The receipt independently binds every trial to the current PAK, authored
underlay, source metadata and composed RGB555 hash. All 17 protected file
hashes match. Sixty-one focused renderer, exact-math and integer-backend tests
pass, as does the width audit: 9825 labels and zero failures. Alpha remains
exact BOR 4086 SCREEN followed by RGB555 conversion. No color reduction is
applied.
