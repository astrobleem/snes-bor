"""Explicit compatibility projection of source binary32 movement into Q16.16."""
import struct

def project(bits):
 value=struct.unpack('<f',struct.pack('<I',bits))[0]
 if not -32768<value<32768:raise ValueError('SOURCE_SPEED_Q16_DOMAIN_REQUIRED')
 return int(value*65536)

def fixture_bits():
 values={0,0x80000000,1,0x80000001,0x007fffff,0x807fffff,0x00800000,0x80800000,0x7f800000,0xff800000,0x7fc00000,0xffc00000}
 for exp in range(256):
  for mantissa in (0,1,0x7fffff):
   for sign in (0,0x80000000):values.add(sign|(exp<<23)|mantissa)
 for value in (1.3,-1.3,0.5,-0.5,32767.998046875,-32767.998046875):values.add(struct.unpack('<I',struct.pack('<f',value))[0])
 return sorted(values)
