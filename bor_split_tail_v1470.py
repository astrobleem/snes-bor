"""Run one authenticated split upload after all retained committed-NMI clients."""
import bor_split_atlas_v1467 as split
TRAMP=0x28f000

def fix(raw,candidate,sy):
    read=candidate.connected.link.read
    adds,changes,q,_=split.build(raw,read,249)
    far=split.far
    head=read(raw,0xd347,11)
    if head!=bytes.fromhex("af02507ef0053a8f02507e"):
        raise ValueError("normal-only skipped-frame decrement")
    if read(raw,0xd352,15)!=bytes.fromhex("22ddf8105c6ae631ea2bab7afa6860"):
        raise ValueError("shared input and physical-publisher tail")
    tail=read(raw,0x31e66a,14)
    if tail!=bytes.fromhex("2250b930af104200c2305c5bd300"):
        raise ValueError("physical publisher tail changed")
    # Retained normal tail before the join, then both native publisher calls.
    # The skipped-interrupt arm continues to use the untouched original join.
    body=head+far(0x22,0x10f8dd)+tail[:-4]+far(0x22,split.NMI+4)+tail[-4:]
    adds.append((TRAMP,body))
    hooks=[(a,o,n) for a,o,n in changes if a!=0xd274]
    if len(hooks)+1!=len(changes) or read(raw,0xd274,4)!=far(0x22,0x3d9287):
        raise ValueError("exactly one early NMI seam must remain stock")
    hooks.append((0xd347,head[:4],far(0x5c,TRAMP)))
    for i,(a,b) in enumerate(sorted(adds)):
        if i+1<len(adds) and a+len(b)>sorted(adds)[i+1][0]:raise ValueError("helper overlap")
        if any(a<=v<a+len(b) for tab in sy for v in tab.values() if type(v)is int):raise ValueError("linked label overlap")
    return candidate.finish_bytes(raw,raw,(),adds,hooks)[0]
