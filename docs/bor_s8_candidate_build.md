# Opt-in S8 Normal candidate builds

## Final persistent-SA-1 Normal candidate

Use the candidate wrapper for the complete selectable Normal runtime. It first
builds a compiler-owned source-sized Normal image, then overlays the persistent
SA-1 worker and leaves `distribution/bor.sfc` unchanged:

```powershell
py -3.10 -B tools/bor_compile/build_normal_sa1_candidate.py --output build/s8_normal_review_candidate
```

Choose a new output directory; the wrapper refuses to replace an existing
candidate. PCM companions remain hardlinked. The bounded campaign receipt
commands, candidate hashes, and acceptance limits are recorded in
`docs/bor_s8_normal.md`.

## Lower-level compiler source image

The explicit `--normal-candidate` build below creates only the compiler-owned
source image. It does not by itself install the persistent SA-1 runtime and is
not the final Normal candidate used by the campaign receipts.

From the repository root:

```powershell
python build_rom.py --normal-candidate
```

Only this explicit flag enables Normal in the generated availability table.
Hard and Bonus remain unavailable. Running `python build_rom.py` without the
flag regenerates Normal unavailable and uses the established production target.

After successful assembly and layout checks, candidate output is:

- `build/s8_candidate/bor.sfc`
- `build/s8_candidate/bor.msu`
- `build/s8_candidate/bor-N.pcm` companions, copied from hash-verified music
  catalog inputs so playback resolves beside the candidate ROM.

Candidate ROM/MSU publication does not write `distribution/bor.sfc`,
`distribution/bor.msu`, `build/bor.sfc`, or `build/bor.msu`. No artifacts are
deleted or moved. Shared compiler, stage, pack metadata, audio-generation,
`src/main.bin`, and symbol paths remain the existing paths. This is target
isolation, not a separate checkout or release approval. The existing audio
build may regenerate shared music PCM inputs under distribution.

## Diagnostic source-only relink

Only with an existing matched candidate MSU, generated includes, and music
catalog, a source-only change such as `Scene_Init` can be relinked without
regenerating audio/media. From the repository root, with the emulator closed:

```powershell
@'
from pathlib import Path
import build_rom
msu = Path("build/s8_candidate/bor.msu").read_bytes()
rom = build_rom.link_rom()
build_rom.write_build_outputs(rom, msu, normal_candidate=True)
'@ | python -
```

`link_rom()` assembles and runs all three existing layout validators, then
returns ROM bytes using the unchanged header/vector/checksum algorithm. Only
assembler intermediates (`src/main.bin`/`src/main.sym`) are refreshed; ROM/MSU
publication waits for `write_build_outputs()`, which retains music hash checks.
This diagnostic does not regenerate availability or certify media matching:
do not use it after media, catalog, packing-layout, or generated-input changes.
Default/distribution ROM/MSU outputs remain untouched.

Final reproducibility still requires the full command:

```powershell
python build_rom.py --normal-candidate
```

## Native harness

For a later explicitly authorized native harness run:

```powershell
$env:BOR_TEST_ROM = 'build/s8_candidate/bor.sfc'
python tools/verify/game_s8_normal_campaign.py --mode natural
# When finished with candidate testing:
Remove-Item Env:BOR_TEST_ROM
```

`_harness.rom_path()` resolves relative overrides from the repository root,
not the process working directory. Absolute user-named fixtures outside the
repository are also supported. Empty, missing, and directory overrides fail;
they never silently load distribution. With the variable unset, the default
remains repository `distribution/bor.sfc`.

Harness owner (Kuhn): hash `Path(rom_path(__file__))` and
`Path(rom_path(__file__)).with_suffix('.msu')`, not hard-coded distribution
paths. The S8 campaign harness's artifact-hash update is owned separately.
Generated campaign metadata and `src/main.sym` describe the most recent shared
build, so run native proof before another build replaces those inputs.

Focused validation only:

```powershell
python -m unittest tools.verify.test_s8_candidate_build tools.audio.test_s8_audio_gate -v
```

Before the relink extraction, 17 tests passed: opt-in/reset gating, protected target preservation, candidate
companions, corrupt-music rejection, no publication after assembly failure,
ROM environment overrides, audio source guards, and isolated death-selector
assembly. The three audio join labels `__slot_store`, `__check_identity`, and
`__source_ready` explicitly declare `.a8` / `.i16`. No full build or emulator
was run by this implementation pass.

After the relink extraction, all 8 candidate tests passed independently
(`python -m unittest tools.verify.test_s8_candidate_build -v`). The two new
tests compare every output byte against the previous algorithm for empty,
64 KiB, and 4 MiB synthetic assembly inputs, and check layout-failure/overflow
rejection without publication. Assembly is mocked; no main assembly, encoding,
full build, or emulator was run for this extraction.
