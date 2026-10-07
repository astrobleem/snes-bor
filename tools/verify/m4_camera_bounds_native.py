"""Native camera role bounds paired with literal pinned C player loops."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local cpu={};local before={};local ctx=0;local returned=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('SourceCameraBounds4086_Ready',0xb5da);set('SourceCameraBounds4086_Status',0);set('SourceCameraBounds4086_MaxPlayers',c.maxplayers);set('SourceCameraBounds4086_CameraType',c.cameratype)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000)
 for i=0,3 do put(0x43fd84+i*4,0,4)end
 for i,p in ipairs(c.players)do if p.live==1 then
  local v=0x414000+p.slot*80;put(0x43fd84+(i-1)*4,v,4);put(v,v,4)
  put(v+4,0,4);put(0x439014+p.slot*80,65536,4);put(0x40c048+p.slot*96,0,4)
  put(v+48,2,4);put(v+52,p.x,4);put(v+56,2,4);put(v+60,p.z,4);put(v+8,2,4);put(v+12,p.a,4)
 end end
 local first=c.players[1];local v=0x414000+first.slot*80
 if c.bad=='ready'then set('SourceCameraBounds4086_Ready',0)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',0)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='role_bank'then put(0x43fd84,0x424000,4)
 elseif c.bad=='role_low'then put(0x43fd84,0x413fff,4)
 elseif c.bad=='role_end'then put(0x43fd84,0x416800,4)
 elseif c.bad=='role_align'then put(0x43fd84,0x414001,4)
 elseif c.bad=='token'then put(v,v+80,4)
 elseif c.bad=='slot_count'then set('VmSourceWorld_Count',1)
 elseif c.bad=='x_tag'then put(v+48,1,4)
 elseif c.bad=='z_tag'then put(v+56,1,4)
 elseif c.bad=='a_tag'then put(v+8,1,4)
 elseif c.bad=='ignored_role'then put(0x43fd90,0x424001,4)end
 before={};for _,r in ipairs({{0x414000,10240},{0x40c000,12288},{0x439000,10240},{0x43fd84,16}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();returned=s['cpu.a'];ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('CAMERABOUNDS|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceCameraBounds4086_Status)..'|'..returned..'|'..dw(sy.SourceCameraBounds4086_RM)..'|'..dw(sy.SourceCameraBounds4086_LM)..'|'..dw(sy.SourceCameraBounds4086_BM)..'|'..dw(sy.SourceCameraBounds4086_TM))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    camera=json.loads(a.authority.read_text());assert camera['status']=='PASS';cases=camera['inputs'];sample=cases[::67]+cases[-192:];rows=[]
    for i,c in enumerate(sample):
        players=[]
        for j,role in enumerate(c['players']):
            p=role or dict(x=0,z=0,a=0)
            players.append(dict(live=int(role is not None),slot=(127,0,63,1)[j],**{k:int(p[k]*65536)for k in ('x','z','a')}))
        rows.append(dict(maxplayers=c['maxplayers'],cameratype=c['cameratype'],players=players,bad='',fault=0))
    # Near Q16 limits and original -9999 lower-bound sentinel.
    for camera_type in (0,1):
        for values in ((-9999,-9999,0),(-12000,-12000,0),(32767.5,-32768,0),(-32768,32767.5,0),(0,10.25,5.5)):
            rows.append(dict(maxplayers=1,cameratype=camera_type,players=[dict(live=1,slot=127,**{k:int(v*65536)for k,v in zip(('x','z','a'),values)})]+[dict(live=0,slot=0,x=0,z=0,a=0)]*3,bad='',fault=0))
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');full=extract(raw,'update_scroller');start=full.index('    for(i = 0;');end=full.index('    if(level->waiting)',start);role_block=full[start:end]
    start=full.index('        if(cameratype == 1)');end=full.index('        if(bm - tm >',start);altitude_block=full[start:end]
    crows=[]
    for r in rows:
        players=['{'+','.join(map(str,[p['live'],p['x']/65536,p['z']/65536,p['a']/65536]))+'}'for p in r['players']]
        crows.append('{'+str(r['maxplayers'])+','+str(r['cameratype'])+',{'+','.join(players)+'}}')
    code=r'''#include <stdio.h>
typedef struct {float x,z,y;} Position;typedef struct {Position position;} Entity;typedef struct {Entity *ent;} Player;
Entity ents[4];Player player[4];struct {int maxplayers;} levelsets[1];int current_set=0,cameratype;
struct {int maxplayers,cameratype;struct {int live;float x,z,a;} players[4];} cases[]={'''+','.join(crows)+r'''};
int main(void){unsigned n;int i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
float rm=-9999,lm=999999,bm=-9999,tm=999999;int numplay=0;levelsets[0].maxplayers=cases[n].maxplayers;cameratype=cases[n].cameratype;
for(i=0;i<4;i++){player[i].ent=cases[n].players[i].live?ents+i:0;ents[i].position.x=cases[n].players[i].x;ents[i].position.z=cases[n].players[i].z;ents[i].position.y=cases[n].players[i].a;}
'''+role_block+altitude_block+r'''
printf("%d,%d,%d,%d,%d\n",numplay,(int)(rm*65536),numplay?(int)(lm*65536):2147483647,(int)(bm*65536),numplay?(int)(tm*65536):2147483647);
}return 0;}
'''
    (a.output/'bounds.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','bounds.c','-fe=bounds.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('CAMERA_BOUNDS_AUTHORITY_BUILD')
    log=subprocess.check_output([str(a.output/'bounds.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);values=[list(map(int,line.split(',')))for line in log.splitlines()]
    for r,v in zip(rows,values):r['expected']=[v[0],*[n&0xffffffff for n in v[1:]]]
    base=dict(rows[-1],players=[dict(live=1,slot=127,x=80*65536,z=220*65536,a=0)]+[dict(live=0,slot=0,x=0,z=0,a=0)]*3,cameratype=1)
    for bad in ('ready','world','count','pool','role_bank','role_low','role_end','role_align','token','slot_count','x_tag','z_tag','a_tag'):rows.append(dict(base,bad=bad,fault=1))
    for field,value in (('maxplayers',0),('maxplayers',5),('cameratype',2)):rows.append(dict(base,**{field:value},fault=1))
    rows.append(dict(base,players=[dict(live=1,slot=127,x=0,z=32767*65536,a=-65536)]+base['players'][1:],fault=1))
    rows.append(dict(base,bad='ignored_role',expected=[1,80*65536,80*65536,220*65536,220*65536]))
    sy=symbols(Path('src/main.sym'));entry=sy['SourceCameraBounds4086_Collect'];lua=LUA+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-CAMERA-BOUNDS',kind='GATE');rom,log=run_fixture(a.rom,a.output,rows,'SourceCameraBounds4086_Collect','SourceCameraBounds4086_Ready',0xb5da,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('CAMERABOUNDS|',1)[1].split('|')))for line in log.splitlines()if 'CAMERABOUNDS|'in line]
    r.check('literal C role/altitude bounds, four roles and pool edge slots, ignored dead/type/existence, readonly CPU/entities and guards',len(results)==len(rows)and all(v[:3]==[i,0,0]and(v[3]==3 if c['fault']else v[3]==2 and v[4:]==c['expected'])for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_CAMERA_BOUNDS_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,engine_commit=ENGINE_COMMIT,role_block_sha256=hashlib.sha256(role_block.encode()).hexdigest(),altitude_block_sha256=hashlib.sha256(altitude_block.encode()).hexdigest(),rom_sha256=hashlib.sha256(rom).hexdigest(),numeric_policy='Admitted Q16 coordinates; no-player min sentinel INT_MAX is unused, source 999999 sentinel outside admitted coordinates; altitude overflow fails explicitly',native_camera_motion_bound=False,moving_rendering_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
