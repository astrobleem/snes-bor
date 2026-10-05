# BYOR — Bring Your Own Rage

BYOR compiles supported Beats of Rage/OpenBOR source features to the SNES
runtime and reports unsupported capabilities explicitly. It is a capability
driven compiler, with the existing `tools/bor_compile` pipeline as its implementation.
It does not promise compatibility with arbitrary OpenBOR games or scripts.

The current production build adapter is bound to the original Beats of Rage
PAK in this repository, the historical BOR dialect and its reviewed encoded
media. Other source games need explicit source, model, media and runtime capability
bindings before this adapter can build them. `SOURCE_PROFILE_UNCONFIGURED`
rejects a different source rather than silently compiling the original game.

From the repository root, with Python 3.10 and the existing build dependencies:

```powershell
py -3.10 byor.py inventory --set Bonus --output out/byor-bonus-source.json
py -3.10 byor.py build --set Bonus --output build/byor-bonus
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
resolves Normal, Hard or Bonus through generated offsets and typed entry tables.
Physical stage adjacency never defines a campaign route.

`inventory` traces required source directives to lowering/consumer definitions,
executes queue lowering in memory and reports compatibility adaptations and
pending native evidence. Unknown directives, unbound identities or media,
ambiguous bindings and resource-capacity failures stop compilation with an
explicit diagnostic. Existing `ACCEPTED_COMPAT` policies remain adaptations,
including coordinate/health transport, flattened scenery and encoded palettes;
they are not promoted to `SOURCE_EXACT`. There is no automatic artwork shrink
or legacy 32×48 fallback for this source-sized build path.

Normal, Hard and Bonus availability is emitted only for complete linked
candidates. A Bonus candidate includes all four original sets. Content availability
is independent of unlock: the real saved 32-bit `TimesCompleted` must meet the
PAK's `ifcomplete` threshold. Easy/Normal/Hard require 0; Bonus requires 1.
Locked names remain visible with a locked marker and cannot be confirmed.
Easy uses its existing compatibility path; Normal, Hard and Bonus share the
accepted source-world systems.

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
