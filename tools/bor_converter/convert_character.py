#!/usr/bin/env python3
"""Convert a character's idle/walk/attack1 animations through
convert_animation.py's own per-animation pipeline (shared scale, per-frame
placement -- see that module's docstring), but quantize ALL of them into
ONE shared 16-color palette instead of three independent ones.

Why this exists: convert_animation.py already shares a palette *within*
one animation (all of idle's frames quantize together), but each
animation is converted in its own separate CLI invocation, so idle/walk/
attack each end up with their own independently-chosen 16 colors.
main.pasm (via gen_pasm_animset.py) only ever loads ONE of those three
palettes into CGRAM -- today, idle's -- so walk and attack render through
whatever colors idle happened to pick, which is wrong whenever a
character's walk/attack use meaningfully different colors than its idle
(confirmed with both Ralf and JHUN -- see handoff.md). Quantizing all
three animations' frames together fixes this at the source: `palette.txt`
ends up identical across `<prefix>_idle/_walk/_attack`, so
gen_pasm_animset.py's existing `load_palette(idle_dir)` (unchanged) is
already reading the right, now-shared, answer.

Per-animation scale/placement is intentionally left independent (each
animation's geometry is legitimately different -- a walk cycle's stride
needs different framing than an idle stance) -- only the palette step is
combined across animations.

Usage:
    python convert_character.py <pak_path> <entity_txt_entry> <out_prefix>

Example:
    python convert_character.py "Beats of Rage Original [v.3.0 Build 4086].pak" \\
        "DATA\\CHARS\\RALF\\RALF.TXT" out/ralf
    # -> out/ralf_idle/, out/ralf_walk/, out/ralf_attack/ (frameNN.bin,
    #    palette.txt identical across all three, manifest.json, preview.png)
"""
import sys
import os

sys.path.append(os.path.dirname(__file__))
from convert_animation import _load_anim_frames, _quantize_shared, _write_anim_outputs

# (entity anim name, output dir suffix) -- matches the existing out/ralf_*
# / out/jhun_* naming convention already used by convert_animation.py's CLI.
ANIMS = [('idle', '_idle'), ('walk', '_walk'), ('attack1', '_attack')]


def convert_character(pak_path, entity_entry_name, out_prefix):
    loaded = [
        _load_anim_frames(pak_path, entity_entry_name, anim_name, out_prefix + suffix)
        for anim_name, suffix in ANIMS
    ]

    all_canvases = [c for L in loaded for c in L['canvases']]
    all_masks = [m for L in loaded for m in L['masks']]
    palette, all_frame_indices = _quantize_shared(all_canvases, all_masks)

    results = []
    cursor = 0
    for (anim_name, suffix), L in zip(ANIMS, loaded):
        n = len(L['canvases'])
        frame_indices = all_frame_indices[cursor:cursor + n]
        cursor += n
        result = _write_anim_outputs(
            out_prefix + suffix, L['frames_meta'], frame_indices, palette,
            L['entity_name'], anim_name, L['loop'], L['scale'], L['hotspot_canvas'])
        results.append((anim_name, result))

    return results


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)
    pak_path, entity_entry, out_prefix = sys.argv[1:4]
    for anim_name, result in convert_character(pak_path, entity_entry, out_prefix):
        print(f'--- {anim_name} ---')
        for k, v in result.items():
            print(f'{k}: {v}')


if __name__ == '__main__':
    main()
