# S6 numerical preflight: BOR 2004 Watcom reference

## Scope and verdict

This is a source/toolchain investigation only. It does not modify production
runtime code, select rational arithmetic, or select a new IEEE policy.

Selected tier: **HISTORICAL_NUMERIC_FAMILY**, bounded by the gameplay-visible
probes listed below. A unique historical executable oracle was not recovered.
The tested Watcom configurations agree on the observed branch, pixel, random
sample, and integer-conversion results, but the original compiler version,
switches, binary, and build files are absent. This is not a claim that every
unprobed expression or optimization has been identified.

The existing `docs/bor_actor_s6_numeric.md` rational and conditional-store
analysis remains a reference sidecar. It is not changed into a source-exact
runtime contract by this preflight.

## Authoritative source and availability

The pinned source file used here is:

`out/bor_compile_s6/BOR.C`

SHA-256:

`68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41`

The pinned source includes `RAND32.ASM` and `RAND32.H`, but the released
archive does not contain the GAMELIB3 C sources or a project/build file. The
source release README identifies BOR V1.0029, last edited 30 January 2004,
compiled with Watcom for DOS/4GW or PmodeW, and explicitly supplies no
compilation instructions. The README also says the release contains the BOR
C/ASM code but not level data or other game assets.

## Gameplay-visible floating-point inventory

The source uses IEEE-format `float` object fields for `entity.speed`,
`x`, `z`, `a`, `xdir`, `zdir`, `xto`, `zto`, `base`, and `tossv` (BOR.C lines
230, 254–263). It also has float globals `advancex`, `advancey`, and
`lasthitx/lasthitz/lasthita` (404–405, 480).

| Path | Source operation | Observable point |
|---|---|---|
| `diff` / `inair` | float compare/subtract; `diff(...) >= 0.1` | air/ground branch at 691–699 |
| `randf` | `u32 % 1000`, conversion to float, division by `(1000/max)` | randomized speed/lift/position at 702–708 |
| gravity | `a += tossv`; `tossv -= 0.1`; `a <= base`; `a < PIT_DEPTH` | landing, death, hole, and callback branches at 2738–2749 |
| toss/drop | `tossv = lift`; `a += 0.5` | fall/drop state at 2875–2879 and callers |
| ordinary movement | `x += xdir`, `z += zdir`, speed divisions and bounds | movement and obstacle/hole decisions at 3019–3052, 3878–4000 |
| target/AI | float deltas and strict range comparisons | target and attack-choice branches at 3842–3872 and 4006–4130 |
| attack geometry | float anchors converted to `int`, then integer boxes | hit/no-hit and hit-center positions at 2441–2510 |
| hole geometry | float tilt intermediates from integer coordinates | hole decision at 2591–2610 |
| scroller | float camera targets and `advancey += 0.5` | camera/queue progress at 4749–4827 |
| raster projection | `x-advancex`, `z-a+offset`, mirror projection | sprite coordinates at 2840–2860 |
| source spawn | `(int)advancex` added to authored spawn X | entity initial pixel/world position at 4582–4599 |
| background/panel conversion | float-to-int assignments such as `(advancey+0.5)/2` and `advancex*1.4` | raster tile/panel offsets at 4850–4939 |

Integer conversion is therefore part of the reference, not merely a logging
detail. The source has explicit casts at smartspawn and implicit float-to-int
assignments in hit and raster paths. The bounded Watcom executable probe
observed truncation toward zero for `+1.9` and `-1.9`; no source FPU-control
initialization was found.

Source execution order relevant to numeric visibility is: lost-entity pass,
gravity pass, exact `nextthink == time` AI pass, exact `nextanim == time`
animation pass, alternating collision pass, then displayed-health update
(2718–2835). The outer update consumes each logical tick in order (5035–5047).

## Watcom-specific evidence

The source contains only these relevant pragmas/directives:

- `#pragma pack(4)` in BOR.C line 39.
- `#pragma aux rand32 modify[eax edx] value[eax]`.
- `#pragma aux srand32 parm[eax]` in RAND32.H.
- `.386p` in RAND32.ASM.

No BOR.C/RAND32 source evidence was found for FPU-control-word setup,
`NO87`, `/fp*`, `/op`, `/on`, inline floating-point assembly, or an explicit
rounding mode. No `srand32` call appears in the pinned BOR.C; the RAND32 seed
continues from its static initializer unless omitted external code reseeds it.

The locally available investigation toolchain is Open Watcom C/C++ 1.9:

- `wcc386`/`wcl386` report Open Watcom 1.9.
- `dos4gw.exe` and `pmodew.exe` are installed locally.
- The local binaries are 2010-era Open Watcom release tools, not proof of the
  2004 BOR build.

Using isolated expressions copied from BOR.C, the following configurations
were compiled and run locally: `/fp2`, `/fp3`, `/fpi87`, `/fpc`, `/fp3 /op`,
and `/fp3 /od`. The DOS-target object checks also succeeded for `/bt=dos`
with `/fp3` and `/fpc`.

The inline configurations emitted x87 instructions. Assignment statements in
the gravity probe stored the float objects, while expression temporaries and
returns used the x87 stack. `/fpc` emitted Watcom floating-library calls.
`/op` and `/od` changed code size/layout, but not the bounded results below.
The compiler's integer conversion path used a helper followed by `fistp`;
the helper's exact historical startup/control-word context is not available.

## Candidate results and divergence witnesses

The exact source-shaped probes used:

- gravity: `a=240`, `base=0`, `tossv=1`, 70 repeated source updates;
- `TYPE_NONE` walk: `x=20`, authored speed `9` -> source float `0.9`,
  `randf(3)` residue zero, then ten `x += xdir` updates;
- `randf(40)` with residue input 118;
- casts of `+1.9` and `-1.9`.

All six Watcom configurations produced:

```text
gravity a=42890006 v=c0bffff9 branch=1
anything_walk x=41e7fffe pixel=28 xdir=3f666666
inair a=3f800000 result=1
casts +1.9=1 -1.9=-1
```

The values decode as approximately:

- gravity altitude `68.50004577636719`, velocity `-5.999996662139893`,
  therefore the source `tossv > -6` branch remains true at update 70;
- walk position `28.999996185302734`, therefore integer pixel 28;
- source `randf(40)` probe residue 118 returns `4.71999979`.

The existing exact-rational sidecar gives the contrasting witnesses:

- nominal rational walk reaches exactly 29.0 at update 10, pixel 29;
- nominal rational gravity reaches exactly `-6` at update 70, so the strict
  `>-6` branch is false.

Thus rational arithmetic is rejected as an unconditional source-equivalence
claim. The Watcom candidate family agrees with the conditional binary32-store
direction on these probes, but that does not identify the original executable
or prove every historical register/spill choice.

## Precision and conversion findings

The probes demonstrate all of the following are relevant dimensions:

1. `float` object storage is binary32; repeated stores affect the result.
2. x87 candidates can evaluate through 80-bit registers between stores.
3. the unsuffixed source literal `0.1` is a double constant; the Watcom
   object contains its IEEE-754 binary64 encoding before storing to `tossv`.
4. `/op` changes store policy/code shape, so optimization/store boundaries
   are not recoverable from source alone.
5. `/fpc` uses a distinct software/library path even when this bounded output
   agrees.
6. float-to-int conversion has its own helper/control-word behavior and must
   be tested separately from binary32 motion.

Fused operations were not observed in the x87 candidates. The source/build
evidence does not establish a historical FMA policy. The tested cases do not
distinguish the candidate x87 modes from one another, but they do distinguish
floating evaluation from the existing nominal rational model.

## Provenance classification

### Proven

- BOR V1.0029, date, DOS target, Watcom/DOS4GW or PmodeW target, and absence
  of build instructions from the source-release README.
- The source float fields, expressions, strict comparisons, assignment
  boundaries, integer conversions, execution order, and RAND32 implementation
  in the pinned source files.
- Local Open Watcom 1.9/DOS4GW/PmodeW installation and the object/executable
  results recorded above.

### Strongly inferred

- The original game was likely a 32-bit protected-mode Watcom C build because
  DOS/4GW and PmodeW are named as the target extenders and the source uses
  `.386p`/32-bit-oriented auxiliary assembly.
- An x87-compatible inline path is historically plausible, as is a Watcom
  floating-library path; the source does not select between them.

### Unknown

- Exact Watcom version/release and patch level.
- `/fp2` versus `/fp3` versus `/fpi`/`/fpi87`/`/fpc` and `/op`/optimization
  switches.
- DOS/4GW versus PmodeW for the released executable.
- Linker/startup options, FPU availability, control-word initialization,
  register lifetime/spills, and the actual released executable.
- Any omitted GAMELIB3 floating code, because that source is not included in
  the re-release available here.

## S6 consequence

The numerical family is sufficient to retain bounded source-shaped tests and
to reject the current rational motion as SOURCE_EXACT. It is not sufficient
to certify unrestricted Crab drift, gravity lifecycle, or all float-to-pixel
paths. Those remain blocked outside the common tested domain until either a
historical binary/build configuration or a separately approved canonical
source-numeric contract is provided.

No production runtime change was made. No canonical IEEE contract was
selected. No fixed-point implementation is authorized unless it later proves
observational equivalence at every branch, pixel, velocity, state-transition,
lifetime, and collision point for the selected reference domain.

## Reproduction artifacts

The isolated source probes are retained under:

- `out/bor_compile_s6/watcom_fp_probe.c`
- `out/bor_compile_s6/watcom_fp_source_cases.c`
- `out/bor_compile_s6/watcom_fp_values.c`

They are investigation fixtures only and are not production inputs.
