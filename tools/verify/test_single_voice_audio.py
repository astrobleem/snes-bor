"""Tests for the source-C single-active audio compiler."""
from __future__ import annotations

import io
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
import source_single_voice_audio as audio


def wav_bytes(samples: bytes, *, width: int = 1, rate: int = 22050, channels: int = 1) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(samples)
    return out.getvalue()


class SingleVoiceAudioTests(unittest.TestCase):
    def test_original_phase_and_rate_mapping(self):
        # Entry.wav's original cache rate is 22050; source channel 11 starts
        # at frame 44. The mixed stream is already phase-baked before 4:1
        # resampling, so prepared frame zero remains the original frame 44.
        frames = 272007
        phase = audio.source_channel_phase(11, frames)
        self.assertEqual(phase, 44 << 12)
        self.assertEqual(audio.source_q12_period(22050), 2048)
        self.assertEqual(audio.source_phase_time(phase, 22050), 44 / 22050)
        self.assertEqual(audio.source_frames_to_mix_frames(frames, phase, 2048), 543928)

    def test_resampler_keeps_pcm16_constant_and_duration(self):
        output = audio.resample_44100_to_11025([1234] * 404)
        self.assertEqual(len(output), 101)
        self.assertEqual(output, [1234] * 101)

    def test_resampler_preserves_passband_and_rejects_alias_energy(self):
        count = 44100
        passband = [round(12000 * math.sin(2 * math.pi * 1000 * i / 44100)) for i in range(count)]
        pass_out = audio.resample_44100_to_11025(passband)
        target = [12000 * math.sin(2 * math.pi * 1000 * i / 11025) for i in range(len(pass_out))]
        error_rms = math.sqrt(sum((a - b) ** 2 for a, b in zip(pass_out[32:-32], target[32:-32])) / (len(pass_out) - 64))
        self.assertLess(error_rms, 100)
        stopband = [round(12000 * math.sin(2 * math.pi * 12000 * i / 44100)) for i in range(count)]
        stop_out = audio.resample_44100_to_11025(stopband)
        rms = math.sqrt(sum(v * v for v in stop_out[32:-32]) / (len(stop_out) - 64))
        self.assertLess(rms, 100)

    def test_rejects_unsupported_wav_domains(self):
        with self.assertRaisesRegex(ValueError, "MONO_REQUIRED"):
            audio.parse_pcm_wav(wav_bytes(bytes(100 * 2), channels=2))
        with self.assertRaisesRegex(ValueError, "PCM8_OR_PCM16_REQUIRED"):
            audio.parse_pcm_wav(wav_bytes(bytes(100 * 3), width=3))
        with self.assertRaisesRegex(ValueError, "FRAME_DOMAIN"):
            audio.parse_pcm_wav(wav_bytes(b""))
        with self.assertRaisesRegex(ValueError, "SOURCE_CHANNEL_INDEX"):
            audio.source_channel_phase(12, 272007)

    def test_accepts_source_signed_pcm16_metadata(self):
        parsed = audio.parse_pcm_wav(wav_bytes(((-1234).to_bytes(2, "little", signed=True) * 64), width=2, rate=32000))
        self.assertEqual((parsed["bits"], parsed["sample_rate_hz"], parsed["frames"]), (16, 32000, 64))
        self.assertEqual(parsed["pcm"][:2], (-1234).to_bytes(2, "little", signed=True))

    @unittest.skipUnless(
        (ROOT / "out/byor-motu-live-world-v1/pinned-soundmix.c").is_file()
        and (ROOT / "out/byor-motu-update-frame-authority/update_frame.c").is_file()
        and (os.environ.get("WCL386") or os.environ.get("WATCOM") or shutil.which("wcl386.exe")),
        "pinned C text or Watcom compiler unavailable",
    )
    def test_pinned_c_selects_channel11_and_finishes_from_phase44(self):
        soundmix = (ROOT / "out/byor-motu-live-world-v1/pinned-soundmix.c").read_text(encoding="latin1")
        openbor = (ROOT / "out/byor-motu-update-frame-authority/update_frame.c").read_text(encoding="latin1")
        authority = audio.extract_authority_text(soundmix, openbor)
        self.assertEqual(authority["commit"], audio.ENGINE_COMMIT)
        self.assertTrue(any(c["arguments"][1].strip() == "0" for c in authority["calls"]))
        # Exercise the actual pinned functions on a small original-rate WAV.
        raw = wav_bytes(bytes((128 + ((i * 19) % 101 - 50)) & 255 for i in range(257)))
        info = audio.parse_pcm_wav(raw)
        with tempfile.TemporaryDirectory() as tmp:
            result = audio._run_mixer(authority, info, Path(tmp), engine=ROOT, wcl=None, effect_volume=100)
        self.assertEqual(result["selected_channel"], 11)
        self.assertEqual(result["play_id"], 1)
        self.assertEqual(result["initial_channel_fields"]["phase_q12"], 44 << 12)
        self.assertEqual(result["initial_channel_fields"]["period_q12"], 2048)
        self.assertEqual(result["initial_channel_fields"]["left"], 64)
        self.assertEqual(result["initial_channel_fields"]["right"], 64)
        self.assertEqual(result["final_channel_fields"]["active"], 0)
        self.assertEqual(len(result["mono_signed_pcm16"]), result["mixed_frames_44100"])


if __name__ == "__main__":
    unittest.main()
