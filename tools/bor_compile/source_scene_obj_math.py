"""Explicit-context exact opaque/additive OBJ encoding, never source admission.

Banks 0..3 bypass OBJ math; banks 4..7 add the actor-free BG subscreen.
Residuals describe the already source-composited output, not an approximation
of BOR SCREEN. BG priority, subscreen routing and native timing remain unproven.
"""
import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

import numpy as np
from compiler import Source
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from source_scene_obj_raster import prepare, geometry
from raster_bank_search import assign
from raster_palette import schedule, pieces_for_grid, bounded_schedule
from raster_palette_interval import interval_bound


def subdivide_for_limits(pieces, surfaces, height):
    """Choose legal 32x32->8x8 subdivisions under all three OBJ limits."""
    from scipy.optimize import milp, Bounds, LinearConstraint
    choices = []
    for i, piece in enumerate(pieces):
        if piece['width'] != 32 or piece['height'] != 32:
            continue
        actor = surfaces[piece['actor']]
        x, y = piece['local_x'], piece['local_y']
        children = pieces_for_grid(actor['pixels'][y:y+32, x:x+32], (8, 8))
        for child in children:
            child.update(actor=piece['actor'], local_x=x+child['x'], local_y=y+child['y'])
            child['x'] += x + actor['left']; child['y'] += y + actor['top']
            child['rows'] = {yy+y+actor['top']: colors for yy, colors in child['rows'].items() if 0 <= yy+y+actor['top'] < height}
        choices.append((i, children))
    if not choices:
        return pieces, dict(status='NO_SUBDIVISION_CHOICES')
    def costs(objects):
        return np.array([len(objects)] + [sum(p['y'] <= y < p['y']+p['height'] for p in objects) for y in range(height)] + [sum(p['width']//8 for p in objects if p['y'] <= y < p['y']+p['height']) for y in range(height)])
    initial = costs(pieces)
    matrix = np.column_stack([costs(children)-costs([pieces[i]]) for i, children in choices])
    limits = np.array([128]+[32]*height+[34]*height)
    result = milp(matrix[0].astype(float), integrality=np.ones(len(choices)),
                  bounds=Bounds(0, 1), constraints=LinearConstraint(matrix, -np.inf, limits-initial),
                  options={'time_limit': 20})
    info = dict(status='SUBDIVISION_LIMIT' if result.status != 2 else 'THIS_GRID_SUBDIVISION_INFEASIBLE', solver_status=int(result.status))
    if result.x is None:
        return pieces, info
    replacements = {i: children for (i, children), value in zip(choices, result.x) if value > .5}
    selected = [child for i, piece in enumerate(pieces) for child in replacements.get(i, [piece])]
    if np.any(costs(selected) > limits):
        raise AssertionError('SUBDIVISION_HARDWARE_LIMIT_FAULT')
    return selected, dict(status='SUBDIVISION_GEOMETRY_PROVEN', subdivided_objects=len(replacements))


def residual(output, background):
    """Smallest per-channel additive operand; None when addition cannot match."""
    result = 0
    for shift in (0, 5, 10):
        out = (output >> shift) & 31
        bg = (background >> shift) & 31
        if out < bg:
            return None
        result |= (out - bg) << shift
    return result


def add_rgb555(left, right):
    return sum(min(31, ((left >> s) & 31) + ((right >> s) & 31)) << s
               for s in (0, 5, 10))


def split_interval_bound(groups, slots_per_group=60):
    """Both eligibility pools consume the same HBlank, with one CGRAM latch."""
    worst = None
    for start in range(len(groups[0])):
        unions = [set(group[start]) for group in groups]
        for end in range(start+1, len(groups[0])):
            for union, group in zip(unions, groups):
                union.update(group[end])
            commits = sum(max(0, len(union)-slots_per_group) for union in unions)
            required = max(0, 2*commits-1); available = 44*(end-start)
            if worst is None or required-available > worst['signed_byte_deficit']:
                worst = dict(first_line=start, last_line=end, distinct_colors_per_group=[len(u) for u in unions], minimum_new_color_commits=commits, minimum_data_bytes=required, available_data_bytes=available, signed_byte_deficit=required-available)
    return dict(status='CGRAM_DATA_WINDOW_INFEASIBLE' if worst and worst['signed_byte_deficit'] > 0 else 'LOWER_BOUND_DOES_NOT_REJECT', worst_interval=worst, feasibility_proven=False, setup_and_contention_excluded=True)


def minimum_cover(edges, forced):
    """Unit-cost bipartite vertex cover with mandatory opaque identities.

    Pure Python augmenting paths and Konig alternating reachability. Minimizes
    global identity count only, not row traffic or OAM; callers report that limit.
    """
    adjacency = {}
    for normal, additive in sorted(set(edges)):
        if normal not in forced:
            adjacency.setdefault(normal, set()).add(additive)
    left_match, right_match = {}, {}
    for root in adjacency:
        queue = deque([root]); parents = {}; seen = {root}; end = None
        while queue and end is None:
            left = queue.popleft()
            for right in sorted(adjacency[left]):
                if right in parents:
                    continue
                parents[right] = left
                if right not in right_match:
                    end = right
                    break
                other = right_match[right]
                if other not in seen:
                    seen.add(other); queue.append(other)
        while end is not None:
            left = parents[end]; previous = left_match.get(left)
            left_match[left] = end; right_match[end] = left
            end = previous
    reached_left = set(adjacency) - set(left_match)
    reached_right = set(); queue = deque(sorted(reached_left))
    while queue:
        left = queue.popleft()
        for right in adjacency[left]:
            if left_match.get(left) == right or right in reached_right:
                continue
            reached_right.add(right)
            if right in right_match and right_match[right] not in reached_left:
                reached_left.add(right_match[right]); queue.append(right_match[right])
    normal = set(forced) | (set(adjacency) - reached_left)
    additive = reached_right
    if any(n not in normal and a not in additive for n, a in edges):
        raise AssertionError('UNCOVERED_PIXEL_IDENTITY')
    return normal, additive


def probe(source, stage, scene, preference='additive', time_limit=20, geometry_mode='mixed', write_budget=None, cover_policy='minimum'):
    actors, metadata, expected = prepare(source, stage, scene)
    background, _ = compose_rgb8(source, stage, dict(scene, actors=[]))
    background = rgb555(background)
    records = []; edges = set(); forced = set()
    for i, actor in enumerate(actors):
        for y, x in zip(*np.where(actor['pixels'] >= 0)):
            out = int(actor['pixels'][y, x])
            bg = int(background[y + actor['top'], x + actor['left']])
            value = residual(out, bg)
            records.append((i, int(y), int(x), out, bg, value))
            if value is None:
                forced.add(out)
            else:
                edges.add((out, value))
    normal, additive = minimum_cover(edges, forced)
    if cover_policy != 'minimum':
        normal = set(); additive = set()
        for i, y, x, out, bg, value in records:
            math = value is not None and (cover_policy == 'additive' or actors[i]['metadata']['alpha'] != 0)
            (additive if math else normal).add(value if math else out)
    surfaces = []
    for actor in actors:
        for math in (False, True):
            surfaces.append(dict(actor, pixels=np.full_like(actor['pixels'], -1), math=math))
    replay = background.copy()
    for i, y, x, out, bg, value in records:
        math = value is not None and value in additive and (preference == 'additive' or out not in normal)
        if cover_policy == 'source-alpha':
            math = value is not None and actors[i]['metadata']['alpha'] != 0
        elif cover_policy == 'additive':
            math = value is not None
        encoded = value if math else out
        surfaces[i * 2 + int(math)]['pixels'][y, x] = encoded
        decoded = add_rgb555(encoded, bg) if math else encoded
        if decoded != out:
            raise AssertionError('ADDITIVE_IDENTITY_MISMATCH')
        replay[y + actors[i]['top'], x + actors[i]['left']] = decoded
    if not np.array_equal(replay, rgb555(expected)):
        raise AssertionError('FINAL_CONTEXT_IDENTITY_MISMATCH')
    pieces = geometry(surfaces, 'mixed' if geometry_mode == 'adaptive' else geometry_mode)
    subdivision = None
    if geometry_mode == 'adaptive':
        pieces, subdivision = subdivide_for_limits(pieces, surfaces, expected.shape[0])
    for piece in pieces:
        piece['allowed_banks'] = list(range(4, 8) if surfaces[piece['actor']]['math'] else range(4))
    h = expected.shape[0]
    geom = dict(oam_entries=len(pieces),
                peak_sprites_per_line=max(sum(p['y'] <= y < p['y'] + p['height'] for p in pieces) for y in range(h)),
                peak_tile_slivers_per_line=max(sum(p['width'] // 8 for p in pieces if p['y'] <= y < p['y'] + p['height']) for y in range(h)))
    r = dict(schema='BYOR_EXACT_CONTEXT_OBJ_MATH_V1', metadata=metadata, geometry=geom,
             status='ENCODING_PIXEL_IDENTITY_PROVEN', preference=preference, geometry_mode=geometry_mode, subdivision=subdivision,
             selected_global_identities=dict(opaque=len(normal), additive=len(additive)), cover_policy=cover_policy,
             forced_opaque_identities=len(forced), source_visible_pixels=len(records),
             source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
             exact_final_pixel_identity_verified=True, no_color_reduction=True,
             source_context_reachability_proven=False, native_presentation_proven=False,
             alpha_policy='EXACT_SOURCE_RGB8_SCREEN_OUTPUT_ENCODED_AS_OPAQUE_OR_BG_ADDITIVE_RESIDUAL',
             architecture_requirements=['actor-free BG on subscreen', 'OBJ math only on banks 4..7', 'no half math', 'frontpanel priority above OBJ'],
             scope='One explicit pose. Cover policy does not minimize transfer traffic. Saturated channels use the smallest exact residual; alternate saturated operands remain open.')
    groups = []
    for math, banks in ((False, range(4)), (True, range(4, 8))):
        group = [p for p in pieces if p['allowed_banks'] == list(banks)]
        lines = [{c for p in group for c in p['rows'].get(y, [])} for y in range(h)]
        groups.append(lines)
        r['additive_interval_bound' if math else 'opaque_interval_bound'] = interval_bound(lines, slots=60)
    r['shared_hblank_split_interval_bound'] = split_interval_bound(groups)
    if r['shared_hblank_split_interval_bound']['status'] == 'CGRAM_DATA_WINDOW_INFEASIBLE':
        r['status'] = 'THIS_ENCODING_CGRAM_WINDOW_INFEASIBLE'
        return r
    if geom['oam_entries'] > 128 or geom['peak_sprites_per_line'] > 32 or geom['peak_tile_slivers_per_line'] > 34:
        r['status'] = 'CANDIDATE_GEOMETRY_OVERFLOW'
        return r
    assignment = assign(pieces, tuple(range(8)), time_limit, adjacent_write_budget=write_budget, interval_write_budget=write_budget)
    r['bank_search'] = assignment
    if 'assignment' not in assignment:
        r['status'] = assignment['status']
        return r
    bank_groups = [[{c for piece, bank in zip(pieces, assignment['assignment']) if bank == b for c in piece['rows'].get(y, [])} for y in range(h)] for b in range(8)]
    r['fixed_bank_interval_bound'] = split_interval_bound(bank_groups, 15)
    if write_budget is None:
        trace, states = schedule(pieces, assignment['assignment'], h, 16)
    else:
        bounded = bounded_schedule(pieces, assignment['assignment'], h, write_budget=write_budget, lookahead=32, time_limit=time_limit)
        r['bounded_slot_solver'] = {k:v for k,v in bounded.items() if k not in ('trace', 'states')}
        if 'states' not in bounded:
            r.update(status=bounded['status'], pieces=pieces)
            return r
        trace, states = bounded['trace'], bounded['states']
    recovered = [np.full_like(surface['pixels'], -1) for surface in surfaces]
    indices = [np.zeros_like(surface['pixels'], dtype=np.uint8) for surface in surfaces]
    for piece, bank in zip(pieces, assignment['assignment']):
        for y, colors in piece['rows'].items():
            if not set(colors).issubset(states[y][bank]):
                raise AssertionError('SCHEDULE_PIXEL_IDENTITY_MISMATCH')
            surface = surfaces[piece['actor']]; local_y = y-surface['top']
            for x in range(piece['local_x'], min(piece['local_x']+piece['width'], surface['pixels'].shape[1])):
                color = int(surface['pixels'][local_y, x])
                if color >= 0:
                    slot = states[y][bank].index(color)
                    indices[piece['actor']][local_y, x] = slot+1
                    recovered[piece['actor']][local_y, x] = states[y][bank][slot]
    if any(not np.array_equal(surface['pixels'], pixels) for surface, pixels in zip(surfaces, recovered)):
        raise AssertionError('COMPILED_SURFACE_PIXEL_IDENTITY_MISMATCH')
    counts = [line['colors_written'] for line in trace[1:]]
    r.update(status='EXACT_CONTEXT_MATH_SLOT_SCHEDULE_PROVEN', pieces=pieces, trace=trace,
             peak_scheduled_writes=max(counts, default=0), peak_cgram_data_bytes=2 * max(counts, default=0),
             compiled_surface_pixel_identity_verified=True,
             compiled_indices_sha256=[hashlib.sha256(v.tobytes()).hexdigest() for v in indices],
             compiled_schedule_sha256=hashlib.sha256(json.dumps(dict(pieces=pieces, assignment=assignment['assignment'], trace=trace), sort_keys=True).encode()).hexdigest())
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True); p.add_argument('--stage', required=True)
    p.add_argument('--scene', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--preference', choices=('opaque', 'additive'), default='additive')
    p.add_argument('--geometry', choices=('mixed', 'small', 'adaptive'), default='mixed')
    p.add_argument('--time-limit', type=int, default=20)
    p.add_argument('--write-budget', type=int)
    p.add_argument('--cover-policy', choices=('minimum', 'additive', 'source-alpha'), default='minimum')
    a = p.parse_args()
    report = probe(Source(a.source), a.stage, json.loads(a.scene.read_text()), a.preference, a.time_limit, a.geometry, a.write_budget, a.cover_policy)
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'geometry', 'selected_global_identities')}))


if __name__ == '__main__':
    main()
