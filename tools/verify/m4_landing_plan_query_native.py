"""Native identity-bound landing metadata, every source animation and fault fences."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from m4_animation_physics_query_native import LUA as PHYSICS_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=PHYSICS_LUA.replace('SourceAnimationPhysics4086_','SourceLandingPlan4086_').replace('0xb61f','0xb625')
LUA=LUA.replace("set('Frame',c.frame)","set('Model',c.model)")
LUA=LUA.replace('0x41ff10,0x41ff29','0x41ffd2,0x41ffdd').replace('{0x41fef0,0x41ff50}','{0x41ffb2,0x41ffee}')
LUA=LUA.replace('for i=1,6','for i=1,3').replace('dw(0x41ff10+(i-1)*4)','dw(0x41ffd2+(i-1)*4)')
LUA=LUA.replace(" if word(0x41ff28)~=(c.fault==1 and 0xa5a5 or c.count)then mismatches=mismatches+1 end\n",'')
LUA=LUA.replace("'ANIMPHYS|'","'LANDPLAN|'").replace('word(0x41ff02)','word(0x41ffc4)')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--table',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    data=a.table.read_bytes();magic,version,count,size,*reserved=struct.unpack_from('<4s6H',data)
    assert (magic,version,size,reserved)==(b'B4LP',1,16,[0,0,0]) and len(data)==16+16*count
    rows=[]
    for index in range(count):
        handle,model,factor,bounce,noquake=struct.unpack_from('<HHI i I',data,16+index*16)
        rows.append(dict(handle=handle,model=model,expected=[factor,bounce,noquake],fault=0))
    rows.append(dict(rows[-1],base=65536-len(data),bank=59))
    for name,value in (('Ready',0),('Ready',0xb626),('Status',2),('Status',3),('Bank',64),('Bank',126),('Bank',256),
                       ('Bytes',15),('Bytes',len(data)-2),('Animations',0),('Animations',129),('Animations',count-1),
                       ('Handle',0),('Handle',count+1),('Model',128),('Model',127),('Base',0x7fff),('Base',0xfff1),('Base',0xff00)):
        rows.append(dict(rows[0],bad=name,value=value,fault=1))
    payloads=[(58,0,data),(59,32768-len(data),data)]
    for number,(offset,value)in enumerate(((0,0),(4,2),(8,8),(10,1),(16,2),(18,127),(20,0x7f800000),(28,4),(30,1))):
        changed=bytearray(data);struct.pack_into('<I'if offset==20 else'<H',changed,offset,value)
        at=0x1000+number*0x800;payloads.append((58,at,changed));rows.append(dict(rows[0],base=0x8000+at,fault=1))
    reporter=Reporter('M4-LANDING-PLAN-QUERY',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceLandingPlan4086_Query','SourceLandingPlan4086_Ready',0xb625,
                        payloads,LUA.replace('TABLEBYTES',str(len(data))).replace('ANIMATIONCOUNT',str(count)),reporter,batch_size=8)
    actual=[list(map(int,l.split('LANDPLAN|',1)[1].split('|')))for l in log.splitlines()if 'LANDPLAN|'in l]
    wanted=[[i,0,0,3 if r['fault']else 2]for i,r in enumerate(rows)]
    reporter.check('every authored animation/model landing identity; malformed/foreign metadata never publishes; CPU and adjacent scratch preserved',actual==wanted)
    report=dict(schema='BYOR_4086_LANDING_PLAN_QUERY_NATIVE_V1',status='PASS'if actual==wanted else'FAIL',cases=len(rows),
                authored_animation_rows=count,inputs=rows,actual=actual,expected=wanted,compiled_table_sha256=hashlib.sha256(data).hexdigest(),
                rom_sha256=hashlib.sha256(raw).hexdigest(),scratch_domain='41FFC2..41FFED',
                native_landing_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
