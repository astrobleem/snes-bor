#!/usr/bin/env python3
import os

PATH = 'build/bor.sfc'
rom = bytearray(open(PATH, 'rb').read())

# Header at $7FC0 (LoROM)
title = b'BEATS OF RAGE SNES   '
rom[0x7FC0:0x7FC0+21] = title
rom[0x7FD5] = 0x23   # LoROM + SA-1
rom[0x7FD6] = 0x35   # ROM+SA-1+RAM+Battery
rom[0x7FD7] = 0x0C   # ROM size: 4MB
rom[0x7FD8] = 0x08   # RAM size: 256KB
rom[0x7FD9] = 0x01   # USA
rom[0x7FDA] = 0x33   # Licensee
rom[0x7FDB] = 0x00   # Version

# Pad/mirror to 4MB if needed
if len(rom) < 0x400000:
    bank = rom[:0x8000]
    rom = bank
    while len(rom) < 0x400000:
        rom += bank
    rom = rom[:0x400000]

# Clear checksum
rom[0x7FDC:0x7FE0] = b'\x00\x00\x00\x00'

# Compute checksum
total = sum(rom) & 0xFFFF
comp = (~total) & 0xFFFF
rom[0x7FDC] = comp & 0xFF
rom[0x7FDD] = (comp >> 8) & 0xFF
rom[0x7FDE] = total & 0xFF
rom[0x7FDF] = (total >> 8) & 0xFF

open(PATH, 'wb').write(rom)
open('distribution/bor.sfc', 'wb').write(rom)
print('ROM', hex(len(rom)))
print('reset', hex((rom[0x7FFD]<<8)|rom[0x7FFC]))
print('nmi', hex((rom[0x7FFB]<<8)|rom[0x7FFA]))
print('irq', hex((rom[0x7FFF]<<8)|rom[0x7FFE]))
print('map', hex(rom[0x7FD5]), 'cart', hex(rom[0x7FD6]))