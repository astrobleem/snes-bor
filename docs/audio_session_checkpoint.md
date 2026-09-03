# SNES BOR Audio Content Pass Checkpoint

## Resume Here

- Branch: `audio-content-pass`.
- Work is uncommitted and must be preserved.
- Published transport boundary: `d58b513`.
- Transaction 0 and serialized chunks 0..15 are exact and ACK-gated; bank-0 layout is resolved and guarded.
- Current next gate: controlled physical playback and ring-wrap proof. Full Stage A remains unproven.
- The source provenance cleanup is uncommitted; no playback has started.
- Current driver evidence: latest accepted export is 3420 bytes, SHA `12b285126ee811aacb6012b2ded6df056accf252df19563377accd5d4b69e3aa`.
- Current audio blob evidence: SHA `ee3b47b3c0c50bfa5ddab1539198ed6b597c2d8255f95e6602cd2c6022f28235`.
- Current ROM evidence: source-built ROM SHA `9a2f47fb27b9e0bfa2bf632c28215cf404e70ba7a43209128946f28f0c66d240`.
- Source provenance cleanup is now reconstructed as the pinned upstream commit plus the accepted voice-0 patch and the new stream-transport patch; fresh reconstructed export is byte-identical to the accepted driver and blob.
- Revalidated after cleanup: transaction 0 exact ARAM PASS, serialized chunks 0..15 exact PASS, `rebuild.py --check` PASS, voice-0 reservation PASS, and authoritative G11 voice-7 PASS.
- Current next gate: controlled physical playback and ring-wrap proof. Do not claim playback or full Stage A yet.
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
- Current serial acceptance: 16/16 chunks exact, 16/16 ACKed, no playback enabled.
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
