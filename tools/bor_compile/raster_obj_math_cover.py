"""Complete exact operands for SNES addition/subtraction, with optional halving.

Allowing different modes per pixel is a necessary relaxation only: the real
color-math control is shared. No returned cover is a hardware schedule.
"""
import hashlib
import numpy as np

MODES=('add','half-add','subtract','half-subtract')


def apply_math(operand,background,mode):
    if mode not in MODES:raise ValueError('OBJ_MATH_COVER_MODE')
    result=0
    for shift in (0,5,10):
        a=operand>>shift&31;b=background>>shift&31
        value=max(0,a-b)if 'subtract' in mode else a+b
        if mode.startswith('half-'):value>>=1
        result|=min(31,value)<<shift
    return result


def complete_math_cover(requirements,modes=MODES,tag_modes=False,allow_window_bypass=False,fixed_window_context=False):
    if not modes or any(m not in MODES for m in modes):raise ValueError('OBJ_MATH_COVER_MODE')
    modes=tuple(dict.fromkeys(modes))
    pairs=sorted(set((int(out),int(bg),bool(enabled))for out,bg,enabled in requirements))if fixed_window_context else sorted(set((int(out),int(bg))for out,bg in requirements))
    if any(not 0<=c<32768 for key in pairs for c in key[:2]):raise ValueError('OBJ_MATH_COVER_RGB555_DOMAIN')
    keys=[(mode,*pair)for mode in modes for pair in pairs]if tag_modes else pairs
    outputs=np.array([k[-3]if fixed_window_context else k[-2]for k in keys],dtype=np.int32)
    backgrounds=np.array([k[-2]if fixed_window_context else k[-1]for k in keys],dtype=np.int32)
    enabled=np.array([k[-1]for k in keys],dtype=bool)if fixed_window_context else None
    signatures={};mapping=[]
    for start in range(0,32768,256):
        colors=np.arange(start,start+256,dtype=np.int32)
        covers=np.zeros((256,len(keys)),dtype=bool)
        for mode_index,mode in enumerate(modes):
            subset=slice(mode_index*len(pairs),(mode_index+1)*len(pairs))if tag_modes else slice(None)
            mode_outputs=outputs[subset];mode_backgrounds=backgrounds[subset]
            match=np.ones((256,len(mode_outputs)),dtype=bool)
            for shift in (0,5,10):
                a=colors[:,None]>>shift&31;b=mode_backgrounds[None,:]>>shift&31
                value=np.maximum(0,a-b)if 'subtract' in mode else a+b
                if mode.startswith('half-'):value=value>>1
                match&=np.minimum(31,value)==(mode_outputs[None,:]>>shift&31)
            if allow_window_bypass:match|=colors[:,None]==mode_outputs[None,:]
            if fixed_window_context:match=np.where(enabled[subset][None,:],match,colors[:,None]==mode_outputs[None,:])
            if tag_modes:covers[:,subset]=match
            else:covers|=match
        for color,row in zip(colors,np.packbits(covers,axis=1,bitorder='little')):
            signature=int.from_bytes(row.tobytes(),'little')
            if signature:
                signatures.setdefault(signature,int(color));mapping.append((int(color),signature))
    maximal=[];representatives={}
    for signature,color in sorted(signatures.items(),key=lambda pair:(-pair[0].bit_count(),pair[1])):
        dominant=next((c for mask,c in maximal if signature&mask==signature),None)
        if dominant is None:maximal.append((signature,color));dominant=color
        representatives[signature]=dominant
    masks={c:mask for mask,c in maximal};digest=hashlib.sha256()
    for color,signature in mapping:
        representative=representatives[signature]
        if signature&masks[representative]!=signature:raise AssertionError('OBJ_MATH_COVER_DOMINANCE')
        digest.update(color.to_bytes(2,'little')+representative.to_bytes(2,'little'))
    options={key:sorted(c for mask,c in maximal if mask>>i&1)for i,key in enumerate(keys)}
    return options,dict(modes=list(modes),rgb555_operands_examined=32768,
                        distinct_requirements=len(keys),valid_operands=len(mapping),
                        maximal_cover_operands=len(maximal),dominance_mapping_sha256=digest.hexdigest(),
                        modes_relaxed_per_pixel=len(modes)>1 and not tag_modes,mode_tagged_coverage=tag_modes,global_mode_schedule_proven=False,
                        color_math_window_bypass_relaxed_per_pixel=allow_window_bypass,
                        fixed_color_math_window_context=fixed_window_context,
                        all_valid_operand_coverages_retained=True,no_color_reduction=True)
