"""Full MOTU registry cache with all existing shared-state ceilings enabled."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_model_switch_requirements import derive,pack_animation_cache
from source_frame_effects_4086 import derive as frames,pack as pack_frames
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory;local start=0;local cpu={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function blob(a,hex)for i=1,#hex,2 do emu.write(a+(i-1)//2,tonumber(hex:sub(i,i+1),16),mt)end end
local function set(k,v)put(sy['SourceModelAnimationCopy4086_'..k],v)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 blob(0x43c000,c.initial)
 set('Ready',0xb4e9);set('Models',16);set('Maximum',c.maximum);set('Bytes',c.bytes);set('OldModel',c.old);set('NewModel',c.new);set('Flags',c.flags)
 put(sy.SourceAttackCostState4086_Ready,0xb609);put(sy.SourceMovementState4086_Ready,0xb60b);put(sy.SourceAutokillState4086_Ready,0xb60e);put(sy.SourceOffscreenState4086_Ready,c.bad=='offscreen_ready'and 0xb611 or 0xb610)
 put(sy.SourceUpdateFrame4086_Ready,0xb4e3);put(sy.SourceUpdateFrame4086_Bank,60);put(sy.SourceUpdateFrame4086_Base,0x8000);put(sy.SourceUpdateFrame4086_Bytes,TABLEBYTES)
 put(EXPECTFAULT,c.fault)
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();start=s.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local mismatch=0
 for i=1,#c.expected,2 do if emu.read(0x43c000+(i-1)//2,mt)~=tonumber(c.expected:sub(i,i+1),16)then mismatch=mismatch+1 end end
 local s=emu.getState();local context=0;for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then context=context+1 end end
 if cpu.sp+3~=s['cpu.sp']or(cpu.ps&254)~=(s['cpu.ps']&254)then context=context+1 end
 emu.log('REGISTRYCACHE|'..word(INDEX)..'|'..mismatch..'|'..context..'|'..word(sy.SourceModelAnimationCopy4086_Status)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','source','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);source=Source(a.source)
    r=derive(source);cache=pack_animation_cache(r);fr=frames(source);table=pack_frames(fr)
    count=len(r['models']);maximum=r['maximum_animations']
    if count!=16 or maximum!=168 or len(cache)!=5376:raise ValueError('REGISTRY_PROOF_SHAPE_CHANGED')
    framecounts={an['handle']:len(an['frames'])for an in fr['animations']};words=list(struct.unpack('<2688H',cache));initial=cache+bytes([0xa5])*(8192-len(cache))
    pairs={(i,i)for i in range(count)}|{(i,(i+1)%count)for i in range(count)}
    for model in r['models']:
        for target in model['weapon_ids']or():pairs.add((model['id'],target));pairs.add((target,model['id']))
    rows=[]
    for old,new in sorted(pairs):
        for flags in range(8):
            expected=bytearray(initial)
            if not flags&1:
                for i in range(maximum):
                    h=words[old*maximum+i]
                    if not words[new*maximum+i]and h and framecounts[h]>0:struct.pack_into('<H',expected,2*(new*maximum+i),h)
            rows.append(dict(old=old,new=new,flags=flags,maximum=maximum,bytes=len(cache),initial=initial.hex(),expected=expected.hex(),fault=0,bad=''))
    # Full 5632-byte boundary accepted when inheritance is disabled; next row
    # would collide with source offscreen storage and must be rejected.
    for cap,fault in ((176,0),(177,1)):
        rows.append(dict(old=0,new=15,flags=1,maximum=cap,bytes=16*cap*2,initial=initial.hex(),expected=initial.hex(),fault=fault,bad=''))
    rows.append(dict(rows[0],bad='offscreen_ready',fault=1))
    reporter=Reporter('M4-FULL-REGISTRY-CACHE',kind='GATE')
    lua=LUA.replace('TABLEBYTES',str(len(table)))
    raw,log=run_fixture(a.rom,folder,rows,'SourceModelAnimationCopy4086_Apply','SourceModelAnimationCopy4086_Ready',0xb4e9,
                       [(60,0,table)],lua,reporter,batch_size=2,link_pcm=False,frame_limit=900)
    actual=[list(map(int,l.split('REGISTRYCACHE|',1)[1].split('|')))for l in log.splitlines()if 'REGISTRYCACHE|'in l]
    errors=[v for i,v in enumerate(actual)if v[:4]!=[i,0,0,2 if rows[i]['fault']else 1]]
    reporter.check('full registry mutation and shared-state boundary retained',len(actual)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_FULL_REGISTRY_ANIMATION_CACHE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
                cases=len(rows),models=count,maximum_source_animation_ids=maximum,highest_authored_animation_id=max(a['engine_animation_id']for m in r['models']for a in m['animation_slots']),
                cache_bytes=len(cache),shared_state_cache_ceiling=5632,remaining_bytes=5632-len(cache),
                cache_sha256=hashlib.sha256(cache).hexdigest(),frame_table_sha256=hashlib.sha256(table).hexdigest(),
                rom_sha256=hashlib.sha256(raw).hexdigest(),errors=errors[:10],peak_master_clocks=max(v[4]for v in actual),
                full_registry_cache_fits=True,weapon_dependencies_source_derived=True,actual_model_switch_owner_bound=False,
                motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish()

if __name__=='__main__':main()
