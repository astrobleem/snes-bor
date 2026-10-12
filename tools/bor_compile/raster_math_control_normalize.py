"""Normalize source-exact raster math windows using only observable OBJ pixels.

Unused horizontal coordinates and rows can retain previous controls. A failed
positive-union normalization keeps the verified original descriptor. No source
word, pixel, OAM bank or geometry is changed; full source replay is mandatory.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from compiler import Source
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from raster_slot_greedy import demand
from raster_obj_math_cover import apply_math
from raster_math_windows import compile_sparse_mask,compile_mask,evaluate


def normalize(schedule,background,expected,window_union='positive'):
    if schedule.get('color_math')!='additive' or not schedule.get('scanline_math_controls_source_bound'):raise ValueError('MATH_CONTROL_SOURCE_BOUND_ADDITIVE_REQUIRED')
    if window_union not in('positive','negative'):raise ValueError('MATH_CONTROL_UNION_DOMAIN')
    def fixed_window(constraints):
        descriptor=compile_sparse_mask({x:not enabled for x,enabled in constraints.items()}if window_union=='negative'else constraints,fixed_positive_union=True)
        if window_union=='negative':
            descriptor.pop('fixed_positive_union',None);descriptor.update(wobjsel_color_bits=0xf0,wobjlog_color_bits=4,fixed_negative_union=True)
        return descriptor
    background=np.asarray(background,dtype=np.uint16);expected=np.asarray(expected,dtype=np.uint16)
    if background.shape!=expected.shape or hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()!=schedule['source_rgb555_sha256']:raise ValueError('MATH_CONTROL_CONTEXT_IDENTITY')
    required,uses,pixels=demand(schedule);height=len(required)
    if background.shape!=(height,256):raise ValueError('MATH_CONTROL_VIEWPORT_DOMAIN')
    rows={};old_replay=background.copy()
    for p,image in zip(schedule['pieces'],pixels):
        for ly,lx in zip(*np.where(image>=0)):
            y,x=int(p['y']+ly),int(p['x']+lx);c=int(image[ly,lx]);mode=schedule['selected_modes'].get(str(y),'add')
            descriptor=schedule['compiled_color_window_descriptors'].get(str(y));gate=descriptor is None or evaluate(descriptor,x)
            value=apply_math(c,int(background[y,x]),mode)if p['bank']>=4 and gate else c
            old_replay[y,x]=value
            if p['bank']>=4:rows.setdefault(y,[]).append((x,c,value))
    if not np.array_equal(old_replay,expected):raise ValueError('MATH_CONTROL_INPUT_PIXEL_IDENTITY')
    previous=fixed_window({0:False,255:False});previous_mode='add';windows={};modes={};fallback=[]
    for y in range(height):
        if y in rows:
            mode=schedule['selected_modes'].get(str(y),'add');constraints={}
            for x,c,out in rows[y]:
                blended=apply_math(c,int(background[y,x]),mode)
                if blended==c:continue
                if out!=blended and out!=c:raise AssertionError('MATH_CONTROL_WORD_HAS_NO_EXACT_GATE')
                constraints[x]=out==blended
            if constraints:
                try:previous=fixed_window(constraints)
                except ValueError:
                    descriptor=schedule['compiled_color_window_descriptors'].get(str(y))
                    if descriptor is None:descriptor=compile_mask([True]*256)
                    previous=copy.deepcopy(descriptor);fallback.append(y)
            previous_mode=mode
        windows[str(y)]=copy.deepcopy(previous);modes[str(y)]=previous_mode
    replay=background.copy()
    for p,image in zip(schedule['pieces'],pixels):
        for ly,lx in zip(*np.where(image>=0)):
            y,x=int(p['y']+ly),int(p['x']+lx);c=int(image[ly,lx])
            replay[y,x]=apply_math(c,int(background[y,x]),modes[str(y)])if p['bank']>=4 and evaluate(windows[str(y)],x)else c
    if not np.array_equal(replay,expected):raise AssertionError('MATH_CONTROL_NORMALIZED_PIXEL_IDENTITY')
    result=copy.deepcopy(schedule)
    for key in('physical_slot_layout','prepared_dma_packets','compiled_transfer_descriptor_sha256'):result.pop(key,None)
    result.update(selected_modes=modes,compiled_color_window_descriptors=windows,native_presentation_proven=False,
        input_compiled_schedule_sha256=schedule.get('compiled_schedule_sha256'),
        math_control_normalization=dict(schema='BYOR_OBSERVABLE_OBJ_MATH_CONTROL_NORMALIZATION_V1',
            complete_source_pixel_identity_verified=True,fixed_piece_banks_preserved=True,palette_words_preserved=True,
            window_union=window_union,union_fallback_rows=fallback,unused_rows_hold_previous_controls=True,
            source_rgb555_sha256=hashlib.sha256(replay.astype('<u2').tobytes()).hexdigest(),native_timing_admitted=False,no_color_reduction=True))
    payload=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=result['trace'],selected_modes=modes,compiled_color_window_descriptors=windows)
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    from raster_presentation_identity import refresh_presentation_identity
    refresh_presentation_identity(result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source','stage','scene','schedule','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--window-union',choices=('positive','negative'),default='positive')
    a=p.parse_args();source=Source(Path(a.source));scene=json.loads(Path(a.scene).read_text());expected=rgb555(compose_rgb8(source,a.stage,scene)[0]);background=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0])
    result=normalize(json.loads(Path(a.schedule).read_text()),background,expected,a.window_union);Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['math_control_normalization']))


if __name__=='__main__':main()
