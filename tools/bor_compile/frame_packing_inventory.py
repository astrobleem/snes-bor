"""Source-preserving packing/resource measurements, not hardware certification."""
import argparse
import hashlib
import json
from pathlib import Path

from compiler import Source
from frame_packing import pack_image, reconstruct, transition_delta, viewport_resources


def inventory(pak, report):
    source = Source(pak)
    report_bytes = Path(report).read_bytes()
    data = json.loads(report_bytes)
    frames, animations, failures, cache = [], [], [], {}
    project_tiles, project_blocks = set(), set()
    model_sets = {}
    for name, model in sorted(data['models'].items()):
        model_tiles, model_blocks = set(), set()
        for animation in model['ir']['animations']:
            previous = None
            animation_tiles, animation_blocks, records = set(), set(), []
            for index, frame in enumerate(animation['frames']):
                path = frame['source_path']
                try:
                    offset = tuple(frame['state'].get('offset', (0, 0)))
                    key = (path, offset)
                    if key not in cache:
                        raw = source.read(path)
                        packed = pack_image(raw, offset)
                        if not reconstruct(raw, packed):
                            raise ValueError('VISIBLE_PIXEL_RECONSTRUCTION_MISMATCH')
                        cache[key] = (hashlib.sha256(raw).hexdigest(), packed)
                    digest, packed = cache[key]
                    if digest != frame['asset_sha256']:
                        raise ValueError('SOURCE_ASSET_HASH_MISMATCH')
                    delta = transition_delta(previous, packed)
                    record = dict(model=name, role=animation['role'], frame=index,
                        source_path=path, source_sha256=digest,
                        dimensions=packed['dimensions'], bbox=packed['bbox'],
                        offset=list(offset), pieces=len(packed['pieces']),
                        small=sum(p['size'] == [16, 32] for p in packed['pieces']),
                        large=sum(p['size'] == [32, 64] for p in packed['pieces']),
                        tile_bytes=packed['tile_bytes'],
                        nonempty_tiles=packed['nonempty_tiles'], padding_tiles=packed['padding_tiles'],
                        unique_tile_bytes=len(set(packed['tile_ids']))*32,
                        unique_block_bytes=len(packed['small_blocks'])*256,
                        source_delay=frame['state'].get('delay'), transition=delta,
                        viewport_at_source_origin=viewport_resources(packed),
                        pixel_reconstruction=True)
                    frames.append(record)
                    records.append(record)
                    animation_tiles.update(packed['tile_ids'])
                    animation_blocks.update(packed['small_blocks'])
                    previous = packed
                except (OSError, ValueError, KeyError) as error:
                    failures.append(dict(model=name, role=animation['role'], frame=index,
                                         source_path=path, error=str(error)))
            animations.append(dict(model=name, role=animation['role'], frames=len(records),
                full_frame_bytes=sum(r['tile_bytes'] for r in records),
                unique_block_bytes=len(animation_blocks)*256,
                unique_tile_bytes=len(animation_tiles)*32))
            model_tiles.update(animation_tiles)
            model_blocks.update(animation_blocks)
        model_sets[name] = dict(unique_tile_bytes=len(model_tiles)*32,
                               unique_block_bytes=len(model_blocks)*256)
        project_tiles.update(model_tiles)
        project_blocks.update(model_blocks)
    return dict(project_id=data['project_id'],
        input_report_sha256=hashlib.sha256(report_bytes).hexdigest(),
        frames=frames, animations=animations, models=model_sets, failures=failures,
        maximum_pieces=max(frames, key=lambda f:f['pieces'], default=None),
        maximum_tile_bytes=max(frames, key=lambda f:f['tile_bytes'], default=None),
        maximum_transition=max(frames, key=lambda f:f['transition']['new_bytes'], default=None),
        maximum_animation=max(animations, key=lambda a:a['unique_block_bytes'], default=None),
        project_unique_tile_bytes=len(project_tiles)*32,
        project_unique_block_bytes=len(project_blocks)*256,
        certification='ANALYSIS_ONLY',
        nonclaims=['Packing is a heuristic upper bound, not a minimum.',
                   'Foreign index-zero transparency requires dialect validation.',
                   'Indexed-content dedup is not linked palette/VRAM equivalence.',
                   'Viewport sample is not an all-position scanline proof.',
                   'Animation pool is not a concurrent VRAM allocation.',
                   'Transition bytes have no measured transport deadline proof.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', nargs=3, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {label:inventory(pak, report) for label,pak,report in args.project}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    for label, item in result.items():
        maximum = item['maximum_pieces']
        print(label, 'frames', len(item['frames']), 'failures', len(item['failures']),
              'max pieces', maximum['pieces'], maximum['source_path'])


if __name__ == '__main__':
    main()
