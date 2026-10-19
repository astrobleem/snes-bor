"""Exact per-field RGB24 capture protocol for Mesen's read-only Lua API.

The emitted observer captures the full dynamically-sized Lua framebuffer, emits
full frames as fixed-width RGB24 RLE chunks, and references prior full frames
only after exact element-by-element equality. This is a capture protocol, not a
claim that MCP frame stepping pauses exactly at the requested field.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence

PIXEL_HEX = 6
RUN_HEX = 8
TOKEN_CHARS = PIXEL_HEX + RUN_HEX
MAX_PAYLOAD_CHARS = 7000  # exactly 500 whole tokens; entire log row stays bounded
FIELD_TAG = "WARMPIXFULL"
REF_TAG = "WARMPIXREF"


class PixelCaptureError(ValueError):
    """Malformed, incomplete, or inconsistent WARMPIX log protocol."""


@dataclass(frozen=True)
class CapturedFrame:
    ordinal: int
    ppu_frame: int
    width: int
    height: int
    pixels: tuple[int, ...]
    full_ordinal: int
    referenced: bool


def _validate_pixels(pixels: Sequence[int]) -> tuple[int, ...]:
    values = tuple(pixels)
    if not values:
        raise PixelCaptureError("PIXELS_EMPTY")
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFFFFFF:
            raise PixelCaptureError("RGB24_VALUE")
    return values


def encode_rgb24(pixels: Sequence[int], max_payload_chars: int = MAX_PAYLOAD_CHARS) -> tuple[str, ...]:
    """Encode RGB24 pixels as chunked fixed-width count(32)/color(24) runs."""
    values = _validate_pixels(pixels)
    if (max_payload_chars < TOKEN_CHARS or max_payload_chars > MAX_PAYLOAD_CHARS
            or max_payload_chars % TOKEN_CHARS):
        raise PixelCaptureError("CHUNK_LIMIT_ALIGNMENT")
    tokens: list[str] = []
    start = 0
    while start < len(values):
        color = values[start]
        end = start + 1
        while end < len(values) and values[end] == color:
            end += 1
        count = end - start
        tokens.append(f"{count:08X}{color:06X}")
        start = end
    per_chunk = max_payload_chars // TOKEN_CHARS
    return tuple("".join(tokens[i:i + per_chunk]) for i in range(0, len(tokens), per_chunk))


def decode_rgb24(chunks: Sequence[str], expected_pixels: int) -> tuple[int, ...]:
    """Validate and decode token-aligned RGB24 RLE chunks to exact pixels."""
    if not isinstance(expected_pixels, int) or isinstance(expected_pixels, bool) or expected_pixels <= 0:
        raise PixelCaptureError("PIXEL_COUNT")
    if not chunks:
        raise PixelCaptureError("CHUNKS_EMPTY")
    output: list[int] = []
    for chunk in chunks:
        if not isinstance(chunk, str) or not chunk or len(chunk) % TOKEN_CHARS:
            raise PixelCaptureError("RLE_CHUNK_EXTENT")
        for i in range(0, len(chunk), TOKEN_CHARS):
            token = chunk[i:i + TOKEN_CHARS]
            if not re.fullmatch(r"[0-9A-Fa-f]{14}", token):
                raise PixelCaptureError("RLE_TOKEN")
            count = int(token[:RUN_HEX], 16)
            value = int(token[RUN_HEX:], 16)
            if count == 0:
                raise PixelCaptureError("RLE_ZERO_RUN")
            if len(output) + count > expected_pixels:
                raise PixelCaptureError("RLE_OVERFLOW")
            output.extend([value] * count)
    if len(output) != expected_pixels:
        raise PixelCaptureError("RLE_UNDERFILL")
    return tuple(output)


def full_frame_records(ordinal: int, ppu_frame: int, width: int, height: int,
                       pixels: Sequence[int], *, max_payload_chars: int = MAX_PAYLOAD_CHARS) -> tuple[str, ...]:
    """Create a canonical set of full-frame log rows, useful to producers/tests."""
    values = _validate_pixels(pixels)
    if not all(isinstance(v, int) and not isinstance(v, bool) and 0 < v <= 0xFFFF
               for v in (width, height)):
        raise PixelCaptureError("FRAME_GEOMETRY")
    if not isinstance(ordinal, int) or isinstance(ordinal, bool) or not 0 < ordinal <= 0xFFFFFFFF:
        raise PixelCaptureError("FIELD_ORDINAL")
    if not isinstance(ppu_frame, int) or isinstance(ppu_frame, bool) or not 0 <= ppu_frame <= 0xFFFFFFFF:
        raise PixelCaptureError("PPU_FRAME")
    if width * height > 0xFFFFFFFF or width * height != len(values):
        raise PixelCaptureError("FRAME_PIXEL_COUNT")
    chunks = encode_rgb24(values, max_payload_chars)
    chunk_count = len(chunks)
    return tuple(
        f"{FIELD_TAG}|{ordinal:08X}|{ppu_frame:08X}|{width:04X}|{height:04X}|{len(values):08X}|{i:04X}|{chunk_count:04X}|{payload}"
        for i, payload in enumerate(chunks)
    )


def reference_record(ordinal: int, ppu_frame: int, prior_full_ordinal: int) -> str:
    if not (isinstance(ordinal, int) and 0 < ordinal <= 0xFFFFFFFF
            and isinstance(prior_full_ordinal, int) and 0 < prior_full_ordinal < ordinal):
        raise PixelCaptureError("REFERENCE_ORDINAL")
    if not isinstance(ppu_frame, int) or not 0 <= ppu_frame <= 0xFFFFFFFF:
        raise PixelCaptureError("PPU_FRAME")
    return f"{REF_TAG}|{ordinal:08X}|{ppu_frame:08X}|{prior_full_ordinal:08X}"


def parse_log(text: str | Iterable[str], *, expected_ordinals: Iterable[int] | None = None) -> dict[int, CapturedFrame]:
    """Parse captured log rows; reject missing fields/chunks and invalid refs."""
    lines = text.splitlines() if isinstance(text, str) else list(text)
    refs: dict[int, tuple[int, int]] = {}
    full_parts: dict[int, dict[str, object]] = {}
    saw = False
    for raw in lines:
        line = raw.strip()
        if not (line.startswith(FIELD_TAG + "|") or line.startswith(REF_TAG + "|")):
            continue
        saw = True
        parts = line.split("|")
        try:
            if parts[0] == REF_TAG:
                if len(parts) != 4 or not all(re.fullmatch(r"[0-9A-Fa-f]{8}", x) for x in parts[1:]):
                    raise PixelCaptureError("REF_ROW_FORMAT")
                ordinal, frame, prior = (int(x, 16) for x in parts[1:])
                if ordinal <= 0 or prior <= 0 or prior >= ordinal:
                    raise PixelCaptureError("REFERENCE_ORDINAL")
                if ordinal in refs or ordinal in full_parts:
                    raise PixelCaptureError("DUPLICATE_ORDINAL")
                refs[ordinal] = (frame, prior)
                continue
            if len(parts) != 9:
                raise PixelCaptureError("FULL_ROW_FORMAT")
            if not all(re.fullmatch(r"[0-9A-Fa-f]{8}", parts[i]) for i in (1, 2, 5)):
                raise PixelCaptureError("FULL_ROW_U32")
            if not all(re.fullmatch(r"[0-9A-Fa-f]{4}", parts[i]) for i in (3, 4, 6, 7)):
                raise PixelCaptureError("FULL_ROW_U16")
            ordinal, frame = int(parts[1], 16), int(parts[2], 16)
            width, height, count = int(parts[3], 16), int(parts[4], 16), int(parts[5], 16)
            chunk_index, chunk_count = int(parts[6], 16), int(parts[7], 16)
            payload = parts[8]
            if ordinal == 0 or width == 0 or height == 0 or width * height != count:
                raise PixelCaptureError("FRAME_PIXEL_COUNT")
            if chunk_count == 0 or chunk_index >= chunk_count:
                raise PixelCaptureError("CHUNK_INDEX")
            if not payload or len(payload) > MAX_PAYLOAD_CHARS or len(payload) % TOKEN_CHARS:
                raise PixelCaptureError("CHUNK_PAYLOAD_EXTENT")
            bucket = full_parts.setdefault(ordinal, {
                "frame": frame, "width": width, "height": height, "count": count,
                "chunk_count": chunk_count, "chunks": {},
            })
            if ordinal in refs:
                raise PixelCaptureError("DUPLICATE_ORDINAL")
            if (bucket["frame"], bucket["width"], bucket["height"], bucket["count"], bucket["chunk_count"]) != (
                    frame, width, height, count, chunk_count):
                raise PixelCaptureError("CHUNK_HEADER_MISMATCH")
            chunks = bucket["chunks"]
            assert isinstance(chunks, dict)
            if chunk_index in chunks:
                raise PixelCaptureError("DUPLICATE_CHUNK")
            chunks[chunk_index] = payload
        except PixelCaptureError:
            raise
        except (ValueError, TypeError, IndexError) as exc:
            raise PixelCaptureError("ROW_PARSE") from exc
    if not saw:
        raise PixelCaptureError("NO_CAPTURE_ROWS")
    ordinals = set(full_parts) | set(refs)
    if not ordinals:
        raise PixelCaptureError("NO_FIELDS")
    ordered = sorted(ordinals)
    if expected_ordinals is None:
        raise PixelCaptureError("EXPECTED_ORDINALS_REQUIRED")
    expected = tuple(expected_ordinals)
    if (not expected or expected[0] != 1
            or expected != tuple(range(1, expected[-1] + 1))):
        raise PixelCaptureError("EXPECTED_ORDINALS_INVALID")
    if ordered != list(expected):
        raise PixelCaptureError("MISSING_OR_EXTRA_ORDINAL")
    frames: dict[int, CapturedFrame] = {}
    for ordinal in ordered:
        if ordinal in full_parts:
            bucket = full_parts[ordinal]
            chunks = bucket["chunks"]
            assert isinstance(chunks, dict)
            chunk_count = int(bucket["chunk_count"])
            if sorted(chunks) != list(range(chunk_count)):
                raise PixelCaptureError("MISSING_CHUNK")
            pixels = decode_rgb24([chunks[i] for i in range(chunk_count)], int(bucket["count"]))
            frames[ordinal] = CapturedFrame(ordinal, int(bucket["frame"]), int(bucket["width"]),
                                            int(bucket["height"]), pixels, ordinal, False)
        else:
            frame, prior = refs[ordinal]
            if prior not in frames or frames[prior].referenced:
                raise PixelCaptureError("REFERENCE_NOT_PRIOR_FULL")
            source = frames[prior]
            frames[ordinal] = CapturedFrame(ordinal, frame, source.width, source.height,
                                            source.pixels, prior, True)
    return frames


def lua_observer() -> str:
    """Return read-only Mesen Lua callback source for exact full-buffer evidence."""
    return r'''-- WARMPIX RGB24 observer; read-only, endFrame callback, local field ordinal.
local WARMPIX_MAX_PAYLOAD = 7000 -- 500 * 14 hex chars per whole run token
local WARMPIX_TOKEN = 14
local warmPixOrdinal = 0
local warmPixPrevious = nil
local warmPixLastFullOrdinal = nil

local function warmPixEqual(a, b)
  if b == nil or #a ~= #b then return false end
  for i = 1, #a do
    if a[i] ~= b[i] then return false end
  end
  return true
end

local function warmPixLogFull(ordinal, cpuFrame, width, height, pixels)
  local runs = {}
  local i = 1
  while i <= #pixels do
    local color = pixels[i]
    local j = i + 1
    while j <= #pixels and pixels[j] == color do j = j + 1 end
    runs[#runs + 1] = string.format("%08X%06X", j - i, color)
    i = j
  end
  local chunks = {}
  local payload = ""
  for _, token in ipairs(runs) do
    if #payload + #token > WARMPIX_MAX_PAYLOAD then
      chunks[#chunks + 1] = payload
      payload = token
    else
      payload = payload .. token
    end
  end
  if #payload > 0 then chunks[#chunks + 1] = payload end
  for chunkIndex, part in ipairs(chunks) do
    emu.log(string.format("WARMPIXFULL|%08X|%08X|%04X|%04X|%08X|%04X|%04X|%s",
      ordinal, cpuFrame, width, height, #pixels, chunkIndex - 1, #chunks, part))
  end
end

local function WarmPixOwned7FFB88B6D0_EndFrame(cpuType)
  if emu.read16(0x7ffb88, emu.memType.snesMemory) ~= 0xb6d0 then return end
  local raw = emu.getScreenBuffer()
  -- Both Lua APIs explicitly disable overscan (LuaApi::GetRenderedFrame and
  -- InternalGetScreenSize). Crop the returned full buffer using the console
  -- settings, then require independent MCP visible-viewport calibration.
  local rawSize = emu.getScreenSize()
  local surface = emu.getDrawSurfaceSize(emu.drawSurface.consoleScreen)
  local crop = surface.overscan
  if crop.left < 0 or crop.right < 0 or crop.top < 0 or crop.bottom < 0
      or crop.left + crop.right >= rawSize.width
      or crop.top + crop.bottom >= rawSize.height then
    error("WARMPIX_CROP_BOUNDS")
  end
  local width = rawSize.width - crop.left - crop.right
  local height = rawSize.height - crop.top - crop.bottom
  if width ~= surface.visibleWidth or height ~= surface.visibleHeight then
    error("WARMPIX_UNSUPPORTED_FILTER_GEOMETRY")
  end
  if width <= 0 or height <= 0 or #raw ~= rawSize.width * rawSize.height then
    error("WARMPIX_DIMENSION_BUFFER_MISMATCH|"..width.."|"..height.."|"..#raw.."|"..rawSize.width.."|"..rawSize.height.."|"..surface.visibleWidth.."|"..surface.visibleHeight)
  end
  local pixels = {}
  for y = crop.top, rawSize.height - crop.bottom - 1 do
    for x = crop.left, rawSize.width - crop.right - 1 do
      pixels[#pixels + 1] = raw[y * rawSize.width + x + 1]
    end
  end
  if #pixels ~= width * height then error("WARMPIX_CROP_EXTENT") end
  local state = emu.getState()
  local cpuFrame = state['ppu.frameCount']
  if warmPixOrdinal == 0 then
    emu.log('WARMPIXGEOMETRY|'..rawSize.width..'|'..rawSize.height..'|'..crop.left..'|'..crop.right..'|'..crop.top..'|'..crop.bottom..'|'..width..'|'..height)
  end
  warmPixOrdinal = warmPixOrdinal + 1
  if warmPixEqual(pixels, warmPixPrevious) then
    emu.log(string.format("WARMPIXREF|%08X|%08X|%08X",
      warmPixOrdinal, cpuFrame, warmPixLastFullOrdinal))
  else
    warmPixLogFull(warmPixOrdinal, cpuFrame, width, height, pixels)
    warmPixLastFullOrdinal = warmPixOrdinal
  end
  warmPixPrevious = pixels
end

emu.addEventCallback(WarmPixOwned7FFB88B6D0_EndFrame, emu.eventType.endFrame)
'''
