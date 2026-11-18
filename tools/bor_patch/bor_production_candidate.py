from types import SimpleNamespace
import bor_production_link as link
connected=SimpleNamespace(link=link)

def finish_bytes(raw,initial,spans,additions,patches):
    """Exact disjoint patch accounting. Internal, not native admission."""
    if len(raw)!=4194304 or len(initial)!=len(raw):raise ValueError('exact 4MiB image required')
    out=bytearray(initial);owned=[]
    for at,n in spans:
        a,b=connected.link.mapping().rom_file_span(at,n);owned.append((a,b))
    for at,data in additions:
        a,b=connected.link.mapping().rom_file_span(at,len(data))
        if raw[a:b]!=bytes(len(data)):raise ValueError('retained component/fixture span occupied:%06X'%at)
        if any(a<y and x<b for x,y in owned):raise ValueError('patch component overlap:%06X'%at)
        owned.append((a,b));out[a:b]=data
    for at,old,new in patches:
        a,b=connected.link.mapping().rom_file_span(at,len(old))
        if len(old)!=len(new) or raw[a:b]!=old or initial[a:b]!=old:raise ValueError('actual caller instruction mismatch')
        if any(a<y and x<b for x,y in owned):raise ValueError('caller overlaps component')
        owned.append((a,b));out[a:b]=new
    # Standard fixed-size/no-copier-header SA1 image. Complement+checksum
    # bytes sum510 independent of the resulting16-bit checksum.
    a,b=0x7fdc,0x7fe0
    if any(a<y and x<b for x,y in owned):raise ValueError('component overlaps header checksum')
    out[a:b]=b'\xff\xff\0\0';checksum=sum(out)&65535
    out[a:b]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little');owned.append((a,b))
    if sum(out)&65535!=checksum:raise ValueError('private checksum inconsistent')
    allowed=bytearray(len(raw))
    for a,b in owned:
        if any(allowed[a:b]):raise ValueError('patch-mask alias')
        allowed[a:b]=b'\x01'*(b-a)
    if any(a!=b and not allowed[i] for i,(a,b) in enumerate(zip(raw,out))):raise ValueError('unaccounted ROM change')
    return bytes(out),tuple(owned)
