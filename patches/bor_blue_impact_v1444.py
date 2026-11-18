"""Authenticated P2 impact palette for the isolated Kula two-player stage."""
import hashlib
import struct

BASE=0x28c600
ADMIT=0x28c700
TABLE=0x28c780
PALETTE=bytes.fromhex('1f7c414de1408030401c3605ae00104a1867ff7bde73d64eff223d0e7c63d239')
MAP_LOAD=bytes.fromhex('afb90a7e29ff00')
GATES=(0x308969,0x309918,0x30b174,0x31c258,0x31e3ce,0x31eb59)

def check_catalog(path):
    with path.open('rb') as f:
        def read(offset,n):
            f.seek(30977164+offset)
            data=f.read(n)
            if len(data)!=n:raise ValueError('short original resource')
            return data
        rows=[]
        for index in (785,786):
            meta=struct.unpack('<BBBBHHhhHHII',read(18+index*24,24))
            if meta[:4]!=(22,2,2,index-785) or meta[8]!=13:raise ValueError('impact entry')
            rows.append(list(struct.iter_unpack('<hhhhBBHHH',read(0x1856a+meta[10]*16,208))))
        for a,b in zip(*rows):
            if a[:5]+a[7:]!=b[:5]+b[7:] or (a[6],b[6])!=(361,353):raise ValueError('impact pair mismatch')
        digest,size,offset,length=struct.unpack('<32sHII',read(0x1b3af6+353*42,42))
        if size!=32 or length!=32 or read(offset,32)!=PALETTE or hashlib.sha256(PALETTE).digest()!=digest:
            raise ValueError('original alternate palette mismatch')

def fix(private,msu,candidate,catalogs):
    check_catalog(msu)
    read=candidate.connected.link.read
    def addr(x):return x.to_bytes(3,'little')
    def jump(x):return b'\x5c'+addr(x)
    def call(x):return b'\x22'+addr(x)
    def conditionals(prefix,clauses,success,done):
        out=bytearray.fromhex(prefix);branches=[]
        for clause in clauses:
            out.extend(bytes.fromhex(clause));branches.append(len(out));out.append(0)
        out.extend(bytes.fromhex(success))
        for at in branches:
            distance=len(out)-at-1
            if not 0<=distance<=127:raise ValueError('branch outside range')
            out[at]=distance
        return bytes(out)+done
    # Narrow completion seam. The ordinary MDMAEN store completes first.
    # A, X, flags and the original short-return bank are preserved. A ready
    # byte is never manufactured and an existing owner is never replaced.
    dma=bytes.fromhex('8d0b42c23160')
    retained=read(private,0x00c4bb,51)
    if retained.count(dma)!=1:raise ValueError('CGRAM completion seam differs')
    end=0xc4bb+retained.index(dma)
    prefix='8d0b42 c231 08 48 da'
    checks=['bf80047e c92000 d0','bf82047e c90001 d0','bf85047e c90049 d0',
            'bf87047e 29ff00 c97e00 d0','af009643 c90100 d0','afb90a7e 29ff00 c90100 d0',
            'afa04f7e c96101 d0']
    # After matching the ordinary slot-zero staging address, compare all
    # 32 bytes actually transferred with the private ROM reference.
    checks+=['a21e00 bf00497e df80c728 d0']
    success='ca ca 10f2 af002443 090001 8f002443'
    # DEX/DEX/BPL returns to LDA staging,X, not to the LDX that sets 30.
    assert bytes.fromhex(success)[3]==242
    pin=conditionals(prefix,checks,success,bytes.fromhex('fa6828')+jump(end+5))
    # Guard each formerly map-zero publication/acquisition. Other roster,
    # scene, generation, queue, physical-ready and cancellation tests remain.
    clauses=['afb90a7e 29ff00 c90100 d0','afa04f7e c96101 d0','afa34f7e 29ff00 c90100 d0',
             'af002443 890001 f0']
    admit=conditionals('',clauses,'a90000 6b',bytes.fromhex('a901006b'))
    before=bytes.fromhex('af0c96430a0f169843')
    if read(private,0x25af0a,len(before))!=before:raise ValueError('wrong P2 worker colour selector')
    stock=read(private,0x10c5f5,27)
    if bytes.fromhex('bf0024431f40244329ff03') not in stock:raise ValueError('published hold not protected')
    adds=((BASE,pin),(ADMIT,admit),(TABLE,PALETTE))
    for symbols in catalogs:
        for a,b in adds:
            if any(type(v) is int and a<=v<a+len(b) for v in symbols.values()):raise ValueError('private code label conflict')
    patches=[(end,dma[:4],jump(BASE)),(0x25af0a,before[:4],bytes.fromhex('a90000ea'))]
    for a in GATES:patches.append((a,MAP_LOAD,call(ADMIT)+bytes.fromhex('eaeaea')))
    return candidate.finish_bytes(private,private,(),adds,patches)[0]
