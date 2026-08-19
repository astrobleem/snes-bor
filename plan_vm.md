# plan_vm.md — the OpenBOR Build 4086 script VM on this engine

> **READ THIS BANNER BEFORE ANYTHING ELSE.**
>
> This plan builds a **bytecode interpreter** for `openborscript`, the embedded
> scripting language real OpenBOR mods are written in. It is a *compatibility
> substrate*.
>
> **It is NOT the path to a playable, shippable game, and Gates 0–5 produce
> zero user-visible change.** You can finish Gate 5 and the ROM will look and
> play exactly like it does today. If your goal is "a complete Beats of Rage
> game with menus, stages, and a win condition," you want **`plan_game.md`**,
> not this file. Nothing in `plan_game.md` depends on this VM.
>
> Do not let anyone (including yourself, three gates from now) restate this
> plan as "the VM enables menus/levels/progression later." It does not. Those
> are separate, independent work, planned separately, and mostly gated on a
> font/text renderer that does not exist yet.
>
> **Why build it at all, then?** Because today `tools/bg_converter/` can only
> read the *declarative* keywords out of a BOR level (`background`, `panel`,
> `spawn`, `at`, `order`). Anything a mod expresses as actual script —
> conditional waves, bosses with scripted phases, cutscenes, custom win
> conditions — is discarded at convert time and cannot be expressed as a
> convert-time table. The VM is what makes those runnable. That is its whole
> value proposition. It is a real one, and it is not urgent.

---

## How to use this plan

Read §0 in full **once**, then work one gate per change, top to bottom, in order.
Gate 0a is the first one; it is §1.

Everything you need is in this file or in a committed file it names. You should
not need to consult a person, another model, or the internet to finish a gate.
Specifically:

- **Missing constant?** §0.8 defines every `VMSTAT_*`, `VMERR_*`, and WRAM
  address. It is the authority, not the zip.
- **How do I write 65816 for this project?** §0.6 (toolchain bugs) and §0.9
  (file conventions). Both are inline on purpose — you will not go read
  `CLAUDE.md` mid-gate.
- **Stuck?** §0.10, in order, before escalating to anything.
- **How do I know the gate is done?** §0.7 for the criteria that apply to every
  gate, plus the gate's own "Definition of done" checklist.

Two things are worth reading end to end before you touch anything, and they are
short: `src/core/spawn.pasm` (the template §1 asks you to copy) and
`build_rom.py`'s `check_spawn_constants` (the template §1 asks you to mirror).

---

## §0 — Ground truth measured for this plan (2026-08-16)

Everything in this section was **measured this session**, not assumed. Do not
re-derive it, but do re-measure anything marked *(re-check each gate)* before
depending on it.

### §0.1 Where the source material lives

**Everything the gates actually need is committed to `tools/verify/vm_fixtures/`.**
You do not need the zip to start:

| Committed file | What it is |
|---|---|
| `gate0_program.json` | Gate 0 fixture + expected final state — this *is* the gate |
| `gate0_module.bin` | Same fixture, packed as a revision-1 module (184 B) |
| `gate0_expected_slots.bin` | Expected final slot image (40 B) — Gate 0's ground truth |
| `run_gate0_reference.py` | Host oracle (path-adjusted for this location) |
| `opcode_manifest.csv` | All 48 opcodes, operands, semantics — this is the ABI |
| `bor_vm_opcodes.pasm` | 48 opcode constants — paste into the build as-is |
| `validate_fixtures.py` | Cross-checks all of the above against each other |

**Run `python tools/verify/vm_fixtures/validate_fixtures.py` before trusting any
Gate 0 failure** (expects `FIXTURES: PASS`). It verifies the module header
against `FORMAT.md`, the stored CRC32, every instruction record against the JSON,
and both slot images — with no engine involved. If it fails, the fixture is
wrong, not your interpreter. It passed when vendored (2026-08-16), including the
CRC; that was the first time anything in the package had been checked at all.

**What is *not* in that directory, and where it is instead:** the VM's status
codes, fault codes, and WRAM addresses. `bor_vm_opcodes.pasm` is the 48 opcode
numbers and nothing else. **§0.8 of this file defines all of the rest, ready to
paste.** Do not go looking for them in the zip — its README lists status *names*
with no numeric values at all, which is exactly the kind of gap that turns into
two incompatible enumerations three gates apart.

The remaining design documents stay in `openbor4086_sa1_bootstrap.zip` in the
repo root (untracked, created 2026-08-03 by an earlier session). Extract and read
them — they are genuinely good research:

```bash
unzip -o openbor4086_sa1_bootstrap.zip -d <scratch>/
```

| File in the zip | What it is | Trust level |
|---|---|---|
| `README.md` | Full design contract, 12 sections | High — read it all |
| `FORMAT.md` | Binary module format, revision 1 | High — implement as written |
| `src/bor_vm_core.pasm` | ~800-line interpreter scaffold | **Low — see §0.5** |

`IMPLEMENTATION_CHECKLIST.md`'s every box is unchecked. Nothing in that package
was ever assembled or run. Treat it as a design document, not as code.

### §0.2 Three deliberate deviations from the bootstrap package

The package was written against a *generic* SA-1 project. This project has
constraints it did not know about. **These three deviations are decided. Do not
re-litigate them mid-implementation.**

---

**Deviation 1 — the VM runs on the S-CPU, not the SA-1.**

The package (and `README.md`'s architecture section) assumes SA-1. That is wrong
*here*, for one discriminating reason: **the SA-1 in this project is not idle.**
`sa1_main` (`src/main.pasm:51`) runs a persistent, *blocking* recomposite loop —
it redraws 21 blits into the BW-RAM canvas, re-arms CC-DMA, then spins on an
I-RAM mailbox byte (`$3025`) waiting for the S-CPU's pump to consume the canvas,
forever. There is no yield point. Putting the VM on the SA-1 means restructuring
that loop *and* designing a cross-CPU mailbox *before* a single opcode executes.

Running on the S-CPU instead costs nothing that matters at these gates:
- ~107 KB of free WRAM is S-CPU-native (§0.4) — no BW-RAM windowing, which is a
  documented recurring bug class in this project (`CLAUDE.md`, "getting the wrong
  window … is a recurring class of bug here, not a one-off").
- The VM is called once per frame from `scpu_main_loop` with a cooperative
  opcode budget, exactly like `Core_Screen_Play` / `Core_Oop_Play` already are.
- Game-logic scripts run a few hundred opcodes per frame, not millions.

**Escape hatch:** if Gate 6 *measures* the interpreter over its frame budget,
SA-1 offload becomes its own later gate with its own mailbox design (§9). It is
not a mid-flight pivot, and "the design doc said SA-1" is not a reason to make it
one.

---

**Deviation 2 — the module ships in `bor.msu` and is read into WRAM at boot, not
`.incbin`'d into ROM.**

This is not a preference; it copies a decision this project already made and
shipped. `core/spawn.pasm` (Phase 13) put the spawn table in `bor.msu` for
exactly this reason, quoted from `README.md`:

> *"The table ships via `bor.msu` … not a ROM `.incbin` — this codebase has no
> proven pattern for indexed ROM reads, and CLAUDE.md documents a confirmed
> Poppy bug in exactly that addressing mode, so the table is read sequentially
> into WRAM at boot instead, then indexed there using the same `.l Label,x`
> pattern already proven throughout the engine."*

Copy that template wholesale, including its build-time guard (§1).

**Module transport itself still goes through WRAM/`bor.msu`, per the spawn-table
precedent above** — that decision rests on the *indexed-ROM-read* Poppy bug
(`.l Label,x` against a ROM `.incbin`), which is a different bug and is not
addressed by anything below.

**Correction (2026-08-19): the "high-bank ROM is a trap" framing that used to
sit here was stale and has been removed.** It cited "Poppy's confirmed
cross-bank label mis-resolution (bug 9)" — that bug is fixed in the fork (see
CLAUDE.md's toolchain table, and re-confirmed this session with a fresh
two-bank repro: `jsl` in both directions, a `.dw` pointer table, and
back-and-forth `.bank` switching all resolved the correct bank byte and landed
bytes at the correct LoROM file offset). This means §0.3's 7168-byte ceiling
is a real constraint on where `main.pasm`'s *own* bank-0 code sits today, but
it is not a hard ceiling on VM code in general — a future gate that outgrows
bank 0 can put overflow code in another bank and reach it with an ordinary
`jsl`/`jml`, the same way any other cross-bank call would work. Nothing below
in §0.3 needed to change as a result (Gate 0 fits in ~5.7 KB of the existing
budget with room to spare), so this is recorded here for whichever future gate
first needs to decide whether to spill into a second bank, not acted on now.

---

**Deviation 3 — record fetch uses `.l VmCode_Wram,x`, not the scaffold's
`lda [VM_CODE_PTR],y`.**

The scaffold keeps VM state in Direct Page and fetches records through a
DP-based long-indirect pointer. Both halves are wrong for this codebase:

- **DP is already spoken for.** `core/oop.pasm` re-points the DP register per
  entity instance before calling `Init`/`Play`. A VM that also owns DP has to
  save/restore it around every entry and never be reachable from inside an OOP
  dispatch. That is a live footgun for no benefit.
- **`.l Label,x` is the proven pattern here.** Every `src/core/*.pasm` module
  indexes WRAM this way, and `core/spawn.pasm` indexes a *table read from
  `bor.msu`* this way — the exact thing the VM needs.

So: VM state lives at fixed absolute `$7E`/`$7F` addresses like every other core
module, and record fetch is `lda.l VmCode_Wram,x` with `X = IP*8 + field`.

Confirmed against `E:\gh\snesmanual\fullsnes.txt` this session:
- Absolute-long indexed exists **only** in the `,X` form (`Base+1F`,
  `nnnnnn,X`; e.g. `BF`=LDA, `9F`=STA). There is **no** `nnnnnn,Y` opcode —
  which is why `.l Symbol,y` must never appear (Poppy accepts it and silently
  emits a wrong 3-byte absolute,Y instruction).
- X is 16-bit, so the reachable window is 64 KB from the base label. At 8 bytes
  per record that is 8192 records — the format's own revision-1 cap. Long
  addressing is linear across the full 24-bit space, so a base in `$7E` indexing
  past `$7EFFFF` into `$7F` is fine.

### §0.3 ROM budget — the constraint most likely to kill this

**All VM code goes in `$9000`–`$AC00` in bank 0. It is 7168 bytes
(`$AC00 - $9000 = $1C00`) and it is all you get.**

The full free gap in bank 0 is `$8C60`–`$AC00` (8096 bytes), but **it is shared
and it is already divided**:

| Range | Size | Owner |
|---|---|---|
| `$8C60`–`$9000` | 928 B | `core/text.pasm` — `plan_game.md` phase G1 |
| **`$9000`–`$AC00`** | **7168 B** | **this VM** |

`plan_game.md`'s font/text renderer has priority because it is on the critical
path to a shippable game and this VM is not. **Do not start the VM at `$8C60`.**
If both plans proceed independently and each assumes it owns the whole gap,
Poppy will silently truncate one into the other — and because the overflow lands
on `LoadAudioData` at `$AC00`, it presents as an *audio* bug with no visible
connection to either feature.

Measured region occupancy (re-check each gate, §0.6):

| Region | Contents | Free after |
|---|---|---|
| `$8000`–`$8800` | SA-1 entry | 1477 |
| `$8800`–`$8C00` | TAD driver | 141 |
| **`$8C00`–`$AC00`** | **anim tilemaps (96 B, end `$8C60`) — then FREE** | **8096** |
| `$AC00`–`$B000` | `LoadAudioData` | 1017 |
| `$B000`–`$C100` | audio blob | 972 |
| `$C100`–`$FC00` | **all `core/*.pasm` + game code** | **1913** |
| `$FC00`–`$10000` | S-CPU boot, NMI/IRQ | 144 |

Two things follow, and both are load-bearing:

1. **The VM cannot go in `$C100`–`$FC00`.** 1913 bytes is not enough, and that
   region is where every future non-VM feature also wants to live. New VM code
   goes in a new `src/core/vm/*.pasm` set `.include`d under a **new `.org $9000`
   block**, not appended to the existing `$C100` include list.
2. **`.org` regions silently truncate on overflow** (`CLAUDE.md`). If VM code
   runs past `$AC00` it corrupts `LoadAudioData` and presents as an *audio* bug —
   a symptom with no obvious connection to the VM. This is why §0.6 makes a
   region-occupancy check a mandatory exit criterion for every single gate.

**Measured size of the stubbed scaffold: 1162 bytes** (dispatcher + all 48
handler entry points + all helper stubs, top label `vm_return`). That leaves
**~6006 bytes** of the VM's 7168 for real helper implementations.

(Note the measured-vs-quoted trap this number already sprang once: the top
*symbol* in that region used to be `$8C30` while the 96-byte `.incbin` after it
really ended at `$8C60`, because `.incbin` contributed nothing to the layout
pass. That is fixed (poppy#384) and `.sym` now accounts for blob bytes, but the
habit is still the right one: **size from the end of the data, not from the top
label.** Always size this region from `$8C60`.)

(Also verified 2026-08-18, after the assembler fixes moved a 1536-byte blob out
of this window and then back out again: `$8C60`-`$ABFF` really is 8096
contiguous free bytes in the shipping ROM. Measure it yourself with a zero-run
scan over `src/main.bin` before trusting this line — it is the one number the
whole VM budget rests on.)

Projected budget against the **7168-byte ceiling**. **Only the scaffold row is
measured — every other row is an estimate. Replace each with the real number
from the occupancy check when that gate lands, and never treat a projection as
a reason to skip your own check.**

| Gate | Adds | Running total | Measured? |
|---|---|---|---|
| scaffold | 1162 | 1162 | **yes — measured** |
| 0 | module load/validate, slot copy, 32-bit ADD, EQ, truth, trace | ~1700 | estimate |
| 1 | remaining handlers/faults (mostly already in the 1162) | ~1800 | estimate |
| 2 | 32-bit MUL/DIV/MOD/shifts/compares/unary | ~3500 | estimate |
| 3 | call frames, PARAM/JUMPR/RET, native table | ~3900 | estimate |
| 4 | strings: intern, refcount, concat, compare | ~5100 | estimate |
| 5 | decimals, **Q16.16 only** | ~5700 | estimate |

At the projected ~5700 against a 7168 ceiling the margin is roughly **300–1400
bytes**, not comfortable. **Gate 4 (strings) is where the budget actually gets
decided** — it is the largest single estimate and the least certain. If Gate 4
comes in materially over ~1200 bytes, stop and re-plan the remaining gates
rather than pushing into `$AC00`.

**Q16.16 is not a preference, it is a budget decision.** The strict binary64
profile needs software float conversion, arithmetic, comparison *and*
formatting; that does not fit in the remaining margin and would force the bank
relocation this plan is designed to avoid. Stamp `numeric_profile = 0` (Q16.16)
in the module header and make the host oracle quantize to match. If a future mod
genuinely needs binary64, that is a re-plan, not a stretch goal.

### §0.4 WRAM budget and the VM memory map

Measured: the engine's WRAM high-water mark is `SpawnTable_Wram = $7E5507` plus
the spawn table itself (~196 bytes for the shipped level), ending near `$7E55CB`.
`WramBuffer` occupies `$7E2000`–`$7E4FFF`. WRAM is 128 KB at `$7E0000`–`$7FFFFF`
(fullsnes L389), so everything from ~`$7E5600` up is free — about 107 KB.

Use this map. Bank-align it so a later `X`-indexed read never has to think:

```
addr      size    region
--------  ------  ----------------------------------------------------------
$7E6000   32768   VmCode_Wram    module image: header + instruction records.
                                 4096-record cap (revision 1 allows 8192; the
                                 lower cap is what keeps this inside 32 KB).
                                 Ends $7EDFFF.
$7EE000      16   VmGuardLo      guard bytes, pattern $A5 (§0.7)
$7EE010    8192   VmSlots_Wram   1024 mutable variant slots x 8 B.
                                 Ends $7F000F.
  ($7F0010-$7F00FF is deliberate slack — do not allocate it without redrawing
   this table; it is what makes the two banks' contents independently movable.)
$7F0100     768   VmFrames_Wram  64 call frames x 12 B (Gate 3). Ends $7F03FF.
$7F0400    4096   VmStrPool_Wram dynamic string pool (Gate 4). Ends $7F13FF.
$7F1400     128   VmTrace_Wram   (IP,opcode) ring, 32 x 4 B. Ends $7F147F.
$7F1480      16   VmGuardHi      guard bytes, pattern $5A
$7F1500      20   VmState_*      status, error, IP, budget, counts, scratch
```

**Check the arithmetic before you move anything in this table.** An earlier draft
of this plan put `VmGuardLo` at `$7EFF00`, which is *inside* a 1024-slot array
based at `$7EE000` — the guard would have been silently overwritten by ordinary
slot writes to slots 1008–1023 and reported a corrupt-memory failure that was
really a map bug. Every region above has its end address written out for exactly
that reason. Add yours the same way.

`VmState_*` cells are plain absolute `$7F15xx` addresses, one per line, exactly
like `core/spawn.pasm`'s own `Spawn_Index` / `Spawn_Scratch*` block. Do not use
Direct Page (§0.2, deviation 3).

**NMI hazard — this has shipped as a real bug here once already.** Every
`VmState_*` cell, both guard regions, and `VmTrace_Wram`'s head index must be
explicitly zeroed **before `Core_Nmi_Init` enables NMI** in `scpu_boot`, not
merely "early in boot." NMI is non-maskable and `sei` does not protect against
it; see project memory `boot_nmi_race_before_oam_init` for the session this cost.
If any per-frame NMI-driven routine ever reads VM state, this applies to that
state too.

### §0.5 The scaffold cannot be pasted in as-is — measured, not predicted

`src/bor_vm_core.pasm` **does not assemble**. Assembling it unmodified produces a
wall of hard errors (measured this session; the errors are branch-range errors
and so are independent of which `.org` you use):

```
vmsize.pasm:673:5: error: Branch target out of range (-334 bytes, must be -128 to +127)
vmsize.pasm:774:5: error: Branch target out of range (-957 bytes, must be -128 to +127)
vmsize.pasm:799:5: error: Branch target out of range (-994 bytes, must be -128 to +127)
... 37 sites total
```

The cause: nearly every handler ends `jsr <helper>` / `bcs vm_fault_from_a`, and
`vm_fault_from_a` sits hundreds of bytes away. **37 branch sites** need the
invert-and-`brl` workaround (or a local trampoline near each cluster) before the
file assembles at all. With that applied it assembles clean at 1162 bytes.

Note carefully: these particular errors *were* reported. That is the **less**
dangerous case. `CLAUDE.md` documents that a conditional branch past ±127 bytes
can also assemble **with no error whatsoever** and hang the CPU at runtime. Do
not conclude from "it built clean" that no branch is over-range.

Beyond branch range, the scaffold also violates project conventions in ways that
will silently miscompile here:
- **No `sep`/`rep` width directive at branch targets** (Poppy's linear width
  tracking — still live, §0.6 item 1). This is the one that will actually bite.
  (Its missing `nop` label guards, by contrast, are now fine: that bug is fixed.)
- **DP-based state and `[dp],y` fetch** (deviation 3).
- **`.snes` / bank directives** that don't match this project's single-`.bank 0`
  layout.

Treat the scaffold as a **structural reference for the dispatcher shape and the
handler exit contract**, and retype it into this project's conventions. Do not
copy-paste it.

### §0.6 The Poppy checklist — apply to every line of new assembly

Inline here on purpose, because you will not go read `CLAUDE.md` mid-gate.

**Re-measured 2026-08-18 against `E:\gh\poppy-astrobleem` HEAD `a7a760e`, with
fresh minimal repros. Most of this toolchain's historical silent-miscompile bugs
are FIXED.** That materially changes what you have to write. The rules below are
split accordingly, and **do not add defensive scaffolding for anything in the
second list** — the `nop` guards throughout `src/core/*.pasm` are historical, not
a pattern to extend.

**Still live — exactly one, and you must handle it.** The other five were fixed
in the fork on 2026-08-18 (`272f7ea`, `08fe283`); see the table below.

1. **Open every routine, and every branch-target label, with an explicit
   `sep #$20` / `.a8` (or `rep #$31` / `.a16 .i16`) width directive**
   ([poppy#386](https://github.com/TheAnsarya/poppy/issues/386)). Poppy still
   tracks accumulator width linearly, not along control flow, so a label reached
   by a branch that jumps over a `rep`/`sep` gets its following `lda #`/`cmp #`
   mis-sized and every byte after it misaligns. Measured: `cmp #$02` at such a
   label assembles as `c9 02 00` — three bytes — and the trailing `00` decodes as
   a phantom `BRK`. **An explicit `.a8` after the label fixes it** (measured:
   `c9 02`). Apply it unconditionally rather than reasoning about whether it is
   needed; it is a runtime no-op when the width already matches. This one is
   still open on purpose — it needs a new analysis pass with a false-positive
   budget, not a one-line reconciliation between two existing passes.

   **You do not have to remember this.** `python tools/rom_audit/check_width_directives.py`
   (also run by `audit_all.py`) fails on any NEW branch/jump-target label that
   reaches a width-dependent immediate without a directive. Run it before every
   gate's exit criteria. A 48-way opcode dispatcher is 48 branch targets, so
   this check is aimed squarely at the code you are about to write: put
   `sep #$20` / `.a8` (or `rep #$30` / `.a16 .i16`) at the top of every handler,
   unconditionally. If the check fires, add the directive — never add a line to
   `check_width_directives_baseline.txt` to silence it.

**Fixed — do not write workarounds for these:**

| Historical bug | Status now |
|---|---|
| `jsl` sized 3 / emitted 4 → cumulative label drift | **Fixed.** Labels after three `jsl`s land exactly right. **New code does not need `nop` guards before labels.** |
| `bcs`/`bcc` past ±127 assembling silently | **Fixed.** All conditional branches *and* `bra` now error, with the correct line number. |
| `.org` overflow silently truncating into the next region | **Fixed.** Now errors: "overlaps previously emitted bytes". |
| `stz.l`, `ldx.l`/`ldy.l`, `cpx.l`/`cpy.l`, `.l Symbol,y` | **Fixed.** All are hard errors now ("no long form for this mode"). |
| Standalone `.dw` data table resolving to garbage | **Fixed.** Resolves correctly. |
| Branch to a dot-prefixed local label silently deleted | **Fixed.** Dot-locals work. |
| Macro invocations sized 0 bytes in the estimation pass | **Fixed.** |
| `.include` errors reported under the wrong filename | **Fixed.** |
| Cross-bank `jsl` resolving with bank `$00` | **Fixed** in codegen, and in the `.sym` export as of `272f7ea` (poppy#387). |
| An unknown mnemonic silently ignored (poppy#382) | **Fixed** `272f7ea`. A typo'd instruction is now a hard error naming the token. It used to assemble clean and emit nothing. |
| Macros emitting zero bytes (poppy#383) | **Not a bug — the docs were wrong.** Macros work correctly, including inside branch-skipped code. Invocations are `@Name`, not `%Name`; parameters are bare names, not `\param`. **You may use a macro for the 48-handler dispatcher.** |
| `.incbin` sized 0 bytes in the layout pass (poppy#384) | **Fixed** `272f7ea`. Labels after a blob resolve correctly and the `.org` overlap check sees blobs now. |
| `sta.w $7E1234,x` emitting a truncated long instruction (poppy#385) | **Fixed** `272f7ea`. Now a hard error. Write `.l` or bare anyway — see the 65816 facts below. |
| `-name` lexed as a label, dropping the subtraction in `#$ffff-SIZE` and `#End-Start` (poppy#388) | **Fixed** `272f7ea`. Length expressions are usable. |

**Still true, but as 65816 facts rather than Poppy bugs:**

4. **Indexed WRAM access uses `.l` or bare, never `.w`.** `.w` on a bank-`$7E`
   symbol is a genuinely wrong 16-bit address. Poppy rejects it now rather than
   emitting a truncated instruction (poppy#385), so this is a constraint on what
   you write, not a silent trap.
5. **Long addressing is indexed by `X` only**; there is no `nnnnnn,Y` opcode
   (verified in fullsnes, §0.2). Poppy now rejects it, so this is a constraint on
   how you lay out loops, not a trap.
6. **Conditional branches are ±127 bytes.** Poppy errors now instead of failing
   silently, but you still have to structure code so it does not happen — see
   §0.9 item 7 for the trampoline shape.
7. **No `@`-local labels in anything `.include`d.** No `src/core/*.pasm` file uses
   them; match that convention.

**If you hit a silent miscompile that is on neither list**, that is a genuinely
new finding: build a minimal repro (a dozen lines — `.snes`, `.bank 0`,
`.org $8000`, assemble, dump the bytes), confirm it, and record it. This section
was rewritten from exactly that process and it took about ten minutes. Then
file it upstream at https://github.com/TheAnsarya/poppy/issues with the repro
inline, the way poppy#382–388 are written — then fix it in the fork at
`E:\gh\poppy-astrobleem` with a regression test in
`src/Poppy.Tests/Semantics/SilentMiscompileRegressionTests.cs`.

### §0.7 Universal exit criteria — every gate, no exceptions

A gate is not done until **all** of these pass. Run them in this order.

```bash
python build_rom.py                          # never skip; no incremental step
python tools/rom_audit/check_label_drift.py  # exits nonzero on drift
python tools/rom_audit/audit_all.py          # -> ALL CHECKS PASS
python tools/verify/vm_gate<N>.py            # -> GATE <N>: PASS
```

Plus the full existing regression suite, which must stay green — the VM is
additive and must not disturb anything:

```bash
python tools/verify/phase5.py phase6.py phase7.py phase8.py phase9.py \
       phase11_damage.py phase12_roster.py    # run individually
```

(**All seven pass, `phase8.py` included.** An earlier revision of this plan said
`phase8.py` was known-stale and must not be fixed — it had been hard-failing on
its own precondition since Phase 14 swapped in a streaming level. It was repaired
in commit `a71e26c` and now derives its world bounds from whatever level ships.
Treat a `phase8.py` failure as a real regression like any other.)

**Plus the region-occupancy check** — mandatory, because `.org` truncation is
silent and presents as an audio bug:

```bash
python - <<'EOF'
import re
syms=[(int(m.group(2),16),m.group(3))
      for l in open('src/main.sym',encoding='utf-8-sig')
      if (m:=re.match(r'([0-9A-F]{2}):([0-9A-F]{4})\s+(\S+)',l.strip()))
      and m.group(1)=='00']
cand=[a for a,_ in syms if 0x9000<=a<0xAC00]   # VM owns $9000-$AC00 only
top=max(cand) if cand else 0x9000      # empty until Gate 0a lands a symbol here
print(f'VM region top ${top:04X}, {0xAC00-top} bytes free before $AC00')
assert top < 0xAB00, 'VM REGION OVERFLOW RISK — stop and relocate'
# text.pasm owns $8C60-$9000; the VM must not have leaked below $9000
low=[a for a,n in syms if 0x8C60<=a<0x9000 and n.lower().startswith('vm')]
assert not low, f'VM symbols below $9000 collide with core/text.pasm: {low}'
print('region OK')
EOF
```

**Plus the guard-byte check** (§0.4): `VmGuardLo`/`VmGuardHi` must still read
their fill patterns after the gate's test run. A changed guard byte is a failed
gate even if every other assertion passes.

**Stop rule.** Do not begin Gate N+1 in the same change as Gate N. Commit at the
gate boundary with the gate name in the message, and update this file's status
line for that gate. This rule comes from the bootstrap package and it is a good
one — these gates build on each other, and a half-finished Gate 2 sitting under a
started Gate 3 is unreviewable.

**Ground-truth rule.** Every gate script compares against data **the engine did
not produce** — the fixture `.bin` files, the host oracle's output, the packed
`bor.msu`. Never assert on the VM's own status bytes alone. Phase 7 is the
cautionary tale: TAD reported `PLAYING` at full volume for as long as it was
faithfully loading pure zeros, and every engine-visible byte read perfect.

**Gate-line rule.** Every gate script's last line is `GATE <N>: PASS` or
`GATE <N>: FAIL`, and the process exits 0 / 1 to match. `tools/verify/_harness.py`'s
`Reporter` prints `PHASE <n>: ...`, which is the wrong word. **Add a `kind`
parameter to it once, in the Gate 0a change** — it is a two-line edit and every
later gate depends on it:

```python
class Reporter:
    def __init__(self, phase_number, kind='PHASE'):
        self.phase_number = phase_number
        self.kind = kind
        ...
    def finish(self):
        ...
        print(f'{self.kind} {self.phase_number}: {"PASS" if overall else "FAIL"}')
```

Then `Reporter('0a', kind='GATE')` prints `GATE 0a: PASS`. Existing `phaseN.py`
scripts are unaffected because `kind` defaults to `'PHASE'`.

---

## §0.8 — Constants and enums: nothing committed defines these, so define them here

**`VMSTAT_*` and `VMERR_*` do not exist in any committed file.** `bor_vm_opcodes.pasm`
is the 48 opcode numbers only. The status names live in the zip's `README.md` §3 with
**no numeric values at all**, and the error values live in its §9. Both are reproduced
below so you never have to open the zip for them.

**Create `src/core/vm/vm_consts.pasm` with exactly this content, first thing, before
any other VM file.** Every later gate, and every gate *script*, reads its values from
this one file.

```
; ============================================================================
; core/vm/vm_consts.pasm -- VM status codes, fault codes, and WRAM map.
; Equates only, no code. .include'd FIRST inside main.pasm's .org $9000 block
; so every later vm/*.pasm file sees these names.
;
; If main.pasm itself ever needs one of these, move that single constant to
; main.pasm ABOVE its .org $C100 include block instead -- main.pasm has twice
; been bitten by a constant used textually before the .include that defined it
; (see its own notes near "declared here, textually before core/nmi.pasm's
; .include").
; ============================================================================

; --- Status. Held in VmState_Status as ONE byte. ---
; UNINIT is deliberately 0 so that "boot zeroed this WRAM and the loader never
; ran" is distinguishable from "the loader ran and succeeded". Never renumber
; READY to 0.
VMSTAT_UNINIT   = 0
VMSTAT_READY    = 1
VMSTAT_RUNNING  = 2
VMSTAT_YIELDED  = 3
VMSTAT_DONE     = 4
VMSTAT_FAULT    = 5

; --- Fault codes. Held in VmState_Error as a 16-bit word.
; $0001-$000F are the bootstrap package's own recommended values (its README
; section 9) -- do not renumber them, the gate fixtures use them.
VMERR_NONE            = $0000
VMERR_BAD_OPCODE      = $0001   ; opcode value >= 48
VMERR_FIELD_OPCODE    = $0002   ; opcode 7 (FIELD) -- always a fault, never a no-op
VMERR_EXPLICIT_ERR    = $0003   ; opcode 15 (ERR)
VMERR_BAD_SLOT        = $0004
VMERR_BAD_TYPE        = $0005
VMERR_DIV_ZERO        = $0006
VMERR_CALL_DEPTH      = $0007
VMERR_NO_CALL_FRAME   = $0008
VMERR_BAD_CALLSITE    = $0009
VMERR_BAD_NATIVE      = $000A
VMERR_STRING_POOL     = $000B
VMERR_STRING_OVERFLOW = $000C
VMERR_BAD_JUMP        = $000D   ; IP outside 0..instruction_count-1
VMERR_BAD_MODULE      = $000E   ; header validation failed (Gate 0a)
VMERR_BUDGET_PROTOCOL = $000F   ; opcode budget exhausted without a yield
VMERR_UNIMPLEMENTED   = $0010   ; opcode is a VALID ABI value but this gate
                                ; has not implemented it yet. See the note
                                ; below -- this is NOT the same as $0001.

; --- WRAM map (plan_vm.md 0.4). Absolute addresses, never Direct Page.
; End addresses are written out on purpose -- see 0.4's note about the guard
; region that was originally placed inside the slot array. ---
VmCode_Wram     = $7E6000   ; 32768 B, ends $7EDFFF
VmGuardLo       = $7EE000   ; 16 B of $A5
VmSlots_Wram    = $7EE010   ; 1024 slots x 8 B = 8192 B, ends $7F000F
VmFrames_Wram   = $7F0100   ; 64 frames x 12 B = 768 B   (Gate 3)
VmStrPool_Wram  = $7F0400   ; 4096 B string pool         (Gate 4)
VmTrace_Wram    = $7F1400   ; 32 x 4 B = 128 B           (Gate 0)
VmGuardHi       = $7F1480   ; 16 B of $5A
VM_GUARD_LEN    = 16
VM_GUARD_LO_FILL = $A5
VM_GUARD_HI_FILL = $5A
VM_CODE_MAX      = 32768
VM_INSTR_MAX     = 4096
VM_SLOT_MAX      = 1024

; --- VmState_* scalars. One per line, plain absolute addresses, exactly like
; core/spawn.pasm's Spawn_Index / Spawn_Scratch* block. ---
VmState_Status      = $7F1500   ; .db -- VMSTAT_*
VmState_Error       = $7F1501   ; .dw -- VMERR_*
VmState_Ip          = $7F1503   ; .dw -- current instruction index
VmState_ErrorIp     = $7F1505   ; .dw -- IP at time of fault
VmState_ErrorOpcode = $7F1507   ; .db -- opcode at time of fault
VmState_Budget      = $7F1508   ; .dw -- opcodes remaining this frame
VmState_FrameTop    = $7F150A   ; .dw -- call-frame depth        (Gate 3)
VmState_TraceHead   = $7F150C   ; .db -- trace ring write index  (Gate 0)
VmState_InstrCount  = $7F150D   ; .dw -- copied from header at load
VmState_SlotCount   = $7F150F   ; .dw -- copied from header at load
VmState_Scratch0    = $7F1511   ; .dw
VmState_Scratch1    = $7F1513   ; .dw
VM_STATE_FIRST      = $7F1500
VM_STATE_LAST       = $7F1515   ; exclusive -- zero [FIRST,LAST) at boot
```

**Why `$0010 VMERR_UNIMPLEMENTED` is a separate code from `$0001
VMERR_BAD_OPCODE`, and why you must not merge them.** The committed host oracle
`run_gate0_reference.py` faults with `0x0010` on any opcode it does not handle,
and with `0x0002` on `FIELD`. It never emits `0x0001`, because Gate 0's fixture
contains no out-of-range opcode. The package's README, meanwhile, calls `$0001`
`VMERR_BAD_OPCODE`. Both are right about different things:

- `>= 48` — not an ABI value at all — is `$0001 VMERR_BAD_OPCODE`.
- `< 48` but not implemented at the gate you are on is `$0010 VMERR_UNIMPLEMENTED`,
  which is what the oracle already emits.

Implement both. Gate 1 (§3) is where `VMERR_UNIMPLEMENTED` stops being reachable
for values `0..47`, and its gate table asserts exactly that.

**Gate scripts must read these values out of `vm_consts.pasm`, never hardcode
them.** `_harness.py`'s `pasm_constant()` only searches `src/main.pasm`, so add
its sibling once, in the Gate 0a change:

```python
def pasm_constant_in(relpath, name):
    """Same contract as pasm_constant(), for any .pasm file under the repo
    root -- e.g. pasm_constant_in('src/core/vm/vm_consts.pasm', 'VMSTAT_READY').
    Verification scripts must never hardcode engine layout values; see
    pasm_constant()'s docstring for the phase5.py incident that rule came from."""
    path = os.path.join(repo_root_from(None), *relpath.split('/'))
    pattern = re.compile(r'^\s*' + re.escape(name) + r'\s*=\s*(\$?[0-9A-Fa-f]+)\s*(?:;.*)?$')
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = pattern.match(line)
            if m:
                raw = m.group(1)
                return int(raw[1:], 16) if raw.startswith('$') else int(raw, 10)
    raise KeyError(f'constant {name!r} not found in {path}')
```

## §0.9 — Conventions for every VM source file

These are not style preferences. Each one is a bug this project has already paid
for.

1. **`jsr`/`rts`, never `jsl`/`rtl`.** All VM code is in bank 0 alongside its
   callers, so long calls buy nothing — and every `jsl` you avoid is one byte of
   Poppy label drift (§0.6 item 2) you never accrue. `Vm_Load` is called by
   `scpu_boot`, which is bank 0. `core/spawn.pasm` is `jsr`/`rts` for the same
   reason; match it.
2. **New files go in `src/core/vm/`**, `.include`d inside main.pasm's **new
   `.org $9000` block** — never appended to the `.org $C100` list (§0.3).
3. **`.include` order inside that block is fixed:** `vm_consts.pasm` first
   (equates), then `bor_vm_opcodes.pasm`, then code files. Poppy resolves
   top-to-bottom.
4. **No `@`-local and no dot-prefixed labels** (§0.6 items 6, 7). Name labels
   `Vm_Load__seek_busy`-style, the same double-underscore convention
   `core/spawn.pasm` uses.
5. **Do NOT add `nop` guards before labels.** Every `core/*.pasm` file has them
   and they are historical: the `jsl`-sizing bug that made labels drift is fixed
   (§0.6). New code that copies the guards inherits dead weight in a 7168-byte
   budget. `tools/rom_audit/check_label_drift.py` still runs and will tell you if
   this ever regresses.
6. **A redundant `sep #$20` / `.a8` (or `rep #$31` / `.a16` / `.i16`) as the
   first line after every label**, §0.6 item 1.
7. **When a conditional branch's target is more than ~15 source lines away,
   invert it and `brl`.** `core/spawn.pasm` has a worked example with a comment
   explaining the exact build error it fixes; copy that shape. For a *cluster* of
   handlers that all need to reach one distant fault label, put a local
   trampoline next to the cluster instead:
   ```
       bne Vm_Foo__to_fault      ; near branch, always in range
       ...
   Vm_Foo__to_fault:
       brl Vm_Fault              ; one long branch serves the whole cluster
   ```
   §0.5 measured 37 sites in the bootstrap scaffold that need exactly this.

## §0.10 — When you get stuck

In priority order, and **before** asking anyone anything:

1. **A Poppy build error, or code that assembles but behaves impossibly** (a
   `BRK #$xx` appearing mid-routine in `m.disassemble()`, a routine that runs the
   wrong instructions, `Nmi_FrameCounter` frozen): it is §0.6. Work the list
   top to bottom. Do not theorize about 65816 semantics until §0.6 is exhausted.
2. **A gate failing on values:** run `python tools/verify/vm_fixtures/validate_fixtures.py`
   and `python tools/verify/vm_fixtures/run_gate0_reference.py` first. If either
   is red, the *fixture* is wrong and your interpreter may be fine.
3. **A gate failing on reads that look like garbage or don't change:** it is
   probably the harness, and `build.md`'s "Known harness gaps" names the exact
   failure modes — reads under 32 bytes go stale, bare offsets silently misread,
   `read_memory` returns `0` for hardware registers, exec hooks fire once then
   stop. Re-read a 32-byte block spanning the address after `m.reset_emulator()`
   before concluding anything.
4. **A result that looks nondeterministic or "flaky":** in this project that has
   been a 100%-reproducible logic bug every single time it has come up. Do not
   accept it. Get raw bytes.
5. **You believe a decision in §0.2 is wrong.** Do not act on that mid-gate.
   Finish the gate as specified, then write the case up. Those three deviations
   exist because re-litigating them mid-implementation is how this kind of work
   stalls.

---

## §1 — Gate 0a: module transport (do this first; the package doesn't list it)

> **Status: DONE** (2026-08-19). `GATE 0a: PASS` — 8 assertions, all green:
> both guard regions, 184 bytes at `$7E6000` byte-matching
> `tools/verify/vm_fixtures/gate0_module.bin`, `VMSTAT_READY`/`VMERR_NONE`, the
> two header counts copied out, and frame-counter liveness. VM symbols occupy
> `$9000`-`$90F6`, leaving 6922 bytes of the region's 7168. Gate 0 (§2) is next
> and is a separate change.

The bootstrap package's Gate 0 assumes the module is already in memory. Under
deviation 2 it isn't — it has to travel `bor.msu` → WRAM first. **Build and
verify that transport before writing one line of interpreter**, or you will
debug interpreter logic against a module that never loaded.

### Files

| File | New/edit | What |
|---|---|---|
| `src/core/vm/vm_consts.pasm` | **new** | §0.8's equates, verbatim |
| `src/core/vm/vm_load.pasm` | **new** | `Vm_Init` + `Vm_Load` + `Vm_ValidateHeader` |
| `src/main.pasm` | edit | New `.org $9000` block; `.include` the two files; `jsr Vm_Load` in `scpu_boot` |
| `tools/bor_converter/pack_msu_roster.py` | edit | Append a VM-module section **after** the spawn section |
| `build_rom.py` | edit | `VM_MODULE` constant; pass to packer; `check_vm_constants()` |
| `tools/verify/_harness.py` | edit | `Reporter(kind=...)` (§0.7) + `pasm_constant_in()` (§0.8) |
| `tools/verify/vm_gate0a.py` | **new** | The gate |

**The module to ship is `tools/verify/vm_fixtures/gate0_module.bin` itself.** An
earlier draft of this plan said `out/vm/gate0_module.bin`; that was written before
the fixtures were vendored (commit `f6dd0ac`) and copying the file to a second
location would only create a way for the packed bytes and the compared-against
bytes to drift apart. Pack the fixture directly.

### Step 1 — `src/core/vm/vm_consts.pasm`

Create it with §0.8's content, unchanged. Nothing else in this step.

### Step 2 — pack the module into `bor.msu`

In `tools/bor_converter/pack_msu_roster.py`, extend `pack_roster`'s signature to
`def pack_roster(prefixes, bgs=None, fps=None, spawn_blob=None, vm_blob=None):`
and add the VM section **strictly after** the existing spawn append — the block
that begins `spawn_offset = 0` and ends `msu_bytes = msu_bytes + spawn_blob`:

```python
    vm_offset = 0
    vm_size = 0
    if vm_blob:
        vm_offset = len(msu_bytes)
        vm_size = len(vm_blob)
        msu_bytes = msu_bytes + vm_blob
```

then add `"vm_offset": vm_offset, "vm_size": vm_size` to the `sidecar` dict, and
document it in `pack_roster`'s docstring the way `spawn_blob` already is.

**Ordering is the whole point.** Appending last means no earlier section's
`data_offset` moves, so no existing constant needs re-syncing. **If
`check_spawn_constants` starts reporting a mismatch after this edit, you inserted
the VM block too early — move it, do not "fix" `SPAWN_MSU_OFFSET`.** It should
stay exactly `$0270A0` / 28.

In `build_rom.py`, next to `SPAWN_TABLE`:

```python
# Gate 0a (plan_vm.md 1): the VM's Gate 0 module, packed at the very end of
# bor.msu so it can never move an earlier section's offset. This is the same
# file tools/verify/vm_gate0a.py byte-compares the loaded WRAM region against
# -- deliberately one file, not a copy, so the packed bytes and the ground
# truth cannot drift apart.
VM_MODULE = "tools/verify/vm_fixtures/gate0_module.bin"
```

read it beside `spawn_blob` in `main()`, pass `vm_blob=vm_blob` to `pack_roster`,
and call `check_vm_constants(roster_sidecar)` right after `check_spawn_constants`.
Write `check_vm_constants` **modelled line for line on `check_spawn_constants`**
(same `re.search` shape, same `sys.exit(1)`, same "here is the corrected value"
message), reading `VM_MSU_OFFSET` and `VM_MODULE_SIZE` out of
`src/core/vm/vm_load.pasm` and comparing them against `roster_sidecar["vm_offset"]`
and `roster_sidecar["vm_size"]`. Print `check_vm_constants: OK (offset=..., size=...)`
on success.

This guard is not bookkeeping. Any future asset that changes size shifts the VM
module's offset, and without the guard the loader silently reads whatever bytes
now sit there — a garbage module with a plausible-looking header.

**Bootstrap order:** on the very first build, `vm_load.pasm` doesn't exist yet and
you don't know the offset. Run the build once with placeholder values, read the
mismatch message, paste the reported values in, rebuild. That is the intended
workflow — it is what `check_spawn_constants`'s message is written for.

### Step 3 — `src/core/vm/vm_load.pasm`

`Vm_Load` is `Spawn_Init` with a different destination, a header check, and a
status byte. **Open `src/core/spawn.pasm` and keep it visible while writing this.**
Copy its structure but **not** its `nop` guard lines (§0.9 item 5). Copy its
`php`/`sei`/`sep #$20` opening, its exact `$2000`–`$2003` seek, its
`Spawn_Init__seek_busy` spin (`lda $2000` / `bmi`), and its byte-at-a-time
`lda $2001` / `sta.l <dest>,x` read loop. Do not invent a different MSU access
pattern; sequential reads only, and this one blocking boot-time read deliberately
sits outside `Msu1_StreamBusy`'s one-stream-per-frame budget exactly like
`Spawn_Init` does.

Structure, in this order:

```
VM_MSU_OFFSET   = $000000   ; hand-synced; build_rom.py's check_vm_constants()
                            ; prints the correct value on mismatch
VM_MODULE_SIZE  = 184       ; gate0_module.bin, likewise checked at build time

Vm_Init:        ; zero VmState_*, fill both guard regions
Vm_Load:        ; jsr Vm_Init, seek+read into VmCode_Wram, jsr Vm_ValidateHeader
Vm_ValidateHeader:
Vm_Load__fail:  ; VmState_Status = VMSTAT_FAULT, VmState_Error = VMERR_BAD_MODULE
```

`Vm_Init` must:
- write `0` to every byte in `[VM_STATE_FIRST, VM_STATE_LAST)` — a single
  `ldx #0` / `sta.l VM_STATE_FIRST,x` / `inx` / `cpx #(VM_STATE_LAST-VM_STATE_FIRST)`
  loop, leaving `VmState_Status` at `VMSTAT_UNINIT` (§0.8);
- fill `VmGuardLo` with 16 × `$A5` and `VmGuardHi` with 16 × `$5A`.

`Vm_ValidateHeader` checks, in this order, per `FORMAT.md`'s 64-byte header —
**offsets are from `VmCode_Wram`, and each is one `lda.l` / `cmp #` / branch**:

| Header offset | Check |
|---|---|
| `+$00..$03` | the four bytes are `'B'`, `'4'`, `'8'`, `'S'` (`$42 $34 $38 $53`) |
| `+$04` | `== 1` (format_version) |
| `+$05` | `== $30` (opcode_abi) |
| `+$06` | `== 0` (numeric_profile — Q16.16, §0.3) |
| `+$08` (u16) | `<= 4096`, and store to `VmState_InstrCount` |
| `+$0A` (u16) | `<= 1024`, and store to `VmState_SlotCount` |
| `+$34` (u32) | low 16 bits `== VM_MODULE_SIZE`, high 16 bits `== 0` |

Worked example for the first check, showing every convention from §0.9 in place —
follow this shape for all of them:

```
Vm_ValidateHeader:
    sep #$20
.a8
    lda.l VmCode_Wram+0
    cmp #$42                ; 'B'
    bne Vm_ValidateHeader__to_fail
    lda.l VmCode_Wram+1
    cmp #$34                ; '4'
    bne Vm_ValidateHeader__to_fail
    ...
Vm_ValidateHeader__to_fail:
    brl Vm_Load__fail       ; ONE trampoline for the whole routine -- every
                            ; bne above stays a short, in-range branch (0.9 item 7).
                            ; No nop guard before either label: that bug is fixed
                            ; (0.6), and core/spawn.pasm's guards are historical.
```

On success: `VmState_Status = VMSTAT_READY`, `VmState_Error = VMERR_NONE`, `rts`.
On any failure: fall into `Vm_Load__fail`, which sets `VMSTAT_FAULT` /
`VMERR_BAD_MODULE` and returns. **Never leave `VmState_Status` at `VMSTAT_UNINIT`
on either path** — an unwritten status is indistinguishable from a loader that
never ran, which is precisely the confusion §0.8 numbers `UNINIT = 0` to prevent.

CRC32 is **deferred to Gate 1**. Write `; TODO(Gate 1): verify crc32 at header
+$38 over bytes $40..module_size` at the end of the routine and move on.

Index-width reminder: the read loop runs with `rep #$31` (`.a16 .i16`) and flips
to `sep #$20` (`.a8`) inside the body, exactly as `Spawn_Init__read` does. `X`
counts bytes to `VM_MODULE_SIZE`, which is well under 64 KB.

### Step 4 — wire it into `src/main.pasm`

Two edits, both at anchors you should locate by **searching for the quoted text**
rather than trusting line numbers, which drift:

1. **The new `.org` block.** Find the line
   `; ends at $8C00 + 96 = $8C60, leaving ~8096 bytes free before $AC00.`
   That is the end of the `.org $8C00` block, immediately before the
   `LoadAudioData` banner and `.org $AC00`. Insert between them:

   ```
   ; ============================================================================
   ; VM region -- plan_vm.md 0.3. Owns $9000-$AC00 (7168 bytes) and no more.
   ; $8C60-$9000 is reserved for plan_game.md's core/text.pasm; do NOT start
   ; here at $8C60. Overflow past $AC00 silently corrupts LoadAudioData and
   ; presents as an AUDIO bug -- run plan_vm.md 0.7's region-occupancy check
   ; after every change in this region.
   ; ============================================================================
   .org $9000
   .include "core/vm/vm_consts.pasm"
   .include "core/vm/vm_load.pasm"
   ```

   `.org` blocks in this file are in ascending address order and there is no
   precedent for a backwards one. `$9000` sits correctly between `$8C00` and
   `$AC00`.

2. **The call site.** Find `jsr Spawn_Init` in `scpu_boot` and add directly after
   it:

   ```
       ; --- Gate 0a (plan_vm.md 1): boot-time MSU -> WRAM load of the script
       ; VM's bytecode module, plus header validation. Placed here for two
       ; reasons at once: it is after MSU-1 is up (same blocking-read shape as
       ; Spawn_Init directly above, outside the per-frame Msu1_StreamBusy
       ; budget), and it is before Core_Nmi_Init enables NMI -- every
       ; VmState_* cell and both guard regions must be initialized before a
       ; vblank can occur (plan_vm.md 0.4; see memory
       ; boot_nmi_race_before_oam_init for the session that rule cost). ---
       jsr Vm_Load
   ```

   That one placement satisfies both ordering constraints without you having to
   reason about either.

### Step 5 — `tools/verify/vm_gate0a.py`

Use `tools/verify/_harness.py`. It derives the ROM path from the repo root, which
is what stops a worktree from silently testing the main checkout's stale ROM
(memory `worktree_mesen_rom_path_footgun`). **Never hardcode the ROM path**, and
read every constant with `pasm_constant_in('src/core/vm/vm_consts.pasm', ...)`
rather than typing numbers.

Assertions, **in this order** — the order is deliberate:

1. **Guards first.** `VmGuardLo` at `$7EE000` reads 16 × `$A5` **and** `VmGuardHi`
   at `$7F1480` reads 16 × `$5A`. Running this first means a harness that cannot
   see `$7E` or `$7F` at all fails here, distinguishably, instead of masquerading
   as a loader bug two assertions later.
2. **The module bytes.** Read `VM_MODULE_SIZE` bytes from `$7E6000` and
   byte-compare against `tools/verify/vm_fixtures/gate0_module.bin` read from
   disk. Compare against the file, never against a checksum the engine computed
   (§0.7's ground-truth rule). On mismatch, print the first differing offset and
   both bytes — "arrays differ" is not a usable failure message.
3. **Status.** `VmState_Status == VMSTAT_READY` and `VmState_Error == 0`.
4. **Liveness.** `Nmi_FrameCounter` advances normally across 120 frames. The
   loader runs at boot under forced blank; a hang or vblank overrun here is real.

Read rules that are not optional, all from `build.md`'s "Known harness gaps":
- Call `m.reset_emulator()` before reading anything.
- Use `_harness.read_block(m, addr, length)` with `length >= 32` — **reads under
  32 bytes have returned stale data in this harness.** `VmState_Status` is a
  single byte, exactly the size that gap applies to, so read a 32-byte block
  spanning `$7F1500` and slice locally.
- Full addresses (`0x7E6000`), never bare offsets (memory
  `mesen_read_memory_bare_offset_gap`).

Finish with `Reporter('0a', kind='GATE').finish()` (§0.7), giving `GATE 0a: PASS`.

### Definition of done

- [ ] `python build_rom.py` prints both `check_spawn_constants: OK` (still
      `$0270A0` / 28) and `check_vm_constants: OK`
- [ ] `python tools/rom_audit/check_label_drift.py` exits 0
- [ ] `python tools/rom_audit/audit_all.py` → `ALL CHECKS PASS`
- [ ] §0.7's region-occupancy check prints `region OK` (this is the first gate
      where it has any symbols to find)
- [ ] `python tools/verify/vm_gate0a.py` → `GATE 0a: PASS`
- [ ] The regression suite in §0.7 is still green — all seven, no exceptions
- [ ] Committed with `Gate 0a` in the message, and this section's status updated

**Then stop.** Gate 0 is a separate change (§0.7's stop rule).

---

## §2 — Gate 0: fetch, dispatch, integer slots, branch, root RET

> **Status: DONE** (2026-08-19). `GATE 0: PASS` -- 9 assertions, all green:
> host oracle + fixture self-consistency both PASS before the engine was
> trusted, status/error, the full 40-byte slot region byte-identical to
> `gate0_expected_slots.bin`, the reconstructed 8-entry trace ring exact
> match, both guard regions, frame-counter liveness. `Vm_Run` is wired into
> `scpu_main_loop` (deviation 1) and is a no-op once terminal. VM symbols
> occupy `$9000`-`$9586`, 5754 of 7168 bytes still free. Gate 1 (§3) is next
> and is a separate change.
>
> Two things worth carrying forward, found executing this gate rather than
> reading it:
> - **The exit contract's "jmp Vm_Run" for control transfer is implemented as
>   a separate internal label (`Vm_Run__loop`), not the literal jsr entry
>   point.** The public `Vm_Run` does one-time per-frame budget/status setup
>   that must not repeat every instruction (it would re-arm a full frame's
>   budget on every fetch and the cooperative yield could never trigger).
>   `Vm_Run__loop` is the re-fetch continuation the contract actually means.
>   Name it that way in any later gate's own control-transfer handlers.
> - **The carry-propagation regression this gate's own header warns about
>   ("one slot's high word wrong, low word right") is not actually
>   detectable by `gate0_program.json`'s fixture.** Its ADD is `2 + 3 = 5`,
>   which never generates a carry out of the low 16 bits -- a stray `clc`
>   between the two `adc`s was deliberately reintroduced and reverted during
>   this gate's own verification, and `vm_gate0.py` passed regardless. The
>   carry-handling discipline documented in `vm_run.pasm`'s header is still
>   correct and still worth keeping, but no committed gate currently proves
>   it; a fixture whose ADD actually crosses a 16-bit boundary would close
>   this gap and is worth adding in a later gate rather than assumed covered
>   now.
> - **`vm_gate0a.py`'s status assertion had to be relaxed.** It originally
>   pinned `VmState_Status == VMSTAT_READY`; once `Vm_Run` runs automatically
>   every frame, the shipped module completes to `VMSTAT_DONE` well before
>   Gate 0a's own snapshot, so that assertion started failing -- a real
>   cross-gate regression, not flakiness. It now asserts status left
>   `VMSTAT_UNINIT` and never reached `VMSTAT_FAULT`, which is what Gate 0a
>   was actually protecting.

The bootstrap package's mandatory first milestone. Scope is *exactly*
`tools/verify/vm_fixtures/gate0_program.json` and nothing more.

### Implement

| Piece | Notes |
|---|---|
| `Vm_Run` entry | Establish widths explicitly; set `VMSTAT_RUNNING` |
| Budget check | Decrement `VmState_Budget`; 0 → `vm_yield` |
| Record fetch | `X = IP*8`, then `lda.l VmCode_Wram,x` for each field. Bounds-check `IP < instruction_count` **before** the multiply |
| Trace ring | Write `(IP, opcode)` to `VmTrace_Wram`, 32-entry wrap |
| Dispatch | Compare-and-branch chain, exactly as the scaffold. **Do not build a jump table yet** — the chain makes every ABI value visible during bring-up, and Gate 7 is where dispatch gets optimized |
| `CONSTINT` (2) | Runtime no-op → `vm_next` (constants are prelinked) |
| `ADD` (16) | Signed 32-bit, INTEGER-only at this gate; non-INTEGER → `VMERR_BAD_TYPE` |
| `EQ` (26) | INTEGER-only; result is INTEGER 0/1 |
| `Branch_FALSE` (36) | Truthiness on INTEGER only |
| `JUMP` (20) | Assign IP, **do not fall through to the increment** |
| `ERR` (15) | `VMERR_EXPLICIT_ERR` |
| `RET` (43) | Root only → `VMSTAT_DONE` |
| `NOOP` (33) | → `vm_next` |
| `FIELD` (7) | Always faults: `VMERR_FIELD_OPCODE` ($0002) |
| Opcode `>= 48` | `VMERR_BAD_OPCODE` ($0001) |
| Any other value `0..47` | `VMERR_UNIMPLEMENTED` ($0010) — a deterministic fault, **never** a silent no-op. §0.8 explains why these last two are different codes; the committed host oracle already emits $0010 |

### Files

| File | New/edit | What |
|---|---|---|
| `src/core/vm/bor_vm_opcodes.pasm` | **new** | Copy `tools/verify/vm_fixtures/bor_vm_opcodes.pasm` as-is |
| `src/core/vm/vm_run.pasm` | **new** | Dispatcher, trace ring, handlers |
| `src/core/vm/vm_slots.pasm` | **new** | Slot read/write + the 32-bit helpers |
| `src/main.pasm` | edit | Two more `.include`s in the `.org $9000` block; `Vm_LoadSlots` call after `Vm_Load` |
| `tools/verify/vm_gate0.py` | **new** | The gate |

Gate 0a loaded the module image but deliberately did **not** copy the initial
slot image out of it. Do that here: read `initial_slots_offset` (header `+$1C`)
and `slot_count` (already in `VmState_SlotCount`), and copy `slot_count * 8`
bytes from `VmCode_Wram + initial_slots_offset` to `VmSlots_Wram`. For the Gate 0
fixture that is 5 slots / 40 bytes.

### The exit contract, and the trace ring

**The single most bug-prone thing at this gate is the IP contract.** Sequential
handlers increment IP exactly once (`jmp vm_next`); control-transfer handlers
assign IP and re-enter (`jmp vm_run`). A handler that does both advances two
instructions and the trace will not match. The scaffold's exit-contract comment
(its §8) is correct — follow it literally:

```
normal sequential instruction -> jmp Vm_Next    ; IP = IP + 1, then re-fetch
control transfer              -> jmp Vm_Run     ; IP already assigned, re-fetch
fault                         -> jmp Vm_Fault
cooperative boundary          -> jmp Vm_Yield
root return                   -> jmp Vm_Done
```

`JUMP` (20) and `Branch_FALSE` (36) are the two handlers at this gate that take
the `Vm_Run` exit. Everything else takes `Vm_Next`. If your trace shows IP
skipping by 2 after a branch, this is why — it is not a fetch bug.

**Trace ring record, 4 bytes, at `VmTrace_Wram` (`$7F1300`), 32 entries:**

```
+0  u16  IP
+2  u8   opcode
+3  u8   reserved (write 0)
```

`VmState_TraceHead` is the next write index, `0..31`, wrapping. Write the entry
**before** dispatching, so a faulting instruction appears in its own trace. The
gate reads the ring back and reconstructs execution order from `TraceHead`; with
8 executed instructions and a 32-entry ring there is no wrap to reason about at
this gate, but write the wrap correctly anyway — Gate 1's fault fixtures use it.

32-bit arithmetic on a 16-bit accumulator: operate on two 16-bit halves, low then
high, and let the carry propagate. This project has already been bitten by a
**chained-`adc` carry-propagation bug** that silently corrupted a computed address
(Phase 10, `README.md`) — write the carry handling deliberately, don't improvise.

### Gate

`tools/verify/vm_gate0.py`:

1. Run the host oracle first and require it green:
   `python tools/verify/vm_fixtures/run_gate0_reference.py`
   → `OK: Gate 0 reference result and complete IP/opcode trace match.`
   Also run `python tools/verify/vm_fixtures/validate_fixtures.py`
   → `FIXTURES: PASS`, so a fixture problem can never masquerade as an
   interpreter bug.
2. In Mesen2: run until `VmState_Status != VMSTAT_RUNNING`, bounded by a frame
   cap so a hang fails instead of hanging the test.
3. Assert `VmState_Status == VMSTAT_DONE`, `VmState_Error == 0`.
4. **Byte-compare the 40-byte `VmSlots_Wram` region against
   `tools/verify/vm_fixtures/gate0_expected_slots.bin`.** This is the gate. Not a spot-check of one
   slot — all 40 bytes.
5. Assert the executed trace ring matches the fixture's `executed_trace` exactly:
   `[[0,2],[1,2],[2,16],[3,2],[4,26],[5,36],[6,20],[9,43]]`. This independently
   proves sequential increment, that `Branch_FALSE` did *not* branch on a true
   condition, that `JUMP` assigned IP without a double increment, and that the
   unreachable `ERR` at IP 8 stayed unreachable.
6. Assert both guard regions unchanged.

Same harness rules as Gate 0a's step 5 — `reset_emulator()` first, reads `>= 32`
bytes, full addresses, every constant via
`pasm_constant_in('src/core/vm/vm_consts.pasm', ...)`, and
`Reporter('0', kind='GATE').finish()`.

Pass line: `GATE 0: PASS`.

**Two failures to expect, so you recognize them instead of debugging blind:**
- *Slots right, trace wrong.* The IP contract (above). Look for a handler that
  both assigns IP and falls through to `Vm_Next`.
- *One slot's high 16 bits wrong, low 16 right.* Carry propagation in the 32-bit
  `ADD`. This project already shipped that exact bug once (Phase 10 — a chained
  `adc` silently corrupted a computed address); write the carry handling
  deliberately rather than improvising it.

**Stop here.** Do not add calls, strings, decimals, or dispatcher optimization in
the same change.

---

## §3 — Gate 1: complete the control/no-op family and the fault model

**Pass condition: every ABI value 0..47 reaches either its intended handler or an
explicit, deterministic fault. No value is silently a no-op.**

Implement `PJUMP` (21), `Branch_TRUE` (37), `Branch_EQUAL` (38), and the
link/no-op family that the host linker consumes and the runtime ignores:
`CONSTSTR` (0), `CONSTDBL` (1), `PUSH` (34), `POP` (35), `DATA` (39),
`IMMEDIATE` (41), `DEFERRED` (42), `CHECKARG` (44), `CLEAN` (45), `FUNCDECL` (47),
`NOOP` (33). `FIELD` (7) faults with `VMERR_FIELD_OPCODE`; anything `>= 48` faults
with `VMERR_BAD_OPCODE`.

Also land here: module CRC32 validation (deferred from Gate 0a), and full fault
capture — failing IP, failing opcode, operands A/B/C, frame depth, and the trace
ring frozen at the fault point.

**Gate** (`vm_gate1.py`): generate a 48-record fixture, one record per opcode
value, plus a record with opcode 48 and one with 255. Run each in isolation and
assert the resulting `(status, error)` pair matches a table you write *from
`opcode_manifest.csv`*, not from the implementation. Pass line: `GATE 1: PASS`.

---

## §4 — Gate 2: the integer unary/binary family

The big one for ROM budget (~1700 bytes projected). Implement `LOAD` (3),
`SAVE` (4), `INC` (5), `DEC` (6), `POS` (9), `NEG` (10), `NOT` (11), `MUL` (12),
`DIV` (13), `MOD` (14), `SUB` (17), `SHL` (18), `SHR` (19), `GE`/`LE`/`LT`/`GT`
(22–25), `NE` (27), `OR`/`AND` (28–29), `BIT_OR`/`XOR`/`BIT_AND` (30–32).

**Semantic decisions to make explicitly and stamp in the source** (all from the
package's §6, all needing fixtures rather than recollection):

- Integer overflow = two's-complement 32-bit wrap.
- Shift counts normalized `count & 31`. Test `-1, 0, 31, 32, 33` against the
  oracle.
- `DIV` by zero → EMPTY (historical behavior). `MOD` by zero → `VMERR_DIV_ZERO`
  (deliberate divergence; historical code has no guard and this VM must not
  scribble).
- `NEG` on DECIMAL appears to fall through to INTEGER handling in the historical
  source. Do not reproduce a bug you haven't confirmed — write the fixture, record
  the decision in the source comment either way.

`core/math.pasm` already has 16×16 multiply and 16-bit divide. Read it before
writing 32-bit versions; it may compose, and it is already byte-verified.

**Gate** (`vm_gate2.py`): a generated edge-vector fixture per operation
(`0`, `1`, `-1`, `$7FFFFFFF`, `$80000000`, and a few ordinary values), compared
against a host oracle extended from `run_gate0_reference.py`. Pass line:
`GATE 2: PASS`. Watch the region-occupancy check especially closely at this gate.

---

## §5 — Gate 3: calls, frames, and the native ABI

Implement `CALL` (8), `PARAM` (40), `JUMPR` (46), `RET` (43) with real frames,
per the package's §7 — a fixed 64-deep WRAM frame stack at `VmFrames_Wram`
(12 bytes per frame, layout in the package's `BorCallFrame`), the callsite table,
and the flat argument-slot table. (The package says BW-RAM; under deviation 1
this is plain WRAM.)

Overflow → `VMERR_CALL_DEPTH`. Missing argument (`arg_cursor >= argc`) → clear
destination to EMPTY, not a fault.

Add a minimal native function table with `abs`, `min`, `max`, and a test-logging
function, using the package's carry-clear/carry-set ABI. **Native IDs are stable
and host-generated** — never a raw pointer, never an index that shifts when the
table grows.

**Gate** (`vm_gate3.py`): nested and recursive fixtures, missing-parameter cases,
return values, and a deliberate depth-overflow case. Assert no BW-RAM/WRAM
sentinel (the guard regions) is disturbed by deep recursion. Pass line:
`GATE 3: PASS`.

---

## §6 — Gate 4: strings and typed pointers

Interned ROM strings (in the module image), a bounded dynamic pool at
`VmStrPool_Wram`, refcount on copy, decrement on clear/retype, concatenation,
truthiness (empty = false), lexicographic byte comparison.

`VT_PTR` is a **typed engine handle** — `bits 31..24` handle class, `bits 23..0`
object index — never a raw address. Natives validate the class before resolving.

Every overflow path (pool exhausted, invalid handle, concat past limit) is a
deterministic fault: `VMERR_STRING_POOL` / `VMERR_STRING_OVERFLOW`. Never scribble
past a buffer to reproduce old C behavior.

**Gate** (`vm_gate4.py`): repeated call/copy/concat cycles that must not leak
handles or exhaust the pool; comparison determinism across runs; guard regions
intact. Pass line: `GATE 4: PASS`.

---

## §7 — Gate 5: decimals, Q16.16 only

Stamp `numeric_profile = 0`. Implement INTEGER↔Q16.16 conversion (truncate toward
zero on the way down), arithmetic, comparison, truthiness, and a **cartridge-
defined** decimal→string format (the historical behavior was host `printf`; define
ours exactly and fixture it).

**Do not compare Q16.16 output against unquantized binary64 expectations.** The
host oracle must quantize identically or every fixture is a false failure. Binary64
is out of budget (§0.3) — if it is ever genuinely needed, that is a re-plan.

**Gate** (`vm_gate5.py`): profile-specific differential vectors. Pass line:
`GATE 5: PASS`.

---

## §8 — Gate 6: a real OpenBOR script, and engine integration

This is the first gate that changes anything a player could see, and the first
that needs the host-side exporter to be real.

1. **Build `export_bor4086_module`** (`tools/bor_converter/`) — parse a real
   script out of `Beats of Rage Original [v.3.0 Build 4086].pak`, link it
   (resolve labels to instruction indices, `ScriptVariant` identities to slot IDs,
   native pointers to stable IDs, strings to interned handles) and emit the
   revision-1 binary module. `FORMAT.md`'s §"Normalization rules" is the spec.
2. **Build `dump_bor4086_oracle` and `compare_vm_trace`** — run the same script on
   a host interpreter, record slots/branches/calls/faults, and diff at instruction
   boundaries against the SA-1... *S-CPU* trace.
3. **Wire natives to the real engine.** The first genuinely useful ones map to
   what already exists: spawn an enemy (drive `core/spawn.pasm`'s queue), query
   player position/HP, set camera bounds, play a song. Every PPU/APU-facing
   native publishes a bounded command — it does not perform arbitrary register
   writes from inside the interpreter.
4. **Wire the cooperative budget** into `scpu_main_loop`. Start conservative
   (a few hundred opcodes/frame) and measure. `Nmi_FrameCounter` must still
   advance 1:1 — a VM that overruns vblank reproduces this project's
   most-repeated bug (four recurrences, memory `ccdma_validated_nmi_timing_bug`).

**Gate** (`vm_gate6.py`): the real script reaches the same native calls in the
same order with the same normalized arguments and results as the host oracle, and
the full existing regression suite still passes. Pass line: `GATE 6: PASS`.

---

## §9 — Gate 7: performance, and the SA-1 question

Only after Gate 6 is green and *measured*. In order:

1. Profile organic gameplay — actual opcodes/frame, actual worst-case frame.
2. If over budget, replace the compare-and-branch dispatcher with a 48-entry
   same-bank handler-address table. This is the cheapest large win and should be
   tried before anything structural.
3. If still over budget, *then* consider SA-1 offload (deviation 1's escape
   hatch). That needs its own design: restructuring `sa1_main`'s blocking loop to
   yield, a command/result mailbox, and moving VM state to a region both CPUs can
   reach coherently. Plan it separately; do not start it inside Gate 7.

**Always keep an interpreter-only correctness fallback.** Any native escape must
be diffable against the plain interpreter path.

---

## §10 — Host tooling checklist

Per the package's §11, all under `tools/bor_converter/` or `tools/verify/`:

- [ ] `export_bor4086_module` — linked graph → revision-1 binary
- [ ] `dump_bor4086_oracle` — host interpreter reference run
- [ ] `compare_vm_trace` — instruction-boundary diff
- [ ] `verify_module` — counts, ranges, slot/callsite/string/native IDs, CRC
- [ ] `make_opcode_vectors` — per-family fixture generator

Never serialize `Instruction*`, `ScriptVariant*`, function pointers, list nodes,
or host struct padding into a module.

---

## §11 — What this VM will still not give you

Complete after Gate 6 and the game is *still* not a game. Missing, and not in
scope here — see `plan_game.md`:

- No title screen, no menu system, no font or text renderer
- No stage progression, no level transition, no win condition, no game over
- No continue/score/lives
- No pause
- No player death (the player is deliberately exempt from the damage system)
- No throws, grabs, jumps, or specials
- No items or pickups
- No boss encounters
- No ending or credits

The VM makes *scripted* versions of some of the above expressible. It does not
implement any of them, and every one of them can be built without it.
