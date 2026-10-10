"""Closed source completion slow-motion policy; ordinary clock stays unchanged."""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT


def derive(source):
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 header=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
 enum=re.search(r'typedef enum\s*\{([^}]+)\}\s*e_slow_motion_enable;',header,re.S)[1];enum=re.sub(r'/\*.*?\*/','',enum,flags=re.S)
 if [v.strip()for v in enum.split(',')]!=['SLOW_MOTION_OFF','SLOW_MOTION_ON']:raise ValueError('COMPLETION_CLOCK_SWITCH_ENUM_AUTHORITY')
 if 'level = calloc(1, sizeof(*level));'not in raw or raw.count('level->noslow =')!=1:raise ValueError('COMPLETION_CLOCK_NOSLOW_DEFAULT_AUTHORITY')
 init=re.search(r's_slow_motion\s+slowmotion\s*=\s*\{.*?\};',raw,re.S)[0]
 if not re.search(r'\.toggle\s*=\s*SLOW_MOTION_OFF',init)or not re.search(r'\.counter\s*=\s*0',init)or not re.search(r'\.duration\s*=\s*2',init):raise ValueError('COMPLETION_CLOCK_DEFAULT_AUTHORITY')
 start=raw.index('        if((level_completed && !level->noslow && !tospeedup)');end=raw.index('        while(time < newtime)',start);block=raw[start:end]
 for _,(name,_)in source.index.items():
  if name.lower().endswith(('.txt','.c')):
   text=source.read(name).decode('latin1')
   if re.search(r'\bslowmotion\b|^\s*noslow\b',text,re.I|re.M):raise ValueError('COMPLETION_CLOCK_DYNAMIC_POLICY_REQUIRED:'+name)
 # The target's existing clock has reserved bytes through 7FFA4F. None of
 # these policy bytes occur in the current source clock's code or equates.
 clock=Path('src/core/vm/vm_source_clock.pasm').read_text(encoding='cp1252')
 if re.search(r'\$7FFA(?:3[A-F]|4[0-9A-F])\b',clock,re.I):raise ValueError('COMPLETION_CLOCK_RESERVED_TAIL_USED')
 return dict(schema='BYOR_COMPLETION_CLOCK_CLOSED_POLICY_V1',engine_commit=ENGINE_COMMIT,source_block=block,source_block_sha256=hashlib.sha256(block.encode('latin1')).hexdigest(),initializer_sha256=hashlib.sha256(init.encode('latin1')).hexdigest(),duration=2,toggle=0,noslow=0,policy_controls=0x7ffa3a,policy_bytes=8,within_existing_clock_reservation=True,noslow_calloc_default_authority=True,source_switch_enum=[0,1],source_clock_field_epoch_adaptation='Existing explicit NTSC field observation; SDL update-call cadence equivalence unclaimed',source_unsigned_clock_wrap_equivalence=False,production_clock_consumer_bound=False,production_unload_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def emit(req,speedup,sy):
 if req['duration']!=2 or req['toggle']or req['noslow']or req['policy_controls']!=0x7ffa3a or req['policy_bytes']!=8:raise ValueError('COMPLETION_CLOCK_CLOSED_POLICY')
 w=req['policy_controls'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CompletionClock_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='CompletionClock_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp CompletionClock_'+n+'\n'+k+':\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');branch('bne')
 label('Start');put(' php\n rep #$39\n phx\n phy');require(sy['SourceClock4086_Ready'],0xb4c5)
 put(f' lda #0\n sta.l {w}+2\n lda.l {sy["SourceClock4086_LastFieldsLo"]}\n sec\n sbc #1\n sta.l {w}+4\n lda.l {sy["SourceClock4086_LastFieldsHi"]}\n sbc #0\n sta.l {w}+6\n lda #$B6BE\n sta.l {w}\n jmp CompletionClock_Good')
 label('Filter');put(' php\n rep #$39\n phx\n phy');require(w,0xb6be);require(sy['SourceClock4086_Ready'],0xb4c5);require(sy['SourceForeignWork_Ready'],0xb671);require(sy['SourceScrollerPrefix4086_Ready'],0xb5d7)
 put(f' lda.l {w}+2\n cmp #3');branch('bcs')
 put(f' lda.l {sy["SourceClock4086_Running"]}\n cmp #2');branch('bcs');put(f' lda.l {sy["SourceClock4086_Due"]}\n cmp #51');branch('bcs');put(f' lda.l {speedup}\n cmp #2');branch('bcs')
 put(f' lda.l {sy["SourceClock4086_LastFieldsLo"]}\n cmp.l {w}+4');branch('bne','Observation');put(f' lda.l {sy["SourceClock4086_LastFieldsHi"]}\n cmp.l {w}+6');branch('beq','Good')
 label('Observation')
 for off in(0,2):put(f' lda.l {sy["SourceClock4086_LastFieldsLo"]}+{off}\n sta.l {w}+{4+off}')
 put(f' lda.l {sy["SourceClock4086_Running"]}');branch('beq','Good')
 put(f' lda.l {sy["SourceScrollerPrefix4086_Completed"]}\n ora.l {sy["SourceScrollerPrefix4086_Completed"]}+2');branch('beq','Counter');put(f' lda.l {speedup}');branch('bne','Counter');put(f' lda.l {w}+2\n cmp #2');branch('beq','Counter');put(f' lda #0\n sta.l {sy["SourceClock4086_Due"]}')
 label('Counter');put(f' lda.l {w}+2\n inc a\n cmp #3');branch('bcc','WriteCounter');put(' lda #0')
 label('WriteCounter');put(f' sta.l {w}+2')
 label('Good');put(f' lda.l {sy["SourceClock4086_Due"]}\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(' ply\n plx\n plp\n sec\n rtl')
 # Only the tospeedup projection of unload_level, not its other side effects.
 label('UnloadSpeedup');put(f' php\n rep #$20\n pha\n lda #0\n sta.l {speedup}\n pla\n plp\n rtl')
 return '\n'.join(lines)+'\n'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);req=derive(Source(a.source));rows=[dict(pause=p,completed=c,speedup=s,interval=i,counter=n)for p,c,s,i,n in itertools.product((0,1),(0,1,-1,65536),(0,1),(0,1,3,50),(0,1,2))]
 code='''#include <stdio.h>
typedef unsigned u32;
#define SLOW_MOTION_OFF 0
#define SLOW_MOTION_ON 1
struct {unsigned toggle,counter,duration;}slowmotion;
struct {int noslow;}stage,*level=&stage;
u32 time,newtime,interval;int level_completed,tospeedup,pause;
int main(void){unsigned p,c,s,i,n;while(scanf("%u %u %u %u %u",&p,&c,&s,&i,&n)==5){time=48;newtime=0;pause=p;level_completed=(int)c;tospeedup=s;interval=i;slowmotion.toggle=0;slowmotion.duration=2;slowmotion.counter=n;level->noslow=0;if(!pause){
'''+req['source_block']+'''
}printf("%u %u\\n",newtime>time?newtime-time:0,slowmotion.counter);}return 0;}
'''
 (a.output/'completion.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','completion.c','-fe=completion.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr);assert proc.returncode==0;log=subprocess.check_output([str(a.output/'completion.exe')],input='\n'.join(' '.join(str(c[k]&0xffffffff)for k in ('pause','completed','speedup','interval','counter'))for c in rows)+'\n',text=True);actual=[list(map(int,l.split()))for l in log.splitlines()];expected=[[0 if c['pause']or(c['completed']and not c['speedup']and c['counter']!=2)else c['interval'],c['counter']if c['pause']else(c['counter']+1)%3]for c in rows];ok=actual==expected and len(actual)==len(rows);result=dict(req,status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,native_consumer_bound=False);(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(rows),'pinned completion clock cases');assert ok

if __name__=='__main__':main()
