# BG3 stage-load address-width correction

The real Stage_Load path now selects A16 before loading the full `$6800`
VRAM word address. Previously it loaded only `$00` in A8, then stored the
inherited accumulator high byte to `$2117`. In the measured case this cleared
BG1 words `$0000..03FF`, not BG3 `$6800..6BFF`.

Only the width/address setup changes. The existing 1024-word loop, VMAIN
contract, stage loading, actor policy and content are unchanged.

Validation on the rebuilt ROM:

- Address-store observation: A=`$6800`, P=`$04` (M=0).
- 1024 clear iterations; VRAM bytes `$D000..D7FF` all zero afterward.
- Full before/after VRAM comparison: zero changes outside that interval.
- Emitted `LDA #$6800` is A16 and overwrites both prior accumulator bytes;
  checked independently of all65536 prior A values.
- Corrected resident/layout-dispatch replay retains43 semantic snapshots,
  25 callback events and source pass ordering.
- Corrected control original-epoch time4676456 vs4676514 before; the tiny
  58-clock difference is recorded, not claimed as a useful optimization.

Live clear evidence: `out/actor_s7_dma_bj3ngxre/clear-proof.json` and
`clear-oracle.log`. S7's private `tools/verify/actor_s7_bg3_clear.py` drives
the oracle; it is not a production dependency. The full-VRAM capture is
isolated from the performance trace to avoid observer timeout overhead.

Build: `python build_rom.py --reuse-audio-from HEAD`, with121 unchanged
audio inputs,25 PCM hashes and8 bank hashes verified. The initial ordinary
build stopped on an existing stale runtime-audio summary; no audio evidence
was modified to bypass it. The pinned reuse path then built successfully.

ROM SHA256: `df46b8b9a030186c567ee1227fd96fe7aa903bc313dc17d7247be80cf2edc96e`.
MSU SHA256 unchanged:
`b1c4e499d611445e83a67f80f5be88dc2c5c0e2d91ebc14901e7891b8bcd89fc`.

S7 fetch/layout/residency experiments remain separate and uncommitted.
