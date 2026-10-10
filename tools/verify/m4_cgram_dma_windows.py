"""Prepared palette DMA followed by automatic-cursor window DMA.

Synthetic native timing fixture. NMI resets descriptor cursors; IRQ preserves
A and hardware-stacked P and leaves X/Y/D/DBR untouched. No production lease.
"""
import struct
from raster_math_windows import compile_mask


def palette_color(row):
    return (0x1111,0x1112,0x1151,0x1511)[row%4]


def expected_frame():
    from m4_cgram_window_pixels import fixture
    expected=fixture()[2]
    masks=[[1]*256,[int(32<=x<=63 or 128<=x<=191)for x in range(256)],[int(0<=x<=31 or 96<=x<=127)for x in range(256)],[0]*256]
    for y in range(80,208):
        c=palette_color(y);r=c&31;g=(c>>5)&31;b=c>>10
        for x in range(96,224):
            enabled=((x-96)//32)%2==1 and masks[y%4][x]
            half=y%8>=4
            expected[y,x]=((r//2)|(((g+5)//2)<<5)|((b//2)<<10))if enabled and half else(r|((g+5)<<5)|(b<<10))if enabled else c
    return expected


def compile_rom(timer,context_widths='16/16',decimal_context=False):
    if context_widths not in ('16/16','8/16','16/8','8/8'):raise ValueError('DMA_WINDOWS_CONTEXT_WIDTHS')
    from m4_cgram_window_pixels import fixture
    visual,assets,_,_,_=fixture()
    raw=bytearray([255])*131072
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(a,v):code.extend([0xa9,v,0x8d,a&255,a>>8])
    for a,v in ((0x4200,0),(0x420c,0),(0x2100,128)):store(a,v)
    code.extend(visual)
    for offset,data in assets.items():raw[offset:offset+len(data)]=data
    # Palette and window payload cursors advance in DMA hardware. NMI resets
    # them together; each visible palette row has a different payload.
    for ch,mode,dest,source,bank in ((1,0,0x22,0x8000,2),(2,8,0x21,0x8000,3),(3,0,0x22,0xa000,2),(6,4,0x26,0xa000,3),(7,0,0x31,0xa400,3),(0,4,0x40,0x9000,3)):
        base=0x4300+16*ch
        for a,v in ((base,mode),(base+1,dest),(base+2,source&255),(base+3,source>>8),(base+4,bank),(base+6,0)):store(a,v)
    for a,v in ((0x4207,timer&255),(0x4208,timer>>8),(0x2125,0xa0),(0x212b,0),(0x420d,1)):store(a,v)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    store(0x420c,1);store(0x2100,15);store(0x4200,0x90)
    code.extend(bytes.fromhex('c2 30 a9 45 23 5b a2 78 56 a0 cd ab e2 20 a9 40 48 ab c2 20 a9 34 12'))
    if decimal_context:code.append(0xf8)
    mask=(0x20 if context_widths.startswith('8/')else 0)|(0x10 if context_widths.endswith('/8')else 0)
    if mask:code.extend([0xe2,mask])
    code.extend(bytes.fromhex('58 80 fe'))
    irq=bytearray.fromhex('c2 38 48 e2 20 af 11 42 00 af 12 42 00 29 80')
    branches=[];labels={}
    def branch(op,target):irq.extend([op,0]);branches.append((len(irq)-1,target))
    def longstore(a,v):irq.extend([0xa9,v,0x8f,a&255,a>>8,0])
    branch(0xd0,'restore')
    irq.extend(bytes.fromhex('c2 20 af 62 43 00 c9 80 a3'));branch(0xb0,'restore')
    irq.extend(bytes.fromhex('c9 2c a1 e2 20'));branch(0x90,'windows_only')
    for a,v in ((0x4315,24),(0x4325,1),(0x4335,14),(0x2121,128),(0x4365,4),(0x4375,1),(0x420b,206)):longstore(a,v)
    branch(0x80,'restore')
    labels['windows_only']=len(irq)
    for a,v in ((0x4365,4),(0x4375,1),(0x420b,192)):longstore(a,v)
    labels['restore']=len(irq);irq.extend(bytes.fromhex('c2 30 68 40'))
    for at,label in branches:
        delta=labels[label]-at-1
        if not -128<=delta<=127:raise AssertionError('DMA_WINDOWS_BRANCH_RANGE')
        irq[at]=delta&255
    nmi=bytearray.fromhex('c2 38 48 e2 20 af 10 42 00 c2 20 a9 00 a0 8f 62 43 00 a9 00 a4 8f 72 43 00 a9 00 80 8f 12 43 00 a9 00 a0 8f 32 43 00 68 40')
    raw[:4]=bytes.fromhex('5c 00 80 01');raw[0x100:0x104]=bytes.fromhex('5c 00 86 81');raw[0x120:0x124]=bytes.fromhex('5c 00 88 81')
    if len(code)>0x600:raise AssertionError('DMA_WINDOWS_BOOT_OVERLAP')
    raw[0x8000:0x8000+len(code)]=code;raw[0x8600:0x8600+len(irq)]=irq;raw[0x8800:0x8800+len(nmi)]=nmi
    for y in range(75,224):
        word=struct.pack('<H',palette_color(y));i=y-75
        raw[0x10000+24*i:0x10000+24*(i+1)]=word*12
        raw[0x12000+14*i:0x12000+14*(i+1)]=word*7
    raw[0x18000]=192
    raw[0x19000:0x19000+366]=bytes([0x81,0,0,0,57])*73+bytes([0])
    masks=[[1]*256,[int(32<=x<=63 or 128<=x<=191)for x in range(256)],[int(0<=x<=31 or 96<=x<=127)for x in range(256)],[0]*256]
    for y in range(224):
        bounds=sum(compile_mask(masks[y%4],True)['bounds'],[])
        raw[0x1a000+4*y:0x1a004+4*y]=bytes(bounds)
        raw[0x1a400+y]=0x10|(0x40 if y%8>=4 else 0)
    raw[0x7fc0:0x7fd5]=b'M4 DMA WINDOW PROOF  '
    raw[0x7fd5:0x7fdc]=bytes([0x30,0,7,0,1,0,0])
    for offset,value in ((0x7ffc,0x8000),(0x7fee,0x8100),(0x7fea,0x8120)):struct.pack_into('<H',raw,offset,value)
    return bytes(raw)
