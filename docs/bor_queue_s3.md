# S3 queue-capacity ABI and overflow closure

Pre-fix source: `28c71f99c51428bb3d18457b434fd5973048a01e`.
Pre-fix ROM: `d96adbe4bacdaa574450f4aea29503e491ec4c8cb10a562a2327434a9f028b10`.

## Proven production overflow

Committed `spawn.pasm` allocated 90 ten-byte records at `$7E550F`, or 900 bytes
through `$7E5892`. `Bg_LoadScene` took the low byte of the catalog's u16 count;
`Spawn_Init` zero-extended it, calculated count * 10 in a 16-bit word, and copied
that many bytes using 16-bit X. No allocation check intervened.

| Records | Copied bytes | Overflow bytes | Out-of-bounds addresses |
|---:|---:|---:|---|
| 92 | 920 | 20 | `$7E5893–$7E58A6` |
| 94 | 940 | 40 | `$7E5893–$7E58BA` |

Easy 6A's live production `Stage_Load` writes all 920 bytes consecutively. Its
last twenty bytes are `900be004a801182d0000900b9803ac01452d001e`; these exactly
replace the first twenty sentinel bytes after the old allocation. This is not
an inference from gameplay appearing to work. The trace preserves every write.

The 92-record load overwrites:

| Address | Object |
|---|---|
| `$7E5893` | Spawn_ScratchKind |
| `$7E5894` | Spawn_ScratchHp |
| `$7E5895–96` | Spawn_GroupMin / Spawn_GroupMax |
| `$7E5897` | Spawn_Waiting |
| `$7E5898–99` | Spawn_PreClearHoldX |
| `$7E589A–9C` | Entity1/2/3_IsBoss |
| `$7E589D` | Spawn_ScratchEnemyCount |
| `$7E589E` | Spawn_ScratchMap |
| `$7E589F` | MapApply_Index |
| `$7E58A0–A2` | MapApply_PaletteBaseLo / Hi |
| `$7E58A3–A5` | MapApply_MapBaseLo / Hi |
| `$7E58A6` | MapApply_PaletteSlot |

A 94-record load also reaches roster/pickup scratch, saved selection state,
per-entity item identities, slot offset scratch, and Entity4/5 boss/item flags,
ending at Spawn_SavedCharSelectLoaded. Not every byte in that region is a named
object; the complete committed symbol-start inventory through `$7E58FF` is in
`bor_queue_s3_capacity.json`. No unused byte is treated as overflow permission.

## Single contract and WRAM strategy

`tools/queue_abi.json` defines ABI v1's ten-byte record, u8 count/index, u16
catalog count/copy length, and the `$7F9200–$7F9FFF` arena. `queue_abi.py` derives
the target limit and build allocation. The linker checks each actual packed
blob; `build_rom.py` writes `src/generated/queue_abi.{json,pasm}` from the
finalized selected catalog. Assembly consumes that generated contract.
Compiler lowering checks its byte count/record shape against the same ABI.
The pinned legacy encoder's size is mechanically checked, not silently trusted.

Capacity is **build-scoped**, not a new arbitrary round-number constant:

- Current production maximum: Easy 6A, 92 records; generated capacity 92.
- Complete Normal shadow maximum: Normal 6A, 107 records; capacity 107.
- Full original source queue-shape maximum: EXTRA, 184 records; capacity 184.
- Target ABI ceiling: 255 records, chosen by the count/index domain, not a stage.

The arena is 3,584 bytes. At the ceiling, 2,550 bytes hold records, followed by
32 verifier guard bytes; a fault byte is reserved at `$7F9FFF`. The immediately
preceding indexed frontpanel scroll buffer ends at `$7F9120`; the next cache
table begins at `$7FA000`. The include-closure/neighbor-extent check rejects
overlapping absolute ownership and changed indexed-buffer extents.

Current buffer: `$7F9200–$7F9597` (920 bytes), first guard byte `$7F9598`.
No scratch, boss, palette or other existing state moves. The retired 900-byte
queue range becomes unused. Queue payload allocation grows by 20 bytes net;
the new fault cell adds one byte. The 32-byte test guard is explicitly reserved
headroom, not gameplay state. EXTRA needs 1,840 bytes, 940 more than the old
queue allocation, and fits without moving neighboring caches.

## Width and failure behavior

The catalog count stays u16. Runtime count/index stay u8: 0..255, with 255 a
valid exhausted index after processing record 254. Iteration checks index <
count before use. Copy byte count and offset calculations are u16: maximum
2,550 bytes, with no bank crossing. The existing ten-byte stride remains ABI v1.
Wait/group/hole controls consume records normally; nothing is removed or split.

The loader checks the catalog high byte and compares the zero-extended runtime
count against generated capacity before copying. A mismatch sets `QUEUE_ERROR`
and halts; it does **not** clamp, clear a stage, or return to TITLE. Compiler
and linker reject bad counts first with `QUEUE_CAPACITY_EXCEEDED`, including
project, set, stage/path, packed count, capacity, required/available bytes and
target limit. Counts above 255 require a future ABI widening, never truncation.

## Resource results

Capacity PASS is independent of model/environment/content certification.
No unseen actor payloads or stages are published.

| Build/content | Packed records | Bytes | Queue-capacity result |
|---|---:|---:|---|
| Current production maximum / Easy 6A | 92 | 920 | Fits generated production build |
| Normal 5B shadow | 94 | 940 | Fits a 94+ record build; not the 92-record production image |
| Complete Normal maximum / 6A | 107 | 1,070 | Fits shadow build |
| Bonus EXTRA | 184 | 1,840 | Fits target; payload binding still blocked |
| TMNT accepted production subset maximum | 86 | 860 | Fits current build |
| TMNT complete source | Unknown | Unknown | Unbound queue constructs; maximum observed `at` count 99 in STREETS2 |
| He-Man complete source | Unknown | Unknown | Unresolved queue shape; maximum observed `at` count 34 in GUILE2 |

EXTRA has 184 authored records (166 spawns, 7 waits, 11 groups), no added hole
control, hence a 184-record ABI shape. This is exact shape analysis, not a fake
Crab/Lobster payload. TMNT/He-Man unknown controls and unpaired `at` directives
remain diagnostics; recognized records or `at` counts are not substituted for
a certified packed maximum. This batch does not implement their semantics.

## Reproduction and validation

```powershell
python tools/bor_compile/queue_capacity.py --output docs/bor_queue_s3_capacity.json
python build_rom.py --reuse-audio-from 28c71f99c51428bb3d18457b434fd5973048a01e
python -m unittest discover -s tools/bor_compile -p test_queue_capacity.py
python tools/verify/game_g15_s3_queue.py --output out/bor_compile_s3/after.json
python tools/rom_audit/check_width_directives.py
```

The default full audio-build path has a pre-existing stale explorer summary;
regeneration exceeds its 500,000-state limit on Easy 5B. It remains unfixed.
The explicit non-audio rebuild path instead verifies 121 Git-canonical tracked
audio inputs and every accepted encoded PCM/SFX hash (25 tracks, 8 banks).
It refuses changed inputs or outputs. This is reuse of proven identical audio,
not a claim that the stale explorer passed or a weakening of the default gate.

Final proof artifacts record the new ROM hash, complete queue-copy traces for
Easy 6A and ordinary Easy 1B, guard preservation, and the unchanged MSU hash.
`bor_queue_s3_live.json` contains the compact, revalidated before/after evidence
and hashes of the full traces. Seven queue-only unit/integration tests pass;
all 24 golden queues remain byte-identical. Both final live copies pass
(Easy 6A: 92/920; Easy 1B: 35/350), including every write in order and intact
32-byte guards. The compiled-symbol allocation check and width audit pass
(zero new width findings; 187 pre-existing baselines).
The production bank-0 guard passes with two bytes remaining before the fixed
NMI entry; future code growth must respect that separate ROM-layout limit.

Final ROM SHA-256:
`0337ad98d9262616caac2efd6208baf71da59a973a38899a0e9ac064b4d8ebb6`.
Final unchanged MSU SHA-256:
`e7fe744af2928939f926a1c9121f6ac9e7f1d378533b95366e4afefd6bfe90af`.

No campaign replay, stage content changes, map/Z work, actor adapters, or
Normal/Bonus publication belongs to S3.
