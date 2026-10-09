"""Native release, actual immutable body/query owners, instrumented sound result.

This checks the real animation Begin up to frame-zero pending. It does not claim
physical source audio or execution of the pending frame callback.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_player_release_profile import derive as release
from source_player_release_native import emit
from source_attack_body_profile import derive as bodies,pack_runtime
from source_animation_init_4086 import derive as animations,pack as pack_animations
from source_frame_effects_4086 import derive as effects,pack as pack_effects
from source_model_switch_requirements import derive as models,pack_animation_cache
from source_animation_ids import configure,role_id
from source_profile import document
from source_u32_float_threshold_4086 import compare
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter
W,H,O=0x7fa400,0x7fa000,0x7fa480
ASM='''
ReleaseProbe:
.a16
.i16
 php
 sed
 jsl PlayerRelease_Begin
ReleaseProbe_BeginReturn:
.a16
.i16
 bcs ReleaseProbe_Bad
 lda.l W+2
 cmp #3
 bne ReleaseProbe_Done
ReleaseProbe_Sound:
.a16
.i16
 nop
 jsl PlayerRelease_FinishSound
ReleaseProbe_SoundReturn:
.a16
.i16
 bcs ReleaseProbe_Bad
ReleaseProbe_Done:
.a16
.i16
 plp
 clc
 rtl
ReleaseProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v)put(sy[k],v)end
local function blob(a,hex)for i=1,#hex,2 do emu.write(a+(i-1)//2,tonumber(hex:sub(i,i+1),16),mt)end end
local before,cpu,trace,start,errors,prefix,decimal,sounds={}, {},{},0,0,-1,0,0
local ranges={{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x439000,10240},{0x43eb00,4096},{0x437e00,2560},{0x42e000,5120},{H,1024}}
local function body(slot,model)
 local at=slot<96 and 0x435980+slot*11 or 0x40bdcc+(slot-96)*11
 blob(at,BODIES[model+1]);put(at+9,0xb605);return at
end
local function check(c,active)
 local wanted={};for a,v in pairs(before)do wanted[a]=v end
 local function expect(a,v)for j=0,3 do wanted[a+j]=(v>>(8*j))&255 end end
 if c.release&64~=0 and c.initial_fault==0 then
  if active then
   expect(0x43900c+c.slot*80,17);expect(0x40c058+c.slot*96,1);expect(0x43eb00+c.slot*32,0)
   expect(0x437e08+c.slot*20,0);expect(0x416824+c.slot*64,0);expect(0x416828+c.slot*64,0)
  end
  if c.fault==0 or active then expect(0x42e008+c.slot*40,0)end
 end
 if sounds>0 and c.mutation==1 then
  local side=0x416800+c.slot*64;wanted[side]=c.to_model;wanted[side+1]=0
  expect(0x42e008+c.slot*40,99);expect(0x43eb00+c.slot*32,-9);expect(0x437e08+c.slot*20,7)
 end
 local n=0;for a,v in pairs(wanted)do if emu.read(a,mt)~=v then n=n+1;if n<4 then emu.log('RELEASEBYTE|'..word(INDEX)..'|'..string.format('%06X',a)..'|'..v..'|'..emu.read(a,mt))end end end
 return n
end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];errors=0;prefix=-1;decimal=0;sounds=0;trace={}
 for _,r in ipairs(ranges)do for j=0,r[2]-1 do put(r[1]+j,0,1)end end
 for j=0,127 do put(W+j,0,1)end;blob(0x43c000,CACHE)
 put(W,0xb68f);put(W+4,c.slot);put(W+6,c.port);put(W+8,c.notinair);put(W+12,c.sample,4);put(O,0xb674)
 put(H+256*c.port+228,c.release,4)
 local v=0x414000+c.slot*80;put(v,v,4);put(v+16,1);put(v+20,0,4)
 put(0x416800+c.slot*64,c.model);put(0x416804+c.slot*64,0)
 put(0x416824+c.slot*64,2<<16,4);put(0x416828+c.slot*64,3<<16,4)
 put(0x43900c+c.slot*80,9,4);put(0x43904a+c.slot*80,0xb4fb)
 put(0x40c058+c.slot*96,-5,4);put(0x43eb00+c.slot*32,7,4)
 put(0x437e08+c.slot*20,3,4);put(0x437e0c+c.slot*20,123,4);put(0x437e10+c.slot*20,0xb5fb)
 put(0x42e008+c.slot*40,c.stall,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000)
 set('SourceClock4086_Ready',0xb4c5);put(sy.SourceClock4086_TimeLo,c.time,4);set('SourceWorldTick4086_Ready',0)
 set('SourceFreeze4086_Ready',0xb5df)
 set('SourceAttackBody4086_Ready',0xb605);set('SourceAttackBody4086_Status',0);set('SourceAttackBody4086_Bank',58);set('SourceAttackBody4086_Base',0x8000);set('SourceAttackBody4086_Bytes',BODYBYTES)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',16)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_Bytes',5376)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Base',0x8000);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',AIBYTES);set('SourceAnimationInit4086_Issued',0)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FEBYTES);set('SourceUpdateFrame4086_Animations',HANDLES)
 local at=body(c.slot,c.model)
 if c.bad=='ready'then put(W,0)elseif c.bad=='busy'then put(W+2,3)elseif c.bad=='input'then put(O,0)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)elseif c.bad=='slot'then put(W+4,128)
 elseif c.bad=='port'then put(W+6,4)elseif c.bad=='clock'then set('SourceClock4086_Ready',0)
 elseif c.bad=='freeze'then set('SourceFreeze4086_Ready',0)elseif c.bad=='body'then put(at+9,0)
 elseif c.bad=='life'then put(0x43904a+c.slot*80,0)elseif c.bad=='combat'then put(0x437e10+c.slot*20,0)
 elseif c.bad=='token'then put(v,0x4001)end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 put(EXPECTFAULT,c.fault);local st=emu.getState();start=st.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];prefix=check(c,true);sounds=sounds+1
 put(W+42,c.ack)
 if c.mutation==1 then
  put(0x416800+c.slot*64,c.to_model);body(c.slot,c.to_model)
  put(0x42e008+c.slot*40,99,4);put(0x43eb00+c.slot*32,-9,4);put(0x437e08+c.slot*20,7,4)
 end
end,emu.callbackType.exec,SOUND,SOUND,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()trace[#trace+1]=word(sy.SourceAnimationInit4086_Number)end,emu.callbackType.exec,sy.SourceAnimationInit4086_Resolve,sy.SourceAnimationInit4086_Resolve,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()errors=errors+check(rows[word(INDEX)+1],true)end,emu.callbackType.exec,PREFIX,PREFIX,emu.cpuType.snes,mt)
for _,address in ipairs({BEGINRETURN,SOUNDRETURN})do emu.addMemoryCallback(function()if emu.getState()['cpu.ps']&8==0 then decimal=decimal+1 end end,emu.callbackType.exec,address,address,emu.cpuType.snes,mt)end
emu.addMemoryCallback(function()
 local st=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if st['cpu.'..k]~=cpu[k]then errors=errors+1 end end
 if(st['cpu.ps']&254)~=(cpu.ps&254)then errors=errors+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];if c.active==0 or c.bad=='ack'then errors=errors+check(c,c.active==1)end
 if prefix>0 then errors=errors+prefix end
 emu.log('RELEASE|'..word(INDEX)..'|'..word(W+2)..'|'..(errors+decimal)..'|'..sounds..'|'..table.concat(trace,',')..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','rom','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);(folder/'report.json').write_text('{"status":"RUNNING"}\n')
    source=Source(a.source);rp=release(source);bp=bodies(source);ap=animations(source);fp=effects(source)
    cache=pack_animation_cache(models(source));ai=pack_animations(ap);fe=pack_effects(fp);base=pack_runtime(bp)
    charge=role_id(configure(document(source,'data/models.txt')['directives']),'chargeattack')
    rows=[]
    for slot in range(128):
        for time in (400,401,402,0xffffffff):
            model=(3,4,8,14)[slot%4];stall=(1,65536,0xffffffff)[slot%3]
            active=int(bool(compare(stall,time,rp['models'][model]['final_attack_duration'])))
            rows.append(dict(slot=slot,port=slot%4,model=model,to_model=model,release=0x80000040,notinair=1,stall=stall,time=time,sample=-1 if slot%2 else 26,ack=1,mutation=0,active=active,bad='',fault=0,initial_fault=0))
    first=next(c for c in rows if c['active'])
    for changes in (dict(release=0),dict(notinair=0),dict(stall=0),dict(sample=-1),dict(ack=2),dict(mutation=1,to_model=4),dict(mutation=1,to_model=3)):
        c=dict(first,sample=26,**{k:v for k,v in changes.items()if k!='sample'});c['sample']=changes.get('sample',26)
        c['active']=int(bool(c['release']&64 and c['notinair']and c['stall']and compare(c['stall'],c['time'],400)));rows.append(c)
    for bad in ('ready','busy','input','world','slot','port','clock','freeze','body','life','combat','token'):
        rows.append(dict(first,bad=bad,fault=1,initial_fault=1,active=0))
    rows.append(dict(first,sample=26,ack=0,bad='ack',fault=1,initial_fault=0))
    for m in rp['models']:
        if m['final_attack_duration']is None:rows.append(dict(first,model=m['id'],bad='missing',fault=1,initial_fault=0,active=0))
    for c in rows:
        q=[]
        if c['release']&64 and c['stall']and c['notinair']and (c['initial_fault']==0 or c['bad']=='body'):q=[charge,charge]
        if c['active']and c['bad']!='ack':q+=[charge,rp['models'][c['to_model']]['final_attack']]
        c['trace']=','.join(map(str,q));c['sound_count']=int(bool(c['active']and c['sample']>=0))
        c['state']=5 if c['fault']else 6 if c['active']else 2
    sy=symbols(Path('src/main.sym'));extra={k:v for k,v in sy.items()if k.startswith('SourceAttackBody4086_')}
    lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+LUA
    values=dict(W=W,H=H,O=O,CACHE=luav(cache.hex()),BODIES='('+luav([base[16+i*9:25+i*9].hex()for i in range(len(bp['models']))])+')',BODYBYTES=len(base),AIBYTES=len(ai),FEBYTES=len(fe),HANDLES=len(ap['animations']))
    for n,v in values.items():lua=re.sub(r'\b'+n+r'\b',str(v),lua)
    reporter=Reporter('M4-PLAYER-RELEASE',kind='GATE')
    raw,log=run_fixture(a.rom,folder,rows,'ReleaseProbe','SourceAnimationInit4086_Ready',0xb4ec,[(58,0,base),(59,0,ai),(60,0,fe)],lua,reporter,
        append=ASM.replace('W',str(W))+emit(W,H,O,0xb674,rp,bp,charge,sy),probes=dict(SOUND='ReleaseProbe_Sound',PREFIX='PlayerRelease_BeforeAnimation',BEGINRETURN='ReleaseProbe_BeginReturn',SOUNDRETURN='ReleaseProbe_SoundReturn'),batch_size=2,frame_limit=900,link_pcm=False)
    observed=[l.split('RELEASE|',1)[1].strip().split('|')for l in log.splitlines()if 'RELEASE|'in l]
    errors=[dict(case=i,input=rows[i],actual=v)for i,v in enumerate(observed)if v[:5]!=[str(i),str(rows[i]['state']),'0',str(rows[i]['sound_count']),rows[i]['trace']]]
    reporter.check('canonical release writes, source query order, mandatory sound continuation, fresh model and actual animation Begin',len(observed)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_PLAYER_RELEASE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guards=sum(c['fault']for c in rows),errors=errors[:8],rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max((int(v[-1])for v in observed),default=0),actual_body_and_animation_query_owners=True,source_animation_begin_executed=True,sound_results_and_post_sound_model_mutation_instrumented=True,physical_sound_backend_bound=False,frame_zero_callbacks_executed=False,production_player_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish();assert report['status']=='PASS'

if __name__=='__main__':main()
