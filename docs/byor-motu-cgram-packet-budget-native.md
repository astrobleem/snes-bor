# CGRAM packet budget: 36 bytes with audio rows, 42 bytes afterward

The native prepared-HIRQ DMA fixture now supports bounded audio table lengths
and complete-packet observation. Current production authority builds one
mode-4 APU submit row and 72 data rows (144 genuine BRR bytes), then terminates
the HDMA table. The fixture reproduces that 73-row bus pattern with dummy APU
values. It does not prove the TAD protocol, actual production interrupt context,
NMI/background load or source renderer.

At timer 178 dots, a contiguous 36-byte CGRAM transfer has zero active-window
writes over 669 complete packets: every tested row 1–223 across three fields,
including the audio rows. After the audio table finishes, a 42-byte transfer
has zero unsafe writes over 447 packets on rows 75–223 across three fields.
A 44-byte transfer on the same late rows produces 744 unsafe writes over 447
packets. Complete first/last data clocks and counts are retained separately
from the original 100-write sample. Earlier timer-176 trials include both
premature and late writes; they are not claimed safe. Partial frame timeouts
were handled by bounded retries until all requested fields completed.

These measurements establish safe tested bursts of 18 words early and 21 words
late for this isolated IRQ program, not universal bandwidth maxima. A raw
44-byte data ceiling does not include interrupt jitter or HDMA occupancy. The
20-write pooled source candidate remains potentially compatible with a late
42-byte burst only if physical bank/slot placement and transfer descriptors
fit. That physical schedule is still unproven. No raster or BG/hybrid family
is universally rejected, and MOTU remains uncertified.

All new handler code is in bank 1 of independent fixture ROMs. No production
bank-zero code changes, color reduction or PCM copies. The width audit remains
clean and all 17 protected tracked hashes match.
[Native packet receipt](receipts/byor-motu-cgram-packet-budget-native.json).
