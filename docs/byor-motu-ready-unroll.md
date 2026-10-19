# MOTU READY unroll experiment: not accepted

The optional 911-byte READY helper saved 101,002 clocks in the epoch-3
drain-to-READY interval: 288,078 to 187,076 clocks (35.06%). Its success pilot
verified 85 consecutive fields and 4,874,240 exact RGB555 pixels with no
ownership or resource faults. Epoch 2 saved 330 clocks at 22 fields, but epoch 3
added 36 clocks at 31 fields. That violates the unchanged strict transaction
nonregression gate, so the candidate was not promoted. There is no full
eight-case certification or READY-unroll pass receipt.

READY runs before map DMA. Its interval must not be combined with the separate
post-map reference rebuild interval, and elapsed master clocks include memory
stalls. Small regressions are retained rather than rounded away.

Independent review verified the 225-file raw manifest and the negative result.
The 14 model/adapter tests pass, including both rejection forms, full ordered
map writes, CPU context, literal ROM encoding and fail-closed thresholds.
The frozen receipt is
[`receipts/byor-motu-ready-unroll.json`](receipts/byor-motu-ready-unroll.json).
Raw capture and review remain under `out/byor-motu-ready-unroll-pilot-v1` and
`out/byor-motu-ready-unroll-integration-v1`. The accepted REF ROM is unchanged.
