"""Source spawn descriptors for immutable stages with empty terrain geometry.

This compiles the literal spawnplayer placement plan offline. Nonempty wall or
hole stages require a live query owner and are reported explicitly as unbound.
Camera translation belongs to smartspawn, not these relative descriptors.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_default_drop_context import derive as drop_context
from source_player_spawn_4086 import spawnplayer
from source_binary32_q16 import project
from dialect_4086 import ENGINE_COMMIT
from source_model_core_4086 import integer


def placements(width,minimum,maximum,direction,spawns):
    if width<=0 or minimum>maximum:raise ValueError('SPAWN_INPUT_GEOMETRY_DOMAIN')
    result=[]
    for index in range(4):
        players=[dict(name='source-player',colourmap=0,spawnhealth=0,spawnmp=0,weapnum=0)for _ in range(4)]
        state=dict(players=players,level=dict(spawn=spawns,scrolldir=direction,setweap=0),hres=width,minz=minimum,maxz=maximum,advancex=0,max_wall_height=1000,rush_policy=0,currentspawnplayer=-1)
        descriptor=spawnplayer(state,index,lambda x,z:None,lambda x,z:False,lambda d:dict(health=1,mp=0,model_health=1,model_mp=0),lambda *args:None)
        x,z=descriptor['position']['x'],descriptor['position']['z']
        bits=[struct.unpack('<I',struct.pack('<f',v))[0]for v in (x,z)]
        q16=[project(v)for v in bits]
        if any(struct.unpack('<f',struct.pack('<I',v))[0]!=q/65536 for v,q in zip(bits,q16)):raise ValueError('SPAWN_INPUT_EXACT_Q16_REQUIRED')
        result.append(dict(index=index,x_binary32=bits[0],z_binary32=bits[1],x_q16=q16[0],z_q16=q16[1],flip=descriptor['flip']))
    return result


def derive(source):
    contexts=drop_context(source)['stages'];by_path={key(s['source_path']):s for s in contexts}
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs)
    z=[160,232];seen={};stages=[]
    for row in docs[key(structure['levels_path'])]['directives']:
        if row['directive']=='z':
            values=list(row['values'])+['0','0']
            for i in range(2):
                value=integer(values,i)
                z[i]=value if value>0 else (160,232)[i]
        if row['directive'] not in ('file','stage')or not row['values']:continue
        path=key(row['values'][0])
        if path not in by_path:continue
        if path in seen:
            if seen[path]!=z:raise ValueError('SPAWN_INPUT_REPEATED_STAGE_Z_CONTEXT')
            continue
        seen[path]=list(z);context=by_path[path];doc=docs[path];spawns=[(0,0)]*4;gaps=[]
        for r in doc['directives']:
            if r['directive'] in ('wall','hole','endhole'):gaps.append('SOURCE_SPAWN_NONEMPTY_'+r['directive'].upper()+'_QUERY_REQUIRED')
            if r['directive'] in ('spawn1','spawn2','spawn3','spawn4'):
                values=list(r['values'])+['0','0'];spawns[int(r['directive'][-1])-1]=(integer(values,0),integer(values,1))
        stage=dict(stage_id=context['stage_id'],source_path=context['source_path'],source_sha256=doc['sha256'],source_width=context['source_width'],minimum_z=z[0],maximum_z=z[1],scroll=context['scroll'],spawn_offsets=spawns,diagnostics=sorted(set(gaps)),capability='SOURCE_EMPTY_TERRAIN_SPAWN_INPUTS'if not gaps else'UNBOUND_SOURCE_TERRAIN_SPAWN_INPUTS')
        if not gaps:stage['placements']=placements(context['source_width'],z[0],z[1],8 if context['scroll']=='left'else 0,spawns)
        stages.append(stage)
    return dict(schema='BYOR_4086_PLAYER_SPAWN_INPUTS_V1',engine_commit=ENGINE_COMMIT,stages=stages,source_pak_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest() if hasattr(source,'path')else None,native_placement_bound=False,smartspawn_camera_translation_bound=False,full_spawnplayer_bound=False,no_color_reduction=True)


def emit_stage(stage,sy):
    """Initial-camera native placement, A=index and X/Y=foreign generation.

    Publishes actual ctor inputs only after checked stage/camera admission.
    Nonzero camera, changed geometry or stale owner must use a separate owner.
    No terrain/constructor child is acknowledged here.
    """
    if stage['diagnostics']or stage['capability']!='SOURCE_EMPTY_TERRAIN_SPAWN_INPUTS':raise ValueError('SPAWN_INPUT_EMPTY_TERRAIN_REQUIRED')
    if [row['index']for row in stage['placements']]!=list(range(4)):raise ValueError('SPAWN_INPUT_INDEX_ROWS')
    if any(row['flip']not in (0,1)or any(not -0x80000000<=row[name]<0x80000000 for name in ('x_q16','z_q16'))for row in stage['placements']):raise ValueError('SPAWN_INPUT_NATIVE_DOMAIN')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SpawnInputs_'+n+':\n.a16\n.i16')
    def guard(op):
        nonlocal serial
        serial+=1;k='SpawnInputs_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp SpawnInputs_Bad\n'+k+':\n.a16\n.i16')
    label('Apply');put(' php\n rep #$39\n pha\n phx\n phy');put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs')
    for name,value in (('VmSourceWorld_Ready',0xb4a3),('VmSourceWorld_Level',1),('SourceEnvironment4086_Ready',0xb4d1),('SourceEnvironment4086_Stage',stage['stage_id']),('SourceEnvironment4086_WallCount',0),('SourceCtorState4086_Ready',0xb5c2),('VmSourceWorld_ScrollAxis',0)):
        put(f' lda.l {sy[name]}\n cmp #{value}');guard('bne')
    for name in ('VmSourceWorld_AdvanceX','VmSourceWorld_AdvanceY'):
        put(f' lda.l {sy[name]}\n ora.l {sy[name]}+2');guard('bne')
    put(f' lda.l {sy["SourceCtorState4086_Status"]}\n cmp #3');guard('beq')
    put(' lda 5,s\n and #3');put(f' cmp.l {sy["SourceCtorState4086_Player"]}');guard('bne');put(f' lda.l {sy["SourceCtorState4086_Player"]}+2');guard('bne')
    put(' lda 5,s\n and #3')
    for row in stage['placements']:
        i=row['index'];put(f' cmp #{i}\n bne SpawnInputs_Next{i}')
        for name,value in (('X',row['x_q16']),('Z',row['z_q16']),('Direction',row['flip']),('A',0)):
            put(f' lda #{value&65535}\n sta.l {sy["SourceCtorState4086_"+name]}\n lda #{(value>>16)&65535}\n sta.l {sy["SourceCtorState4086_"+name]}+2')
        put(' jmp SpawnInputs_Good');label('Next'+str(i))
    put(' jmp SpawnInputs_Bad')
    for name,carry in (('Good','clc'),('Bad','sec')):
        label(name);put(' ply\n plx\n pla\n plp\n '+carry+'\n rtl')
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
