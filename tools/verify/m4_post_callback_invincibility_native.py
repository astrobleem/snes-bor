"""Fresh makeinv continuation without reselecting the already-entered TYPE case."""
import argparse,hashlib,itertools,json
from pathlib import Path
from m4_default_init_tail_native import LUA as TAIL_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=TAIL_LUA.replace("put(b+8,c.platform,4)","put(b+8,c.platform,4);put(b+72,c.type,4);put(0x416800+c.slot*64,c.model);put(0x439048+c.slot*80,c.model);put(0x43904a+c.slot*80,0xb4fb);put(0x439038+c.slot*80,c.makeinv,4);set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',2);put(sy.SourceDefaultPlayer4086_TimeLo,c.time,4)")
LUA=LUA.replace("elseif c.bad=='empty'then", "elseif c.bad=='life'then set('SourceLifecycle4086_Ready',0)\n elseif c.bad=='life_sticky'then set('SourceLifecycle4086_Status',3)\n elseif c.bad=='marker'then put(0x43904a+c.slot*80,0)\n elseif c.bad=='model'then put(0x439048+c.slot*80,c.model+1)\n elseif c.bad=='minimum'then put(0x439038+c.slot*80,0x80000000,4)\n elseif c.bad=='empty'then")
LUA=LUA.replace("if c.fault==0 and c.level~=0 and c.multiple<0 then for i=0,3 do before[0x40c000+c.slot*96+i]=0 end end", "if c.fault==0 and c.time~=0 and c.makeinv~=0 then\n local function expect(off,v)for i=0,3 do before[0x439000+c.slot*80+off+i]=(v>>(i*8))&255 end end\n expect(24,1);expect(28,c.makeinv>0 and 1 or 0);expect(32,(c.time+math.abs(c.makeinv))&0xffffffff);expect(36,1)\n end")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 # Actual complete C case changes TYPE to NONE and makeinv to -20 in JUMP.
 mutation=[r for r in authority['results']if r['case']['mutation']==2 and r['case']['level']==1];assert mutation and all(r['actual']['state'][4:8]==[1,0,68,1]for r in mutation)
 base=dict(level=1,multiple=0,platform=0,wall=0,bad='',fault=0)
 rows=[dict(base,slot=s,alive=alive,type=t,model=model,time=time,makeinv=inv)for s,alive,t,model,time,inv in itertools.product((0,127),(0,1),(0,1,2,32),(0,15),(0,48,0xffffffff),(0,-20,20,-65536,65536,-2147483647,2147483647))]
 # Keep bounded private fixture below 2000 cases.
 rows=rows[::2]+[dict(base,slot=s,alive=alive,type=0,model=15,time=48,makeinv=-20)for s,alive in itertools.product((0,127),(0,1))]
 for bad in ('ready','sticky','world','pool','side','count','slot','token','token_high','life','life_sticky','marker','model','minimum'):
  for s in (0,127):rows.append(dict(rows[-1],slot=s,bad=bad,fault=1))
 r=Reporter('M4-POST-CALLBACK-INVINCIBILITY',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultPlayer4086_ApplyInvincibility','SourceDefaultPlayer4086_Ready',0xb503,[],LUA,r)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('fresh current-model makeinv after changed TYPE/model or killed entity; guards and untouched callback state',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]for i,(v,c)in enumerate(zip(results,rows))))
 report=dict(schema='BYOR_4086_POST_CALLBACK_INVINCIBILITY_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,c_mutation_cases=mutation,callback_mutation_installation_instrumented=True,actual_authored_jump_separately_proven=True,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
