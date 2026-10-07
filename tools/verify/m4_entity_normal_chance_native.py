"""Actual current-model/aiattack/X/camera selection of literal-C RNG cutoff."""
import argparse,hashlib,json
from pathlib import Path
from m4_ai_owner_native import LUA as OWNER_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from compiler import Source
from source_normal_chance_profile import pack
from source_actor_numeric import random32_step
from m4_animation_init_native import luav

SETUP=r'''
 set('SourceAI4086_State',2);set('SourceAI4086_Slot',s);set('SourceCommonThink4086_Ready',c.bad=='common_ready'and 0 or 0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',s)
 put(side,c.bad=='model'and 16 or c.model);put(side+4,65535);put(side+6,65535)
 put(v+48,c.bad=='x_tag'and 1 or 2,4);put(v+52,c.x,4);put(0x40c038+s*96,c.ai,4)
 put(sy.VmSourceWorld_AdvanceX,c.camera,4);set('SourceCameraMotion4086_Ready',c.bad=='camera_ready'and 0 or 0xb5db);set('SourceCameraMotion4086_HRes',c.bad=='native_width'and 256 or 320);set('SourceCameraMotion4086_VRes',240)
 set('SourceEntityNormalChance4086_Ready',c.bad=='ready'and 0 or 0xb601);set('SourceEntityNormalChance4086_Status',c.bad=='busy'and 1 or 0);set('SourceEntityNormalChance4086_Bank',c.bad=='bank'and 0 or 59);set('SourceEntityNormalChance4086_Base',c.bad=='base'and 0x7fff or c.bad=='extent'and 0xfff0 or 0x8000);set('SourceEntityNormalChance4086_Bytes',TABLEBYTES);put(sy.SourceEntityNormalChance4086_Result,55,4)
 set('SourceNormalChance4086_Ready',c.bad=='kernel_ready'and 0 or 0xb600);set('SourceNormalChance4086_Status',c.bad=='kernel_busy'and 1 or 0)
 set('SourceRandom4086_Ready',c.bad=='rng_ready'and 0 or 0xb4d4);put(sy.SourceRandom4086_SeedLo,c.seed,4);put(sy.SourceRandom4086_CallsLo,0xffffffff,4);set('SourceRandom4086_Busy',c.bad=='rng_busy'and 1 or 0)
 for j=0,7 do emu.write(sy.VmNativeVariant_Result+j,0xa5,mt)end;put(sy.SourceModelEntityCopy4086_Lo,0x12345678,4)
 for j,value in ipairs(tablebytes)do emu.write(59*32768+j-1,value,emu.memType.snesPrgRom)end
 if c.patch>=0 then for j=0,1 do emu.write(59*32768+c.patch+j,(c.value>>(8*j))&255,emu.memType.snesPrgRom)end end
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());table=pack(Source(a.source),authority);rows=[]
 positions=[(-11*65536,0),(-10*65536-1,0),(-10*65536,0),(-10*65536+1,0),(330*65536-1,0),(330*65536,0),(330*65536+1,0),(331*65536,0),(0x7fffffff,-0x80000000),(-0x80000000,0x7fffffff),(20*65536,30*65536),(350*65536,20*65536)]
 for model in range(16):
  for x,camera in positions:
   for ai in (0,8,65536,0xffffffff):
    i=len(rows);seed=(0,1,65535,0xffffffff)[i%4];after,value=random32_step(seed);off=int(x-camera < -10*65536 or x-camera >330*65536);cutoff=authority['source_models'][model]['offscreen_last_allowed'if off else'onscreen_last_allowed'];calls=int(not ai&8)
    rows.append(dict(slot=(0,1,63,127)[i%4],model=model,x=x,camera=camera,ai=ai,seed=seed,seed_after=after if calls else seed,calls=calls,expected=1 if ai&8 else int(value%10000<=cutoff),offscreen=off,time=50,nextthink=50,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=1,animation=5,spawn=3,respawn=4,animating=1,exists=(0,1,65536,0xffffffff)[i%4],bad='',fault=0,patch=-1,value=0))
 base=rows[0]
 for bad in ('ready','busy','common_ready','phase','model','x_tag','camera_ready','native_width','bank','base','extent','kernel_ready','kernel_busy','rng_ready','rng_busy'):
  rows.append(dict(base,bad=bad,fault=1,expected=55,seed_after=base['seed'],calls=0))
 for at,value in ((0,0),(4,2),(6,0),(6,15),(8,8),(10,256),(12,224),(14,1),(16,10000),(18,65534)):
  rows.append(dict(base,patch=at,value=value,fault=1,expected=55,seed_after=base['seed'],calls=0))
 for bad in ('camera_ready','native_width','x_tag','bank','rng_ready','rng_busy'):
  rows.append(dict(base,bad=bad,ai=8,calls=0,seed_after=base['seed'],expected=1))
 lua=OWNER_LUA[:OWNER_LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=')]
 lua='local tablebytes='+luav(list(table))+'\n'+lua.replace(' before={};',SETUP+' before={};').replace('TABLEBYTES',str(len(table))).replace('{{0x414000,18432}','{{sy.VmNativeVariant_Result,8},{sy.SourceModelEntityCopy4086_Lo,4},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{sy.VmSourceWorld_AdvanceX,4},{0x437e00,2560},{0x40c000,12288},{0x414000,18432}')
 lua+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];for _,r in ipairs({{sy.SourceRandom4086_SeedLo,c.seed_after},{sy.SourceRandom4086_CallsLo,(0xffffffff+c.calls)&0xffffffff}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('ENTITYCHANCE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceEntityNormalChance4086_Status)..'|'..dw(sy.SourceEntityNormalChance4086_Result)..'|'..dw(sy.SourceRandom4086_SeedLo)..'|'..dw(sy.SourceRandom4086_CallsLo)..'|'..word(sy.SourceEntityNormalChance4086_Offscreen))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 reporter=Reporter('M4-ENTITY-NORMAL-CHANCE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceEntityNormalChance4086_Execute','SourceEntityNormalChance4086_Ready',0xb601,[(59,0,table)],lua,reporter,batch_size=1,frame_limit=6000)
 actual=[list(map(int,l.split('ENTITYCHANCE|',1)[1].split('|')))for l in log.splitlines()if 'ENTITYCHANCE|'in l]
 expected=[[i,0,0,3 if c['fault']else 2,c['expected'],c['seed_after'],(0xffffffff+c['calls'])&0xffffffff]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v[:7],expected=e)for c,v,e in zip(rows,actual,expected)if v[:7]!=e or not c['fault']and not c['ai']&8 and v[7]!=c['offscreen']]
 reporter.check('actual current model/aiattack, source-sized camera, strict extended Q16 screen thresholds, exact cutoff/RNG/CPU/VM/CRT/entity retention and guards',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ENTITY_NORMAL_CHANCE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),numeric_policy='ACCEPTED_COMPAT_Q16_16',requires_closed_static_attackthrottle_and_global_coefficients=True,source_viewport=[320,240],normal_attack_caller_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
