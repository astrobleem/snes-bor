# Window HDMA and prepared CGRAM DMA contention

The native window descriptor component proves masks and upper-bank eligibility,
but its transfers must also fit beside palette writes. The generic CGRAM timing
fixture now optionally installs the same four descriptor/mode HDMA channels,
transferring seven bytes on every visible line. Prepared split palette DMA owns
channels 5, 6 and 7; the existing dummy APU HDMA pattern owns channel 0 for 73
rows. Every channel has an explicit owner in this isolated experiment.

At timer 155, 38 palette data bytes (24 + 14) and one intermediate CGRAM address
byte produce **447 complete packets** across three fields on lines 75..223.
All packet address/range sequences match. Of 8,493 high-byte commits, **2,209**
occur inside the unsafe active window. Peak high-commit span is **408 master
clocks**, exceeding the measured 356-clock window. The corresponding unchanged
baseline ROM without window HDMA has a 328-clock peak and zero unsafe commits.

This rejects this combined prepared-DMA/every-line-HDMA mechanism. It does not
reject sparse window updates, CPU descriptor writes outside the CGRAM window,
other prepared packets or raster presentation generally. Source HBreath pixels,
production audio protocol and gameplay leases are not certified by this timing
fixture. The baseline generator produces its previously recorded ROM hash
unchanged when the new option is absent.

The [receipt](receipts/byor-motu-window-cgram-contention.json) retains packet,
commit and range hashes, all frame advancement records and explicit nonclaims.
No color reduction, PCM copies or production bank-zero changes.
