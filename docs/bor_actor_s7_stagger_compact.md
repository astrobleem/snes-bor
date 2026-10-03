# S7 bounded staggered residency closure

## Reproduce

From the canonical checkout, with the existing local source PAK, build tools,
MSU assets and Mesen environment:

```powershell
python tools/verify/actor_s7_stream_publisher.py --output out/s7_stagger_compact_repro --second-actor --instance-leases --compact-residency --stagger-ticks 1 --live
python tools/verify/actor_s7_stagger_residency.py out/s7_instances_stagger_delivery --replacement out/s7_stagger_compact_delivery --output out/s7_stagger_live_set.json
```

Use a new output directory. Compact packing uses local SciPy 1.11.2/HiGHS,
NumPy and Pillow. The solver must return an optimal cover or compilation fails;
sorted candidate ordering and a repeated compilation test establish local
determinism. A different solver version is not promised byte-identical output.

## Diagnosis and concrete correction

Both old D703 boundaries retain the physically consumed 4/3 packet and require
frame5. There is no queued unconsumed packet or in-flight tile job at either
miss. Seven NEW frame5 jobs require retirement minimum4. The real consumed
minimum is3: shortening that lease would overwrite displayed P2 graphics.
The first miss is clock110885228/snapshot39; the second111166290/snapshot43.

`out/s7_stagger_live_set.json` enumerates all36 SHA256-addressed256-byte
resources at EACH miss, actor/frame references, four physical64-byte row spans,
actual last OAM consumption, observed safe release and all32 resident slots.
Each required-block ledger sums to9216. Displayed footprints occupy5376 bytes;
2816 bytes are not displayed, largest contiguous byte run2112. Required
allocation shape is four64-byte rows with512-byte row stride, not a flat256-byte
run. Old placement also conflicts in slots9..16. No optional future-only
prefetch contributes to that required union. No missed refcount decrement or
extra publication lease was found.

However,9216 is NOT a minimum source-pixel representation. The old packer
restricted pieces to a grid. The new opt-in compiler covers occupied8x8 source
cells with overlapping16x32 source rectangles. Overlaps repeat IDENTICAL source
pixels; source transparent padding remains transparent. This changes neither
source artwork, palette indices, offsets, facing, source timing nor native OBJ
address semantics. Native pieces remain nonwrapping SMALL objects.

Piece counts for frames0..5 become10,12,13,12,12,11. The critical union3/4/5 is
30 distinct blocks =7680 bytes, fitting the SAME8192-byte window at VRAM byte
$8000-$9FFF (word$4000-$4FFF), with512 bytes remaining. This is a constructive
upper bound, not a claim of globally optimal VRAM packing.

The allocator additionally retains older already-resident frame sets when they
fit alongside the mandatory current/next set. Union2/3/4 fits32 slots;3/4/5
fits30. Frame5 replaces retired frame2 resources, not still-displayed frame3.
No displayed or queued blocks move. Existing last-use leases, actual DMA
completion and immutable OAM-consumption fences are unchanged. Content identity
uses encoded bytes, not instance names; independent actor state is unchanged.
No extra future-frame allocation/prefetch policy was added. Known-next-frame
jobs still use the existing admitted transfer path; this trace, not a host
planner, establishes readiness for this specific workload.

## Native evidence

Artifact: `out/s7_stagger_compact_delivery`.

- Both instances: all six frames observed through real OAM/PPU pixels.
- Independent pairs1/0,3/2,4/3; final formerly blocked5/5 is now visible.
- Zero D703/readiness misses; zero native faults.
-33 tile completions,11008 bytes, zero incorrect bytes or visible overwrites.
-13 complete immutable OAM packets; palette and OAM comparison pass.
- Final5/5 snapshot39 prepared111024230; hardware consumed111096614,
  physical field311, sequence13. Raster observation111447728 matches2334 P1
  and2331 P2 pixels;3 P2 pixels are correctly occluded by existing HUD.
- Screenshot: `packet-0-5_1-5.png`. Full `stream-publication.json`, `mesen.log`,
  raw raster/OAM/CGRAM evidence retained. The ledger includes the new30 blocks
  with physical placements and hardware consumers plus the completion trace.

ROM SHA256: `2ee5cdfa6924a3f002d7e91a1257abdd8db99001af27548a47ffdac9193c7752`.
MSU SHA256: `ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`.

## Validation and limits

Four focused tests check all source pixels after native encoding/placement,
retained lease safety, the7680-byte conflict-free placement, and repeated
compiler determinism. The original resource-blocked test remains unchanged.
Staggered observation requires each instance's six frames, not six identical
frame pairs; synchronized runs retain the stronger synchronized-pair assertion.
Production width audit:0 new findings. Candidate built before native proof.

Original controls each rerun once: `out/s7_stagger_single_closure` and
`out/s7_stagger_sync_closure`, both PASS. Their ROM hashes remain respectively
`2736cfead18747c3b8e7ff8760166ca9bf87d25c21d09624fd033cbd4502aef1` and
`67953df872febe68731b8e0d363ee2bdff4b21c8ee2598213ed13427c1285430`.

This does NOT close earlier CPU latency failures, whole-model certification or
arbitrary phase combinations. Other triple-frame sets can still exceed32 slots.
No transfer-time budget is inferred from the512-byte space margin. No second
OBJ window, new DMA budget, early lease release, actor-state workaround or
accepted-policy change is used. Independent-model residency remains next.
