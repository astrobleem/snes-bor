"""Complete RGB555 additive operand coverage for one immutable source context.

Equivalent/dominated hardware operands may be removed without changing any
source output. Source RGB555 pixels are never quantized or approximated.
"""
import hashlib
import numpy as np


def complete_cover(requirements):
    keys=sorted(set((int(out),int(minimum))for out,minimum in requirements if minimum is not None))
    if not keys:return {},dict(rgb555_operand_domain=32768,rgb555_operands_examined=0,distinct_requirements=0,valid_operands=0,distinct_coverage_sets=0,maximal_cover_operands=0,maximal_operand_colors=[],dominance_mapping_sha256=hashlib.sha256(b'').hexdigest(),all_valid_operand_coverages_retained=True,complete_for_immutable_context=True,no_color_reduction=True)
    out=np.array([k[0]for k in keys],dtype=np.int32)
    minimum=np.array([k[1]for k in keys],dtype=np.int32)
    if np.any(out<0)or np.any(out>32767)or np.any(minimum<0)or np.any(minimum>32767):
        raise ValueError('ADDITIVE_COVER_RGB555_DOMAIN')
    signatures={};valid=0;mapping=[]
    for start in range(0,32768,256):
        colors=np.arange(start,start+256,dtype=np.int32)
        covers=np.ones((256,len(keys)),dtype=bool)
        for shift in (0,5,10):
            channel=(colors[:,None]>>shift)&31;needed=(minimum[None,:]>>shift)&31
            saturated=((out[None,:]>>shift)&31)==31
            covers&=np.where(saturated,channel>=needed,channel==needed)
        packed=np.packbits(covers,axis=1,bitorder='little')
        for color,row in zip(colors,packed):
            sig=int.from_bytes(row.tobytes(),'little')
            if not sig:continue
            valid+=1;signatures.setdefault(sig,int(color));mapping.append((int(color),sig))
    maximal=[];representatives={}
    for sig,color in sorted(signatures.items(),key=lambda pair:(-pair[0].bit_count(),pair[1])):
        dominant=next((c for mask,c in maximal if sig&mask==sig),None)
        if dominant is None:maximal.append((sig,color));dominant=color
        representatives[sig]=dominant
    # Verify every valid operand's full-context coverage is retained. Replacing
    # it globally in a bank/slot schedule cannot add writes or pixel errors.
    maximal_masks={c:mask for mask,c in maximal};digest=hashlib.sha256()
    for color,sig in mapping:
        representative=representatives[sig]
        if sig&maximal_masks[representative]!=sig:raise AssertionError('ADDITIVE_COVER_DOMINANCE_FAULT')
        digest.update(color.to_bytes(2,'little')+representative.to_bytes(2,'little'))
    options={key:sorted(c for mask,c in maximal if mask>>i&1)for i,key in enumerate(keys)}
    if any(not values for values in options.values()):raise AssertionError('ADDITIVE_COVER_REQUIREMENT_LOST')
    return options,dict(rgb555_operand_domain=32768,rgb555_operands_examined=32768,distinct_requirements=len(keys),
        valid_operands=valid,distinct_coverage_sets=len(signatures),maximal_cover_operands=len(maximal),
        maximal_operand_colors=sorted(maximal_masks),dominance_mapping_sha256=digest.hexdigest(),
        all_valid_operand_coverages_retained=True,complete_for_immutable_context=True,no_color_reduction=True)
