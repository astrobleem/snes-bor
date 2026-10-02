#!/usr/bin/env python3
"""Fail-closed differential oracle for the passive Mesen voice-7 capture."""
import argparse
import hashlib
import json
import math
import struct
import sys


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def load_capture(report_path, raw_path, expected_rom, expected_voice):
    report = json.load(open(report_path, encoding='utf-8'))
    raw = open(raw_path, 'rb').read()
    required = ('rom_sha256', 'capture_sha256', 'voice', 'sample_rate',
                'sample_count', 'kon_sample', 'endx_sample')
    missing = [key for key in required if key not in report]
    if missing:
        raise ValueError(f'{report_path}: missing fields: {", ".join(missing)}')
    if report['rom_sha256'] != expected_rom:
        raise ValueError(f'{report_path}: ROM hash mismatch')
    if report['voice'] != expected_voice:
        raise ValueError(f'{report_path}: selected voice mismatch')
    if report['sample_rate'] != 32000:
        raise ValueError(f'{report_path}: unexpected sample rate')
    if report['kon_sample'] != 0:
        raise ValueError(f'{report_path}: capture is not KON-bounded')
    if report['endx_sample'] != report['sample_count']:
        raise ValueError(f'{report_path}: ENDX/sample-count mismatch')
    if len(raw) != report['sample_count'] * 4:
        raise ValueError(f'{report_path}: PCM byte-count mismatch')
    actual_sha = sha256(raw_path)
    if report['capture_sha256'] != actual_sha:
        raise ValueError(f'{report_path}: PCM hash mismatch')
    return report, raw


def correlation(a, b):
    xs = struct.unpack('<' + 'h' * (len(a) // 2), a)
    ys = struct.unpack('<' + 'h' * (len(b) // 2), b)
    if len(xs) != len(ys) or not xs:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    return numerator / (denom_x * denom_y) if denom_x and denom_y else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--good-report', required=True)
    parser.add_argument('--good-raw', required=True)
    parser.add_argument('--good-rom-sha256', required=True)
    parser.add_argument('--current-report', required=True)
    parser.add_argument('--current-raw', required=True)
    parser.add_argument('--current-rom-sha256', required=True)
    parser.add_argument('--voice', type=int, default=7)
    parser.add_argument('--min-correlation', type=float, default=0.99)
    args = parser.parse_args()

    try:
        good, good_raw = load_capture(args.good_report, args.good_raw,
                                      args.good_rom_sha256, args.voice)
        current, current_raw = load_capture(args.current_report, args.current_raw,
                                            args.current_rom_sha256, args.voice)
        if good['sample_rate'] != current['sample_rate']:
            raise ValueError('capture sample rates differ')
        if good['sample_count'] != current['sample_count']:
            raise ValueError('KON-to-ENDX sample counts differ')
        if good.get('koff_sample') is not None and current.get('koff_sample') is not None:
            if abs(good['koff_sample'] - current['koff_sample']) > 2:
                raise ValueError('KOFF timing differs')
        corr = correlation(good_raw, current_raw)
        if corr < args.min_correlation:
            raise ValueError(f'voice PCM correlation {corr:.6f} below threshold')
        result = {
            'result': 'PASS',
            'voice': args.voice,
            'sample_rate': current['sample_rate'],
            'good_sample_count': good['sample_count'],
            'current_sample_count': current['sample_count'],
            'good_duration_s': good['sample_count'] / good['sample_rate'],
            'current_duration_s': current['sample_count'] / current['sample_rate'],
            'good_pcm_sha256': good['capture_sha256'],
            'current_pcm_sha256': current['capture_sha256'],
            'direct_correlation': corr,
            'byte_identical': good_raw == current_raw,
        }
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({'result': 'INVALID_CAPTURE', 'reason': str(exc)}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
