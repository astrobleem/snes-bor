# S7 publisher delivery — bounded admission, not a complete engine

The historical bounded milestones below are superseded for closure by
[the final delivery record](bor_actor_s7_closure.md) and
[native ownership/admission guards](bor_actor_s7_publication_guards.md).
Earlier artifacts remain evidence, not proof of the later fixes. In particular
the old source-excluded teardown, shared OBJ reservation, packet ordering and
BG-staging-overlapping admission cache were corrected during closure.

The initial bounded milestone below was supplemented by
[native packet palettes](bor_actor_s7_packet_palettes.md) and
[native release/reuse](bor_actor_s7_epoch_reuse.md). Those documents contain the
historical live streaming/lifetime evidence and its remaining timing failures.
The final record declares the tested publisher scope; these older sections
are not independent completion gates.
**COMPLETE SOURCE_EXACT ENGINE: NOT CERTIFIED. WHOLE PAK: NOT CERTIFIED.**
Strict source-snapshot latency and six-actor real-time feasibility remain
uncertified/failed. No content sets were enabled. ACCEPTED_COMPAT stays shipped.

Machine-readable delivery: `out/s7_delivery/report.json`. Full native traces,
ROM/MSU, snapshots, manifests and generated assembly remain in the referenced
`out/s7_final_*` directories. `out/s7_delivery/*-live-ledger.json` gives exact
content hashes, physical VRAM row ranges, displayed/queued references, actual
consumption clocks and terminal release state. Screenshots in that directory
are copies of emulator PPU output, not host-rendered references.

## Commits

| Commit | Capability |
|---|---|
| 575b5da | Native source entry frame |
| 64d4705ed2d04e6d523aeb77cb605d2e11376275 | Six-frame streaming |
| e51f6bef6cd3c9061dd41c9343013d208ca9f17d | Shared two-instance streaming |
| a94fb2deaf67452fca6a79ba8932b4c8120b3146 | Compact staggered residency |
| e6fa7d1 | Multi-model compiler/linker and normal-player independent-prefix proof |
| ce102e0 | Independent full animation probes, resident maps, two packet buffers and safe teardown |
| 3b43dd0 | Consolidated bounded evidence and foreign-frame resource diagnostics |
| 6610fc0 | Live palette replacement in atomic CGRAM/OAM packets, independent model/phase/map proof |
| fbfc338 | Hardware-fenced epoch release/reload, native compatibility checks, scoped staging-cache experiment |

The final evidence commit contains this report, foreign probes, resource
ledgers, screenshots and additional focused assertions. BG3 prerequisite
cf79e2a is retained; no production assembly or accepted actor semantics changed
in this closure. Other dirty/untracked project work was not staged.
The native assembly template is now a data-only emitter: multi-model linking
does not first load a fixture Kula image. A rebuild through that extracted
generator is byte-identical to `out/s7_final_cycles`; its existing native proof
therefore remains applicable. Empty-piece frames generate a zero-piece guard.

## Reproduce

From `E:\gh\snes-bor`, using fresh output directories:

```powershell
python tools/verify/actor_s7_stream_publisher.py --output out/repro_single --live
python tools/verify/actor_s7_stream_publisher.py --output out/repro_sync --second-actor --instance-leases --live
python tools/verify/actor_s7_stream_publisher.py --output out/repro_stagger --second-actor --instance-leases --compact-residency --stagger-ticks 1 --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_players --case players --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_cycles --case cycles --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_maps --case map-switch --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_bonus --case bonus --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_palette_phase --case palette-phase --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_epoch_reuse --case epoch-reuse --live
python tools/verify/actor_s7_foreign_publication.py
```

Requires the genuine local PAKs and existing installed Poppy, Mesen, Pillow and
SciPy toolchain. The foreign probe uses the pinned local S7 IR inventory and
verifies actual source-asset hashes. No foreign ROMs are packaged.
The `players` case intentionally admits only Kula0/Mary0..1; D705 outside that
prefix is expected, not a full animation or zero-miss certificate.

## Native capability evidence

| Workload | Result | Pinned bytes | Peak displayed + queued bytes |
|---|---|---:|---:|
| Single Kula attack1 | All six actual source frames; zero readiness faults | Existing stream | Existing lease proof |
| Synchronized Kula pair | Both six frames; zero readiness faults | Existing stream | Existing lease proof |
| Independent Kula pair | Both six frames; independent1/0,3/2,4/3; zero readiness faults | Existing compact stream | Existing lease proof |
| Kula + Mary | Normal source-world actions; Kula0/Mary1; base/alternate palettes | 7936 | Bounded prefix |
| Crab walk + Gold idle | All8 +6 frames, independent phases;122 checked displayed pictures | 5888 | 2304 |
| Two Lobsters, maps0/4→4/0 | Both actors' actual pixels, palettes and depth order;5 pictures | 4608 | 4608 |
| Crab + Lobster/map4 | Both actual source images;6 pictures | 5376 | 5376 |

The Bonus/cycle/map fixtures exercise exact animation/frame publication from
real source contexts and production slots under an explicit animation-only
fixture driver. They do **not** certify ordinary source AI, gravity, pickups,
Crab drift or Lobster fall behavior. The old fall-attack descriptor proof is
preserved separately. The viewport deliberately selects two slots; unrelated
control-world entities are not advertised as source-rendered. Every model key
inside that selection must resolve or the entire packet is rejected.

Single/sync/stagger closure ROMs are byte-identical to their accepted hashes:

```
single   2736cfead18747c3b8e7ff8760166ca9bf87d25c21d09624fd033cbd4502aef1
sync     67953df872febe68731b8e0d363ee2bdff4b21c8ee2598213ed13427c1285430
stagger  2ee5cdfa6924a3f002d7e91a1257abdd8db99001af27548a47ffdac9193c7752
```

New runnable artifacts (`bor.sfc` in each directory):

```
out/s7_final_cycles  7c88ba17590b83828770eb403c2fba78121e278860b58460c7e814d141a46f8e
out/s7_final_maps    9003c0e9b3feff3d3eb71145fa69e2aa0275632a2f5d58caf5078bf1facdc1c0
out/s7_final_bonus   79b99cfee79780ce5ad2e2704c817dc5574f45f0ecc15a8120fa3564bff07a77
```

All use `bor.msu` SHA256:
`ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`.

## Publication and ownership contract

One source IR feeds explicit policy-specific output. SOURCE_EXACT uses a
coherent pre-catch-up snapshot: source tick, slot/model/role/frame/map, projected
position/facing/altitude and depth order. The real compositor consumes it instead
of accepted actor-frame selection. Non-render world synchronization is retained.

The legal OBJ window is VRAM **bytes $8000-$9FFF**, words $4000-$4FFF. SMALL
16x32 blocks retain every encoded source pixel; source target-color adaptation
remains explicit RGB555 truncation. Different models share only identical
encoded blocks with compatible fixed layout. Remaps have separate palette hashes.

Existing same-model streaming retains its compact dynamic lease path. The new
small multi-model path pins the explicitly admitted set; it requires no heuristic
prefetch or relocation. Entry uploads are eight1024-byte tile transfers plus
two32-byte CGRAM transfers. Real completion is required before the source epoch.
Changing between two already-resident palettes requires no new tile copy and
has no palette lag relative to its OAM packet. More than two palette identities
or a larger pinned set is not silently admitted. This is not an unbounded
dynamic palette cache.

OAM packets at $7F8D00 and $7FA600 have independent sequence/source ownership.
Actual DMA ACTIVE publication and hardware completion are observed; no buffer
is written while owned. All544 consumed bytes are compared with the immutable
packet. CGRAM and actual target pixels are checked for every admitted picture.
Teardown waits for old packets, publishes a hidden replacement, then releases
the whole pinned lease only after hardware consumption. The native proof sees
phase2/hidden=false → phase2/hidden=true → phase3/both queues free.

## Timing — failures remain failures

A captured pre-update snapshot, a prepared packet, a DMA-consumed packet and a
physically rasterized picture are different events. Multiple packets can be
consumed in one VBlank; only the final one is counted as that displayed picture.
No source tick, attack, callback or frame duration was changed to improve timing.

Example cycle snapshot549 (Crab7/Gold5):

```
tiles/palettes ready        107518762 (before epoch)
coherent snapshot captured 167066934 / physical field467
packet preparation entered 167362022 / field468
hardware OAM consumed      167560418 / field469
actual pixels observed     167911556 / field469
```

This is pixel/resource PASS, **not** snapshot-to-next-field latency PASS.
The longer cycle trace also has two narrower preparation misses:

| Snapshot | Prepare entry | Actual queue publication | OAM consumption |
|---|---:|---:|---:|
| 199 | 129669582 /362 | 129704358 /363 | 130036994 /364 |
| 402 | 151466536 /423 | 151501272 /424 | 151836324 /425 |

Tiles and palettes were already resident. Immutable OAM packing/submission,
including intervening NMI time, finishes after the next opportunity; it costs
34776/34736 elapsed clocks from entry to queue publication in these witnesses.
The compiler/observer does not add a field of slack or label them exact. There
are zero packet-busy/resource-readiness rejections in the final cycle fixture.
Map/Bonus fixtures have zero prepare-entry-to-next-field misses, but their
earlier snapshot-capture latency is also not certified. No general transfer
margin or sustained six-actor CPU certificate is inferred.

The earlier six-actor finite-envelope and pre-fault attack-burst failures remain
failed. These smaller publisher tests do not overwrite their traces or claims.

## Resource diagnostics and foreign probes

`live_set_report` separates displayed/queued/new requirements from optional
prefetch. The fixed emitted-block lower bound for a six-instance packet using
Kula frames0..5 is **16640 bytes versus8192**, zero fragmentation; its detailed
ledger is `out/s7_delivery/blocked-packet-ledger.json`. This is a dry packet
layout diagnostic, not a six-actor runtime result or global SNES minimum.

The exploratory same-height Lobster/map pair had40 slivers versus34 and139
missing pixels; it remains **RESOURCE_BLOCKED for that emitted layout**. Final
map proof uses a declared vertical separation, not silently relaxed resource
limits. All admitted screenshots now must match, not merely one early picture.

Foreign dry probes preserve source/index geometry conditionally but retain
**DIALECT_BLOCKED** for unproven global palette/transparency/remap semantics:

| Model | Pieces (current packer) | Full-frame tile-byte upper bound | Source colors |
|---|---:|---:|---:|
| TMNT leo | 17 | 8960 | 12 |
| TMNT foot01 | 19 | 8704 | 9 |
| TMNT yellowb diagnostic | 189 | 193536 | 250 |
| He-Man he_man | 14 | 5120 | 31 |
| He-Man knightbot | 3 | 1536 | 16 |

These are not proven minimum VRAM requirements. The last two also exceed the
single15-opaque-color encoder. Nothing forces foreign syntax into BOR semantics.

## Validation and remaining engine work

- Native single/sync/stagger controls, distinct-model full cycles, map switch,
  Bonus pixels, complete transfers, independent packet identities and teardown.
- Bounded compatibility rendering/hit control100→96; exact control100→95.
- Eleven targeted compiler/resource assertions and one fixture-independent
  native-template assertion; Python compilation/diff hygiene.
- Generated width audit:472 cycle/Bonus and474 map labels, zero S7 violations.
- No campaign, all-PAK certification, historical-numeric rerun or SA-1 work.

Remaining categories are recorded in the JSON: **CPU** strict deadlines;
**NUMERIC** unrestricted movement/gravity/drift; **AI** runoff13 and other prior
gaps; **MEDIA** SEWER/role-media gaps; **DIALECT** foreign palette interpretation;
**RESOURCE** larger working sets, palette pools and scanline limits;
**ENVIRONMENT** water/rocking/depth/alias HUD; **SPECIAL_EFFECT** Time and auxiliary
effects. None is promoted to whole-model SOURCE_CERTIFIED by this renderer.
