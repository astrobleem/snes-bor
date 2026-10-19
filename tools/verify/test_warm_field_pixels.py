from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "verify"))

from warm_field_pixels import (
    MAX_PAYLOAD_CHARS, CapturedFrame, PixelCaptureError, decode_rgb24,
    encode_rgb24, full_frame_records, lua_observer, parse_log, reference_record,
)


def test_exact_rgb24_roundtrip_including_zero_high_colors_and_long_runs():
    pixels = (0, 0, 0x010203, 0x010203, 0xFE12AB, 0xFFFFFF, 0xFFFFFF, 0)
    chunks = encode_rgb24(pixels)
    assert chunks == ("000000020000000000000201020300000001FE12AB00000002FFFFFF00000001000000",)
    assert decode_rgb24(chunks, len(pixels)) == pixels


def test_runs_split_only_at_token_boundaries_and_reconstruct_every_pixel():
    pixels = tuple((index * 7919) & 0xFFFFFF for index in range(1007))
    chunks = encode_rgb24(pixels, max_payload_chars=42)
    assert len(chunks) == 336
    assert all(len(chunk) == 42 for chunk in chunks[:-1])
    assert len(chunks[-1]) == 28
    assert decode_rgb24(chunks, len(pixels)) == pixels
    assert all(len(chunk) <= MAX_PAYLOAD_CHARS and len(chunk) % 14 == 0 for chunk in chunks)


def test_full_frame_log_roundtrip_and_reference_chain_always_points_to_prior_full():
    first_pixels = (0, 0xA0B0C0, 0xFFFFFF, 0xFFFFFF, 0x010203, 0)
    next_pixels = (0, 0, 0, 0, 0, 0)
    lines = list(full_frame_records(1, 0x10203040, 3, 2, first_pixels, max_payload_chars=28))
    lines += [reference_record(2, 0x10203100, 1), reference_record(3, 0x10203120, 1)]
    lines += list(full_frame_records(4, 0x10203200, 3, 2, next_pixels))
    frames = parse_log(lines, expected_ordinals=range(1, 5))
    assert frames[1] == CapturedFrame(1, 0x10203040, 3, 2, first_pixels, 1, False)
    assert frames[2] == CapturedFrame(2, 0x10203100, 3, 2, first_pixels, 1, True)
    assert frames[3] == CapturedFrame(3, 0x10203120, 3, 2, first_pixels, 1, True)
    assert frames[4] == CapturedFrame(4, 0x10203200, 3, 2, next_pixels, 4, False)


def test_parser_accepts_reordered_chunks_but_requires_all_indices():
    records = full_frame_records(1, 3, 5, 2, tuple(range(10)), max_payload_chars=28)
    assert len(records) == 5
    parsed = parse_log(list(reversed(records)), expected_ordinals=range(1, 2))
    assert parsed[1].pixels == tuple(range(10))
    with pytest.raises(PixelCaptureError, match="MISSING_CHUNK"):
        parse_log(records[:-1], expected_ordinals=range(1, 2))


@pytest.mark.parametrize("bad_chunk,expected", [
    ("", "RLE_CHUNK_EXTENT"),
    ("0000000000000", "RLE_CHUNK_EXTENT"),  # truncated token
    ("GG000001000000", "RLE_TOKEN"),
    ("00000000000000", "RLE_ZERO_RUN"),
    ("00000002FFFFFF", "RLE_OVERFLOW"),
])
def test_rle_decoder_rejects_malformed_or_out_of_extent_runs(bad_chunk, expected):
    with pytest.raises(PixelCaptureError, match=expected):
        decode_rgb24([bad_chunk], 1)


def test_rle_decoder_rejects_underfill_and_invalid_chunk_limit():
    with pytest.raises(PixelCaptureError, match="RLE_UNDERFILL"):
        decode_rgb24(["00000001000000"], 2)
    for size in (13, 15, MAX_PAYLOAD_CHARS + 14):
        with pytest.raises(PixelCaptureError, match="CHUNK_LIMIT_ALIGNMENT"):
            encode_rgb24((1, 2), size)


def test_parser_rejects_missing_duplicate_bad_and_forward_reference_records():
    full = list(full_frame_records(1, 8, 1, 1, (0x123456,)))
    ref = reference_record(2, 9, 1)
    with pytest.raises(PixelCaptureError, match="MISSING_OR_EXTRA_ORDINAL"):
        parse_log(full + [reference_record(3, 10, 1)], expected_ordinals=range(1, 3))
    with pytest.raises(PixelCaptureError, match="DUPLICATE_CHUNK"):
        parse_log(full + full, expected_ordinals=range(1, 2))
    with pytest.raises(PixelCaptureError, match="REFERENCE_ORDINAL"):
        parse_log(["WARMPIXREF|00000001|00000009|00000000"], expected_ordinals=range(1, 2))
    with pytest.raises(PixelCaptureError, match="REFERENCE_NOT_PRIOR_FULL"):
        parse_log(full + [reference_record(2, 9, 1), reference_record(3, 10, 2)], expected_ordinals=range(1, 4))
    with pytest.raises(PixelCaptureError, match="MISSING_OR_EXTRA_ORDINAL"):
        parse_log(full + [ref], expected_ordinals=(1, 2, 3))


def test_parser_rejects_duplicate_chunk_and_mismatched_header():
    rows = full_frame_records(1, 8, 2, 1, (0x11, 0x22), max_payload_chars=14)
    assert len(rows) == 2
    with pytest.raises(PixelCaptureError, match="DUPLICATE_CHUNK"):
        parse_log([rows[0], rows[0], rows[1]], expected_ordinals=range(1, 2))
    malformed = rows[1].replace("|00000008|0002|", "|00000009|0002|")
    with pytest.raises(PixelCaptureError, match="CHUNK_HEADER_MISMATCH"):
        parse_log([rows[0], malformed], expected_ordinals=range(1, 2))


def test_parser_rejects_dimension_count_and_payload_corruption():
    row = full_frame_records(1, 7, 2, 1, (1, 2))[0]
    with pytest.raises(PixelCaptureError, match="FRAME_PIXEL_COUNT"):
        parse_log([row.replace("|00000002|", "|00000003|")], expected_ordinals=range(1, 2))
    with pytest.raises(PixelCaptureError, match="CHUNK_PAYLOAD_EXTENT"):
        parse_log([row[:-1]], expected_ordinals=range(1, 2))


def test_lua_observer_is_read_only_dynamic_size_and_uses_exact_pixel_compare():
    code = lua_observer()
    assert "WarmPixOwned7FFB88B6D0_EndFrame" in code
    assert "emu.addEventCallback(WarmPixOwned7FFB88B6D0_EndFrame, emu.eventType.endFrame)" in code
    assert "emu.read16(0x7ffb88, emu.memType.snesMemory) ~= 0xb6d0" in code
    assert "emu.getDrawSurfaceSize(emu.drawSurface.consoleScreen)" in code
    assert "rawSize.width - crop.left - crop.right" in code
    assert "rawSize.height - crop.top - crop.bottom" in code
    assert "#raw ~= rawSize.width * rawSize.height" in code
    assert "raw[y * rawSize.width + x + 1]" in code
    assert "WARMPIX_CROP_BOUNDS" in code
    assert "WARMPIX_UNSUPPORTED_FILTER_GEOMETRY" in code
    assert "if a[i] ~= b[i] then return false end" in code
    assert 'string.format("%08X%06X", j - i, color)' in code
    assert '"WARMPIXREF|%08X|%08X|%08X"' in code
    assert '"WARMPIXFULL|%08X|%08X|%04X|%04X|%08X|%04X|%04X|%s"' in code
    assert "emu.setScreenBuffer" not in code
    assert "emu.write" not in code



def test_parser_requires_expected_final_ordinal_to_detect_trailing_loss():
    row = full_frame_records(1, 3, 1, 1, (0x123456,))
    with pytest.raises(PixelCaptureError, match="EXPECTED_ORDINALS_REQUIRED"):
        parse_log(row)
    with pytest.raises(PixelCaptureError, match="MISSING_OR_EXTRA_ORDINAL"):
        parse_log(row, expected_ordinals=range(1, 3))
