#!/usr/bin/env python3
"""plan_vm.md §8 step 1: export_*_module -- pull a real openborscript function
out of an arbitrary OpenBOR .pak and emit the VM's revision-1 binary module
(FORMAT.md). General-purpose per CLAUDE.md's own rule for tools/bor_converter/:
takes a pak path and an internal script path on the command line, not a
single mod hardcoded in the script body. What's still specific to one script
is natives.py's CALL_SPECIALIZATIONS table (compiler.py's own docstring
explains why: this exporter compiles ahead of time, so each (native
function, compile-time-constant string arg) pair the TARGET script actually
uses gets its own stable ID rather than a runtime string dispatcher) --
exporting a script that calls a native/property-string pair not already in
that table fails with CompileError naming exactly which call is unsupported,
not a silent wrong module.

Usage:
    python export_openbor_script_module.py <pak_path> <internal_script_path> <out.vmmod>

Example (this project's own Gate 6 fixture):
    python export_openbor_script_module.py \\
        "Double Dragon Moto [Ver. 0.2][v.3.0 Build 4432].pak" \\
        "DATA\\SCRIPTS\\SPAWN000.C" out/spawn000.vmmod
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pak_extract  # noqa: E402
from openbor_script import lexer, parser, compiler, module as modpkg  # noqa: E402


def export_module(pak_path, internal_path):
    """Returns (compiler.Module, packed_bytes)."""
    src_bytes = pak_extract.extract(pak_path, internal_path)
    src = src_bytes.decode('utf-8', errors='replace')
    toks = lexer.tokenize(src)
    program = parser.Parser(toks).parse_program()
    m = compiler.compile_module(program)
    blob = modpkg.pack_module(m)
    return m, blob


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)
    pak_path, internal_path, out_path = sys.argv[1:4]

    m, blob = export_module(pak_path, internal_path)

    print(f'source: {internal_path} (from {os.path.basename(pak_path)})')
    print(f'instructions: {len(m.instructions)}')
    print(f'slots: {len(m.slots)}')
    print(f'callsites: {len(m.callsites)}')
    print(f'strings: {len(m.strings)}')
    print(f'natives used: {sorted(m.natives_used)}')
    print(f'params: {[(n, t) for n, _s, t in m.param_names]}')
    print(f'module size: {len(blob)} bytes')

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(blob)
    print(f'wrote {out_path}')


if __name__ == '__main__':
    main()
