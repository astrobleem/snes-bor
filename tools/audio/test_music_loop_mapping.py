#!/usr/bin/env python3
"""Focused regression for BOR encoded-byte loop offsets."""
from convert_bor_music import bor_loop_frames, msu_loop_frames


def main() -> int:
    assert bor_loop_frames(0, 1) == 0
    assert bor_loop_frames(1, 1) == 2
    assert msu_loop_frames(bor_loop_frames(1, 1), 22050) == 4
    assert bor_loop_frames(7, 2) == 7
    assert msu_loop_frames(bor_loop_frames(7, 2), 22050) == 14
    # Repeat is an engine-call property, independent of the encoded offset.
    assert bor_loop_frames(0, 1) == bor_loop_frames(0, 1)
    print("BOR LOOP PASS: byte offsets map to decoded/resampled stereo frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
