"""Read-only, compact end-frame observer for the warm world capture.

The observer emits a fixed, self-describing sequence of canonical WRAM ranges
instead of thousands of individual Lua log fields.  The Python decoder uses
the exact same schema to reconstruct progress rows and verify accepted SPC
ring packets.  It performs no writes and does not affect emulation state.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence


_FIXED_RANGES = (
    ("actor_hex", 0x414000, 80),
    ("side_hex", 0x416800, 64),
    ("latest_hex", 0x7E7800, 148),
    ("render_pin_hex", 0x7E9600, 148),
    ("display_pin_hex", 0x7E9700, 148),
    ("cold_pin_hex", 0x7FBA00, 146),
    ("clock", "SourceClock4086_Ready", 64),
    ("world", "SourceWorldTick4086_Ready", 64),
    ("work", 0x7E7700, 24),
    ("warm_controls", 0x7E9500, 32),
    ("raw_input1", "SourceInputController_Raw1", 2),
    ("raw_input2", "SourceInputController_Raw2", 2),
    ("mapped_input_hex", "VmSourceInput_Data", 12),
    ("audio_control", 0x7E8100, 64),
    ("channel11", 0x7E8140 + 440, 40),
    ("compact11", 0x7EFF88 + 88, 8),
    ("transport", "TadPrivate_stream_frame", 64),
    ("chunks_accepted", "TadPrivate_stream_chunks_accepted", 2),
    ("source_status", "SourceAudio_Status", 2),
    ("actual_joy", 0x4218, 4),
    ("world_time", "VmSourceWorld_Time", 4),
    ("constructor_ready_word", 0x7FFB96, 2),
)

_CLOCK_SYMBOL_FIELDS = (
    ("SourceClock4086_TimeLo", 4, "source_time"),
    ("SourceClock4086_Due", 2, "due"),
)
_WORLD_SYMBOL_FIELDS = (
    ("SourceWorldTick4086_TimeLo", 4, "world_tick_time"),
    ("SourceWorldTick4086_State", 2, "world_state"),
    ("SourceWorldTick4086_Phase", 2, "phase"),
    ("SourceWorldTick4086_Pending", 2, "pending"),
    ("SourceWorldTick4086_Fault", 2, "source_fault"),
)


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFF:
        raise ValueError("WARM_FIELD_ADDRESS:" + name)
    return value


def schema(contract):
    """Resolve all fixed ranges and symbol-derived scalar fields.

    Any symbol intended to be decoded from the 64-byte owner rows must lie
    wholly inside its declared row.  A symbol outside the row is captured as
    a separate explicit range, never guessed from an assumed structure layout.
    """
    if not isinstance(contract, Mapping) or not isinstance(contract.get("symbols"), Mapping):
        raise ValueError("WARM_FIELD_CONTRACT_SYMBOLS")
    sy = contract["symbols"]
    ranges = []
    for name, address, length in _FIXED_RANGES:
        if isinstance(address, str):
            if address not in sy:
                raise ValueError("WARM_FIELD_SYMBOL:" + address)
            address = _integer(sy[address], address)
        else:
            address = _integer(address, name)
        if address + length > 0x1000000:
            raise ValueError("WARM_FIELD_EXTENT:" + name)
        ranges.append(dict(name=name, address=address, length=length))
    by_name = {r["name"]: r for r in ranges}
    fields = []
    for base_name, specs in (("clock", _CLOCK_SYMBOL_FIELDS),
                             ("world", _WORLD_SYMBOL_FIELDS)):
        owner = by_name[base_name]
        for symbol_name, length, field_name in specs:
            if symbol_name not in sy:
                raise ValueError("WARM_FIELD_SYMBOL:" + symbol_name)
            address = _integer(sy[symbol_name], symbol_name)
            offset = address - owner["address"]
            if 0 <= offset and offset + length <= owner["length"]:
                fields.append(dict(name=field_name, range=base_name,
                                   offset=offset, length=length))
            else:
                explicit = dict(name=field_name + "_bytes", address=address,
                                 length=length)
                if address + length > 0x1000000:
                    raise ValueError("WARM_FIELD_EXTENT:" + field_name)
                ranges.append(explicit)
                fields.append(dict(name=field_name, range=explicit["name"],
                                   offset=0, length=length))
    audio = contract.get("audio") or contract.get("config", {}).get("audio")
    if audio:
        payload_bytes = audio.get("payload_bytes")
        if isinstance(payload_bytes, bool) or not isinstance(payload_bytes, int) or payload_bytes <= 0:
            raise ValueError("WARM_FIELD_AUDIO_PAYLOAD_LENGTH")
        max_chunks = (payload_bytes + 143) // 144
    else:
        max_chunks = 0
    if "TAD_STREAM_RING_ADDR" not in sy:
        if audio:
            raise ValueError("WARM_FIELD_SYMBOL:TAD_STREAM_RING_ADDR")
        ring = None
    else:
        ring = _integer(sy["TAD_STREAM_RING_ADDR"], "TAD_STREAM_RING_ADDR")
        if ring + 8 * 144 > 0x10000:
            raise ValueError("WARM_FIELD_SPC_RING_EXTENT")
    return dict(ranges=ranges, fields=fields, ring_address=ring,
                max_payload_chunks=max_chunks,
                payload_bytes=(audio.get("payload_bytes") if audio else 0),
                audio_enabled=bool(audio))


def observer(contract):
    """Return (Lua source, observer metadata) for a read-only endFrame hook."""
    resolved = schema(contract)
    ranges = resolved["ranges"]
    ranges_lua = "local warmFieldRanges={" + ",".join(
        "{" + str(r["address"]) + "," + str(r["length"]) + "}"
        for r in ranges) + "}\n"
    names_lua = "local warmFieldNames={" + ",".join(
        "'" + r["name"] + "'" for r in ranges) + "}\n"
    # `spcRam` is Mesen's Lua enum spelling; the repository's MCP reader
    # exposes the same memory domain as `SpcRam`.
    lua = ranges_lua + names_lua + f"""
local warmFieldMt=emu.memType.snesMemory
local warmFieldSpc=emu.memType.spcRam
local warmFieldPrevAccepted=0
local warmFieldMaxChunks={resolved['max_payload_chunks']}
local function warmFieldHex(address,length,mt)
 local out={{}}
 for i=0,length-1 do out[#out+1]=string.format('%02x',emu.read(address+i,mt)) end
 return table.concat(out)
end
local function warmFieldWord(address)
 return emu.read(address,warmFieldMt)+256*emu.read(address+1,warmFieldMt)
end
emu.addEventCallback(function()
 if word(0x7ffb88)~=0xb6d0 then return end
 local s=emu.getState();local packed={{}}
 for _,r in ipairs(warmFieldRanges) do
  packed[#packed+1]=warmFieldHex(r[1],r[2],warmFieldMt)
 end
 emu.log('WARMFIELDDATA|'..s['ppu.frameCount']..'|'..s.masterClock..'|'..table.concat(packed))
 local accepted=warmFieldWord({dict((r['name'],r['address']) for r in ranges)['chunks_accepted']})
 if accepted<warmFieldPrevAccepted then
  emu.log('WARMFIELDAUDIOFAULT|ACCEPTED_REWIND|'..accepted..'|'..warmFieldPrevAccepted)
  warmFieldPrevAccepted=accepted;return
 end
 local delta=accepted-warmFieldPrevAccepted
 if delta>8 then
  emu.log('WARMFIELDAUDIOFAULT|RING_OVERRUN|'..delta..'|'..warmFieldPrevAccepted..'|'..accepted)
  warmFieldPrevAccepted=accepted;return
 end
 if accepted>warmFieldMaxChunks then
  emu.log('WARMFIELDAUDIOFAULT|PAYLOAD_OVERRUN|'..accepted..'|'..warmFieldMaxChunks)
  warmFieldPrevAccepted=accepted;return
 end
 for chunk=warmFieldPrevAccepted,accepted-1 do
  local address={resolved['ring_address'] or 0}+((chunk%8)*144)
  local packet=warmFieldHex(address,144,warmFieldSpc)
  emu.log('WARMARMPACKET|'..chunk..'|'..s['ppu.frameCount']..'|'..packet)
 end
 warmFieldPrevAccepted=accepted
end,emu.eventType.endFrame)
"""
    return lua, dict(schema="WARM_FIELD_STATE_V1", ranges=ranges,
                     scalar_fields=resolved["fields"],
                     audio_enabled=resolved["audio_enabled"],
                     payload_bytes=resolved["payload_bytes"],
                     ring_address=resolved["ring_address"],
                     max_payload_chunks=resolved["max_payload_chunks"],
                     lua_spc_memory_enum="emu.memType.spcRam",
                     existing_host_reader_enum="SpcRam",
                     source_references=[
                         "tools/verify/m4_warm_world_capture.py:596-603",
                         "tools/verify/m4_projectile_audio_fixture.py:207-211"],
                     ring_symbol_reference="contract.symbols.TAD_STREAM_RING_ADDR",
                     accepted_symbol_reference="contract.symbols.TadPrivate_stream_chunks_accepted")


def _u16(data, offset=0):
    return int.from_bytes(data[offset:offset + 2], "little")


def _u32(data, offset=0):
    return int.from_bytes(data[offset:offset + 4], "little")


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(text, expected_frame_ids, contract, expected_payload=None):
    """Strictly decode observer events and return canonical progress/audio rows.

    `expected_frame_ids` is mandatory so a missing or duplicate endFrame cannot
    silently turn into a shorter successful capture.  The packet payload is
    the actual prepared ROM byte stream; when given, all 144-byte ring entries
    are checked at `chunk * 144`, including only the established slot-7 header
    mutation for nonfinal ring-slot-7 packets.
    """
    if (not isinstance(expected_frame_ids, Sequence) or isinstance(expected_frame_ids, (str, bytes))
            or not expected_frame_ids):
        raise ValueError("WARM_FIELD_EXPECTED_FRAMES")
    expected = list(expected_frame_ids)
    if any(isinstance(f, bool) or not isinstance(f, int) or f < 0 for f in expected):
        raise ValueError("WARM_FIELD_EXPECTED_FRAME_ID")
    if len(set(expected)) != len(expected):
        raise ValueError("WARM_FIELD_DUPLICATE_EXPECTED_FRAME")
    resolved = schema(contract)
    if expected_payload is not None:
        expected_payload = bytes(expected_payload)
        if len(expected_payload) != resolved["payload_bytes"]:
            raise ValueError("WARM_FIELD_AUDIO_PAYLOAD_LENGTH_MISMATCH")
    ranges = resolved["ranges"]
    packed_bytes = sum(r["length"] for r in ranges)
    rows_by_frame = {}
    packets = []
    malformed = []
    faults = []
    for line in text.splitlines():
        if "WARMFIELDAUDIOFAULT|" in line:
            faults.append(line.split("WARMFIELDAUDIOFAULT|", 1)[1])
        if "WARMFIELDDATA|" in line:
            try:
                frame_s, clock_s, payload = line.split("WARMFIELDDATA|", 1)[1].split("|", 2)
                frame, master_clock = int(frame_s), int(clock_s)
                if frame in rows_by_frame:
                    raise ValueError("DUPLICATE_FRAME")
                if not re.fullmatch(r"[0-9a-f]+", payload) or len(payload) != packed_bytes * 2:
                    raise ValueError("PACKED_HEX_LENGTH")
                raw = bytes.fromhex(payload)
                blobs = {}
                cursor = 0
                for r in ranges:
                    blobs[r["name"]] = raw[cursor:cursor + r["length"]]
                    cursor += r["length"]
                decoded = dict(frame=frame, master_clock=master_clock,
                               master_clock_source="Lua endFrame field observer",
                               ranges_hex={k: v.hex() for k, v in blobs.items()})
                for field in resolved["fields"]:
                    decoded[field["name"]] = int.from_bytes(
                        blobs[field["range"]][field["offset"]:field["offset"] + field["length"]], "little")
                decoded.update(index=None, mcp_state=None, frames_advanced=None,
                    work=blobs["work"].hex(), clock=blobs["clock"].hex(), world=blobs["world"].hex(),
                    actor_hex=blobs["actor_hex"].hex(), side_hex=blobs["side_hex"].hex(),
                    latest_hex=blobs["latest_hex"].hex(), render_pin_hex=blobs["render_pin_hex"].hex(),
                    display_pin_hex=blobs["display_pin_hex"].hex(), cold_pin_hex=blobs["cold_pin_hex"].hex(),
                    latest_epoch=int.from_bytes(blobs["latest_hex"][144:148],'little'),
                    display_epoch=int.from_bytes(blobs["display_pin_hex"][144:148],'little'),
                    latest_matches_current=(blobs["latest_hex"][:144] == blobs["actor_hex"] + blobs["side_hex"]),
                    constructor_ready_word=_u16(blobs["constructor_ready_word"]),
                    constructor_ready=_u16(blobs["constructor_ready_word"]) == 0xB4B8,
                    warm_status=_u16(blobs["warm_controls"]), sticky_fault=_u16(blobs["warm_controls"], 2),
                    guard_status=_u16(blobs["warm_controls"], 4), alias_fault=_u16(blobs["warm_controls"], 6),
                    committed_count=_u32(blobs["work"], 8),
                    world_time=_u32(blobs["world_time"]),
                    raw_input1=_u16(blobs["raw_input1"]), raw_input2=_u16(blobs["raw_input2"]),
                    mapped_input_hex=blobs["mapped_input_hex"].hex(),
                    raw_joy1=_u16(blobs["actual_joy"]), raw_joy2=_u16(blobs["actual_joy"], 2),
                    actual_mcp_input_mask=None)
                audio_row = dict(frame=frame, master_clock=master_clock,
                    transport=blobs["transport"].hex(),
                    chunks_accepted=_u16(blobs["chunks_accepted"]),
                    control=blobs["audio_control"].hex(), channel11=blobs["channel11"].hex(),
                    compact11=blobs["compact11"].hex(), source_status=_u16(blobs["source_status"]))
                if resolved["audio_enabled"]:
                    decoded["audio_progress"] = audio_row
                rows_by_frame[frame] = decoded
            except (ValueError, IndexError) as exc:
                malformed.append(dict(line=line, error=str(exc)))
        if "WARMARMPACKET|" in line:
            try:
                chunk_s, frame_s, packet_hex = line.split("WARMARMPACKET|", 1)[1].split("|", 2)
                chunk, frame = int(chunk_s), int(frame_s)
                if chunk < 0 or not 0 <= frame <= 0x7FFFFFFF:
                    raise ValueError("PACKET_DOMAIN")
                if not re.fullmatch(r"[0-9a-f]{288}", packet_hex):
                    raise ValueError("PACKET_HEX_LENGTH")
                if packets and chunk != packets[-1]["chunk"] + 1:
                    raise ValueError("PACKET_SEQUENCE")
                actual = bytes.fromhex(packet_hex)
                packet = dict(chunk=chunk, frame=frame, aram=resolved["ring_address"] + (chunk % 8) * 144,
                              actual_hex=packet_hex, actual_sha256=_digest(actual),
                              mismatched_bytes=None, expected_sha256=None)
                if expected_payload is not None:
                    total_chunks = (len(expected_payload) + 143) // 144
                    if chunk >= total_chunks:
                        raise ValueError("PACKET_OUTSIDE_EXPECTED_PAYLOAD")
                    expected_packet = bytearray(expected_payload[chunk * 144:(chunk + 1) * 144].ljust(144, b"\0"))
                    if chunk % 8 == 7 and chunk + 1 < total_chunks:
                        expected_packet[135] |= 3
                    packet.update(mismatched_bytes=sum(a != b for a, b in zip(actual, expected_packet)),
                                  expected_sha256=_digest(expected_packet))
                packets.append(packet)
            except (ValueError, IndexError, TypeError) as exc:
                malformed.append(dict(line=line, error=str(exc)))
    if malformed:
        raise ValueError("WARM_FIELD_MALFORMED:" + repr(malformed[:3]))
    actual_frames = list(rows_by_frame)
    if actual_frames != expected:
        raise ValueError("WARM_FIELD_FRAME_SET:" + repr(dict(expected=expected, actual=actual_frames)))
    accepted_by_frame = ({frame: row["audio_progress"]["chunks_accepted"]
                          for frame, row in rows_by_frame.items()}
                         if resolved["audio_enabled"] else {})
    progress = []
    audio_progress = []
    for index, frame in enumerate(expected):
        row = rows_by_frame[frame]
        row["index"] = index
        audio = row.pop("audio_progress", None)
        progress.append(row)
        if audio is not None:
            audio["index"] = index
            audio_progress.append(audio)
    for packet in packets:
        if not resolved["audio_enabled"]:
            raise ValueError("WARM_FIELD_PACKET_WITHOUT_AUDIO_CONTRACT")
        if packet["frame"] not in rows_by_frame:
            raise ValueError("WARM_FIELD_PACKET_FRAME:" + str(packet["frame"]))
        packet["field"] = rows_by_frame[packet["frame"]]["index"]
        accepted = accepted_by_frame[packet["frame"]]
        if packet["chunk"] >= accepted:
            raise ValueError("WARM_FIELD_PACKET_NOT_ACCEPTED:" + str(packet["chunk"]))
    if resolved["audio_enabled"]:
        previous = 0
        packets_by_frame = {}
        for packet in packets:
            packets_by_frame.setdefault(packet["frame"], []).append(packet["chunk"])
        for frame in expected:
            accepted = accepted_by_frame[frame]
            delta = accepted - previous
            if delta < 0 or delta > 8:
                raise ValueError("WARM_FIELD_AUDIO_DELTA:" + repr((frame, previous, accepted)))
            if accepted > resolved["max_payload_chunks"]:
                raise ValueError("WARM_FIELD_AUDIO_PAYLOAD_OVERRUN:" + str(accepted))
            wanted = list(range(previous, accepted))
            if packets_by_frame.get(frame, []) != wanted:
                raise ValueError("WARM_FIELD_PACKET_COVERAGE:" + repr((frame, wanted, packets_by_frame.get(frame, []))))
            previous = accepted
    return dict(schema="WARM_FIELD_STATE_V1", progress=progress,
                audio_progress=audio_progress, packets=packets,
                audio_packet_mismatches=sum(p["mismatched_bytes"] or 0 for p in packets),
                audio_faults=faults, malformed_events=malformed,
                exact_expected_frames=True,
                packet_payload_verified=expected_payload is not None)
