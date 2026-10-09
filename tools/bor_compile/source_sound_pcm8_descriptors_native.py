"""Bind admitted PCM8 identity to an integer-stride, gain-64 worker lease.

Other prepared periods or gains require their matching worker capability and
fail this descriptor capability explicitly. No RAM allocation or frame Ack.
"""
def emit(work,channels,lengths,bases,metadata,sy,*,samples=30):
    if not 1<=samples<=32767 or not 0<=metadata<=0xffffff-8-samples*8:
        raise ValueError('PCM8_DESCRIPTOR_METADATA_DOMAIN')
    ranges=[(work,work+32),(channels,channels+480),(lengths,lengths+48),(bases,bases+48)]
    if any(not 0<=a<b<=0x1000000 for a,b in ranges)or any(max(a,c)<min(b,d)for i,(a,b)in enumerate(ranges)for c,d in ranges[i+1:]):
        raise ValueError('PCM8_DESCRIPTOR_RAM_DOMAIN')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SoundPCM8Descriptor_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='SoundPCM8Descriptor_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp SoundPCM8Descriptor_'+n+'\n'+l+':\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    label('Run');put(' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #24\n tcs\n inc a\n tcd')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
    for at,v in ((work,0xb63b),(work+2,2),(work+30,0xb63c),(metadata,0x4350),(metadata+2,0x4438),(metadata+4,1),(metadata+6,samples),(work+12,4096),(work+14,0),(work+16,64),(work+18,0),(work+20,64),(work+22,0)):
        require(at,v)
    put(f' lda.l {work}+28\n cmp #12');branch('bcs');put(' asl a\n asl a\n sta $02\n asl a\n pha\n asl a\n asl a\n clc\n adc 1,s\n tax\n pla')
    # X is selected*40; descriptor slots use selected*4 at DP02.
    put(f' lda.l {channels}+8,x\n cmp.l {work}+4');branch('bne')
    put(f' lda.l {channels}+10,x');branch('bne')
    for off in (0,2):put(f' lda.l {channels}+16+{off},x\n cmp.l {work}+24+{off}');branch('bne')
    put(f' lda.l {work}+4\n cmp #{samples}');branch('bcs');put(' asl a\n asl a\n asl a\n tax')
    for src,dst in ((metadata+8,6),(metadata+10,8),(metadata+12,10),(metadata+14,12)):
        put(f' lda.l {src},x\n sta ${dst:02X}')
    put(' lda $06\n ora $08');branch('beq');put(' lda $06\n and #1');branch('bne')
    put(f' lda.l {work}+8\n asl a\n sta $0E\n lda.l {work}+6\n rol a\n sta $10\n cmp $08');branch('bne');put(' lda $0E\n cmp $06');branch('bne')
    put(' lda $0C\n cmp #$E0');branch('bcc');put(' cmp #$100');branch('bcs');put(' lda $0A\n and #1');branch('bne')
    put(' lda $0A\n clc\n adc $06\n sta $12\n lda $0C\n adc $08\n cmp #$100');branch('bcc','EndGood');branch('bne');put(' lda $12');branch('bne')
    label('EndGood');put(' ldx $02')
    for src,dst in ((6,lengths),(8,lengths+2),(10,bases),(12,bases+2)):
        put(f' lda ${src:02X}\n sta.l {dst},x')
    put(' tsc\n clc\n adc #24\n tcs\n pld\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(' tsc\n clc\n adc #24\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
