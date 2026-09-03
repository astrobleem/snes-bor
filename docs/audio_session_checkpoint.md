# Audio Session Checkpoint

## Current Identity

- Project: snes-bor
- Branch: `audio-content-pass`
- Agent: Luna
- Published HEAD: `3ae798724c3a4d0fd688d27a2c7a1e69612e0607`
- Parent semantic boundary: `06d4d866a0a9e990fe7da1878ed90aa8c37ebad7`
- Accepted Stage A: `c7c5f80f47bd1f9b7cab341bcc4732ec2968f4b0`
- Do not amend or rewrite published history.

## Accepted Architecture

- MSU1 provides soundtrack audio.
- Physical DSP voice 0 is reserved for specialized streamed long BRR SFX.
- Physical DSP voices 6/7 remain normal resident TAD SFX.
- Voice 1 and generalized sample residency are out of scope.
- TAD owns APUIO `$2140-$2143`; the streamer is a TAD-owned extension.
- DSP DIR is global and remains the normal TAD directory page.
- The streamer uses a reserved SRCN entry and does not switch DIR.

## Accepted Stage A

- FOOTDIE source is directory-derived and source-faithful: BRR SHA `6b7677dc2666ab4de95021ef88ff2ce43b2f30263ffee6ec2562a455745d3c7d`, 32733 bytes, 3637 blocks, 58192 decoded samples.
- Transport uses 72 mode-4 rows, APUIO1/2 payload, APUIO3 commit token, APUIO0 stable command, and `$57` submit marker.
- Stage A evidence: 228/228 chunks, 28 physical wraps, first post-wrap block 128, final block 3636/header `$01`, voice 0 168852 samples / 5.276625 seconds, no KOFF, natural ENDX.
- Resident coexistence passed with voice 7 G11: 12049 samples / 0.37653125 seconds and accepted per-voice PCM oracle.
- Do not reopen transport, protocol, ring, throughput, voice-0 firewall, or coexistence without new regression evidence.

## Shared Armory

- TAD fork: `astrobleem/terrific-audio-driver`
- Branch: `bor-poppy-stage-a-v0.3.0`
- Upstream base: `00215a2e9aaf327d620120a48b47d74f80d5b521`
- Stage-A lineage: `2aae713e68c2a2b5962c643eb9631f630a00eadd`
- Poppy API: `audio-driver/poppy-api/tad-stream.pasm`
- Poppy API commit: `97d2a189150d8c1a16930a9e55ec35a1c5e4cf4b`
- Frameexact tool: `E:\gh\Mesen2-mcp-frameexact`, branch `debug/bor-frameexact`, commit `18c05d3f076728d05310c6e591b7d0a08d604d42`.
- Protected `E:\gh\Mesen2-mcp-server` remains untouched.

## Build Provenance

- Authoritative graph is patched TAD source -> patched compiler -> fresh export -> `audio-data.bin` -> `src/main.pasm` -> ROM.
- Stage-A driver: 3437 bytes, SHA `a0d4a0b37dbd41ec85c6afbaabc2ebc9744822a9be5eb1115f5864ee7db39730`.
- Current generated audio blob remains the FALL resident-content artifact; current ROM after the semantic hook rebuild is SHA `1282a768254197a2d37c992b95360622e82478052ce0fe3398f78b20bb701a82`.
- `rebuild.py --check` was previously PASS; current fresh assembly and bank-0 guard PASS. Re-run final focused build checks after the semantic correction is stable.
- Bank-0 contract: reset `$FC00`, NMI `$FFA0`, IRQ `$FFB0`, runtime end below NMI.

## FALL Source Provenance

- Correct source: `Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak`, entry `DATA\\SOUNDS\\FALL.WAV`.
- PAK SHA `f9ab7a086263f9e9e5d439388b2f69c85b4f054b1663e4f3f2b81dc6a951e182`.
- Raw SHA `b55008537a246b99b1a20f3f5056012f292997fb6dec083398fd394539ca89ef`.
- Canonical WAV SHA `4a71174b6f9905fe6f9441b5f46c8429da0da2b75ae883b2933e5ae6d62f8f91`.
- Mono unsigned 8-bit PCM, 22050 Hz, 11466 authored frames, about 0.52 seconds.
- Resident export: 6453 BRR bytes, 717 blocks, 11472 decoded samples after BRR padding. Authored source is unchanged.

## FALL Review Correction

- Published `3ae7987` FALL acceptance is revoked for both semantic and physical playback claims.
- The initial `ApplyDamage -> AudioSemantic_EmitFall` edge is not source-faithful. Pinned OpenBOR revision `bcec7cb765eebec555c74aac64a23aa73f1cfe21` has one FALL play call in the ground-impact branch after `tobounce(self) && self->modeldata.bounce`; the relevant source is `engine/openbor.c` and `engine/openbor.h`.
- `tobounce` requires a qualifying downward ground impact and bounce-enabled model. Relevant TMNT player/enemy models inherit bounce enabled by default; no explicit TMNT override was found in the audited character data.
- The prior gameplay capture was exactly the accepted G11 hit waveform: capture SHA `6d1bffacfe7c893f8e645404a9bce8ecc0a1b59b0e6e656cb88910b635c2e00`, 12049 samples. It is rejected FALL evidence.
- Existing SNES `Character_Throw_Play__ordinary_land` is a documented adaptation of the source bounce-impact event; the simplified SNES throw model does not implement every OpenBOR `tobounce` predicate. Safe UP+A landing intentionally bypasses it.
- Current uncommitted source correction removes damage-edge emission and emits FALL on ordinary thrown landing, deriving the entity offset from the active DP window.

## Current Direct FALL Golden

- `tools/verify/capture_fall_voice7.py` now uses a fresh direct resident fixture: it queues normal TAD local ID 1 (`sfx_fall`) through `Tad_Process`, without gameplay or fake APUIO submission.
- Current direct capture: ROM `1282a768254197a2d37c992b95360622e82478052ce0fe3398f78b20bb701a82`; capture SHA `1d082f16ce3123b711041fcc6ff96406071bca9c00ce1fd8081daef592a9958d`; physical voice 7; queued local ID 1; capture telemetry reports KON/ENDX 12049 and a distinct artifact from G11.
- This is backend/content evidence only. Final FALL acceptance still requires a clean gameplay capture correlated to this golden and distinct from G11.
- The capture wrapper removes raw, sidecar, report, and arm artifacts before each run and records ROM/session/effect identity.

## Semantic and Validator State

- `tools/rom_audit/check_sfx_id_sync.py` now checks both `SFX_HIT_ID -> sfx_hit` and `SFX_FALL_ID -> sfx_fall`, rejects missing entries and duplicate generated IDs. Current result: PASS.
- The old damage-transition semantic fixture is no longer valid. The updated `--fall-only` fixture drives a thrown entity into ordinary landing and passes with one request at frame 241 for actor slot 1/roster 5.
- Queue ordering previously explains the false positive: FALL ID 1 can be enqueued, then normal HIT ID 0 arrives and lower-ID priority consumes HIT. This must be traced, not inferred from a voice capture.

## FALL SPC Command Boundary

- The matched current-ROM host trace reaches the gameplay FALL queue and submits the valid TAD play-SFX command `APUIO0=$06`, `APUIO1=$01`, `APUIO2=$40`.
- Direct local-ID-1 FALL control reaches the SPC resident play-SFX path with `Y=$01`, installs the FALL channel state, and produces the distinct FALL golden.
- Gameplay FALL currently diverges before SPC command dispatch: the SPC poll observes `A=$E7` and SPC `previousCommand=$E7`, remains in the command polling loop, and produces no new resident KON. The captured `$E7` is a freshness-bearing play-SFX command for local ID 0, not the stream command.
- Current classification: host enqueue and host command submission PASS; gameplay SPC recognition/ACK and all downstream allocator/DSP stages NOT PROVEN. No TAD/content change is authorized until the source of the intervening `$E7` and the exact command-port ordering are proven.
- Boundary trace: immediately after semantic FALL, host previous command was `$E7`, host queue was `ID=$01/pan=$40`, and SPC APUIO/previous command were `$E7`. After one service frame, host previous command and SPC APUIO/previous command were `$06`, the host queue was cleared, but the bounded SPC trace still contained no resident-handler body and no resident KON. This proves the exact command-fence transition; it does not yet prove dispatcher ACK or handler entry.
- Shared Armory audit: `E:\gh\Mesen2` and `E:\gh\Mesen2-mcp-frameexact` provide generic SPC-qualified execution hooks, SPC trace logging, SPC state/memory reads, and CPU selection; current diagnostic capture uses `E:\gh\Mesen2-mcp-voice7` (`debug/bor-voice7`, `ed2e70e9473bff453072fd090964118fbec3b819`). The protected `E:\gh\Mesen2-mcp-server` checkout remains read-only. No shared tool was changed or pushed.

## Protected State

- `tools/audio/sfx_production_banks.json` is pre-existing, user-owned dirty state. It is untouched, unstaged, and excluded from commits.
- Untracked TAD reproduction directories are intentionally retained and must not be cleaned.
- No G12, full regression, voice 1, generalized heap, authored-audio modification, merge, or history rewrite.

## SPC Observability Sharpening

The reusable execution-hook fix is pushed to `astrobleem/Mesen2`, branch
`debug/spc-command-trace`, commit `9ae1fb2b1db4fe2a9df42737eab95077757e7728`.
The Nexen derivative is `debug/spc-command-trace-nexen`, commit
`d84c6fc617b167950e3a64ba2ae47b7e71a9e6bb`, pushed to the same fork.  It
preserves the processor-qualified instruction PC before SPC dispatch.  The
clean derivative was built with VS18 at
`C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe`
and is consumed by the fixture from
`E:\gh\Mesen2-spc-command-trace-nexen\bin\win-x64\Release`.
The consumed `NexenCore.dll` SHA-256 is
`62f924452f0c0a114bbf3f1e588ca8040b4b1e3cd989418776d71477660757bd`.

The corrected matched run proves host `$E7 -> $06`, SPC previous-command
`$E7 -> $06`, and command-handler entry at SPC `$08C1` for gameplay.  Both
direct FALL and gameplay reach SPC `$098F`, the resident channel-setup path.
At handler entry gameplay has `nSoundEffects=$02` and `activeSoundEffects=$80`,
so the legal allocation is resident voice 6 while voice 7 is occupied; direct
control has `activeSoundEffects=$C0`.  This corrects the prior voice-7-only
false negative and rules out the earlier freshness hypothesis.

`get_cpu_state('Spc')` is unsupported by this MCP build and resets the session;
the fixture therefore uses CPU-qualified execution notifications, SPC trace,
ARAM, and port snapshots.  The current diagnostic capture still reports zero
bytes after the exact handler/channel hooks, so gameplay FALL physical PCM,
DSP KON, bytecode progression, and ACK are not accepted yet.  No TAD/content
change is authorized.

The bounded post-setup tick probe reaches `$098F` for gameplay with voice 6
selected. The first sampled DSP key-on mask contains `$40`, but voice 6 shows
`SRCN=128` only at the first sampled tick and `SRCN=0` on the next two; the
capture remains empty. This is not sufficient to identify a FALL KON and is
the current bytecode/DSP observation red state, not an accepted playback
result.

## Resume Here

- Current first unproven gate: resident channel setup `$098F` -> SFX bytecode -> DSP KON for gameplay FALL, with physical voice 6 selected.
- Next test: trace the generic SFX bytecode entry/set-instrument/play-note path after `$098F`, using voice 6, and distinguish the transient `$40` DSP mask from FALL SRCN before accepting PCM. The current paused diagnostic reaches `$098F` but reports no post-hook capture; this is not yet a physical PASS or a proven bytecode failure.
- Keep the direct ID-1 FALL golden as the non-perturbation control. Do not modify TAD, FALL content, freshness rules, queue priority, or Stage A transport until this first command-plane divergence is resolved.
### 2026-09-03 FALL two-tick diagnostic update

The accepted FALL causal chain remains valid through resident channel setup:
the current ROM reaches SPC command $06 with ID $01/$40, accepts two resident
effects, selects physical voice 6 when voice 7 is occupied, and returns from
the setup body at current-build SPC $0A2E.  The shared SPC execution hook is
the pushed generic Mesen/Nexen implementation recorded below; no TAD or FALL
audio source was changed.

The post-setup diagnostic is currently red at the timer boundary.  A
CPU-qualified SPC execution range covering 20 exact frames after setup shows
setup/teardown PCs only ($098D-$0A2E and $0BBA-$0BDA); no SFX bytecode entry,
set-instrument, or play-note execution occurs.  SPC main-loop execution
repeatedly takes the T1OUT-zero branch at $03DD-$03E3.  The sampled SPC I/O
state has CONTROL $F1 = $00 and T1OUT $FE = $00.  This result is identical for
direct local-ID-1 and gameplay probes.  A fixture-only queued UNPAUSE command
is proven to enter current-build $087D (MOV $F1,#$03), but the subsequent
resident probe still has no SFX tick; queued PAUSE_MUSIC_PLAY_SFX was also
tested and did not produce a bytecode tick.  These are diagnostic lifecycle
findings, not evidence against TAD, FALL content, or Stage A.

The transient gameplay DSP observation (KON including $40 and SRCN $80 before
later $00) remains unclassified because it is not aligned to set-instrument,
play-note, or the following process_sfx_channels tick.  No physical gameplay
FALL PCM or ENDX has been accepted.  The current diagnostic script retains
bounded SPC execution, timer, and disassembly instrumentation only.  The
known protected `tools/audio/sfx_production_banks.json` modification remains
pre-existing/user-owned dirty state and has not been touched or staged.

## Resume Here

Repair or replace the FALL fixture's audio-playing lifecycle using an existing
proven gameplay-start/session path, then rerun matched direct-ID-1 and
gameplay probes.  The first required physical gate is a real TIMER_1 SFX tick
after $098F/$0A2E, followed by FALL bytecode, voice-6 keyOnShadow $40, the
following DSP KON $40, and physical FALL PCM.  Do not modify TAD or FALL audio
content until that boundary is observed.
## TIMER_1 / Session Lifecycle

Current BOR HEAD is `3ae798724c3a4d0fd688d27a2c7a1e69612e0607`; origin matches.
Current `distribution/bor.sfc` SHA-256 is
`1282a768254197a2d37c992b95360622e82478052ce0fe3398f78b20bb701a82`.

The standard launcher is `E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe`,
SHA-256 `66fc84e03481dedc521b095d0aa3022297f09e48ddcc3b8beabd019f96c0b268`,
through `_harness.open_session()` and an ephemeral port.  The accepted SPC
hook Nexen binary remains
`E:\gh\Mesen2-spc-command-trace-nexen\bin\win-x64\Release\NexenCore.dll`,
SHA-256 `62f924452f0c0a114bbf3f1e588ca8040b4b1e3cd989418776d71477660757bd`.

Session matrix using current ROM:

| launcher / fixture | setup | repeated `$03E5` SFX processing |
| --- | --- | --- |
| standard Mesen / idle | n/a | YES, 125 entries / 60 frames |
| standard Mesen / direct ID 1 | YES, 6 `$098F` entries | YES, 125 entries / 60 frames |
| standard Mesen / gameplay FALL | semantic delta 1; handler window missed | YES, 334 entries / 60 frames |
| custom Nexen / idle | n/a | YES, 41 entries / 20 frames |
| custom Nexen / direct ID 1 | setup reached | NO after setup |
| custom Nexen / gameplay FALL | setup reached in prior trace | NO after setup |

The standard direct probe reaches setup and later reports voice 6 `SRCN=1`,
but the standard Mesen binary has no matching passive voice-capture artifact;
the empty capture is not a physical FALL verdict.  The custom Nexen direct
probe reaches setup but no later SFX bytecode/timer branch.  This is now
classified as a session/launcher differential, not a FALL-content or TAD
allocator failure.

The generated main-loop disassembly identifies `$0391` as `MOV $F1,#$00` and
`$087D` as the current UNPAUSE handler `MOV $F1,#$03`.  The accepted custom
probe observed the latter handler.  `$FB` readback returned zero in both
launchers and is treated as unresolved debugger I/O identity, not as proof of
the timer target; no destructive `$FE` polling is used in the timer probe.

Known shared-tool debt remains: `get_cpu_state('Spc')` resets MCP and
directional SPC write hooks emit no events.  The generic SPC execution hook
used here is the accepted Mesen commit
`9ae1fb2b1db4fe2a9df42737eab95077757e7728` and Nexen derivative
`d84c6fc617b167950e3a64ba2ae47b7e71a9e6bb`; no new shared change was made.
The protected production-bank file remains untouched, unstaged,
pre-existing/user-owned dirty state.

## Resume Here

Use the standard Mesen session for timer/bytecode causal tracing and audit the
custom Nexen launch/runtime difference before changing shared tooling.  The
first required FALL gate remains a real post-setup `$03E5` SFX tick, followed
by `set_instrument`, `play_note`, deferred voice-6 KON, and physical FALL PCM.
Do not modify TAD or FALL audio content until that differential is resolved.

## Standard Mesen Voice Capture Port

- Shared armory audit: existing generic per-voice capture was found as an uncommitted four-file implementation in `E:\gh\Mesen2-mcp-voice7`, branch `debug/bor-voice7`, HEAD `ed2e70e9473bff453072fd090964118fbec3b819`. It uses `MESEN_VOICE_CAPTURE_PATH`, `MESEN_VOICE_CAPTURE_VOICE`, and `MESEN_VOICE_CAPTURE_ARM_FILE` and observes physical DSP voice output plus KON/KOFF/ENDX.
- Ported to `astrobleem/Mesen2`, branch `debug/spc-command-trace-voice-capture`, based on standard head `18c05d3f076728d05310c6e591b7d0a08d604d42`.
- Shared commits: `642fa81ff0426500e0c104b46625dd02b92b530e` (passive capture port), `f7715e7646829d88e8a8162984cd396ce72f6d1a` (lazy initialization and process-environment fallback). Both pushed to `fork/debug/spc-command-trace-voice-capture`.
- Native build: `E:\gh\Mesen2\bin\win-x64\Release\MesenCore.dll`, SHA-256 `09f8fe2c08e6e3ba1b5c53fbdec4084cfe3edf91316ff7b46e4fa6d4beFB03DD`.
- Full solution remains blocked by the existing UI SDK environment: `Microsoft.NET.Sdk` is unavailable under the installed VS18 MSBuild. Native Core and InteropDLL build successfully.
- The exact standard Mesen process loads the intended `MesenCore.dll`, but direct and gameplay BOR capture runs create no raw or sidecar file, including absolute capture paths. Therefore standard-Mesen physical capture is not yet proven active; zero-byte results are not FALL evidence.

## Timer / Session Matrix Update

- BOR HEAD remains `3ae798724c3a4d0fd688d27a2c7a1e69612e0607`; origin is unchanged.
- ROM SHA-256 remains `1282a768254197a2d37c992b95360622e82478052ce0fe3398f78b20bb701a82`.
- Standard Mesen through `_harness.open_session()` with the rebuilt native DLL: idle `$03E5` repeated 125 times in 60 frames; direct ID 1 setup reached and `$03E5` remained 125 times; gameplay FALL semantic delta 1, setup reached, `$03E5` remained live (observed 334 times in 60 frames).
- Nexen remains excluded from the FALL physical platform: idle processing exists, but post-resident-setup `$03E5` disappears. Its deep emulator-lineage divergence is shared-tool debt, not a BOR/TAD audio finding.
- `$FB` debugger read remains unresolved and is not used as timer proof. `$FE` polling remains excluded from liveness evidence.
- The generic SPC execution-hook commits remain Mesen `9ae1fb2b1db4fe2a9df42737eab95077757e7728` and Nexen derivative `d84c6fc617b167950e3a64ba2ae47b7e71a9e6bb`.

## Resume Here

Run one minimal standard-Mesen MCP session with the pushed `debug/spc-command-trace-voice-capture` native DLL and establish why `Dsp::InitVoiceCapture` does not create its configured file. Prove environment visibility or the first DSP lifecycle boundary, then rerun direct ID 1 before gameplay FALL. Do not change BOR/TAD audio implementation.

## FALL Capture Launcher Update (2026-09-03)

BOR identity remains:
- HEAD: `3ae798724c3a4d0fd688d27a2c7a1e69612e0607`
- `origin/audio-content-pass`: `3ae798724c3a4d0fd688d27a2c7a1e69612e0607`
- ROM SHA-256: `1282a768254197a2d37c992b95360622e82478052ce0fe3398f78b20bb701a82`
- FALL corrective BOR work remains preserved and uncommitted.
- `tools/audio/sfx_production_banks.json` remains pre-existing dirty state and was not staged or intentionally changed.

The standard-Mesen capture launcher now passes explicit child environment overrides through `McpSession(env=...)`; the parent `os.environ` is not mutated. BOR forwards absolute capture, voice, and arm paths through `_harness.open_session(..., env=..., stderr_log=...)`. Shared regression coverage passed for explicit overrides, multiple variables, parent-environment preservation, and compatible construction.

Shared Mesen capture lineage:
- Repository: `astrobleem/Mesen2`
- Branch: `debug/spc-command-trace-voice-capture`
- Published commits: `642fa81ff0426500e0c104b46625dd02b92b530e`, `f7715e7646829d88e8a8162984cd396ce72f6d1a`, `5fb1f1b6cba1b9348b40ff2d03ae6e4afde16f63`
- New shared child-environment commit: `5fb1f1b6cba1b9348b40ff2d03ae6e4afde16f63`, pushed to `fork/debug/spc-command-trace-voice-capture`.
- Last verified runtime DLL used by the smoke run: `E:\gh\Mesen2\bin\win-x64\Release\MesenCore.dll`, SHA-256 `390d0a5c3ead0268cfbf022f2ca382cc0527c3ade5bf4511b8027b8f678c2b32`. The matching `Dependencies\MesenCore.dll` copy was synchronized for that run.
- Native Core/InteropDLL rebuild succeeded; full managed/UI build remains limited by unavailable `Microsoft.NET.Sdk` in the VS18 UI environment.

Capture initialization result:
- Explicit child environment contract: implemented and unit-tested.
- Smoke launch: child Mesen process started from `E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe`.
- Capture path/voice/arm values were passed before spawn.
- No raw capture file, metadata sidecar, or trace file was created; only the arm/report/stderr artifacts exist.
- No `[voice-capture]` initialization diagnostic was observed in captured Mesen stderr, despite the verified native DLL containing the capture implementation. A live module probe confirmed `Mesen.exe` loads the executable-directory `MesenCore.dll`; the runtime still does not expose the expected constructor/init diagnostic.
- This is a standard-Mesen native capture initialization/observability blocker, before arming, KON, PCM, or ENDX. It is not evidence against FALL content, semantics, TAD command $06, allocator, or the two-tick SFX pipeline.

Prior accepted timer differential remains unchanged:
- Standard Mesen: idle `$03e5` 125/60 frames; direct ID1 and gameplay FALL retain post-setup SFX processing.
- Nexen: post-setup SFX processing disappears; Nexen is excluded from the FALL physical platform and remains shared-tool debt.
- The standard Mesen line is authoritative for the remaining physical gate.

TAD lineage remains:
- `astrobleem/terrific-audio-driver`, branch `bor-poppy-stage-a-v0.3.0`, head `97d2a189150d8c1a16930a9e55ec35a1c5e4cf4b`.
- Upstream base `00215a2e9aaf327d620120a48b47d74f80d5b521`; Stage-A lineage `2aae713e68c2a2b5962c643eb9631f630a00eadd`.
- No TAD change is justified by this capture-initialization failure.

## Resume Here

First executable action: identify why the standard Mesen process does not execute or expose `SNES::Spc/Dsp` capture initialization despite loading the verified DLL; resolve that generic runtime/module boundary, then rerun the initialization smoke before any FALL tick/KON/PCM claim.

## FALL Physical Gate Result (2026-09-03)

Packaged-runtime provenance is now proven:
- Stale managed package: `Mesen.dll` embedded `MesenCore.dll` SHA `340dec4ff581012d8fa4f9a199dc397f84d2a17581e65b4a4902b46d935b520a`.
- Source-built core from shared Mesen commit `5fb1f1b6cba1b9348b40ff2d03ae6e4afde16f63`: SHA `4491627aae1ecdb746605e1391725321bdcde9d92abd050f6212850741fabcb8`.
- .NET SDK: `8.0.100`; managed package built with `OptimizeUi=true`.
- Isolated runtime: `E:\gh\Mesen2-runtime\voice-capture-5fb1f1b` with portable `settings.json`.
- Generated embedded resource core and post-extraction runtime core both match the source-built core.
- Capture initialization succeeded before any request; raw, JSON, and trace files were created.

Direct FALL golden:
- Local ID: `1`; physical voice: `6`.
- Capture format: physical voice PCM, signed 16-bit stereo, 32000 Hz.
- KON sample: `0`; KOFF sample: `16617`; natural ENDX sample: `16618`.
- Samples: `16618` frames, `66472` bytes.
- PCM SHA-256: `9fe5b4f16ff1cf35e04494d72478cefd5a10d0056724ae5564af8e1e0ed96434`.

Gameplay FALL:
- Ordinary thrown-landing adaptation; semantic delta exactly `1`; local ID `1`.
- Fresh allocator selected physical voice `7` in this run; the earlier voice-6-only negative was invalid preselection.
- KON sample: `0`; KOFF sample: `16617`; natural ENDX sample: `16618`.
- Samples: `16618` frames, `66472` bytes.
- PCM SHA-256: `9fe5b4f16ff1cf35e04494d72478cefd5a10d0056724ae5564af8e1e0ed96434`.
- Direct and gameplay PCM are byte-identical and therefore match the FALL golden. The gameplay capture is not the accepted G11 HIT waveform.

Focused canaries:
- TAD rebuild/check: PASS.
- TAD baseline: PASS.
- Voice-0 reservation and live ownership: PASS.
- HIT/FALL ID sync: PASS.
- Audio manifest, shipped content, runtime state, assembly/layout guards: PASS.
- G11 lifecycle/content checks execute successfully, but the historical waveform analyzer still fails its duration/correlation checks; this remains separately reported G11 oracle debt and is not used as FALL evidence.
- Semantic-lifetime evidence reports stale manifest state; protected production-bank state was not staged or changed by this correction.

FALL physical acceptance: PASS.
Nexen post-setup timer divergence remains documented shared-tool debt; standard packaged Mesen is the authoritative physical platform.

## Resume Here

STOP FOR INDEPENDENT REVIEW. Do not begin another SFX slice, G12, generalized residency, or Stage-A regression.

## Final FALL Bookkeeping (authoritative, 2026-09-03)

Historical diagnostic sections above are superseded by the accepted packaged-runtime result below. They remain retained as failure and provenance evidence.

Published HEAD:
    `60c21f5c3024726b241a88665927ecc84f767e4a`

FALL metadata:
- Before: `audio_implemented = False`.
- After: `audio_implemented = True`.
- `mechanic_reachable = True`.
- `event = ordinary-thrown-landing`.
- Wording remains explicit that this is a documented SNES adaptation of OpenBOR's qualifying bounce-impact event, not a literal reproduction of every OpenBOR predicate.

FALL physical gate:
    PASS

direct/gameplay PCM:
    byte-identical

accepted implementation:
    `60c21f5c3024726b241a88665927ecc84f767e4a`

next action:
    independent review complete / ready for next audited audio slice

No FALL source, hook, resident ID, allocator, TAD, capture, Stage-A, voice-policy, or gameplay-proof work was reopened by this bookkeeping change.

## Resume Here

Independent review complete. Begin the next audited audio slice only after review authorization.
## JUMP Audio Slice

This section records the completed JUMP slice and supersedes the earlier
JUMP-in-progress notes.

- Starting BOR HEAD: b524640c5c762e6a704ecf40ef9ada8a894c4c0f
- Final ROM SHA-256: c8586733d35ae46817c80b894635964e2b864ced3fda0eb4a614e8281818ba9d
- OpenBOR source: engine/openbor.c dojump(); global_sample_list.jump is played once at jump initiation before jump state initialization.
- Source PAK: TMNT pack, SHA f9ab7a086263f9e9e5d439388b2f69c85b4f054b1663e4f3f2b81dc6a951e182
- Source asset: DATA\\SOUNDS\\JUMP.WAV, SHA 0f9ffe9cfed79c7cc5af789b1ba2407f238d325918149a702bb294171e41faf9, 11025 Hz mono unsigned 8-bit, 5941 frames.
- Canonical resident sample: soundwork/tad/project/samples/jump.wav, SHA d56fa9c2803e72f2d5823b93465cba4f397843ccbb8acb920a3043c92ff025e0, 5952 frames.
- Backend: resident TAD SFX; BRR size 3348 bytes, 209 blocks.
- Generated IDs: HIT 0, FALL 1, JUMP 2. Semantic ID: AUDIO_SEMANTIC_JUMP $08.
- SNES hook: grounded player A-trigger accepted by Jump_PlayerTick; airborne/held-A and no-jump-data paths do not request JUMP.
- Semantic fixture: first ground jump delta 1; held airborne duplicate delta 0; no-jump-data delta 0; second distinct ground jump delta 1.
- Direct JUMP golden: physical voice 6, local ID 2, 17204 frames, 32000 Hz stereo signed 16-bit raw capture, KON 0, KOFF 17203, ENDX 17204, SHA 6b2c1b7e965d3267423230abde6db539a811eae388f24a02e2ad6922de76ba36.
- Gameplay JUMP: semantic delta 1; physical voice 7; KON 72294 and ENDX 89498 in the full capture; the exact 17204-frame KON-to-ENDX interval SHA 8580df11db281465cc72b8fa53b2d1cf80366de2ae8903cbcb8192b2ede2b331; aligned channel correlation 0.9999999962 against the direct golden.
- The gameplay capture's leading 72294 frames are pre-event voice output and are excluded by the KON-to-ENDX boundary. The resulting JUMP PCM is distinct from the accepted FALL and G11 HIT controls.
- Shared Mesen runtime: astrobleem/Mesen2, debug/spc-command-trace-voice-capture, 5fb1f1b6cba1b9348b40ff2d03ae6e4afde16f63. No shared change was required.
- TAD fork: astrobleem/terrific-audio-driver, bor-poppy-stage-a-v0.3.0, 97d2a189150d8c1a16930a9e55ec35a1c5e4cf4b.
- Focused checks: TAD rebuild/check PASS; HIT/FALL/JUMP ID sync PASS; audio manifest PASS; shipped content PASS; layout guard PASS; TAD baseline PASS; voice-0 static reservation PASS; voice-0 live ownership PASS. The direct G11 command requires its explicit ROM-hash argument and did not yield a usable result in the combined invocation; no G11 result is claimed here.
- FALL physical gate remains PASS and is not reopened.

JUMP physical gate: PASS
Direct/gameplay PCM: matched after exact KON-to-ENDX normalization
Accepted next implementation: audio: add jump sfx

## Resume Here

Independent review of the JUMP slice after its single corrective commit.
