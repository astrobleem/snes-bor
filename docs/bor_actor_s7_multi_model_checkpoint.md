# S7 multi-model pinned-set milestone (not S7 closure)

The opt-in compiler now links content-addressed pieces from distinct models,
independent model/role/frame/map keys, and two independently completed CGRAM
palettes into the existing legal8KiB OBJ window. It does not change the accepted
single/same-model streaming compiler or default production assembly.

Reproduce:

```powershell
python tools/verify/actor_s7_multi_publisher.py --output out/s7_multi_repro --live
```

Uses existing local SciPy1.11.2, source PAK, Poppy and Mesen prerequisites.
Fixture actions are issued to real source-world slots at source ticks1 and6.
Subsequent frames are produced by the existing scheduler, not injected.
Kula attack1 frame0/base map and Mary attack1 frames0..1/map1 form a31-block,
7936-byte pinned set. This is deliberately bounded admission, NOT a full
two-model animation stream. Oversize pinned sets are diagnosed as a POLICY
pool limit, not misrepresented as a minimum simultaneous hardware requirement.

Native artifact `out/s7_multi_native_07`:

- Snapshot9: prepared109372520, consumed109667128/field307,
  raster110018264: Kula0 + Mary1,4019 source-visible pixels, zero mismatch.
- Snapshot13: prepared109788110, consumed110024490/field308,
  raster110375628: same independent identities, zero mismatch.
- Eight1024-byte VRAM transfers and two32-byte CGRAM transfers all compared
  against actual ROM bytes at the real DMA completion consumer: zero mismatch.
- Palettes completed before the source epoch; each packet compares both actual
  hardware palettes and actual OAM to its coherent source snapshot.
- No tile/palette replacement occurs while the pinned set is live. Whole-world
  teardown is its release boundary. This intentionally does not claim a dynamic
  multi-model cache or alternate-map replacement-in-flight proof.
- Outside the admitted model/frame keys, D705 is recorded and the entire packet
  is refused. Missing Mary/Kula resources cannot produce a mixed partial packet.
  The harness's passing assertion is bounded pixel publication, NOT a zero-miss
  full-run assertion. Other source models in the control world are outside this
  linked publication set and are not claimed as rendered/certified.

The new emitter also handles partially offscreen SMALL pieces using the actual
X-high bit; the source-pixel oracle detected the old whole-piece clipping.
This change is opt-in and does not modify accepted rendering.

ROM SHA256 `1dcf3a4379c02725e79d540de68d761e2b0683fde7dbd6c1717d163d2e948b09`.
MSU SHA256 `ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`.
Screenshots `publication-7.png`, `publication-8.png`; `multi-proof.json` records
completion clocks and pixel results. The full raw trace remains `mesen.log`.

Four focused compiler tests pass: multi-model keys, map4 palette/tile identity,
honest pinned-pool rejection and native lookup/error generation. Generated
world width audit:473 branch-target labels, zero S7 violations. Python compile,
native assembly and diff checks pass. Source remap derivation follows pinned
BOR.C `load_colourmap`: identity initialization, common rectangle, row-major
last assignment wins. RGB555 truncation remains the declared target adaptation.

Remaining S7 work: native selector>=4/Bonus probes, admitted multi-model lifetime
coverage beyond this pinned prefix, palette streaming policy/fences, resource
lower-bound diagnostics, foreign-frame probes and final bounded integration.
