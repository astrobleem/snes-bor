"""Pinned literal post-checkdeath common_takedamage tail, explicit child trace."""
import argparse,hashlib,itertools,json,os,re,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_landing_callback_authority import PREAMBLE
from source_damage_tail_4086 import run
FLOATS=('y','count','model_count','vx','vy','vz','dropx','dropy','dropz','defense_pain')
STATE=('landing','escape','action','vx','vy','vz','count','ktime','other_action','other_stall','release')

def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def cases():
 b=dict(type=2,force=7,y=0.,dead=0,landing=0,opponent=1,other_grabbing=0,frozen=0,drop=0,escapehits=0,escape=3,health=100,weaploss=0,falldie=0,vx=1.,vy=2.,vz=3.,damagetype=0,dropx=3.,dropy=2.,dropz=0.,direction=0,attack_landing=0,count=4.,model_count=3.,ktime=47,valid_fall=1,grab=0,no_pain=0,nopain=0,defense_pain=0.,action=0,other_action=0,time=48,other_stall=17,release=19,attack_drop=0,no_block=0,guardcost=0,jugglecost=0,pause_add=0)
 rows=[dict(b,**dict(zip(('type','drop','health','weaploss','falldie','valid_fall'),v)))for v in itertools.product((1,2,3),(-1,0,1),(-1,0,1,100),(-1,0,1,2,3),(0,1,2),(0,1))]
 for n,vs in dict(y=(-251.,-250.,-249.),dead=(-1,1),landing=(-1,1),opponent=(0,),other_grabbing=(1,),escapehits=(-1,1),escape=(-3,0),frozen=(-1,1),grab=(-1,1),no_pain=(-1,1),nopain=(-1,1),defense_pain=(-1.,6.,7.,8.),direction=(-1,1,2),damagetype=(-1,19),attack_landing=(-1,7),model_count=(-2.5,0.,3.5),time=(0,4294967195,4294967295),dropx=(-1.5,0.),dropy=(-2.5,0.),dropz=(-3.5,2.5),attack_drop=(-1,1),no_block=(1,),guardcost=(7,),jugglecost=(8,),pause_add=(9,)).items():
  for v,t,d,h,g in itertools.product(vs,(1,2),(0,1),(-1,100),(0,1)):
   rows.append(dict(b,**{n:v,'type':t,'drop':d,'health':h,'grab':g}))
 # Joint predicates and the grab timeout wrapping branch.
 for v in itertools.product((0,1),repeat=7):
  rows.append(dict(b,**dict(zip(('frozen','nopain','no_pain','grab','opponent','other_grabbing','dead'),v))))
 return rows

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');header=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
 constants={n:re.search(r'^#define\s+'+n+r'\s+([^\r\n]+)',header,re.M)[0]for n in ('GAME_SPEED','GRAB_STALL','PIT_DEPTH')}
 body=extract(raw,'common_takedamage');start=body.index('    if(self->modeldata.type & TYPE_PLAYER)',body.index('checkdeath('));tail=body[start:]
 pre=PREAMBLE
 for n in constants:pre=re.sub(r'^#define '+n+r' .*$',constants[n],pre,flags=re.M)
 pre=pre.replace('int events[256],ne,','int events[256],ne,')
 replacements={
 'control_rumble':'void control_rumble(int p,int f){event(1);event(f);}',
 'player_die':'void player_die(void){event(2);}', 'kill':'void kill(entity *e){event(3);}',
 'ent_unlink':'void ent_unlink(entity *e){event(4);}', 'dropweapon':'void dropweapon(int n){event(5);event(n);}',
 'set_death':'void set_death(entity *e,int t,int r){event(6);event(t);event(r);}',
 'toss':'void toss(entity *e,float f){event(7);event(fbits(f));}',
 'set_fall':'int valid_fall;int set_fall(entity *e,int t,int r,entity *o,int f,int d,int b,int g,int j,int p){event(8);event(t);event(r);event(f);event(d);event(b);event(g);event(j);event(p);return valid_fall;}',
 'set_pain':'void set_pain(entity *e,int t,int r){event(9);event(t);event(r);}' }
 pre=pre.replace('void unexpected(void)', 'unsigned fbits(float f){unsigned n;memcpy(&n,&f,4);return n;}\nfloat fvalue(unsigned n){float f;memcpy(&f,&n,4);return f;}\nvoid unexpected(void)')
 for n,v in replacements.items():pre=re.sub(r'^(?:void|int) '+n+r'\(.*$',lambda m:v,pre,flags=re.M)
 rows=cases();fields=list(rows[0]);mapping={
 'type':'victim.modeldata.type','force':'attack.attack_force','y':'victim.position.y','dead':'victim.dead','landing':'victim.damage_on_landing','opponent':'victim.opponent','other_grabbing':'opponent.grabbing','frozen':'victim.frozen','drop':'victim.drop','escapehits':'victim.modeldata.escapehits','escape':'victim.escapecount','health':'victim.health','weaploss':'victim.modeldata.weaploss[0]','falldie':'victim.modeldata.falldie','vx':'victim.velocity.x','vy':'victim.velocity.y','vz':'victim.velocity.z','damagetype':'victim.damagetype','dropx':'attack.dropv.x','dropy':'attack.dropv.y','dropz':'attack.dropv.z','direction':'victim.direction','attack_landing':'attack.damage_on_landing','count':'victim.knockdowncount','model_count':'victim.modeldata.knockdowncount','ktime':'victim.knockdowntime','valid_fall':'valid_fall','grab':'attack.grab','no_pain':'attack.no_pain','nopain':'victim.modeldata.nopain','defense_pain':'victim.defense[0].pain','time':'time','other_stall':'opponent.stalltime','release':'victim.releasetime','attack_drop':'attack.attack_drop','no_block':'attack.no_block','guardcost':'attack.guardcost','jugglecost':'attack.jugglecost','pause_add':'attack.pause_add'}
 code=pre+'\nint tail_probe(entity *other,s_attack *attack){\n'+tail+'\nint main(void){unsigned v['+str(len(fields))+'];int ret,j;s_attack attack;while(scanf("'+' '.join('%u'for n in fields)+'",'+','.join('&v['+str(i)+']'for i in range(len(fields)))+')=='+str(len(fields))+'){memset(&victim,0,sizeof(victim));memset(&opponent,0,sizeof(opponent));memset(&attack,0,sizeof(attack));self=&victim;ne=0;\n'
 for i,n in enumerate(fields):
  if n in ('action','other_action'):continue
  val=f'v[{i}]'
  if n in FLOATS:val=f'fvalue({val})'
  elif n=='opponent':val=f'({val}?&opponent:NULL)'
  elif n=='other_grabbing':val=f'({val}?self:NULL)'
  elif n!='time':val=f'(int){val}'
  code+=mapping[n]+'='+val+';\n'
 code+='ret=tail_probe(&opponent,&attack);'
 expr=['ret','victim.damage_on_landing','victim.escapecount','victim.takeaction==common_fall?1:victim.takeaction==common_pain?2:0','fbits(victim.velocity.x)','fbits(victim.velocity.y)','fbits(victim.velocity.z)','fbits(victim.knockdowncount)','victim.knockdowntime','opponent.takeaction==common_grabattack?3:0','opponent.stalltime','victim.releasetime']
 code+='printf("'+' '.join('%u'for e in expr)+'|",'+','.join(expr)+');for(j=0;j<ne;j++)printf("%s%u",j?" ":"",(unsigned)events[j]);puts("");}return 0;}\n'
 (a.output/'authority.c').write_text(code,encoding='latin1');env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','authority.c','-fe=authority.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
 if q.returncode:raise ValueError('DAMAGE_TAIL_C_BUILD:'+q.stdout+q.stderr)
 q=subprocess.run([str(a.output/'authority.exe')],input=''.join(' '.join(str(bits(r[n])if n in FLOATS else r[n]&0xffffffff)for n in fields)+'\n'for r in rows),capture_output=True,text=True);(a.output/'authority.log').write_text(q.stdout)
 actual=[[list(map(int,v.split()))for v in line.split('|')]for line in q.stdout.splitlines()];expected=[]
 for r in rows:
  ret,e,events=run(r);state=[ret]+[bits(e[n])if n in FLOATS else e[n]&0xffffffff for n in STATE];trace=[]
  for ev in events:
   trace.extend([ev[0]]+[bits(x)if ev[0]==7 else x&0xffffffff for x in ev[1:]])
  expected.append([state,trace])
 failures=[dict(index=i,input=rows[i],actual=x,expected=y)for i,(x,y)in enumerate(zip(actual,expected))if x!=y]
 report=dict(schema='BYOR_COMMON_DAMAGE_TAIL_AUTHORITY_V1',status='PASS'if q.returncode==0 and actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),observed_cases=len(actual),literal_tail_unmodified=True,tail_sha256=hashlib.sha256(tail.encode('latin1')).hexdigest(),full_function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),constants=constants,inputs=rows,failures=failures,output_sha256=hashlib.sha256(q.stdout.encode()).hexdigest(),instrumented_child_services=list(replacements),proof_domain='post-checkdeath fields; binary32 velocities/counts; attack_type0 defense; valid non-self other; no signed overflow; child trace only',native_tail_bound=False,full_common_takedamage_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'tail cases',len(failures),'mismatches');print(json.dumps(failures[:2],indent=2))
 if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
