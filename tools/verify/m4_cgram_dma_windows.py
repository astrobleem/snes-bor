"""Prepared palette DMA followed by automatic-cursor window DMA.

Synthetic native timing fixture. NMI resets descriptor cursors; IRQ preserves
A and hardware-stacked P and leaves X/Y/D/DBR untouched. No production lease.
"""
import struct
from raster_math_windows import compile_mask


def palette_color(row):
    return (0x1111,0x1112,0x1151,0x1511)[row%4]


def fixed_color_for_row(color,row,dynamic=False):
    return color if not dynamic else sum((((color>>s&31)+row%4)%32)<<s for s in (0,5,10))


def window_masks(general=False):
    return [[1]*256,[int(32<=x<=63 or 128<=x<=191)for x in range(256)],
            [int(not(32<=x<=63 or 128<=x<=191))for x in range(256)]if general else[int(0<=x<=31 or 96<=x<=127)for x in range(256)],[0]*256]


def expected_frame(general_windows=False,fixed_math_mode=False,fixed_color=None,dynamic_fixed_color=False):
    from m4_cgram_window_pixels import fixture
    expected=fixture()[2]
    masks=window_masks(general_windows)
    for y in range(80,208):
        c=palette_color(y);r=c&31;g=(c>>5)&31;b=c>>10
        fixed=fixed_color_for_row(fixed_color,y,dynamic_fixed_color)if fixed_color is not None else None
        for x in range(96,224):
            enabled=((x-96)//32)%2==1 and masks[y%4][x]
            half=y%8>=4 and not fixed_math_mode
            if fixed_color is None:
                expected[y,x]=((r//2)|(((g+5)//2)<<5)|((b//2)<<10))if enabled and half else(r|((g+5)<<5)|(b<<10))if enabled else c
            elif enabled:
                subtract=y%16>=8 and not fixed_math_mode
                value=0
                for shift in (0,5,10):
                    a=c>>shift&31;b=fixed>>shift&31
                    channel=max(0,a-b)if subtract else a+b
                    if half:channel//=2
                    value|=min(31,channel)<<shift
                expected[y,x]=value
            else:expected[y,x]=c
    return expected


def compile_rom(timer,context_widths='16/16',decimal_context=False,general_windows=False,three_ranges=False,fixed_math_mode=False,retire_audio_hdma=False,fetch_gateway=False,direct_fetch_route=False,compact_visible_handler=False,fixed_color=None,dynamic_fixed_color=False):
    if fixed_color is not None and(type(fixed_color)is not int or not 0<=fixed_color<32768):raise ValueError('DMA_WINDOWS_FIXED_COLOR_DOMAIN')
    if dynamic_fixed_color and(fixed_color is None or general_windows or three_ranges):raise ValueError('DYNAMIC_FIXED_COLOR_CHANNEL_OWNERSHIP')
    if fetch_gateway and direct_fetch_route:raise ValueError('FETCH_GATEWAY_ROUTE_CONFLICT')
    if three_ranges and general_windows:raise ValueError('THREE_PALETTE_RANGES_REQUIRE_NINE_DMA_CHANNELS_WITH_GENERAL_WINDOWS')
    if fixed_math_mode and (not three_ranges or general_windows):raise ValueError('FIXED_MATH_MODE_THREE_RANGE_PROBE_REQUIRED')
    if context_widths not in ('16/16','8/16','16/8','8/8'):raise ValueError('DMA_WINDOWS_CONTEXT_WIDTHS')
    from m4_cgram_window_pixels import fixture
    visual,assets,_,_,_=fixture()
    raw=bytearray([255])*131072
    code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(a,v):code.extend([0xa9,v,0x8d,a&255,a>>8])
    for a,v in ((0x4200,0),(0x420c,0),(0x2100,128)):store(a,v)
    code.extend(visual)
    if fixed_color is not None:
        # Keep the same prevent-outside-window policy, use COLDATA rather
        # than the BG subscreen, and leave ordinary OBJ banks math-ineligible.
        store(0x2130,0x10)
        for shift,mask in ((0,0x20),(5,0x40),(10,0x80)):store(0x2132,mask|(fixed_color>>shift&31))
    for offset,data in assets.items():raw[offset:offset+len(data)]=data
    # Palette and window payload cursors advance in DMA hardware. NMI resets
    # them together; each visible palette row has a different payload.
    for ch,mode,dest,source,bank in ((1,0,0x22,0x8000,2),(2,8,0x21,0x8000,3),(3,0,0x22,0xa000,2),(6,4,0x26,0xa000,3),(7,0,0x31,0xa400,3),(0,4,0x40,0x9000,3)):
        base=0x4300+16*ch
        for a,v in ((base,mode),(base+1,dest),(base+2,source&255),(base+3,source>>8),(base+4,bank),(base+6,0)):store(a,v)
    if general_windows:
        for ch,dest,source in ((4,0x25,0xa500),(5,0x2b,0xa600)):
            base=0x4300+16*ch
            for a,v in ((base,0),(base+1,dest),(base+2,source&255),(base+3,source>>8),(base+4,3),(base+6,0)):store(a,v)
    if dynamic_fixed_color:
        for a,v in ((0x4340,0),(0x4341,0x32),(0x4342,0),(0x4343,0xa7),(0x4344,3),(0x4346,0)):store(a,v)
    if three_ranges:
        for ch,mode,dest,source,bank in ((4,8,0x21,0x8001,3),(5,0,0x22,0xc000,2)):
            base=0x4300+16*ch
            for a,v in ((base,mode),(base+1,dest),(base+2,source&255),(base+3,source>>8),(base+4,bank),(base+6,0)):store(a,v)
    for a,v in ((0x4207,timer&255),(0x4208,timer>>8),(0x2125,0xa0),(0x212b,0),(0x420d,1)):store(a,v)
    if fixed_math_mode:store(0x2131,0x10)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'))
    store(0x420c,1);store(0x2100,15);store(0x4200,0x90)
    code.extend(bytes.fromhex('c2 30 a9 45 23 5b a2 78 56 a0 cd ab e2 20 a9 40 48 ab c2 20 a9 34 12'))
    if decimal_context:code.append(0xf8)
    mask=(0x20 if context_widths.startswith('8/')else 0)|(0x10 if context_widths.endswith('/8')else 0)
    if mask:code.extend([0xe2,mask])
    code.extend(bytes.fromhex('58 22 90 96 00 80 fa')if fetch_gateway else bytes.fromhex('58 22 00 8b 81 80 fa')if direct_fetch_route else bytes.fromhex('58 80 fe'))
    irq=bytearray.fromhex('e2 20 af 11 42 00 af 12 42 00'if fetch_gateway else'c2 38 48 e2 20 af 11 42 00 af 12 42 00')
    if not compact_visible_handler:irq.extend(bytes.fromhex('29 80'))
    branches=[];labels={}
    def branch(op,target):irq.extend([op,0]);branches.append((len(irq)-1,target))
    def longstore(a,v):irq.extend([0xa9,v,0x8f,a&255,a>>8,0])
    branch(0x30 if compact_visible_handler else 0xd0,'restore')
    irq.extend(bytes.fromhex('c2 20 af 62 43 00'))
    # VBlank already rejects all out-of-field IRQs and NMI resets the cursor.
    # Removing the duplicate end bound requires that NMI/cursor ownership.
    if not compact_visible_handler:
        irq.extend(bytes.fromhex('c9 80 a3'));branch(0xb0,'restore')
    irq.extend(bytes.fromhex('c9 2c a1 e2 20'));branch(0x90,'windows_only')
    if retire_audio_hdma:longstore(0x420c,0)
    for a,v in ((0x4315,16 if three_ranges else 24),(0x4325,1),(0x4335,12 if three_ranges else 14),(0x2121,129),(0x4365,4)):longstore(a,v)
    if not fixed_math_mode:longstore(0x4375,1)
    if dynamic_fixed_color:longstore(0x4345,3)
    if three_ranges:
        for a,v in ((0x4345,1),(0x4355,12)):longstore(a,v)
    if general_windows:
        for a,v in ((0x4345,1),(0x4355,1)):longstore(a,v)
    longstore(0x420b,126 if fixed_math_mode else 254 if general_windows or three_ranges else 222 if dynamic_fixed_color else 206)
    branch(0x80,'restore')
    labels['windows_only']=len(irq)
    longstore(0x4365,4)
    if not fixed_math_mode:longstore(0x4375,1)
    if dynamic_fixed_color:longstore(0x4345,3)
    if general_windows:
        for a,v in ((0x4345,1),(0x4355,1)):longstore(a,v)
    longstore(0x420b,64 if fixed_math_mode else 240 if general_windows else 208 if dynamic_fixed_color else 192)
    labels['restore']=len(irq);irq.extend(bytes.fromhex('c2 30 68 28 40'if fetch_gateway else'c2 30 68 40'))
    for at,label in branches:
        delta=labels[label]-at-1
        if not -128<=delta<=127:raise AssertionError('DMA_WINDOWS_BRANCH_RANGE')
        irq[at]=delta&255
    nmi=bytearray.fromhex('c2 38 48 e2 20 af 10 42 00 c2 20 a9 00 a0 8f 62 43 00 a9 00 a4 8f 72 43 00 a9 00 80 8f 12 43 00 a9 00 a0 8f 32 43 00 68 40')
    if retire_audio_hdma:nmi[9:9]=bytes.fromhex('a9 01 8f 0c 42 00')
    if general_windows:nmi[-2:-2]=bytes.fromhex('a9 00 a5 8f 42 43 00 a9 00 a6 8f 52 43 00')
    if three_ranges:nmi[-2:-2]=bytes.fromhex('a9 00 c0 8f 52 43 00')
    if dynamic_fixed_color:nmi[-2:-2]=bytes.fromhex('a9 00 a7 8f 42 43 00')
    raw[:4]=bytes.fromhex('5c 00 80 01');raw[0x100:0x104]=bytes.fromhex('5c 00 86 81');raw[0x120:0x124]=bytes.fromhex('5c 00 88 81')
    if len(code)>0x600:raise AssertionError('DMA_WINDOWS_BOOT_OVERLAP')
    raw[0x8000:0x8000+len(code)]=code;raw[0x8600:0x8600+len(irq)]=irq;raw[0x8800:0x8800+len(nmi)]=nmi
    if fetch_gateway:
        # Exact instruction shape of the size-neutral production Vm_Fetch
        # gateway. The ordinary fetch body is a preserving RTL stub here;
        # production fetch/NMI/gameplay ownership is not supplied by this ROM.
        raw[0x1697:0x169c]=bytes.fromhex('5c 00 8a 81 60')
        raw[0x1690:0x1694]=bytes.fromhex('20 97 96 6b')
        raw[0x8a00:0x8a1c]=bytes.fromhex('08 c2 39 48 a3 03 29 04 00 f0 04 5c 00 86 81 68 28 22 00 8b 81 5c 9b 96 00')+bytes([255])*3
        raw[0x8b00]=0x6b
    if direct_fetch_route:
        raw[0x1697:0x169c]=bytes.fromhex('5c 00 86 81 60')
        raw[0x8b00]=0x6b
    for y in range(75,224):
        word=struct.pack('<H',palette_color(y));i=y-75
        n1,n2=(16,12)if three_ranges else(24,14)
        raw[0x10000+n1*i:0x10000+n1*(i+1)]=word*(n1//2)
        raw[0x12000+n2*i:0x12000+n2*(i+1)]=word*(n2//2)
        if three_ranges:raw[0x14000+12*i:0x14000+12*(i+1)]=word*6
    raw[0x18000]=161 if three_ranges else 193;raw[0x18001]=193
    raw[0x19000:0x19000+366]=bytes([0x81,0,0,0,57])*73+bytes([0])
    masks=window_masks(general_windows)
    for y in range(224):
        descriptor=compile_mask(masks[y%4],not general_windows);bounds=sum(descriptor['bounds'],[])
        raw[0x1a000+4*y:0x1a004+4*y]=bytes(bounds)
        raw[0x1a400+y]=0x10|(0x40 if y%8>=4 else 0)|(0x80 if fixed_color is not None and y%16>=8 else 0)
        if dynamic_fixed_color:
            color=fixed_color_for_row(fixed_color,y,True)
            raw[0x1a700+3*y:0x1a703+3*y]=bytes(mask|(color>>shift&31)for shift,mask in ((0,0x20),(5,0x40),(10,0x80)))
        if general_windows:raw[0x1a500+y]=descriptor['wobjsel_color_bits'];raw[0x1a600+y]=descriptor['wobjlog_color_bits']
    raw[0x7fc0:0x7fd5]=b'M4 DMA WINDOW PROOF  '
    raw[0x7fd5:0x7fdc]=bytes([0x30,0,7,0,1,0,0])
    for offset,value in ((0x7ffc,0x8000),(0x7fee,0x9697 if fetch_gateway or direct_fetch_route else 0x8100),(0x7fea,0x8120)):struct.pack_into('<H',raw,offset,value)
    return bytes(raw)
