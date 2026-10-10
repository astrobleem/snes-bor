"""Checked player_die recovery snapshot from current global self.

A is the original player index captured before the pdie script. The source
reads current global self afterward, so it may identify a different slot.
This leaf only binds the two recovery fields, not the whole death continuation.
"""
from source_player_global_layout import layout


def emit_recovery_snapshot(tail,sy):
    plan=layout(tail);base=plan['player_base'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerDieSnapshot_'+n+':\n.a16\n.i16')
    def guard(op,n='Bad'):
        nonlocal serial
        serial+=1;g='PlayerDieSnapshot_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+g+'\n jmp PlayerDieSnapshot_'+n+'\n'+g+':\n.a16\n.i16')
    def require(at,value):put(f' lda.l {at}\n cmp #{value}');guard('bne')
    label('Run');put(' php\n rep #$39\n pha\n phx\n phy\n phd\n tsc\n sec\n sbc #16\n tcs\n inc a\n tcd\n lda 23,s\n cmp #4');guard('bcs');put(' sta $00')
    put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs')
    put(' jsl PlayerGlobal_Check');guard('bcs')
    for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),
                 (sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),
                 (sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),
                 (sy['SourceWorldTick4086_Fault'],0),(sy['SourceSelf4086_Ready'],0xb4f6),
                 (sy['SourceSelf4086_Active'],0),(sy['SourceSelf4086_Fault'],0),
                 (sy['SourceSelf4086_GlobalHigh'],0x41),(sy['SourceModelEntityCopy4086_Ready'],0xb4eb)):
        require(at,v)
    for off in (0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');guard('bne')
    put(f' lda.l {sy["VmSourceWorld_Count"]}');guard('beq');put(' cmp #129');guard('bcs')
    put(f' cmp.l {sy["SourceModelEntityCopy4086_Entities"]}');guard('bne')
    put(f' lda.l {sy["SourceSelf4086_GlobalLow"]}\n sec\n sbc #$4000');guard('bcc');put(' sta $02\n ldx #0')
    label('FindSlot');put(' cmp #80');guard('bcc','SlotFound');put(' sec\n sbc #80\n inx');put(f' sta $06\n txa\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs');put(' lda $06\n jmp PlayerDieSnapshot_FindSlot')
    label('SlotFound');put(' cmp #0');guard('bne');put(f' txa\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs')
    put(' txa\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $04\n asl a\n clc\n adc $04\n sta $04\n ldx $02')
    put(f' lda.l $414000,x\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');guard('bne');require('$414002,x',0x41)
    put(' ldx $04')
    for offset,temp in ((60,8),(62,10),(64,12),(66,14)):put(f' lda.l $40C000+{offset},x\n sta ${temp:02X}')
    put(' lda $00\n asl a\n asl a\n sta $06\n asl a\n asl a\n clc\n adc $06\n tax')
    for offset,temp in ((8,8),(10,10),(12,12),(14,14)):put(f' lda ${temp:02X}\n sta.l {base+offset},x')
    put(' jmp PlayerDieSnapshot_Good')
    for name,carry in (('Good','clc'),('Bad','sec')):
        label(name);put(' tsc\n clc\n adc #16\n tcs\n pld\n ply\n plx\n pla\n plp\n '+carry+'\n rtl')
    return '\n'.join(lines)+'\n'
