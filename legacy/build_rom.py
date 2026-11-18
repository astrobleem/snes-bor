#!/usr/bin/env python3
# Build SNES-BOR ROM — LoROM, SA-1 + CC-DMA + MSU-1 PoC
import os

ROM_SIZE = 0x400000
BANK0_SIZE = 0x8000

MSU_DATA = b"BEATS OF RAGE SNES MSU-1 PROOF OF CONCEPT OK!\x00"

def main():
    poppy_data = bytearray(open('src/main.bin', 'rb').read())
    print(f"Poppy binary: {len(poppy_data)} bytes (0x{len(poppy_data):X})")

    rom = bytearray(ROM_SIZE)
    copy_len = min(len(poppy_data), BANK0_SIZE)
    rom[0:copy_len] = poppy_data[0:copy_len]

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
    NMI = 0xFE00     # nmi_handler (rti stub)
    IRQ = 0xFE10     # irq_handler (rti stub)

    # Native vectors at $7FE4
    rom[0x7FEA] = NMI & 0xFF;    rom[0x7FEB] = (NMI >> 8) & 0xFF   # NMI
    rom[0x7FEC] = IRQ & 0xFF;    rom[0x7FED] = (IRQ >> 8) & 0xFF   # IRQ

    # Emulation vectors at $7FF4
    rom[0x7FFA] = NMI & 0xFF;    rom[0x7FFB] = (NMI >> 8) & 0xFF   # NMI
    rom[0x7FFC] = RESET & 0xFF;  rom[0x7FFD] = (RESET >> 8) & 0xFF  # RESET
    rom[0x7FFE] = IRQ & 0xFF;    rom[0x7FFF] = (IRQ >> 8) & 0xFF   # IRQ

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
