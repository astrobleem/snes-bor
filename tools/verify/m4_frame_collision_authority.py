"""Compare collision IR to verbatim pinned loader numeric case bodies.

This isolates loader state; it does not claim engine combat or native gameplay.
"""
import argparse
import hashlib
from fractions import Fraction
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source,key
from source_profile import document,discover
from source_frame_state_4086 import derive,loader_frames,ATTACK_TYPES
from dialect_4086 import ENGINE_COMMIT


def run(source, output, engine):
    raw=subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':engine/openbor.c'])
    text=raw.decode()
    def section(start,end):
        pos=text.index(start,text.index('case CMD_MODEL_BBOX:'))
        return text[pos:text.index(end,pos)]
    # Case text is unchanged. Only the surrounding test services are mocked.
    attack=section('case CMD_MODEL_ATTACK:\n','            case CMD_MODEL_BLAST:')
    boxes=section('case CMD_MODEL_BBOX:\n','            case CMD_MODEL_PLATFORM:')
    drop=section('case CMD_MODEL_DROPV:\n','            case CMD_MODEL_OTG:')
    # COUNTERATTACK precedes BBOX in the source switch.
    pos=text.index('case CMD_MODEL_COUNTERATTACK:')
    counter=text[pos:text.index('            case CMD_MODEL_THROWFRAME:',pos)]
    force=section('case CMD_MODEL_FORCEDIRECTION:\n','            case CMD_MODEL_DAMAGEONLANDING:')
    pos=text.index('bbox_con[0] = bbox[0] - offset[0];')
    frame=text[pos:text.index('                //attack.attack_coords[4]',pos)]
    commands=['ANIM','FRAME','OFFSET','DELAY','BBOX','BBOXZ']+[n.upper() for n in ATTACK_TYPES]+[
        'ATTACK_ETC','ATTACKZ','HITZ','DROPV','COUNTERATTACK','FORCEDIRECTION']
    enums=', '.join('CMD_MODEL_'+n for n in commands)
    atk_enums='ATK_NORMAL, ATK_NORMAL2, ATK_NORMAL3, ATK_NORMAL4, ATK_BLAST, ATK_BURN, ATK_FREEZE, ATK_SHOCK, ATK_STEAL, ATK_NORMAL5, ATK_NORMAL6, ATK_NORMAL7, ATK_NORMAL8, ATK_NORMAL9, ATK_NORMAL10, ATK_ITEM'
    code='''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GAME_SPEED 200
#define MAX_ATKS 20
#define STA_ATKS 10
#define GET_INT_ARG(n) atoi(args[n])
#define GET_FLOAT_ARG(n) ((float)atof(args[n]))
typedef struct { float x,y,z; } axis;
typedef struct { int attack_coords[6],attack_force,attack_drop,no_block,no_flash,pause_add,attack_type,freeze,forcemap,steal,counterattack,force_direction; unsigned freezetime; axis dropv; } Attack;
typedef struct { Attack *smartbomb; } Model;
enum { '''+enums+''' };
enum { '''+atk_enums+''' };
int main(void) {
    char args[11][64], command[64]; int cmd,n,j,tempInt,newanim=1;
    int bbox[6]={0},bbox_con[6],abox[4]={0},offset[2]={0},delay=0;
    Attack attack={0},*pattack; Model model={0},*newchar=&model;
    axis default_model_dropv={1.2f,3.f,0.f};
    while(scanf("%d %d",&cmd,&n)==2) {
        memset(args,0,sizeof(args)); for(j=1;j<=n;j++) scanf("%63s",args[j]);
        switch(cmd) {
        case CMD_MODEL_ANIM: memset(bbox,0,sizeof(bbox)); memset(abox,0,sizeof(abox)); memset(offset,0,sizeof(offset)); memset(&attack,0,sizeof(attack)); break;
        case CMD_MODEL_OFFSET: offset[0]=GET_INT_ARG(1); offset[1]=GET_INT_ARG(2); break;
        case CMD_MODEL_DELAY: delay=GET_INT_ARG(1); break;
        '''+boxes+attack+drop+counter+force+'''
        case CMD_MODEL_FRAME:
        '''+frame+'''
        printf("%d %d %d", delay*GAME_SPEED/100, (bbox_con[2]-bbox_con[0])&&(bbox_con[3]-bbox_con[1]), (attack.attack_coords[2]-attack.attack_coords[0])&&(attack.attack_coords[3]-attack.attack_coords[1]));
        for(j=0;j<6;j++) printf(" %d",bbox_con[j]);
        for(j=0;j<6;j++) printf(" %d",attack.attack_coords[j]);
        printf(" %d %d %d %d %d %d %d %u %d %d %d %.9g %.9g %.9g\\n",attack.attack_force,attack.attack_drop,attack.no_block,attack.no_flash,attack.pause_add,attack.attack_type,attack.freeze,attack.freezetime,attack.forcemap,attack.counterattack,attack.force_direction,attack.dropv.y,attack.dropv.x,attack.dropv.z);
        break;
        }
    }
    return 0;
}
'''
    output.mkdir(parents=True,exist_ok=True)
    c=output/'loader_probe.c'; exe=output/'loader_probe.exe'; c.write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    built=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','-fe='+str(exe.resolve()),str(c.resolve())],cwd=output,env=env,capture_output=True,text=True)
    if built.returncode: raise RuntimeError(built.stdout+built.stderr)
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs); rows=[]
    for model in structure['models']:
        active=False
        for d in docs[key(model['source_path'])]['directives']:
            name=d['directive'].upper()
            if name=='ANIM': active=True
            if not active or name not in commands: continue
            vals=[] if name in ('ANIM','FRAME') else d['values']
            rows.append(str(commands.index(name))+' '+str(len(vals))+' '+' '.join(vals))
    ir=derive(source); expected=[f for a in ir['animations'] for f in a['frames']]
    source_frames=len(expected)
    probe_rows=[]
    for n,line in enumerate(('anim idle','delay 3','offset 4 10','bbox 5 12 8 20 2 6',
            'freeze 7 14 12 30 5 0.5','attackz 2 6','frame one.png','frame two.png',
            'attack 7 14 12 30 2','dropv 4 0 0','frame three.png',
            'attack 0 0 0 0','frame four.png','anim idle',
            'attack2 0 0 5 8 3','frame five.png')):
        words=line.split(); probe_rows.append(dict(directive=words[0],values=words[1:],line=n+1))
        vals=[] if words[0] in ('anim','frame') else words[1:]
        rows.append(str(commands.index(words[0].upper()))+' '+str(len(vals))+' '+' '.join(vals))
    expected.extend(f for a in loader_frames(probe_rows) for f in a['frames'])
    observed=subprocess.run([str(exe.resolve())],input='\n'.join(rows)+'\n',text=True,capture_output=True,check=True).stdout.splitlines()
    if len(observed)!=len(expected): raise AssertionError((len(observed),len(expected)))
    mismatches=[]; attacks=0; vulnerable=0
    fields='attack_force attack_drop no_block no_flash pause_add attack_type freeze freezetime forcemap counterattack force_direction'.split()
    for index,(line,f) in enumerate(zip(observed,expected)):
        v=line.split(); ints=list(map(int,v[:26])); valid=True
        valid &= ints[:3]==[f['delay_ticks'],int(f['vulnerable']),int(f['attack'] is not None)]
        if f['bbox'] is not None: valid &= ints[3:9]==f['bbox']; vulnerable+=1
        if f['attack'] is not None:
            attacks+=1; a=f['attack']; valid &= ints[9:15]==a['attack_coords']
            valid &= ints[15:26]==[a[n] for n in fields]
            floats=[struct.unpack('<f',struct.pack('<f',float(Fraction(n))))[0] for n in a['dropv']]
            valid &= all(abs(float(s)-e)<=max(1e-7,abs(e)*1e-8) for s,e in zip(v[26:],floats))
        if not valid: mismatches.append(dict(index=index,expected=f,observed=line))
    r=dict(status='PASS' if not mismatches else 'FAIL',engine_authority=ENGINE_COMMIT,
        engine_source_sha256=hashlib.sha256(raw).hexdigest(),probe_sha256=hashlib.sha256(code.encode()).hexdigest(),
        source_frames=source_frames,synthetic_frames=len(expected)-source_frames,
        frames=len(expected),vulnerable_frames=vulnerable,attack_frames=attacks,mismatches=mismatches,
        scope='verbatim numeric collision loader bodies; external media services and engine runtime excluded',
        native_gameplay_proven=False)
    (output/'report.json').write_text(json.dumps(r,indent=2)+'\n'); print(json.dumps(r))
    if mismatches: raise AssertionError('FRAME_COLLISION_AUTHORITY_MISMATCH')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
    a=p.parse_args();run(Source(a.source),a.output,a.engine)
