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
py -3.10 byor.py inventory --set Hard --output out/byor-hard-source.json
py -3.10 byor.py build --set Hard --output build/byor-hard
```

The optional `--reuse-audio-from` skips audio compilation only after verifying
pinned audio inputs against the supplied Git ref. Adding a campaign changes
those inputs, so the first Hard build must regenerate audio metadata. The output directory must
be new. The result contains `bor.sfc`, `bor.msu`, hardlinked PCM companions,
symbols and `production-runtime.json`. Build success establishes linkage;
it does not certify combat, visuals or a completed campaign traversal.

The runtime keeps the canonical source world on persistent SA-1, simulates
BOR at 200 Hz and presents at 30 Hz. Source-sized actors share 16 KiB of OBJ
residency. A sequenced event ring carries worker events. The compiler owns
typed campaign entries, queue records, source-model/resource bindings,
environment metadata, scenes and completion flags. Campaign ABI 3 names this
shared source-world runtime family; the independently selected source-set ID
resolves Normal or Hard through generated offsets and typed entry tables.
Physical stage adjacency never defines a campaign route.

`inventory` traces required source directives to lowering/consumer definitions,
executes queue lowering in memory and reports compatibility adaptations and
pending native evidence. Unknown directives, unbound identities or media,
ambiguous bindings and resource-capacity failures stop compilation with an
explicit diagnostic. Existing `ACCEPTED_COMPAT` policies remain adaptations,
including coordinate/health transport, flattened scenery and encoded palettes;
they are not promoted to `SOURCE_EXACT`. There is no automatic artwork shrink
or legacy 32×48 fallback for this source-sized build path.

Hard availability is emitted only for the complete linked candidate. Bonus
remains unavailable. Easy uses its existing compatibility path; Normal and
Hard share the accepted source-world systems.
