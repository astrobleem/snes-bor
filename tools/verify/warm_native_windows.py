"""Fail-closed timing analysis for warm renderer queue/map work.

The warm capture observer emits WARMPOINT rows as
``name|masterClock|ppuFrame|...`` and WARMPPU boundary rows as
``VBLANK_START|masterClock|ppuFrame`` / ``VBLANK_END|...``.  This module
only analyzes those read-only log records; it does not infer blanking from
the renderer's own labels.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


_POINT_NAMES = {
    "WarmRenderer_NbQueueHasPending": "queue_start",
    "WarmRenderer_NbQueueDrainDone": "queue_done",
    "WarmRenderer_NbPairBegin": "pair_begin",
    "WarmRenderer_NbPairComplete": "pair_done",
    "WarmRenderer_NbMapCommit": "map_start",
    "WarmRenderer_NbMapsComplete": "map_done",
}
_PPU_RE = re.compile(r"WARMPPU\|(VBLANK_START|VBLANK_END)\|([^|]+)\|([^|]+)")


@dataclass(frozen=True)
class _Event:
    kind: str
    clock: int
    frame: int
    order: int


def _int_field(raw: str, what: str) -> int:
    try:
        value = int(raw, 0)
    except ValueError as exc:
        raise ValueError(f"malformed {what}: {raw!r}") from exc
    if value < 0:
        raise ValueError(f"negative {what}: {raw!r}")
    return value


def _parse(logtext: str) -> tuple[list[_Event], list[_Event]]:
    points: list[_Event] = []
    ppu: list[_Event] = []
    for order, line in enumerate(logtext.splitlines()):
        if "WARMPOINT|" in line:
            payload = line[line.index("WARMPOINT|"):]
            fields = payload.split("|")
            if len(fields) < 33 or fields[0] != "WARMPOINT":
                raise ValueError(f"malformed WARMPOINT row at line {order + 1}")
            _, name, raw_clock, raw_frame, *_ = fields
            try:
                for value in fields[2:]:
                    int(value, 0)
            except ValueError as exc:
                raise ValueError(f"malformed WARMPOINT numeric payload at line {order + 1}") from exc
            kind = _POINT_NAMES.get(name)
            if kind is not None:
                points.append(_Event(kind, _int_field(raw_clock, "clock"),
                                     _int_field(raw_frame, "frame"), order))
        if "WARMPPU|" in line:
            payload = line[line.index("WARMPPU|"):]
            match = _PPU_RE.fullmatch(payload)
            if not match:
                raise ValueError(f"malformed WARMPPU row at line {order + 1}")
            tag, raw_clock, raw_frame = match.groups()
            ppu.append(_Event(tag.lower(), _int_field(raw_clock, "clock"),
                              _int_field(raw_frame, "frame"), order))
    return points, ppu


def _windows(boundaries: list[_Event]) -> tuple[list[dict[str, int]], list[_Event]]:
    """Pair chronological vblank boundaries, allowing only edge partials."""
    if not boundaries:
        raise ValueError("missing VBlank boundaries")
    if any((b.clock, b.order) <= (a.clock, a.order)
           for a, b in zip(boundaries, boundaries[1:])):
        raise ValueError("VBlank boundary order/clock mismatch")
    for a,b in zip(boundaries,boundaries[1:]):
        expected=a.frame+1 if a.kind=='vblank_start' else a.frame
        if b.frame!=expected:
            raise ValueError('missing or inconsistent physical VBlank edge')
    intervals: list[dict[str, int]] = []
    leading: list[_Event] = []
    i = 0
    if boundaries[0].kind == "vblank_end":
        leading.append(boundaries[0])
        i = 1
    while i + 1 < len(boundaries):
        start, end = boundaries[i], boundaries[i + 1]
        if start.kind != "vblank_start" or end.kind != "vblank_end":
            raise ValueError("unpaired VBlank boundaries")
        if end.clock <= start.clock or end.frame < start.frame:
            raise ValueError("VBlank interval chronology mismatch")
        intervals.append({"start_clock": start.clock, "end_clock": end.clock,
                          "start_frame": start.frame, "end_frame": end.frame,
                          "start_order": start.order, "end_order": end.order})
        i += 2
    trailing: list[_Event] = []
    if i < len(boundaries):
        if boundaries[i].kind != "vblank_start":
            raise ValueError("unpaired VBlank boundaries")
        trailing.append(boundaries[i])
    if not intervals:
        raise ValueError("missing complete VBlank interval")
    return intervals, leading + trailing


def _containing(event: _Event, intervals: list[dict[str, int]]) -> dict[str, int]:
    found = [w for w in intervals if w["start_clock"] <= event.clock < w["end_clock"]
             and w["start_order"] < event.order < w["end_order"]]
    if len(found) != 1:
        raise ValueError(f"{event.kind} is outside or ambiguous across VBlank")
    return found[0]


def _paired_work(points: list[_Event], start_kind: str, done_kind: str,
                 label: str) -> list[tuple[_Event, _Event]]:
    pairs: list[tuple[_Event, _Event]] = []
    start: _Event | None = None
    for event in points:
        if event.kind == start_kind:
            if start is not None:
                raise ValueError(f"nested {label} starts")
            start = event
        elif event.kind == done_kind:
            if start is None:
                raise ValueError(f"{label} completion without start")
            if (event.clock <= start.clock or event.order <= start.order):
                raise ValueError(f"{label} chronology mismatch")
            pairs.append((start, event))
            start = None
    if start is not None:
        raise ValueError(f"missing {label} completion")
    if not pairs:
        raise ValueError(f"missing {label} evidence")
    return pairs


def _check_window(start: _Event, done: _Event, intervals: list[dict[str, int]],
                  label: str) -> tuple[dict[str, int], int]:
    a = _containing(start, intervals)
    b = _containing(done, intervals)
    if a is not b:
        raise ValueError(f"{label} crosses VBlank boundary")
    if not (a["start_frame"] <= start.frame <= a["end_frame"] and
            a["start_frame"] <= done.frame <= a["end_frame"]):
        raise ValueError(f"{label} PPU frame mismatch")
    margin = a["end_clock"] - done.clock
    if margin < 10_000:
        raise ValueError(f"{label} lacks 10000-clock VBlank margin")
    return a, margin


def _measure(points: list[_Event], intervals: list[dict[str, int]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queue_pairs = _paired_work(points, "queue_start", "queue_done", "queue batch")
    batches: list[dict[str, Any]] = []
    used_pair_orders: set[int] = set()
    for batch_start, batch_done in queue_pairs:
        if batch_done.clock <= batch_start.clock:
            raise ValueError("queue batch chronology mismatch")
        contained = [e for e in points if batch_start.order < e.order < batch_done.order]
        pair_events = [e for e in contained if e.kind in ("pair_begin", "pair_done")]
        # Match every DMA pair in strict order. Any extra completion or active
        # transfer means the reported queue drain cannot certify retirement.
        pair_seq: list[_Event] = []
        waiting = False
        for e in pair_events:
            if e.kind == "pair_begin":
                if waiting:
                    raise ValueError("active DMA overlapped another pair begin")
                waiting = True
            else:
                if not waiting:
                    raise ValueError("DMA completion without pair begin")
                waiting = False
            pair_seq.append(e)
        if waiting or not pair_seq:
            raise ValueError("queue batch has active DMA or no matched pairs")
        if len(pair_seq) % 2:
            raise ValueError("queue batch has unmatched DMA pair")
        transfer_start = next(e for e in pair_seq if e.kind == "pair_begin")
        # QueueHasPending is a staging marker and may precede the renderer's
        # VBlank wait. The actual transfer window begins at the first DMA pair.
        if transfer_start.clock <= batch_start.clock:
            raise ValueError("DMA starts before queue batch is staged")
        interval, margin = _check_window(transfer_start, batch_done, intervals, "queue batch")
        for a, b in zip(pair_seq[::2], pair_seq[1::2]):
            if not (batch_start.clock < a.clock < b.clock < batch_done.clock):
                raise ValueError("DMA pair chronology mismatch")
            pair_window, _ = _check_window(a, b, intervals, "DMA pair")
            if pair_window is not interval:
                raise ValueError("DMA pair crosses VBlank boundary")
            used_pair_orders.update((a.order, b.order))
        batches.append({"queued_clock": batch_start.clock,
                        "start_clock": transfer_start.clock,
                        "complete_clock": batch_done.clock,
                        "dma_pairs": len(pair_seq) // 2,
                        "vblank_start": interval["start_clock"],
                        "vblank_end": interval["end_clock"],
                        "vblank_frame_start": interval["start_frame"],
                        "vblank_frame_end": interval["end_frame"],
                        "duration_clocks": batch_done.clock - transfer_start.clock,
                        "staging_and_wait_clocks": transfer_start.clock - batch_start.clock,
                        "margin_clocks": margin})
    # A pair event not covered by one complete batch is unaccounted DMA work.
    for e in points:
        if e.kind in ("pair_begin", "pair_done") and e.order not in used_pair_orders:
            raise ValueError("DMA pair event outside a complete queue batch")

    map_pairs = _paired_work(points, "map_start", "map_done", "map commit")
    maps: list[dict[str, Any]] = []
    for start, done in map_pairs:
        interval, margin = _check_window(start, done, intervals, "map commit")
        maps.append({"start_clock": start.clock, "complete_clock": done.clock,
                     "vblank_start": interval["start_clock"],
                     "vblank_end": interval["end_clock"],
                     "vblank_frame_start": interval["start_frame"],
                     "vblank_frame_end": interval["end_frame"],
                     "duration_clocks": done.clock - start.clock,
                     "margin_clocks": margin})
    return batches, maps


def analyze(logtext: str) -> dict[str, Any]:
    """Return measured windows, with ``accepted=False`` on any missing evidence."""
    result: dict[str, Any] = {"accepted": False, "batches": [], "maps": [],
                              "vblank_windows": [], "errors": []}
    if not isinstance(logtext, str) or not logtext.strip():
        result["errors"] = ["empty log"]
        return result
    try:
        points, raw_boundaries = _parse(logtext)
        if not points:
            raise ValueError("missing warm timing events")
        windows, edge_partials = _windows(raw_boundaries)
        batches, maps = _measure(points, windows)
        completion_orders = {e.order for e in points
                             if e.kind in ("queue_done", "map_done")}
        if any(e.order in completion_orders for e in edge_partials):
            raise ValueError("DMA/map completion in partial VBlank edge")
        # Also reject work completions outside all full windows. The queue/map
        # checks normally catch this; this guard covers malformed extra rows.
        for e in points:
            if e.kind in ("queue_done", "map_done"):
                _containing(e, windows)
        result.update({"accepted": True, "batches": batches, "maps": maps,
                       "vblank_windows": windows,
                       "leading_or_trailing_partial_boundaries": len(edge_partials)})
    except ValueError as exc:
        result["errors"] = [str(exc)]
    return result
