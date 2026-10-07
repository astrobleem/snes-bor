"""Full pinned update_animation timed branch, with service calls observed."""
import argparse, ast, hashlib, json, os, subprocess
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from source_animation_step import derive
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('source','native-report','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 native=json.loads(a.native_report.read_text());assert native['status']=='PASS'and not native['guards']
 rows=native['inputs'];animations={an['handle']:an for an in derive(Source(a.source))['animations']}
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');function=extract(raw,'update_animation')
 tree=ast.parse(Path('tools/bor_compile/source_update_animation_prefix_authority.py').read_text())
 assignment=next(n for n in ast.walk(tree)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets))
 # Reuse only the C declarations and instrumented service stubs, never the
 # previous authority's mutated function or its expected results.
 expression=assignment.value
 while isinstance(expression,ast.BinOp):expression=expression.left
 header=ast.literal_eval(expression)
 header=header.replace('void update_frame(entity*e,int f){updates++;}','int requested_frame;void update_frame(entity*e,int f){updates++;requested_frame=f;}')
 code=header+function+'\nint main(void){\n';expected=[]
 for c in rows:
  an=animations[c['handle']]
  code+='memset(self,0,sizeof(*self));memset(&anim,0,sizeof(anim));self->animation=&anim;self->modeldata.sleepwait=1000;self->animnum=65536;self->sleeptime=123;self->update_mark=0x80000002u;thaws=maps=updates=kills=0;requested_frame=-1;level=&scene;'
  for name,value in [('animpos',c['frame']),('animating',c['direction']),('nextanim',c['time']if c['equal']else c['time']^65536)]:
   code+='self->'+name+'='+str(value)+('u'if value>=0 else'')+';'
  code+='self->autokill='+str(c.get('autokill',0))+'u;time='+str(c['time'])+'u;anim.numframes='+str(an['count'])+';anim.loop.mode='+str(an['loop_mode'])+';anim.loop.frame.min='+str(an['loop_min'])+';anim.loop.frame.max='+str(an['loop_max'])+';update_animation();'
  code+='printf("%u,%d,%u,%d,%d,%d\\n",self->sleeptime,self->animating,self->update_mark,updates,kills,requested_frame);\n'
  expected.append([(c['time']+1000)&0xffffffff,0 if c['action']in (2,3) else c['direction'],0x80000003 if c['action']==1 else 0x80000002,int(c['action']==1),int(c['action']==3),c['result']if c['action']==1 else -1])
 code+='return 0;}\n';(a.output/'animation.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','animation.c','-fe=animation.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
 log=subprocess.check_output([str(a.output/'animation.exe')],text=True);(a.output/'authority.log').write_text(log)
 actual=[list(map(int,line.split(',')))for line in log.splitlines()];assert actual==expected
 r=dict(schema='BYOR_4086_UPDATE_ANIMATION_AUTHORITY_V1',status='PASS',engine_commit=ENGINE_COMMIT,source_function_sha256=hashlib.sha256(function.encode()).hexdigest(),source_function_unmodified=True,cases=len(rows),native_report_sha256=hashlib.sha256(a.native_report.read_bytes()).hexdigest(),actual=actual,expected=expected,instrumented_services=['update_frame','kill','unfrozen','ent_set_colourmap'],domain='Source animation rules; signed playback, deadline equality and high-word mismatch, frame mark, sleep, terminal stop and actual input autokill values',motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(rows),'literal full update_animation timed cases')

if __name__=='__main__':main()
