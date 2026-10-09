"""Retained source checkdeath prefix after common health.

Actual score executes. Positive death sound, item and boss children remain
explicit requirements. No world/callback acknowledgement or actor retirement.
"""
from source_current_colourmap import layout


def emit(work,sy):
 w=layout()['controls'];lines=[];serial=0;size=32
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CombatDeath_'+n+':\n.a16\n.i16')
 def jump(op,n):
  nonlocal serial
  serial+=1;g='CombatDeath_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi')[op]+f' {g}\n jmp CombatDeath_{n}\n{g}:\n.a16\n.i16')
 def guard(op):jump(op,'Bad')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');guard('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd')
 put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs')
 for op,off in(('txa',8),('tya',10)):put(f' {op}\n cmp.l {work}+{off}');guard('bne')
 for a,v in((work+64,0xb6b2),(work+66,2),(w+40,0xb6ad),(w+42,2),(sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),(sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Fault'],0),(sy['SourceSelf4086_GlobalHigh'],0x41),(sy['SourceLifecycle4086_Ready'],0xb4fb)):
  require(a,v)
 for a,b in((w+48,work+4),(w+46,work+6),(w+8,work+8),(w+10,work+10),(w+12,sy['SourceWorldTick4086_TimeLo']),(w+14,sy['SourceWorldTick4086_TimeHi'])):put(f' lda.l {a}\n cmp.l {b}');guard('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}');guard('beq');put(' cmp #129');guard('bcs')
 put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs');put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $02\n asl a\n asl a\n sta $04\n clc\n adc $02\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');guard('bne');put(f' cmp.l {sy["SourceSelf4086_GlobalLow"]}');guard('bne');require('$414002,x',0x41)
 for off,v in((32,1),(34,0)):require(f'$414000+{off},x',v)
 put(f' lda.l {w}+44\n cmp #5');guard('bcc');put(' cmp #11');guard('bcs');put(' sta $06\n cmp #10');jump('beq','Good')
 put(' lda.l $414026,x');jump('bmi','Death');jump('bne','Complete');put(' lda.l $414024,x');jump('bne','Complete')
 label('Death');require(sy['SourceDeathFields4086_Ready'],0xb638);require(sy['SourceCtorState4086_Ready'],0xb5c2);put(' lda $04\n tax');require('$40903A,x',0xb638);put(' lda.l $409038,x\n cmp.l $416800,x');guard('bne');put(' lda $04\n tax\n lda.l $416800,x\n sta $10\n lda $02\n tax');require('$43904A,x',0xb4fb);put(' lda.l $439048,x\n cmp $10');guard('bne')
 put(' lda $04\n tax');require('$43383E,x',0xb5c2)
 put(' lda $06\n cmp #5');jump('bne','Score')
 put(' lda $02\n tax\n lda #1\n sta.l $439014,x\n lda #0\n sta.l $439016,x');put(f' lda #6\n sta.l {w}+44\n sta $06')
 label('Score');put(' lda $06\n cmp #6');jump('bne','Flags')
 put(' lda $04\n tax\n lda.l $40900C,x\n sta $08\n lda.l $40900E,x\n sta $0A\n ora $08');jump('beq','ScoreDone');put(' lda $0A\n cmp #$41');guard('bne')
 put(' lda $08\n sec\n sbc #$4000');guard('bcc');put(' ldx #0');label('Decode');put(' cmp #80');jump('bcc','Decoded');put(' sec\n sbc #80\n inx\n cpx #128');guard('bcs');put(' jmp CombatDeath_Decode')
 label('Decoded');put(' cmp #0');guard('bne');put(f' txa\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs');put(' sta $0C\n lda $08\n tax\n cmp.l $410000,x');guard('bne');require('$410002,x',0x41)
 put(' lda $0C\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $0E\n asl a\n clc\n adc $0E\n tax\n lda.l $40C048,x\n and #1');jump('beq','ScoreDone')
 put(' lda $08\n tax');require('$410028,x',1);require('$41002A,x',0)
 for a,v in((sy['SourceScore4086_Ready'],0xb631),(sy['SourceScore4086_StatsReady'],0xb633),(sy['SourceScore4086_NoScriptsReady'],0xb632),(sy['SourceScore4086_ScriptMask'],0)):
  require(a,v)
 # A required score child owns its retained controls. Retrying checkdeath must
 # neither restart addscore nor duplicate already accepted extra lives.
 put(f' lda.l {work}+94\n cmp #1');jump('bne','ScoreStart')
 for off in(0,2):put(f' lda.l $41002C+{off},x\n cmp.l {sy["SourceScore4086_Index"]}+{off}');guard('bne')
 put(' lda $02\n tax')
 for off in(0,2):put(f' lda.l $414048+{off},x\n cmp.l {sy["SourceScore4086_Add"]}+{off}');guard('bne')
 put(f' lda.l {sy["SourceScore4086_Status"]}');jump('beq','ScoreDone');put(' cmp #3');guard('bcs');put(' jmp CombatDeath_Required')
 label('ScoreStart');put(' lda $08\n tax')
 for off in(0,2):put(f' lda.l $41002C+{off},x\n sta.l {sy["SourceScore4086_Index"]}+{off}')
 put(' lda $02\n tax')
 for off in(0,2):put(f' lda.l $414048+{off},x\n sta.l {sy["SourceScore4086_Add"]}+{off}')
 put(f' jsl {sy["SourceScore4086_Execute"]}');guard('bcs');put(f' lda.l {sy["SourceScore4086_Status"]}');jump('bne','Required')
 label('ScoreDone');put(f' lda #7\n sta.l {w}+44\n sta $06')
 label('Flags');put(' lda $06\n cmp #7');jump('bne','Sound')
 put(' lda $02\n tax\n lda #1\n sta.l $439010,x\n lda #0\n sta.l $439012,x\n lda $00\n asl a\n asl a\n asl a\n asl a\n asl a\n tax\n lda #0\n sta.l $43EB00,x\n sta.l $43EB02,x');put(f' lda #8\n sta.l {w}+44\n sta $06')
 label('Sound');put(' lda $06\n cmp #8');jump('bne','Item');put(' lda $02\n tax\n lda.l $41404E,x');jump('bpl','Required');put(f' lda #9\n sta.l {w}+44\n sta $06')
 label('Item');put(' lda $06\n cmp #9');jump('bne','Boss');put(' lda $04\n tax\n lda.l $40903C,x\n ora.l $40903E,x');jump('bne','Required')
 # A zero cached item-model index is a source no-op; otherwise count/drop is required.
 label('Boss');put(' lda $04\n tax\n lda.l $433838,x\n ora.l $43383A,x');jump('bne','Required')
 label('Complete');put(f' lda #10\n sta.l {w}+44')
 for n,status,carry in(('Good',0,'clc'),('Required',1,'clc'),('Bad',3,'sec')):
  label(n);put(f' lda #{status}\n sta.l {work}+94\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
 return '\n'.join(lines)+'\n'
