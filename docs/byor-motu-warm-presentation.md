# Private MOTU warm presentation checkpoint

The opt-in owner now presents immutable snapshots from naturally committed
source ticks while later ticks and the entry-sound transport continue.
This bounded native checkpoint is not selected by the production build.
It establishes whole-picture stability, not gameplay or target cadence.

The private profile admits one naturally born He_Man, SELECT/IDLE/WALK,
map 0, zero camera/altitude, and integer anchors inside the 256 by 224 viewport.
Unsupported tuples stop visibly. Assets include all 149 authored frame
references and 70 distinct full indexed images, without cropping or colour
reduction. The native run reaches SELECT frame 8 and displays frames 1 and 4;
IDLE/WALK rendering and actual movement remain unmeasured.

## Runtime ownership

The callable service resumes the actual twelve-phase world dispatcher,
commits at most one completed tick, and seals actor/side rows with an epoch.
Fresh physical input is sampled only when prior source clock debt is empty;
catch-up ticks retain that sample. The pinned source lateness clamp is intact.
Latest, render and display snapshots are separate. A coherent 148-byte render
pin remains frozen while real ticks advance the latest snapshot. Immediately
after both map DMAs, a leaf copies that pin to the display snapshot before
unchanged reference bookkeeping. It preserves A/X/P and never calls source
work. The final map wait cannot yield after the last reversible fault check.

The accepted bank-57 publisher is unchanged. Its private bank-46 copy retains
pair-DMA, capacity, retry, rollback and fused-reference algorithms. Checked
full-bank source images feed a lossless row decoder and ten-plane contribution
tables. Twelve unused CGRAM entries are appended; old entries remain intact.
All code sections and assets have checked non-overlapping bank extents.

The same preconstructor acquisition drains the old DMA queue, retires its
producers and extends the exclusive retired SceneVideo lease through
`$7E9A60`; the old foreground never resumes. Every yielded source call has an
exact 736-byte guard covering renderer DP, restoration records and queued DMA.
A changed byte faults, restores those bytes and takes pre-map rollback.
This does not establish production concurrency.

## Measured evidence

Final build: `out/byor-motu-warm-presentation-v1/native-v10`, ROM SHA256
`a785450eca535b873435532ebdd3d03b55339e1ed7e5a46f7dc437796e3235d3`.
Its corrected audio/world input is `audio-full-v15`, SHA256
`8964ddc6587b35fb233c0aea7f53eb2daff479d95872110c151a5286826d629b`.

`fast-capture-v6` records 1,800 consecutive one-field host steps. Every owned
field has complete read-only state, full 148-byte warm snapshots with 32-bit
epochs, and lossless RGB24 viewport evidence.
Unchanged images reference a prior full image only after comparing every
pixel; changed images use RLE. All owned MCP screenshot calibrations match,
including the final field. Lua returns a 256 by 239 uncropped buffer; the
configured seven-top/eight-bottom crop yields the calibrated 256 by 224 view.

All 1,779 fields after `WarmMainReady` match the source compositor exactly:
102,014,976 RGB555 pixels. The earlier constructor-ready field at index 20 /
host frame 525 is blank and remains a reported mismatch; the diagnostic's
`exact_pixels_all_fields` flag stays false. A publication must strictly precede
the completed field's endFrame clock. Host joins require exactly
`frameCount = endFrame.ppuFrame + 1`; future tuples never authorize old images.

There are 216 real commits and coherent seals, advancing source time 48 to
264. Epoch 25 / SELECT frame 1 publishes at native frame 1199; epoch 98 /
frame 4 at 1717. At capture end, display is epoch 98, in-progress render is
epoch 162 / frame 6, and latest is epoch 216 / frame 8. Fresh pictures take
hundreds of fields, far outside the target cadence.

Actual PPU VBlank edges bound 23 complete DMA batches and two map commits.
Minimum completion margins are 24,082 clocks for batches and 11,616 for maps,
retaining the 10,000-clock requirement. Missing pairs, active-display work,
reordered boundaries, incomplete transactions and insufficient margins reject.
Thirteen one-player source refreshes exactly cover physical Right, Left and
release samples. Port 2 is unowned; SELECT samples do not prove movement.
All 532 ARAM packets match the prepared source payload with zero mismatched
bytes; the backend retires and channel 11 becomes idle.

## Audio completion correction

The longer run exposed an inherited width fault after voice retirement.
The inactive path reached `LiveAudio_PumpCheckCompletion` with M=8, but the
historical ROM encoded `CMP #4` as `C9 04 00`; the extra byte executes as BRK.
The unfixed native trace loses stack depth and source-clock progress.
The shared entry now establishes word width with `REP #$20`; fixed bytes
begin `C2 20 AF F0 28 7E C9 04 00`. Executed tests cover both paths, full
context restoration and the historical failure. The fixed native trace keeps
NMI/source-clock gate counts equal and counts all 1,778 fields after clock
initialization, including after audio retirement. Old captures/receipts remain
intact; their short observations did not establish continued interrupt health.

## Reproduction and remaining work

Build with `tools/verify/m4_warm_world_native.py` after regenerating its pinned
audio/world input using `m4_live_world_native.py --audio-assets`. Capture uses
`m4_warm_world_fast_capture.py` inside the contained job and ordinary shared
lease, with exactly one field per host step. Wrapped/reordered 32-bit Lua clock
observations reject; longer runs need a verified unwrapping protocol.
The compact receipt is `docs/receipts/byor-motu-warm-presentation.json`.
Private builds, failed attempts, raw evidence, independent reviews, test logs
and preservation checks remain under `out/byor-motu-warm-presentation-v1/`.
The configured regression suite passes 731 tests and 6,432 subtests without
skips; all 39 affected capture/timing tests pass after the epoch observer
extension and missing-edge regression. Thirty inherited controls and 77 prior controls match their input
hashes, including the absent prompt. The final shared lease is released and
the contained job has zero surviving processes.

Natural SELECT completion, IDLE/WALK with movement, other poses/models,
stage/camera integration, multiple actors, combat, HUD, general audio and
progression remain unfinished. No 200-Hz, 30-FPS, production concurrency,
general-audio or complete-game claim follows.
