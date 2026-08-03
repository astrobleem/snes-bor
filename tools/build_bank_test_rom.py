#!/usr/bin/env python3
# Pack one of the bank_test_*.pasm experiments into a bootable plain-LoROM
# SNES ROM (no SA-1) for behavioral verification in Mesen2. Usage:
#   python tools/build_bank_test_rom.py bank_test_symbolic
#   python tools/build_bank_test_rom.py bank_test_explicit
import os
import subprocess
import sys

ROM_SIZE = 0x400000

DOTNET = r'C:\Users\chad\.dotnet\dotnet.exe'
POPPY_DLL = r'E:\gh\SNES-CrimePatrol\tools\poppy-src\src\Poppy.CLI\bin\Release\net10.0\poppy.dll'

def main():
    if len(sys.argv) != 2:
        print("usage: build_bank_test_rom.py <name (no .pasm)>", file=sys.stderr)
        return 1
    name = sys.argv[1]
    src = f'tools/{name}.pasm'
    binpath = f'tools/{name}.bin'

    result = subprocess.run([DOTNET, POPPY_DLL, src, '-s', f'tools/{name}.sym', '-o', binpath])
    if result.returncode != 0:
        print(f"Poppy assembly failed (exit {result.returncode})", file=sys.stderr)
        return result.returncode

    data = bytearray(open(binpath, 'rb').read())
    print(f"Poppy binary: {len(data)} bytes (0x{len(data):X})")

    rom = bytearray(ROM_SIZE)
    rom[0:len(data)] = data

    title = (name.upper() + " " * 21)[:21].encode('ascii')
    rom[0x7FC0:0x7FC0+21] = title
    rom[0x7FD5] = 0x20   # LoROM, no coprocessor
    rom[0x7FD6] = 0x00   # ROM only
    rom[0x7FD7] = 0x0C   # ROM size (informational only)
    rom[0x7FD8] = 0x00   # RAM size
    rom[0x7FD9] = 0x01   # USA
    rom[0x7FDA] = 0x33   # Licensee
    rom[0x7FDB] = 0x00   # Version

    RESET = 0x8000
    IRQ = 0x8000  # unused; point at Start as a harmless fallback
    NMI = 0x8000

    rom[0x7FE4] = IRQ & 0xFF;    rom[0x7FE5] = (IRQ >> 8) & 0xFF    # COP (native)
    rom[0x7FE6] = IRQ & 0xFF;    rom[0x7FE7] = (IRQ >> 8) & 0xFF    # BRK (native)
    rom[0x7FE8] = IRQ & 0xFF;    rom[0x7FE9] = (IRQ >> 8) & 0xFF    # ABORT (native)
    rom[0x7FEA] = NMI & 0xFF;    rom[0x7FEB] = (NMI >> 8) & 0xFF    # NMI (native)
    rom[0x7FEC] = IRQ & 0xFF;    rom[0x7FED] = (IRQ >> 8) & 0xFF    # IRQ (native)

    rom[0x7FF4] = IRQ & 0xFF;    rom[0x7FF5] = (IRQ >> 8) & 0xFF    # COP (emu)
    rom[0x7FF8] = IRQ & 0xFF;    rom[0x7FF9] = (IRQ >> 8) & 0xFF    # ABORT (emu)
    rom[0x7FFA] = NMI & 0xFF;    rom[0x7FFB] = (NMI >> 8) & 0xFF    # NMI (emu)
    rom[0x7FFC] = RESET & 0xFF;  rom[0x7FFD] = (RESET >> 8) & 0xFF  # RESET (emu)
    rom[0x7FFE] = IRQ & 0xFF;    rom[0x7FFF] = (IRQ >> 8) & 0xFF    # IRQ (emu)

    total = sum(rom) & 0xFFFF
    complement = (~total) & 0xFFFF
    rom[0x7FDC] = complement & 0xFF
    rom[0x7FDD] = (complement >> 8) & 0xFF
    rom[0x7FDE] = total & 0xFF
    rom[0x7FDF] = (total >> 8) & 0xFF

    out = f'tools/{name}.sfc'
    with open(out, 'wb') as f:
        f.write(rom)
    print(f"Wrote {out} ({len(rom)} bytes)")
    return 0

if __name__ == '__main__':
    sys.exit(main())
