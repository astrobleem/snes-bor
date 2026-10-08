"""Native cost/resource/unlink prefix and mandatory frame-zero transition."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_costmove_authority import cases
from source_costmove_native import emit,emit_combo_energy_query
from source_animation_energy_4086 import derive as energies,pack as pack_energies
from source_animation_init_4086 import derive as animations,pack as pack_animations
from source_frame_effects_4086 import derive as effects,pack as pack_effects
from source_model_switch_requirements import derive as models,pack_animation_cache
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

WORK=0x7fc800;TAIL=0x7fc900

LUA=r'''
local mt=emu.memType.snesMemory;local before={};local start=0;local prefix=0;local cpu={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function long(a)return word(a)|(word(a+2)<<16)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function dword(a,v)put(a,v&65535);put(a+2,(v>>16)&65535)end
local function blob(a,hex)for i=1,#hex,2 do emu.write(a+(i-1)//2,tonumber(hex:sub(i,i+1),16),mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local s=c.slot;local p=(s+1)%128
 local v=0x414000+s*80;local core=0x40c000+s*96;local fl=0x43eb00+s*32;local life=0x439000+s*80;local co=0x437e00+s*20;local rel=0x409000+s*64;local aux=0x41f500+s*20
 for _,r in ipairs({{v,80},{core,96},{fl,32},{life,80},{co,20},{rel,64},{aux,20},{0x414000+p*80,80},{0x40c000+p*96,96},{0x409000+p*64,64}})do for i=0,r[2]-1 do emu.write(r[1]+i,0,mt)end end
 blob(0x43c000,CACHE)
 dword(v,v);put(v+16,1);dword(v+20,0);put(v+32,1);dword(v+36,c.original.health)
 put(0x416800+s*64,c.model);put(0x416804+s*64,0);put(0x416806+s*64,0)
 dword(core+72,c.original.type);dword(core+76,c.original.mp);dword(core+80,0x414000+p*80)
 dword(life+12,99);dword(fl,3);dword(fl+4,9);dword(co+4,c.original.seal);dword(co+8,1);put(co+16,0xb5fb)
 for i=0,3 do dword(TAILADDR+s*16+4*i,i+2)end
 dword(aux,229376);dword(aux+4,4294803456)
 dword(0x409000+p*64+28,v);dword(0x40c000+p*96+80,v)
 dword(rel+28,c.linked and(0x414000+p*80)or 0)
 put(WORKADDR,0xb670);put(WORKADDR+2,0);put(WORKADDR+4,s);put(WORKADDR+6,c.role)
 dword(WORKADDR+8,c.fs);dword(WORKADDR+12,c.jump);dword(WORKADDR+16,c.context.nospecial);dword(WORKADDR+20,c.context.nocost);dword(WORKADDR+24,c.context.healthcheat)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128);put(sy.SourceModelEntityCopy4086_Ready,0xb4eb)
 put(sy.SourceModelAnimationCopy4086_Ready,0xb4e9);put(sy.SourceModelAnimationCopy4086_Models,16);put(sy.SourceModelAnimationCopy4086_Maximum,168);put(sy.SourceModelAnimationCopy4086_Bytes,5376)
 put(sy.SourceAnimationInit4086_Ready,0xb4ec);put(sy.SourceAnimationInit4086_State,0);put(sy.SourceAnimationInit4086_Base,0x8000);put(sy.SourceAnimationInit4086_Bank,59);put(sy.SourceAnimationInit4086_Bytes,AIBYTES);put(sy.SourceAnimationInit4086_Issued,0)
 put(sy.SourceUpdateFrame4086_Ready,0xb4e3);put(sy.SourceUpdateFrame4086_State,0);put(sy.SourceUpdateFrame4086_Pending,0);put(sy.SourceUpdateFrame4086_Base,0x8000);put(sy.SourceUpdateFrame4086_Bank,60);put(sy.SourceUpdateFrame4086_Bytes,FEBYTES);put(sy.SourceUpdateFrame4086_Animations,HANDLES)
 put(sy.SourceClock4086_Ready,0xb4c5);put(sy.SourceClock4086_TimeLo,48);put(sy.SourceClock4086_TimeHi,0);put(sy.SourceWorldTick4086_Ready,0)
 put(sy.SourceRetirement4086_Ready,0xb4f8)
 put(sy.SourceAnimationEnergy4086_Ready,0xb5fc);put(sy.SourceAnimationEnergy4086_Bank,58);put(sy.SourceAnimationEnergy4086_Bytes,AEBYTES);put(sy.SourceAnimationEnergy4086_Status,0)
 put(sy.SourceCheckEnergy4086_Ready,0xb5fa);put(sy.SourceCheckEnergy4086_Status,0)
 -- Fields come from each literal C case. This modifies only the private
 -- immutable energy table, never the production source archive.
 local at=58*32768+16+(c.handle-1)*16
 for i,value in ipairs({c.original.fields.cost,c.original.fields.mponly,c.original.fields.disable})do for j=0,3 do emu.write(at+(i-1)*4+j,(value>>(8*j))&255,emu.memType.snesPrgRom)end end
 if c.bad=='ready'then put(WORKADDR,0)
 elseif c.bad=='pending'then put(WORKADDR+2,3)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='slot'then put(WORKADDR+4,128)
 elseif c.bad=='animation_ready'then put(sy.SourceAnimationInit4086_Ready,0)
 elseif c.bad=='energy_ready'then put(sy.SourceAnimationEnergy4086_Ready,0)
 elseif c.bad=='energy_bank'then put(sy.SourceAnimationEnergy4086_Bank,64)
 elseif c.bad=='numeric_ready'then put(sy.SourceCheckEnergy4086_Ready,0)
 elseif c.bad=='health_tag'then put(v+32,2)
 elseif c.bad=='health_reserved'then put(v+34,1)
 elseif c.bad=='combat_marker'then put(co+16,0)
 elseif c.bad=='combat_reserved'then put(co+18,1)
 elseif c.bad=='link'then dword(rel+28,0x424000)
 elseif c.bad=='role_absent'then put(0x43c000+2*(c.model*168+c.role),0)end
 put(EXPECTFAULT,c.fault)
 before={};for _,r in ipairs({{v,80},{core,96},{fl,32},{life,80},{co,20},{rel,64},{aux,20},{TAILADDR+s*16,16},{0x40c000+p*96,96},{0x409000+p*64,64}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 prefix=0;start=emu.getState().masterClock
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local s=c.slot;local p=(s+1)%128;local w=c.wanted;local got={1,long(0x40c04c+s*96),long(0x414024+s*80),long(0x43900c+s*80),long(0x40c058+s*96),long(0x43eb00+s*32),long(0x43eb04+s*32),long(0x437e08+s*20)}
 for i=0,3 do got[#got+1]=long(TAILADDR+s*16+4*i)end
 for _,a in ipairs({0x40901c+p*64,0x40c050+p*96,0x40901c+s*64,0x40c050+s*96})do got[#got+1]=long(a)~=0 and 1 or 0 end
 got[#got+1]=long(0x41f500+s*20);got[#got+1]=long(0x41f504+s*20);got[#got+1]=1;got[#got+1]=c.role
 for i,v in ipairs(got)do if v~=(w[i]&0xffffffff)then prefix=prefix+1;emu.log('COSTPREFIXDIFF|'..word(INDEX)..'|'..i..'|'..v..'|'..w[i])end end
end,emu.callbackType.exec,PREFIX,PREFIX,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local changed=0
 if c.wanted[1]==0 or c.fault~=0 then for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end end
 local state=word(WORKADDR+2);local anim=word(sy.SourceAnimationInit4086_State)
 emu.log('COSTMOVENATIVE|'..word(INDEX)..'|'..prefix..'|'..changed..'|'..state..'|'..anim..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--combo-query',action='store_true',help='Prove pure MP-first combo energy selection; no debit or actor mutation.')
    for n in ('rom','source','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);source=Source(a.source);sy=symbols(Path('src/main.sym'))
    energy=energies(source);ai=animations(source);fe=effects(source);model=models(source)
    energytable=pack_energies(energy);aitable=pack_animations(ai);fetable=pack_effects(fe);cache=pack_animation_cache(model)
    choices=[an for an in ai['animations']if an['role'].lower().startswith(('freespecial','special'))]
    names={m['identity']:m['id']for m in model['models']};allcases=list(cases(energy));rows=[]
    for i in range(192):
        c=allcases[i*(len(allcases)-1)//191]
        if c['original']['frames']==0:continue
        an=choices[(i*(len(allcases)-1)//191)%len(choices)]
        # The native source model cache is real; stage field variants select
        # the immutable descriptor for its actual authored handle.
        c=dict(c);c['original']=dict(c['original'],frames=an['numframes']);c.update(model=names[an['model']],role=an['engine_animation_id'],handle=an['handle'],slot=(0,1,127)[i%3],fault=0,bad='')
        # Native testing requires the same frame presence as the source case.
        if c['original']['frames']==0:continue
        wanted=list(struct.unpack('<20I',c['expected']));wanted[-1]=c['role']if wanted[0]else 0;c['wanted']=wanted
        c.pop('expected');rows.append(c)
    base=next(c for c in rows if c['wanted'][0]and c['linked']and not c['context']['nocost']and not c['context']['healthcheat'])
    for bad in ('ready','pending','world','slot','animation_ready','energy_ready','energy_bank','numeric_ready','health_tag','health_reserved','combat_marker','combat_reserved','link'):
        rows.append(dict(base,bad=bad,fault=1))
    absent=dict(base,bad='role_absent',wanted=list(base['wanted']));absent['wanted'][0]=0;rows.append(absent)
    # Source C signed overflow is undefined: native capability rejects it
    # before debit, velocity, flags, history, unlink or animation changes.
    overflow=dict(base,bad='overflow',fault=1,original=dict(base['original'],mp=0x7fffffff,health=0x7fffffff,seal=0,fields=dict(cost=-1,mponly=1,disable=0)))
    rows.append(overflow)
    if a.combo_query:
        from source_animation_energy_4086 import check
        rows[-1]=dict(rows[-1],fault=0)
        for c in rows:
            if c['bad']=='link':c['fault']=0
            e=c['original'];mp=check(1,e['fields'],e['type'],e['seal'],e['mp'],e['health'])
            hp=check(0,e['fields'],e['type'],e['seal'],e['mp'],e['health'])
            c['query_expected']=0 if c['fault'] or c['bad']=='role_absent' else int(mp or hp)
            c['query_trace']='' if c['fault'] or c['bad']=='role_absent' else '1' if mp else '1,0'
            if c['bad']=='numeric_ready':c['query_trace']='1'
    lua=LUA
    if a.combo_query:
        begin=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local s=c.slot;local p=(s+1)%128;local w=c.wanted;')
        end=lua.index('emu.addMemoryCallback(function()',begin+1)
        lua=lua[:begin]+lua[end:]
        lua=lua.replace('prefix=0;start=emu.getState().masterClock','prefix=0;querytrace={};start=emu.getState().masterClock')
        lua='local querytrace={};local query_a=0;local query_c=0\n'+lua
        lua+=r'''
emu.addMemoryCallback(function()
 querytrace[#querytrace+1]=word(sy.SourceCheckEnergy4086_Which)
end,emu.callbackType.exec,QUERYEXEC,QUERYEXEC,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();query_a=s['cpu.a'];query_c=s['cpu.ps']&1
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('COMBOENERGYNATIVE|'..word(INDEX)..'|'..query_a..'|'..query_c..'|'..changed..'|'..table.concat(querytrace,',')..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    for k,v in dict(WORKADDR=WORK,TAILADDR=TAIL,AIBYTES=len(aitable),FEBYTES=len(fetable),HANDLES=len(ai['animations']),AEBYTES=len(energytable)).items():lua=lua.replace(k,str(v))
    lua=lua.replace('CACHE',json.dumps(cache.hex()))
    if a.combo_query:lua=lua.replace('QUERYEXEC',str(sy['SourceCheckEnergy4086_Execute']))
    reporter=Reporter('M4-COSTMOVE-NATIVE',kind='GATE')
    raw,log=run_fixture(a.rom,folder,rows,'SourceComboEnergy_Query' if a.combo_query else 'SourceCostMove_Begin','VmSourceInput_Ready',0xb670,
                       [(58,0,energytable),(59,0,aitable),(60,0,fetable)],lua,reporter,
                       append=emit_combo_energy_query(WORK,sy) if a.combo_query else emit(WORK,TAIL,sy),probes=None if a.combo_query else dict(PREFIX='SourceCostMove_BeforeAnimation'),batch_size=2,frame_limit=700,link_pcm=False)
    if a.combo_query:
        actual=[l.split('COMBOENERGYNATIVE|',1)[1].strip().split('|') for l in log.splitlines() if 'COMBOENERGYNATIVE|' in l]
        errors=[v for i,v in enumerate(actual) if v[:5]!=[str(i),str(rows[i]['query_expected']),str(rows[i]['fault']),'0',rows[i]['query_trace']]]
        reporter.check('pure canonical combo energy query preserves actor state and MP-first short circuit',len(actual)==len(rows) and not errors)
        report=dict(schema='BYOR_4086_COMBO_ENERGY_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',cases=len(rows),errors=errors[:10],rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max(int(v[5]) for v in actual),private_energy_descriptors_instrumented=True,production_player_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
        (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish();return
    actual=[list(map(int,l.split('COSTMOVENATIVE|',1)[1].split('|')))for l in log.splitlines()if 'COSTMOVENATIVE|'in l]
    errors=[v for i,v in enumerate(actual)if v[:4]!=[i,0,0,5 if rows[i]['fault']else 3 if rows[i]['wanted'][0]else 2]]
    reporter.check('actual cost/resource/unlink prefix and frame-zero request',len(actual)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_COSTMOVE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guard_cases=sum(c['fault']for c in rows),errors=errors[:10],
                rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max(v[5]for v in actual),source_frame_zero_pending=True,
                private_energy_descriptors_instrumented=True,source_resource_storage_bound=True,source_unlink_storage_bound=True,frame_zero_execution_bound=False,production_player_owner_bound=False,
                motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish()

if __name__=='__main__':main()
