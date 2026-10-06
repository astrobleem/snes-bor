# BYOR — Bring Your Own Rage

BYOR compiles supported Beats of Rage/OpenBOR source features to the SNES
runtime and reports unsupported capabilities explicitly. It is a capability
driven compiler, with the existing `tools/bor_compile` pipeline as its implementation.
It does not promise compatibility with arbitrary OpenBOR games or scripts.

The proven production build adapter remains bound to the original Beats of Rage
PAK, the historical BOR dialect and reviewed encoded media. Its immutable SHA-256
and adapter policies are recorded in `tools/bor_compile/source_profiles.json`.
That catalog contains no campaigns, queues or model lists. `--set` is validated
against the supplied source's discovered sets, rather than a CLI choice list.
The legacy original-source media builder still requires its canonical source
location; an identical PAK at another path is inspectable but fails build with
`SOURCE_MEDIA_LOCATION_UNBOUND` until that media binding is generalized.

Foreign PACK archives can now be inspected without an installed build profile:

```powershell
py -3.10 byor.py inspect --source "Masters of the Universe [v.3.0 Build 4086].pak" --output out/byor-motu-survey.json
py -3.10 byor.py inventory --source "Masters of the Universe [v.3.0 Build 4086].pak" --set Demo --output out/byor-motu-inventory.json
py -3.10 byor.py build --source "Masters of the Universe [v.3.0 Build 4086].pak" --set Demo --output build/byor-motu
```

`inspect` writes source documents/directive locations, discovered routes and
registry order, player declarations, palette authorities, animation frames,
scripts, image dimensions/delays/color requirements, audio identities, and raw
queue records. It also writes a neighboring `*-capabilities.json` and `.md`
summary. Unknown directives are retained. `inspect` exit 0 means inspection
finished, not that a ROM can be compiled. Foreign `inventory` currently returns
2 for unresolved capabilities; its source report is still written.

Foreign `build` currently returns specific capability diagnostics and produces
no candidate. It never invokes the original-game builder for an unknown source
identity. Resource diagnostics include actual required/available capacities;
schema diagnostics retain malformed queue locations. Classification counts
count source uses, not unique implemented features. `NOT_USED` means outside
the explicitly discovered campaign and declared model registry; implicit
engine scene hooks and dynamic script references still require dialect review.

MOTU milestone 4 is **partial**, not a compiled or native-certified game. The
survey finds source set 0, `Demo`, threshold 0, two stages, 34 syntactically
complete queue records and 22 stage spawns. An additional stray `at 1800` needs
dialect resolution; these are not certified packed-record counts. `He_Man` is
the sole loaded `type player`; `He_ManB` is a `type none` weapon form. The
filename's Build 4086 claim is not authenticated engine metadata. Script
commands, inline scripts and per-model palettes rule out treating it as the
reviewed historical original BOR dialect.

The shared `source_palette.py` helper resolves explicit palettes or first-frame
palette authority, decodes PNG/ACT colors and retains source alternate palette
indices. Its named RGB8-to-RGB555 conversion is a hardware adaptation. It does
not reduce color count, borrow original-game palettes, or certify production
runtime consumption. MOTU's HBreath peak frame still needs 204 opaque RGB555
colors (at least 14 static OBJ palette banks); hardware provides eight banks
of 15 opaque colors each. `source_color_capacity.py` produces reproducible
requirements and optional fixed-bank raster schedules. No color-reduction
examples or modified source assets are generated. That is a limitation of the current
static OBJ renderer, not proof that a raster palette or BG renderer is
impossible. The authorized policy is lossless raster OBJ first, then lossless
BG/hybrid if raster reaches a measured limit. The four banks eligible for OBJ
color math cannot carry the peak frame's unavoidable 50-byte adjacent-line
transition within the safe CGRAM access window. Generic offline slot scheduling
and Mode 4 component BG proofs preserve all 40 precomposed effect poses in a
fixed player/enemy/foreground context without reducing RGB555 colors. Native
SA-1 SCREEN arithmetic and palette bindings also pass exact cache, CGRAM and
pixel checks. The continuous production sequence now passes with the real
TAD frame/late pumps and an original-BOR stream request; complete transport
and MOTU audio bindings remain unproven. Moving geometry, changing underlays
and the live MOTU world remain unimplemented; this is not a MOTU candidate. See the
[lossless presentation receipt](receipts/byor-motu-lossless-feasibility.md).

The generic typed `playerkeys` API returns the pinned BOR key-mask values for
three-argument calls over an immutable, explicitly owned source-tick snapshot.
Native tests cover held, new and released keys, all fourteen source selectors,
dynamic strings and invalid ownership/index rejection. Q16.16 to integer
conversion remains an explicit adaptation. The native controller bridge now
publishes exact held/new/released masks from both physical SNES ports, with
Y/B attack/attack2, A jump, X special, L/R attack3/4 and Select escape as an
explicit target binding. Its outer refresh retains edges across catch-up ticks.
The live MOTU input/world owner remains unfinished.

The opt-in 4086 clock counts physical NTSC fields before visual busy gates,
accounts for short fields, consumes paused intervals and applies the pinned
50-tick/over-200-tick catch-up limits. Logical time advances only at a tick
commit. Its exclusive lease retires the legacy stage timer; opt-out preserves
that timer. Native arithmetic/ownership tests and the combined fixed-context
BG/audio sequence pass. Those combined ticks are empty: this is not a live
MOTU actor, combat or campaign owner.

From the repository root, with Python 3.10 and the existing build dependencies:

```powershell
py -3.10 byor.py inventory --set Easy --output out/byor-easy-source.json
py -3.10 byor.py build --set Easy --output build/byor-easy
```

The optional `--reuse-audio-from` skips audio compilation only after verifying
pinned audio inputs against the supplied Git ref. Adding a campaign changes
those inputs, so the first build after source bindings change must regenerate audio metadata. The output directory must
be new. The result contains `bor.sfc`, `bor.msu`, hardlinked PCM companions,
symbols and `production-runtime.json`. Build success establishes linkage;
it does not certify combat, visuals or a completed campaign traversal.

The runtime keeps the canonical source world on persistent SA-1, simulates
BOR at 200 Hz and presents at 30 Hz. Source-sized actors share 16 KiB of OBJ
residency. A sequenced event ring carries worker events. The compiler owns
typed campaign entries, queue records, source-model/resource bindings,
environment metadata, scenes and completion flags. Campaign ABI 3 names this
shared source-world runtime family; the independently selected source-set ID
resolves Easy, Normal, Hard or Bonus through generated offsets and typed entry tables.
Physical stage adjacency never defines a campaign route.

`inventory` traces required source directives to lowering/consumer definitions,
executes queue lowering in memory and reports compatibility adaptations and
pending native evidence. Unknown directives, unbound identities or media,
ambiguous bindings and resource-capacity failures stop compilation with an
explicit diagnostic. Existing `ACCEPTED_COMPAT` policies remain adaptations,
including coordinate/health transport, flattened scenery and encoded palettes;
they are not promoted to `SOURCE_EXACT`. There is no automatic artwork shrink
or legacy 32×48 fallback for this source-sized build path.

Original BOR source-set availability is emitted only for complete linked
candidates. Easy and Bonus candidates include all four original sets. Content availability
is independent of unlock: the real saved 32-bit `TimesCompleted` must meet the
PAK's `ifcomplete` threshold. Easy/Normal/Hard require 0; Bonus requires 1.
Locked names remain visible with a locked marker and cannot be confirmed.
All four original BOR sets share the compiler-owned source-world systems.
Easy no longer selects the historical campaign-0 path. Foreign/test catalog
bindings remain independent of this migration.

Bonus is source set 3. Its complete authored route is `DATA/EXTRA.TXT` followed
by `DATA/SCENES/SEWER.TXT`; neither entry has `next`. EXTRA has 184 packed queue
records, including 166 source spawns and no generated hole prefix. Its physical
stage ID is compiler-allocated after Hard. Queue storage follows the maximum
linked count (184 records, 1,840 bytes) within the existing u8 count/index ABI.

Bonus adds source Crab (`type none`, walking scenery) and Lobster (`type enemy`)
identities. Both use their own source-sized catalog art and source remaps.
Crab uses the generic noncombat horizontal-drift service on the S-CPU, alongside
the persistent SA-1 combat world. This is a new explicit `ACCEPTED_COMPAT`
adaptation: fixed-point motion, byte RNG and committed-source-tick scheduling do not
establish exact source float/RNG/scheduler equivalence. Authored spawn heading,
walk animation, noncombat classification and offscreen lifetime are retained.
No identity alias or artwork shrink is introduced.

Scene sequences lower ordered clips, music and repeat from source declarations.
Sewer plays the real two-frame `SEWER.GIF` (10 seconds per frame), then the
one-frame `THANKS.GIF` (5 seconds), using `TIME.BOR` repeat 1 through the
production scene transport. Existing 256×192 scene encoding is an adaptation.
`BOR.C:playgame()` increments the saved completion count at the terminal entry
of every set; the runtime's completion latch guards exactly one increment and
returns to TITLE. Build success alone is not a native completion certificate.

To recover a completed media build after an overlay failure, use the same
candidate with `--source-image build/byor-bonus`. This relinks generated
source assets through the shared builder and verifies source catalog identity;
it does not reconvert the PAK or replace the media. The source-image and
output paths must match, and PCM companions remain hardlinks.


Source visual admission now retires wholly offscreen poses and pins only visible
pieces before allocating tile blocks. A reused actor slot cannot resume a pending
pose from another source identity. These shared rules retain the 16 KiB OBJ budget,
source dimensions and visible artwork. The Biker model uses a compiler-declared
lossless shared palette layout across animations: source colors share the same
RGB555 palette banks and tile blocks across live/death poses. Independent decoding
checks the encoded pixels against the source GIFs; no artwork shrink or visual
identity substitution is involved.

After regenerating source media, `--source-image build/byor-bonus --repack-media`
repacks the same candidate through the shared media builder, then relinks it. It
preserves compiled audio and hardlinked PCM companions. A normal fresh build
performs this source/media compilation automatically.

Native milestone evidence: [Bonus certification](receipts/byor-bonus-m2.md).


Easy convergence (Milestone 3)

Easy is source set 0 with `ifcomplete 0`. The source linker owns all 16 typed
entries: 14 stages plus Rugal and Ending. Physical media IDs remain
`0, 1, 2, 11..21`; logical route order comes exclusively from LEVELS.TXT.
Queues contain 667 packed records (664 authored records plus three hole-prefix
records), including 545 source spawns. Source-owned queues use private compiler
output paths; the ROM packs fresh compiler bytes rather than unrelated dirty
legacy queue outputs.

The accepted pre-M3 Easy implementation used slot-owned compatibility enemies,
fixed-size visuals and 15 completion presentations, including Rugal. The migration explicitly
binds every spawn to its source identity, including Ramon and Time. The source's
six `next` boundaries now control showcomplete; the legacy nine extra completion
presentations are removed. All original BOR sets select the shared campaign ABI 3
and source-sized visual path. The old campaign-0 resolver remains unexposed for
historical/internal compatibility; no original BOR selector maps to it.

Source `mirror` reuses the same source-sized pose, palette and tiles for its
second image, with shared viewport/resource admission and foreground priority.
Ground reflection uses BOR.C's foot formula through the existing coordinate
adapter. Fixed-point placement, flattened layer/depth and airborne presentation
remain explicit ACCEPTED_COMPAT adaptations rather than SOURCE_EXACT claims.

The shared player controller remains bounded to its established movement and
grounded attack support. Pending source-resource admissions can defer a pose;
this milestone does not certify continuous presentation cadence or complete
original-engine player behavior. The inherited shared bootstrap actor is outside
authored queue coverage and is excluded from the representative enemy proof.

The Easy semantic differential and native certification are recorded in
[the Milestone 3 receipt](receipts/byor-easy-m3.md). Existing Milestone 2 receipts
remain evidence of the accepted pre-M3 architecture.
