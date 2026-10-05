"""Owner-scoped named script variables and the bounded native storage ABI.

Pinned authority: af23dc9 openborscript.c Varlist_*, Script_Copy and
system_*localvar; scriptlib/List.c uses strcmp. Script_Copy shares executable
code but retains the destination instance's variable list. Animation callbacks
for current/default models therefore use the entity's same animation instance.
"""
import struct

MAGIC=0xb4a4
BANK=0x41
BASE=0x8800
CAPACITY=384
STRIDE=64
KEY_BYTES=48
FIRST_UNUSED=BASE+CAPACITY*STRIDE
SUPPORTED_TAGS={0,1,2,5}


def pack_record(owner,scope,name,value):
    if not 0<owner<=0xffffffff or not 0<scope<=0xffff:
        raise ValueError('SCRIPT_VARIABLE_INSTANCE_ID')
    raw=name.encode('utf-8')
    if not 1<=len(raw)<KEY_BYTES or b'\0' in raw:
        raise ValueError('SCRIPT_VARIABLE_NATIVE_KEY_CAPACITY')
    if len(value)!=8 or value[0] not in SUPPORTED_TAGS or value[1:4]!=bytes(3):
        raise ValueError('SCRIPT_VARIABLE_NATIVE_VALUE_CAPABILITY')
    if value[0]==0 and value[4:]!=bytes(4):raise ValueError('SCRIPT_VARIABLE_EMPTY_PAYLOAD')
    return struct.pack('<IHH',owner,scope,len(raw))+value+raw+bytes(KEY_BYTES-len(raw))


def validate_pool(data):
    if not data or len(data)%STRIDE or len(data)//STRIDE>CAPACITY:
        raise ValueError('SCRIPT_VARIABLE_NATIVE_POOL_CAPACITY')
    identities=set()
    for offset in range(0,len(data),STRIDE):
        row=data[offset:offset+STRIDE];owner,scope,length=struct.unpack_from('<IHH',row)
        if length==0:
            if row!=bytes(STRIDE):raise ValueError('SCRIPT_VARIABLE_FREE_RECORD_NOT_ZERO')
            continue
        if not 0<length<KEY_BYTES or any(row[16+length:]):raise ValueError('SCRIPT_VARIABLE_NATIVE_KEY_RECORD')
        raw=row[16:16+length]
        try:name=raw.decode('utf-8')
        except UnicodeDecodeError:raise ValueError('SCRIPT_VARIABLE_NATIVE_KEY_ENCODING') from None
        if pack_record(owner,scope,name,row[8:16])!=row:raise ValueError('SCRIPT_VARIABLE_NATIVE_RECORD')
        identity=(owner,scope,raw)
        if identity in identities:raise ValueError('SCRIPT_VARIABLE_DUPLICATE_KEY')
        identities.add(identity)


def descriptor(owner,scope=1,count=CAPACITY):
    if not 0<owner<=0xffffffff or not 0<scope<=0xffff or not 1<=count<=CAPACITY:
        raise ValueError('SCRIPT_VARIABLE_NATIVE_DESCRIPTOR')
    return struct.pack('<HIHHHBx',MAGIC,owner,scope,count,BASE,BANK)


class VariantList:
    """Source authority oracle; native STR/index capabilities remain separate."""
    def __init__(self):self.names={};self.indices={}
    def get(self,key):
        if isinstance(key,str):return self.names.get(key,bytes(8))
        if isinstance(key,(int,float)):return self.indices.get(int(key),bytes(8))
        raise ValueError('SCRIPT_VARIABLE_INVALID_KEY_TYPE')
    def set(self,key,value):
        if isinstance(key,str):
            if not key:return 0
            self.names[key]=value
        elif isinstance(key,(int,float)):
            index=int(key)
            if index<0:return 0
            self.indices[index]=value
        else:raise ValueError('SCRIPT_VARIABLE_INVALID_KEY_TYPE')
        return 1
    def cleanup(self):
        for key in self.names:self.names[key]=bytes(8)
        for key in self.indices:self.indices[key]=bytes(8)


class Instances:
    def __init__(self):self.instances={}
    def for_script(self,entity_token,script_kind='animation'):
        return self.instances.setdefault((entity_token,script_kind),VariantList())
