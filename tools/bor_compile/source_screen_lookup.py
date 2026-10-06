"""Offline exact SCREEN matrix for a finite source RGB8 underlay vocabulary.

Indices identify RGB8 triples, never nearest colours. A new composed underlay
colour must fault or use a different exact arithmetic capability. This table
alone does not admit stacked translucent layers or a live world compositor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from compiler import Source,key
from source_profile import document,discover
from source_palette import model_palettes
from source_bg_feasibility import decode
from dialect_4086 import ENGINE_COMMIT


def colors(indices,rgb,transparent=True):
    selected=rgb[indices!=0] if transparent else rgb.reshape(-1,3)
    return {tuple(map(int,c)) for c in np.unique(selected.reshape(-1,3),axis=0)}


def matrix(sources,destinations):
    s=np.asarray(sources);d=np.asarray(destinations)
    if s.ndim!=2 or d.ndim!=2 or s.shape[1]!=3 or d.shape[1]!=3 or s.dtype.kind not in 'ui' or d.dtype.kind not in 'ui' or np.any(s<0) or np.any(d<0) or np.any(s>255) or np.any(d>255):
        raise ValueError('SCREEN_LOOKUP_RGB8_DOMAIN')
    s=s.astype(np.uint32);d=d.astype(np.uint32)
    rgb=255-((255-s[:,None,:])*(255-d[None,:,:])//255)
    words=(rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)
    return words.astype('<u2')


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);underlay={(0,0,0)};effects=[];identities=[]
    for model in structure['models']:
        palettes=model_palettes(source,model)
        if palettes['base'] is None: raise ValueError('SCREEN_LOOKUP_PER_FRAME_PALETTE_UNBOUND')
        palette_rows=[palettes['base'],*palettes['alternates']];used=set();frames=[]
        for a in model['animations']:
            for f in a['frames']:
                path=f['values'][0]
                idx,rgb,digest=decode(source,path,palettes['base']['rgb8'])
                used.update(map(int,np.unique(idx[idx!=0])))
                frames.append(dict(path=source.image_path(path),sha256=digest))
        model_colors=set()
        for palette in palette_rows:
            values=palette['rgb8']
            model_colors.update(tuple(values[i*3:i*3+3]) for i in used)
        underlay.update(model_colors)
        alpha=model['properties'].get('alpha',[])
        mode=int(alpha[-1]['values'][0]) if alpha else 0
        identities.append(dict(model=model['declaration'],rgb8_colors=len(model_colors),alpha=mode,
            source_path=model['source_path'],source_sha256=docs[key(model['source_path'])]['sha256']))
        if mode==1: effects.append(dict(model=model['declaration'],colors=sorted(model_colors),frames=frames))
    stages=[]
    stage_paths=sorted({e['source_path'] for s in structure['sets'] for e in s['entries'] if e['kind']=='STAGE'})
    for path in stage_paths:
        for row in docs[key(path)]['directives']:
            if row['directive'] not in ('background','panel','frontpanel','bglayer','fglayer'): continue
            if not row['values']: raise ValueError('SCREEN_LOOKUP_STAGE_IMAGE_ARITY')
            for image in (row['values'] if row['directive']=='panel' else row['values'][:1]):
                if image.lower()=='none': continue
                idx,rgb,digest=decode(source,image)
                image_colors=colors(idx,rgb,row['directive']!='background');underlay.update(image_colors)
                stages.append(dict(stage=path,directive=row['directive'],path=source.image_path(image),
                    sha256=digest,rgb8_colors=len(image_colors)))
    # Runtime receives precompiled row addresses. A power-of-two row pitch
    # buys no addressing benefit and wastes ROM for this exact vocabulary.
    destinations=sorted(underlay);cols=len(destinations)
    for e in effects:
        e.update(rows=len(e['colors']),columns=cols,row_stride_bytes=cols*2,source_color_count=len(e['colors']),
                 table_bytes=len(e['colors'])*cols*2)
    return dict(schema='BYOR_SOURCE_SCREEN_LOOKUP_V1',engine_authority=ENGINE_COMMIT,
        destinations=destinations,destination_rgb8_colors=len(destinations),effects=effects,
        model_colors=identities,stage_images=stages,no_color_reduction=True,
        scope='Finite opaque-source underlay vocabulary including all source models, alternates and stage images; conservative colour union, not simultaneous scene proof',
        stacked_screen_layers_bound=False,geometry_bound=False,palette_schedule_bound=False,
        live_world_bound=False,motu_gameplay_proven=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    r=derive(Source(a.source))
    for n,e in enumerate(r['effects']):
        words=matrix(e['colors'],r['destinations']);table=np.zeros((e['rows'],e['columns']),dtype='<u2')
        table[:,:words.shape[1]]=words
        raw=table.tobytes();path=a.output/('screen-%02d.rgb555'%n);path.write_bytes(raw)
        e.update(table_path=path.name,table_sha256=hashlib.sha256(raw).hexdigest())
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(destination_colors=r['destination_rgb8_colors'],effects=[{k:e[k] for k in ('model','rows','columns','table_bytes')} for e in r['effects']])))


if __name__=='__main__':main()
