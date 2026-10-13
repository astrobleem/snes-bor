# Bounded native MOTU movement and component display

The immediate controller-to-pixel slice passes. One ROM receives actual JOY1
input, moves a persistent constructor-owned He_ManB through the existing source
ground/frame/velocity/check_move services, seals canonical world snapshots, and
uses those snapshots to select and publish admitted component contexts. All 12
observed displays match independently composed source RGB555 pixels: 688,128
pixels, zero mismatches. Receipt: [native movement component](receipts/byor-motu-native-movement-component.json).

Four right requests move X from 80 to 82; five up requests move Z from 220 to
218.75. Releasing the controller stops displacement and selects actual IDLE.
WALK/frame-zero comparisons at epochs 1/2, 3/4 and 9/10 isolate position-driven
pixel changes from animation changes. Subpixel positions that project to the
same integer screen coordinate correctly retain the same pixels.
The same-pose comparison is retained at [X=80.5](receipts/byor-motu-movement-walk-80_5.png)
and [X=81](receipts/byor-motu-movement-walk-81.png).

## Ownership and binding

`m4_animation_callback_owner_native.py --live-ground` reuses the complete
constructor/model/script/default-init path and its generation-checked player
state and RUN capture. Its new native owner retains that player across requests.
Initial position (80,220,0), empty collision environment and fixed camera are
controlled fixture inputs, not an authored stage-spawn certification. Lua installs
source-derived readonly tables and constructor inputs once. It does not write
input masks, velocities, actor positions or animation frames during movement.

The native hardware bridge feeds `PlayerHistory_Refresh`. Source ground services
capture canonical state, execute mandatory real animation/frame continuations,
and publish velocities. The existing signed velocity accumulator and check_move
publish world positions under explicit phase leases. The independently checked
Q16 product is `velocity * mobility / 2^17`; these sample values are exactly
representable. The same source pointer survives every epoch.

The 80-byte canonical view and 64-byte sidecar are copied before publishing the
snapshot epoch. The host compositor reads only those sealed snapshots, resolves
native animation handles back to authored roles/frames, and uses the existing
RGB8 source compositor before RGB555 decomposition. These twelve contexts form
a finite native admission set, indexed by altitude, direction, position, model,
animation handle and frame, rather than by field count or input-script ordinal.
Native replay produces byte-identical snapshots to the compiler inputs.

`m4_bounded_component_publisher.py` reuses the existing component renderer's
generated bootstrap/DMA instructions and data. It changes ROM source pointers
for the admitted data and supplies a checked ownership handoff. The authorized
64-KiB VRAM allocation remains HIGH CHR 0..49151, LOW CHR 49152..61439 and maps
61440..65535. There is no additional OBJ arena, color reduction, SCREEN
approximation, artwork shrinking or removal of source foreground layers.

Publication uses forced blank for complete CHR/maps/palette replacement. The
previous bootstrap windows are retired, the component owner supplies its NMI,
and completion is published after DMA. A real left input outside the admitted
tuple set faults explicitly, leaves the displayed epoch unchanged and retains
the previous independently verified picture.

## Regression and limits

The retained passing 75-field control remains the reference. Its ROM and compiler
inputs were hash-checked; its unchanged native experiment was not rerun. Twenty-one
focused tests pass, including snapshot identity, stable actor/controller/delta
checks and the existing eighteen component regressions. All 29 inherited dirty
tracked files retain their original SHA256, including main.bin/main.sym/main.pansy.

This proves bounded native ground movement and displayed pixels. It does not
prove the complete player controller prefix, SourceWorldTick traversal/200-Hz
scheduling, natural timed WALK animation, stage collision/camera/spawn integration,
general online composition or tile-cache publication, production presentation
cadence, authored audio, breath lifecycle, HUD or complete MOTU Demo. Publication
waits in this bounded run are 3..7 fields, including complete forced-blank uploads;
they are not a production latency/deadline admission.

The next step is to replace finite tuple admission with the existing returning
graphics/online bundle producer driven by authoritative snapshots, and join the
complete controller/world owner. The authorized component direction remains in
force. OBJ-only raster research is not a prerequisite.

## Reproduce

Run from the repository root, with a new output directory:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_live_ground_component_native.py `
  --source 'Masters of the Universe [v.3.0 Build 4086].pak' `
  --output out/byor-motu-movement-component-NEW
out/byor-motu-solver-venv/Scripts/python.exe -m unittest `
  test_m4_live_ground_component test_component_live_bundle test_m4_component_publication `
  test_bg_component_residency test_bg_component_deadlines test_bg_components -v
```

The driver links the already assembled source binary with header/vectors, without
reassembling or changing protected source artifacts. It reuses the retained
assembled binary/symbol identities recorded in the receipt; the proof is specific
to those inputs. It reuses the retained
matching MSU; if that file has reached the Windows hardlink limit it copies only
that MSU into the new private output. No PCM copies or protected-output regeneration
are performed.

Engineering failures retained during integration included a bare binary without
header/vectors, mismatched bootstrap MSU, residual type-1 character conversion
returning converted bytes in place of BW-RAM controls, stale optional-service and
freeze readiness, and retained bootstrap side windows. These were resolved in
the bounded owner. No external limit was reached or claimed.
