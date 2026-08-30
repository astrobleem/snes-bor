#!/usr/bin/env python3
"""Reproducibly regenerate soundwork/tad/build/* from the checked-in TAD
authoring project (soundwork/tad/project/02_coin.terrificaudio), and detect
drift between the committed outputs and what the real compiler produces.

G11 hardening: before this tool existed, editing the .terrificaudio project
or sound-effects.txt and forgetting to regenerate build/audio-data.bin was a
silent failure mode -- the ROM would keep .incbin'ing stale audio data with
no error anywhere in the pipeline. This is the fix: an explicit, auditable
regeneration step with --check/--update semantics, plus a compiler-identity
check so a differently-versioned compiler can't silently produce different
bytes without anyone noticing.

This project does NOT vendor the tad-compiler binary (it is a build tool,
not a runtime asset -- consistent with Poppy living in a sibling repo per
CLAUDE.md's toolchain section). Point this script at one with --compiler,
or set the TAD_COMPILER environment variable. As a last resort it will
look in a couple of sibling-repo conventional locations used elsewhere in
this developer's own tree, but will refuse to guess silently -- it always
prints which binary and version it used.

Usage:
    python soundwork/tad/rebuild.py --check
    python soundwork/tad/rebuild.py --update
    python soundwork/tad/rebuild.py --check --compiler C:\\path\\to\\tad-compiler.exe
"""
import argparse
import filecmp
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
PROJECT_FILE = HERE / "project" / "02_coin.terrificaudio"
BUILD_DIR = HERE / "build"
OUT_ASM = BUILD_DIR / "audio-data.s"
OUT_BIN = BUILD_DIR / "audio-data.bin"
OUT_INC = BUILD_DIR / "audio-enums.inc"
OUT_SYMS = BUILD_DIR / "tad_blob_syms.pasm"
MAIN_SYM = HERE.parents[1] / "src" / "main.sym"

# This is a REAL, tested compiler binary -- not a guessed version number.
# The project file's own "_about"."version" field is the TAD *project file
# format* version, which is versioned independently of the compiler CLI
# version (confirmed empirically: this compiler reports itself as 0.3.0 and
# writes/reads "_about" version "0.3.0" project files, not 0.4.2 -- an
# earlier draft of this task assumed the CLI was also on 0.4.2, which does
# not exist anywhere on this machine or in any sibling repo. Ground truth
# beats an assumed version number.)
REQUIRED_COMPILER_VERSION = "0.3.0"

FALLBACK_COMPILER_PATHS = [
    Path(r"E:\gh\snes-outrun-sa1\tools\tad\tad-compiler.exe"),
    Path(r"E:\gh\SNES-SuperMonkeyIsland\tools\tad\tad-compiler.exe"),
]


def find_compiler(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise SystemExit(f"FAIL: --compiler path does not exist: {p}")
        return p
    env = os.environ.get("TAD_COMPILER")
    if env:
        p = Path(env)
        if not p.exists():
            raise SystemExit(f"FAIL: TAD_COMPILER path does not exist: {p}")
        return p
    for p in FALLBACK_COMPILER_PATHS:
        if p.exists():
            return p
    raise SystemExit(
        "FAIL: no tad-compiler binary found. Pass --compiler <path>, set "
        "TAD_COMPILER, or vendor one under soundwork/tad/. This project "
        "deliberately does not silently assume a global 'tad-compiler' on "
        "PATH."
    )


def check_compiler_version(compiler: Path, allow_mismatch: bool = False) -> str:
    """Enforces REQUIRED_COMPILER_VERSION. A mismatch used to be a warning
    only -- that defeats the whole point of pinning a version, since a
    silently-different compiler can legitimately produce different bytes
    for reasons that have nothing to do with a real project edit, and
    --check would then either false-positive DRIFT against a still-correct
    commit, or (worse) --update would silently commit output from the wrong
    compiler. A mismatch is now fatal unless the caller explicitly passes
    --allow-version-mismatch."""
    result = subprocess.run(
        [str(compiler), "--version"], capture_output=True, text=True, check=True
    )
    version_line = result.stdout.strip()
    # "tad-compiler 0.3.0"
    version = version_line.rsplit(" ", 1)[-1]
    if version != REQUIRED_COMPILER_VERSION:
        if allow_mismatch:
            print(
                f"WARNING: compiler reports version {version!r}, expected "
                f"{REQUIRED_COMPILER_VERSION!r} ({compiler}). Proceeding "
                f"ONLY because --allow-version-mismatch was passed -- "
                f"outputs may differ from the committed ones for reasons "
                f"other than a real project edit."
            )
        else:
            raise SystemExit(
                f"FAIL: compiler version mismatch -- {compiler} reports "
                f"{version!r}, pinned REQUIRED_COMPILER_VERSION is "
                f"{REQUIRED_COMPILER_VERSION!r}. Refusing to compile with "
                f"an unpinned compiler (this is exactly the guarantee this "
                f"tool exists to enforce -- see rebuild.py's own module "
                f"docstring). Pass --allow-version-mismatch to override "
                f"explicitly if you have a genuine, deliberate reason to "
                f"test a different compiler version."
            )
    return version


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_project(compiler: Path, out_dir: Path) -> None:
    out_asm = out_dir / "audio-data.s"
    out_bin = out_dir / "audio-data.bin"
    out_inc = out_dir / "audio-enums.inc"
    cmd = [
        str(compiler), "ca65-export", str(PROJECT_FILE),
        "-a", str(out_asm), "-b", str(out_bin), "-i", str(out_inc),
        "-s", "AUDIO0", "--lorom",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"FAIL: tad-compiler ca65-export failed (exit {result.returncode})")


def parse_blob_syms(audio_data_s: Path, base_addr: int) -> str:
    """Regenerate tad_blob_syms.pasm (the Poppy-syntax constants main.pasm
    .include's) from a freshly compiled audio-data.s.

    THE REAL BUG THIS FUNCTION EXISTS TO PREVENT (found during G11
    hardening, 2026-08-30): audio-data.s/.bin/enums.inc were regenerated by
    an earlier version of this script, but tad_blob_syms.pasm -- also
    machine-generated originally (its own header says "GENERATED by
    tad-compiler ca65-export; do not edit"), but ported to Poppy syntax BY
    HAND when TAD was first integrated and never wired into any regen
    tooling since -- was NOT. Its `Tad_DataTable` offset went stale by the
    exact number of bytes common-data grew (29, from the beat1 fix), and
    main.pasm's LoadAudioData read the data-item directory table from the
    WRONG offset at runtime: not a crash, not a build error, not a static-
    audit finding -- TadPrivate_state still reached PLAYING and the S-DSP
    still produced non-silent output (phase7.py's own weaker checks all
    passed), but the actual song-data pointer/size read out of that
    misaligned table was `addr=$B727 size=12080` instead of the real
    `addr=$9044 size=1905` -- reading and streaming ~10KB of unrelated
    adjacent ROM content as if it were audio data. Found only because
    phase7.py's ground-truth blob_end assertion (not "did TAD report a
    status word", the exact class of false-positive CLAUDE.md's own
    Testing section warns about) caught the wrong final address. This is
    now regenerated automatically instead of trusted to stay in sync by
    hand.
    """
    text = audio_data_s.read_text()

    def find_export(name: str) -> str:
        m = re.search(rf'\.export\s+{re.escape(name)}\s*:?=\s*(.+)', text)
        if not m:
            m = re.search(rf'^{re.escape(name)}\s*:?=\s*(.+)$', text, re.M)
        if not m:
            raise SystemExit(f"FAIL: could not find {name!r} in {audio_data_s}")
        return m.group(1).strip()

    def resolve(expr: str) -> int:
        expr = expr.strip()
        m = re.match(r'__Tad_AudioData_0\s*\+\s*(\d+)', expr)
        if m:
            return base_addr + int(m.group(1))
        return int(expr)

    loader_size = resolve(find_export('Tad_Loader_SIZE'))
    driver_bin = resolve(find_export('Tad_AudioDriver_Bin'))
    driver_size = resolve(find_export('Tad_AudioDriver_SIZE'))
    data_table = resolve(find_export('Tad_DataTable'))
    n_items_m = re.search(r'^N_DATA_ITEMS\s*=\s*(\d+)', text, re.M)
    if not n_items_m:
        raise SystemExit(f"FAIL: could not find N_DATA_ITEMS in {audio_data_s}")
    n_items = int(n_items_m.group(1))

    bank = (base_addr >> 16) & 0xFF
    return (
        "; GENERATED by soundwork/tad/rebuild.py (parses tad-compiler's own\n"
        "; ca65-export output); do not edit by hand -- see rebuild.py's\n"
        "; parse_blob_syms() docstring for the exact staleness bug this\n"
        "; automation replaced.\n"
        f"AUDIO_DATA_BANK = ${bank:02X}\n"
        f"Tad_Loader_Bin = ${base_addr:06X}\n"
        f"Tad_Loader_SIZE = {loader_size}\n"
        f"Tad_AudioDriver_Bin = ${driver_bin:06X}\n"
        f"Tad_AudioDriver_SIZE = {driver_size}\n"
        f"Tad_DataTable = ${data_table:06X}\n"
        f"N_DATA_ITEMS = {n_items}\n"
    )


def find_audio_data_base() -> int:
    """(bank<<16 | addr) of __Tad_AudioData_0, from a real Poppy build's
    src/main.sym -- same approach tools/verify/phase7.py's blob_base() uses.
    __Tad_AudioData_0 marks where main.pasm's .incbin of audio-data.bin
    begins; it moves only if code before that .incbin (inside .bank 1)
    changes size, not when the audio project itself changes, so reading it
    from the last real build is reliable here."""
    if not MAIN_SYM.exists():
        raise SystemExit(
            f"FAIL: {MAIN_SYM} does not exist -- run 'python build_rom.py' "
            f"at least once first so tad_blob_syms.pasm regeneration has a "
            f"real bank:address to anchor to."
        )
    with open(MAIN_SYM, encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            m = re.match(r'\s*([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)', line)
            if m and m.group(3) == '__Tad_AudioData_0':
                return (int(m.group(1), 16) << 16) | int(m.group(2), 16)
    raise SystemExit(f"FAIL: __Tad_AudioData_0 not found in {MAIN_SYM}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                       help="regenerate to a temp dir and compare with committed build/ outputs; fail on drift")
    mode.add_argument("--update", action="store_true",
                       help="regenerate and overwrite committed build/ outputs")
    ap.add_argument("--compiler", default=None, help="path to tad-compiler.exe")
    ap.add_argument("--allow-version-mismatch", action="store_true",
                     help="proceed even if the compiler's --version does not match "
                          "REQUIRED_COMPILER_VERSION (default: fatal). Explicit "
                          "override only -- never silent.")
    args = ap.parse_args()

    if not PROJECT_FILE.exists():
        raise SystemExit(f"FAIL: project file not found: {PROJECT_FILE}")

    compiler = find_compiler(args.compiler)
    version = check_compiler_version(compiler, allow_mismatch=args.allow_version_mismatch)
    print(f"Using compiler: {compiler} (version {version})")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        compile_project(compiler, tmp_dir)

        new_files = {
            "audio-data.s": tmp_dir / "audio-data.s",
            "audio-data.bin": tmp_dir / "audio-data.bin",
            "audio-enums.inc": tmp_dir / "audio-enums.inc",
        }
        old_files = {
            "audio-data.s": OUT_ASM,
            "audio-data.bin": OUT_BIN,
            "audio-enums.inc": OUT_INC,
        }

        base_addr = find_audio_data_base()
        new_syms = parse_blob_syms(new_files["audio-data.s"], base_addr)

        if args.update:
            BUILD_DIR.mkdir(parents=True, exist_ok=True)
            for name, src in new_files.items():
                shutil.copyfile(src, old_files[name])
            OUT_SYMS.write_text(new_syms)
            print("Updated committed outputs:")
            for name, dst in old_files.items():
                print(f"  {name}: sha256={sha256_of(dst)} ({dst.stat().st_size} bytes)")
            print(f"  tad_blob_syms.pasm: sha256={sha256_of(OUT_SYMS)} ({OUT_SYMS.stat().st_size} bytes)")
            return 0

        # --check
        drift = False
        for name, new_path in new_files.items():
            old_path = old_files[name]
            if not old_path.exists():
                print(f"DRIFT: {name} does not exist in build/ at all")
                drift = True
                continue
            if name == "audio-data.bin":
                same = old_path.read_bytes() == new_path.read_bytes()
            else:
                # .s / .inc: compare with normalized line endings (text)
                same = old_path.read_text().replace("\r\n", "\n") == \
                    new_path.read_text().replace("\r\n", "\n")
            if same:
                print(f"OK: {name} matches committed output")
            else:
                print(f"DRIFT: {name} differs from committed output")
                if name == "audio-data.bin":
                    print(f"  committed: sha256={sha256_of(old_path)} ({old_path.stat().st_size} bytes)")
                    print(f"  fresh:     sha256={sha256_of(new_path)} ({new_path.stat().st_size} bytes)")
                drift = True

        if not OUT_SYMS.exists():
            print("DRIFT: tad_blob_syms.pasm does not exist at all")
            drift = True
        else:
            old_syms_text = OUT_SYMS.read_text().replace("\r\n", "\n")
            if old_syms_text.split("\n", 4)[-1] == new_syms.split("\n", 4)[-1]:
                # Compare content past the header comment (line count varies
                # if the header wording changes; the actual constants are
                # what matters for drift).
                print("OK: tad_blob_syms.pasm matches committed output")
            else:
                print("DRIFT: tad_blob_syms.pasm differs from committed output "
                      "(main.pasm's LoadAudioData would read the WRONG data-"
                      "table offset -- see parse_blob_syms()'s own docstring "
                      "for the real bug this caught)")
                print(f"  committed:\n{old_syms_text}")
                print(f"  fresh:\n{new_syms}")
                drift = True

        if drift:
            print(
                "\nFAIL: committed soundwork/tad/build/* is stale relative to "
                "soundwork/tad/project/02_coin.terrificaudio and/or "
                "sound-effects.txt. Run 'python soundwork/tad/rebuild.py "
                "--update' and commit the result."
            )
            return 1

        print("\nOK: committed build/ outputs are up to date with the project source.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
