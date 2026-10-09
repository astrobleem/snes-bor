"""Real ranged target service feeding canonical attack-chain continuations."""
import argparse,hashlib,itertools,json,re
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from compiler import Source
from source_profile import document
from source_animation_ids import configure
from source_target_4086 import Target,normal_find
from source_attack_chain_4086 import execute
from source_attack_chain_native import emit as emit_chain
from source_normal_target_native import emit as emit_target
from source_foreign_state_layout import layout
from source_attack_body_profile import derive as bodies,pack_runtime
from source_animation_init_4086 import derive as init_derive,pack as init_pack
from source_frame_effects_4086 import derive as effects_derive,pack as effects_pack
from source_model_switch_requirements import derive as models_derive,pack_animation_cache
from source_frame_state_4086 import derive as frames_derive,pack as frames_pack
from source_animation_range_4086 import derive as ranges_derive,pack as ranges_pack
from m4_normal_target_native import SETUP
from m4_target_metadata_native import LUA
from m4_animation_init_native import luav
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''
TargetChainProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 jsl AIBEGIN
 bcs TargetChainProbe_Bad
 cmp #2
 bne TargetChainProbe_Bad
 jsl SourceAttackChain_Begin
 bcs TargetChainProbe_Bad
TargetChainProbe_Loop:
.a16
.i16
 lda.l WORK+2
 cmp #3
 bne TargetChainProbe_Good
TargetChainProbe_Query:
.a16
.i16
 nop
 jsl NormalTarget_AttackChain
 bcc TargetChainProbe_Bad
TargetChainProbe_GuardRejected:
.a16
.i16
 nop
 jsl NormalTarget_AttackChain
 bcs TargetChainProbe_Bad
TargetChainProbe_Response:
.a16
.i16
 nop
 jsl SourceAttackChain_TargetResume
 bcs TargetChainProbe_Bad
 jmp TargetChainProbe_Loop
TargetChainProbe_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
TargetChainProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);sy=symbols(Path('src/main.sym'));fi=frames_derive(source);ft=frames_pack(fi);ri=ranges_derive(source);rt=ranges_pack(ri)
    br=bodies(source);bt=pack_runtime(br);ar=init_derive(source);at=init_pack(ar);fe=effects_pack(effects_derive(source));cache_full=pack_animation_cache(models_derive(source))
    cache=cache_full
    attacks=configure(document(source,'data/models.txt')['directives'])['arrays']['normal_attacks']
    ranges={an['handle']:an['ranges']for an in ri['animations']}
    regions={r['name']:r['address']for r in layout(0x7fa000,6400)['regions']};work=regions['attack_chain_controls'];styles=regions['entity_combostyle']
    frames={}
    ids={m['identity']:m['index']for m in br['models']}
    for an in fi['animations']:
        for i,f in enumerate(an['frames']):frames.setdefault(bool(f['vulnerable']),(ids[an['model']],an['handle'],i))
    rows=[]
    for model,style,kind,step,choice,direction in itertools.product((3,4),range(4),(1,2),range(3),('near','far','hidden'),(0,1)):
        fm,fh,fp=frames[True]
        targets=[Target(0x414000,type=kind,hostile=2,direction=direction),Target(0x414050,type=2,x=(10 if choice!='far' else 1000)*65536*(1 if direction else -1),hide=1 if choice=='hidden' else 0),Target(0x4140a0,type=2,x=1200*65536)]
        entities=[asdict(t)|dict(slot=s,model=model if s==0 else fm,handle=fh,frame=fp,exists=1,dead=0)for s,t in enumerate(targets)]
        fields=deepcopy(br['models'][model]['fields']);fields.update(combostyle=style,type=kind)
        entity=dict(modeldata=fields,combostep=[step,0,0,0,0],combotime=49,takeaction=0,attacking=55,idling=66);trace=[]
        def handle(role):return int.from_bytes(cache[model*336+2*role:model*336+2*role+2],'little')
        def target(role,adjustment):
            result=normal_find(targets,targets[0].token,ranges[handle(role)],adjustment)or 0;trace.append([role,result]);return result
        gen=execute(entity,dict(time=48,combodelay=100,attacks=attacks),lambda role:bool(handle(role)),target)
        try:next(gen);pick=1
        except StopIteration as stop:pick=stop.value
        rows.append(dict(name=f'chain_{len(rows)}',count=3,time=48,entities=entities,order=[0,1,2],bad='',fault=0,role=0,handle=1,adjustment=0,model=model,style=style,step=step,pick=pick,step_expected=entity['combostep'][0],timer_expected=entity['combotime'],trace=trace))
    setup=SETUP+'''\n
 for j=0,95 do emu.write(WORK+j,0,mt)end
 put(WORK,0xb675);put(WORK+4,0);put(WORK+58,100,4);put(STYLES,c.style,4)
 for j=1,#cachebytes do emu.write(0x43c000+j-1,cachebytes[j],mt)end
 set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_Bytes',5376)
 for j=0,8 do emu.write(0x435980+j,bodybytes[17+c.model*9+j],mt)end;put(0x435989,0xb605)
 put(0x437e08,c.step,4);put(0x437e0c,49,4);put(0x437e10,0xb5fb);put(0x437e12,0)
 put(0x40c058,55,4);put(0x43eb00,66,4)
 put(0x414010,1,4);put(0x414014,0,4)
 set('SourceClock4086_Ready',0xb4c5);put(sy.SourceClock4086_TimeLo,48,4)
 set('SourceAttackBody4086_Ready',0xb605);set('SourceAttackBody4086_Status',0);set('SourceAttackBody4086_Bank',58);set('SourceAttackBody4086_Base',BODYBASE);set('SourceAttackBody4086_Bytes',BODYBYTES)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Base',INITBASE);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',INITBYTES);set('SourceAnimationInit4086_Issued',0)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',EFFECTBYTES);set('SourceUpdateFrame4086_Animations',80)
 chaintrace={}
'''
    lua='local cachebytes='+luav(list(cache))+'\nlocal bodybytes='+luav(list(bt))+'\nlocal chaintrace={}\n'+LUA[:LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local n=0;')]
    lua=lua.replace('put(v+28,1,4)','put(v+28,e.direction,4)').replace('put(v+52,65536*e.slot,4)','put(v+52,e.x,4)').replace('put(v+60,220*65536,4)','put(v+60,e.z,4)').replace(' before={};',setup+' before={};')
    # Compare state before animation init changes the cursor. The native
    # target result is observed after its marker is published, never supplied.
    lua+=r'''
local function observe()
 local c=rows[word(INDEX)+1];local expected={}
 for address,value in pairs(before)do expected[address]=value end
 local function want(address,value,n)for j=0,(n or 4)-1 do expected[address+j]=(value>>(8*j))&255 end end
 want(0x416814,50);want(0x437e08,c.step_expected)
 if c.pick==1 then want(0x43900c,17);want(0x40c058,1);want(0x43eb00,0)else want(0x437e0c,c.timer_expected)end
 local changed=0;for address,value in pairs(expected)do if emu.read(address,mt)~=value then changed=changed+1 end end
 return changed
end
local prefix=-1
local guardserial=-1
local guardrestore,guardbefore={},{}
emu.addMemoryCallback(function()
 guardserial=(guardserial+1)%8
 local variants={{{WORK,0}},{{WORK+2,4}},{{WORK+4,1}},{{WORK+18,0xb676}},{{WORK+12,2}},{{WORK+50,128}},{{WORK+50,168},{WORK+6,168}},{{sy.SourceAI4086_Callback,6}}}
 guardrestore={};for _,pair in ipairs(variants[guardserial+1])do guardrestore[#guardrestore+1]={pair[1],word(pair[1])};put(pair[1],pair[2])end
 guardbefore={};for _,span in ipairs({{WORK,96},{sy.VmNativeVariant_Result,8}})do for j=0,span[2]-1 do guardbefore[span[1]+j]=emu.read(span[1]+j,mt)end end
end,emu.callbackType.exec,GUARD,GUARD,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local delta=0;for address,value in pairs(guardbefore)do if emu.read(address,mt)~=value then delta=delta+1 end end
 emu.log('TARGETCHAINGUARD|'..guardserial..'|'..word(INDEX)..'|'..delta)
 for _,pair in ipairs(guardrestore)do put(pair[1],pair[2])end
end,emu.callbackType.exec,GUARDREJECTED,GUARDREJECTED,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('TARGETCHAINFAULT|'..word(INDEX)..'|'..word(WORK+2)..'|'..word(sy.SourceAttackBody4086_Status)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..word(sy.SourceAITarget4086_Status))end,emu.callbackType.exec,FAULT,FAULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()prefix=observe()end,emu.callbackType.exec,PREFIX,PREFIX,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()chaintrace[#chaintrace+1]=word(WORK+50)..':'..(word(WORK+14)|(word(WORK+16)<<16))..':'..word(WORK+18)end,emu.callbackType.exec,RESPONSE,RESPONSE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local variant=0;for j=0,7 do if emu.read(sy.VmNativeVariant_Result+j,mt)~=0xa5 then variant=variant+1 end end
 emu.log('NATIVETARGETCHAIN|'..word(INDEX)..'|'..ctx..'|'..(c.pick==1 and prefix or observe())..'|'..word(WORK+2)..'|'..word(0x437e08)..'|'..word(sy.SourceAI4086_State)..'|'..variant..'|'..table.concat(chaintrace,','))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    lua+='local initguard="entry"\n'
    for name,address in sy.items():
        if name.startswith('SourceAnimationInit4086_Relaxed_'):
            lua+=f"emu.addMemoryCallback(function()initguard='{name}'end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
    lua+=f"emu.addMemoryCallback(function()emu.log('CHAININITFAULT|'..word(INDEX)..'|'..initguard)end,emu.callbackType.exec,{sy['SourceAnimationInit4086_ResolveBad']},{sy['SourceAnimationInit4086_ResolveBad']},emu.cpuType.snes,mt)\n"
    assembly=ASM+emit_chain(work,styles,attacks,sy)+emit_target(sy,chain=work)+'\nTargetChainProbe_End:\n'
    values=dict(WORK=work,STYLES=styles,AIBEGIN=sy['SourceAI4086_Begin'],QUERYROLE=0x7ffd8a,QUERYADJUST=0x7ffd8c,TABLESIZE=len(ft),RANGEBYTES=len(rt),BODYBASE=0x8000+len(rt),BODYBYTES=len(bt),INITBASE=0x8000+len(ft),INITBYTES=len(at),EFFECTBYTES=len(fe))
    for k,v in values.items():assembly=re.sub(r'\b'+k+r'\b',str(v),assembly);lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    reporter=Reporter('M4-NATIVE-TARGET-CHAIN',kind='GATE')
    def boundary(raw,all_symbols):
        if all_symbols['TargetChainProbe_End']>>16!=39:raise ValueError('TARGET_CHAIN_FIXTURE_BANK_OVERFLOW')
    raw,log=run_fixture(a.rom,a.output,rows,'TargetChainProbe','SourceAITarget4086_Ready',0xb5f3,[(58,0,rt),(58,len(rt),bt),(59,0,ft),(59,len(ft),at),(60,0,fe)],lua,reporter,append=assembly,probes=dict(PREFIX='SourceAttackChain_BeforeAnimation',RESPONSE='TargetChainProbe_Response',FAULT='TargetChainProbe_Bad',GUARD='TargetChainProbe_Query',GUARDREJECTED='TargetChainProbe_GuardRejected'),batch_size=4,link_pcm=False,rom_transform=boundary)
    actual=[l.split('NATIVETARGETCHAIN|',1)[1].strip().split('|')for l in log.splitlines()if'NATIVETARGETCHAIN|'in l];failures=[]
    for i,v in enumerate(actual):
        c=rows[i];expected=list(map(str,[i,0,0,4 if c['pick'] else 2,c['step_expected'],2,0]))+[','.join(f'{role}:{result}:46710'for role,result in c['trace'])]
        if v!=expected:failures.append(dict(input=c,actual=v,expected=expected))
    reporter.check('actual ranged selection, pointer/slot/role publication, native chain continuation and real animation request',len(actual)==len(rows)and not failures)
    guards=[list(map(int,l.split('TARGETCHAINGUARD|',1)[1].split('|')))for l in log.splitlines()if'TARGETCHAINGUARD|'in l]
    reporter.check('eight stale chain/owner forms reject without publishing or changing chain/VM state',len(guards)==sum(len(c['trace'])for c in rows)and set(v[0]for v in guards)==set(range(8))and all(v[2]==0 for v in guards))
    report=dict(schema='BYOR_4086_NORMAL_TARGET_CHAIN_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),native_target_queries=sum(len(c['trace'])for c in rows),guard_results=guards,target_results_instrumented=False,source_chain_geometry_preserved=True,combostyle_and_type_inputs_instrumented=True,source_animation_begin_executed=True,frame_zero_pending_only=True,production_player_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
