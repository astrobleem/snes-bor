"""Retain the original, physically transferred blue palette while atlas DMA is pending."""
import bor_split_budget_v1473 as tiles
import bor_split_atlas_v1467 as sp
import bor_blue_impact_v1444 as blue
compose=tiles.compose
evidence=tiles.evidence
observer=tiles.observer
ELIG=0x29c600
PIN=0x29c700
ARM=0x29c800
CANCEL=0x29c900
PUB=0x29ca00
TAG=0x75e5
def fix(raw,candidate,sy):
    raw=tiles.fix(raw,candidate,sy)
    read=candidate.connected.link.read;I=sp.imm;L=sp.far
    boot=0x439600;held=0x432400;tag=sp.ROW+6
    e=sp.Code(ELIG);e.put(L(0xaf,boot));e.when(0xd0,'ret')
    e.put(L(0xaf,sp.ROW)+I(0xc9,sp.BASE_MARK));e.when(0x90,'no')
    e.put(I(0xc9,sp.BASE_MARK+9));e.when(0xb0,'no')
    for a,v in ((sp.ROW+2,sp.PRIVATE),(0x439614,1),(0x7e175c,1)):
        e.put(L(0xaf,a)+I(0xc9,v));e.when(0xd0,'no')
    e.put(I(0xa9,1));e.lab('ret');e.put('6b');e.lab('no');e.put(I(0xa9,0));e.put('6b')
    # Existing exact descriptor/map/ID and all 32 byte comparisons precede PIN.
    pin=sp.Code(PIN);pin.put(L(0xaf,boot));pin.when(0xd0,'hold')
    pin.put(L(0xaf,held)+I(0x89,0x100));pin.when(0xd0,'hold')
    pin.put(I(0xa9,TAG)+L(0x8f,tag));pin.lab('hold')
    seq=L(0xaf,held)+I(0x09,0x100)+L(0x8f,held)
    pin.put(seq);pin.put('6b')
    arm=I(0xa9,0)+L(0x8f,tag)+I(0xa9,sp.BASE_MARK)+L(0x8f,sp.ROW)+L(0x5c,0x308709)
    # Revoke the phase first. Drop only the bit acquired by this private owner.
    c=sp.Code(CANCEL);c.put(L(0x8f,sp.ROW));c.put(L(0xaf,tag)+I(0xc9,TAG));c.when(0xd0,'done')
    c.put(L(0xaf,sp.ROW+2)+I(0xc9,sp.PRIVATE));c.when(0xd0,'done')
    c.put(L(0xaf,boot));c.when(0xd0,'done')
    c.put(L(0xaf,held)+I(0x29,0xfeff)+L(0x8f,held)+I(0xa9,0)+L(0x8f,tag))
    c.lab('done');c.put('6b')
    # Private palette receipt alone never grants permission to publish. The
    # original ready stanzas transfer ownership, then set PPBoot after all DMA.
    u=sp.Code(PUB);u.put(L(0xaf,boot)+I(0xc9,1));u.when(0xd0,'no')
    u.put(L(0xaf,0x7e0ab9)+L(0x5c,blue.ADMIT+4));u.lab('no');u.put(I(0xa9,1));u.put('6b')
    def seam(base,n,pattern):
        b=read(raw,base,n)
        if b.count(pattern)!=1:raise ValueError("ambiguous retained seam")
        return base+b.index(pattern)
    hook1=seam(blue.BASE,118,L(0xaf,boot)+I(0xc9,1))
    hook2=seam(blue.BASE,118,seq)
    clear=seam(sp.RELEASE,40,I(0xa9,65535)+L(0x8f,sp.ROW))+3
    adds=[(ELIG,e.done()),(PIN,pin.done()),(ARM,arm),(CANCEL,c.done()),(PUB,u.done())]
    patches=[(hook1,L(0xaf,boot),L(0x22,ELIG)),(hook2,seq,L(0x22,PIN)+bytes([0xea])*(len(seq)-4)),
             (sp.ARM,I(0xa9,sp.BASE_MARK)+L(0x8f,sp.ROW),L(0x5c,ARM)+bytes([0xea])*3),
             (clear,L(0x8f,sp.ROW),L(0x22,CANCEL)),(blue.ADMIT,L(0xaf,0x7e0ab9),L(0x5c,PUB))]
    for a,b in adds:
        if any(a<=v<a+len(b) for tab in sy for v in tab.values() if type(v)is int):raise ValueError("linked label overlap")
    return candidate.finish_bytes(raw,raw,(),adds,patches)[0]
