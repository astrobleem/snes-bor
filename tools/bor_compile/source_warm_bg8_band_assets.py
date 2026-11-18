"""Out-only ROM/data preparation prototype for conservative BG8 row bands.

This module does not mutate a ROM. It only returns sparse data-write records.
The input warm_config must carry
the exact source manifest/image pointers, the checked candidate ROM intervals,
and all existing contract-owned ROM intervals.
"""
from __future__ import annotations

import hashlib
import struct
from source_warm_frame_assets import decode_image  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


def _checked_ranges(items, name):
    out = []
    for row in items:
        start_value = row["offset"]
        size_value = row.get("bytes", row.get("length"))
        if type(start_value) is not int or type(size_value) is not int:
            raise ValueError(f"{name} interval values must be strict integers")
        start, size = start_value, size_value
        if start < 0 or size <= 0:
            raise ValueError(f"invalid {name} interval")
        out.append((start, start + size, row))
    return out


def _row_records(mask):
    """Return 4-byte records for source-row starts -7..height-1.

    Each record is {u16 minX,u16 maxX_exclusive}; {0,0} means empty.
    """
    import numpy as np

    h, _w = mask.shape
    data = bytearray()
    for start in range(-7, h):
        rows = mask[max(0, start):min(h, start + 8)]
        xs = np.nonzero(rows)[1]
        if not len(xs):
            data.extend(b"\x00\x00\x00\x00")
        else:
            lo, hi_exclusive = int(xs.min()), int(xs.max()) + 1
            data.extend(struct.pack("<HH", lo, hi_exclusive))
    return bytes(data)


def prepare_row_bands(rom: bytes, warm_config: dict):
    """Build validated row-band tables and a compact pose directory.

    Required warm_config keys:
      source_manifest.images/poses, image_cpu_addresses,
      row_band_candidate_ranges (physical ROM offset/bytes),
      existing_rom_ranges (physical ROM offset/bytes).

    Returns (writes, spec). A write is {offset,data,reason,sha256}. Candidate
    intervals must be zero-filled and disjoint from every existing ROM range.
    The first candidate interval holds the pose directory; image row records
    are next-fit packed into later candidate intervals without crossing one.
    """
    manifest = warm_config["source_manifest"]
    images = manifest["images"]
    poses = manifest["poses"]
    image_cpus = warm_config["image_cpu_addresses"]
    candidate = _checked_ranges(warm_config["row_band_candidate_ranges"], "candidate")
    occupied = _checked_ranges(warm_config["existing_rom_ranges"], "existing")
    if len(rom) != 0x400000:
        raise ValueError("row-band prototype requires the checked 4 MiB V21 ROM extent")
    pak_hash = manifest.get("source_pak_sha256")
    if (len(image_cpus) != len(images) or len(poses) != 149 or len(images) != 71
            or not isinstance(pak_hash, str) or len(pak_hash) != 64
            or pak_hash != warm_config.get("source_pak_sha256")):
        raise ValueError("source manifest dimensions are not the checked V21 profile")
    if not candidate:
        raise ValueError("no checked candidate intervals")
    if any(end > len(rom) for _start, end, _ in occupied):
        raise ValueError("existing contract ROM range exceeds the checked ROM extent")
    candidate_keys = set()
    for start, end, _ in candidate:
        if end - start != 0x8000 or start % 0x8000 or not (111 <= start // 0x8000 <= 127):
            raise ValueError("candidate must be a 32 KiB-aligned physical slice in bank slots 111..127")
        if (start, end) in candidate_keys:
            raise ValueError("duplicate candidate interval")
        candidate_keys.add((start, end))
        if end > len(rom) or any(rom[start:end]):
            raise ValueError("candidate interval is not in-ROM and zero-filled")
        if any(_overlap(start, end, x, y) for x, y, _ in occupied):
            raise ValueError("candidate interval overlaps an existing ROM contract range")
    for i, (start, end, _) in enumerate(candidate):
        if any(_overlap(start, end, other_start, other_end)
               for other_start, other_end, _ in candidate[i + 1:]):
            raise ValueError("candidate intervals overlap")

    image_rows = []
    for i, image in enumerate(images):
        if type(image.get("image_index")) is not int or image["image_index"] != i:
            raise ValueError(f"source image manifest order/index mismatch at {i}")
        cpu = image_cpus[i]
        if type(cpu) is not int:
            raise ValueError(f"image {i} CPU address must be a strict integer")
        if not 0xC00000 <= cpu < 0x1000000:
            raise ValueError(f"image {i} is not a supported HiROM address")
        source_offset = cpu - 0xC00000
        for key in ("image_length", "width", "height"):
            if type(image.get(key)) is not int:
                raise ValueError(f"image {i} {key} must be a strict integer")
        length = image["image_length"]
        width, height = image["width"], image["height"]
        for key in ("encoded_sha256", "index_sha256"):
            if not isinstance(image.get(key), str) or len(image[key]) != 64:
                raise ValueError(f"source image {i} {key} is missing or malformed")
        if length <= 0 or source_offset < 0 or source_offset + length > len(rom):
            raise ValueError(f"source image {i} extent is outside ROM")
        if source_offset // 0x8000 != (source_offset + length - 1) // 0x8000:
            raise ValueError(f"source image {i} crosses a checked 32 KiB source window")
        encoded = rom[source_offset:source_offset + length]
        if len(encoded) != length or _sha(encoded) != image["encoded_sha256"]:
            raise ValueError(f"source image {i} does not match its pinned encoded hash")
        mask = decode_image(encoded)
        if (mask.shape != (height, width)
                or _sha(mask.tobytes()) != image["index_sha256"]):
            raise ValueError(f"source image {i} does not match decoded dimensions/hash")
        records = _row_records(mask)
        image_rows.append({"image_index": i, "width": width,
                           "height": height, "records": records,
                           "sha256": _sha(records), "record_count": height + 7})

    # Pose directory is exactly 8 bytes per pose: low word, bank word,
    # full-width and full-height words. Pointer targets row record zero.
    directory_size = 8 * len(poses)
    first_start, first_end, _ = candidate[0]
    if first_start + directory_size > first_end:
        raise ValueError("pose directory does not fit first checked interval")

    next_offsets = {start: start for start, _end, _ in candidate[1:]}
    placements = {}
    for row in image_rows:
        size = len(row["records"])
        chosen = None
        for start, end, _ in candidate[1:]:
            cursor = next_offsets[start]
            if cursor + size <= end:
                chosen = (start, cursor)
                next_offsets[start] += size
                break
        if chosen is None:
            raise ValueError(f"row records for image {row['image_index']} do not fit checked intervals")
        bank, offset = chosen
        cpu = 0xC00000 + offset
        if cpu > 0xFFFFFF:
            raise ValueError("row record pointer exceeds 24-bit HiROM range")
        placements[row["image_index"]] = {"interval_start": bank, "rom_offset": offset,
                                           "cpu_address": cpu, "bytes": size,
                                           "sha256": row["sha256"], "image_index": row["image_index"]}

    directory = bytearray()
    pose_map = []
    for index, pose in enumerate(poses):
        if any(type(pose.get(k)) is not int for k in ("image_index", "width", "height")):
            raise ValueError(f"pose {index} image index/dimensions must be strict integers")
        image_index = pose["image_index"]
        if not 0 <= image_index < len(images):
            raise ValueError(f"pose {index} image index outside image directory")
        placement = placements[image_index]
        cpu = int(placement["cpu_address"])
        if cpu < 0xC00000:
            raise ValueError("invalid HiROM pointer")
        low = cpu & 0xFFFF
        bank = (cpu >> 16) & 0xFF
        width, height = pose["width"], pose["height"]
        if not (1 <= width <= 0xFFFF and 1 <= height <= 0xFFFF):
            raise ValueError(f"invalid pose dimensions at {index}")
        if (width, height) != (image_rows[image_index]["width"], image_rows[image_index]["height"]):
            raise ValueError(f"pose {index} dimensions disagree with its indexed source image")
        directory.extend(struct.pack("<HHHH", low, bank, width, height))
        pose_map.append({"pose_index": index, "image_index": image_index,
                         "pointer_low": low, "pointer_bank": bank,
                         "width": width, "height": height})

    writes = [{"offset": first_start, "data": bytes(directory),
               "reason": "8-byte-per-pose row-band directory",
               "sha256": _sha(bytes(directory))}]
    for row in image_rows:
        p = placements[row["image_index"]]
        writes.append({"offset": p["rom_offset"], "data": row["records"],
                       "reason": f"image {row['image_index']} row-band records",
                       "sha256": row["sha256"]})
    spec = {
        "schema": "BG8_ROW_BAND_SPEC_V2",
        "pose_directory_cpu": 0xC00000 + first_start,
        "pose_count": len(poses), "pose_stride": 8,
        "pose_fields": {"pointer_low": 0, "pointer_bank_word": 2,
                         "width": 4, "height": 6},
        "row_record_bytes": 4,
        "row_fields": {"min_x_inclusive": 0, "max_x_exclusive": 2},
        "row_window_start": -7, "row_window_count_formula": "height+7",
        "empty_record": [0, 0],
        "mirror_rule": "transform interval [x0,x1) to [width-x1,width-x0); row bounds remain unmirrored",
        "fallback": "malformed/out-of-domain data returns CLC and uses ordinary tile composition",
        "directory_sha256": _sha(bytes(directory)),
        "pose_rows": pose_map, "image_placements": list(placements.values()),
        "candidate_intervals": [{"offset": a, "end_exclusive": b} for a, b, _ in candidate],
        "existing_contract_ranges_checked": len(occupied),
        "writes": [{"offset": w["offset"], "bytes": len(w["data"]),
                    "sha256": w["sha256"], "reason": w["reason"]} for w in writes],
        "runtime_layout": {"pose_table_cpu": 0xC00000 + first_start,
                           "pose_count": len(poses), "descriptor_stride": 8,
                           "window_row_bytes": 4},
        "rom_modified": False,
    }
    return writes, spec
