"""Source-derived 4086 special command tables and ordered combo selection.

Selection does not pay cost or start an animation. A selected move becomes a
check_costmove request; all mutation services must be bound by the world owner.
"""
import argparse,hashlib,json,re,struct
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_animation_ids import configure,role_id
from source_player_input_4086 import match_combo,FORWARD,BACKWARD
from source_script_input import authority
from dialect_4086 import ENGINE_COMMIT


def select(combos,player,state,valid,energy):
    best=-1;length=-1
    for combo in combos:
        if state['cancel']:
            if (state['animnum']!=combo['cancel']or combo['frame_min']>state['animpos']or
                combo['frame_max']<state['animpos']or state['animhits']<combo['hits']):continue
        elif combo['cancel']or not state['idling']or abs(state['alt']-state['base'])>1:continue
        if (len(combo['input'])>length and valid(combo['anim'])and
            (energy(1,combo['anim'])or energy(0,combo['anim']))and
            match_combo(combo['input'],player)):
            best=combo['anim'];length=len(combo['input'])
    return best


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    registry=discover(source,docs)
    ids=configure(docs[key(registry['models_path'])]['directives'])
    masks={r['name']:r['mask']for r in authority()['keys']}
    tokens=dict(u=masks['moveup'],d=masks['movedown'],f=FORWARD,b=BACKWARD,
                a=masks['attack'],a2=masks['attack2'],a3=masks['attack3'],a4=masks['attack4'],
                j=masks['jump'],s=masks['special'],k=masks['special'])
    models=[]
    for model in registry['models']:
        doc=docs[key(model['source_path'])];combos=[];current=None;roles=set();cancel_anims=[]
        for row in doc['directives']:
            name=row['directive'];values=row['values']
            if name=='anim':current=role_id(ids,' '.join(values));roles.add(current)
            if name not in ('com','cancel'):continue
            metadata=dict(cancel=0,frame_min=0,frame_max=0,hits=0,origin='AUTHORED',source_line=row['line'])
            if name=='cancel':
                if current is None or len(values)<5:raise ValueError('SOURCE_COMBO_CANCEL_ARITY')
                metadata.update(cancel=current,frame_min=int(values[0]),frame_max=int(values[1]),hits=int(values[2]))
                values=values[3:];cancel_anims.append(current)
            limit=24 if name=='com'else 21
            if not 2<=len(values)<=limit:raise ValueError('SOURCE_COMBO_LOADER_INPUT_LIMIT')
            target=re.fullmatch(r'freespecial([0-9]*)',values[-1].lower())
            if not target:raise ValueError('SOURCE_COMBO_FINAL_TARGET_REQUIRED')
            number=max(1,int(target[1]or 1))
            if any(v.lower()not in tokens for v in values[:-1]):raise ValueError('SOURCE_COMBO_TOKEN_UNSUPPORTED')
            combo=dict(metadata,input=[tokens[v.lower()]for v in values[:-1]],anim=role_id(ids,'freespecial'+str(number)))
            combos.append(combo)
        defaults=(('freespecial',[FORWARD,FORWARD,masks['attack']]),
                  ('freespecial2',[masks['movedown'],masks['movedown'],masks['attack']]),
                  ('freespecial3',[masks['moveup'],masks['moveup'],masks['attack']]))
        for role,sequence in defaults:
            anim=role_id(ids,role)
            if anim in roles and not any(c['anim']==anim for c in combos):
                combos.append(dict(input=sequence,anim=anim,cancel=0,frame_min=0,frame_max=0,hits=0,origin='LOADER_DEFAULT',source_line=0))
        models.append(dict(model=model['declaration'],source_path=doc['source_path'],source_sha256=doc['sha256'],
                           combos=combos,cancel_animations=sorted(set(cancel_anims))))
    return dict(schema='BYOR_4086_SPECIAL_COMMAND_IR_V1',engine_commit=ENGINE_COMMIT,models=models,
                longest_first=True,equal_length_source_order=True,native_costmove_owner_bound=False,motu_gameplay_proven=False)


def pack(report):
    models=report['models'];header=16+8*len(models);records=bytearray();directory=[]
    for i,model in enumerate(models):
        directory.append(struct.pack('<4H',i,len(model['combos']),header+len(records),0))
        for c in model['combos']:
            if len(c['input'])>27:raise ValueError('SOURCE_COMBO_RING_CAPACITY')
            records+=struct.pack('<6i',c['anim'],c['cancel'],c['frame_min'],c['frame_max'],c['hits'],len(c['input']))
            records+=struct.pack('<27I',*c['input'],*[0]*(27-len(c['input'])))
    data=struct.pack('<4s6H',b'B4CS',1,len(models),16,header,132,0)+b''.join(directory)+records
    if len(data)>32768:raise ValueError('SOURCE_COMBO_BANK_CAPACITY')
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=derive(Source(a.source));data=pack(report)
    report.update(table_bytes=len(data),table_sha256=hashlib.sha256(data).hexdigest(),combo_count=sum(len(m['combos'])for m in report['models']))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');a.output.with_suffix('.b4cs').write_bytes(data)
    print('Derived',report['combo_count'],'source special commands;',len(data),'bytes')

if __name__=='__main__':main()
