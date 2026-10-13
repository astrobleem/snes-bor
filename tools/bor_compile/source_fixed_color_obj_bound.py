"""Exact OBJ operands using a selected shared SNES fixed color per scanline.

This expands the actor-free-subscreen family without changing source pixels.
It is a two-class cache experiment, never physical or production admission.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from compiler import Source
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from raster_obj_math_cover import MODES, apply_math, complete_math_cover
from raster_math_mode_liveness import lower_bound, verify_integer_pool
from raster_math_windows import compile_sparse_mask, evaluate


def derive_colors(pixels, policy):
    if policy not in ('zero', 'add-minimum', 'subtract-headroom', 'half-add-bright'):
        raise ValueError('FIXED_COLOR_POLICY')
    grouped = {}
    for y, x, out in pixels:
        grouped.setdefault(y, []).append(out)
    colors = {}
    for y, words in grouped.items():
        channels = []
        for shift in (0, 5, 10):
            values = [word >> shift & 31 for word in words]
            channels.append(0 if policy == 'zero' else min(values) if policy == 'add-minimum'
                            else 31-max(values) if policy == 'subtract-headroom'
                            else max(0, 2*max(values)-31))
        colors[y] = sum(c << s for c, s in zip(channels, (0, 5, 10)))
    return colors


def inputs(actors, background, fixed_colors, modes):
    """Retain ordinary visible words statically; bypass effect=BG exactly."""
    pixels = []
    reserve = set()
    ordinary = []
    bypass = 0
    for actor in actors:
        for ly, lx in zip(*np.where(actor['pixels'] >= 0)):
            y, x = actor['top']+int(ly), actor['left']+int(lx)
            out = int(actor['pixels'][ly, lx])
            if not actor['metadata']['alpha']:
                reserve.add(out)
                ordinary.append((y, x, out))
            elif out == int(background[y, x]):
                bypass += 1
            else:
                pixels.append((y, x, out))
    if fixed_colors is None:
        return pixels, reserve, ordinary, bypass
    if set(fixed_colors) != {y for y, x, out in pixels} or any(
            type(y) is not int or type(c) is not int or not 0 <= c < 32768
            for y, c in fixed_colors.items()):
        raise ValueError('FIXED_COLOR_ROW_DOMAIN')
    options, cover = complete_math_cover(((out, fixed_colors[y]) for y, x, out in pixels),
                                        modes=modes, tag_modes=True)
    rows = [{mode: set() for mode in modes} for _ in background]
    window_pixels = [[] for _ in background]
    for y, x, out in pixels:
        choices = {mode: tuple(options[mode, out, fixed_colors[y]]) for mode in modes}
        for mode, words in choices.items():
            # Check the actual operation, independently of cover signatures.
            if any(apply_math(c, fixed_colors[y], mode) != out for c in words):
                raise AssertionError('FIXED_COLOR_OPERAND_REPLAY')
            rows[y][mode].add((out, words))
        window_pixels[y].append(dict(x=x, output=out, modes=choices))
    return pixels, reserve, ordinary, bypass, rows, window_pixels, cover


def replay(bound, rows, window_pixels, fixed_colors, pixels, ordinary, background, expected,
           control_choices=None):
    verify_integer_pool(bound, rows, window_pixels=window_pixels)
    states = {int(y): {int(k): set(cs) for k, cs in state.items()}
              for y, state in bound['selected_palette_residency'].items()}
    modes = {int(y): mode for y, mode in bound['selected_modes'].items()}
    if control_choices is not None:
        selected = {y: control_choices[y][label] for y, label in modes.items()}
        fixed_colors = {y: c for y, (mode, c) in selected.items()}
        modes = {y: mode for y, (mode, c) in selected.items()}
    masks = {int(y): {int(x): v for x, v in mask.items()}
             for y, mask in bound.get('selected_window_eligibility', {}).items()}
    descriptors = {y: compile_sparse_mask(masks[y], bound.get('positive_union_with_disabled_edges_only', False)) if y in masks else compile_sparse_mask({0: 1})
                   for y in modes}
    rendered = background.copy()
    for y, x, out in pixels:
        if out in states[y][0]:
            value = out
        else:
            enabled = evaluate(descriptors[y], x)
            values = [apply_math(c, fixed_colors[y], modes[y]) if enabled else c
                      for c in states[y][1]]
            if out not in values:
                raise AssertionError('FIXED_COLOR_SOURCE_PIXEL_REPLAY')
            value = out
        rendered[y, x] = value
    for y, x, out in ordinary:
        if y in states and out not in states[y][0]:
            raise AssertionError('FIXED_COLOR_ORDINARY_RESIDENCY_REPLAY')
        if out not in set(bound['reserved_normal_colors']):
            raise AssertionError('FIXED_COLOR_ORDINARY_STATIC_REPLAY')
        rendered[y, x] = out
    if not np.array_equal(rendered, expected):
        raise AssertionError('FIXED_COLOR_COMPLETE_VIEWPORT_REPLAY')
    return dict(viewport_pixels_replayed=int(expected.size),
                source_rgb555_sha256=hashlib.sha256(rendered.astype('<u2').tobytes()).hexdigest(),
                encoded_effect_pixels_replayed=len(pixels), ordinary_pixels_replayed=len(ordinary),
                compiled_color_window_descriptors=descriptors,
                fixed_color_rgb555_rows=fixed_colors, selected_math_modes=modes,
                fixed_color_register_bytes={y: [0x20 | (c & 31), 0x40 | (c >> 5 & 31),
                                               0x80 | (c >> 10 & 31)]
                                           for y, c in fixed_colors.items()},
                cgwsel_add_subscreen=False, main_screen_clipping=False,
                palette_bank_assignment_proven=False, physical_transfer_admitted=False,
                native_timing_admitted=False)


def measure(source, stage, scene, policy='add-minimum', modes=('add',), time_limit=60,
            integer_budget=None, fixed_colors=None, hardware_windows=True,
            candidate_policies=None, positive_windows_only=False):
    if not modes or any(m not in MODES for m in modes):
        raise ValueError('FIXED_COLOR_MODE_DOMAIN')
    if positive_windows_only and not hardware_windows:
        raise ValueError('FIXED_COLOR_POSITIVE_WINDOWS_REQUIRE_WINDOWS')
    if candidate_policies is not None and (fixed_colors is not None or not candidate_policies
            or len(set(candidate_policies)) != len(candidate_policies)):
        raise ValueError('FIXED_COLOR_CANDIDATE_POLICY')
    actors, metadata, expected_rgb8 = prepare(source, stage, scene)
    expected = rgb555(expected_rgb8)
    background = rgb555(compose_rgb8(source, stage, dict(scene, actors=[]))[0])
    pixels, reserve, ordinary, bypass = inputs(actors, background, None, modes)
    if not pixels:
        raise ValueError('FIXED_COLOR_EFFECT_DEMAND_REQUIRED')
    if fixed_colors is None and candidate_policies is None:
        fixed_colors = derive_colors(pixels, policy)
    if candidate_policies is None:
        pixels, reserve, ordinary, bypass, rows, window_pixels, cover = inputs(
            actors, background, fixed_colors, modes)
    control_choices = None
    domains = None
    if candidate_policies is not None:
        rows = [{} for _ in background]
        window_pixels = [[] for _ in background]
        control_choices = {y: {} for y, x, out in pixels}
        domains = {}
        cover = {}
        for candidate_policy in candidate_policies:
            candidate_colors = derive_colors(pixels, candidate_policy)
            *_, candidate_rows, candidate_pixels, candidate_cover = inputs(
                actors, background, candidate_colors, modes)
            domains[candidate_policy] = candidate_colors
            cover[candidate_policy] = candidate_cover
            for y, row in enumerate(candidate_rows):
                if y not in candidate_colors:
                    continue
                for mode, requirements in row.items():
                    label = candidate_policy+':'+mode
                    rows[y][label] = requirements
                    control_choices[y][label] = (mode, candidate_colors[y])
                if not window_pixels[y]:
                    window_pixels[y] = [dict(x=p['x'], output=p['output'], modes={})
                                        for p in candidate_pixels[y]]
                for pixel, candidate in zip(window_pixels[y], candidate_pixels[y]):
                    if (pixel['x'], pixel['output']) != (candidate['x'], candidate['output']):
                        raise AssertionError('FIXED_COLOR_CANDIDATE_SOURCE_COVERAGE')
                    pixel['modes'].update({candidate_policy+':'+m: cs
                                          for m, cs in candidate['modes'].items()})
    if not hardware_windows:
        window_pixels = None
    options = {} if integer_budget is None else dict(integer_modes=True, integer_windows=hardware_windows,
        integer_palette=True, integer_backend='cp-sat', write_budget=integer_budget,
        minimum_transfer_window=357)
    bound = lower_bound(rows, window_pixels=window_pixels, reserved_normal_colors=reserve,
                        time_limit=time_limit, explicit_pixel_paths=hardware_windows,
                        positive_windows_only=positive_windows_only, **options)
    report = dict(schema='BYOR_FIXED_COLOR_OBJ_CACHE_EXPERIMENT_V1', status=bound['status'],
        source_rgb555_sha256=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest(),
        source_pak_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),
        scene=scene, source_metadata=metadata,
        fixed_color_policy=policy if domains is None else 'JOINT_SELECTED_GUIDES',
        candidate_fixed_color_domains=domains,
        fixed_color_choice_relaxed=bool(candidate_policies) and integer_budget is None,
        hardware_window_masks_modeled=hardware_windows,
        fixed_color_rgb555_rows=fixed_colors, allowed_math_modes=list(modes),
        ordinary_visible_words_statically_reserved=sorted(reserve), reserved_word_count=len(reserve),
        effect_pixels_equal_to_background=bypass, effect_pixels_with_operand_requirements=len(pixels),
        ordinary_visible_pixels=len(ordinary), operand_cover=cover, cache_bound=bound,
        source_alpha_policy='BOR4086_SCREEN_RGB8_THEN_RGB555', no_color_reduction=True,
        fixed_color_and_math_window_control_deadlines_proven=False,
        physical_transfer_admitted=False, native_timing_admitted=False,
        universal_raster_rejected=False,
        scope='Selected shared fixed colors; 60/60 class capacity, static ordinary words. '
              'Fixed banks, slots, OAM geometry, CHR, control setup, native timing and gameplay unproved.')
    if bound.get('integer_pool_pixel_coverage_verified'):
        report['independent_source_replay'] = replay(bound, rows, window_pixels, fixed_colors,
                                                   pixels, ordinary, background, expected, control_choices)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--policy', choices=('zero', 'add-minimum', 'subtract-headroom', 'half-add-bright'), default='add-minimum')
    parser.add_argument('--math-mode', action='append', choices=MODES)
    parser.add_argument('--time-limit', type=float, default=60)
    parser.add_argument('--integer-budget', type=int)
    parser.add_argument('--fixed-colors', type=Path)
    parser.add_argument('--no-windows', action='store_true')
    parser.add_argument('--positive-windows-only', action='store_true')
    parser.add_argument('--candidate-policy', action='append', choices=('zero', 'add-minimum', 'subtract-headroom', 'half-add-bright'),
                        help='Choose one shared fixed-color guide per scanline jointly with its math mode; repeat to expand the domain.')
    args = parser.parse_args()
    fixed = {int(y): c for y, c in json.loads(args.fixed_colors.read_text()).items()} if args.fixed_colors else None
    result = measure(Source(args.source), args.stage, json.loads(args.scene.read_text()),
                     args.policy, tuple(args.math_mode or ('add',)), args.time_limit,
                     args.integer_budget, fixed, not args.no_windows, args.candidate_policy,
                     args.positive_windows_only)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result['cache_bound'][k] for k in ('status', 'variables', 'constraints',
        'validated_dual_lower_bound', 'peak_replayed_pool_writes', 'solver_seconds') if k in result['cache_bound']}))


if __name__ == '__main__':
    main()
