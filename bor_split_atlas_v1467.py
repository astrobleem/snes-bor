"""Private split cold-atlas upload on the qualified two-Kula stage-zero bootstrap."""
BOOT=0x308159
NMI=0x28d000
ARM=0x28d900
FINISH=0x28dc00
RESET=0x28e500
RELEASE=0x28e600
CHUNKS=((0x308b60,0x5860,320),(0x308ca0,0x5960,320),(0x308de0,0x5a60,320),(0x308f20,0x5b60,320),
        (0x309060,0x5c00,512),(0x309260,0x5d00,512),(0x309460,0x5e00,512),(0x309660,0x5f00,512))
ROW=0x7e4d98
BASE_MARK=0xf680
COUNT=len(CHUNKS)
PRIVATE=0x4601
VICTIM=0x28ef00

def far(op,target):return bytes([op])+target.to_bytes(3,'little')
def imm(op,num):return bytes([op])+num.to_bytes(2,'little')

class Code:
    def __init__(self,base):
        self.base=base;self.buf=bytearray();self.labels={};self.refs=[]
    def put(self,b):self.buf.extend(bytes.fromhex(b) if isinstance(b,str) else b)
    def lab(self,key):self.labels[key]=self.base+len(self.buf)
    def go(self,key):
        self.put('5c000000');self.refs.append((len(self.buf)-3,key))
    def when(self,op,key):
        # Skip the long jump when the condition is false.
        self.put(bytes([op^0x20,4]));self.go(key)
    def done(self):
        for at,key in self.refs:self.buf[at:at+3]=self.labels[key].to_bytes(3,'little')
        return bytes(self.buf)

def copy_stage(raw,read):
    # Authenticate every original slot/ID and five actual DMA descriptors.
    original=read(raw,0x308172,13*35)
    ids=[];stanzas=bytearray();patched=bytearray()
    for i in range(13):
        row=(51+i)*8;tile=((51+i)%8)*2+(((51+i)//8)%4)*64+((51+i)//32)*256
        at=i*35;first=imm(0xa9,row)+far(0x8f,0x439620+2*i)+imm(0xa9,tile)+far(0x8f,0x439640+2*i)
        ident=int.from_bytes(original[at+15:at+17],'little')
        tail=far(0x8f,0x7e4c00+row)+imm(0xa9,1)+far(0x8f,0x7e4c02+row)+imm(0xa9,256)+far(0x8f,0x432000+row)
        stanzas+=first+imm(0xa9,ident)+tail
        patched+=first+imm(0xa9,0xffff if i==0 else BASE_MARK+16+i)+tail.replace(imm(0xa9,1)+far(0x8f,0x7e4c02+row),imm(0xa9,PRIVATE)+far(0x8f,0x7e4c02+row))
        ids.append(ident)
    if original!=stanzas or len(set(ids))!=13 or max(ids)>=BASE_MARK:raise ValueError('original atlas claims differ')
    for j,(src,dest,size) in enumerate(CHUNKS[:4]+((0x309060,0x5c00,2048),)):
        original=read(raw,0x308433+j*37,37)
        expect=b'\xc2\x30'+imm(0xa9,src&0xffff)+far(0x8f,0x4372)+imm(0xa9,size)+far(0x8f,0x4375)+imm(0xa9,dest)+far(0x8f,0x2116)+bytes.fromhex('e220a9308f744300a9808f0b4200')
        if original!=expect:raise ValueError('stock physical DMA descriptor '+str(j))
    return ids,bytes(stanzas),bytes(patched)

def build(raw,read,latest):
    ids,oldslots,newslots=copy_stage(raw,read)
    def expect(a,h):
        if read(raw,a,len(bytes.fromhex(h))).hex()!=h:raise ValueError('patch seam '+hex(a))
    expect(BOOT,'78e220af03507e8f809643297f8f004200a9808f002100c230')
    expect(0x308000,'08c23048da5a8b0bd8')
    expect(0x308339,'e220221287309003')
    expect(0xd25e,'a9008d0c428f06507ea9808d0021c23120a9c3209cf62287923d')
    expect(0x10c1fb,'2228ec10')
    expect(0x30869b,'a90d008f169643a900008fec4b7ea901008f009643a903008f149643e220')
    saved='08c23048da5a';rest='7afa6828'
    # The scan and epoch change still run in the original caller. Arm last.
    arm=Code(ARM);arm.put(imm(0xa9,BASE_MARK)+far(0x8f,ROW));arm.put(far(0x5c,0x308709))
    # Only the real NMI commit arm calls this hook, with HDMA off and forced blank.
    # Use WRAM and immutable ROM only in NMI: no conversion-sensitive BW-RAM.
    q=Code(NMI);q.put(far(0x22,0x3d9287));q.put(saved)
    q.put(far(0xaf,ROW)+imm(0xc9,BASE_MARK));q.when(0x90,'done')
    q.put(imm(0xc9,BASE_MARK+COUNT));q.when(0xb0,'done')
    for a,value in ((0x7e2750,0),(0x7e2758,0),(0x7e275e,3)):
        q.put(far(0xaf,a))
        if a==0x7e275e:q.put(imm(0x29,255))
        q.put(imm(0xc9,value));q.when(0xd0,'done')
    q.put(far(0xaf,0x7e5005)+imm(0x29,0x0080));q.when(0xd0,'done')
    for i in range(13):
        if i:
            q.put(far(0xaf,ROW+8*i)+imm(0xc9,BASE_MARK+16+i));q.when(0xd0,'done')
        q.put(far(0xaf,ROW+8*i+2)+imm(0xc9,PRIVATE));q.when(0xd0,'done')
        q.put(far(0xaf,ROW+8*i+4)+imm(0x29,255));q.when(0xd0,'done')
    # Latch after validating the rows. Inherit the original convention for
    # WRIO and the counter high/low latch. Reject late or non-vblank calls.
    q.put('e220af1242002980');q.when(0xf0,'done')
    q.put('af1342004809808f014200af372100af3f2100af3d2100c22029ff00aae220af3d21002901eb688f014200ebc220290100');q.when(0xd0,'done')
    q.put(imm(0xe0,225));q.when(0x90,'done')
    q.put(imm(0xe0,latest+1));q.when(0xb0,'done')
    q.put('e220')
    for i in range(7):q.put(far(0xaf,0x4370+i)+b'\x48')
    q.put('a9808f152100a9018f704300a9188f714300a9308f744300c220')
    q.put(far(0xaf,ROW))
    for i in range(COUNT-1):
        q.put(imm(0xc9,BASE_MARK+i));q.when(0xf0,'slice'+str(i))
    q.go('slice7')
    for i,(src,dest,size) in enumerate(CHUNKS):
        q.lab('slice'+str(i));q.put(imm(0xa9,src&65535)+far(0x8f,0x4372)+imm(0xa9,dest)+far(0x8f,0x2116)+imm(0xa9,size)+far(0x8f,0x4375));q.go('dma')
    q.lab('dma');q.put('e220a9808f0b4200');q.lab('physical_return')
    for i in reversed(range(7)):q.put(b'\x68'+far(0x8f,0x4370+i))
    q.put('c220');q.put(far(0xaf,ROW)+b'\x1a'+far(0x8f,ROW))
    q.lab('done');q.put('c230'+rest+'6b')
    # An original foreground publication boundary revalidates the full reservation.
    # Busy/boot/readiness fields remain untouched in the interrupt.
    f=Code(FINISH);f.put(saved);f.put(far(0xaf,ROW));f.put(imm(0x29,0xfff0)+imm(0xc9,BASE_MARK));f.when(0xd0,'done')
    for addr,val,mask in ((0x7e2750,0,65535),(0x7e2758,0,65535),(0x7e275e,3,255)):
        f.put(far(0xaf,addr)+imm(0x29,mask)+imm(0xc9,val));f.when(0xd0,'cancel')
    f.put(far(0xaf,ROW)+imm(0xc9,BASE_MARK+COUNT));f.when(0xd0,'done')
    # The established foreground uses BW-RAM only in ordinary game service.
    for addr,val in ((0x439600,0),(0x439614,1),(0x7e175c,1)):
        f.put(far(0xaf,addr)+imm(0xc9,val));f.when(0xd0,'cancel')
    for i in range(13):
        idx=8*(51+i)
        for addr,val,mask in ((ROW+i*8,BASE_MARK+COUNT if not i else BASE_MARK+16+i,65535),(ROW+i*8+2,PRIVATE,65535),(ROW+i*8+4,0,255),(0x432000+idx,256,65535),(0x432200+idx,0,65535)):
            f.put(far(0xaf,addr)+imm(0x29,mask)+imm(0xc9,val));f.when(0xd0,'cancel')
    # No incomplete row is available under a real catalog ID. Publish
    # the original ready states then the stock PPBoot/boot-status pair.
    for i,ident in enumerate(ids):f.put(imm(0xa9,ident)+far(0x8f,ROW+i*8))
    ready=read(raw,0x3084ec,0x3086b7-0x3084ec)
    if ready[:9]!=bytes.fromhex('c230a902008f9a4d7e') or ready[-4:]!=far(0x8f,0x439614):raise ValueError('ready group end')
    f.put(ready);f.go('done');f.lab('cancel');f.put(far(0x22,RELEASE));f.lab('done');f.put(rest);f.put(far(0x5c,0x10ec28))
    # Cancel on a fresh bootstrap or a state transition. Revoke row zero's
    # arm before other rows, and release only exactly-matching private claims.
    c=Code(RELEASE);c.put(saved);c.put(far(0xaf,ROW)+imm(0x29,0xfff0)+imm(0xc9,BASE_MARK));c.when(0xd0,'done')
    c.put(imm(0xa9,0xffff)+far(0x8f,ROW))
    for i in range(13):
        skip='skip'+str(i);idx=8*(51+i)
        for addr,val,mask in ((ROW+i*8,0xffff if not i else BASE_MARK+16+i,65535),(ROW+i*8+2,PRIVATE,65535),(ROW+i*8+4,0,255),(0x432000+idx,256,65535),(0x432200+idx,0,65535)):
            c.put(far(0xaf,addr)+imm(0x29,mask)+imm(0xc9,val));c.when(0xd0,skip)
        c.put(imm(0xa9,0)+far(0x8f,ROW+i*8+2)+far(0x8f,0x432000+idx));c.lab(skip)
    c.put(imm(0xa9,0)+far(0x8f,0x7e4bec));c.lab('done');c.put(rest+'6b')
    reset=far(0x22,RELEASE)+bytes.fromhex('08c23048')+far(0x5c,0x308004)
    # Do not let the normal state-1 pending uploader see private rows.
    # The victim scan treats only the reserved state as ineligible. Preserve
    # caller carry/N/Z for ordinary rows by repeating the original load.
    expect(0x10a61a,'bf024c7ef023c90100f013')
    victim=bytes.fromhex('08bf024c7e')+imm(0xc9,PRIVATE)+bytes.fromhex('d00528')+far(0x5c,0x10a638)+bytes.fromhex('28bf024c7e')+far(0x5c,0x10a61e)
    adds=[(NMI,q.done()),(ARM,arm.done()),(FINISH,f.done()),(RESET,reset),(RELEASE,c.done()),(VICTIM,victim)]
    changes=[(0x10a61a,bytes.fromhex("bf024c7e"),far(0x5c,VICTIM)),(0x308000,bytes.fromhex('08c23048'),far(0x5c,RESET)),(BOOT,bytes.fromhex('78e220af'),far(0x5c,0x308172)),(0x308172,oldslots,newslots),(0x308339,bytes.fromhex('e2202212'),far(0x5c,ARM)),(0xd274,far(0x22,0x3d9287),far(0x22,NMI)),(0x10c1fb,far(0x22,0x10ec28),far(0x22,FINISH))]
    return adds,changes,q.labels,f.labels

def fix(raw,candidate,sy,latest=233):
    adds,changes,_,_=build(raw,candidate.connected.link.read,latest)
    for i,(a,b) in enumerate(sorted(adds)):
        if i+1<len(adds) and a+len(b)>sorted(adds)[i+1][0]:raise ValueError('helper overlap '+hex(a))
        if any(a<=v<a+len(b) for tab in sy for v in tab.values() if type(v)is int):raise ValueError('occupied helper')
    return candidate.finish_bytes(raw,raw,(),adds,changes)[0]
