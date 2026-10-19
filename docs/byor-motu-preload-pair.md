# MOTU preload copy experiment: not accepted

The optional 373-byte preload copy helper was not promoted. Its success pilot
retained 26,000 ownership-monitor faults (22,800 queue-owner and 3,200 extra
IRAM-owner faults); no fault was filtered into an acceptance result. The
provisional epoch-3 publication also added 10 master clocks, despite a 3.75%
copy-function improvement. No full eight-case certification was performed.

The narrowly checked observer extension was developed after that capture and
tested offline. It has not been recaptured or accepted. The inherited guards,
10,000-clock DMA margin floor and exact frame checks remain unchanged.

The frozen negative receipt is
[`receipts/byor-motu-preload-pair.json`](receipts/byor-motu-preload-pair.json).
Raw failed capture and source snapshots remain under
`out/byor-motu-preload-pair-pilot-v1` and
`out/byor-motu-preload-pair-integration-v1`. The optional overlay and tests are
retained for reproducibility; they do not change the accepted REF ROM.
