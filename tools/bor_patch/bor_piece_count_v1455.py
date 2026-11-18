"""Count visible normal sprites with register-local geometry. Stock last iteration preserves scratch."""
SITE=0x10aee3
BASE=0x28ce00
PRECOUNT=bytes.fromhex('a900008faa447e8f5e4b7eaf5e4b7ecf544b7eb0272085b19009afaa447e1a8faa447e2011b29009afaa447e1a8faa447eaf5e4b7e1a8f5e4b7e80cf')
CLIP=bytes.fromhex('af5e4b7e0a0a0a0aaabf0e407e290080f00ca920008fac447ea94000800aa910008fac447ea920008fae447ea50829ff00f013bf04407e186fa0447e8fa6447ebf06407e8011bf00407e186fa0447e8fa6447ebf02407e186fa2447e8fa8447eafa6447e3005c90001b01f186fac447e3018f016afa8447e3005c9e000b00b186fae447e3004f00238601860')
def long(op,a):return bytes([op])+a.to_bytes(3,'little')
def imm(op,a):return bytes([op])+a.to_bytes(2,'little')
def make():
    out=bytearray();labels={}; pending=[]
    def mark(k):labels[k]=len(out)
    def br(op,k):out.extend([op,0]);pending.append((len(out)-1,k,1))
    def j(k):out.extend(b'\x82\0\0');pending.append((len(out)-2,k,2))
    # Fall back if decimal mode, mirrored, empty/single or out of contract.
    out.extend(bytes.fromhex('08e220688908c220'));br(0xd0,'ordinary')
    out.extend(long(0xaf,0x7e27af)+imm(0x29,255));br(0xd0,'ordinary')
    out.extend(long(0xaf,0x7e4b54)+imm(0xc9,2));br(0x90,'ordinary')
    out.extend(imm(0xc9,66));br(0xb0,'ordinary');br(0x80,'enter')
    mark('ordinary');out.extend(PRECOUNT[:11]+long(0x5c,SITE+11))
    mark('enter');out.extend(bytes.fromhex('5a3a0a0a0a0a48a20000a00000a50829ff00'));br(0xf0,'right');j('left')
    for side,off in [('right',0),('left',4)]:
        mark(side);out.extend(long(0xbf,0x7e400e));br(0x30,side+'large')
        for size,w,h in [('small',16,32),('large',32,64)]:
            mark(side+size)
            for field,base,extent,limit in ((off,0x7e44a0,w,256),(off+2,0x7e44a2,h,224)):
                out.extend(long(0xbf,0x7e4000+field)+b'\x18'+long(0x6f,base)+b'\x18'+imm(0x69,extent-1)+imm(0xc9,limit+extent-1))
                br(0xb0,side+'next')
            out.append(0xc8) # INY
            if size=='small':br(0x80,side+'next')
        mark(side+'next');out.extend(bytes.fromhex('8a18691000aac301'));br(0xb0,'finish'+side);j(side)
        mark('finish'+side);j('finish')
    mark('finish');out.extend(b'\x98'+long(0x8f,0x7e44aa)+bytes.fromhex('684a4a4a4a')+long(0x8f,0x7e4b5e)+b'\x7a'+long(0x5c,SITE+11))
    for at,k,n in pending:out[at:at+n]=(labels[k]-at-n).to_bytes(n,'little',signed=True)
    return bytes(out)

def fix(raw,candidate,sy):
    read=candidate.connected.link.read
    for a,data in ((SITE,PRECOUNT),(0x10b185,CLIP),(0x10b211,bytes.fromhex('afaf277e29ff00d0021860'))):
        if read(raw,a,len(data))!=data:raise ValueError('exact source geometry changed')
    code=make()
    if any(BASE<=v<BASE+len(code) for tab in sy for v in tab.values() if type(v)is int):raise ValueError('occupied')
    return candidate.finish_bytes(raw,raw,(),[(BASE,code)],[(SITE,PRECOUNT[:7],long(0x5c,BASE)+b'\xea'*3)])[0]
