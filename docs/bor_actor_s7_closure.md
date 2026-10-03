# S7 delivery: generic source actor publisher

**S7 publisher capabilities are complete for the declared admission domains.**
This is not complete SOURCE_EXACT engine, whole-model, whole-PAK, or six-actor
real-time certification. Existing simulation and publication deadline failures
remain failed. ACCEPTED_COMPAT remains the default; no sets were enabled.

## Implementation

One source-exact IR feeds compiler-owned `source_publication_native.py` and
the existing lossless frame packer. Runtime render snapshots capture real
resident source-world state before catch-up, separately from mutable OAM.
SOURCE_EXACT consumes its generated pieces; accepted actors retain their
existing renderer. Shared depth order and low-level OAM remain common.

Same-model animation streaming retains the accepted compact working-set path.
The distinct-model backend admits a deterministic content-addressed block set
per epoch. It shares only byte-identical encoded blocks, distinguishes palette
identity from graphics identity, and maintains separate instance frame,
position, facing, altitude and map state. It does not reserve duplicate tiles
merely because two actors reference a resource.

The legal OBJ range is VRAM bytes `$8000–9FFF` (8 KiB), never the overlapping
second window. Accepted actors reserve their actual footprints. Distinct-model
entry transfers fill only permitted source rows when accepted allocations
coexist. Subsequent frame changes select resident content, while packet-local
palettes can stream new maps without duplicating indexed graphics.

Tile readiness follows actual completed queued transfers. A packet with two
palettes charges 608 bytes: 64 CGRAM then 544 OAM in the same NMI transaction.
Two immutable packet buffers remain owned until actual queue consumption.
Tickets prevent reversal if NMI interrupts ring insertion. Whole-epoch leases
are released only after an actually consumed source-excluded picture, retaining
valid accepted actors. Close/reopen, invalid-owner rejection, shared scanline
admission and displayed-framing fault retirement are native, not host oracles.
See [the boundary audit](bor_actor_s7_publication_guards.md).

The final DMA consumer independently enforces those leases. A late legacy
VRAM/CGRAM request cannot overwrite source resources between render guards.
Only the exact current entry tuple can fill protected resources before ready;
after ready they remain immutable until hardware retirement. The final mixed
artifact additionally rejects malformed VRAM and CGRAM requests with zero
hardware changes. These negative requests occur after its positive workload.

## Supported and measured workloads

| Workload | Evidence | Prepared-next-field misses |
|---|---|---:|
| Single Kula, six frames | Fresh control, all source pixels, accepted ROM hash | 0 recorded readiness misses |
| Synchronized same-model pair | Accepted six-frame streaming/fence control retained | 0 recorded readiness misses |
| Independent staggered same-model pair | Accepted compact six-frame control retained | 0 recorded readiness misses |
| Crab + Lobster map4 | Distinct models, 5,376 resident bytes, native pixels | 0 |
| Two Lobsters, maps0/4 exchanged | 4,608 bytes, distinct palette ownership | 0 |
| Crab walk + Angel pain, left-facing, maps0/1/4 | Independent phases, 7,680 pinned / 6,144 peak live bytes | 2 |
| Crab eight-frame / Gold six-frame cycles, close/reopen | 5,888 pinned / 2,304 peak live bytes; 107 pixel proofs | 8 |
| Source Crab + accepted Mary, close/reopen | Accepted tiles/OAM protected; 38 source pixel proofs | 4 |

These columns do **not** replace the stricter snapshot-capture deadline.
`report.json` separately records both clocks and every failed witness. For
example, the final phase workload's snapshots 26 and 36 were prepared at
110,722,144 and 111,440,474 master clocks, queued at 110,754,550 and 111,492,036,
and consumed at 111,187,300 and 111,902,036. Both missed the next opportunity
from preparation; the actual tile/CGRAM/OAM output was correct. No new slack,
source delay extension, or spare transfer budget is inferred.

The map-only probe is explicitly bounded through completed source tick19,
before its unlinked later idle frame. Its old observer waited for a stale
snapshot-valid bit and unintentionally continued into unadmitted frames; that
failed run remains `out/s7_closure_maps`. The corrected bound changes no source
state, timer, simulation update or publication cutoff.

## Exact reproduction

Run from `E:\gh\snes-bor`, with the existing local PAK, Poppy and Mesen tooling.
Use fresh output directories. All commands build from source/code generation
before native execution; no expected OAM or screenshot is injected.

```powershell
python tools/verify/actor_s7_stream_publisher.py --output out/reproduce-single --live
python tools/verify/actor_s7_stream_publisher.py --output out/reproduce-sync --second-actor --instance-leases --live
python tools/verify/actor_s7_stream_publisher.py --output out/reproduce-stagger --second-actor --instance-leases --compact-residency --stagger-ticks 1 --live
python tools/verify/actor_s7_multi_publisher.py --output out/reproduce-bonus --case bonus --live
python tools/verify/actor_s7_multi_publisher.py --output out/reproduce-maps --case map-switch --live
python tools/verify/actor_s7_multi_publisher.py --output out/reproduce-phase --case palette-phase --facing-left-slot 1 --live
python tools/verify/actor_s7_multi_publisher.py --output out/reproduce-epoch --case epoch-reuse --live
python tools/verify/actor_s7_multi_publisher.py --output out/reproduce-mixed --case mixed-epoch --retirement-probe dma --live
python tools/verify/actor_s7_multi_publisher.py --output out/reproduce-resource --case scanline-block --live
python tools/verify/actor_s7_multi_publisher.py --output out/reproduce-framing --case palette-phase --retirement-probe framing --live
python tools/verify/actor_s7_delivery_report.py
```

The report command consolidates the named retained closure artifacts, not the
arbitrary `reproduce-*` folders. Primary artifact roots and ROM SHA-256:

| Directory under `out/` | `bor.sfc` SHA-256 |
|---|---|
| `s7_closure_single` | `2736cfead18747c3b8e7ff8760166ca9bf87d25c21d09624fd033cbd4502aef1` |
| `s7_final_sync` | `67953df872febe68731b8e0d363ee2bdff4b21c8ee2598213ed13427c1285430` |
| `s7_final_stagger` | `2ee5cdfa6924a3f002d7e91a1257abdd8db99001af27548a47ffdac9193c7752` |
| `s7_lease_enforced_bonus` | `e4ebaf1e8077a2eef3cf18124389e0270054e41d73b894c79bd2dab7a1b4e3a6` |
| `s7_lease_enforced_maps` | `eed6d77faa6207d303468e0b5ac182078aecc140512d00cc22b47dbf912652f6` |
| `s7_lease_enforced_phase_02` | `3aebbb48e0d24eb2443efcd1320955d8802e6f87ba5d1d61c5e5d81410a560a6` |
| `s7_lease_enforced_epoch` | `15b683ce4a28513e5ef804f1b1bc26a6f9d90594fc5e1ca2da7f524d92f4a45d` |
| `s7_dma_lease_negative` | `6304c241e2e4d1ad492ce3ace9dbc1401ca92b939dc280a3eaf32b4e65d559a7` |

Each root retains `bor.msu`, generated assembly/symbols, manifests and native
traces. Common MSU SHA-256:
`ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`.
Screenshots copied to `out/s7_delivery/{maps,bonus,palette-phase,epoch-reuse,mixed}.png`
are actual emulator framebuffer output. `*-live-ledger.json` enumerates exact
block hashes, physical VRAM rows, queued/displayed references and release
clocks. Source-excluded shared packets may continue after source leases end;
they are not outstanding source graphics references.

## Commits and validation

Publisher history, in order: `575b5da`, `64d4705`, `e51f6be`, `a94fb2d`,
`e6fa7d1`, `ce102e0`, `3b43dd0`, `6610fc0`, `fbfc338`, `27b6377`, `7f3e71a`,
`502cec7`, `439cfb2`, `58d7427`, followed by the closure-evidence commit containing this document.
Full hashes and subjects are in `out/s7_delivery/report.json`; BG3 prerequisite
`cf79e2a9b0fbe76c4cd84f16a0b0b803b13c4daa` remains accepted separately.

Closure checks: 15 compiler/resource tests, six shared-admission/ownership
tests, two palette tests, native source/accepted pixel and transfer proofs,
public close under persistent resource/owner rejection, actual framing-fault
retirement, width audit (638 labels, no S7 violations), changed-Python
compilation and diff hygiene. The single control's first emulator startup
attempt timed out before gameplay; its log is retained. A retry using the same
already-built byte-identical ROM passed all six frames. No campaign or
historical-numeric suite was rerun.

## Explicit remaining blockers

- **CPU:** strict snapshot/display latency, listed preparation misses, and
  existing six-actor early/burst misses. No sustained six-actor claim.
- **NUMERIC:** unrestricted movement, gravity and decimal drift beyond the
  bounded Watcom-family domains.
- **AI:** runoff driver13 and unsupported behavior/effect paths, including
  Time's still-missing gameplay timer/lifecycle.
- **MEDIA:** SEWER and independently missing/unencoded source-role media.
- **DIALECT:** genuine TMNT/He-Man palette, transparency and remap semantics.
  Retained dry probes decode Leo/Foot01/He-Man images; their geometry reports
  are conditional and are not foreign-game or target-pixel certification.
- **RESOURCE:** the admitted pinned block set must fit 8 KiB minus accepted
  reservations; 16 descriptor keys per current table and two simultaneous
  packet palette instance slots. Six independent Kula frames require 16,640
  bytes in the emitted indivisible-block ABI. Same-height two-Lobster OAM
  exceeds the 34-sliver constraint and is rejected natively. These are current
  allocation/encoding bounds, not proofs of global SNES impossibility.
- **ENVIRONMENT:** water, rocking, depth-dependent blocked/endhole and alias
  name/HUD semantics remain unchanged.

No failed CPU or visual deadline has been renamed PASS. The delivered result
is the reusable, opt-in native publisher with tested ownership and explicit
resource/timing limits, not universal source execution certification.
