"""Guard malformed resume identities and module pairing before native use."""
import struct, zlib
import pytest
from source_native_continuation import pack, unpack, CONTEXT_BYTES

def sample():
    return dict(program_count=1,instruction_crc32=1,metadata_crc32=2,records=[dict(
        program=0,resume_ip=10,native_id=0x20e,callsite=3,result_slot=8,
        frame_callsites=[2],slots=[7,8,9],snapshot_bytes=CONTEXT_BYTES+12+24)])

def reseal(raw):
    raw=bytearray(raw);struct.pack_into('<I',raw,16,zlib.crc32(raw[32:])&0xffffffff);return bytes(raw)

def test_capacity_and_source_slots():
    report=sample();raw=pack(report);rows,icrc,mcrc=unpack(raw)
    assert rows==report['records']and(icrc,mcrc)==(1,2)
    report['records'][0]['slots']=list(range(40));report['records'][0]['snapshot_bytes']=CONTEXT_BYTES+12+320
    with pytest.raises(ValueError,match='RECORD'):pack(report)

@pytest.mark.parametrize('offset,value,error',[(32,33,'DIRECTORY'),(34,14,'DIRECTORY'),(46,10,'ROW'),(50,1,'ROW'),(50,513,'ROW'),(58,7,'SLOTS')])
def test_valid_crc_does_not_admit_malformed_rows(offset,value,error):
    raw=bytearray(pack(sample()));struct.pack_into('<H',raw,offset,value)
    with pytest.raises(ValueError,match=error):unpack(reseal(raw))

def test_crc_and_truncation_are_rejected():
    raw=pack(sample())
    with pytest.raises(ValueError,match='ABI'):unpack(raw[:-1])
    broken=bytearray(raw);broken[-1]^=1
    with pytest.raises(ValueError,match='ABI'):unpack(broken)
