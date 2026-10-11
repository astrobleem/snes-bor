"""Measure RGB555 additive compatibility against authoritative RGB8 SCREEN.

This is an alpha-policy measurement, never palette quantization, policy
selection, a compiled schedule or native/gameplay admission.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from compiler import Source
from source_profile import document,discover
from source_palette import model_palettes,select_model_palette
from source_scene_bg import compose_rgb8
from source_bg_feasibility import decode,rgb555


def channel_errors():
    source=np.arange(256,dtype=np.int32)[:,None]
    destination=np.arange(256,dtype=np.int32)[None,:]
    exact=(255-((255-source)*(255-destination)//255))>>3
    added=np.minimum(31,(source>>3)+(destination>>3))
    error=added-exact
    return dict(exhaustive_source_destination_pairs=int(error.size),
        signed_error_histogram={str(int(v)):int(np.sum(error==v))for v in np.unique(error)},
        maximum_absolute_rgb5_channel_error=int(np.max(np.abs(error))),
        maximum_positive_rgb5_channel_error=int(error.max()),minimum_signed_rgb5_channel_error=int(error.min()))


def measure(source,stage,scene):
    expected,metadata=compose_rgb8(source,stage,scene)
    docs={key:document(source,path)for key,(path,_)in source.index.items()if key.endswith('.txt')}
    models=discover(source,docs)['models']
    canvas=np.zeros(expected.shape[:2],dtype=np.int32);identities=[]
    for layer in metadata['layers']:
        palette=None
        actor=layer['kind'].startswith('actor:')
        if actor:
            model=next(m for m in models if layer['kind']=='actor:'+m['name'])
            selected,_=select_model_palette(model_palettes(source,model),layer['requested_map']);palette=selected['rgb8']
        indices,rgb,_=decode(source,layer['path'],palette)
        if layer['source_flip']:indices=indices[:,::-1];rgb=rgb[:,::-1]
        words=rgb555(rgb);x,y=layer['position'];ih,iw=indices.shape
        x0=max(0,x);y0=max(0,y);x1=min(256,x+iw);y1=min(224,y+ih)
        if layer['alpha']not in(0,1):raise ValueError('ALPHA_COMPAT_UNSUPPORTED_SOURCE_ALPHA')
        mask=indices!=0 if actor or layer['kind']!='background'else np.ones(indices.shape,dtype=bool)
        identities.append(dict(path=layer['path'],alpha=layer['alpha'],
            opaque_source_rgb555_colors=len(set(map(int,words[mask]))),opaque_source_pixels=int(mask.sum()),
            source_word_pixels_sha256=hashlib.sha256(np.where(mask,words,-1).astype('<i4').tobytes()).hexdigest()))
        if x1<=x0 or y1<=y0:continue
        visible=mask[y0-y:y1-y,x0-x:x1-x]
        source_words=words[y0-y:y1-y,x0-x:x1-x];view=canvas[y0:y1,x0:x1]
        if layer['alpha']==0:view[visible]=source_words[visible]
        else:
            result=np.zeros(view.shape,dtype=np.int32)
            for shift in (0,5,10):result|=np.minimum(31,((source_words>>shift)&31)+((view>>shift)&31))<<shift
            view[visible]=result[visible]
    exact=rgb555(expected);channels=lambda image:np.stack([(image>>s)&31 for s in (0,5,10)],axis=-1)
    error=channels(canvas)-channels(exact);changed=np.any(error!=0,axis=-1)
    return dict(schema='BYOR_SCREEN_TO_ADDITIVE_ALPHA_MEASUREMENT_V1',metadata=metadata,
        source_pak_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),
        source_alpha_policy='BOR4086_SCREEN_RGB8_THEN_RGB555',
        measured_alternative='SNES_FULL_ADD_OF_UNCHANGED_SOURCE_RGB555',
        alpha_compatibility_policy_selected=False,source_palette_quantized=False,
        source_art_palette_identities=identities,exhaustive_channel_comparison=channel_errors(),
        source_composite_sha256=hashlib.sha256(exact.astype('<u2').tobytes()).hexdigest(),
        measured_additive_composite_sha256=hashlib.sha256(canvas.astype('<u2').tobytes()).hexdigest(),
        compared_pixels=int(exact.size),changed_pixels=int(changed.sum()),
        maximum_absolute_rgb5_channel_error=int(np.max(np.abs(error))),
        mean_absolute_rgb5_channel_error=float(np.mean(np.abs(error))),
        mean_absolute_changed_pixel_rgb5_channel_error=float(np.mean(np.abs(error[changed])))if np.any(changed)else 0.,
        native_layer_routing_admitted=False,compiled_schedule_admitted=False,
        native_timing_admitted=False,production_runtime_admitted=False,
        universal_raster_rejected=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=measure(Source(a.source),a.stage,json.loads(a.scene.read_text()))
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k]for k in('changed_pixels','maximum_absolute_rgb5_channel_error','mean_absolute_rgb5_channel_error','alpha_compatibility_policy_selected','no_color_reduction')}))


if __name__=='__main__':main()
