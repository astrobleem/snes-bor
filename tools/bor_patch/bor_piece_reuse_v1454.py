"""Reuse the just-computed normal piece geometry during ordinary non-mirrored emission."""
def fix(raw,candidate,sy):
    read=candidate.connected.link.read
    a=0x10b05d; helper=0x28cd00
    def long(op,d):return bytes((op,))+d.to_bytes(3,'little')
    expected={0x10af69:'207cb1b003820e01',0x10b17c:'2085b1b0032011b260',
              a:'c2312085b19003200fb12011b29013',
              0x10b10f:'e220afa6447e8fab537eafa8447e8fac537e'}
    # Authenticate the path between the successful first clip and the write.
    # Only per-piece attributes and diagnostic cells are written here. The
    # normal X/Y/size and source piece index are unchanged on that path.
    attr=bytes.fromhex('afa6447e8fab537eafa8447e8fac537eaf5e4b7e0a0a0a0aaa8faa4b7ebf0e407e29ff01186f524b7ee2208fad537ebf08407e8fa44b7ec231af624b7e18691000186fa44b7eaae220bf804a7ef0093a8f4c467ec9089003822f01c220afaa4b7eaae220af4c467e0a09308fae537ec220bf0e407e29ff01186f524b7e290001f00ce220afae537e09018fae537ee220a508f00cafae537e09408fae537e8000afa4447ef00aafae537e29cf8fae537ea9258fd8457ea9018f40467ec220bf0e407e290080f006e220a9028004e220a9008faf537ec220afa6447e290001f00ce220afaf537e09018faf537e')
    if len(attr)!=a-0x10af71 or read(raw,0x10af71,len(attr))!=attr:raise ValueError('attribute writer or boundaries changed')
    for pos,val in expected.items():
        if read(raw,pos,len(bytes.fromhex(val))).hex()!=val:raise ValueError('emitter seam changed')
    # Retain stock clipping for mirrored stages. PEA reproduces the displaced
    # bank-local JSR return (the original BCC at $10:B062 remains intact).
    slow=bytes.fromhex('f461b0')+long(0x5c,0x10b185)
    fast=long(0xaf,0x7e44a8)+bytes.fromhex('18')+long(0x6f,0x7e44ae)+bytes.fromhex('38')+long(0x5c,0x10b064)
    code=bytes.fromhex('c231')+long(0xaf,0x7e27af)+bytes.fromhex('29ff00f0')+bytes([len(slow)])+slow+fast
    if any(helper<=v<helper+len(code) for tab in sy for v in tab.values() if type(v)is int):raise ValueError('helper overlaps label')
    return candidate.finish_bytes(raw,raw,(),[(helper,code)],[(a,bytes.fromhex(expected[a])[:5],long(0x5c,helper)+b'\xea')])[0]
