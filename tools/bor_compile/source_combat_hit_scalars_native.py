"""Nonself source MP/hit-score predecessor for zero model multipliers.

An explicit capability covers absent score scripts and magic_type != 1.
Rumble has a declared SNES controller adaptation; extra-life/death scoring
is separate and is not certified by this zero-add hit score service.
"""
import hashlib,subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_model_core_4086 import derive as core
from source_score_inputs_4086 import derive as globals_inputs
from source_current_colourmap import layout


def derive(source):
 c=core(source);g=globals_inputs(source)
 if any(m['fields']['multiple'] for m in c['models']):raise ValueError('HIT_SCORE_MULTIPLICATION_REQUIRED')
 if not g['absent_score_scripts_capability']:raise ValueError('HIT_SCORE_SCRIPT_REQUIRED')
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 return dict(schema='BYOR_COMBAT_HIT_SCALARS_REQUIREMENTS_V1',capability='NONSELF_ZERO_HIT_MULTIPLIER',models=c['models'],globals=g,engine_commit=ENGINE_COMMIT,source_hashes={n:hashlib.sha256(extract(raw,n).encode('latin1')).hexdigest() for n in ('checkhitscore','checkmpadd')},rumble_policy='ACCEPTED_COMPAT_NO_SNES_CONTROLLER_RUMBLE',full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def emit(req,work,sy):
 if req['capability']!='NONSELF_ZERO_HIT_MULTIPLIER':raise ValueError('HIT_SCALAR_CAPABILITY')
 w=layout()['controls'];lines=[];serial=0;size=24
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CombatHitScalars_'+n+':\n.a16\n.i16')
 def guard(op):
  nonlocal serial
  serial+=1;g='CombatHitScalars_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {g}\n jmp CombatHitScalars_Bad\n{g}:\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');guard('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd')
 put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs')
 for op,off in(('txa',8),('tya',10)):put(f' {op}\n cmp.l {work}+{off}');guard('bne')
 for a,v in((work+60,0xb6b3),(work+62,0),(work+64,0xb6b2),(work+66,2),(work+88,0xb6b4),(work+92,0),(w+40,0xb6ad),(w+42,2),(sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),(sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Fault'],0),(sy['SourceSelf4086_GlobalHigh'],0x41)):
  require(a,v)
 for a,b in((w+48,work+4),(w+46,work+6),(w+8,work+8),(w+10,work+10),(w+12,sy['SourceWorldTick4086_TimeLo']),(w+14,sy['SourceWorldTick4086_TimeHi'])):put(f' lda.l {a}\n cmp.l {b}');guard('bne')
 put(f' lda.l {work}+84\n cmp #1\n bne CombatHitScalars_MagicOk\n lda.l {work}+86');guard('beq');label('MagicOk')
 put(f' lda.l {work}+4\n cmp.l {work}+6');guard('beq')
 put(f' cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs')
 put(f' asl a\n asl a\n asl a\n asl a\n sta $00\n asl a\n asl a\n clc\n adc $00\n sta $02\n tax\n clc\n adc #$4000\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');guard('bne')
 put(' cmp.l $414000,x');guard('bne');require('$414002,x',0x41)
 put(f' lda.l {work}+4\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $00\n asl a\n clc\n adc $00\n tax\n lda.l $40C000,x\n ora.l $40C002,x');guard('bne')
 put(f' lda.l {work}+4\n asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n tax');require('$40903A,x',0xb638)
 put(' lda.l $40900C,x\n sta $04\n lda.l $40900E,x\n sta $06\n ora $04\n bne CombatHitScalars_HasOpponent\n jmp CombatHitScalars_NoOpponent\nCombatHitScalars_HasOpponent:\n.a16\n.i16')
 put(' lda $06\n cmp #$41');guard('bne')
 # Exact token division; no pointer rounding or raw pool indexing.
 put(' lda $04\n sec\n sbc #$4000');guard('bcc');put(' ldx #0')
 label('Decode');put(' cmp #80\n bcc CombatHitScalars_Decoded\n sec\n sbc #80\n inx\n cpx #128');guard('bcs');put(' jmp CombatHitScalars_Decode')
 label('Decoded');put(' cmp #0');guard('bne');put(f' txa\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs');put(' sta $08\n lda $04\n tax\n cmp.l $410000,x');guard('bne');require('$410002,x',0x41)
 put(' lda $08\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $00\n asl a\n clc\n adc $00\n tax\n lda.l $40C048,x\n and #1\n sta $0A')
 put(f' lda $08\n cmp.l {work}+4\n beq CombatHitScalars_NoOpponent\n lda $0A\n beq CombatHitScalars_NoOpponent')
 put(' lda $08\n asl a\n asl a\n asl a\n asl a\n sta $00\n asl a\n asl a\n clc\n adc $00\n tax');require('$414028,x',1);require('$41402A,x',0)
 put(' lda.l $41402C,x\n sta $0C\n lda.l $41402E,x\n sta $0E\n lda #1\n sta $10\n jmp CombatHitScalars_Cursor')
 label('NoOpponent');put(' lda #0\n sta $10')
 label('Cursor');put(f' lda.l {w}+44\n cmp #4\n bne CombatHitScalars_NewCursor\n jmp CombatHitScalars_Good\nCombatHitScalars_NewCursor:\n.a16\n.i16\n cmp #2');guard('bne')
 put(' lda $10\n beq CombatHitScalars_Commit')
 for a,v in((sy['SourceScore4086_Ready'],0xb631),(sy['SourceScore4086_StatsReady'],0xb633),(sy['SourceScore4086_NoScriptsReady'],0xb632),(sy['SourceScore4086_ScriptMask'],0)):
  require(a,v)
 for off in(0,2):require(sy['SourceScore4086_LifeScore']+off,(req['globals']['lifescore']>>(off*8))&65535)
 for off in(0,2):put(f' lda ${12+off:02X}\n sta.l {sy["SourceScore4086_Index"]}+{off}\n lda #0\n sta.l {sy["SourceScore4086_Add"]}+{off}')
 put(f' jsl {sy["SourceScore4086_Execute"]}');guard('bcs');require(sy['SourceScore4086_Status'],0)
 label('Commit');put(f' lda #4\n sta.l {w}+44')
 for n,status,carry in(('Good',2,'clc'),('Bad',3,'sec')):
  label(n);put(f' lda #{status}\n sta.l {work}+90\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
 return '\n'.join(lines)+'\n'
