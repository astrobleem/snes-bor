"""Pinned draw_scrolled_bg positioning, repeat normalization and clipping.

Only unwarped layers with a zero viewport origin are admitted. Layer alpha and
pixel composition are separate. Source offset/spacing fields are signed ints;
ratio/camera values are binary32, and the literal 1.0 promotes the final product
in the engine expression to double before the int truncation.
"""
import math,struct

def f32(value):
    value=struct.unpack('<f',struct.pack('<f',float(value)))[0]
    if not math.isfinite(value):raise ValueError('LAYER_POSITION_NONFINITE')
    return value


def placements(size,ratio,offset,spacing,repeat,camera,viewport,*,bgtravel=0,bgspeedratio=0,up=False):
    width,height=(int(size[i])+int(spacing[i])for i in range(2))
    if width<=0 or height<=0 or any(not isinstance(v,int)for v in [*offset,*spacing,*repeat,*size,*viewport]):
        raise ValueError('LAYER_POSITION_GEOMETRY_DOMAIN')
    if any(v<0 for v in repeat):raise ValueError('LAYER_REPEAT_REQUIRES_LOAD_NORMALIZATION')
    advancex,advancey=map(f32,camera);rx,rz=map(f32,ratio)
    motion=f32(advancex+f32(f32(bgtravel)*f32(bgspeedratio)))
    x=int(offset[0]-motion*(1.0-rx));z=int(offset[1]+(1 if up else-1)*advancey*(1.0-rz))
    if not -2147483648<x<2147483648 or not -2147483648<z<2147483648:raise ValueError('LAYER_POSITION_SIGNED32_DOMAIN')
    i=(-x)//width if x<0 else 0;j=(-z)//height if z<0 else 0
    if x<0:x+=i*width
    if z<0:z+=j*height
    # C remainder retains the negative sign. Exact multiples become zero.
    xs=[];ys=[]
    while i<repeat[0]and x<viewport[0]:xs.append(x);x+=width;i+=1
    while j<repeat[1]and z<viewport[1]:ys.append(z);z+=height;j+=1
    return [(x,y)for y in ys for x in xs]


def legacy_layer(kind,size,*,ordinal=0,front_count=0):
    if kind=='background':
        return dict(size=size,ratio=(.5,.5),offset=(-size[0]*20000,-size[1]*20000),spacing=(0,0),repeat=(40000,40000),bgspeedratio=1)
    if kind=='panel':return dict(size=size,ratio=(0.,0.),offset=(0,0),spacing=(0,0),repeat=(1,1),bgspeedratio=0)
    if kind=='frontpanel':
        if front_count<1:raise ValueError('FRONTPANEL_COUNT_DOMAIN')
        # load_layer normalizes repeat first. layersref then replaces offset.x
        # with ordinal * this layer's own width, including mixed-width quirks.
        return dict(size=size,ratio=(-.4,1.),offset=(ordinal*size[0],0),spacing=((front_count-1)*size[0],0),repeat=(40000,1),bgspeedratio=0)
    raise ValueError('LEGACY_LAYER_KIND_UNSUPPORTED')
