# Raster OBJ ROM mapping and CPU context proof

The native source peak-frame executor now has a production-cartridge-mapping
variant. It preserves the base SA-1 header and default MMC register mapping.
The original production ROM has verified empty banks 96 through 127. Private
code uses banks 103 and 104, palette/CHR/OAM payloads use bank 106, and their
fast-ROM CPU aliases are A7, A8 and AA. The offline assembler's return labels
are relocated with an exact 225-JML count check. No bank-zero code grows.

Executing the descriptor loop through slow-ROM aliases misses deadlines. The
retained failed trace shows packets drifting across scanlines; it is a rejected
executor, not evidence that the source palette schedule is infeasible. The
fast-ROM executor restores exact scanline packet identity without changing
source pixels, OAM, palette allocation, MMC configuration or the schedule.

Four native fields pass with zero RGB555 pixel differences, zero CGRAM packet
identity faults, zero unsafe high commits, clear OBJ overflow flags, and exact
OAM RAM/write traces. The peak first-high-to-last-high span remains 216 master
clocks. Under a held BRA context first high writes occur at clocks 1100 through
1120. A bounded foreground stress loop adds long WRAM reads/writes, stack
operations and accumulator-width changes, retaining nonzero D and DBR. It also
passes four fields and 1,032 paired IRQ context checks with no fault. Its first
high phase ranges from 1100 through 1144. This measured 44-clock spread fits
the controlled schedule's transfer span inside the 356-clock safe window.

The foreground stress is not actual source VM execution. SA-1 worker execution,
production NMI/audio services and a gameplay presentation lease remain unproven
by this fixture. Its NMI only restores the initial palette and DMA stream
cursors. The earlier standalone LoROM proof is retained separately.

The controlled player-plus-effect cache witness reaches 17 writes with a
validated fractional lower bound of 16.2. Minimizing total writes while retaining
the favorable 328-clock range bound produces a 410-write candidate with ten
lines of actual prefetch. Physical slot searches with fixed or flexible write
times still reach their deadlines without a candidate. A persistent color-slot
restriction is separately infeasible for that fixed encoding; the general
slot allocator remains open. None of these results reject raster universally.

The controlled player-plus-KnightBot pose has 306 opaque output colors. A legal
8/16 compaction reduces 240 intermediate masks to 112 OAM entries, 24 sprites
and 34 tile slivers. Its emitted CHR uses 286 occupied cells and 241 unique tiles
and independently replays every pixel index. The fixed-encoding cache lower
bound is 19.6666666667; a twenty-write/344-clock range family is infeasible,
while the wider twenty-two-write/356-clock search remains unresolved.

The authored GUILE2 context is also being tested with a generic cap of sixty
distinct resident colors per bank across the frame, preserving exact opaque
and additive operand choices. That bounded solve returns UNKNOWN. Defaults
remain unchanged, and source pixels are independently replayed before any
candidate can claim success. No color reduction is applied.
