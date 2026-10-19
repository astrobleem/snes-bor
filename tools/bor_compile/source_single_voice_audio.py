"""Build one source-faithful, single-active sound stream from a source WAV.

The pinned OpenBOR C routines select and mix the original-rate sample first.
Only the completed mono PCM16 mix is then resampled to the TAD 11025 Hz stream
rate and encoded as BRR. The input WAV is read in memory and never copied.
This is an offline asset compiler, not a runtime channel backend.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "bor_compile")]
from dialect_4086 import ENGINE_COMMIT  # noqa: E402
from script_nested_authority import extract  # noqa: E402

SOUND_CHANNELS = 12
SOURCE_PLAY_FREQUENCY = 44100
STREAM_RATE = 11025
SOURCE_SPEED = 100
SOURCE_PRIORITY = 0
MAX_SOURCE_FRAMES = 1_000_000
BRR_SEGMENT_SAMPLES = 65520
PINNED_SOUNDMIX_SHA256 = "362a92f4f69b9e50bde1bed25720afeb048eea75c883e9c9f8803baac2789617"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_pcm_wav(raw: bytes) -> dict:
    """Validate the exact PCM domain supported by the source C mixer."""
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("SOURCE_WAV_EMPTY")
    try:
        with wave.open(io.BytesIO(raw), "rb") as wav:
            if wav.getcomptype() != "NONE":
                raise ValueError("SOURCE_WAV_COMPRESSION")
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            rate = wav.getframerate()
            frames = wav.getnframes()
            if channels != 1:
                raise ValueError("SOURCE_WAV_MONO_REQUIRED")
            if width not in (1, 2):
                raise ValueError("SOURCE_WAV_PCM8_OR_PCM16_REQUIRED")
            if not 1 <= rate <= 192000:
                raise ValueError("SOURCE_WAV_RATE_DOMAIN")
            if not 1 <= frames <= MAX_SOURCE_FRAMES:
                raise ValueError("SOURCE_WAV_FRAME_DOMAIN")
            pcm = wav.readframes(frames)
    except wave.Error as error:
        raise ValueError("SOURCE_WAV_INVALID") from error
    if len(pcm) != frames * width:
        raise ValueError("SOURCE_WAV_TRUNCATED_PCM")
    return {
        "channels": channels,
        "sample_width_bytes": width,
        "bits": width * 8,
        "sample_rate_hz": rate,
        "frames": frames,
        "pcm": pcm,
    }


def source_channel_phase(channel: int, sample_frames: int) -> int:
    if not 0 <= channel < SOUND_CHANNELS:
        raise ValueError("SOURCE_CHANNEL_INDEX")
    if sample_frames <= 0:
        raise ValueError("SOURCE_SAMPLE_LENGTH")
    return ((channel * 4) % sample_frames) << 12


def source_q12_period(sample_rate: int, speed: int = SOURCE_SPEED,
                      play_frequency: int = SOURCE_PLAY_FREQUENCY) -> int:
    """Evaluate the pinned unsigned 32-bit C expression, including truncation."""
    if not 0 < sample_rate <= 0xFFFFFFFF:
        raise ValueError("SOURCE_SAMPLE_RATE")
    if not 1 <= speed <= 0xFFFFFFFF or not 0 < play_frequency <= 0xFFFFFFFF:
        raise ValueError("SOURCE_PERIOD_DOMAIN")
    value = (4096 * speed) & 0xFFFFFFFF
    value = value // 100
    value = (value * sample_rate) & 0xFFFFFFFF
    value //= play_frequency
    return value


def source_phase_time(phase_q12: int, sample_rate: int) -> float:
    if phase_q12 < 0 or sample_rate <= 0:
        raise ValueError("SOURCE_PHASE_TIME_DOMAIN")
    return (phase_q12 >> 12) / sample_rate


def source_frames_to_mix_frames(sample_frames: int, phase_q12: int,
                                period_q12: int) -> int:
    if sample_frames <= 0 or phase_q12 < 0 or period_q12 <= 0:
        raise ValueError("SOURCE_MIX_FRAME_DOMAIN")
    remaining = (sample_frames << 12) - phase_q12
    if remaining <= 0:
        raise ValueError("SOURCE_PHASE_OUTSIDE_SAMPLE")
    # A small guard covers the pinned mixer's increment-before-stop boundary.
    return (remaining + period_q12 - 1) // period_q12 + 2


def resample_44100_to_11025(samples: list[int] | tuple[int, ...]) -> list[int]:
    """Polyphase-equivalent 4:1 low-pass decimation of signed PCM16.

    A symmetric 127-tap Kaiser-windowed sinc keeps the source-time origin at
    output frame zero (linear phase is centered before decimation). This acts
    on the already mixed PCM16 waveform, never on the original source asset.
    """
    if not samples:
        raise ValueError("RESAMPLE_EMPTY")
    if any(not -32768 <= int(value) <= 32767 for value in samples):
        raise ValueError("RESAMPLE_PCM16_DOMAIN")
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("NUMPY_REQUIRED_FOR_44100_TO_11025_RESAMPLE") from error
    source = np.asarray(samples, dtype=np.float64)
    taps_count = 127
    center = (taps_count - 1) / 2
    offsets = np.arange(taps_count, dtype=np.float64) - center
    # 11025 Hz Nyquist is one eighth of the 44100 Hz input rate.
    taps = 0.25 * np.sinc(0.25 * offsets) * np.kaiser(taps_count, 8.6)
    taps /= taps.sum()
    pad = taps_count // 2
    padded = np.pad(source, (pad, pad), mode="reflect" if len(source) > 1 else "edge")
    filtered = np.convolve(padded, taps, mode="valid")
    target_count = (len(source) + 3) // 4
    out = np.rint(filtered[::4][:target_count])
    out = np.clip(out, -32768, 32767).astype(np.int16)
    return out.tolist()


def _pinned_file(engine: Path, commit: str, path: str) -> str:
    command = ["git", "-C", str(engine), "show", f"{commit}:{path}"]
    result = subprocess.run(command, capture_output=True, check=True)
    return result.stdout.decode("latin1")


def extract_authority(engine: Path, commit: str = ENGINE_COMMIT) -> dict:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise ValueError("ENGINE_COMMIT_SHA1_REQUIRED")
    soundmix = _pinned_file(engine, commit, "engine/source/gamelib/soundmix.c")
    openbor = _pinned_file(engine, commit, "engine/openbor.c")
    return extract_authority_text(soundmix, openbor, commit)


def extract_authority_text(soundmix: str, openbor: str, commit: str = ENGINE_COMMIT) -> dict:
    """Extract from caller-pinned source text when Git access is unavailable."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        raise ValueError("ENGINE_COMMIT_SHA1_REQUIRED")
    soundmix_sha = sha256(soundmix.encode("latin1"))
    if commit.lower() == ENGINE_COMMIT and soundmix_sha != PINNED_SOUNDMIX_SHA256:
        raise ValueError("PINNED_SOUNDMIX_SHA256_MISMATCH")
    function_names = ("clearmixbuffer", "mixaudio", "update_sample", "sound_play_sample")
    bodies = {name: extract(soundmix, name) for name in function_names}
    calls = _sound_play_calls(openbor)
    source_call_matches = [
        call for call in calls
        if len(call["arguments"]) == 5
        and call["arguments"][1].strip() == "0"
        and call["arguments"][4].strip() == "100"
        and re.sub(r"\s", "", call["arguments"][2]) == "savedata.effectvol"
        and re.sub(r"\s", "", call["arguments"][2])
        == re.sub(r"\s", "", call["arguments"][3])
    ]
    if not source_call_matches:
        raise ValueError("PINNED_FRAME_SOUND_CALL_NOT_FOUND")
    typedef_start = soundmix.index("typedef struct")
    typedef_end = soundmix.index("} musicchannelstruct;") + len("} musicchannelstruct;")
    typedefs = soundmix[typedef_start:typedef_end]
    macro_names = (
        "MIXSHIFT", "MAXVOLUME", "MAX_CHANNELS", "INT_TO_FIX", "FIX_TO_INT",
        "CHANNEL_PLAYING", "CHANNEL_LOOPING", "MUSIC_NUM_BUFFERS", "SOUND_MONO",
    )
    macros = []
    for name in macro_names:
        found = re.search(r"^#define\s+" + re.escape(name) + r"[^\n]*", soundmix, re.M)
        if not found:
            raise ValueError("PINNED_SOUND_MIXER_MACRO_MISSING:" + name)
        macros.append(found.group(0))
    return {
        "commit": commit.lower(),
        "soundmix_sha256": soundmix_sha,
        "openbor_input_sha256": sha256(openbor.encode("latin1")),
        "functions": bodies,
        "function_sha256": {name: sha256(body.encode("latin1")) for name, body in bodies.items()},
        "calls": calls,
        "typedefs": typedefs,
        "macros": "\n".join(macros),
    }


def _sound_play_calls(source: str) -> list[dict]:
    text = re.sub(r"/\*.*?\*/|//[^\n]*", lambda m: "".join("\n" if c == "\n" else " " for c in m[0]), source, flags=re.S)
    result = []
    for match in re.finditer(r"\bsound_play_sample\s*\(", text):
        pos = match.end()
        depth = 1
        start = pos
        args = []
        while pos < len(text) and depth:
            ch = text[pos]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    args.append(text[start:pos].strip())
                    break
            elif ch == "," and depth == 1:
                args.append(text[start:pos].strip())
                start = pos + 1
            pos += 1
        if depth or len(args) != 5:
            raise ValueError("PINNED_SOUND_CALL_PARSE")
        result.append({"line": source.count("\n", 0, match.start()) + 1, "arguments": args})
    return result


def _wcl_path(explicit: Path | None) -> Path:
    if explicit:
        return explicit
    configured = os.environ.get("WCL386")
    if configured:
        return Path(configured)
    watcom = os.environ.get("WATCOM")
    if watcom:
        candidates = (Path(watcom) / "BINNT" / "wcl386.exe", Path(watcom) / "binnt" / "wcl386.exe")
        for candidate in candidates:
            if candidate.exists():
                return candidate
    found = shutil.which("wcl386") or shutil.which("wcl386.exe")
    if found:
        return Path(found)
    raise FileNotFoundError("set WCL386 or WATCOM, or pass --wcl")


def _build_harness(authority: dict) -> str:
    return r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <io.h>
'''+authority["macros"]+"\n"+authority["typedefs"]+r'''
typedef signed int s32;
channelstruct vchannel[MAX_CHANNELS];
musicchannelstruct musicchannel;
s_soundcache cache[1], *soundcache=cache;
int mixing_inited=1, sound_cached=1, max_channels=12, playfrequency=44100;
int playbits=16, sample_play_id=0, reload_result=1;
unsigned samplesplayed;
s32 *mixbuf;
int sound_reload_sample(int n) { return reload_result; }
'''+"\n".join(authority["functions"].values())+r'''
int main(void) {
    int bits, rate, frames, volume, byte_count, selected, i;
    unsigned int max_mix_frames, produced=0;
    unsigned char *pcm;
    unsigned short *stereo;
    channelstruct initial;
    if (sizeof(int)!=4 || sizeof(void*)!=4 || sizeof(channelstruct)!=40) return 2;
    setmode(fileno(stdin), O_BINARY); setmode(fileno(stdout), O_BINARY);
    if (fread(&bits,4,1,stdin)!=1 || fread(&rate,4,1,stdin)!=1 ||
        fread(&frames,4,1,stdin)!=1 || fread(&volume,4,1,stdin)!=1 ||
        fread(&max_mix_frames,4,1,stdin)!=1) return 3;
    if ((bits!=8 && bits!=16) || rate<=0 || frames<=0 || max_mix_frames==0) return 4;
    byte_count=frames*(bits/8);
    pcm=(unsigned char*)malloc((unsigned)byte_count);
    stereo=(unsigned short*)malloc((unsigned long)max_mix_frames*2*sizeof(unsigned short));
    mixbuf=(s32*)calloc(2,sizeof(s32));
    if (!pcm || !stereo || !mixbuf) return 5;
    if (fread(pcm,1,byte_count,stdin)!=(unsigned)byte_count) return 6;
    memset(vchannel,0,sizeof(vchannel)); memset(&musicchannel,0,sizeof(musicchannel));
    memset(cache,0,sizeof(cache));
    cache[0].sample.sampleptr=pcm; cache[0].sample.bits=bits;
    cache[0].sample.frequency=rate; cache[0].sample.soundlen=frames;
    cache[0].sample.channels=SOUND_MONO;
    selected=sound_play_sample(0,0,volume,volume,100);
    if (selected<0 || selected>=12) return 7;
    initial=vchannel[selected];
    while (vchannel[selected].active && produced<max_mix_frames) {
        update_sample((unsigned char*)(stereo+produced*2),4);
        produced++;
    }
    if (vchannel[selected].active || produced==0) return 8;
    if (fwrite("SVCA",1,4,stdout)!=4 || fwrite(&selected,4,1,stdout)!=1 ||
        fwrite(&sample_play_id,4,1,stdout)!=1 || fwrite(&produced,4,1,stdout)!=1 ||
        fwrite(&initial,sizeof(initial),1,stdout)!=1 ||
        fwrite(&vchannel[selected],sizeof(channelstruct),1,stdout)!=1 ||
        fwrite(stereo,4,produced,stdout)!=produced) return 9;
    return 0;
}
'''


def _run_mixer(authority: dict, wav: dict, output_dir: Path, *, engine: Path,
               wcl: Path | None, effect_volume: int) -> dict:
    compiler = _wcl_path(wcl)
    if not compiler.is_file():
        raise FileNotFoundError("WCL386_NOT_FOUND:" + str(compiler))
    rate = wav["sample_rate_hz"]
    period = source_q12_period(rate)
    phase = source_channel_phase(11, wav["frames"])
    max_frames = source_frames_to_mix_frames(wav["frames"], phase, period)
    if max_frames > 16_000_000:
        raise ValueError("SOURCE_MIX_FRAME_CAP")
    output_dir.mkdir(parents=True, exist_ok=True)
    source_text = _build_harness(authority)
    c_path = output_dir / "single_voice_authority.c"
    exe_path = output_dir / "single_voice_authority.exe"
    c_path.write_text(source_text, encoding="latin1")
    env = dict(os.environ)
    watcom = env.get("WATCOM")
    if watcom:
        include = [str(Path(watcom) / "H"), str(Path(watcom) / "H" / "NT")]
        if env.get("INCLUDE"):
            include.append(env["INCLUDE"])
        env["INCLUDE"] = ";".join(include)
    command = [str(compiler), "-q", "-za99", "-bt=nt", "-op", "-fpc", str(c_path), "-fe="+str(exe_path)]
    build = subprocess.run(command, cwd=output_dir, env=env, capture_output=True, text=True)
    (output_dir / "build.log").write_text(build.stdout + build.stderr, encoding="utf-8")
    if build.returncode:
        raise RuntimeError("SOURCE_C_BUILD_FAILED:" + build.stdout + build.stderr)
    header = struct.pack("<iiiii", wav["bits"], rate, wav["frames"], effect_volume, max_frames)
    run = subprocess.run([str(exe_path)], input=header + wav["pcm"], capture_output=True, check=True)
    data = run.stdout
    if len(data) < 96 or data[:4] != b"SVCA":
        raise ValueError("SOURCE_C_OUTPUT_HEADER")
    selected, play_id, produced = struct.unpack_from("<iii", data, 4)
    initial_raw = data[16:56]
    final_raw = data[56:96]
    expected_bytes = 96 + produced * 4
    if selected != 11 or play_id != 1 or produced <= 0 or len(data) != expected_bytes:
        raise ValueError("SOURCE_C_OUTPUT_SHAPE")
    initial = struct.unpack("<10i", initial_raw)
    final = struct.unpack("<10i", final_raw)
    expected_phase = source_channel_phase(selected, wav["frames"])
    expected_period = source_q12_period(rate)
    if initial[0] != 1 or initial[1] != 0 or initial[2] != 0 or initial[3] != SOURCE_PRIORITY:
        raise ValueError("SOURCE_C_INITIAL_CHANNEL_IDENTITY")
    if initial[4] != play_id or initial[5] != min(64, effect_volume) or initial[6] != min(64, effect_volume):
        raise ValueError("SOURCE_C_INITIAL_CHANNEL_VOLUME_OR_PLAYID")
    if initial[7] != 1 or initial[8] != expected_phase or initial[9] != expected_period:
        raise ValueError("SOURCE_C_INITIAL_CHANNEL_PHASE_OR_PERIOD")
    if final[0] != 0 or final[4] != play_id:
        raise ValueError("SOURCE_C_CHANNEL_DID_NOT_FINISH")
    unsigned = struct.unpack_from("<" + "H" * produced * 2, data, 96)
    left = unsigned[0::2]
    right = unsigned[1::2]
    if left != right:
        raise ValueError("SOURCE_C_MONO_CHANNELS_DIVERGED")
    signed = [((value ^ 0x8000) - 0x10000 if (value ^ 0x8000) & 0x8000 else (value ^ 0x8000)) for value in left]
    return {
        "selected_channel": selected,
        "play_id": play_id,
        "mixed_frames_44100": produced,
        "period_q12": initial[9],
        "initial_phase_q12": initial[8],
        "initial_channel_raw": initial_raw,
        "final_channel_raw": final_raw,
        "initial_channel_fields": _channel_fields(initial),
        "final_channel_fields": _channel_fields(final),
        "mono_signed_pcm16": signed,
        "source_c_command": command,
        "source_c_sha256": sha256(source_text.encode("latin1")),
    }


def _channel_fields(row: tuple[int, ...]) -> dict:
    names = ("active", "paused", "sample", "priority", "play_id", "left", "right", "channels", "phase_q12", "period_q12")
    return dict(zip(names, row))


def _pcm16_bytes(samples: list[int]) -> bytes:
    return struct.pack("<" + "h" * len(samples), *samples)


def _mono_wav(samples: list[int], rate: int) -> bytes:
    raw = _pcm16_bytes(samples)
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(raw)
    return stream.getvalue()


def _compile_brr(samples: list[int], rate: int, *, root: Path,
                 tad_compiler: Path, tad_memmap: Path) -> tuple[bytes, list[dict], dict]:
    if not tad_compiler.is_file() or not tad_memmap.is_file():
        raise FileNotFoundError("TAD_COMPILER_OR_MEMMAP_MISSING")
    sys.path[:0] = [str(root / "tools" / "audio"), str(root / "tools" / "bor_converter")]
    import build_batch_b_audio as tad_builder
    import production_sfx
    tad_builder.COMPILER = tad_compiler
    tad_builder.COMMON_MEMMAP = tad_memmap
    padded = list(samples)
    padding = (-len(padded)) % 16
    padded.extend([0] * padding)
    result = bytearray()
    segments = []
    for start in range(0, len(padded), BRR_SEGMENT_SAMPLES):
        segment = padded[start:start + BRR_SEGMENT_SAMPLES]
        if len(segment) % 16:
            raise ValueError("BRR_SEGMENT_ALIGNMENT")
        wav_bytes = _mono_wav(segment, rate)
        _, ticks, _ = production_sfx.duration_ticks(wav_bytes, rate)
        brr, common_bytes = tad_builder.bracked_project(root, wav_bytes, rate, ticks, f"source_voice_{start // BRR_SEGMENT_SAMPLES:03d}")
        if not brr or len(brr) != len(segment) // 16 * 9:
            raise ValueError("TAD_BRR_LENGTH")
        if brr[0] & 0x0C:
            raise ValueError("TAD_BRR_FIRST_FILTER")
        if any(brr[i] & 3 for i in range(0, len(brr) - 9, 9)) or brr[-9] & 3 != 1:
            raise ValueError("TAD_BRR_END_FLAGS")
        brr_start = len(result)
        result.extend(brr)
        result[-9] &= 0xFC
        segments.append({
            "sample_offset": start,
            "samples": len(segment),
            "brr_offset": brr_start,
            "brr_bytes": len(brr),
            "first_filter": (brr[0] >> 2) & 3,
            "compiler_common_bytes": common_bytes,
        })
    if not result:
        raise ValueError("TAD_BRR_EMPTY")
    result[-9] |= 1
    if any(result[i] & 3 for i in range(0, len(result) - 9, 9)) or result[-9] & 3 != 1:
        raise ValueError("TAD_BRR_FINAL_CHAIN")
    return bytes(result), segments, {"padding_samples": padding, "compiler": str(tad_compiler), "memmap": str(tad_memmap)}


def compile_wav(raw: bytes, *, engine: Path, output: Path,
                wcl: Path | None = None, tad_compiler: Path | None = None,
                tad_memmap: Path | None = None, commit: str = ENGINE_COMMIT,
                pinned_soundmix: Path | None = None, pinned_openbor: Path | None = None,
                source_path: str = "input.wav", sample_index: int = 0,
                effect_volume: int = 100) -> dict:
    if sample_index < 0:
        raise ValueError("SOURCE_SAMPLE_INDEX")
    if not 0 <= effect_volume <= 100:
        raise ValueError("SOURCE_EFFECT_VOLUME")
    info = parse_pcm_wav(raw)
    period = source_q12_period(info["sample_rate_hz"])
    if period == 0:
        raise ValueError("SOURCE_PERIOD_ZERO")
    if pinned_soundmix:
        soundmix_text = pinned_soundmix.read_text(encoding="latin1")
        openbor_text = pinned_openbor.read_text(encoding="latin1") if pinned_openbor else _pinned_file(engine, commit, "engine/openbor.c")
        authority = extract_authority_text(soundmix_text, openbor_text, commit)
    else:
        authority = extract_authority(engine, commit)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    mixed = _run_mixer(authority, info, output, engine=engine, wcl=wcl, effect_volume=effect_volume)
    stereo = []
    for value in mixed["mono_signed_pcm16"]:
        stereo.extend((value, value))
    stereo_raw = _pcm16_bytes(stereo)
    mono_stream = resample_44100_to_11025(mixed["mono_signed_pcm16"])
    mono_raw = _pcm16_bytes(mono_stream)
    tad_compiler = tad_compiler or (Path(os.environ["TAD_COMPILER"]) if os.environ.get("TAD_COMPILER") else None)
    tad_memmap = tad_memmap or (Path(os.environ["TAD_MEMMAP"]) if os.environ.get("TAD_MEMMAP") else None)
    if tad_compiler is None or tad_memmap is None:
        raise FileNotFoundError("set TAD_COMPILER and TAD_MEMMAP or pass CLI options")
    brr, segments, tad = _compile_brr(mono_stream, STREAM_RATE, root=ROOT,
                                      tad_compiler=tad_compiler, tad_memmap=tad_memmap)
    (output / "mixed-stereo16-44100.pcm").write_bytes(stereo_raw)
    (output / "mixed-mono16-11025.pcm").write_bytes(mono_raw)
    (output / "prepared.brr").write_bytes(brr)
    raw_phase = mixed["initial_channel_fields"]["phase_q12"]
    physical_source_offset = raw_phase >> 12
    report = {
        "schema": "BYOR_SINGLE_VOICE_SOURCE_AUDIO_V1",
        "status": "PASS",
        "engine_commit": authority["commit"],
        "pinned_source_inputs": {"soundmix_bytes_sha256": authority["soundmix_sha256"],
                                 "openbor_callsite_text_sha256": authority["openbor_input_sha256"],
                                 "soundmix_input": str(pinned_soundmix) if pinned_soundmix else "git show <commit>:engine/source/gamelib/soundmix.c",
                                 "openbor_input": str(pinned_openbor) if pinned_openbor else "git show <commit>:engine/openbor.c"},
        "function_sha256": authority["function_sha256"],
        "frame_sound_call_candidates": authority["calls"],
        "source_identity": {"source_path": source_path, "sample_index": sample_index, "source_wav_sha256": sha256(raw)},
        "original_cache_metadata": {k: info[k] for k in ("channels", "sample_width_bytes", "bits", "sample_rate_hz", "frames")},
        "source_call": {"priority": SOURCE_PRIORITY, "raw_left_volume": effect_volume, "raw_right_volume": effect_volume,
                        "clamped_left_volume": min(64, effect_volume), "clamped_right_volume": min(64, effect_volume), "speed": SOURCE_SPEED},
        "source_channel": {"selected": mixed["selected_channel"], "play_id": mixed["play_id"],
                           "initial": mixed["initial_channel_fields"], "initial_raw_40b_hex": mixed["initial_channel_raw"].hex(),
                           "final": mixed["final_channel_fields"], "final_raw_40b_hex": mixed["final_channel_raw"].hex(),
                           "logical_phase_q12": raw_phase, "logical_phase_source_frames": physical_source_offset,
                           "source_phase_time_seconds": source_phase_time(raw_phase, info["sample_rate_hz"]),
                           "source_period_q12": mixed["period_q12"], "mix_output_rate_hz": SOURCE_PLAY_FREQUENCY},
        "mixed_pcm": {"stereo16_rate_hz": SOURCE_PLAY_FREQUENCY, "frames": mixed["mixed_frames_44100"],
                      "bytes": len(stereo_raw), "sha256": sha256(stereo_raw), "mono_sides_equal": True,
                      "mono11025_pcm16_frames": len(mono_stream), "mono11025_bytes": len(mono_raw), "mono11025_sha256": sha256(mono_raw)},
        "phase_time_mapping": {"prepared_stream_rate_hz": STREAM_RATE, "prepared_stream_frame_zero_is_source_frame": physical_source_offset,
                                "prepared_stream_frame_zero_source_time_seconds": source_phase_time(raw_phase, info["sample_rate_hz"]),
                                "phase_is_baked_into_full_mixed_waveform": True,
                                "leading_44_normalized_frame_trim_applied": False,
                                "resampler": "127-tap Kaiser-windowed sinc, 4:1, centered; processes mixed signed PCM16"},
        "prepared_brr": {"bytes": len(brr), "sha256": sha256(brr), "blocks": len(brr) // 9,
                         "samples_including_padding": sum(x["samples"] for x in segments), "segments": segments, "tad": tad},
        "build": {"source_c_command": mixed["source_c_command"], "source_c_sha256": mixed["source_c_sha256"],
                  "used_pinned_C_bodies": True, "original_wav_written": False, "runtime_binding_installed": False},
        "scope": "offline single-active sound authority/asset; no actor dispatch, source ticket Ack, native runtime, or polyphony claim",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _resolve_wav(args) -> tuple[bytes, str]:
    if args.wav:
        return args.wav.read_bytes(), args.asset or args.wav.name
    if not args.source or not args.asset:
        raise ValueError("SOURCE_PAK_AND_ASSET_REQUIRED")
    sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools" / "bor_converter"), str(ROOT / "tools" / "bg_converter"), str(ROOT / "tools" / "bor_compile")]
    from compiler import Source
    return Source(args.source).read(args.asset), args.asset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--engine-commit", default=ENGINE_COMMIT)
    parser.add_argument("--pinned-soundmix", type=Path, help="read-only exact source file already pinned to --engine-commit")
    parser.add_argument("--pinned-openbor", type=Path, help="optional read-only exact OpenBOR call-site source file")
    parser.add_argument("--source", type=Path, help="source PAK/directory; bytes are read in memory")
    parser.add_argument("--asset", help="normalized PAK path when using --source")
    parser.add_argument("--wav", type=Path, help="direct input WAV; never copied into output")
    parser.add_argument("--sample-index", type=int, default=0)
    parser.add_argument("--effect-volume", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wcl", type=Path)
    parser.add_argument("--tad-compiler", type=Path)
    parser.add_argument("--tad-memmap", type=Path)
    args = parser.parse_args()
    raw, label = _resolve_wav(args)
    report = compile_wav(raw, engine=args.engine, output=args.output, wcl=args.wcl,
                         tad_compiler=args.tad_compiler, tad_memmap=args.tad_memmap,
                         commit=args.engine_commit, pinned_soundmix=args.pinned_soundmix,
                         pinned_openbor=args.pinned_openbor, source_path=label,
                         sample_index=args.sample_index, effect_volume=args.effect_volume)
    print(json.dumps({"status": report["status"], "source": report["source_identity"],
                      "selected": report["source_channel"]["selected"], "phase": report["source_channel"]["logical_phase_q12"],
                      "mix_frames": report["mixed_pcm"]["frames"], "brr_bytes": report["prepared_brr"]["bytes"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
