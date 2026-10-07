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
