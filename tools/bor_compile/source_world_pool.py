"""Exclusive foreign-world pool ownership, separate from original-BOR slots.

The proposed physical SA-1 BW-RAM lease is $41:4000..$41:87ff (128 views plus
128 sidecars). It must not be granted concurrently with another owner of those
bytes. Slot tokens are stable across births, matching source entity pool reuse.
This allocation ABI does not implement physics, collisions or presentation.
"""
import struct
from source_entity_abi import record,PROPERTIES

POOL_BANK=0x41
POOL_BASE=0x4000
SIDE_BASE=0x6800
CAPACITY=128
VIEW_STRIDE=80
SIDE_STRIDE=64
MAGIC=0xb4a3
FIRST_UNUSED=0x8800


def empty_pool(count=CAPACITY):
    if not 1<=count<=CAPACITY:raise ValueError('SOURCE_WORLD_POOL_CAPACITY')
    values={name:0 for name,_ in PROPERTIES}
    records=[]
    for n in range(count):
        # Opaque stable token, not a legacy character index or model identity.
        token=(POOL_BANK<<16)+POOL_BASE+n*VIEW_STRIDE
        records.append(record(token,values,alive=False))
    return b''.join(records),bytes(count*SIDE_STRIDE)


def descriptor(count,template_address,template_count,template_bytes,time=0,level=True):
    if not 1<=count<=CAPACITY or template_address>>16>=64 or template_address&65535<0x8000:
        raise ValueError('SOURCE_WORLD_POOL_DESCRIPTOR')
    if not 1<=template_count<=CAPACITY or template_bytes!=24+160*template_count:
        raise ValueError('SOURCE_WORLD_TEMPLATE_SIZE')
    if (template_address&65535)+template_bytes>65536 or not 0<=time<=0xffffffff:
        raise ValueError('SOURCE_WORLD_TEMPLATE_BANK_OR_TIME')
    return struct.pack('<HHHHHHBxHHI',MAGIC,int(level),POOL_BASE,SIDE_BASE,count,
                       template_address&65535,template_address>>16,template_count,template_bytes,time)
