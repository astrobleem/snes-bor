"""Offline constant randf capability; explicit Q16 numeric compatibility."""
import struct,math
from source_binary32_q16 import project

MAGIC=b'B5RF'
HEADER=24
MODULUS=10000
def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]
def values(maximum,source_bits=None):
 maximum=f32(maximum)
 if not math.isfinite(maximum)or maximum<0 or maximum>=256:raise ValueError('SOURCE_RANDF_U24_MAXIMUM_DOMAIN')
 if source_bits is not None:
  if len(source_bits)!=MODULUS:raise ValueError('SOURCE_RANDF_AUTHORITY_COUNT')
  result=list(source_bits)
  for v in result:
   f=struct.unpack('<f',struct.pack('<I',v))[0]
   if not math.isfinite(f)or f<0 or f>maximum:raise ValueError('SOURCE_RANDF_AUTHORITY_VALUE_DOMAIN')
  return result
 if maximum==0:return [0]*MODULUS
 try:divisor=f32(10000/maximum)
 except OverflowError:raise ValueError('SOURCE_RANDF_DIVISOR_DOMAIN')from None
 if not math.isfinite(divisor)or divisor==0:raise ValueError('SOURCE_RANDF_DIVISOR_DOMAIN')
 # C/x87 may retain a wider intermediate divisor. Do not substitute an
 # independently rounded binary32 divisor without current C authority.
 if divisor!=10000/maximum:raise ValueError('SOURCE_RANDF_C_TABLE_REQUIRED')
 return [bits(f32(n/divisor))for n in range(MODULUS)]
def pack(maximum,source_bits=None):
 original=values(maximum,source_bits);projected=[project(v)for v in original]
 assert all(0<=v<1<<24 for v in projected)
 return struct.pack('<4sHHIIII',MAGIC,1,3,MODULUS,bits(f32(maximum)),HEADER,0)+b''.join(v.to_bytes(3,'little')for v in projected)
def unpack(raw,source_bits=None):
 if len(raw)!=HEADER+MODULUS*3:raise ValueError('SOURCE_RANDF_U24_BYTES')
 magic,version,stride,count,maximum,offset,reserved=struct.unpack_from('<4sHHIIII',raw)
 if(magic,version,stride,count,offset,reserved)!=(MAGIC,1,3,MODULUS,HEADER,0):raise ValueError('SOURCE_RANDF_U24_DESCRIPTOR')
 expected=pack(struct.unpack('<f',struct.pack('<I',maximum))[0],source_bits)
 if raw!=expected:raise ValueError('SOURCE_RANDF_U24_SOURCE_IDENTITY')
 return [int.from_bytes(raw[i:i+3],'little')for i in range(HEADER,len(raw),3)]
