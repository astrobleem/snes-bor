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

## §0 — Ground truth measured for this plan (2026-08-16)

Everything in this section was **measured this session**, not assumed. Do not
re-derive it, but do re-measure anything marked *(re-check each gate)* before
depending on it.

### §0.1 Where the source material lives

The design work this plan builds on ships as `openbor4086_sa1_bootstrap.zip` in
the repo root (untracked, created 2026-08-03 by an earlier session). Extract it
somewhere scratch and read it — it is genuinely good research:

```bash
unzip -o openbor4086_sa1_bootstrap.zip -d <scratch>/
```

| File | What it is | Trust level |
|---|---|---|
| `README.md` | Full design contract, 12 sections | High — read it all |
| `FORMAT.md` | Binary module format, revision 1 | High — implement as written |
| `opcode_manifest.csv` | All 48 opcodes, operands, semantics | High — this is the ABI |
| `tests/gate0_program.json` | Gate 0 fixture + expected final state | High — this is the gate |
| `tests/gate0_module.bin` | Same fixture, packed (184 bytes) | High |
| `tests/gate0_expected_slots.bin` | Expected final slot image (40 bytes) | High — ground truth |
| `tools/run_gate0_reference.py` | Host oracle for the fixture | High |
| `src/bor_vm_opcodes.pasm` | 48 opcode constants | High — paste as-is |
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

**Do not put high-bank ROM pointers in this VM, even as an "alternative."** The
ROM is 4 MB with only bank 0 populated, so it *looks* like free real estate. It
is a trap: Poppy's confirmed cross-bank label mis-resolution (bug 9) plus the
LoROM 32 KB-per-bank address window make it strictly worse than WRAM here, and
you have ~107 KB of WRAM you don't have to fight for.

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
*symbol* in that region is `$8C30`, but the 96-byte `.incbin` after it really
ends at `$8C60`. Sizing from the label instead of the data's end overstates the
gap by 48 bytes. Always size from `$8C60`.)

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
$7E6000  VmCode_Wram      module image: header + instruction records
                          32 KB cap = 4096 records (revision-1 allows 8192;
                          cap at 4096 here to keep X-index headroom)
$7EE000  VmSlots_Wram     mutable variant slots, 8 B each
                          8 KB = 1024 slots
$7EFF00  VmGuardLo        16 guard bytes (pattern $A5) — see §0.7
$7F0000  VmFrames_Wram    call frames, 12 B each, 64 deep = 768 B
$7F0300  VmStrPool_Wram   dynamic string pool (Gate 4), 4 KB
$7F1300  VmTrace_Wram     (IP,opcode) ring, 32 entries x 4 B = 128 B
$7F1380  VmGuardHi        16 guard bytes (pattern $5A)
$7F1400  VmState_*        IP, STATUS, ERROR, BUDGET, FRAME_TOP, etc.
```

`VmState_*` cells are plain absolute `$7F14xx` addresses, one per line, exactly
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
- **No `nop` guards before any label** (Poppy bug 13 — `jsl` sized 3, emits 4).
- **No redundant `sep`/`rep` width re-sync at branch targets** (Poppy's linear
  width tracking).
- **DP-based state and `[dp],y` fetch** (deviation 3).
- **`.snes` / bank directives** that don't match this project's single-`.bank 0`
  layout.

Treat the scaffold as a **structural reference for the dispatcher shape and the
handler exit contract**, and retype it into this project's conventions. Do not
copy-paste it.

### §0.6 The Poppy checklist — apply to every line of new assembly

Inline here on purpose, because you will not go read `CLAUDE.md` mid-gate. All of
these are confirmed silent-miscompile bugs in this toolchain.

1. **Open every routine, and every branch-target label, with a redundant
   `sep #$20` / `.a8` (or `rep #$30` / `.a16 .i16`) width re-sync.** Poppy tracks
   accumulator width linearly, not along control flow, so a label reached by a
   branch that jumps over a `rep`/`sep` gets its following `lda #`/`cmp #`
   mis-sized and every byte after it misaligns. Symptom: a phantom `BRK #$xx`
   mid-routine in `m.disassemble()`. The re-sync is a runtime no-op when the
   width already matches — apply it unconditionally rather than reasoning.
2. **Put a `nop` guard before every new label.** Poppy sizes `jsl` as 3 bytes and
   emits 4, so labels drift one byte early per preceding `jsl`, cumulatively.
3. **Keep conditional branch targets within ~15 source lines.** Farther: invert
   the condition and `brl`, or split into a `jsr`'d leaf routine. A conditional
   branch past ±127 bytes can assemble silently and hang the CPU.
4. **Indexed WRAM access uses `.l` or bare, never `.w`.** `.w` on an indexed
   bank-`$7E` symbol silently drops the bank byte.
5. **Never write `.l Symbol,y`.** No such 65816 addressing mode exists (verified
   in fullsnes, §0.2); Poppy emits a wrong absolute,Y instruction with no error.
   Index long addressing by `X` only.
6. **Never branch to a dot-prefixed local label** (`bcc .valid`). Poppy silently
   deletes both the branch and the label (bug 14). Use global labels.
7. **No `@`-local labels in anything `.include`d.** They mis-resolve once reached
   via `.include`. No `src/core/*.pasm` file uses them; match that.
8. **No macro invocations inside branch-skipped code.** Macros are sized 0 bytes
   during address estimation, corrupting the branch offset. Inline by hand.
9. **`stz` has no long addressing mode.** `stz.l` doesn't error, it emits
   garbage. Use `lda #0` / `sta.l`.
10. **`cpx` has no long addressing mode either.** Same failure shape.
11. **Prefer hand-computed literals over computed operand expressions** in
    immediates; this project has been bitten by silently-wrong arithmetic there.

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
python tools/verify/phase5.py phase6.py phase7.py phase9.py \
       phase11_damage.py phase12_roster.py    # run individually
```

(`phase8.py` fails and has failed since Phase 14 — it gates the pre-streaming
whole-level-BG shape. Known stale, not your regression. Do not "fix" it as part
of a VM gate.)

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

---

## §1 — Gate 0a: module transport (do this first; the package doesn't list it)

The bootstrap package's Gate 0 assumes the module is already in memory. Under
deviation 2 it isn't — it has to travel `bor.msu` → WRAM first. **Build and
verify that transport before writing one line of interpreter**, or you will
debug interpreter logic against a module that never loaded.

### Files

| File | New/edit | What |
|---|---|---|
| `tools/bor_converter/pack_msu_roster.py` | edit | Add a VM-module section after the spawn section |
| `build_rom.py` | edit | `VM_MODULE = "out/vm/gate0_module.bin"`; pass to packer; add `check_vm_constants()` |
| `src/core/vm/vm_load.pasm` | **new** | Boot-time MSU→WRAM loader + header validation |
| `src/main.pasm` | edit | New `.org $9000` block (**not `$8C60`** — see §0.3); `.include` VM files; call `Vm_Load` from `scpu_boot` |
| `tools/verify/vm_gate0a.py` | **new** | The gate |

### Steps

1. **Copy the spawn-section pattern exactly.** Read `pack_msu_roster.py`'s spawn
   handling and `core/spawn.pasm`'s loader end to end first. The VM section is
   the same shape: append after existing sections so no earlier `data_offset`
   moves, and return the new offset/size in the sidecar dict.
2. **Add `VM_MSU_OFFSET` / `VM_MODULE_SIZE`** to `src/core/vm/vm_load.pasm` as
   hand-synced constants, and **add `check_vm_constants()` to `build_rom.py`**
   modelled line-for-line on `check_spawn_constants()` — it re-reads the `.pasm`,
   compares against what the packer just computed, and `sys.exit(1)` on mismatch
   with the corrected value printed. This is not optional bookkeeping; adding any
   asset shifts every later offset, and this guard is what turns a silent
   garbage-read into a build failure.
3. **Write `Vm_Load`**: seek `bor.msu` to `VM_MSU_OFFSET`, read `VM_MODULE_SIZE`
   bytes sequentially into `VmCode_Wram`. Sequential MSU reads only — same as
   `core/spawn.pasm`. Call it from `scpu_boot` **after** the existing MSU init,
   and **before** `Core_Nmi_Init` (§0.4).
4. **Write `Vm_ValidateHeader`** per `FORMAT.md`'s 64-byte header: magic `"B48S"`,
   `format_version == 1`, `opcode_abi == $30`, `numeric_profile == 0`,
   `module_size` matches, counts within caps (`instruction_count <= 4096`,
   `slot_count <= 1024`), every table offset inside the module. On any failure
   set `VmState_Status = VMSTAT_FAULT` and `VmState_Error = VMERR_BAD_MODULE`.
   CRC32 verification is deferred to Gate 1 — note it as a TODO in the source.
5. **Fill both guard regions** with their patterns during init.

### Gate

`tools/verify/vm_gate0a.py` must, against a live Mesen2 session on
`distribution/bor.sfc`:

- read back the full loaded region from `VmCode_Wram` and **byte-compare it
  against `tests/gate0_module.bin` on disk** (the ground-truth rule — compare
  against the file, not against a checksum the engine computed);
- assert `VmState_Status == VMSTAT_READY` and `VmState_Error == 0`;
- assert both guard regions still read their fill patterns;
- assert `Nmi_FrameCounter` advances normally across 120 frames (the loader runs
  at boot under forced blank; a hang or a vblank overrun here is a real failure).

Pass line: `GATE 0a: PASS`.

Use `tools/verify/_harness.py` — it derives the ROM path from the repo root, which
is what keeps a worktree from silently testing the main checkout's stale ROM (see
memory `worktree_mesen_rom_path_footgun`). Never hardcode the ROM path.

---

## §2 — Gate 0: fetch, dispatch, integer slots, branch, root RET

The bootstrap package's mandatory first milestone. Scope is *exactly*
`tests/gate0_program.json` and nothing more.

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
| Unknown / `FIELD` (7) | Deterministic fault, never a no-op |

**The single most bug-prone thing at this gate is the IP contract.** Sequential
handlers increment IP exactly once (`jmp vm_next`); control-transfer handlers
assign IP and re-enter (`jmp vm_run`). A handler that does both advances two
instructions and the trace will not match. The scaffold's exit-contract comment
(its §8) is correct — follow it literally.

32-bit arithmetic on a 16-bit accumulator: operate on two 16-bit halves, low then
high, and let the carry propagate. This project has already been bitten by a
**chained-`adc` carry-propagation bug** that silently corrupted a computed address
(Phase 10, `README.md`) — write the carry handling deliberately, don't improvise.

### Gate

`tools/verify/vm_gate0.py`:

1. Run the host oracle first and require it green:
   `python <scratch>/openbor4086_sa1_bootstrap/tools/run_gate0_reference.py`
   → `OK: Gate 0 reference result and complete IP/opcode trace match.`
   (Vendor this script into `tools/verify/` so the gate is self-contained.)
2. In Mesen2: run until `VmState_Status != VMSTAT_RUNNING`, bounded by a frame
   cap so a hang fails instead of hanging the test.
3. Assert `VmState_Status == VMSTAT_DONE`, `VmState_Error == 0`.
4. **Byte-compare the 40-byte `VmSlots_Wram` region against
   `tests/gate0_expected_slots.bin`.** This is the gate. Not a spot-check of one
   slot — all 40 bytes.
5. Assert the executed trace ring matches the fixture's `executed_trace` exactly:
   `[[0,2],[1,2],[2,16],[3,2],[4,26],[5,36],[6,20],[9,43]]`. This independently
   proves sequential increment, that `Branch_FALSE` did *not* branch on a true
   condition, that `JUMP` assigned IP without a double increment, and that the
   unreachable `ERR` at IP 8 stayed unreachable.
6. Assert both guard regions unchanged.

Pass line: `GATE 0: PASS`.

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
