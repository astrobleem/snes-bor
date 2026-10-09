"""Canonical pre-attack button queries joined to the real special service.

Alternate actions are absent by compiler capability; grounded BLOCK presence
requires a real entry/action owner. No unsupported branch mutates the actor.
"""
from source_player_run_4086 import KEYS

def emit(work,directional,special,binding,services,history,input_owner,input_magic,profile,roles,symbols):
    spans=((work,48),(directional,64),(special,192),(binding,64),(services,32),(history,1024),(input_owner,2))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_BUTTON_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_BUTTON_OVERLAP')
    if profile.get('capability')!='READONLY_ABSENT_ALTERNATE_BUTTON_ACTIONS':raise ValueError('PLAYER_BUTTON_CAPABILITY')
    if history&255 or not 1<=input_magic<=65535:raise ValueError('PLAYER_BUTTON_INPUT')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerButton_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerButton_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerButton_'+n+'\n'+skip+':\n.a16\n.i16')
    def resolve(role):
        put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{roles[role]}\n sta.l {symbols["SourceAnimationInit4086_Number"]}')
        label('Query_'+role);put(f' jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
    def absent(role):
        resolve(role);put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Absent'+role)
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('bne');label('Absent'+role)
    def input_key(mask,target):
        put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+224,x\n and #{mask}');branch('beq',target)
    label('Begin');put(' php\n rep #$39\n phx\n phy')
    for address,magic in ((work,0xb68d),(input_owner,input_magic),(directional,0xb68c)):
        put(f' lda.l {address}\n cmp #{magic}');branch('bne')
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('beq','Ready');put(' cmp #4');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2\n lda.l {directional}+2\n cmp #2');branch('bne')
    put(f' lda.l {work}+4\n cmp.l {directional}+4');branch('bne')
    put(f' lda.l {work}+6\n cmp #4');branch('bcs');put(f' cmp.l {directional}+6');branch('bne')
    put(f' lda.l {directional}+8\n sta.l {work}+8\n lda.l {special}+32\n ora.l {special}+34');branch('bne','Charge')
    input_key(KEYS['jump'],'Charge');absent('attackboth')
    label('Charge');input_key(KEYS['jump'],'SpecialKey');absent('charge')
    label('SpecialKey');input_key(KEYS['special'],'CheckSpecial');absent('special2');resolve('block')
    put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','CheckSpecial')
    put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq','CheckSpecial')
    put(f' lda.l {work}+8');branch('bne')
    label('CheckSpecial');put(f' lda.l {work}+8');branch('beq','Continue')
    put(f' lda.l {work}+4\n sta.l {binding}+4\n jsl SpecialServices_Begin');branch('bcs');put(' jmp PlayerButton_SpecialResult')
    label('FinishFrame');put(' php\n rep #$39\n phx\n phy')
    put(f' lda.l {work}\n cmp #$B68D');branch('bne')
    put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {work}+4\n cmp.l {binding}+4');branch('bne')
    put(' jsl SpecialServices_FinishFrame');branch('bcs')
    label('SpecialResult');put(f' lda.l {services}+2\n cmp #3');branch('beq','Pending');put(' cmp #4');branch('beq','Return');put(' cmp #2');branch('bne')
    label('Continue');put(f' lda #2\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Return');put(f' lda #4\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Pending');put(f' lda #3\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
