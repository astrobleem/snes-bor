"""Actual common_drop compatibility predicate, landing and no-event retirement."""
import argparse,hashlib,json,struct
from pathlib import Path
from m4_lost_kill_native import LUA,prepared
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def packets(c,state,mapping,count,probe,after=False):
 rows=prepared(c,state,mapping,count,0);target=0x414000+mapping[1]*80
 for p in rows:
  if p['at']==target:
   data=bytearray(p['data']);struct.pack_into('<I',data,12,probe['y_q16']&0xffffffff);struct.pack_into('<I',data,36,0 if after and probe['compat_expected'][2]else probe['health']&0xffffffff);p['data']=list(data)
  elif p['at']==0x43eb00+mapping[1]*32:
   data=bytearray(p['data']);struct.pack_into('<H',data,0,probe['compat_expected'][0]if after else 3);p['data']=list(data)
 return rows

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--kill-authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());ka=json.loads(a.kill_authority.read_text());assert au['status']==ka['status']=='PASS'and ka['cases']==144
 cases=[r for r in ka['results']if r['case']['mode']==0 and r['case']['summon']==0 and not r['case']['sub']];rows=[]
 for i,c in enumerate(au['inputs']):
  r=cases[i%len(cases)];mapping,count=([0,127,1,2,3,4],128)if i%2 else(list(range(6)),6);kill=c['compat_expected'][2]
  rows.append(dict(c,kill=kill,before=packets(r['case'],None,mapping,count,c),after=packets(r['case'],r['actual']['state']if kill else None,mapping,count,c,True),count=count,slot=mapping[1],path=0,fault=0,bad=''))
 base=next(c for c in rows if c['kill'])
 for bad in ('ready','repeat','parent','phase','retirement','self','onkill','clear_entry','actionid','actionwide','ytag','ytaghigh','htag','htaghigh','cache'):
  rows.append(dict(base,bad=bad,fault=1))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('LIFEREADY',str(sy['SourceLifecycle4086_Ready']))
 lua=lua.replace("set('SourceWorldTick4086_Phase',2)","set('SourceWorldTick4086_Phase',6)")
 lua=lua.replace(" before={};for _,r", """ set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',1);set('SourceAI4086_Slot',c.slot);set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104)
 set('SourceCommonDrop4086_Ready',0xb5e5);set('SourceCommonDrop4086_Status',0)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',128);set('SourceModelAnimationCopy4086_Bytes',4096)
 set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);put(0x43900c+c.slot*80,5,4);put(0x416830+c.slot*64,c.base_q16,4)
 if c.bad=='ready'then set('SourceCommonDrop4086_Ready',0)
 elseif c.bad=='repeat'then set('SourceCommonDrop4086_Status',2)
 elseif c.bad=='parent'then set('SourceAI4086_State',2)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',5)
 elseif c.bad=='actionid'then put(0x43900c+c.slot*80,4,4)
 elseif c.bad=='actionwide'then put(0x43900e+c.slot*80,1)
 elseif c.bad=='ytag'then put(0x414008+c.slot*80,1)
 elseif c.bad=='ytaghigh'then put(0x41400a+c.slot*80,1)
 elseif c.bad=='htag'then put(0x414020+c.slot*80,2)
 elseif c.bad=='htaghigh'then put(0x414022+c.slot*80,1)
 elseif c.bad=='cache'then set('SourceModelAnimationCopy4086_Ready',0)end
 before={};for _,r""")
 start=lua.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.bad=='slot_changed'");end=lua.index('emu.addMemoryCallback(function()',start+len('emu.addMemoryCallback(function()'));lua=lua[:start]+lua[end:]
 lua=lua.replace("if c.fault==0 then for _,p", "if c.fault==0 then for j=0,3 do before[0x43900c+c.slot*80+j]=((c.compat_air==1 and 5 or 0)>>(j*8))&255 end;for _,p")
 lua=lua.replace('word(sy.SourceLost4086_Status)', 'word(sy.SourceCommonDrop4086_Status)')
 entry=sy['SourceCommonDrop4086_Execute'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-COMMON-DROP',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceCommonDrop4086_Execute','SourceCommonDrop4086_Ready',0xb5e5,[],lua,r,batch_size=2)
 results=[list(map(int,l.split('LOSTKILL|',1)[1].split('|')))for l in log.splitlines()if 'LOSTKILL|'in l];failures=[dict(index=i,input={k:v for k,v in c.items()if k not in ('before','after')},result=v)for i,(c,v)in enumerate(zip(rows,results))if v[:4]!=[i,0,0,3 if c['fault']else 2]or(not c['fault']and v[4:]!=[2 if c['kill']else 0,1,48])]
 r.check('explicit Q16 inair predicate, landing flags/action, signed32 health, actual retirement and guards before live writes',len(results)==len(rows)and not failures)
 d=dict(schema='BYOR_4086_COMMON_DROP_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=[{k:v for k,v in c.items()if k not in ('before','after')}for c in rows],results=results,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),kill_authority_sha256=hashlib.sha256(a.kill_authority.read_bytes()).hexdigest(),numeric_policy='ACCEPTED_COMPAT Q16 inair >=6554',source_q16_differences=au['q16_compat_differences'],world_tick_acknowledged=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
