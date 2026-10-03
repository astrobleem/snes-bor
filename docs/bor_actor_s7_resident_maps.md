# Native multi-model and resident-map publication

This capability builds on e6fa7d1 and the accepted native streaming publisher.
It does not replace the single/same-model streaming backend or production
ACCEPTED_COMPAT. New code is generated only for explicit publication requests.

## Admitted implementations

- Existing single, synchronized and compact staggered streaming remain intact.
- A bounded multi-model set shares byte-identical 256-byte encoded SMALL blocks
  across model/frame identities. Content hashes do not collapse palette identity.
- The entire explicitly admitted set is pinned in VRAM bytes $8000-$9FFF;
  palettes occupy CGRAM bytes $1C0-$1FF (OBJ6/7). No second overlapping window.
- Two immutable 544-byte OAM packets have independent queue/source/completion
  identity: $7F8D00 and $7FA600. The latter is after the 768-entry FP Tile2Slot
  table (ending $7FA5FF), before Slot2Tile at $7FB000. Build assertions check
  these bounds. Controls end at $7FA83F. DMA admission remains <2816 bytes.
- Per-slot render state and depth order are captured coherently before source
  catch-up. The snapshot is outside NMI-cleared OAM. The fixture explicitly
  selects slots0/1 for its viewport; other control-world slots are not claimed
  as source-rendered. Unknown keys *inside* the selected viewport reject the
  complete packet with D705, rather than falling back to accepted actor data.
- Teardown request $7F8CF2=1 waits for both old packets, enqueues a fully hidden
  packet, and publishes state3/resource release only after that packet completes.
  This ends a publication epoch; it does not simulate actor death or certify AI.

## Native evidence

`out/s7_final_cycles`: Crab walk0..7 and Gold idle0..5, independently scheduled
from real source contexts, 5888 pinned bytes, two independent palettes. Every
frame is actually visible, all checked pixels/OAM/CGRAM match, no busy rejection
or owned-packet overwrite. The animation-only test driver deliberately does not
execute/certify these actors' unrelated AI or movement. It is a fixture flag,
not a source model-name-specific behavior adapter.

`out/s7_final_maps`: two independently positioned Lobster instances select maps
0/4, then exchange to4/0 through their actual map-owner fields at source tick7.
Both palettes are hardware-completed before the source epoch; switching selects
resident palettes and does not duplicate tiles. 4608 bytes, 36 total SMALL
pieces, conservative maximum20 slivers/scanline. This proves resident remap
switching, not unbounded dynamic CGRAM replacement.

`out/s7_final_bonus`: Crab plus Lobster/map4, 5376 bytes,21 pieces, maximum22
slivers; every observed admitted packet passes source pixels and ownership.
Lobster fall attack and Crab drift semantics are not modified or recertified.

The final long-cycle run retains two preparation-to-next-field misses (source
snapshots199 and402). Snapshot-capture-to-next-field timing is also explicitly
NOT_CERTIFIED. Correct final pixels and bounded queue occupancy do not turn
those into timing passes. Existing six-actor CPU failures are unchanged.

## Rejected evidence retained

- `out/s7_cycles_native_01` and `_02`: one packet,44 busy rejections.
- `out/s7_cycles_native_04/REJECTED.md`: second-buffer DMA source-address bug;
  superseded by independently observed source identities in `_06` and delivery.
- `out/s7_map_switch_delivery_02`: same-height Lobster pair requires40 emitted
  slivers on a scanline;139 source pixels missing. This is RESOURCE_BLOCKED for
  that layout. Earlier assertions that checked only *one* good picture were
  insufficient. The final observer checks **all** admitted pictures. The final
  vertically separated case is a different, explicitly declared admitted layout,
  not a relabeling of this failed one.
- `out/s7_map_switch_delivery`: teardown branch used RTL at a JSR boundary;
  corrected to RTS and actual hide/completion fence retested.
- One initial `out/s7_final_bonus` harness attempt tested an uninitialized tick
  before publication ready. The observer now requires ready plus a valid source
  row; the same already-built candidate then ran successfully.

## Resource bounds

`compile_set` rejects oversized pinned pools with machine-readable block/hash/
reference ledgers. It explicitly does not pretend that all future animation
frames must coexist. `live_set_report` instead accepts concrete displayed,
queued, in-flight, and new-packet keys and computes their union, excluding
prefetch/unreferenced-only blocks. Its lower bound is for the emitted fixed
block ABI, not a global minimum over every possible SNES artwork decomposition.
Equal-sized footprints have zero allocator fragmentation; the admitted sets
never relocate a displayed block. Arbitrary dynamic multi-model working sets
or more than two simultaneous palette identities are not silently admitted.

## Reproduction

Use a fresh output directory for each command:

```powershell
python tools/verify/actor_s7_multi_publisher.py --output out/repro_cycles --case cycles --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_maps --case map-switch --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_bonus --case bonus --live
python -m unittest discover -s tools/bor_compile -p test_source_publication_set.py
```

These commands use the local original BOR PAK, installed Poppy/Mesen/Pillow/SciPy
toolchain and compiler-generated ROM overlays. They do not inject expected OAM,
animation indices, or per-tick expected simulation snapshots.
