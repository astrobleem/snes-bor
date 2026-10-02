"""Lossless compile-time placement for 16x32 SNES OBJ tile footprints."""


def place_full_obj(blocks, attempts=8, steps=100000):
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
    vocabulary = {tile: i for i, tile in enumerate(sorted(
        {block[n:n + 32] for block in ordered for n in range(0, 256, 32)}))}
    block_tiles = np.asarray([
        [vocabulary[block[n:n + 32]] for n in range(0, 256, 32)]
        for block in ordered], dtype=np.int16)
    origins = np.asarray([y * 16 + x for y in range(29) for x in range(15)],
                         dtype=np.int16)
    cells = np.asarray([[(origin // 16 + row) * 16 + origin % 16 + col
                         for row in range(4) for col in range(2)]
                        for origin in origins], dtype=np.int16)

    for seed in range(attempts):
        rng = np.random.default_rng(seed)
        positions = rng.integers(0, len(origins), len(ordered))
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
                for block, origin in result.items():
                    x, y = origin % 16, origin // 16
                    for tile_index in range(8):
                        cell = (y + tile_index // 2) * 16 + x + tile_index % 2
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
