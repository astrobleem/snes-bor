"""Exact source binary32 threshold for a compiler-proven integral duration."""
import struct
def binary32(n):return struct.unpack('<f',struct.pack('<f',n))[0]
def compare(stall,time,delay,evaluation='WIN32_X87_EXTENDED'):
    if not 0<=stall<=0xffffffff or not 0<=time<=0xffffffff or not 0<=delay<=65535:raise ValueError('U32_FLOAT_THRESHOLD_DOMAIN')
    if evaluation=='WIN32_X87_EXTENDED':return int(stall+delay<time)
    if evaluation=='BINARY32':return int(binary32(binary32(stall)+delay)<binary32(time))
    raise ValueError('U32_FLOAT_THRESHOLD_EVALUATION')
