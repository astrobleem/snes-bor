# BYOR MOTU direct scratch-to-VRAM pair DMA

`BYOR_MOTU_DIRECT_PAIR_DMA_PASS` against the certified fused renderer, starting
from commit `7e5823470f67794fb51ca1c03dc969a9306e2ece`.

The opt-in `--direct-pair-dma` applies Astra's supplied transformation after
warm residency, occupancy and tile fusion. Exactly two WarmStage call targets
change: backdrop restoration and changed actor publication. WarmDirectPair
sends the completed HIGH 64 bytes from 42:D680 and LOW 16 bytes from 42:D6C0
directly to the leased slot with channel 7 mode 1. Each descriptor reloads all
source, bank, target and size fields. HIGH uses VRAM word slot*32; LOW uses
6000+slot*8. No scratch-to-staging copies execute. WarmCompare, source simulation,
occupancy, foreground composition, physical residency, backdrop restoration,
map DMA and publication fences retain their code and semantics. The default
staging path remains selectable without the flag.

Candidate: `out/byor-motu-direct-pair-v1/native/bor.sfc`.
SHA256: `00622aaba27c82f20ed1ec6546de7a0ebce94f142b8b85f3de97a88f941b349a`.
A fresh final-source build reproduces it exactly. A build with the new option
disabled reproduces the certified fused control SHA256
`01b757d34ec1ad568758d325678b63bb96ad2f5b87badedae4ee65e1ac711977`.
Astra's Downloads archive and the subsequently copied repository archive have
identical SHA256 `97d49ab5f8095063ade9574ce24be494f19c83501e81052a9b9d6ddd2124e577`.
The package was extracted into a fresh private directory; its five tests pass.

| Worst warm measurement | Staged control | Direct pair |
|---|---:|---:|
| Composition | 108.448 ms | 108.437 ms |
| Preflight + allocation | 52.139 ms | 52.139 ms |
| DMA | 4.329 ms | 4.740 ms |
| Other production | 75.257 ms | 50.029 ms |
| Total production | 231.014 ms | 207.137 ms |
| Publication | 240.665 ms | 208.204 ms |
| Actual forced blank | 190.478 ms | 157.203 ms |

Worst publication improves **13.4878% / 32.460457 ms**. Worst production falls
by **23.877150 ms**. Every changing warm epoch produces faster. The meaningful
gate requires at least 5% lower worst warm production, lower worst publication,
and faster production for every changing warm epoch. No neutral result is
classified as an optimization pass. Column maxima occur in different epochs;
compare the paired rows below rather than adding the maxima.

## Epoch 17: measured staging tradeoff

The old path spent **30.174226 ms / 648,060 clocks** exclusively in WarmStage,
including **25.127961 ms / 539,680 clocks** for the two staging MVNs. The new
path calls WarmDirectPair **126 times**: 30 backdrop restores plus 96 changed
actor pairs. It costs **247,096 clocks / 11.505000 ms inclusive**, comprising
**152,304 clocks / 7.091404 ms CPU/bus-active** and
**94,792 clocks / 4.413596 ms direct CHR DMA**.

CHR data is unchanged at **10,080 bytes**, but descriptors increase from
62 to **252**. Map data is unchanged at **464 bytes / 64 descriptors**.
The complete epoch transfers **10,544 bytes / 316 descriptors**, versus
10,544 bytes / 126 descriptors. Total measured DMA rises from 4.328856 to
4.740267 ms. Production falls from **226.248867 to 201.436402 ms**;
publication falls from **226.331652 to 208.199180 ms**. The former other-production
interval falls from 75.256585 to 50.029077 ms. The descriptor/setup penalty is
measured and does not offset the software-copy savings.

WarmStage executes zero times in every epoch. WarmFlush still executes twice
per changing epoch but staging count 60 stays zero; these are empty returns
with no staging CHR descriptors. No new transfer uses 42:C800 or 42:CC00.
Independent payload capture/replay verifies direct HIGH/LOW data, physical slot
addresses and both post-DMA fences. Pair-list identity with the old coalesced
path is deliberately not required; final resident and written VRAM contents are.

## Paired per-epoch costs

Except for the direct-call column, each pair is **control/direct milliseconds**.
Direct call costs are inclusive/CPU-exclusive milliseconds; exclusive subtracts
its two observed DMA intervals. These are actual native emulated master clocks,
including CPU bus/refresh costs. Routine entry through actual caller return fetch
is observed without adding instructions to the ROM. NMI is suppressed in this
blanked phase. DMA completion is sampled after the first post-DMA instruction,
consistently with the existing control; no nominal CPU-cycle estimate is used.

| Epoch | Direct calls | Direct inclusive/exclusive | DMA bytes | Descriptors control/direct | DMA | Composition | Production | Publication | Actual blank |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 80 | 7.297/4.485 | 58904 | 70/198 | 22.755/23.044 | 78.973/78.975 | 195.852/180.381 | 205.356/188.715 | 159.862/143.220 |
| 1 | 111 | 10.108/6.187 | 9332 | 104/278 | 3.811/4.219 | 103.747/103.739 | 214.364/192.761 | 224.047/192.842 | 179.935/148.730 |
| 2 | 103 | 9.393/5.770 | 8400 | 70/232 | 3.383/3.748 | 102.378/102.373 | 205.336/185.317 | 214.243/197.606 | 173.458/156.822 |
| 3 noop | 0 | 0.000/0.000 | 0 | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.276/0.276 | 0.276/0.276 | 0.000/0.000 |
| 4 | 104 | 9.481/5.812 | 8740 | 98/266 | 3.570/3.963 | 103.913/103.918 | 206.243/186.197 | 214.243/197.608 | 173.439/156.804 |
| 5 noop | 0 | 0.000/0.000 | 0 | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.276/0.276 | 0.276/0.276 | 0.000/0.000 |
| 6 | 104 | 9.501/5.826 | 8564 | 78/244 | 3.467/3.854 | 102.989/102.991 | 203.082/182.967 | 214.246/183.048 | 174.796/143.597 |
| 7 noop | 0 | 0.000/0.000 | 0 | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.276/0.276 | 0.276/0.276 | 0.000/0.000 |
| 8 | 99 | 9.031/5.529 | 8260 | 96/250 | 3.393/3.745 | 102.428/102.432 | 205.289/185.983 | 214.248/197.606 | 173.463/156.821 |
| 9 | 122 | 11.108/6.813 | 10204 | 118/304 | 4.179/4.599 | 93.110/93.108 | 222.873/198.922 | 224.839/208.204 | 172.448/155.813 |
| 10 | 124 | 11.315/6.931 | 10372 | 116/308 | 4.255/4.692 | 104.384/104.375 | 230.866/206.644 | 239.835/206.725 | 189.648/156.538 |
| 11 noop | 0 | 0.000/0.000 | 0 | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.275/0.275 | 0.275/0.275 | 0.000/0.000 |
| 12 noop | 0 | 0.000/0.000 | 0 | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.275/0.275 | 0.275/0.275 | 0.000/0.000 |
| 13 noop | 0 | 0.000/0.000 | 0 | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.275/0.275 | 0.275/0.275 | 0.000/0.000 |
| 14 | 122 | 11.146/6.850 | 10228 | 118/304 | 4.195/4.613 | 91.479/91.481 | 221.600/197.656 | 224.838/208.200 | 172.488/155.850 |
| 15 | 122 | 11.106/6.800 | 10228 | 116/304 | 4.201/4.628 | 104.388/104.384 | 231.014/207.137 | 240.665/207.389 | 190.478/157.203 |
| 16 | 108 | 9.847/6.051 | 8924 | 84/260 | 3.617/4.015 | 108.448/108.437 | 212.077/191.313 | 214.254/197.603 | 173.404/156.752 |
| 17 | 126 | 11.505/7.091 | 10544 | 126/316 | 4.329/4.740 | 94.525/94.528 | 226.249/201.436 | 226.332/208.199 | 173.935/155.802 |

Epoch 0 is cold: production **195.852359 → 180.380560 ms**, publication
**205.356267 → 188.715046 ms**, DMA **22.754847 → 23.044270 ms**.
Cold byte count is unchanged at **58,904**, with descriptors **70 → 198**.
Cold boot and palette transfers are retained. Warm maxima above exclude cold.
Detailed preflight, other-production, direct inclusive/exclusive/DMA master
clocks and complete paired measurements are in the JSON receipt.

## Correctness and resource ownership

One native ROM passes the same 18 real JOY1/source-world epochs and all
**1,032,192 RGB555 pixels with zero mismatches**, independently checked against
source composition, screenshots and decoded physical VRAM. All world snapshots,
CGRAM, expected frames and committed residency directories are byte-identical
to the fused control. Foreground ordering and backdrop restoration remain exact.
Actual descriptor/source-payload replay reproduces all **1,179,648 physical VRAM
bytes** across 18 epochs, with intact-home identities and reference counts checked.
Every direct pair has a 64-byte HIGH and 16-byte LOW transfer to the same leased
physical slot, and all transfers finish before the displayed epoch/unblank.
No palette updates occur during warm epochs.

Raw A/B full-VRAM buffers retain different unreferenced boot garbage in
9,869..10,571 bytes. Every such difference must be never written by the candidate,
unreferenced by the identical directory, and unchanged from each run's initial
capture. Every producer-written/resident byte matches the control; the candidate's
entire physical VRAM also passes independent full DMA replay. This does not
substitute pixel-only comparison for physical transfer verification.

All six repeated projections (epochs 3,5,7,11,12,13) have zero composition, DMA,
direct calls, staging/flush calls and blanking. Actual invalid LEFT retains the
previous complete VRAM/display and epoch. Resource faults and unsafe PPU writes
are zero. Source physics, returning worker code and graphics-end canaries pass.

Poppy assembles **119 bytes** at bank 57 **D400..D476**, exclusive end D477.
The baseline lease contains only zeros. A full-ROM byte audit permits only this
new routine and the two JSR operand changes; all other program/data bytes are
identical. The original 175-byte row kernel, 289-byte fused tile routine, NMI,
WarmCompare, WarmCopyBackdrop, occupancy tables, F43000..F435FF refcount table,
palettes and source assets retain their exact identities. New OnlineDmaDone8/9
markers use the existing completion convention. No additional DP/BW-RAM/WRAM/
VRAM lease is allocated. The established 707/768 paired-slot bound and full
64-KiB HIGH/LOW/map layout remain unchanged, with no added OBJ arena. Both call
sites follow OnlineBlank and precede OnlineComplete, so displayed references
are retired under forced blank before CHR overwrite.

All **71 focused tests** pass, including five supplied offline tests, default
ROM reproducibility, whole-ROM mutation confinement, kernel/data lease tampering,
full native DMA replay, noop preservation and rejection of negligible performance
changes as a PASS. The final-source candidate rebuild is byte-identical. All 29
inherited dirty tracked files, including the protected 17, remain byte-identical
to `out/byor-motu-direct-dirty-before.json`. No reset/stash/clean, PCM copy,
unrelated media/source-output regeneration or master merge occurred. Old native
controls were retained by identity and were not rerun.

## Reproduction and scope

From the repository root with retained source assets, PAK, source-symbol/MSU
identities and toolchain available, use a fresh output directory:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_opaque_component_native.py --output out/byor-motu-direct-pair-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma
out/byor-motu-solver-venv/Scripts/python.exe -m unittest test_direct_pair_dma test_m4_direct_pair_component -v
```

Omit `--direct-pair-dma` for the unchanged staged control. The opt-in experiment
requires --warm, --occupancy and --tile-fusion. Both native artifacts and the
paired JSON receipt are retained; stopping after this verified experiment.

Composition **108.437 ms**, preflight/allocation **52.139 ms** and remaining
other production **50.029 ms** are still substantial. Forced blank still lasts
up to **157.203 ms**; this is not seamless or 30-Hz publication. No SA-1 migration,
general SCREEN alpha, breath, HUD, combat, audio timing, natural 200-Hz world
traversal or complete MOTU Demo is claimed.
