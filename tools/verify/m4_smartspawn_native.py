"""Bounded post-constructor properties; constructor and audio leases instrumented."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_smartspawn_4086 import post
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local ranges={{0x414000,10240},{0x40c000,12288},{0x416800,8192},{0x433800,8192}}
local before={}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0,mt)end end
 local v=0x414000+c.slot*80;local b=0x433800+c.slot*64;local core=0x40c000+c.slot*96
 put(v,0x414000+c.slot*80,4);put(v+4,1,4);put(v+36,111,4);put(v+68,222,4);put(core+60,222,4);put(core+72,2,4)
 local nextslot=0
 for i=1,c.players do if nextslot==c.slot then nextslot=nextslot+1 end;put(0x414004+nextslot*80,1,4);put(0x40c048+nextslot*96,1,4);nextslot=nextslot+1 end
 for i=1,5 do emu.write(b+i-1,string.byte('fresh',i),mt)end
 put(b+48,c.current_map);put(b+50,0);put(b+56,-9,4);put(b+62,0xb5c2)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128);set('VmSourceWorld_TemplateCount',16)
 set('SourceCtorOwner4086_Phase',2);set('SourceCtorOwner4086_Model',0);set('SourceDefaultInit4086_Phase',6);set('SourceDefaultInit4086_OwnerSlot',c.slot)
 set('SourceAnimationInit4086_Ready',0);set('SourceAnimationInit4086_State',0);set('SourceUpdateFrame4086_Ready',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceStageQueue4086_Ready',0xb5d2);set('SourceStageQueue4086_Status',2);set('SourceStageQueue4086_Bank',59);set('SourceStageQueue4086_Base',0x8000);set('SourceStageQueue4086_Row',24+c.record*128)
 set('SourceSmartSpawn4086_Ready',0xb5d4);set('SourceSmartSpawn4086_Status',0);set('SourceSmartSpawn4086_MapModel',0);set('SourceSmartSpawn4086_MapsLoaded',c.maps_loaded);set('SourceSmartSpawn4086_BossMusic',c.music)
 if c.bad=='ready'then set('SourceSmartSpawn4086_Ready',0)
 elseif c.bad=='pending'then set('SourceSmartSpawn4086_Status',1)
 elseif c.bad=='model'then set('SourceSmartSpawn4086_MapModel',1)
 elseif c.bad=='ctor'then set('SourceCtorOwner4086_Phase',1)
 elseif c.bad=='queue'then set('SourceStageQueue4086_Status',0)
 elseif c.bad=='body'then put(b+62,0)
 elseif c.bad=='music'then set('SourceSmartSpawn4086_BossMusic',2)
 elseif c.bad=='players'then put(0x414004+10*80,1,4);put(0x40c048+10*96,1,4)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local b=0x433800+c.slot*64;local v=0x414000+c.slot*80;local core=0x40c000+c.slot*96
 local function expect(a,value,n)for i=0,n-1 do before[a+i]=(value>>(8*i))&255 end end
 if c.fault==0 then
  if c.alias~=''then for i=0,47 do before[b+i]=i<#c.alias and string.byte(c.alias,i+1)or 0 end end
  expect(v+36,c.expected.health,4);expect(v+68,c.expected.model_health,4);expect(core+60,c.expected.model_health,4)
  expect(b+48,c.expected.map,2);expect(b+56,c.expected.boss,4);expect(b+60,1,2)
 end
 local n=0;for a,value in pairs(before)do if emu.read(a,mt)~=value then n=n+1 end end
 emu.log('SMARTNATIVE|'..word(INDEX)..'|'..n..'|'..word(sy.SourceSmartSpawn4086_Status)..'|'..word(sy.SourceSmartSpawn4086_Players))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
    records=[];lookup={};rows=[]
    for i,c in enumerate(authority['inputs']):
        r=c['row'];identity=json.dumps([r['health'],r['map'],r['boss'],r['alias']])
        if identity not in lookup:
            lookup[identity]=len(records);data=bytearray(128)
            struct.pack_into('<4i',data,28,*r['health']);struct.pack_into('<2i',data,44,r['map'],r['boss']);struct.pack_into('<H',data,60,len(r['alias']));data[64:112]=r['alias'].encode().ljust(48,b'\0');records.append(bytes(data))
        e=dict(name='fresh',health=111,model_health=222,map=c['current_map'],palette=c['current_map'],boss=-9,spawntype=0)
        trace=post(e,r,c['players'],c['maps_loaded'],c['music'])
        rows.append(dict(c,alias=r['alias'],record=lookup[identity],slot=127 if i%2 else 0,bad='',fault=0,expected=e,status=1 if 'BOSS_MUSIC'in trace else 2))
    for bad in ('ready','pending','model','ctor','queue','body','music','players'):
        rows.append(dict(rows[-1],players=4,bad=bad,fault=1,status=3))
    table=bytes(24)+b''.join(records);assert len(table)<32768
    from actor_s5_entity_fixture import symbols
    sy=symbols(Path('src/main.sym'));lua=LUA
    for name in [k for k in sy if k.startswith('SourceSmartSpawn4086_G') or k in ('SourceSmartSpawn4086_Bad','SourceCtorOwner4086_Bad')]:
        address=sy[name];lua+=f"emu.addMemoryCallback(function()if word(INDEX)==0 then emu.log('SMARTGUARD|{name}|'..emu.getState()['cpu.a'])end end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-SMARTSPAWN',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceSmartSpawn4086_Apply','SourceSmartSpawn4086_Ready',0xb5d4,[(59,0,table)],lua,r,batch_size=2,frame_limit=6000)
    (a.output/'observer.log').write_text(log)
    results=[list(map(int,line.split('SMARTNATIVE|',1)[1].split('|')))for line in log.splitlines()if 'SMARTNATIVE|'in line]
    r.check('C-paired aliases/health/maps/boss, explicit pending music and unchanged entity bytes on admission faults',len(results)==len(rows)and all(v[:3]==[i,0,c['status']]for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_SMARTSPAWN_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),constructor_ticket_instrumented=True,source_palette_descriptor_instrumented=True,palette_upload_bound=False,music_service_executed=False,live_queue_dispatch_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
