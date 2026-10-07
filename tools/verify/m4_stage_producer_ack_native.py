"""Queue acknowledgement guards after completed construction/property tickets."""
import argparse
import hashlib
import json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from m4_ctor_result_native import LUA as RESULT_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=RESULT_LUA.replace("set('SourceCtorOwner4086_Phase',c.phase)","""
 set('SourceStageProducer4086_Ready',0xb5d6);set('SourceStageProducer4086_State',1)
 set('SourceStageProducer4086_Kind',c.model==65535 and 0 or 1);set('SourceStageProducer4086_RequestIndex',10)
 set('SourceStageQueue4086_Index',10);set('SourceStageQueue4086_Model',0)
 put(sy.VmSourceWorld_Time,48,4);put(sy.SourceStageProducer4086_Time,48,4)
 set('SourceSmartSpawn4086_Ready',0xb5d4);set('SourceSmartSpawn4086_Status',2);set('SourceSmartSpawn4086_MapModel',0)
 set('SourceCtorOwner4086_Phase',c.phase)""")
LUA=LUA.replace("elseif c.bad=='empty'then","""
 elseif c.bad=='producer_ready'then set('SourceStageProducer4086_Ready',0)
 elseif c.bad=='producer_state'then set('SourceStageProducer4086_State',c.value)
 elseif c.bad=='index'then set('SourceStageQueue4086_Index',11)
 elseif c.bad=='time'then put(sy.VmSourceWorld_Time,49,4)
 elseif c.bad=='queue_model'then set('SourceStageQueue4086_Model',1)
 elseif c.bad=='property_ready'then set('SourceSmartSpawn4086_Ready',0)
 elseif c.bad=='property_model'then set('SourceSmartSpawn4086_MapModel',1)
 elseif c.bad=='property_pending'then set('SourceSmartSpawn4086_Status',1)
 elseif c.bad=='kind'then set('SourceStageProducer4086_Kind',2)
 elseif c.bad=='empty'then""")
LUA=LUA.replace("before={};for i=0,7", "before={};for i=0,7")
start=LUA.index(" local c=rows[word(INDEX)+1]\n if c.fault==0 then",LUA.index('callbackType.exec,AFTER'))
end=LUA.index(" local n=0;",start)
LUA=LUA[:start]+LUA[start:end].replace(" if c.fault==0 then"," if c.publish then")+LUA[end:]
LUA=LUA.replace("emu.log('CTORRESULT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceCtorOwner4086_Phase)..'|'..v)","emu.log('PRODUCERACK|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceStageProducer4086_State)..'|'..word(sy.SourceStageQueue4086_Index))")

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    base=dict(slot=0,level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=0,phase=2,model=0,value=0,publish=True)
    rows=[dict(base,slot=slot,alive=alive)for slot in (0,1,127)for alive in (0,1)];rows.append(dict(base,model=65535))
    before_result={'producer_ready','producer_state','index','time','owner_phase','model_pair','token','frame_pending'}
    for bad in ('producer_ready','producer_state','index','time','queue_model','property_ready','property_model','property_pending','kind','owner_phase','model_pair','token','frame_pending'):
        rows.append(dict(base,bad=bad,value=0,fault=1,publish=bad not in before_result))
    sy=symbols(Path('src/main.sym'));lua=LUA;entry=sy['SourceStageProducer4086_AckSpawn'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-STAGE-PRODUCER-ACK',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceStageProducer4086_AckSpawn','SourceStageProducer4086_Ready',0xb5d6,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('PRODUCERACK|',1)[1].split('|')))for line in log.splitlines()if 'PRODUCERACK|'in line]
    r.check('advance only after complete live/dead/null constructor and paired properties/music; entity bytes and CPU context preserved',len(results)==len(rows)and all(v==[i,0,0,3 if c['fault']else 2,(11 if c['bad']=='index'else 10)if c['fault']else 11]for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_STAGE_PRODUCER_ACK_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),constructor_and_property_completion_instrumented=True,actual_music_execution_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
