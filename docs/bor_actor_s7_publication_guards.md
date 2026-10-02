# S7 native publication boundary closure

This extends the existing source publisher, not the shipped ACCEPTED_COMPAT
actor path. Source simulation deadlines and whole-model certificates are not
promoted by these changes.

## Ordered pictures and shared admission

An NMI can advance the DMA ring after a producer samples its insertion cursor.
The previous mixed trace actually consumed snapshot 219 before 216. Two
immutable OAM buffers now carry monotonic producer tickets. The NMI orders
their source pointers before transfer, without moving payloads or unrelated
requests. Queue ownership polling scans actual active requests and retries an
absent result across a committed-NMI generation change. A mismatched request
length is rejected, not transferred with a guessed ABI.

Source snapshots are captured and submitted at the render-before-catch-up
boundary. Source actors do not also execute the accepted renderer. Early
publication preserves the caller's D, DBR, X/Y widths, registers and stack;
the live observer checks those boundaries.

Before staging, a generated capacity bound includes both source pieces and
accepted actors. Before submission, native admission checks the complete
shared OAM picture: 128 entries, 32 objects per line and 34 conservative
8-pixel slivers. The exact cache key is the ordered Y/size sequence plus its
length. X clipping is not used to grant additional capacity.

## Ownership and fault retirement

Accepted OBJ allocations remain reserved in the legal shared 8-KiB window.
Generated guards verify the actual live slot, policy, tile column and palette
owners before entry transfer and publication. An invalid allocation fails
D708. It cannot strand a close: lifecycle requests are serviced before
capture regardless of picture admission, and a source-excluded replacement
omits invalid owners while retaining valid accepted actors. Source tiles are
released only after that replacement is physically consumed.

Incoming source packets must match the camera committed by the NMI. A second
check protects the *already displayed* picture, even without a new packet.
After actual OAM transfer, NMI saves a source-excluded copy of that hardware
picture. On a framing violation it transfers this fallback before forced
blank is released, leaves accepted OAM and CGRAM intact, records D70C and
requests the normal close fence. It does not change the camera, source clock,
or release the graphics pool itself. This is an explicit rejected picture,
not a successful source publication or an extra field of latency allowance.

The negative framing oracle compares actual OAM against the prior picture
with only native SMALL source pieces hidden at Y=224. The failed first
experiment ran after blank release and is retained in
`out/s7_display_retirement_01`. The corrected hook in
`out/s7_display_retirement_02` completed at scanline 244 with zero OAM or CGRAM
differences from the fault-path oracle.

## Audited WRAM

| Owner | Range |
|---|---|
| Source snapshot | `$7F8C00–8CFF` |
| Immutable packet 1/control | `$7F8D00–8F3F` |
| Existing BG staging, untouched | `$7F9000–911F` |
| Existing queue arena, untouched | `$7F9200–9FFF` |
| Existing frontpanel tile map | `$7FA000–A5FF` |
| Immutable packet 2/control | `$7FA600–A83F` |
| Packet palettes and protocol scratch | `$7FA840–A8DF` |
| Admission cache / invalid-owner mask | `$7FA900–AA09` |
| NMI fallback OAM / framing scratch | `$7FAB00–AD27` |
| Existing frontpanel slot map, untouched | starts `$7FB000` |

The initial uncommitted admission cache at `$7F9000` overlapped live BG staging.
It was moved before closure; those earlier cache traces are not memory-safety
certification. The new allocation has compile-time bounds and a focused
non-overlap test.

## Reproduction and scope

From the repository root, use a fresh output directory:

```powershell
python tools/verify/actor_s7_multi_publisher.py --output out/guarded-phase --case palette-phase --facing-left-slot 1 --live
python tools/verify/actor_s7_multi_publisher.py --output out/guarded-epoch --case epoch-reuse --live
python tools/verify/actor_s7_multi_publisher.py --output out/guarded-owner --case mixed-epoch --retirement-probe owner --live
python tools/verify/actor_s7_multi_publisher.py --output out/guarded-framing --case palette-phase --retirement-probe framing --live
python tools/verify/actor_s7_multi_publisher.py --output out/guarded-resource --case scanline-block --live
```

Negative probes are deliberately not full positive animation/timing controls.
The same-height two-Lobster picture is rejected before hardware publication,
then retires through the public close API. Positive left-facing Crab/Angel
publication covers independent frames and maps 0/1/4 with exact target-color
pixel/OAM comparison. Mixed Crab/accepted-Mary publication covers normal
accepted rendering during close/reopen and protects its reserved tile rows.

All measured preparation/publication misses remain in the artifact JSON.
Early publication removes the old render-after-catch-up delay, but it does
not establish universal next-field or six-actor CPU feasibility. No spare
tile-transfer budget is inferred from these measurements.

## Consumer-side graphics lease enforcement

`actor_source_vram_lease.pasm` also checks actual queued VRAM/CGRAM requests
before hardware DMA. Slot/model validation alone cannot prevent a late legacy
upload arriving before the next render guard. The compiler emits a 128-byte
map of protected 64-byte OBJ segments. Requests crossing segment boundaries
inspect every intersected segment; reserved accepted footprints remain free.
During entry, only the exact current compiler transfer tuple (source bank,
source address, destination, length and type) can write protected data. Once
ready, the pinned set cannot be overwritten until the close fence releases it.
Queued legacy CGRAM writes are similarly excluded from palettes6/7. The
publisher's packet-local palette transaction remains its explicit owner.

Armed ownership and NMI scratch occupy `$7FAD28–AD35`, still below the audited
`$7FB000` allocation. The native malformed-request probe in
`out/s7_dma_lease_negative` rejected a 32-byte VRAM write at `$8980` and a
32-byte CGRAM write at byte448. Neither altered VRAM or CGRAM. It injects only
negative DMA requests after the positive mixed workload, never source state
or expected OAM. Valid accepted uploads were byte-compared in the same run.

Reproduce with `--case mixed-epoch --retirement-probe dma --live` using the
same multi-publisher command above. This is a fault-path ownership proof,
not another timing or whole-model certificate.
