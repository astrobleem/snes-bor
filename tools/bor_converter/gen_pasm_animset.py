#!/usr/bin/env python3
"""Emits the Poppy source fragments main.pasm hand-writes per shipped
character (constants, the Anim_Play_Idle/Walk/Attack dispatch bodies, the
idle/attack .incbin labels, the CGRAM palette-load block, and the walk
.incbin line for the `.org $8C00` TAD-gap block) from a character's three
converted animation directories (`convert_animation.py` output: idle/walk/
attack, each `manifest.json` + `frameNN.bin` + `palette.txt`).

Why a generator that emits hand-written-*looking* code, not a runtime data
table: this project's Poppy assembler build silently miscompiles standalone
`.dw` tables and indexed-long addressing to ROM data labels regardless of
placement (see poppy_assembler_bugs.md / main.pasm's own header comments
near ANIM_FRAME_COUNT). The only proven-safe shape is exactly what's
hand-written in main.pasm today: an unrolled `cmp #N / beq` compare chain
per animation, wrapped in the project's standard nop-padding workarounds
for Poppy's branch-target/label-off-by-one bugs. This script automates
*producing* that shape from a character's manifest data -- it does not
replace it with a table.

Deliberately NOT generalized here (see handoff.md / the plan that produced
this script for why): only idle/walk/attack are supported (matching what
main.pasm's scaffolding -- Anim_Play's dispatcher, Anim_UpdateFacing,
Anim_CommitFrame -- expects), attack is assumed non-looping (manifest
loop=0, reverts to idle on completion) and idle/walk looping (loop=1,
wraps). Palette: this script always reads the **idle** dir's palette.txt
by convention -- as of the palette-unification fix (see handoff.md),
convert_character.py writes an identical, jointly-quantized palette.txt
into all three of a character's idle/walk/attack dirs, so reading idle's
copy is correct, not just convenient. If a character's assets were instead
produced by convert_animation.py's standalone single-anim CLI (each
animation quantized independently), this script will still only load
idle's palette and walk/attack will render through it -- use
convert_character.py, not three separate convert_animation.py calls, to
get a character whose animations share one palette.

Per-animation delay: manifests can carry a different delay per frame
(e.g. Ralf's attack1: 7,7,20,10,10) but main.pasm bakes ONE delay constant
per animation (matching Anim_TickCounter being shared, single-valued WRAM
state, not a per-frame table -- see the same no-data-table constraint
above). This script uses the MEDIAN of the manifest's per-frame delays,
confirmed against Ralf's existing shipped constants to reproduce all three
current values (idle=10, walk=8, attack=10) exactly, including attack's
non-uniform case (median of [7,7,20,10,10] = 10, matching; a plain mean
would give 10.8, wrong).

Usage:
    python gen_pasm_animset.py <char_id> <out_base_prefix> <out_dir>

    <char_id>        short identifier used only for progress messages
                      (e.g. "ralf", "jhun") -- NOT baked into any label
                      name (labels are the character-independent
                      AnimCharIdleFrames/AnimCharAttackFrames -- see below).
    <out_base_prefix> e.g. "out/ralf" or "out/jhun" -- expects
                      <prefix>_idle/, <prefix>_walk/, <prefix>_attack/
                      (convert_animation.py's own output convention) each
                      containing manifest.json + palette.txt (idle only).
    <out_dir>         directory to write the two generated fragments into:
                      animset.pasm (constants + Anim_Play_* bodies + idle/
                      attack labels+incbin + palette block) and
                      walk_org8c00.pasm (the walk .incbin line for the
                      `.org $8C00` block -- paste alongside the two
                      character-independent tilemap-flip .incbin lines,
                      which this script does NOT emit; see handoff.md).

Asset .bin filenames referenced by the generated .incbin lines follow the
existing convention: assets/anim_<char_id>_{idle,walk,attack}.bin -- bake
those first with bake_vram_frames.py before assembling against this
fragment.

Labels are intentionally NOT character-specific (AnimCharIdleFrames /
AnimCharAttackFrames, not e.g. AnimJhunIdleFrames) -- only one character's
data ever ships in ROM at a time (see handoff.md: two characters' data
cannot coexist in this project's ROM budget), so the label just needs to be
a stable name for main.pasm's hand-written scaffolding (Anim_Play_Idle/
Walk/Attack's own bodies, which THIS script also regenerates, so the label
is consistently used) to reference; renaming it per character would only
add churn.
"""
import json
import os
import statistics
import sys


NOP_LABEL_OFFBYONE = "    nop                     ; workaround: Poppy label address off-by-one (see poppy bug #4)\n"
NOP_BRANCH_TARGET = "    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)\n"


def load_manifest(anim_dir):
    with open(os.path.join(anim_dir, "manifest.json"), "r", encoding="utf-8") as f:
        m = json.load(f)
    frame_count = len(m["frames"])
    delays = [f["delay"] for f in m["frames"]]
    delay = int(round(statistics.median(delays)))
    return frame_count, delay


def load_palette(anim_dir):
    """Parse a convert_animation.py palette.txt (16 lines of `lda #$imm16`)
    into 16 integer BGR555 values, in CGRAM color-index order."""
    values = []
    with open(os.path.join(anim_dir, "palette.txt"), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            assert line.startswith("lda #$"), f"unexpected palette.txt line: {line!r}"
            values.append(int(line[len("lda #$"):], 16))
    assert len(values) == 16, f"expected 16 palette colors, got {len(values)}"
    return values


def gen_looping_anim(routine_name, delay_const, count_const, frame_count,
                      base_expr_fn):
    """Anim_Play_Idle/Anim_Play_Walk shape: decrement tick counter, on
    expiry advance+wrap the frame index, dispatch via an unrolled
    cmp/beq compare chain to one `lda #<source addr> / jsr Anim_CommitFrame
    / rts` arm per frame."""
    out = []
    out.append(NOP_LABEL_OFFBYONE)
    out.append(f"{routine_name}:\n")
    out.append("    sep #$20\n.a8\n")
    out.append("    lda.l Anim_TickCounter\n    dec a\n    sta.l Anim_TickCounter\n")
    out.append(f"    beq {routine_name}__advance\n")
    out.append("    brl Anim_Done   ; too far for an 8-bit bne from here\n")
    out.append(NOP_BRANCH_TARGET)
    out.append(f"{routine_name}__advance:\n\n")
    out.append(f"    lda #{delay_const}\n    sta.l Anim_TickCounter\n\n")
    out.append("    lda.l Anim_FrameIndex\n    inc a\n    sta.l Anim_FrameIndex\n")
    out.append(f"    cmp #{count_const}\n")
    out.append(f"    bcc {routine_name}__frame_ok\n")
    out.append("    lda #0\n    sta.l Anim_FrameIndex        ; wrap (manifest loop=1)\n")
    out.append(NOP_BRANCH_TARGET)
    out.append(f"{routine_name}__frame_ok:\n\n")
    out.append("    ; frame_index -> source ROM address, via compare chain (no data table,\n")
    out.append("    ; no indexed-long addressing to a ROM data label -- both silently\n")
    out.append("    ; miscompile in this Poppy build; see poppy_assembler_bugs.md).\n")
    out.append("    lda.l Anim_FrameIndex\n")
    for i in range(frame_count - 1):
        out.append(f"    cmp #{i}\n    beq {routine_name}__f{i}\n")
    out.append(f"    bra {routine_name}__f{frame_count - 1}\n")
    out.append(NOP_BRANCH_TARGET)
    for i in range(frame_count):
        out.append(f"{routine_name}__f{i}:\n")
        out.append("    rep #$20\n.a16\n")
        out.append(f"    lda #{base_expr_fn(i)}\n")
        out.append("    jsr Anim_CommitFrame\n    rts\n")
        if i != frame_count - 1:
            out.append(NOP_BRANCH_TARGET)
    return "".join(out)


def gen_attack_anim(routine_name, delay_const, count_const, frame_count,
                     base_expr_fn):
    """Anim_Play_Attack shape: same tick-counter gate, but on frame overflow
    reverts Anim_Selected to idle (forcing an immediate re-render) instead
    of wrapping -- manifest loop=0, non-looping cycle."""
    out = []
    out.append(NOP_LABEL_OFFBYONE)
    out.append(f"{routine_name}:\n")
    out.append("    sep #$20\n.a8\n")
    out.append("    lda.l Anim_TickCounter\n    dec a\n    sta.l Anim_TickCounter\n")
    out.append(f"    beq {routine_name}__advance\n")
    out.append("    brl Anim_Done   ; too far for an 8-bit bne from here\n")
    out.append(NOP_BRANCH_TARGET)
    out.append(f"{routine_name}__advance:\n\n")
    out.append("    lda.l Anim_FrameIndex\n    inc a\n")
    out.append(f"    cmp #{count_const}\n")
    out.append(f"    bcc {routine_name}__frame_ok\n")
    out.append("    ; Animation finished -- revert to idle instead of wrapping.\n")
    out.append("    lda #0\n    sta.l Anim_Selected\n")
    out.append("    lda #$FF\n    sta.l Anim_FrameIndex\n")
    out.append("    lda #1\n    sta.l Anim_TickCounter\n")
    out.append("    brl Anim_Done\n")
    out.append(NOP_BRANCH_TARGET)
    out.append(f"{routine_name}__frame_ok:\n")
    out.append("    sta.l Anim_FrameIndex\n")
    out.append(f"    lda #{delay_const}\n    sta.l Anim_TickCounter\n\n")
    out.append("    ; frame_index -> source ROM address, via compare chain (no data table,\n")
    out.append("    ; no indexed-long addressing to a ROM data label -- both silently\n")
    out.append("    ; miscompile in this Poppy build; see poppy_assembler_bugs.md).\n")
    out.append("    lda.l Anim_FrameIndex\n")
    for i in range(frame_count - 1):
        out.append(f"    cmp #{i}\n    beq {routine_name}__f{i}\n")
    out.append(f"    bra {routine_name}__f{frame_count - 1}\n")
    out.append(NOP_BRANCH_TARGET)
    for i in range(frame_count):
        out.append(f"{routine_name}__f{i}:\n")
        out.append("    rep #$20\n.a16\n")
        out.append(f"    lda #{base_expr_fn(i)}\n")
        out.append("    jsr Anim_CommitFrame\n    rts\n")
        if i != frame_count - 1:
            out.append(NOP_BRANCH_TARGET)
    return "".join(out)


def gen_palette_block(values):
    out = []
    out.append("    ; --- CGRAM palette row 0 ---\n")
    out.append("    ; Inline immediates (16 explicit lda #imm loads) -- no ROM data table\n")
    out.append("    ; at all this time, not just non-indexed addressing. cgram_table as a\n")
    out.append("    ; standalone .dw block, placed either at the tail of the file or right\n")
    out.append("    ; after the .incbin, or before scpu_boot, kept assembling to wrong or\n")
    out.append("    ; corrupted bytes regardless of placement or of avoiding `,x`-indexed\n")
    out.append("    ; reads (see poppy_assembler_bugs.md). Baking the 16 BGR555 values\n")
    out.append("    ; directly into the instruction stream as immediates sidesteps data-\n")
    out.append("    ; table emission entirely.\n")
    out.append("    stz $2121               ; CGRAM address = color 0\n")
    out.append("    rep #$20\n.a16\n")
    for v in values:
        out.append(f"    lda #${v:04X}\n")
        out.append("    sep #$20\n.a8\n")
        out.append("    sta $2122\n    xba\n    sta $2122\n")
        out.append("    rep #$20\n.a16\n")
    return "".join(out)


def main():
    if len(sys.argv) != 4:
        print("usage: gen_pasm_animset.py <char_id> <out_base_prefix> <out_dir>")
        raise SystemExit(1)
    char_id, base_prefix, out_dir = sys.argv[1:4]

    idle_dir = f"{base_prefix}_idle"
    walk_dir = f"{base_prefix}_walk"
    attack_dir = f"{base_prefix}_attack"

    idle_count, idle_delay = load_manifest(idle_dir)
    walk_count, walk_delay = load_manifest(walk_dir)
    attack_count, attack_delay = load_manifest(attack_dir)
    palette = load_palette(idle_dir)

    idle_bin = f"assets/anim_{char_id}_idle.bin"
    walk_bin = f"assets/anim_{char_id}_walk.bin"
    attack_bin = f"assets/anim_{char_id}_attack.bin"

    lines = []
    lines.append(f"ANIM_FRAME_COUNT = {idle_count}\n")
    lines.append(f"ANIM_FRAME_DELAY = {idle_delay}        ; ticks (main-loop frames) per idle frame\n")
    lines.append(f"WALK_FRAME_COUNT = {walk_count}\n")
    lines.append(f"WALK_FRAME_DELAY = {walk_delay}         ; ticks (main-loop frames) per walk frame\n")
    lines.append(f"ATTACK_FRAME_COUNT = {attack_count}\n")
    lines.append(f"ATTACK_FRAME_DELAY = {attack_delay}      ; ticks; median of the manifest's per-frame delays\n")
    lines.append("ANIM_LABEL_FIXUP = 1\n")
    lines.append("ANIM_ATTACK_BASE_OFFSET = ANIM_FRAME_COUNT * ANIM_FRAME_BYTES   ; = idle\n")
    lines.append("                              ; blob's total size; AnimCharAttackFrames's\n")
    lines.append("                              ; .incbin immediately follows AnimCharIdleFrames's\n")
    lines.append("                              ; with no gap, so this is its exact byte offset\n")
    lines.append("\n")

    def frame_bytes_suffix(i):
        # Matches the existing hand-written convention exactly: frame 0 has
        # no suffix, frame 1 is the bare "+ ANIM_FRAME_BYTES" (implicit *1,
        # no literal "*1"), frame 2+ use the explicit "*N" multiplier.
        if i == 0:
            return ""
        if i == 1:
            return " + ANIM_FRAME_BYTES"
        return f" + ANIM_FRAME_BYTES*{i}"

    def idle_base_expr(i):
        return "AnimCharIdleFrames + ANIM_LABEL_FIXUP" + frame_bytes_suffix(i)

    def walk_base_expr(i):
        return "ANIM_WALK_BASE" + frame_bytes_suffix(i)

    def attack_base_expr(i):
        return "AnimCharIdleFrames + ANIM_LABEL_FIXUP + ANIM_ATTACK_BASE_OFFSET" + frame_bytes_suffix(i)

    lines.append(gen_looping_anim("Anim_Play_Idle", "ANIM_FRAME_DELAY", "ANIM_FRAME_COUNT", idle_count, idle_base_expr))
    lines.append("\n")
    lines.append(gen_looping_anim("Anim_Play_Walk", "WALK_FRAME_DELAY", "WALK_FRAME_COUNT", walk_count, walk_base_expr))
    lines.append("\n")
    lines.append(gen_attack_anim("Anim_Play_Attack", "ATTACK_FRAME_DELAY", "ATTACK_FRAME_COUNT", attack_count, attack_base_expr))
    lines.append("\n")
    lines.append("AnimCharIdleFrames:\n")
    lines.append(f'    .incbin "{idle_bin}"\n')
    lines.append("AnimCharAttackFrames:\n")
    lines.append(f'    .incbin "{attack_bin}"\n')
    lines.append("\n")
    lines.append(gen_palette_block(palette))

    os.makedirs(out_dir, exist_ok=True)
    animset_path = os.path.join(out_dir, "animset.pasm")
    with open(animset_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(lines))

    walk_org_path = os.path.join(out_dir, "walk_org8c00.pasm")
    with open(walk_org_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f'    .incbin "{walk_bin}"        ; {walk_count} frames * 768 = {walk_count*768} bytes\n')

    print(f"idle:   {idle_count} frames, delay={idle_delay}")
    print(f"walk:   {walk_count} frames, delay={walk_delay}")
    print(f"attack: {attack_count} frames, delay={attack_delay}")
    print(f"wrote {animset_path}")
    print(f"wrote {walk_org_path}")


if __name__ == "__main__":
    main()
