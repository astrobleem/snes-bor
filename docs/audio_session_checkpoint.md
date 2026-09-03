# SNES BOR Audio Content Pass Checkpoint

## Shared Armory

- Relevant shared tool worktree: `E:\\gh\\Mesen2-mcp-frameexact`.
- Remote/fork: `https://github.com/astrobleem/Mesen2.git`, `origin/master` at `18c05d3f076728d05310c6e591b7d0a08d604d42`.
- Reusable capability: exact frame-count `run_frames`, held/released input, deterministic pause and teardown.
- Liveness proof on this host: requests for 1, 1, and 10 frames returned exact advancement with `timedOut=false`.
- Passive DSP diagnostic edits remain only in the separate worktree. `E:\\gh\\Mesen2-mcp-server` was not modified.

## Resume Here

- Branch: `audio-content-pass`.
- Work after the published transport boundary is uncommitted and must be preserved.
- Published transport boundary: `d58b513`; provenance follow-up is published as `aeccf84`.
- Transaction 0 and serialized chunks 0..15 are exact and ACK-gated; bank-0 layout is resolved and guarded.
- Current next gate: controlled physical playback and ring-wrap proof. Full Stage A remains unproven.
- Playback remains unstarted after the corrected source extraction; Gate A must be rerun with the real BRR content.
- Current d58 reconstruction evidence: driver 3420 bytes, SHA `12b285126ee811aacb6012b2ded6df056accf252df19563377accd5d4b69e3aa`; blob SHA `ee3b47b3c0c50bfa5ddab1539198ed6b597c2d8255f95e6602cd2c6022f28235`.
- Current latest TAD source fix: transport-only prefill no longer claims voice 0; stream directory start and loop low bytes use `lobyte(STREAM_RING_ADDR)`.
- Current latest driver: 3437 bytes, SHA `b55edf38ed53b470789a9a9a6b43b1b13e8d408640c08ca1f3c17cf664da5ea6`; blob SHA `97a734107636d4aa99a993e91aa9d960bf9aa16c34fe31e46ec97a396a5382de`; corrected-content ROM SHA `113f1dff67f9cba1177da0fe39dec97dc701a06a7b600224a7026da50b1bd5d2`.
- Source provenance cleanup is published in `aeccf84`; the active post-d58 source delta remains represented by `tad-v0.3.0-stream-voice0-srcn.patch` and the patched compiler path.
- Revalidated after cleanup: transaction 0 exact ARAM PASS, serialized chunks 0..15 exact PASS, `rebuild.py --check` PASS, voice-0 reservation PASS, and authoritative G11 voice-7 PASS.
- The prior `footdie.brr` extraction used `common[19:...]`, which started inside TAD metadata. The generator now converts data-table segment offsets to blob offsets, reads the directory at Common Audio Data offset 28, and derives BRR start from its `$1815` ARAM pointer.
- Corrected FOOTDIE: Common Audio Data 32782 bytes; base `$17E4`; BRR offset 49; 32733 bytes; 3637 blocks; 58192 decoded samples; first header `$70`; final header `$01`; END count 1; LOOP count 0; decode/source correlation `0.9977658011`; BRR SHA `6b7677dc2666ab4de95021ef88ff2ce43b2f30263ffee6ec2562a455745d3c7d`.
- Corrected-content transport rerun: transaction 0 and serialized chunks 0..15 are exact with ACK-gated external ARAM verification; chunk-0 SHA is `317fa853814e0315096e2ca441d84ab55d8faa3296e0e231b87b609f18f431ae`.
- Current next gate: controlled physical playback and ring-wrap proof. Do not claim playback or full Stage A yet.
- Provenance: pinned upstream plus the voice-0 patch plus `tad-v0.3.0-stream-transport.patch` reproduces d58 exactly; `tad-v0.3.0-stream-voice0-srcn.patch` records the later V0SRCN diagnostic fix.
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
- Reproducible patch chain: upstream `00215a2e9aaf327d620120a48b47d74f80d5b521` + voice patch `a93560dad40a1853c4d3a832b4dd1f1a9c4fc527d95d5968847401edbf525417` + stream patch `4486e95f7a37d66e04c33b93642dd20db7bf9e0ec77744270556802afbc408f1`.
- Reconstructed source content matches the accepted sibling source after line-ending normalization; fresh export is byte-identical to the accepted driver/blob.
- `soundwork/tad/rebuild.py --check` passed for the latest generated export.
- Latest accepted driver: 3420 bytes, SHA `12b285126ee811aacb6012b2ded6df056accf252df19563377accd5d4b69e3aa`.
- Latest accepted audio blob: SHA `ee3b47b3c0c50bfa5ddab1539198ed6b597c2d8255f95e6602cd2c6022f28235`.
- Latest ROM rebuilt from `src/main.pasm`: SHA `9a2f47fb27b9e0bfa2bf632c28215cf404e70ba7a43209128946f28f0c66d240`.
- `build/bor.sfc` and `distribution/bor.sfc` were packaged byte-identically for that build.
- Generated `Tad_DataTable` is `$018E03`; baseline metadata now checks this against fresh generated symbols.
- Stream patch SHA: `4486e95f7a37d66e04c33b93642dd20db7bf9e0ec77744270556802afbc408f1`.

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
- The accepted current contract is mode 4: one submit row followed by 72 payload rows.
- APUIO0 carries the exact freshness-bearing stream command for the transaction.
- APUIO1/2 carry two payload bytes per row; APUIO3 carries the commit token.
- Payload size is therefore 72 x 2 = 144 bytes.
- The submit row uses APUIO3 `$57` as the receive-start marker.
- The receiver reads APUIO1/2 for 72 commit-token iterations and stores 144 bytes.
- The receiver uses the supplied destination pointer and no playback is allowed in transport-only mode.

## Latest Transaction-0 and Serial Evidence

- Host producer entry is reached at `01:A646` on each service frame in the latest ROM.
- CPU submits destination `$121A` and marker `$57`; the command value is `$16`.
- The current contract is one submit row followed by 72 mode-4 rows. APUIO0 remains stable at the freshness-bearing submitted command; APUIO1/2 carry payload and APUIO3 commits each row.
- A one-frame command-to-HDMA gap is present so the SPC command handler can enter before payload rows begin.
- SPC command acceptance and payload-complete ACK are observed for transaction 0; destination `$121A` exactly matches FOOTDIE chunk 0, SHA `cb3bb339dc40eae86ab91d33430e852734f4a7c04d241ca74086368ebb081b00`.
- The original 48 x 3 contract failed because APUIO0 published a row before payload data was stable. The commit-last 72 x 2 contract fixed that race.
- A subsequent alternating serial failure was traced to stale `src/main.bin` packaging: source contained dynamic APUIO0 loads while the packaged ROM still contained immediate `A9 16` bytes.
- After explicit fresh Poppy assembly and repackaging, chunks 0..15 passed serially, one transaction at a time, with exact external ARAM equality. Both generations passed; slot 7's intentional ring-header patch was accounted for.
- Current serial acceptance after the fresh rebuild: 16/16 chunks exact, 16/16 ACKed, no playback enabled.
- Playback observations before corrected extraction: prefill slots 0..6 were exact; normal start changed directory entry 33 to `1A121A12`; voice-0 capture was invalid because the extracted source began with metadata. This is superseded by the corrected BRR and must be rerun.
- `rebuild.py --check`, bank-0 layout guard, and voice-0 reservation verifier pass for the current artifacts.

## Stage A Status

- Stage A is not proven.
- Previous host-reported chunk counts were rejected because they did not prove SPC acceptance or correct ARAM contents.
- A previous playback run stopped near 2017 voice-0 samples, consistent with one physical ring traversal, but DSP diagnosis is deferred until transport is correct.
- Current serial harness proves transaction 0 and chunks 0..15 without playback; host counters are still secondary to ACK plus external ARAM equality.
- A forced-threshold diagnostic with stream enable, active flag, serial permit, and budget 143 still leaves budget/state/table unchanged across frames.
- Execution hooks in the clean diagnostic session reached neither the main-loop producer call-site range nor producer entry `01:A580`.
- Historical layout defect: an earlier image placed main-loop/NMI/IRQ code in the header window and reached `PC=$0007`; it was repaired before d58b513 and is now guarded by the fixed bank-0 contract.
- Current runtime layout: main-loop `$00:FF0C`, ordinary runtime end `$00:FF2E`, NMI `$00:FFA0`, IRQ `$00:FFB0`, with 114 bytes free before NMI.
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

## Latest Gate A Evidence (2026-09-02)

- Corrected FOOTDIE extraction remains authoritative: Common Audio Data directory-derived BRR offset `$31`, 32733 bytes, 3637 blocks, 58192 decoded samples, one final END header, zero LOOP headers.
- Corrected BRR SHA-256: `6b7677dc2666ab4de95021ef88ff2ce43b2f30263ffee6ec2562a455745d3c7d`.
- Serialized transport with corrected content remains 16/16 exact; chunk 0 expected and ARAM SHA-256: `317fa853814e0315096e2ca441d84ab55d8faa3296e0e231b87b609f18f431ae`.
- Host stream table uses HDMA line-count `1` for the submit and 72 payload rows, preserving the accepted 72 x 2 protocol, APUIO ownership, and `$57`.
- The once-per-frame pacing fix plus late stream pump raised measured delivery from 25/60 frames to approximately 43/60 frames, above the 6201.5625-byte/s authored-source requirement.
- A separate consumer-credit safety ceiling now prevents the next submission when it would be eight chunks ahead of the estimated consumer. Transport-only prefill is excluded from this playback epoch.
- Current source-built/package ROM SHA-256: `ddb68415622e65557ad9e68dba3ec65ecddc6a49cad7681c7a88c53e5336a4a2`.
- Playback Gate A controlled run: prefill chunks 0..6 exact; 228/228 source chunks accepted; no KOFF; natural ENDX at output sample `168852`, duration `5.276625 s` at 32000 Hz.
- Clean DSP trace observed 28 physical slot-7-to-slot-0 wraps. The first post-wrap slot-0 fetch resolves to source block 128; the prior unsafe schedule resolved to source block 256 and omitted one 128-block generation. The final fetch is source block 3636 with genuine header `$01`.
- Playback Gate A is PASS for the bounded full-source run: no premature ENDX, no KOFF, physical loop active, final natural END. Explicit overwrite/underrun telemetry remains a follow-up hardening item, not evidence of a failure in this run.
- Targeted G11 resident canary remains PASS: voice 7, 12049 samples, natural ENDX, 0.37653125 s, byte-identical oracle.

## Coexistence Evidence (2026-09-03)

- Shared-armory frame liveness is PASS at `18c05d3f076728d05310c6e591b7d0a08d604d42`: exact 1, 1, and 10 frame requests advanced exactly and did not time out.
- The corrected coexistence fixture required `STREAM_IMMEDIATE_START=1`; the default startup mode stalled during prefill before the consumer epoch was active.
- One real landed player-vs-AI hit changed request count `5 -> 6` exactly once while the stream was active.
- Voice 7 capture: KON sample `24098`, natural ENDX sample `36147`, no KOFF; exactly 12049 samples / `0.37653125 s`.
- Voice 0 capture produced 168852 samples at 32000 Hz, SHA-256 `2e3083c634325e8ed58aa09f525705137d32a586c8924eff2a3817670058d8f1`, no KOFF, natural ENDX. The matched stream-only control produced identical PCM bytes and hash.
- Coexistence stream telemetry: 228/228 accepted chunks, 28 physical wraps, first post-wrap source block 128, final source block 3636 with header `$01`.
- This is local full Stage A coexistence evidence, not yet a published commit boundary.

## Resume Here

- Published baseline is `aeccf841`; serialized transport proof is `d58b513`.
- Transaction 0 and serialized chunks 0..15 remain exact. Bank-0 layout and corrected directory-derived FOOTDIE extraction remain active.
- Playback Gate A is bounded-PASS: the current ROM delivered all 228 chunks, survived 28 physical wraps, reached source block 3636, and naturally ENDXed at `168852` output samples / `5.276625 s`.
- Shared armory liveness is PASS. The ordinary G11 gameplay control reaches its real landed-hit request under the armory; its legacy mixed-waveform checks are non-authoritative and were not used as a G11 verdict.
- The latest stream-only armory probe initially stalled during prefill because the fixture omitted `STREAM_IMMEDIATE_START=1`; the corrected startup mode reached all seven exact prefill ACKs. That earlier result was a fixture failure, not resident-SFX or stream-playback evidence.
- Exact next gate: run focused build/static canaries, remove only disposable BOR diagnostics, review the coherent diff, and create one Stage A completion commit. Do not run full regression.
- Current ROM SHA: `ddb68415622e65557ad9e68dba3ec65ecddc6a49cad7681c7a88c53e5336a4a2`.
- Current safety rule: consumer credit advances once per video frame; a submission is allowed only while `next_chunk - estimated_consumed_chunk < 8`; transport-only prefill does not advance consumer credit.
- Protected dirty file: `tools/audio/sfx_production_banks.json`; leave untouched and unstaged.
- Protected dirty repository: `E:\gh\Mesen2-mcp-server`; leave untouched.
- Forbidden scope: no merge, G12, full regression, voice 1, generalized heap, or authored-audio modification.
