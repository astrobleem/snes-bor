"""Atomic native set_opponent with real owner resolution in world phase 8.

Caller leases 24 serialized foreign-work bytes: B6A9, status, entity slot,
other slot, generation DWORD, and reserved words. FFFF is NULL. This is a
service body, not damage acceptance or a world acknowledgement.
"""


def emit(work,sy):
    lines=[];serial=0;size=48
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SetOpponent_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='SetOpponent_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {l}\n jmp SetOpponent_{n}\n{l}:\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $28\n sty $2A')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6a9)
    for op,off in (('txa',8),('tya',10)):put(f' {op}\n cmp.l {work}+{off}');branch('bne')
    for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),
                 (sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),
                 (sy['SourceRetirement4086_Ready'],0xb4f8)):
        require(at,v)
    for off in (0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
    put(f' lda.l {sy["VmSourceWorld_Count"]}');branch('beq');put(' cmp #129');branch('bcs')
    put(f' lda.l {work}+4\n cmp #$FFFF');branch('beq','Good')
    put(f' cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00\n sta $04')
    put(f' lda.l {work}+6\n sta $02\n sta $06\n cmp #$FFFF');branch('beq','OtherChecked')
    put(f' cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs')
    label('OtherChecked')
    # Resolve both complete graphs before the first opponent write.
    for src,root in ((0,4),(2,6)):
        put(f' lda ${src:02X}\n cmp #$FFFF');branch('beq','Resolved'+str(src));put(' lda #0\n sta $08')
        label('OwnerLoop'+str(src));put(' inc $08\n lda $08\n cmp #129');branch('bcs')
        put(f' lda ${root:02X}\n asl a\n asl a\n asl a\n asl a\n sta $0A\n asl a\n asl a\n sta $0C\n clc\n adc $0A\n adc #$4000')
        put(f' sta $0E\n sta.l {sy["SourceRetirement4086_ArgLo"]}\n lda #$41\n sta.l {sy["SourceRetirement4086_ArgHi"]}\n jsl {sy["SourceRetirement4086_ResolvePointer"]}');branch('bcs')
        put(' lda $0E\n tax\n cmp.l $410000,x');branch('bne');put(' lda.l $410002,x\n cmp #$41');branch('bne')
        put(' lda $0C\n tax\n lda.l $40903A,x\n cmp #$B638');branch('bne')
        put(' lda.l $409008,x\n sta $0E\n lda.l $40900A,x\n sta $10\n ora $0E');branch('beq','Resolved'+str(src))
        for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda ${14+off:02X}\n sta.l {sy["SourceRetirement4086_Arg"+n]}')
        put(f' jsl {sy["SourceRetirement4086_ResolvePointer"]}');branch('bcs');put(' cmp #$FFFF');branch('beq')
        put(f' sta ${root:02X}\n jmp SetOpponent_OwnerLoop{src}')
        label('Resolved'+str(src))
    # Snapshot both root tokens before assignments, preserving shared-root alias.
    for root,dst in ((4,18),(6,22)):
        put(f' lda ${root:02X}\n cmp #$FFFF');branch('beq','NullToken'+str(root))
        put(f' asl a\n asl a\n asl a\n asl a\n sta $0A\n asl a\n asl a\n clc\n adc $0A\n adc #$4000\n sta ${dst:02X}\n lda #$41\n sta ${dst+2:02X}\n jmp SetOpponent_Token{root}')
        label('NullToken'+str(root));put(f' lda #0\n sta ${dst:02X}\n sta ${dst+2:02X}');label('Token'+str(root))
    for slots,token in (((0,4),22),((2,6),18)):
        if slots==(2,6):put(' lda $06\n cmp #$FFFF');branch('beq','Good')
        for slot in slots:
            put(f' lda ${slot:02X}\n asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n tax')
            for off in (0,2):put(f' lda ${token+off:02X}\n sta.l $40900C+{off},x')
    for name,status,carry in (('Good',2,'clc'),('Bad',3,'sec')):
        label(name);put(f' lda #{status}\n sta.l {work}+2\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
    return '\n'.join(lines)+'\n'
