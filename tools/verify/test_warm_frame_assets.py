"""Source and format regressions for the warm SELECT/IDLE/WALK asset pack."""
from __future__ import annotations

import io
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/bor_compile'))

from compiler import Source
from source_warm_frame_assets import (decode_image, derive, encode_image,
                                      pack_metadata, screen_geometry,
                                      unpack_metadata)

PAK = ROOT / 'Masters of the Universe [v.3.0 Build 4086].pak'


@pytest.fixture(scope='module')
def packed():
    return derive(Source(PAK))


def test_all_149_pose_keys_and_source_image_pixels_roundtrip(packed):
    manifest = packed['manifest']
    poses = manifest['poses']
    assert len(poses) == 149
    assert len({(p['model_id'], p['handle'], p['frame']) for p in poses}) == 149
    assert {role: sum(p['role'] == role for p in poses)
            for role in ('select', 'idle', 'walk')} == {'select': 131, 'idle': 8, 'walk': 10}
    assert len(packed['image_blobs']) == 71
    source = Source(PAK)
    # Every byte/pixel from each unique full indexed source image survives.
    for index, image in enumerate(manifest['images']):
        decoded = decode_image(packed['image_blobs'][index])
        assert image['index_sha256'] == hashlib.sha256(decoded.tobytes()).hexdigest()
        with Image.open(io.BytesIO(source.read(image['source_path']))) as original:
            original.load()
            assert original.mode == 'P'
            assert np.array_equal(decoded, np.asarray(original, dtype=np.uint8))
            assert list(original.size) == [image['width'], image['height']]


def test_source_offsets_bounds_and_direction_geometry(packed):
    source = Source(PAK)
    for pose in packed['manifest']['poses']:
        original = decode_image(packed['image_blobs'][pose['image_index']])
        yy, xx = np.nonzero(original)
        expected = ([int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]
                    if len(xx) else [0, 0, 0, 0])
        assert pose['bounds'] == expected
        assert len(pose['offset']) == 2
        for direction in (0, 1):
            actual = screen_geometry(pose, 100, 75, direction)
            w = pose['width']; ox, oy = pose['offset']; x0, y0, x1, y1 = pose['bounds']
            left = 100 - (ox if direction else w - ox)
            if direction == 0:
                x0, x1 = w - x1, w - x0
            assert actual == dict(left=left, top=75 - oy,
                                  visible=[left + x0, 75 - oy + y0, left + x1, 75 - oy + y1])
    with pytest.raises(ValueError, match='WARM_DIRECTION_DOMAIN'):
        screen_geometry(packed['manifest']['poses'][0], 0, 0, 2)


def test_metadata_roundtrip_and_rejects_duplicate_or_invalid_pose(packed):
    manifest = packed['manifest']
    parsed = unpack_metadata(packed['metadata'], b''.join(packed['image_blobs']))
    assert len(parsed['poses']) == 149
    assert len(parsed['images']) == 71
    assert [(p['model_id'], p['handle'], p['frame']) for p in parsed['poses']] == [
        (p['model_id'], p['handle'], p['frame']) for p in manifest['poses']]
    images = manifest['images']
    with pytest.raises(ValueError, match='WARM_META_DUPLICATE_POSE'):
        pack_metadata([manifest['poses'][0], manifest['poses'][0]], images)
    invalid = dict(manifest['poses'][0], image_index=len(images))
    with pytest.raises(ValueError, match='WARM_META_IMAGE_INDEX'):
        pack_metadata([invalid], images)
    invalid = dict(manifest['poses'][0], frame=0x10000)
    with pytest.raises(ValueError, match='WARM_META_POSE_DOMAIN'):
        pack_metadata([invalid], images)
    with pytest.raises(ValueError, match='WARM_META_IMAGE_EXTENT'):
        unpack_metadata(packed['metadata'], b'')


@pytest.mark.parametrize('mutator,tag', [
    (lambda b: b[:5], 'WARM_IMAGE_TRUNCATED_HEADER'),
    (lambda b: b[:-1], 'WARM_IMAGE_EXTENT'),
    (lambda b: b[:10] + b'\xff\xff' + b[12:], 'WARM_IMAGE_ROW_EXTENT'),
    # First run count is at row data offset 10 + (height+1)*2.
    (lambda b: _set_first_run_count(b, 0), 'WARM_IMAGE_RUN'),
    (lambda b: _set_first_run_count(b, 255), 'WARM_IMAGE_RUN'),
])
def test_image_decoder_rejects_bad_extent_offsets_and_runs(packed, mutator, tag):
    with pytest.raises(ValueError, match=tag):
        decode_image(mutator(packed['image_blobs'][0]))


def _set_first_run_count(blob, value):
    raw = bytearray(blob)
    _, _, height, _ = __import__('struct').unpack_from('<4sHHH', raw)
    raw[10 + (height + 1) * 2] = value
    return bytes(raw)


def test_metadata_truncation_duplicate_and_bad_row_extent_rejected(packed):
    with pytest.raises(ValueError, match='WARM_META_HEADER'):
        unpack_metadata(packed['metadata'][:-1])
    broken = bytearray(packed['metadata'])
    # First image directory record has a reserved u16 at bytes 26..27.
    broken[26:28] = b'\x01\x00'
    with pytest.raises(ValueError, match='WARM_META_IMAGE_RECORD'):
        unpack_metadata(broken)


def test_exact_masked_actor_palette_set_comparison_is_recorded(packed):
    comparison = packed['manifest']['masked_color_comparison']
    if comparison.get('accepted_palette_available') is not False:
        assert isinstance(comparison['missing_from_accepted'], list)
        assert isinstance(comparison['extra_in_accepted'], list)
        assert comparison['exact_subset'] == (not comparison['missing_from_accepted'])
        lut = comparison['actor_palette_lookup']
        if lut.get('available') is not False:
            assert len(lut['missing_color_indices_with_zero_lut_word']) == len(lut['missing_color_source_indices'])
            assert lut['all_missing_color_indices_unmapped']
