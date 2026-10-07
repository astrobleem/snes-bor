Source frame audio compilation and private native proof
======================================================

The B4FE sound namespace supplies identities; the compiler contains no actor
name dispatch. `source_frame_audio.py` compiles every selected source WAV through
the pinned TAD compiler. The current stream backend requires 11025 Hz mono
PCM_u8 before BRR encoding. This is an explicit ACCEPTED_COMPAT audio adaptation,
with the full source duration retained and at most one silent BRR block of
padding. It does not alter source image colors or pixels.

The compiler splits long WAVs into independently encoded segments that begin
with filter 0. Only the final concatenated BRR block retains END. This removes
the single-effect compiler sample-count limit without clipping the source.
The existing runtime still needs an extended length/address owner for assets
larger than 65535 bytes; offline compilation does not imply runtime admission.

Run from the repository with `PYTHONPATH=tools/bor_compile;tools/verify`:

```
python tools/bor_compile/source_frame_audio.py --source "Masters of the Universe [v.3.0 Build 4086].pak" --output out/byor-motu-source-frame-audio-stream --stream-rate 11025
python tools/bor_compile/source_frame_audio_verify.py --source "Masters of the Universe [v.3.0 Build 4086].pak" --folder out/byor-motu-source-frame-audio-stream
```

`tools/audio/source_stream_spc.patch` applies to TAD commit
00215a2e9aaf327d620120a48b47d74f80d5b521 in an isolated checkout. It includes
the imported existing stream protocol changes plus explicit voice-0 GAIN/ADSR
initialization and equal left/right volume. The receipt records both the
external baseline and isolated source hashes. The external dirty checkout
was not edited. Build the isolated checkout with:

```
cargo build --release -p tad-compiler --target-dir E:/gh/snes-bor/out/byor-motu-tad-build
```

Use the resulting `audio-driver.bin` with the private native fixture:

```
python tools/verify/m4_scripted_projectile_request_native.py --rom out/byor-motu-vm-regression/bor.sfc --source "Masters of the Universe [v.3.0 Build 4086].pak" --output out/byor-motu-scripted-projectile-audio-native-v13 --constructor --from-frame-zero --audio-source out/byor-motu-source-frame-audio-stream --isolate-audio --idle-audio-pump --spc-driver <isolated-audio-driver.bin> --prefill-audio --audio-arm-guard
python tools/verify/m4_source_audio_native_verify.py --folder out/byor-motu-scripted-projectile-audio-native-v13 --assets out/byor-motu-source-frame-audio-stream
```

The private fixture advances actual authored frames, executes the real
projectile constructor and services the actual source sound ticket. It then
pauses legacy gameplay for transport measurement. Seven chunks prefill before
the eighth transaction starts voice 0. The observer verifies each acknowledged
physical ring chunk in SPC RAM, including intentional intermediate ring-loop
header bits and deterministic final transfer padding. DSP envelope, SRCN,
pitch and END duration are checked separately from the WAV fingerprint.

The v13 proof receives all 8073 meaningful BRR bytes in 57 chunks with no
mismatch or observed producer-ledger underrun. Voice 0 is active for 78 observed
fields versus 78.25 expected at pitch 1411, then reaches envelope zero.
First active observation is field 20 of the post-constructor observer.

This proves isolated transport and full-duration DSP execution. It does not
prove source-event-exact timing, sample-exact recorded waveform, concurrent
effects, ordinary TAD voice coexistence, production binding, or MOTU gameplay.
Those remain integration requirements. No color reduction was applied.

Shared host integration
-----------------------

The host now services stream ACKs while waiting for the next NMI, using code
in bank 63. The original bank-0 wait reserves exactly its old six entry bytes
for an external jump and padding; its loop/RTS addresses and total size remain
unchanged. The helper preserves X/Y/D/DBR/SP and the original REP/CMP A/flags
contract. No stream work was added to NMI.

Repeated service calls no longer re-arm a descriptor in arm phase 2. Consumer
credit begins only after the SPC acknowledges the first normal transaction,
and byte mode/epoch fields are explicitly masked during 16-bit reads. This
prevents premature ring-slot replacement. The private prefill controller grants
a permit only while the producer is idle, so the first normal transaction fills
slot 7 and starts at the original ring head.

`out/byor-motu-scripted-projectile-audio-shared-v3` proves the shared host with
the private SPC driver/source binding. Its sample-level DSP observer traverses
all 897 source BRR blocks in order, checking physical address, header and FNV32
block fingerprint, with no skipped, repeated or mismatched blocks. Separate
SPC RAM reads still check all 8073 meaningful bytes and final transfer padding
against the SHA256-identified compiled asset. The voice envelope remains active
for 78 fields and then ends. This adds source block traversal evidence, without
claiming the resampled BRR recording equals the original WAV sample for sample.

The focused original-BOR Easy selector/first-stage smoke reaches visible static
source OBJ presentation at field 219. Initial `$27` diagnostics are existing
owned-DMA busy retries; they are counted separately from hard errors. Nine
existing source visual tests pass. All 17 protected tracked files are unchanged.
The width audit has zero new violations, 183 existing baseline violations and
two baseline entries now clean; this is not a claim that the raw width guard
has zero violations. The production SPC driver and MOTU sound owner still await
integration. No full campaigns were rerun.

Production SPC driver
---------------------

The pinned production audio blob now contains the same 3449-byte driver used
by the isolated proof. `soundwork/tad/driver_baseline.json` records its compiler,
four source inputs, incremental envelope patch and prior toolchain identity.
`rebuild.py` prefers this declared isolated compiler and validates every input
and generated output. The external TAD checkout remains untouched.

To reproduce the toolchain in a fresh workspace, create a detached worktree
from TAD commit 00215a2e9aaf327d620120a48b47d74f80d5b521 at
`out/byor-motu-tad-toolchain`, apply `tools/audio/source_stream_spc.patch`, and
run the cargo command above from that worktree. Preserve that owned toolchain
and build directory while the pinned production compiler depends on them.
Then run `python soundwork/tad/rebuild.py --check` from this repository.

The loader and common resident content bytes are identical. The three ROM
offsets in the data table move by 12 bytes; the table itself moves from
`$018E14` to `$018E20`. Bank 0 has four changed operand bytes (the existing
driver-size immediate and existing table references), zero growth, and unchanged
existing symbol addresses.

`out/byor-motu-scripted-projectile-audio-production-driver` proves all 897 source
blocks with the production driver and no SPC override. The source binding and
model context remain isolated. `m4_resident_audio_native.py` separately proves
two distinct resident effects can overlap on ordinary voices 7 and 6 without
claiming voice 0; queue inputs are explicitly instrumented. Production source
namespace/long-asset binding and source-event timing remain pending.


ASAD namespace addressing now uses a compiler-owned descriptor table at
`$3C:C000` and a separate `$E0:0000..$EF:FFFF` ROM payload window through
SA-1 EXB mapping 2. FXB remains available to presentation. The fixed metadata
reservation admits at most 2,047 sound identities; larger namespaces fail
explicitly in compiler and runtime. Meaningful source lengths and cursors
are wider than 16 bits. Transport tail padding is explicit and verified.

`docs/receipts/byor-motu-source-audio-asad-native.json` records the isolated
native evidence. Knightbot's authored frame-zero through frame-six callback,
projectile constructor, and frame sound use sound namespace index 16 through
`SourceAudio_Start`, with all 897 BRR blocks traversed exactly. The separate
He_Man entry backend proof crosses the 64 KiB boundary, transfers 532 chunks,
and traverses all 8,501 source blocks before END. Its verification was
recomputed from retained evidence after correcting the observer's single-ACK
assumption: two ACKs in distinct physical ring slots remain observable.

These proofs do not establish live MOTU gameplay, exact sound-event latency,
stream restart, polyphony, or admission alongside the moving lossless effect.
An active stream explicitly rejects a new request as busy; no silent source
alias or preemption is used. The production foreign sound-event owner remains
pending. No color reduction was applied.


The width guard was subsequently resolved in commit dc9e217. All 183 flagged
sites now carry explicit accumulator/index assertions; the entire machine-code
binary was byte-identical before and after. The raw guard has zero violations,
and its obsolete baseline entries were removed. This fixes assembler sizing
annotations without claiming a runtime control-flow proof for every call path.

The current shared stream host also passes the retained fixed-context hybrid
pixel regression: `docs/receipts/byor-motu-hybrid-shared-audio-regression.json`.
Its frozen compiled palette indices match the original residency atlas. A
regenerated frame had changed 421 indices, so combining that frame with the
old atlas correctly failed pixel identity. The matched proof checks 4,300,800
pixels with no mismatch and no unsafe palette/VRAM access or OBJ overflow.
The corrected transport transferred 36 of 44 original-BOR source-2 chunks
during the measured effect sequence; full concurrent playback is unproven.
Do not carry forward the old 44-chunk completion claim to this updated host.


The subsequent joint proof combines the retained hybrid sequence with the real
namespace-16 asset and the production SPC driver. See
`docs/receipts/byor-motu-hybrid-asad-dsp-native.json`. All 57 transport chunks,
8,073 meaningful BRR bytes, tail padding, and 897 DSP blocks match. The voice
plays continuously for 78 fields and reaches END. Concurrently, all 4,300,800
visible pixels match, with zero unsafe CGRAM/VRAM accesses and OBJ overflow.

Late-only packet preparation was insufficient: the consumer overtook the
producer at field 52, and the DSP read stale blocks beginning at source block
336. That failure is retained separately. The working policy prepares the
next-field packet with palette IRQs active. The arm helper changes the NMI
HDMA shadow; it does not enable a channel in the current scanout. One long
pointer now serves an entire 144-byte generic packet, preserving the existing
mode-4 table layout. Legacy sources retain their byte-reader path. The logical
bank carry is explicitly maintained, and the 76,509-byte asset traverses all
8,501 DSP blocks after this optimization.

The final joint proof measures packet preparation at 55,154 master clocks,
frame audio service at 83,394 clocks, peak canvas NMI at 49,942 clocks, and a
minimum NMI return margin of 414 clocks before the next field. These are fixed
scene measurements, not a moving-world resource certificate.

Palette payloads occupy `$E0:0000..$E4:FFFF`. A configurable audio reservation
starts at `$E8:0000`, with all 17 assets occupying 241,920 bytes. Both use EXB
mapping 2 without overlap. Fixture programs avoid bank 60's descriptor table
and the occupied shared-code banks 61..63. The offline transfer replay checks
8,257,536 component pixels and rejects a palette-index/atlas mismatch before
emulation. No color reduction is applied. Stream restart, polyphony, exact
source-event latency and the actual foreign world owner remain pending.
