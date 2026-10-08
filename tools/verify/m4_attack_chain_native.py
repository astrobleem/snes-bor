"""Actual source chain rows/cache and native animation-pending attack prefix."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_profile import document
from source_animation_ids import configure
from source_attack_body_profile import derive as bodies, pack_runtime
from source_attack_chain_4086 import execute
from source_attack_chain_native import emit
from source_animation_init_4086 import derive as animations, pack as pack_animations
from source_frame_effects_4086 import derive as effects, pack as pack_effects
from source_model_switch_requirements import derive as models, pack_animation_cache
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

WORK=0x7fa000
STYLES=0x7fa100
ASM='''
ChainProbe:
.a16
.i16
 php
 sed
 jsl SourceAttackChain_Begin
ChainProbe_AfterBegin:
.a16
.i16
 bcs ChainProbe_BadReturn
ChainProbe_Loop:
 lda.l WORK+2
 cmp #3
 bne ChainProbe_GoodReturn
ChainProbe_Target:
 nop
 jsl SourceAttackChain_TargetResume
ChainProbe_AfterTarget:
 bcc ChainProbe_Loop
ChainProbe_BadReturn:
 plp
 sec
 rtl
ChainProbe_GoodReturn:
 plp
 clc
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function long(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function set(k,v)put(sy[k],v)end
local function blob(a,hex)for i=1,#hex,2 do emu.write(a+(i-1)//2,tonumber(hex:sub(i,i+1),16),mt)end end
local before,cpu,trace,start,prefix,ctx,decimal={}, {},{},0,0,0,0
local ranges={{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x439000,10240},{0x43eb00,4096},{0x437e00,2560},{0x41f500,2560},{STYLES,512}}
local function compare(c)
 local co=0x437e00+c.slot*20;local life=0x439000+c.slot*80;local core=0x40c000+c.slot*96;local fl=0x43eb00+c.slot*32
 local wanted={};for a,v in pairs(before)do wanted[a]=v end
 local function expect(a,v)for j=0,3 do wanted[a+j]=(v>>(8*j))&255 end end
 if c.fault==0 then
  expect(co+8,c.step_expected)
  if c.pick==1 then expect(life+12,17);expect(core+88,1);expect(fl,0)
  elseif c.style&2~=0 and c.length>0 then expect(co+12,(c.time+c.delay)&0xffffffff)end
 end
 local errors=0;for a,v in pairs(wanted)do if emu.read(a,mt)~=v then errors=errors+1;if errors<8 then emu.log('CHAINBYTE|'..word(INDEX)..'|'..string.format('%06X',a)..'|'..v..'|'..emu.read(a,mt))end end end
 return errors
end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for j=0,r[2]-1 do emu.write(r[1]+j,0,mt)end end
 for j=0,95 do emu.write(WORK+j,0,mt)end
 blob(0x43c000,CACHE)
 for j=0,15 do for i=0,8 do emu.write(58*32768+16+j*9+i,c.body[1+i],emu.memType.snesPrgRom)end end
 local at=c.slot<96 and 0x435980+c.slot*11 or 0x40bdcc+(c.slot-96)*11
 for i=0,8 do emu.write(at+i,c.body[1+i],mt)end;put(at+9,0xb605)
 local s=c.slot;local v=0x414000+s*80
 put(v,v,4);put(v+16,1);put(v+20,0,4)
 put(0x416800+s*64,c.model);put(0x416804+s*64,0)
 put(0x40c048+s*96,c.type,4);put(0x40c058+s*96,55,4)
 put(0x43900c+s*80,0,4);put(0x43904a+s*80,0xb4fb)
 put(0x43eb00+s*32,66,4)
 put(0x437e08+s*20,c.step,4);put(0x437e0c+s*20,c.deadline,4);put(0x437e10+s*20,0xb5fb)
 put(STYLES+s*4,c.style,4);put(WORK,0xb675);put(WORK+4,s);put(WORK+58,c.delay,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000)
 set('SourceClock4086_Ready',0xb4c5);put(sy.SourceClock4086_TimeLo,c.time,4);set('SourceWorldTick4086_Ready',0)
 set('SourceAttackBody4086_Ready',0xb605);set('SourceAttackBody4086_Status',0);set('SourceAttackBody4086_Bank',58);set('SourceAttackBody4086_Base',0x8000);set('SourceAttackBody4086_Bytes',BODYBYTES)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',16)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_Bytes',5376)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Base',0x8000);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',AIBYTES);set('SourceAnimationInit4086_Issued',0)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FEBYTES);set('SourceUpdateFrame4086_Animations',HANDLES)
 for i,role in ipairs(ATTACKS)do if(c.valid&(1<<(i-1)))==0 then put(0x43c000+2*(c.model*168+role),0)end end
 if c.bad=='ready'then put(WORK,0)
 elseif c.bad=='busy'then put(WORK+2,4)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='slot'then put(WORK+4,128)
 elseif c.bad=='clock'then set('SourceClock4086_Ready',0)
 elseif c.bad=='body'then put(at+9,0)
 elseif c.bad=='life'then put(0x43904a+s*80,0)
 elseif c.bad=='combat'then put(0x437e10+s*20,0)
 elseif c.bad=='reserved'then put(0x437e12+s*20,1)
 end
 before={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
 trace={};prefix=-1;decimal=0;local st=emu.getState();start=st.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local role=word(WORK+50);trace[#trace+1]=role
 local found=0;for i,r in ipairs(ATTACKS)do if r==role then found=c.targets&(1<<(i-1))end end
 put(WORK+14,found,4)
 put(WORK+18,0xb676);put(WORK+52,c.slot);put(WORK+54,role)
end,emu.callbackType.exec,TARGET,TARGET,emu.cpuType.snes,mt)
for _,address in ipairs({BEGINRETURN,TARGETRETURN})do emu.addMemoryCallback(function()if emu.getState()['cpu.ps']&8==0 then decimal=decimal+1 end end,emu.callbackType.exec,address,address,emu.cpuType.snes,mt)end
emu.addMemoryCallback(function()prefix=compare(rows[word(INDEX)+1])end,emu.callbackType.exec,PREFIX,PREFIX,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();ctx=0
 for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1;emu.log('CHAINCPU|'..word(INDEX)..'|'..k..'|'..cpu[k]..'|'..st['cpu.'..k])end end
 if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local st=emu.getState()
 local errs=c.pick==1 and prefix or compare(c)
 emu.log('ATTACKCHAIN|'..word(INDEX)..'|'..word(WORK+2)..'|'..errs..'|'..(ctx+decimal)..'|'..table.concat(trace,',')..'|'..(st.masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','rom','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);br=bodies(source);ar=animations(source);fr=effects(source)
    cache=pack_animation_cache(models(source));ai=pack_animations(ar);fe=pack_effects(fr)
    attacks=configure(document(source,'data/models.txt')['directives'])['arrays']['normal_attacks']
    base=pack_runtime(br);rng=random.Random(408619092);rows=[]
    for n in range(192):
        model=(3,4)[n%2];fields=deepcopy(br['models'][model]['fields'])
        if n>=48:
            fields['atchain']=[rng.randrange(5)for _ in range(12)];fields['atchain'][0]=0 if n%7==0 else 1
            fields['chainlength']=max(i+1 for i,v in enumerate(fields['atchain'])if v)
        if n%31==0:fields['chainlength']=0;fields['atchain']=[0]*12
        c=dict(model=model,slot=(0,1,95,96,127)[n%5],length=fields['chainlength'],
               chain=fields['atchain'],style=n%8,type=(1,2,3,65536)[n%4],step=n%11,
               deadline=(0,49,50,51,0xffffffff)[n%5],time=(0,50,0xfffffffc)[n%3],
               delay=(0,100,0xffffffff)[n%3],valid=rng.randrange(16),targets=rng.randrange(16),bad='',fault=0)
        # Known declared roles: He_Man ATTACK1, He_ManB ATTACK1..3.
        available=1 if model==3 else 7
        c['valid']&=available
        e=dict(modeldata=dict(atchain=c['chain'],chainlength=c['length'],combostyle=c['style'],type=c['type']),
               combostep=[c['step'],7,8,9,10],combotime=c['deadline'],takeaction=0,attacking=55,idling=66)
        context=dict(time=c['time'],combodelay=c['delay'],attacks=attacks);trace=[]
        def target(role,_):trace.append(role);return c['targets']&(1<<attacks.index(role))
        gen=execute(e,context,lambda role:c['valid']&(1<<attacks.index(role)),target)
        try:next(gen);c['pick']=1
        except StopIteration as done:c['pick']=done.value
        except ValueError:continue # Undefined zero first entry after source restart.
        c['step_expected']=e['combostep'][0];c['trace']=','.join(map(str,trace))
        private=deepcopy(br)
        for m in private['models']:m['fields']=fields
        c['body']=list(pack_runtime(private)[16:25]);rows.append(c)
    first=next(c for c in rows if c['pick'])
    for bad in ('ready','busy','world','slot','clock','body','life','combat','reserved'):
        rows.append(dict(first,bad=bad,fault=1,pick=0,trace='',step_expected=first['step']))
    for step in (12,0x7fffffff,0xffffffff):
        rows.append(dict(first,step=step,deadline=51,time=50,fault=1,pick=0,trace='',step_expected=step))
    sy=symbols(Path('src/main.sym'))
    # SourceAttackBody symbols are intentionally not global fixture exports.
    extra={k:v for k,v in sy.items()if k.startswith('SourceAttackBody4086_')}
    lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+LUA
    values=dict(WORK=WORK,STYLES=STYLES,CACHE=luav(cache.hex()),ATTACKS=luav(attacks),
                BODYBYTES=len(base),AIBYTES=len(ai),FEBYTES=len(fe),HANDLES=len(ar['animations']))
    for name,v in values.items():
        import re
        lua=re.sub(r'\b'+name+r'\b',str(v),lua)
    asm=ASM.replace('WORK',str(WORK))+emit(WORK,STYLES,attacks,sy)
    reporter=Reporter('M4-ATTACK-CHAIN',kind='GATE')
    raw,log=run_fixture(a.rom,folder,rows,'ChainProbe','SourceAnimationInit4086_Ready',0xb4ec,
                        [(58,0,base),(59,0,ai),(60,0,fe)],lua,reporter,append=asm,
                        probes=dict(TARGET='ChainProbe_Target',PREFIX='SourceAttackChain_BeforeAnimation',BEGINRETURN='ChainProbe_AfterBegin',TARGETRETURN='ChainProbe_AfterTarget'),
                        batch_size=2,frame_limit=700,link_pcm=False)
    actual=[l.split('ATTACKCHAIN|',1)[1].strip().split('|')for l in log.splitlines()if 'ATTACKCHAIN|'in l]
    errors=[dict(case=i,input=rows[i],actual=v)for i,v in enumerate(actual)
            if v[:5]!=[str(i),str(6 if rows[i]['fault']else 4 if rows[i]['pick']else 2),'0','0',rows[i]['trace']]]
    reporter.check('canonical chain/target order/actor mutation/real animation pending/CPU retention',len(actual)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_ATTACK_CHAIN_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
                cases=len(rows),guards=sum(c['fault']for c in rows),errors=errors[:10],rom_sha256=hashlib.sha256(raw).hexdigest(),
                peak_master_clocks=max(int(v[5])for v in actual),target_results_instrumented=True,
                private_chain_tables_instrumented=True,source_animation_begin_executed=True,
                decimal_entry_and_flag_retention_proven=True,
                frame_zero_pending_only=True,frame_zero_callbacks_executed=False,
                production_player_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish()


if __name__=='__main__':main()
