"""Explicit-context geometry fusion after source occlusion and alpha evaluation.

This retains source owner identity; it does not admit a live compositor.
"""
import hashlib
import numpy as np


def merge_visible_actors(actors,shape):
    height,width=shape
    pixels=np.full((height,width),-1,dtype=np.int32)
    owners=np.full((height,width),-1,dtype=np.int32)
    records=[]
    for i,actor in enumerate(actors):
        source=np.asarray(actor['pixels'])
        ys,xs=np.where(source>=0)
        sy,sx=ys+actor['top'],xs+actor['left']
        if np.any(sy<0)or np.any(sy>=height)or np.any(sx<0)or np.any(sx>=width):
            raise ValueError('VISIBLE_COMPOSITE_UNCLIPPED_SOURCE_PIXEL')
        if np.any(owners[sy,sx]>=0):raise ValueError('VISIBLE_COMPOSITE_SOURCE_OWNERSHIP_OVERLAP')
        words=source[ys,xs]
        if np.any(words>=32768):raise ValueError('VISIBLE_COMPOSITE_RGB555_DOMAIN')
        pixels[sy,sx]=words;owners[sy,sx]=i
        records.append(dict(source_actor_index=i,source_metadata=actor.get('metadata'),
            source_dimensions=list(source.shape[::-1]),source_position=[actor['left'],actor['top']],visible_pixels=len(xs)))
    proof=dict(source_actors=records,source_owner_sha256=hashlib.sha256(owners.astype('<i4').tobytes()).hexdigest(),
        visible_source_pixels_sha256=hashlib.sha256(pixels.astype('<i4').tobytes()).hexdigest(),
        source_pixel_identity_preserved=True,requires_cross_actor_compiled_mask_ownership=True,
        live_compositor_admitted=False)
    return [dict(pixels=pixels,left=0,top=0,source_owner_indices=owners)],proof
