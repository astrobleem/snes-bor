#!/usr/bin/env python3
"""plan.md Part Two, section 2.5, Phase 7 gate: TAD audio actually plays.

Phase 7's own step-1 gate is prose: "confirm there is real audio content ...
and that a song actually plays". This script makes that mechanical.

Two traps shaped these assertions, and both are the reason the checks below
compare against ground truth rather than against the engine's own opinion:

  1. TAD reported PLAYING ($82) with the S-DSP out of reset and full main
     volume while emitting pure silence, because LoadAudioData resolved the
     data table into the zero padding ahead of `.org $8C00` instead of into
     the audio blob. Every engine-visible status byte looked perfect. So
     `check 3` byte-compares the memory the loader was actually pointed at
     against soundwork/tad/build/audio-data.bin.

  2. This harness has a documented ~40% false-silent rate on the audio
     check (memory: mesen_audio_check_nondeterministic), so the waveform
     assertion is majority-of-3, per plan.md 2.5's explicit warning. The
     tell for REAL silence is a byte-identical sha256 across runs; genuine
     playback differs run to run.

Usage: python tools/verify/phase7.py
"""
import os
import re
import struct
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, read_block,  # noqa: E402
                      repo_root_from, Reporter)

ROOT = repo_root_from(None)
AUDIO_BIN = os.path.join(ROOT, 'soundwork', 'tad', 'build', 'audio-data.bin')

TAD_STATE = pasm_constant('TadPrivate_state')
TAD_ADDR = pasm_constant('TadPrivate_dataToTransfer_addr')
TAD_SIZE = pasm_constant('TadPrivate_dataToTransfer_size')
PLAYING = pasm_constant('PLAYING')

TAD_BLOCK = 0x7E0030          # Tad_flags .. the transfer queue, one read


def blob_base():
    """(bank, address) of __Tad_AudioData_0 from Poppy's symbol table.

    Was bank-0-only (returned just the 16-bit address, and callers assumed
    bank $00) back when the audio blob was `.incbin`'d mid-bank-0 -- that
    assumption broke silently when the blob moved to a `.bank 1` boundary
    on 2026-08-19 (Poppy's cross-bank jsl/label bug that justified bank-0
    confinement turned out to be fixed; see CLAUDE.md's Architecture section
    and poppy_assembler_bugs.md bug 9's correction note). Read the real bank
    from the .sym file instead of assuming $00.
    """
    sym = os.path.join(ROOT, 'src', 'main.sym')
    with open(sym, encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            m = re.match(r'\s*([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)', line)
            if m and m.group(3) == '__Tad_AudioData_0':
                return int(m.group(1), 16), int(m.group(2), 16)
    raise KeyError('__Tad_AudioData_0 not found in src/main.sym')


def wav_peak(path):
    with wave.open(path) as w:
        raw = w.readframes(w.getnframes())
    n = len(raw) // 2
    if not n:
        return 0
    return max(abs(v) for v in struct.unpack('<' + 'h' * n, raw[:n * 2]))


def main():
    r = Reporter(7)

    with open(AUDIO_BIN, 'rb') as f:
        audio = f.read()
    bank, base = blob_base()
    print(f'audio-data.bin = {len(audio)} bytes, blob base ${bank:02X}:{base:04X}, '
          f'spans ${bank:02X}:{base:04X}-${bank:02X}:{base + len(audio):04X}')

    r.check(f'audio-data.bin is non-trivial ({len(audio)} bytes)', len(audio) > 1024)

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        d = read_block(m, TAD_BLOCK, 64)
        state = d[TAD_STATE - TAD_BLOCK]
        addr = d[TAD_ADDR - TAD_BLOCK] | (d[TAD_ADDR + 1 - TAD_BLOCK] << 8)
        size = d[TAD_SIZE - TAD_BLOCK] | (d[TAD_SIZE + 1 - TAD_BLOCK] << 8)
        print(f'TadPrivate_state=${state:02X}  queue addr=${addr:04X} size={size}')

        # --- 1. The state machine completed, not just started. ---
        r.check(f'TadPrivate_state reached PLAYING (${PLAYING:02X})', state == PLAYING)

        # --- 2. The transfer queue drained and landed inside the real blob.
        # Before the fix this pointed at $8F35 -- valid-looking, and entirely
        # outside the blob. ---
        r.check('transfer queue drained (size == 0)', size == 0)
        # The last song ends exactly at the end of the blob, and TAD's
        # TransferData documents that it "may read one byte past the end of
        # the transfer queue" -- so the drained pointer legitimately lands on
        # blob_end + 1. Asserting that exact landing spot is a much sharper
        # check than a range: it proves the table offsets were rebased by the
        # right amount. Using __Tad_AudioData_0 itself as the base (51 bytes
        # too high) overshot to $C0B6, and the pre-fix LoROM math produced
        # $8F35, nowhere near the blob at all.
        blob_end = base + len(audio)
        r.check(f'final queue address ${addr:04X} is the end of the audio blob '
                f'(${blob_end:04X}, +1 for TAD\'s documented one-byte overread)',
                addr in (blob_end, blob_end + 1))

        # --- 3. GROUND TRUTH: the ROM the loader read from really is the
        # compiled audio data, byte for byte. This is the check that would
        # have caught the zero-padding bug immediately. ---
        probe = 256
        got = bytes(read_block(m, (bank << 16) + base, probe, mem_type='snesMemory'))
        r.check(f'ROM at the blob base byte-matches audio-data.bin (first {probe} bytes)',
                got == audio[:probe])

        # --- 4. The S-DSP is actually running, not held in reset+mute.
        # $E0 = reset|mute|echo-disable, which is what it read all through
        # the phase being blocked. ---
        st = m.get_audio_state()
        dsp = st['dsp']
        print(f"DSP flg=${dsp['flg']:02X} mainVol={dsp['mainVolL']}/{dsp['mainVolR']} "
              f"SPC pc={st['spc']['pc']}")
        r.check('S-DSP is out of reset/mute (FLG != $E0)', dsp['flg'] != 0xE0)
        r.check('S-DSP main volume is non-zero',
                dsp['mainVolL'] != 0 or dsp['mainVolR'] != 0)

        # --- 5. Nmi_FrameCounter still advancing: TAD runs from the main
        # loop, and Tad_FinishLoadingData is a blocking spin, so a driver
        # regression shows up here as a frozen game. ---
        before = read_block(m, 0x7E5023, 32)
        m.run_frames(300)
        m.pause()
        after = read_block(m, 0x7E5023, 32)
        c0 = before[0] | (before[1] << 8)
        c1 = after[0] | (after[1] << 8)
        print(f'Nmi_FrameCounter {c0} -> {c1}')
        r.check('Nmi_FrameCounter still advancing (TAD did not hang the main loop)',
                c1 != c0)

    # --- 6. Real waveform output. The recorder itself has a documented
    # external false-silent rate in this Mesen/MCP environment, so use a
    # bounded majority of 3. This is measurement tolerance, not reassurance:
    # the internal TAD state/transfer checks above remain deterministic and
    # must pass on the same run. ---
    peaks = []
    tmp = tempfile.mkdtemp(prefix='phase7-')
    for i in range(3):
        wav = os.path.join(tmp, f'run{i}.wav')
        with open_session(__file__) as m:
            m.reset_emulator()
            m.run_frames(10)
            m.record_audio(wav)
            m.run_frames(300)
            m.stop_audio()
        peaks.append(wav_peak(wav))
    print(f'recorded peak amplitudes over 3 runs: {peaks}')
    r.check(f'audio is audibly non-silent in a majority of captures {peaks}',
            sum(1 for p in peaks if p > 64) >= 2)

    r.finish()


if __name__ == '__main__':
    main()
