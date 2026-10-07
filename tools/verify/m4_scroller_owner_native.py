"""Admitted native scroller to constructor request or no-player return."""
import argparse
import copy
import hashlib
import io
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_stage_queue_4086 import derive,pack,unpack
from source_model_registry import derive as registry
from source_stage_dispatch_4086 import dispatch
from source_profile import document
from PIL import Image
from m4_stage_producer_native import LUA,Request
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

INIT=r'''
 set('SourceScrollerOwner4086_Ready',0xb5dd);set('SourceScrollerOwner4086_State',0)
 set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_State',0);set('SourceScrollerPrefix4086_AdvanceTime',c.advance,4);set('SourceScrollerPrefix4086_FreezeAll',c.freeze,4);set('SourceScrollerPrefix4086_Completed',c.completed,4)
 set('SourceStageCompletion4086_Ready',0xb5d8);set('SourceStageCompletion4086_LevelType',0,4)
 set('SourceWait4086_Ready',0xb5d9);set('SourceWait4086_Status',0);set('SourceWait4086_NoReset',0,4);set('SourceWait4086_SetTime',100,4);set('SourceWait4086_TimeLeft',-77,4)
 set('SourceCameraBounds4086_Ready',0xb5da);set('SourceCameraBounds4086_Status',0);set('SourceCameraBounds4086_MaxPlayers',4);set('SourceCameraBounds4086_CameraType',0)
 set('SourceCameraMotion4086_Ready',0xb5db);set('SourceCameraMotion4086_Status',0)
 for _,pair in ipairs({{'Direction',2},{'Width',c.width},{'Height',c.height},{'HRes',320},{'VRes',240},{'Rocking',0}})do set('SourceCameraMotion4086_'..pair[1],pair[2])end
 for _,pair in ipairs({{'Speed',65536},{'OffsetX',0},{'OffsetZ',0},{'MinX',0},{'MaxX',(c.width-320)*65536},{'MinZ',0},{'MaxZ',c.height*65536},{'Blockade',0}})do set('SourceCameraMotion4086_'..pair[1],pair[2],4)end
 set('SourceDefaultInit4086_Phase',6)
 for i=0,3 do put(0x43fd84+i*4,0,4)end
 if c.owner_bad=='ready'then set('SourceScrollerOwner4086_Ready',0)
 elseif c.owner_bad=='pending'then set('SourceScrollerOwner4086_State',1)
 elseif c.owner_bad=='default'then set('SourceDefaultInit4086_Phase',1)
 elseif c.owner_bad=='wait'then set('SourceWait4086_Ready',0)
 elseif c.owner_bad=='camera'then set('SourceCameraMotion4086_Ready',0)end
'''
OBS=r'''
 emu.log('SCROLLEROWNER|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceScrollerOwner4086_State)..'|'..word(sy.SourceStageQueue4086_Index)..'|'..dw(sy.SourceStageProducer4086_GroupMin)..'|'..dw(sy.SourceStageProducer4086_GroupMax)..'|'..word(sy.SourceStageProducer4086_Waiting)..'|'..dw(sy.SourceStageProducer4086_GoTime)..'|'..returned..'|'..word(sy.SourceWait4086_Status)..'|'..word(sy.SourceCameraMotion4086_Status))
'''
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);models=len(registry(source)['models']);report=derive(source);table=pack(report);unpack(table,models);rows=[];first=0
    for stage in report['stages']:
        panels=[r['values'][0]for r in document(source,stage['source_path'])['directives']if r['directive']=='panel']
        assert len(panels)==1
        with Image.open(io.BytesIO(source.read(panels[0])))as im:width,height=im.size
        records=stage['records'];limit=first+len(records)
        for index in range(len(records)+1):
            at=records[index]['at']if index<len(records)else 0
            for enemies,offset in ((0,-1),(0,0),(3,0)):
                c=dict(stage=stage['stage_id'],first=first,limit=limit,index=first+index,pos=at+offset,enemies=enemies,minimum=100,maximum=100,state=0,completed=0,bad='',owner_bad='',fault=0,advance=47,freeze=0,width=width,height=height)
                s=dict(index=index,groupmin=100,groupmax=100,pos=c['pos'],waiting=0,go_time=77,completed=0,time=48,advancetime=47,freezeall=0,players=[None]*4,leveltype=0)
                requested=False
                def spawn(row,pool):raise Request()
                try:dispatch(s,records,[dict(exists=1,type=2,dead=0)]*enemies,spawn)
                except Request:requested=True
                if not requested and s['waiting']and not enemies:s['waiting']=0;s['go_time']=648
                c['expected']=[1 if requested else 4,first+s['index'],s['groupmin'],s['groupmax'],s['waiting'],s['go_time'],int(requested),0 if requested else 2,0 if requested else 2];rows.append(c)
        first=limit
    base=dict(rows[1])
    for field,value in (('freeze',1),('freeze',65536),('advance',49),('completed',1)):
        c=dict(base,**{field:value});c['expected']=[4,c['index'],100,100,0,77,0,4,4];rows.append(c)
    for bad in ('ready','pending','default','wait','camera'):rows.append(dict(base,owner_bad=bad,fault=1))
    for bad in ('ready','world','queue','stage','ctor','music'):rows.append(dict(base,bad=bad,fault=1))
    sy=symbols(Path('src/main.sym'));lua=LUA.replace(' before={};for _,r',INIT+'\n before={};for _,r')
    start=lua.index(" emu.log('PRODUCER|");end=lua.index('\nend,emu.callbackType.exec,RESULT',start);lua=lua[:start]+OBS+lua[end:]
    for k,v in dict(MODELS=models,RECORDS=sum(len(s['records'])for s in report['stages']),STAGES=len(report['stages']),TABLEBYTES=len(table)).items():lua=lua.replace(k,str(v))
    entry=sy['SourceScrollerOwner4086_Begin'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-SCROLLER-OWNER',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceScrollerOwner4086_Begin','SourceScrollerOwner4086_Ready',0xb5dd,[(59,0,table)],lua,r,batch_size=2)
    results=[list(map(int,line.split('SCROLLEROWNER|',1)[1].split('|')))for line in log.splitlines()if 'SCROLLEROWNER|'in line]
    r.check('real scroller prefix/completion/queue/WAIT/bounds/camera until constructor request, readonly CPU/entities and skipped-prefix guards',len(results)==len(rows)and all(v[:3]==[i,0,0]and(v[3]==3 if c['fault']else v[3:]==c['expected'])for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_SCROLLER_OWNER_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),no_player_return_only=True,constructor_handoff_only=True,constructor_resume_bound=False,full_world_backend_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
