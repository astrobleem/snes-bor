"""Pack a source sound namespace into a bounded SA-1 E-bank ROM window.

ASAD1 rows preserve namespace indices and describe byte-addressed BRR sources:
24-bit SNES address, 24-bit meaningful length, 16-bit transport chunk count.
The 144-byte transfer tail is explicit zero padding, outside meaningful BRR.
No actor identities appear in allocation or addressing decisions.
"""
import argparse,hashlib,json,math,struct
from pathlib import Path

CPU_BASE=0xe00000
ROM_BASE=0x200000
CAPACITY=0x100000
MAGIC=b'ASAD'
MAX_NAMESPACE=(0x4000-8)//8  # Fixed $3C:C000 descriptor reservation.


def unpack(table):
    if len(table)<8:raise ValueError('ASAD_TRUNCATED_HEADER')
    magic,version,count=struct.unpack_from('<4sHH',table)
    if count>MAX_NAMESPACE:raise ValueError('ASAD_NAMESPACE_COUNT')
    if magic!=MAGIC or version!=1 or len(table)!=8+8*count:
        raise ValueError('ASAD_HEADER_OR_LENGTH')
    result=[];end=CPU_BASE
    for i in range(count):
        at=8+i*8
        pointer=int.from_bytes(table[at:at+3],'little')
        length=int.from_bytes(table[at+3:at+6],'little')
        chunks=int.from_bytes(table[at+6:at+8],'little')
        if not length or length%9 or chunks!=math.ceil(length/144):
            raise ValueError('ASAD_BRR_LENGTH_OR_CHUNKS')
        if pointer<end or pointer+chunks*144>CPU_BASE+CAPACITY:
            raise ValueError('ASAD_OVERLAP_OR_ROM_WINDOW')
        result.append(dict(sound_index=i,cpu_pointer=pointer,brr_bytes=length,chunks=chunks))
        end=pointer+chunks*144
    return result


def pack(folder,output,*,cpu_base=CPU_BASE):
    if not CPU_BASE<=cpu_base<CPU_BASE+CAPACITY or cpu_base%65536:
        raise ValueError('ASAD_ROM_WINDOW_BASE')
    capacity=CPU_BASE+CAPACITY-cpu_base
    rom_base=ROM_BASE+cpu_base-CPU_BASE
    manifest=json.loads((folder/'report.json').read_text())
    rows=sorted(manifest['compiled'],key=lambda r:r['sound_index'])
    if [r['sound_index']for r in rows]!=list(range(len(manifest['namespace']))):
        raise ValueError('ASAD_INCOMPLETE_NAMESPACE')
    if len(rows)>MAX_NAMESPACE:raise ValueError('ASAD_NAMESPACE_COUNT')
    table=bytearray(struct.pack('<4sHH',MAGIC,1,len(rows)));data=bytearray();assets=[]
    for row in rows:
        brr=(folder/row['brr_path']).read_bytes()
        if len(brr)!=row['brr_bytes'] or hashlib.sha256(brr).hexdigest()!=row['brr_sha256']:
            raise ValueError('ASAD_ASSET_IDENTITY')
        if not brr or len(brr)%9 or any(brr[i]&3 for i in range(0,len(brr)-9,9))or brr[-9]&3!=1:
            raise ValueError('ASAD_BRR_END_OR_LOOP')
        count=math.ceil(len(brr)/144);start=len(data)
        if count>65535 or start+count*144>capacity:raise ValueError('ASAD_ROM_CAPACITY')
        pointer=cpu_base+start
        table.extend(pointer.to_bytes(3,'little'));table.extend(len(brr).to_bytes(3,'little'));table.extend(struct.pack('<H',count))
        data.extend(brr);data.extend(bytes(count*144-len(brr)))
        assets.append(dict(sound_index=row['sound_index'],source_path=row['source_path'],
            cpu_pointer=pointer,rom_offset=rom_base+start,brr_bytes=len(brr),
            transfer_bytes=count*144,tail_padding_bytes=count*144-len(brr),
            crosses_64k_bank=(pointer>>16)!=((pointer+len(brr)-1)>>16),
            brr_sha256=row['brr_sha256'],source_sha256=row['source_sha256']))
    parsed=unpack(table)
    assert [r['brr_bytes']for r in parsed]==[r['brr_bytes']for r in assets]
    output.mkdir(parents=True,exist_ok=True)
    (output/'descriptors.bin').write_bytes(table);(output/'payload.bin').write_bytes(data)
    report=dict(schema='BYOR_SOURCE_AUDIO_ROM_V1',status='PASS',namespace=manifest['namespace'],
        descriptor_sha256=hashlib.sha256(table).hexdigest(),payload_sha256=hashlib.sha256(data).hexdigest(),
        descriptor_bytes=len(table),payload_bytes=len(data),meaningful_brr_bytes=sum(r['brr_bytes']for r in rows),
        rom_window_base=rom_base,cpu_window_base=cpu_base,capacity_bytes=capacity,
        source_frame_table_sha256=manifest['source_frame_table_sha256'],assets=assets,
        requires_sa1_exb_mapping=2,fxb_mapping_consumed=False,native_runtime_proven=False,
        source_audio_policy='ACCEPTED_COMPAT full-duration mono PCM_u8/11025Hz then BRR',
        no_pcm_copies=True,no_color_reduction=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def install(raw,table,data,descriptor_offset,*,cpu_base=CPU_BASE):
    """Install only into measured empty, disjoint ROM reservations."""
    unpack(table)
    if not CPU_BASE<=cpu_base<CPU_BASE+CAPACITY or cpu_base%65536:
        raise ValueError('ASAD_ROM_WINDOW_BASE')
    rom_base=ROM_BASE+cpu_base-CPU_BASE
    if len(raw)<ROM_BASE+CAPACITY:raise ValueError('ASAD_ROM_TOO_SMALL')
    if not 0<=descriptor_offset<=ROM_BASE-len(table):raise ValueError('ASAD_DESCRIPTOR_RESERVATION')
    if len(data)>CPU_BASE+CAPACITY-cpu_base:raise ValueError('ASAD_ROM_CAPACITY')
    for start,payload in [(descriptor_offset,table),(rom_base,data)]:
        if raw[start:start+len(payload)]!=bytes(len(payload)):
            raise ValueError('ASAD_RESERVATION_NOT_EMPTY')
    # Validate payload extents and final padding before modifying the image.
    for row in unpack(table):
        at=row['cpu_pointer']-cpu_base;length=row['brr_bytes'];end=at+row['chunks']*144
        if at<0 or end>len(data)or any(data[at+length:end]):raise ValueError('ASAD_TRANSFER_PADDING')
    raw[descriptor_offset:descriptor_offset+len(table)]=table
    raw[rom_base:rom_base+len(data)]=data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--cpu-base',type=lambda s:int(s,0),default=CPU_BASE,help='Bank-aligned E-window reservation')
    a=p.parse_args();r=pack(a.assets,a.output,cpu_base=a.cpu_base)
    print('ASAD:',len(r['assets']),'sources;',r['payload_bytes'],'ROM bytes')


if __name__=='__main__':main()
