"""Generic source walker bounds and actual no-event native retirement."""
import argparse,hashlib,json,struct
from pathlib import Path
from m4_lost_kill_native import LUA,prepared
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def packets(c,state,mapping,count,x):
 rows=prepared(c,state,mapping,count,0);target=0x414000+mapping[1]*80
 for p in rows:
  if p['at']==target:
   data=bytearray(p['data']);struct.pack_into('<I',data,12,0);struct.pack_into('<I',data,52,x&0xffffffff);p['data']=list(data)
 return rows

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--kill-authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());ka=json.loads(a.kill_authority.read_text());assert au['status']==ka['status']=='PASS'and ka['cases']==144
 cases=[r for r in ka['results']if r['case']['mode']==0 and r['case']['summon']==0 and not r['case']['sub']];rows=[]
 for i,c in enumerate(au['inputs']):
  r=cases[i%len(cases)];mapping,count=([0,127,1,2,3,4],128)if i%2 else(list(range(6)),6)
  rows.append(dict(c,before=packets(r['case'],None,mapping,count,c['x_q16']),after=packets(r['case'],r['actual']['state']if c['kill']else None,mapping,count,c['x_q16']),count=count,slot=mapping[1],path=0,fault=0,bad=''))
 base=next(c for c in rows if c['kill'])
 for bad in ('ready','repeat','parent','phase','retirement','self','onkill','clear_entry','actionid','actionwide','hres','leftoverflow','rightoverflow','xtag','xtaghigh','cache'):
  rows.append(dict(base,bad=bad,fault=1))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('LIFEREADY',str(sy['SourceLifecycle4086_Ready']))
 lua=lua.replace("set('SourceWorldTick4086_Phase',2)","set('SourceWorldTick4086_Phase',6)")
 lua=lua.replace(" before={};for _,r", """ set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',2);set('SourceAI4086_Slot',c.slot);set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104)
 set('SourceAnythingWalk4086_Ready',0xb5e4);set('SourceAnythingWalk4086_Status',0);set('SourceAnythingWalk4086_HRes',c.hres)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',128);set('SourceModelAnimationCopy4086_Bytes',4096)
 set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('VmSourceWorld_AdvanceX',c.ax_q16,4);put(0x439000+c.slot*80,15,4)
 if c.bad=='ready'then set('SourceAnythingWalk4086_Ready',0)
 elseif c.bad=='repeat'then set('SourceAnythingWalk4086_Status',2)
 elseif c.bad=='parent'then set('SourceAI4086_State',1)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',5)
 elseif c.bad=='actionid'then put(0x439000+c.slot*80,2,4)
 elseif c.bad=='actionwide'then put(0x439002+c.slot*80,1)
 elseif c.bad=='hres'then set('SourceAnythingWalk4086_HRes',32688)
 elseif c.bad=='leftoverflow'then set('VmSourceWorld_AdvanceX',0x80000000,4)
 elseif c.bad=='rightoverflow'then set('VmSourceWorld_AdvanceX',0x7fffffff,4)
 elseif c.bad=='xtag'then put(0x414030+c.slot*80,1)
 elseif c.bad=='xtaghigh'then put(0x414032+c.slot*80,1)
 elseif c.bad=='cache'then set('SourceModelAnimationCopy4086_Ready',0)end
 before={};for _,r""")
 start=lua.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.bad=='slot_changed'");end=lua.index('emu.addMemoryCallback(function()',start+len('emu.addMemoryCallback(function()'));lua=lua[:start]+lua[end:]
 lua=lua.replace('word(sy.SourceLost4086_Status)', 'word(sy.SourceAnythingWalk4086_Status)')
 entry=sy['SourceAnythingWalk4086_Execute'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-ANYTHING-WALK',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceAnythingWalk4086_Execute','SourceAnythingWalk4086_Ready',0xb5e4,[],lua,r,batch_size=2)
 results=[list(map(int,l.split('LOSTKILL|',1)[1].split('|')))for l in log.splitlines()if 'LOSTKILL|'in l];failures=[dict(index=i,input={k:v for k,v in c.items()if k not in ('before','after')},result=v)for i,(c,v)in enumerate(zip(rows,results))if v[:4]!=[i,0,0,3 if c['fault']else 2]or(not c['fault']and v[4:]!=[2 if c['kill']else 0,1,48])]
 r.check('strict pinned bounds, actual retirement state, current dead self retained, CPU and physical guard rejection',len(results)==len(rows)and not failures)
 d=dict(schema='BYOR_4086_ANYTHING_WALK_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=[{k:v for k,v in c.items()if k not in ('before','after')}for c in rows],results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),kill_authority_sha256=hashlib.sha256(a.kill_authority.read_bytes()).hexdigest(),native_coordinate_policy='checked Q16.16; bounds overflow explicitly rejected',world_tick_acknowledged=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
