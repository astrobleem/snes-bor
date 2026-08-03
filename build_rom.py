#!/usr/bin/env python3
# Build SNES-BOR ROM — LoROM, SA-1 + CC-DMA + MSU-1 PoC
import os
import subprocess
import sys

ROM_SIZE = 0x400000
BANK0_SIZE = 0x8000

MSU_DATA = b"BEATS OF RAGE SNES MSU-1 PROOF OF CONCEPT OK!\x00"

DOTNET = r'C:\Users\chad\.dotnet\dotnet.exe'
POPPY_DLL = r'E:\gh\SNES-CrimePatrol\tools\poppy-src\src\Poppy.CLI\bin\Release\net10.0\poppy.dll'

def assemble():
    # Runs Poppy to (re)produce src/main.bin from src/main.pasm. Previously
    # a separate manual step -- running this script alone silently repacked
    # a STALE main.bin whenever main.pasm had been edited but not
    # reassembled, which cost a full debugging cycle chasing "fixes" that
    # were never actually built. Making this automatic removes that failure
    # mode entirely.
    result = subprocess.run([DOTNET, POPPY_DLL, 'src/main.pasm', '-s', 'src/main.sym'])
    if result.returncode != 0:
        print(f"Poppy assembly failed (exit {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)

def main():
    assemble()
    poppy_data = bytearray(open('src/main.bin', 'rb').read())
    print(f"Poppy binary: {len(poppy_data)} bytes (0x{len(poppy_data):X})")

    rom = bytearray(ROM_SIZE)
    copy_len = min(len(poppy_data), BANK0_SIZE)
    rom[0:copy_len] = poppy_data[0:copy_len]

    # SA-1's reset vector (CRV) is hardware-forced into bank $00 on every
    # SA-1 reset (only a 16-bit PC is programmable), and bank $00-$1F
    # $8000-$FFFF maps directly to ROM banks 0-31 unless CXB ($2220) is
    # written -- main.pasm never writes it. So the SA-1 boots into the SAME
    # physical ROM region as the S-CPU's own main.bin, at $8000: that's
    # sa1_main, a complete routine already assembled into main.bin by
    # Poppy above. src/sa1/sa1_boot.pasm's `.bank 1` code is unreachable
    # from a bare CRV write and is not part of the build.

    # Header at $7FC0 (LoROM)
    title = b"BEATS OF RAGE SNES   "
    rom[0x7FC0:0x7FC0+21] = title
    rom[0x7FD5] = 0x23   # LoROM + SA-1
    rom[0x7FD6] = 0x35   # ROM+SA-1+RAM+Battery
    rom[0x7FD7] = 0x0C   # ROM size
    rom[0x7FD8] = 0x08   # RAM size
    rom[0x7FD9] = 0x01   # USA
    rom[0x7FDA] = 0x33   # Licensee
    rom[0x7FDB] = 0x00   # Version

    # Vectors — fixed by .org directives in main.pasm
    RESET = 0xFC00   # scpu_boot
    NMI = 0xFF00     # nmi_handler (rti stub)
    IRQ = 0xFF10     # irq_handler (rti stub)

    # COP/BRK/ABORT never fire intentionally in this codebase, but leaving
    # their vectors unset means they point at ROM offset 0 (zero-filled
    # RAM/whatever WRAM garbage lives at $00:0000), since `rom = bytearray()`
    # starts fully zeroed and nothing else writes these bytes. Any stray
    # BRK/COP -- e.g. PC running off the end of code into a zero/padding
    # region, since opcode $00 IS brk -- then vectors into WRAM and executes
    # whatever garbage is there, which is unrecoverable and looks like a
    # random, nondeterministic crash. Point them at the same rti stub as IRQ
    # so a spurious interrupt is merely a no-op instead of a runaway trap.
    COP = IRQ
    ABORT = IRQ

    # Native vectors at $7FE4
    rom[0x7FE4] = COP & 0xFF;    rom[0x7FE5] = (COP >> 8) & 0xFF    # COP
    rom[0x7FE6] = IRQ & 0xFF;    rom[0x7FE7] = (IRQ >> 8) & 0xFF    # BRK
    rom[0x7FE8] = ABORT & 0xFF;  rom[0x7FE9] = (ABORT >> 8) & 0xFF  # ABORT
    rom[0x7FEA] = NMI & 0xFF;    rom[0x7FEB] = (NMI >> 8) & 0xFF   # NMI
    rom[0x7FEC] = IRQ & 0xFF;    rom[0x7FED] = (IRQ >> 8) & 0xFF   # IRQ

    # Emulation vectors at $7FF4
    rom[0x7FF4] = COP & 0xFF;    rom[0x7FF5] = (COP >> 8) & 0xFF    # COP
    rom[0x7FF8] = ABORT & 0xFF;  rom[0x7FF9] = (ABORT >> 8) & 0xFF  # ABORT
    rom[0x7FFA] = NMI & 0xFF;    rom[0x7FFB] = (NMI >> 8) & 0xFF   # NMI
    rom[0x7FFC] = RESET & 0xFF;  rom[0x7FFD] = (RESET >> 8) & 0xFF  # RESET
    rom[0x7FFE] = IRQ & 0xFF;    rom[0x7FFF] = (IRQ >> 8) & 0xFF   # IRQ (shared w/ BRK in emulation mode)

    # Checksum
    total = sum(rom) & 0xFFFF
    complement = (~total) & 0xFFFF
    rom[0x7FDC] = complement & 0xFF
    rom[0x7FDD] = (complement >> 8) & 0xFF
    rom[0x7FDE] = total & 0xFF
    rom[0x7FDF] = (total >> 8) & 0xFF

    os.makedirs('build', exist_ok=True)
    os.makedirs('distribution', exist_ok=True)
    
    # Write ROMs
    with open('build/bor.sfc', 'wb') as f:
        f.write(rom)
    with open('distribution/bor.sfc', 'wb') as f:
        f.write(rom)

    # Write MSU-1 data files
    with open('build/bor.msu', 'wb') as f:
        f.write(MSU_DATA)
    with open('distribution/bor.msu', 'wb') as f:
        f.write(MSU_DATA)

    print(f"ROM: {len(rom)} bytes")
    print(f"MSU: {len(MSU_DATA)} bytes (bor.msu)")
    print(f"Reset: ${rom[0x7FFD]<<8|rom[0x7FFC]:04X}  NMI: ${rom[0x7FFB]<<8|rom[0x7FFA]:04X}  IRQ: ${rom[0x7FFF]<<8|rom[0x7FFE]:04X}")
    print(f"Map: ${rom[0x7FD5]:02X}  Cart: ${rom[0x7FD6]:02X}")
    return 0

if __name__ == '__main__':
    exit(main())
