#!/usr/bin/env python3
"""G11 hardening: regression coverage proving rebuild.py's compiler-version
pin is actually enforced (fatal by default, override only via an explicit
flag) -- not just a warning that could silently drift again.

Not a pytest suite (this project has no test framework, per CLAUDE.md) -- a
standalone script with the same PASS/FAIL-and-exit-nonzero convention
tools/coverage_ledger/test_verify_phase_status.py already uses:

    python soundwork/tad/test_rebuild_version_check.py

Exercises check_compiler_version() directly against small fake "compiler"
scripts (real subprocesses, real --version output) rather than mocking
subprocess -- so this tests the real code path, not a re-description of it.
"""
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rebuild import check_compiler_version, REQUIRED_COMPILER_VERSION  # noqa: E402

FAILURES = []


def check(name, condition):
    status = 'PASS' if condition else 'FAIL'
    print(f'{name}: {status}')
    if not condition:
        FAILURES.append(name)


def make_fake_compiler(tmp_dir: Path, reported_version: str, tag: str) -> Path:
    """A tiny real executable script that answers `--version` the way
    tad-compiler.exe does: `tad-compiler <version>` on stdout. `tag` keeps
    each fake compiler's filename distinct within tmp_dir -- two identically
    named scripts in the same dir would silently overwrite each other."""
    if os.name == 'nt':
        path = tmp_dir / f'fake_tad_compiler_{tag}.bat'
        path.write_text(f'@echo off\r\necho tad-compiler {reported_version}\r\n')
    else:
        path = tmp_dir / f'fake_tad_compiler_{tag}.sh'
        path.write_text(f'#!/bin/sh\necho "tad-compiler {reported_version}"\n')
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        matching = make_fake_compiler(tmp_dir, REQUIRED_COMPILER_VERSION, 'matching')
        mismatched = make_fake_compiler(tmp_dir, '9.9.9', 'mismatched')

        # 1. Exact match: proceeds, returns the version, no exception.
        try:
            got = check_compiler_version(matching)
            check(f'matching version ({REQUIRED_COMPILER_VERSION}) proceeds without error',
                  got == REQUIRED_COMPILER_VERSION)
        except Exception as e:
            print(f'  (exception: {type(e).__name__}: {e})')
            check('matching version proceeds without error', False)

        # 2. Mismatch, default (no override): must be a hard failure (SystemExit).
        raised = False
        try:
            check_compiler_version(mismatched)
        except SystemExit:
            raised = True
        check('mismatched version (default, no override) raises SystemExit (fatal)', raised)

        # 3. Mismatch with allow_mismatch=True: proceeds (explicit override only).
        try:
            got = check_compiler_version(mismatched, allow_mismatch=True)
            check('mismatched version WITH allow_mismatch=True proceeds (explicit override)',
                  got == '9.9.9')
        except SystemExit:
            check('mismatched version WITH allow_mismatch=True proceeds (explicit override)', False)

    if FAILURES:
        print(f'\nFAIL: {len(FAILURES)} check(s) failed: {FAILURES}')
        return 1
    print('\nPASS: rebuild.py compiler-version enforcement behaves correctly')
    return 0


if __name__ == '__main__':
    sys.exit(main())
