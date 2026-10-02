"""Lossless compile-time placement for 16x32 SNES OBJ tile footprints."""


def _physical_origins(tile_width, tile_height):
    """Mode-6 16x16 OBJ-name-table footprints across both name tables."""
    origins, footprints = [], []
    for table in range(2):
        for y in range(17 - tile_height):
            for x in range(17 - tile_width):
                origins.append(table * 256 + y * 16 + x)
                footprints.append([
                    table * 256 + (y + row) * 16 + x + col
                    for row in range(tile_height) for col in range(tile_width)
                ])
    return origins, footprints


def place_full_obj(blocks, attempts=8, steps=100000, candidate_count=64):
    """Place 16x32 OBJ blocks in the complete 512-tile OBJ address space.

    Each input is eight exact 8x8 SNES tiles. A candidate origin reserves a
    2x4 footprint at legal 16x32 OBJ row/column stride. Overlap is permitted
    only when the tile bytes are identical. Search exhaustion is explicitly
    not an unsatisfiability proof.
    """
    import numpy as np

    ordered = sorted(set(blocks))
    if any(len(block) != 256 for block in ordered):
        raise ValueError('FULL_OBJ_BLOCK_SIZE')
    # Palette-masked frames often need arbitrary 2x4 overlaps rather than
    # whole-row chains. Try exact greedy and bounded min-conflicts before the
    # heavier MILP; the older full-origin local search could spend hundreds
    # of thousands of redundant steps before trying these better solvers.
    try:
        greedy = _greedy_full_obj(ordered, attempts=max(24, attempts),
                                  return_partial=True)
        if greedy[0] is not None:
            return greedy
        try:
            return _anneal_rect_obj(ordered, 2, 4, restarts=8,
                                    steps=min(steps, 30000))
        except ValueError:
            pass
    except ValueError:
        greedy = (None, ({}, {}))

    try:
        return _solve_full_obj_milp(ordered, time_limit=45)
    except ValueError:
        pass
    partial_origins, _ = greedy[1]
    try:
        return _place_all_origins(ordered, attempts=min(attempts, 2),
                                  steps=min(steps, 10000),
                                  initial_origins=partial_origins)
    except ValueError:
        pass
    vocabulary = {tile: i for i, tile in enumerate(sorted(
        {block[n:n + 32] for block in ordered
         for n in range(0, len(block), 32)}))}
    block_tiles = np.asarray([
        [vocabulary[block[n:n + 32]] for n in range(0, 256, 32)]
        for block in ordered], dtype=np.int16)
    origin_list, footprint_list = _physical_origins(2, 4)
    origins = np.asarray(origin_list, dtype=np.int16)
    cells = np.asarray(footprint_list, dtype=np.int16)

    for seed in range(attempts):
        rng = np.random.default_rng(seed)
        positions = rng.integers(0, len(origins), len(ordered))
        counts = np.zeros((512, len(vocabulary)), dtype=np.int16)
        totals = np.zeros(512, dtype=np.int16)
        for index, position in enumerate(positions):
            counts[cells[position], block_tiles[index]] += 1
            totals[cells[position]] += 1
        tabu = np.zeros((len(ordered), len(origins)), dtype=np.int32)

        for step in range(min(steps, 30000)):
            conflicts = (totals[cells[positions]] -
                         counts[cells[positions], block_tiles]).sum(axis=1)
            if not int(conflicts.sum()):
                result = {block: int(origins[position])
                          for block, position in zip(ordered, positions)}
                grid = {}
                for block, origin in result.items():
                    x, y = origin % 16, origin // 16
                    for tile_index in range(8):
                        cell = (origin // 256) * 256 + (y % 16 + tile_index // 2) * 16 + x + tile_index % 2
                        tile = block[tile_index * 32:(tile_index + 1) * 32]
                        if cell in grid and grid[cell] != tile:
                            raise AssertionError('FULL_OBJ_OVERLAP_MISMATCH')
                        grid[cell] = tile
                if len(result) != len(ordered) or any(not 0 <= cell < 512 for cell in grid):
                    raise AssertionError('FULL_OBJ_PLACEMENT_RANGE')
                return result, grid

            active = np.flatnonzero(conflicts)
            index = (int(rng.choice(active)) if step % 13
                     else int(rng.integers(len(ordered))))
            old = positions[index]
            counts[cells[old], block_tiles[index]] -= 1
            totals[cells[old]] -= 1
            candidates = rng.integers(0, len(origins), candidate_count)
            candidate_cells = cells[candidates]
            score = (totals[candidate_cells]
                     - counts[candidate_cells, block_tiles[index]]).sum(axis=1)
            score = score.astype(float)
            score[tabu[index, candidates] > step] += 1000
            minimum = score.min()
            best_candidates = candidates[score == minimum]
            new = int(rng.choice(best_candidates))
            tabu[index, old] = step + int(rng.integers(5, 60))
            positions[index] = new
            counts[cells[new], block_tiles[index]] += 1
            totals[cells[new]] += 1

    raise ValueError(f'FULL_OBJ_OVERLAP_SEARCH_EXHAUSTED: blocks={len(ordered)}; not an impossibility proof')


def place_large_obj(blocks, *, greedy_attempts=16, time_limit=45):
    """Place exact 32x64 OBJ blocks in either physical 8-KiB name table."""
    ordered = sorted(set(blocks))
    if any(len(block) != 1024 for block in ordered):
        raise ValueError('FULL_OBJ_LARGE_BLOCK_SIZE')
    try:
        return _greedy_rect_obj(ordered, 4, 8, attempts=greedy_attempts)
    except ValueError:
        try:
            return _beam_rect_obj(ordered, 4, 8, beam_width=32,
                                  branch=6, order_count=5)
        except ValueError:
            try:
                return _anneal_rect_obj(ordered, 4, 8,
                                        restarts=12, steps=40000)
            except ValueError:
                return _solve_rect_obj_milp(ordered, 4, 8,
                                            time_limit=time_limit)


def place_rect_obj_cpsat(blocks, tile_width, tile_height, *, time_limit=60):
    """Offline exact-origin solver for a native SNES OBJ rectangle."""
    from ortools.sat.python import cp_model

    ordered = sorted(set(blocks))
    if any(len(block) != tile_width * tile_height * 32 for block in ordered):
        raise ValueError('FULL_OBJ_CPSAT_BLOCK_SIZE')
    model = cp_model.CpModel()
    patterns = sorted({block[offset:offset + 32] for block in ordered
                       for offset in range(0, len(block), 32)})
    pattern_ids = {pattern: index + 1 for index, pattern in enumerate(patterns)}
    blocks_by_ids = [[pattern_ids[block[offset:offset + 32]]
                      for offset in range(0, len(block), 32)] for block in ordered]
    tile_cells = [model.NewIntVar(0, len(patterns), f'cell_{cell}')
                  for cell in range(512)]
    placements = []
    for block_index, row in enumerate(blocks_by_ids):
        page = model.NewIntVar(0, 1, f'page_{block_index}')
        x = model.NewIntVar(0, 16 - tile_width, f'x_{block_index}')
        y = model.NewIntVar(0, 16 - tile_height, f'y_{block_index}')
        placements.append((page, x, y))
        for tile_y in range(tile_height):
            for tile_x in range(tile_width):
                cell = model.NewIntVar(0, 511,
                                       f'cell_index_{block_index}_{tile_y}_{tile_x}')
                model.Add(cell == page * 256 + (y + tile_y) * 16 + x + tile_x)
                model.AddElement(cell, tile_cells,
                                 row[tile_y * tile_width + tile_x])
    # The two physical name tables are symmetric for this offline placement.
    # Fixing the first object to table zero removes one redundant branch.
    if placements:
        model.Add(placements[0][0] == 0)

    # Give the portfolio an exact, conflict-free partial hint; unlike fixing
    # those choices, hints remain retractable during backtracking.
    try:
        _complete, partial = _greedy_rect_obj(
            ordered, tile_width, tile_height, attempts=24, return_partial=True)
        partial_origins, _partial_grid = partial
        for block_index, block in enumerate(ordered):
            if block not in partial_origins:
                continue
            origin = partial_origins[block]
            page, x, y = placements[block_index]
            model.AddHint(page, origin // 256)
            model.AddHint(x, origin % 16)
            model.AddHint(y, (origin % 256) // 16)
    except ValueError:
        pass

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    solver.parameters.symmetry_level = 2
    solver.parameters.random_seed = 221
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError(f'FULL_OBJ_CPSAT_NO_LAYOUT: {solver.StatusName(status)}')

    origins = {}
    grid = {}
    for block_index, block in enumerate(ordered):
        page, x, y = (solver.Value(variable)
                      for variable in placements[block_index])
        origin = page * 256 + y * 16 + x
        origins[block] = origin
        for tile_y in range(tile_height):
            for tile_x in range(tile_width):
                cell = page * 256 + (y + tile_y) * 16 + x + tile_x
                tile_index = tile_y * tile_width + tile_x
                tile = block[tile_index * 32:(tile_index + 1) * 32]
                prior = grid.get(cell)
                if prior is not None and prior != tile:
                    raise AssertionError('FULL_OBJ_CPSAT_TILE_CONFLICT')
                grid[cell] = tile
    if any(not 0 <= cell < 512 for cell in grid):
        raise AssertionError('FULL_OBJ_CPSAT_TILE_RANGE')
    return origins, grid


def place_large_obj_cpsat(blocks, *, time_limit=60):
    """Offline 32x64 layout generator retained for atlas experiments."""
    return place_rect_obj_cpsat(blocks, 4, 8, time_limit=time_limit)


def _anneal_rect_obj(ordered, tile_width, tile_height, *, restarts=8,
                     steps=30000):
    """Find an exact legal-origin overlap with vectorized min-conflicts."""
    import numpy as np

    ordered = sorted(set(ordered))
    tile_count = tile_width * tile_height
    if any(len(block) != tile_count * 32 for block in ordered):
        raise ValueError('FULL_OBJ_ANNEAL_BLOCK_SIZE')
    vocabulary = {tile: i for i, tile in enumerate(sorted(
        {block[offset:offset + 32] for block in ordered
         for offset in range(0, len(block), 32)}))}
    block_tiles = np.asarray([
        [vocabulary[block[offset:offset + 32]]
         for offset in range(0, len(block), 32)]
        for block in ordered], dtype=np.int16)
    origin_list, footprint_list = _physical_origins(tile_width, tile_height)
    origins = np.asarray(origin_list, dtype=np.int16)
    cells = np.asarray(footprint_list, dtype=np.int16)
    block_count = len(ordered)

    best_conflict_count = 1 << 30
    for seed in range(restarts):
        rng = np.random.default_rng(seed + 0x5A17)
        positions = rng.integers(0, len(origins), block_count)
        counts = np.zeros((512, len(vocabulary)), dtype=np.int16)
        totals = np.zeros(512, dtype=np.int16)
        for index, position in enumerate(positions):
            counts[cells[position], block_tiles[index]] += 1
            totals[cells[position]] += 1
        tabu = np.zeros((block_count, len(origins)), dtype=np.int32)
        conflict_total = 0

        for step in range(steps):
            conflicts = (totals[cells[positions]] -
                         counts[cells[positions], block_tiles]).sum(axis=1)
            conflict_total = int(conflicts.sum())
            if conflict_total < best_conflict_count:
                best_conflict_count = conflict_total
            if conflict_total == 0:
                result = {block: int(origins[position])
                          for block, position in zip(ordered, positions)}
                grid = {}
                for block_index, (block, position) in enumerate(zip(ordered, positions)):
                    for tile_index, cell in enumerate(cells[position]):
                        tile = block[tile_index * 32:(tile_index + 1) * 32]
                        old = grid.get(int(cell))
                        if old is not None and old != tile:
                            raise AssertionError('FULL_OBJ_ANNEAL_TILE_CONFLICT')
                        grid[int(cell)] = tile
                if len(result) != block_count or any(not 0 <= cell < 512 for cell in grid):
                    raise AssertionError('FULL_OBJ_ANNEAL_PLACEMENT_RANGE')
                return result, grid

            active = np.flatnonzero(conflicts)
            index = (int(rng.choice(active)) if step % 11
                     else int(rng.integers(block_count)))
            old_position = positions[index]
            counts[cells[old_position], block_tiles[index]] -= 1
            totals[cells[old_position]] -= 1
            candidate_cells = cells
            score = (totals[candidate_cells]
                     - counts[candidate_cells, block_tiles[index]]).sum(axis=1)
            score = score.astype(np.float64)
            tabu_mask = tabu[index] > step
            score[tabu_mask] = np.inf
            minimum = score.min()
            if not np.isfinite(minimum):
                score = (totals[candidate_cells]
                         - counts[candidate_cells, block_tiles[index]]).sum(axis=1)
                score = score.astype(np.float64)
                minimum = score.min()
            temperature = 3.0 * (1.0 - step / max(1, steps)) + 0.15
            weights = np.exp(-np.minimum((score - minimum) / temperature, 80.0))
            weights[~np.isfinite(weights)] = 0.0
            total_weight = weights.sum()
            if total_weight <= 0:
                new_position = int(np.argmin(score))
            else:
                new_position = int(rng.choice(len(origins), p=weights / total_weight))
            tabu[index, old_position] = step + int(rng.integers(7, 80))
            positions[index] = new_position
            counts[cells[new_position], block_tiles[index]] += 1
            totals[cells[new_position]] += 1
            conflict_total += 2 * (int(score[new_position]) - int(conflicts[index]))
            if conflict_total < best_conflict_count:
                best_conflict_count = conflict_total

    raise ValueError(
        f'FULL_OBJ_ANNEAL_EXHAUSTED: blocks={block_count}; '
        f'best_conflicting_pairs={best_conflict_count // 2}; '
        'not an impossibility proof')


def _beam_rect_obj(blocks, tile_width, tile_height, *, beam_width=18,
                   branch=6, order_count=5):
    """Bounded exact-placement beam search over legal whole-OBJ origins."""
    import random

    ordered = sorted(set(blocks))
    tile_count = tile_width * tile_height
    if any(len(block) != tile_count * 32 for block in ordered):
        raise ValueError('FULL_OBJ_BEAM_BLOCK_SIZE')
    tile_ids = {tile: index for index, tile in enumerate(sorted(
        {block[n:n + 32] for block in ordered
         for n in range(0, len(block), 32)}))}
    blocks_by_tiles = [
        [tile_ids[block[n:n + 32]] for n in range(0, len(block), 32)]
        for block in ordered
    ]
    frequency = [0] * len(tile_ids)
    for row in blocks_by_tiles:
        for tile in set(row):
            frequency[tile] += 1
    reuse = [sum(frequency[tile] - 1 for tile in set(row))
             for row in blocks_by_tiles]
    origins, footprints = _physical_origins(tile_width, tile_height)
    neighbors = []
    for cell in range(512):
        page, local = divmod(cell, 256)
        y, x = divmod(local, 16)
        neighbors.append([
            page * 256 + y * 16 + x - 1 if x else -1,
            page * 256 + y * 16 + x + 1 if x < 15 else -1,
            page * 256 + (y - 1) * 16 + x if y else -1,
            page * 256 + (y + 1) * 16 + x if y < 15 else -1,
        ])

    rng = random.Random(0xB04)
    orders = []
    for mode in range(order_count):
        order = list(range(len(ordered)))
        rng.shuffle(order)
        if mode == 0:
            order.sort(key=lambda i: reuse[i])
        elif mode == 1:
            order.sort(key=lambda i: -reuse[i])
        elif mode == 2:
            order.sort(key=lambda i: (sum(t == 0 for t in blocks_by_tiles[i]), reuse[i]))
        elif mode == 3:
            order.sort(key=lambda i: (-len(set(blocks_by_tiles[i])), reuse[i]))
        orders.append(order)

    for order in orders:
        # State is (grid, occupied-cell count, seen-tile bitset, perimeter,
        # block-indexed origins).  Zero means unoccupied; tile ids are +1.
        beam = [(tuple([0] * 512, ), 0, 0, 0, tuple([-1] * len(ordered)))]
        for block_index in order:
            block_tiles = blocks_by_tiles[block_index]
            expanded = []
            state_seen = set()
            for grid, occupied, kinds, perimeter, positions in beam:
                choices = []
                for origin_index, cells in enumerate(footprints):
                    added = []
                    for cell, tile in zip(cells, block_tiles):
                        current = grid[cell]
                        if current and current != tile + 1:
                            break
                        if not current:
                            added.append((cell, tile + 1))
                    else:
                        new_cells = set()
                        next_perimeter = perimeter
                        for cell, _tile_value in added:
                            adjacent = sum(
                                neighbor >= 0 and
                                (grid[neighbor] != 0 or neighbor in new_cells)
                                for neighbor in neighbors[cell]
                            )
                            next_perimeter += 4 - 2 * adjacent
                            new_cells.add(cell)
                        next_kinds = kinds
                        for tile in block_tiles:
                            next_kinds |= 1 << tile
                        next_occupied = occupied + len(added)
                        lower_bound = next_occupied + len(tile_ids) - next_kinds.bit_count()
                        if lower_bound <= 512:
                            score = lower_bound + next_perimeter * 0.01
                            choices.append((score, len(added), origin_index,
                                            added, next_kinds, next_perimeter))
                choices.sort(key=lambda row: (row[0], row[1], rng.random()))
                for score, added_count, origin_index, added, next_kinds, next_perimeter in choices[:branch]:
                    updated = list(grid)
                    for cell, tile_value in added:
                        updated[cell] = tile_value
                    updated = tuple(updated)
                    if updated in state_seen:
                        continue
                    state_seen.add(updated)
                    placements = list(positions)
                    placements[block_index] = origins[origin_index]
                    expanded.append((score, updated, occupied + added_count,
                                     next_kinds, next_perimeter, tuple(placements)))
            if not expanded:
                break
            expanded.sort(key=lambda row: (row[0], rng.random()))
            beam = [(grid, occupied, kinds, perimeter, positions)
                    for _, grid, occupied, kinds, perimeter, positions
                    in expanded[:beam_width]]
            complete = next((state for state in beam
                             if all(position >= 0 for position in state[4])), None)
            if complete is not None:
                positions = complete[4]
                result = {block: positions[i] for i, block in enumerate(ordered)}
                grid_result = {}
                origin_to_cells = dict(zip(origins, footprints))
                for block_index, block in enumerate(ordered):
                    origin = positions[block_index]
                    for tile_index, cell in enumerate(origin_to_cells[origin]):
                        tile_bytes = block[tile_index * 32:(tile_index + 1) * 32]
                        if cell in grid_result and grid_result[cell] != tile_bytes:
                            raise AssertionError('FULL_OBJ_BEAM_TILE_CONFLICT')
                        grid_result[cell] = tile_bytes
                if any(not 0 <= cell < 512 for cell in grid_result):
                    raise AssertionError('FULL_OBJ_BEAM_TILE_RANGE')
                return result, grid_result
    raise ValueError('FULL_OBJ_BEAM_EXHAUSTED: not an impossibility proof')


def _greedy_full_obj(ordered, *, attempts=96, return_partial=False):
    return _greedy_rect_obj(ordered, 2, 4, attempts=attempts,
                             return_partial=return_partial)


def _greedy_rect_obj(ordered, tile_width, tile_height, *, attempts=96,
                     return_partial=False):
    import random

    vocabulary = {}
    block_tiles = {}
    for block in ordered:
        block_tiles[block] = [block[n:n + 32]
                              for n in range(0, len(block), 32)]
        for tile in block_tiles[block]:
            vocabulary[tile] = vocabulary.get(tile, 0) + 1
    reuse = {block: sum(vocabulary[tile] - 1 for tile in block_tiles[block])
             for block in ordered}
    legal_origins, legal_cells = _physical_origins(tile_width, tile_height)
    legal_cells = dict(zip(legal_origins, legal_cells))
    rng = random.Random(0)
    best_count = 0
    best_origins = {}
    best_grid = {}

    for attempt in range(attempts):
        order = list(ordered)
        rng.shuffle(order)
        order.sort(key=lambda block: -reuse[block])
        grid = {}
        origins = {}
        for block in order:
            tiles = block_tiles[block]
            best_cost = tile_width * tile_height + 1
            best = []
            for origin in legal_origins:
                x, y = origin % 16, origin // 16
                cells = legal_cells[origin]
                for cell, tile in zip(cells, tiles):
                    old = grid.get(cell)
                    if old is not None and old != tile:
                        break
                else:
                    cost = sum(cell not in grid for cell in cells)
                    if cost < best_cost:
                        best_cost = cost
                        best = [(origin, cells)]
                    elif cost == best_cost:
                        best.append((origin, cells))
            if not best:
                break
            origin, cells = rng.choice(best)
            origins[block] = origin
            for cell, tile in zip(cells, tiles):
                grid[cell] = tile
            if len(origins) > best_count:
                best_count = len(origins)
                best_origins = origins.copy()
                best_grid = grid.copy()
        else:
            if len(origins) != len(ordered) or any(not 0 <= cell < 512 for cell in grid):
                raise AssertionError('FULL_OBJ_GREEDY_PLACEMENT_RANGE')
            return origins, grid

    if return_partial:
        return None, (best_origins, best_grid)
    raise ValueError(
        f'FULL_OBJ_GREEDY_SEARCH_EXHAUSTED: best={best_count}/{len(ordered)}; '
        'not an impossibility proof')


def _solve_full_obj_milp(ordered, *, time_limit=45):
    return _solve_rect_obj_milp(ordered, 2, 4, time_limit=time_limit)


def _solve_rect_obj_milp(ordered, tile_width, tile_height, *, time_limit=45):
    """Exact legal-origin placement via a sparse tile-ownership MILP."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_array

    vocabulary = {tile: i for i, tile in enumerate(sorted(
        {block[n:n + 32] for block in ordered
         for n in range(0, len(block), 32)}))}
    block_tiles = np.asarray([
        [vocabulary[block[n:n + 32]] for n in range(0, len(block), 32)]
        for block in ordered], dtype=np.int32)
    origin_list, footprint_list = _physical_origins(tile_width, tile_height)
    origins = np.asarray(origin_list, dtype=np.int32)
    cells = np.asarray(footprint_list, dtype=np.int32)

    block_count, origin_count = len(ordered), len(origins)
    placement_variables = block_count * origin_count
    tile_variables = {}
    tile_vars_by_cell = [[] for _ in range(512)]
    row_ids, column_ids, values = [], [], []
    row_lower = [1.0] * block_count
    row_upper = [1.0] * block_count

    # Every block chooses exactly one legal origin.
    for block_index in range(block_count):
        start = block_index * origin_count
        row_ids.extend([block_index] * origin_count)
        column_ids.extend(range(start, start + origin_count))
        values.extend([1.0] * origin_count)

    # A selected origin requires its eight exact tile identities at their
    # physical cells. One continuous ownership variable per (cell, bytes)
    # pair is sufficient because placement variables are integral.
    for block_index in range(block_count):
        for origin_index, origin_cells in enumerate(cells):
            placement = block_index * origin_count + origin_index
            for tile_index, cell in enumerate(origin_cells):
                cell = int(cell)
                tile = int(block_tiles[block_index, tile_index])
                key = (cell, tile)
                tile_variable = tile_variables.get(key)
                if tile_variable is None:
                    tile_variable = placement_variables + len(tile_variables)
                    tile_variables[key] = tile_variable
                    tile_vars_by_cell[cell].append(tile_variable)
                row = len(row_lower)
                row_lower.append(-np.inf)
                row_upper.append(0.0)
                row_ids.extend((row, row))
                column_ids.extend((placement, tile_variable))
                values.extend((1.0, -1.0))

    for cell, cell_variables in enumerate(tile_vars_by_cell):
        row = len(row_lower)
        row_lower.append(-np.inf)
        row_upper.append(1.0)
        row_ids.extend([row] * len(cell_variables))
        column_ids.extend(cell_variables)
        values.extend([1.0] * len(cell_variables))

    variable_count = placement_variables + len(tile_variables)
    matrix = coo_array(
        (np.asarray(values, dtype=np.float64),
         (np.asarray(row_ids, dtype=np.int32),
          np.asarray(column_ids, dtype=np.int32))),
        shape=(len(row_lower), variable_count),
    ).tocsc()
    integrality = np.zeros(variable_count, dtype=np.uint8)
    integrality[:placement_variables] = 1
    # This is a feasibility problem: minimizing occupied tile cells made
    # HiGHS spend its bounded run optimizing overlap quality without ever
    # returning the legal placement we actually need.
    objective = np.zeros(variable_count, dtype=np.float64)
    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(np.zeros(variable_count), np.ones(variable_count)),
        constraints=LinearConstraint(matrix, row_lower, row_upper),
        options={"time_limit": time_limit},
    )
    if result.x is None:
        raise ValueError(f"FULL_OBJ_MILP_NO_SOLUTION: status={result.status}; {result.message}")

    packed_origins = {}
    grid = {}
    for block_index, block in enumerate(ordered):
        start = block_index * origin_count
        selected = np.flatnonzero(result.x[start:start + origin_count] > 0.5)
        if len(selected) != 1:
            raise ValueError("FULL_OBJ_MILP_NONINTEGRAL_BLOCK_PLACEMENT")
        origin = int(origins[int(selected[0])])
        packed_origins[block] = origin
        for tile_index in range(tile_width * tile_height):
            cell = int(cells[int(selected[0]), tile_index])
            tile = block[tile_index * 32:(tile_index + 1) * 32]
            if cell in grid and grid[cell] != tile:
                raise ValueError("FULL_OBJ_MILP_TILE_CONFLICT")
            grid[cell] = tile
    if any(not 0 <= cell < 512 for cell in grid):
        raise ValueError("FULL_OBJ_MILP_TILE_RANGE")
    return packed_origins, grid


def _place_all_origins(ordered, attempts, steps, initial_origins=None):
    """Original exhaustive-origin local search retained for compact sets."""
    import numpy as np

    vocabulary = {tile: i for i, tile in enumerate(sorted(
        {block[n:n + 32] for block in ordered for n in range(0, 256, 32)}))}
    block_tiles = np.asarray([
        [vocabulary[block[n:n + 32]] for n in range(0, 256, 32)]
        for block in ordered], dtype=np.int16)
    origin_list, footprint_list = _physical_origins(2, 4)
    origins = np.asarray(origin_list, dtype=np.int16)
    cells = np.asarray(footprint_list, dtype=np.int16)
    origin_indices = {int(origin): index for index, origin in enumerate(origins)}

    for seed in range(attempts):
        rng = np.random.default_rng(seed)
        positions = rng.integers(0, len(origins), len(ordered))
        if initial_origins:
            for index, block in enumerate(ordered):
                if block in initial_origins:
                    positions[index] = origin_indices[initial_origins[block]]
        counts = np.zeros((512, len(vocabulary)), dtype=np.int16)
        totals = np.zeros(512, dtype=np.int16)
        for index, position in enumerate(positions):
            counts[cells[position], block_tiles[index]] += 1
            totals[cells[position]] += 1
        tabu = np.zeros((len(ordered), len(origins)), dtype=np.int32)

        for step in range(steps):
            conflicts = (totals[cells[positions]] -
                         counts[cells[positions], block_tiles]).sum(axis=1)
            if not int(conflicts.sum()):
                result = {block: int(origins[position])
                          for block, position in zip(ordered, positions)}
                grid = {}
                for block_index, (block, origin) in enumerate(result.items()):
                    for tile_index in range(8):
                        cell = int(cells[origin_indices[origin], tile_index])
                        tile = block[tile_index * 32:(tile_index + 1) * 32]
                        if cell in grid and grid[cell] != tile:
                            raise AssertionError('FULL_OBJ_OVERLAP_MISMATCH')
                        grid[cell] = tile
                if len(result) != len(ordered) or any(not 0 <= cell < 512 for cell in grid):
                    raise AssertionError('FULL_OBJ_PLACEMENT_RANGE')
                return result, grid

            active = np.flatnonzero(conflicts)
            index = (int(rng.choice(active)) if step % 13
                     else int(rng.integers(len(ordered))))
            old = positions[index]
            counts[cells[old], block_tiles[index]] -= 1
            totals[cells[old]] -= 1
            score = (totals[cells] - counts[cells, block_tiles[index]]).sum(axis=1).astype(float)
            score[tabu[index] > step] += 1000
            if step % 97 == 0:
                score += rng.random(len(origins)) * 2.0
            new = int(np.argmin(score))
            tabu[index, old] = step + int(rng.integers(5, 60))
            positions[index] = new
            counts[cells[new], block_tiles[index]] += 1
            totals[cells[new]] += 1

    raise ValueError(f'FULL_OBJ_OVERLAP_SEARCH_EXHAUSTED: blocks={len(ordered)}; not an impossibility proof')
