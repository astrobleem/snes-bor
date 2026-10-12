# Measured idle-CPU raster transfer budget

The isolated SA-1-mapped native fixture now sustains a **344-master-clock
prepared CGRAM commit span** with the actual production NMI service and its
2,814-byte queue transfer. Four complete fields have zero viewport pixel
mismatches, unsafe high-byte commits, palette packet identity faults, OBJ
overflow flags or IRQ/NMI context faults. First high-byte commits fall at
1096--1104; the latest aligned safe high-byte commit is 1448. The largest
observed packet data total is 44 bytes. DMA channels 1--7 execute at most four
palette ranges; channel 7 is restored after NMI. No HDMA channel is used.

This is a private executor with an explicit idle 65816 foreground. Its DBR
remains zero, X is untouched by the IRQ, and A/flags are preserved. These are
data-bank ABI restrictions, not code allocation in ROM bank zero: all new
instructions remain in the fixture's nonzero banks. Counts for the next row
are prepared after the current transfer, using bounded eight-bit low-byte
writes; all count high bytes are initialized to zero. HTIMER is 162. The
foreground waits for IRQ and does not execute the source VM or gameplay.

The earlier full-context executor failed a 328-clock padding trial. It drifted
across scanlines and missed palette deadlines. Using eight-bit count setup
alone also failed. The retained failed observer traces therefore prevent
mistaking a favorable CGRAM window for an admitted repeating IRQ service.
The lean executor finishes in time for the next IRQ; its measured peak
entry-to-RTI cost is 1,092 master clocks.

The test extends the proven controlled-black source schedule by transferring
eight additional resident palette words on every active row. These writes
preserve CGRAM identity and all 204 source RGB555 colors. It proves sustained
transport for those descriptors, not authored SCREEN alpha/window updates,
concurrent actors, animated CHR admission or a gameplay resource lease.
The authored 352-clock logical witness still exceeds this measured budget.

Native ROM, logical schedule, input-file and physical descriptor hashes are
in `docs/receipts/byor-motu-raster-idle-transfer-budget.json`. Its paired gzip
retains successful descriptors and bounded native assembly/observer witnesses
for both successful and failed trials. No color reduction was applied.

The later controlled-player witness sustains the same 344-clock packet span
with source-bound window-register traffic. Its explicit private WAI ABI uses
inline row returns and HTIMER 170; peak IRQ entry-to-RTI is 1,180 clocks.
Six complete fields have zero unsafe commits or viewport pixel mismatches,
1,410 context checks with zero faults, and 204 complete physical CGRAM
snapshots with zero byte faults. The NMI peak is 37,946 clocks with the same
2,814-byte queue fixture. Every window control field matches its source-bound
descriptor. Layer math is disabled in this transport test, so authored alpha
rendering remains unadmitted. Positive and negative evidence is retained in
[the lifetime native receipt](receipts/byor-motu-kempe-native.json).

The descriptor byte budget is explicit: 32 peak dirty CGRAM bytes, 38 peak
actual CGRAM DMA bytes including retained slots, and 40 peak raster DMA bus
bytes including address writes. At most seven DMA channels participate.
The repeated native capture with these fields also passes six complete fields.
Initial 256-byte OBJ palette loading belongs to VBlank and is reported
separately from per-line transfers.

Control identity alone is insufficient for alpha timing. A conservative
source-pixel deadline check finds six `$212B` writes 4–10 clocks after the
first math-bank pixel on source row 129 in the prior transport capture.
The PPU line is source viewport row plus one. The optional private executor
now writes byte controls before preparing next-line DMA counts. A repeated
six-field capture has zero late writes under that check, zero unsafe CGRAM
commits, zero pixel mismatches and 1,410 context checks without faults.
Both deadline reports and the native trace are retained in the same receipt.
The check does not prove that each pixel depends on that register, or admit
authored alpha rendering; it establishes a conservative timing requirement.

The default full-context executor remains byte-identical to parent commit
`27b8575` under the same compiler inputs. Both ROM hashes are
`29aa7d9863ab4042de71cea0acdb8568a61f58bb6a6c5044ce7cda5879d5e9e6`;
the comparison is retained in the native default-path regression receipt.
