import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from warm_field_state import decode, observer, schema


def contract(audio=True, payload_bytes=288):
    symbols = {
        "SourceClock4086_Ready": 0x7FFA00,
        "SourceClock4086_TimeLo": 0x7FFA08,
        "SourceClock4086_Due": 0x7FFA10,
        "SourceWorldTick4086_Ready": 0x7FFA80,
        "SourceWorldTick4086_TimeLo": 0x7FFA88,
        "SourceWorldTick4086_State": 0x7FFA84,
        "SourceWorldTick4086_Phase": 0x7FFA8C,
        "SourceWorldTick4086_Pending": 0x7FFA90,
        "SourceWorldTick4086_Fault": 0x7FFA92,
        "SourceInputController_Raw1": 0x7FF8F4,
        "SourceInputController_Raw2": 0x7FF8F6,
        "VmSourceInput_Data": 0x7FF8C8,
        "TadPrivate_stream_frame": 0x7E7700,
        "TadPrivate_stream_chunks_accepted": 0x7E7710,
        "SourceAudio_Status": 0x7E8102,
        "VmSourceWorld_Time": 0x7E72E0,
        "TAD_STREAM_RING_ADDR": 0x0200,
    }
    return dict(symbols=symbols,
                audio=dict(payload_bytes=payload_bytes) if audio else None)


def frame_line(frame, accepted=0, salt=0):
    sch = schema(contract())
    packed = bytearray()
    for r in sch["ranges"]:
        data = bytes(((salt + r["address"] + i) & 0xFF) for i in range(r["length"]))
        if r["name"] == "chunks_accepted":
            data = accepted.to_bytes(2, "little")
        elif r["name"] == "constructor_ready_word":
            data = (0xB4B8).to_bytes(2, "little")
        packed.extend(data)
    # Owner scalar fields are decoded from the real owner rows, not inferred.
    clock = next(r for r in sch["ranges"] if r["name"] == "clock")
    clock_offset = 0x7FFA08 - clock["address"]
    packed[sum(r["length"] for r in sch["ranges"][:sch["ranges"].index(clock)]) + clock_offset:
           sum(r["length"] for r in sch["ranges"][:sch["ranges"].index(clock)]) + clock_offset + 4] = (0x12345678).to_bytes(4, "little")
    return f"WARMFIELDDATA|{frame}|{100000 + frame}|{packed.hex()}"


class WarmFieldStateTests(unittest.TestCase):
    def test_schema_is_fixed_order_and_adds_only_explicit_external_fields(self):
        result = schema(contract())
        names = [r["name"] for r in result["ranges"]]
        self.assertEqual(names[:6], ["actor_hex", "side_hex", "latest_hex",
                                     "render_pin_hex", "display_pin_hex", "cold_pin_hex"])
        self.assertEqual(names[19:22], ["actual_joy", "world_time", "constructor_ready_word"])
        self.assertEqual([r['length'] for r in result['ranges'][2:6]], [148,148,148,146])
        self.assertEqual(result["ring_address"], 0x0200)
        self.assertEqual(result["max_payload_chunks"], 2)
        fields = {f["name"]: f for f in result["fields"]}
        self.assertEqual((fields["source_time"]["range"], fields["source_time"]["offset"]),
                         ("clock", 8))
        self.assertEqual(fields["phase"]["offset"], 12)

    def test_observer_is_read_only_fixed_format_and_uses_spc_ram_enum(self):
        lua, meta = observer(contract())
        self.assertIn("emu.eventType.endFrame", lua)
        self.assertIn("word(0x7ffb88)~=0xb6d0", lua)
        self.assertIn("WARMFIELDDATA|", lua)
        self.assertIn("WARMARMPACKET|", lua)
        self.assertIn("emu.memType.spcRam", lua)
        self.assertIn("warmFieldHex(address,144,warmFieldSpc)", lua)
        self.assertIn("delta>8", lua)
        self.assertNotIn("emu.write", lua)
        self.assertEqual(meta["existing_host_reader_enum"], "SpcRam")

    def test_roundtrip_progress_scalars_and_zero_offset_packet_mapping(self):
        payload = bytes((i * 3) & 0xFF for i in range(288))
        logs = [frame_line(500, accepted=2),
                f"WARMARMPACKET|0|500|{payload[:144].hex()}",
                f"WARMARMPACKET|1|500|{payload[144:].hex()}"]
        result = decode("\n".join(logs), [500], contract(), payload)
        row = result["progress"][0]
        self.assertEqual(row["source_time"], 0x12345678)
        self.assertEqual(row['latest_epoch'], int.from_bytes(bytes.fromhex(row['latest_hex'])[144:148],'little'))
        self.assertGreater(row['latest_epoch'], 65535)
        self.assertEqual(row["constructor_ready_word"], 0xB4B8)
        self.assertEqual(row["raw_joy1"], int.from_bytes(bytes.fromhex(row["ranges_hex"]["actual_joy"][:4]), "little"))
        self.assertEqual(result["packets"][0]["chunk"], 0)
        self.assertEqual(result["packets"][0]["aram"], 0x0200)
        self.assertEqual([p["mismatched_bytes"] for p in result["packets"]], [0, 0])
        self.assertTrue(result["packet_payload_verified"])

    def test_slot_seven_nonfinal_header_mutation_is_checked(self):
        payload = bytes((i + 7) & 0xFF for i in range(9 * 144))
        # Exact observer behavior requires logging all newly accepted chunks.
        logs = [frame_line(77, accepted=8)]
        for chunk in range(8):
            packet = bytearray(payload[chunk * 144:(chunk + 1) * 144])
            if chunk == 7:
                packet[135] |= 3
            logs.append(f"WARMARMPACKET|{chunk}|77|{packet.hex()}")
        result = decode("\n".join(logs), [77], contract(payload_bytes=9 * 144), payload)
        self.assertEqual(result["packets"][7]["mismatched_bytes"], 0)
        self.assertEqual(result["packets"][7]["aram"], 0x0200 + 7 * 144)

    def test_rejects_missing_duplicate_and_unexpected_frames(self):
        first = frame_line(10)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_EXPECTED"):
            decode(first, [10, 10], contract())
        with self.assertRaisesRegex(ValueError, "FRAME_SET"):
            decode(first, [10, 11], contract())
        with self.assertRaisesRegex(ValueError, "MALFORMED"):
            decode(first + "\n" + first, [10], contract())
        with self.assertRaisesRegex(ValueError, "FRAME_SET"):
            decode(first + "\n" + frame_line(12), [10, 11], contract())

    def test_no_audio_contract_returns_no_audio_progress(self):
        result = decode(frame_line(31), [31], contract(audio=False))
        self.assertEqual(result["audio_progress"], [])
        self.assertEqual(result["packets"], [])

    def test_rejects_packet_gap_bad_audio_delta_and_external_symbol_range(self):
        payload = bytes(288)
        logs = [frame_line(20, accepted=2), f"WARMARMPACKET|1|20|{payload[144:].hex()}"]
        with self.assertRaisesRegex(ValueError, "PACKET_SEQUENCE|PACKET_COVERAGE"):
            decode("\n".join(logs), [20], contract(), payload)
        bad_delta = [frame_line(20, accepted=9)]
        with self.assertRaisesRegex(ValueError, "AUDIO_DELTA"):
            decode("\n".join(bad_delta), [20], contract(payload_bytes=9 * 144), bytes(9 * 144))
        bad = contract()
        bad["symbols"]["SourceClock4086_Due"] = 0x7FFAFF
        schema_result = schema(bad)
        self.assertTrue(any(r["name"] == "due_bytes" and r["address"] == 0x7FFAFF
                            for r in schema_result["ranges"]))


if __name__ == "__main__":
    unittest.main()
