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

The default full-context executor remains byte-identical to parent commit
`27b8575` under the same compiler inputs. Both ROM hashes are
`29aa7d9863ab4042de71cea0acdb8568a61f58bb6a6c5044ce7cda5879d5e9e6`;
the comparison is retained in the native default-path regression receipt.
