"""Pinned special continuation over a caller-owned 192-byte snapshot.

HP/MP eligibility and BLOCK validity are mandatory readonly queries. Linked
idle, smartbomb and SPECIAL animation are mandatory callback services. Resource
debit follows callbacks and uses fresh descriptor/resource fields.
"""
from source_player_run_4086 import KEYS


def emit(work):
    if not 0<=work<=0x1000000-192:raise ValueError('PLAYER_SPECIAL_NATIVE_EXTENT')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SourceSpecial_'+n+':\n.a16\n.i16')
    def jump(n):put(' jmp SourceSpecial_'+n)
    def branch(op,n):
        nonlocal serial
        serial+=1;skip='SourceSpecial_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcs='bcc',bcc='bcs',bvs='bvc')[op]+' '+skip+'\n jmp SourceSpecial_'+n+'\n'+skip+':\n.a16\n.i16')
    def zero(off):put(f' lda.l W+{off}\n ora.l W+{off+2}')
    def clear(off):put(f' lda #0\n sta.l W+{off}\n sta.l W+{off+2}')
    def assign(off,value):put(f' lda #{value&65535}\n sta.l W+{off}\n lda #{value>>16&65535}\n sta.l W+{off+2}')
    def copy(src,dst):put(f' lda.l W+{src}\n sta.l W+{dst}\n lda.l W+{src+2}\n sta.l W+{dst+2}')
    def query(role,continuation):
        put(f' lda #{role}\n sta.l W+12\n lda #0\n sta.l W+6\n lda #{continuation}\n sta.l W+4\n lda #3');jump('Pending')
    def service(kind,continuation):
        put(f' lda #{kind}\n sta.l W+6\n lda #65535\n sta.l W+12\n lda #{continuation}\n sta.l W+4\n lda #4');jump('Pending')
    for entry,dest in (('Begin','Start'),('Resume','Continue')):
        label(entry);put(' php\n rep #$39\n phx\n phy\n lda.l W\n cmp #$B682');branch('bne','Fault');jump(dest)
    label('Start');put(' lda.l W+2');branch('beq','StartReady')
    put(' cmp #2');branch('beq','StartReady');put(' cmp #5');branch('bne','Fault')
    label('StartReady');clear(20);put(' lda #1\n sta.l W+2');zero(32);branch('beq','SpecialKey');query(2,1)
    label('Continue');put(' lda.l W+2\n cmp #3');branch('beq','Ack')
    put(' cmp #4');branch('bne','Fault')
    label('Ack');put(' lda.l W+8\n cmp #$B683');branch('bne','Fault')
    put(' lda.l W+10\n cmp.l W+6');branch('bne','Fault')
    put(' lda.l W+14\n cmp.l W+12');branch('bne','Fault')
    put(' lda #0\n sta.l W+8\n lda #1\n sta.l W+2\n lda.l W+4')
    for cont,dest in ((1,'BlockResult'),(2,'HpResult'),(3,'MpResult'),(4,'BombCheck'),(5,'StopRun'),(6,'AfterAnimation'),(7,'Debit')):
        put(f' cmp #{cont}');branch('beq',dest)
    jump('Fault')
    label('BlockResult');put(' lda.l W+16');branch('bne','JumpKey')
    label('SpecialKey');put(' jsr SourceSpecial_PlayerOffset');branch('bcs','Fault')
    put(f' lda.l W+136,x\n and #{KEYS["special"]}');branch('beq','JumpKey');assign(20,KEYS['special']);jump('Eligibility')
    label('JumpKey');zero(32);branch('beq','False');put(' jsr SourceSpecial_PlayerOffset');branch('bcs','Fault')
    put(f' lda.l W+136,x\n and #{KEYS["jump"]}');branch('beq','False')
    put(f' lda.l W+152,x\n and #{KEYS["attack"]}');branch('beq','False');assign(20,KEYS['jump'])
    label('Eligibility');zero(24);branch('beq','CantFire')
    put(' lda.l W+26');branch('bne','False');put(' lda.l W+24\n cmp #3');branch('bne','False')
    label('CantFire');zero(28);branch('bne','False');query(0,2)
    label('HpResult');put(' lda.l W+16');branch('bne','Eligible');query(1,3)
    label('MpResult');put(' lda.l W+16');branch('beq','False')
    label('Eligible');assign(60,17);assign(64,1);clear(68)
    for off in range(72,92,4):clear(off)
    zero(92);branch('beq','BombCheck');copy(92,176)
    for off in (96,100,104,92,108):clear(off)
    service(1,4)
    label('BombCheck');zero(44);branch('beq','StopRun');zero(48);branch('bne','StopRun');copy(44,176);service(2,5)
    label('StopRun')
    for off in (112,116,120):clear(off)
    service(3,6)
    label('AfterAnimation');zero(48);branch('beq','CostFlags');copy(184,124)
    label('CostFlags');zero(36);branch('bne','Success');zero(40);branch('bne','Success');query(1,7)
    label('Debit');zero(168);branch('beq','Fault')
    put(' lda.l W+16');branch('beq','DebitHealth')
    for name,off in (('DebitMp',52),('DebitHealth',56)):
        label(name);put(f' sec\n lda.l W+{off}\n sbc.l W+172\n sta.l W+188\n lda.l W+{off+2}\n sbc.l W+174');branch('bvs','Fault')
        put(f' sta.l W+{off+2}\n lda.l W+188\n sta.l W+{off}');jump('Success')
    label('Success');put(' jsr SourceSpecial_PlayerOffset');branch('bcs','Fault');clear(132)
    put(' lda.l W+20\n eor #$FFFF\n and.l W+136,x\n sta.l W+136,x\n lda.l W+22\n eor #$FFFF\n and.l W+138,x\n sta.l W+138,x\n lda #5');jump('Return')
    label('False');put(' lda #2');jump('Return')
    label('Pending');put(' lda #0\n sta.l W+8');put(' lda.l W+6');branch('beq','PendingQuery')
    put(' lda #4');jump('Return')
    label('PendingQuery');put(' lda #3');jump('Return')
    label('Return');put(' sta.l W+2\n ply\n plx\n plp\n clc\n rtl')
    label('Fault');put(' lda #6\n sta.l W+2\n ply\n plx\n plp\n sec\n rtl')
    label('PlayerOffset');put(' lda.l W+130');branch('bne','BadPort')
    put(' lda.l W+128\n cmp #4');branch('bcs','BadPort')
    put(' asl a\n asl a\n tax\n clc\n rts')
    label('BadPort');put(' sec\n rts')
    return '\n'.join(lines).replace('W+',str(work)+'+').replace(' W\n',' '+str(work)+'\n')+'\n'
