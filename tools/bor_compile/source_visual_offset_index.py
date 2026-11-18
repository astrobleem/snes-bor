"""Dependency-light SVIS block-offset index and version-footer helpers."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

RUNTIME_CATALOG_MAGIC = b"SVIS1\0"
RUNTIME_CATALOG_BINDING_MAGIC = b"SVIX"
RUNTIME_CATALOG_BINDING_BYTES = 8
RUNTIME_BLOCK_INDEX_RECORD_BYTES = 3
RUNTIME_BLOCK_INDEX_BANK_BYTES = 0x8000
RUNTIME_BLOCK_INDEX_BANK0 = 64
RUNTIME_BLOCK_INDEX_BANK1 = 65
RUNTIME_BLOCK_INDEX_BANK0_ENTRIES = RUNTIME_BLOCK_INDEX_BANK_BYTES // RUNTIME_BLOCK_INDEX_RECORD_BYTES
RUNTIME_BLOCK_PAYLOAD_BYTES = 256


def pack_runtime_block_offset_index(catalog_blob: bytes) -> bytes:
    """Pack one catalog-relative 24-bit offset for every serialized block row.

    Entries preserve the catalog's sorted block-ID order. Unsupported payload
    sizes, non-24-bit offsets, malformed table bounds, and out-of-catalog
    payloads are rejected during the build rather than at runtime.
    """
    if len(catalog_blob) < 18:
        raise ValueError("SOURCE_VISUAL_BLOCK_INDEX_CATALOG_HEADER")
    magic, entry_count, piece_count, block_count, palette_count, sheet_count, entry_bytes = \
        struct.unpack_from("<6sHHHHHH", catalog_blob, 0)
    if magic != RUNTIME_CATALOG_MAGIC or entry_bytes != 24:
        raise ValueError("SOURCE_VISUAL_BLOCK_INDEX_CATALOG_HEADER")
    block_offset = 18 + entry_count * entry_bytes + piece_count * 16
    block_rows_end = block_offset + block_count * 42
    catalog_payload_offset = block_rows_end + palette_count * 42 + sheet_count * 42
    if catalog_payload_offset > len(catalog_blob):
        raise ValueError("SOURCE_VISUAL_BLOCK_INDEX_TABLE_BOUNDS")
    offsets = bytearray()
    for index in range(block_count):
        row = block_offset + index * 42
        _resource_sha, size, payload_offset, payload_length = struct.unpack_from(
            "<32sHII", catalog_blob, row)
        if size != RUNTIME_BLOCK_PAYLOAD_BYTES or payload_length != RUNTIME_BLOCK_PAYLOAD_BYTES:
            raise ValueError("SOURCE_VISUAL_BLOCK_INDEX_UNSUPPORTED_SIZE")
        if payload_offset >= (1 << 24):
            raise ValueError("SOURCE_VISUAL_BLOCK_INDEX_OFFSET_WIDTH")
        if payload_offset < catalog_payload_offset or payload_offset + payload_length > len(catalog_blob):
            raise ValueError("SOURCE_VISUAL_BLOCK_INDEX_PAYLOAD_BOUNDS")
        offsets.extend(payload_offset.to_bytes(RUNTIME_BLOCK_INDEX_RECORD_BYTES, "little"))
    return bytes(offsets)


def make_runtime_catalog_binding_footer(catalog_blob: bytes) -> bytes:
    """Return ``SVIX`` plus the little-endian CRC32 of the exact SVIS bytes."""
    return RUNTIME_CATALOG_BINDING_MAGIC + \
        (zlib.crc32(catalog_blob) & 0xFFFFFFFF).to_bytes(4, "little")


def write_runtime_block_offset_index(catalog_blob: bytes, generated_dir: Path) -> dict:
    """Write dense index data and two bank-bounded Poppy include chunks."""
    generated_dir = Path(generated_dir)
    generated_dir.mkdir(parents=True, exist_ok=True)
    index = pack_runtime_block_offset_index(catalog_blob)
    (generated_dir / "production_source_visual_block_offset_index.bin").write_bytes(index)
    bank0_bytes = RUNTIME_BLOCK_INDEX_BANK0_ENTRIES * RUNTIME_BLOCK_INDEX_RECORD_BYTES
    bank0 = index[:bank0_bytes]
    bank1 = index[bank0_bytes:]
    if len(bank0) > RUNTIME_BLOCK_INDEX_BANK_BYTES or len(bank1) > RUNTIME_BLOCK_INDEX_BANK_BYTES:
        raise ValueError("SOURCE_VISUAL_BLOCK_INDEX_ROM_BANK_CAPACITY")
    if len(index) != len(bank0) + len(bank1):
        raise ValueError("SOURCE_VISUAL_BLOCK_INDEX_SPLIT")
    (generated_dir / "production_source_visual_block_offset_bank0.bin").write_bytes(bank0)
    (generated_dir / "production_source_visual_block_offset_bank1.bin").write_bytes(bank1)
    include = [
        "; Generated from source_visual_offset_index.py; do not edit.",
        ".bank 64",
        ".org $8000",
        "SourceVisual_BlockOffsetIndexBank0:",
        '    .incbin "production_source_visual_block_offset_bank0.bin"',
        ".bank 65",
        ".org $8000",
        "SourceVisual_BlockOffsetIndexBank1:",
        '    .incbin "production_source_visual_block_offset_bank1.bin"',
        "",
    ]
    (generated_dir / "production_source_visual_block_offsets.pasm").write_text(
        "\n".join(include), encoding="ascii", newline="\n")
    max_offset = max((int.from_bytes(index[i:i + 3], "little")
                      for i in range(0, len(index), 3)), default=0)
    return {
        "block_count": len(index) // RUNTIME_BLOCK_INDEX_RECORD_BYTES,
        "record_bytes": RUNTIME_BLOCK_INDEX_RECORD_BYTES,
        "index_bytes": len(index),
        "bank0_entries": len(bank0) // RUNTIME_BLOCK_INDEX_RECORD_BYTES,
        "bank0_bytes": len(bank0),
        "bank1_entries": len(bank1) // RUNTIME_BLOCK_INDEX_RECORD_BYTES,
        "bank1_bytes": len(bank1),
        "max_payload_offset": max_offset,
        "catalog_crc32": zlib.crc32(catalog_blob) & 0xFFFFFFFF,
    }
