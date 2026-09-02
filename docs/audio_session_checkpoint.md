# SNES BOR Audio Content Pass Checkpoint

## Resume Here

- Branch: `audio-content-pass`.
- Work is uncommitted and must be preserved.
- Current blocker: transport-only transaction 0 is not reaching a verified end-to-end completion.
- Exact next test: trace one command from CPU APUIO writes through TAD dispatch and payload-complete ACK.
- Do not start DSP playback, ring timing, consumer distance, or the 228-chunk burn-in yet.
- Current driver evidence: latest fresh export is 3411 bytes, SHA prefix `e99d5b3a`.
- Current audio blob evidence: SHA prefix `a815d27e`.
- Current ROM evidence: source-built ROM SHA prefix `c2541246`.
- Protected dirty file: `tools/audio/sfx_production_banks.json`; leave untouched and unstaged.
- Protected repository: `E:/gh/Mesen2-mcp-server`; do not touch.
- Scope exclusions: no merge, G12, full regression, voice 1, generalized heap, resampling, truncation, or substituted authored audio.

## Historical Accepted Commits

- `2db671b6532b2df941a55211ebc64c24103e8118`: semantic diesound path.
- `6ecbddacc663c4a2bc03dd29208ce35f1e3ba163`: corrected TAD voice-0 reservation and final hardware-write firewall.
- `aff4cae0124c5c77c4efd9fd338e2dc43265debd`: earlier reservation patch with defects; superseded, not to be rewritten.

## Architecture

- MSU-1 is reserved for soundtrack use.
- Physical DSP voice 0 is reserved for one specialized streamed long-BRR SFX.
- Physical DSP voices 6 and 7 remain normal TAD resident short-SFX voices.
- Voice 1 is not implemented and is a future candidate only.
- TAD owns APUIO `$2140-$2143`; streaming is a TAD-owned protocol extension.
- DSP DIR is global and must never be switched to a separate stream directory.
- The streamer uses a stable reserved SRCN entry in the normal TAD directory page.
- The design remains coarse residency plus one dedicated long stream.
- No generalized dynamic BRR/sample heap is part of this pass.

## FOOTDIE Source Facts

- Authored source: `FOOTDIE.WAV` production identity.
- Production BRR size: 32733 bytes.
- BRR block count: 3637 complete 9-byte blocks.
- Expected duration: approximately 5.278 seconds.
- Full transport chunks: 227 chunks of 144 bytes, totaling 32688 source bytes.
- Final source chunk: 45 genuine bytes.
- Fixed-size staging padding, if retained: 99 bytes; padding is not source audio.
- Physical ring: 8 slots, 144 bytes per slot, 1152 bytes total.
- Each slot contains 16 BRR blocks and 256 decoded PCM samples.
- One complete physical ring traversal represents 2048 decoded source samples.

## G11 Resident-SFX Oracle

- G11 resident runtime is closed as a runtime issue.
- Clean passive voice-7 capture on known-good `6ecbdd` produced 12049 PCM samples.
- Known-good duration at the capture rate: 0.37653125 seconds.
- Current stream-scaffold build produced identical voice-7 PCM bytes and timing.
- Direct good-versus-current PCM correlation: 1.0.
- The old mixed-output results 0.058, 0.110, and 0.119 seconds were contaminated analyzer/session results.
- Authoritative G11 evidence is one real request, physical voice selection, KON-to-ENDX lifetime, and passive per-voice PCM.
- Amplitude-threshold active-island segmentation is secondary and cannot define completion.

## Build Graph

- Required graph: pinned TAD source -> BOR source patch -> patched compiler -> fresh ca65 export -> generated audio artifacts -> ROM.
- Pinned upstream TAD commit: `00215a2e9aaf327d620120a48b47d74f80d5b521`.
- Compiler version text is not sufficient identity because stock and patched builds both report 0.3.0.
- Stock compiler use is forbidden for this stream branch.
- Manual restoration of `src/main.bin` or `audio-data.bin` is forbidden.
- Latest patched compiler was rebuilt from source and selected explicitly.
- `soundwork/tad/rebuild.py --check` passed for the latest generated export.
- Latest driver: 3411 bytes, SHA prefix `e99d5b3a`.
- Latest audio blob: SHA prefix `a815d27e`.
- Latest ROM rebuilt from `src/main.pasm`: SHA prefix `c2541246`.
- `build/bor.sfc` and `distribution/bor.sfc` were packaged byte-identically for that build.

## Important Protocol Fix

- Earlier APUIO3 markers `$D9` and `$D7` collided with TAD loader-switch bit semantics.
- Submit marker is now unified to `$57`, with the loader-switch bit clear.
- The post-command loader-switch check excludes the stream receive command because payload APUIO3 bytes are arbitrary.
- The marker fix is source-level and must continue through the patched compiler/export graph.

## Memory and Transport Layout

- COMMON_DATA_ADDR is relocated to `$17E4`.
- TAD stream ring is reserved below common data at `$121A-$169A`.
- Ring geometry is 8 x 144 bytes.
- Host HDMA staging table is WRAM `$7E3C00`.
- Current selected HDMA channel is channel 0.
- Channel 7 remains reserved by existing NMI use.
- The intended current contract is donor-style mode 4: one submit row followed by 36 payload rows, four APUIO bytes per payload row.
- Payload size is therefore 36 x 4 = 144 bytes.
- APUIO0..APUIO3 carry four payload bytes on each payload row.
- The submit row uses APUIO3 `$57` as the receive-start marker.
- The receiver reads APUIO0..APUIO3 for 36 iterations and stores 144 bytes.
- The receiver uses the supplied destination pointer and no playback is allowed in transport-only mode.

## Stage A Status

- Stage A is not proven.
- Previous host-reported chunk counts were rejected because they did not prove SPC acceptance or correct ARAM contents.
- A previous playback run stopped near 2017 voice-0 samples, consistent with one physical ring traversal, but DSP diagnosis is deferred until transport is correct.
- Current serial harness after the marker fix shows no valid transaction 0: state remains idle, no ACK is observed, and no ARAM write is verified.
- A forced-threshold diagnostic with stream enable, active flag, serial permit, and budget 143 still leaves budget/state/table unchanged across frames.
- Therefore the first currently observed failure is producer-service invocation or its runtime gating, before HDMA table execution and before SPC payload receive.
- Host counters are not trusted as delivery evidence.
- The current acceptance oracle is CPU port traffic, SPC command/state transition, payload-complete ACK, and exact external ARAM bytes.

## Required Transaction-0 Gate

- No KON voice 0.
- No DSP consumer or safe-refill scheduling analysis.
- No 16-transaction or 228-transaction burn-in.
- Trace CPU writes to `$2140-$2143` with PC and timing.
- Trace SPC observations of APUIO0..APUIO3.
- Prove the TAD dispatcher sees a fresh command and enters the stream handler exactly once.
- Prove handler state leaves idle and reaches receive state.
- Distinguish command-accepted ACK from payload-complete ACK.
- Prove 144 bytes are received and stored to slot 0.
- Require exact slot-0 ARAM equality with FOOTDIE source bytes 0..143.
- Record first mismatch boundary if any.

## Test Process Rules

- Use only the clean diagnostic Mesen/Nexen worktree `E:/gh/Mesen2-mcp-voice7`.
- Use `C:/Users/chad/.dotnet/dotnet.exe` with the existing clean Nexen launcher.
- Do not use `--help` or uncontrolled interactive launches as evidence.
- Record and terminate the exact controlled process for each diagnostic.
- Keep passive voice capture tooling separate from production runtime behavior.
- Update this checkpoint when transaction 0, serial generations, playback, or full Stage A changes state.

## Protected Scope

- Do not modify `tools/audio/sfx_production_banks.json`.
- Do not modify `E:/gh/Mesen2-mcp-server`.
- Do not reset or rewrite history.
- Do not amend the accepted reservation commit.
- Do not commit or push until the coherent transport slice has real evidence.
