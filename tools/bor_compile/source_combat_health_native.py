"""Exact integer health service for unit factors and absent damage scripts.

The caller supplies the already selected attack after player cheat handling.
This service neither checks death nor completes a damage callback.
"""
import hashlib,subprocess
from dialect_4086 import ENGINE_COMMIT
from source_model_factors import derive as factors
from source_damage_inputs_4086 import derive as damage
from source_script_clone import derive as scripts
from script_nested_authority import extract


def derive(source):
 f=factors(source);d=damage(source);s=scripts(source)
 if any(m['defense'][0]!=1 or m['offense']!=1 for m in f['models']):raise ValueError('COMBAT_HEALTH_NONUNIT_FACTORS_REQUIRED')
 if any(m['fields']['guardpoints']for m in d['models']):raise ValueError('COMBAT_HEALTH_GUARDBREAK_REQUIRED')
 if [(m['id'],m['identity'],m['source_sha256'])for m in f['models']]!=[(m['id'],m['identity'],m['source_sha256'])for m in d['models']]:raise ValueError('COMBAT_HEALTH_SOURCE_PAIR')
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 return dict(schema='BYOR_COMBAT_HEALTH_REQUIREMENTS_V1',capability='UNIT_FACTORS_ABSENT_DAMAGE_SCRIPTS',models=f['models'],scripts=s,engine_commit=ENGINE_COMMIT,checkdamage_sha256=hashlib.sha256(extract(raw,'checkdamage').encode('latin1')).hexdigest(),force_domain=[-8388608,8388607],signed_subtraction_overflow_admitted=False,pit_height_policy='ACCEPTED_COMPAT_Q16_16',full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def emit(req,work,sy):
 if req['capability']!='UNIT_FACTORS_ABSENT_DAMAGE_SCRIPTS':raise ValueError('COMBAT_HEALTH_CAPABILITY')
 count=len(req['models']);lines=[];serial=0;size=48
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CombatHealth_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;g='CombatHealth_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi',bvs='bvc')[op]+f' {g}\n jmp CombatHealth_{n}\n{g}:\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');branch('bne')
 def offset(src,stride,dst):
  put(f' lda ${src:02X}\n asl a\n asl a')
  if stride==80:put(' asl a\n asl a\n sta $28\n asl a\n asl a\n clc\n adc $28')
  elif stride==64:put(' asl a\n asl a\n asl a\n asl a')
  elif stride==32:put(' asl a\n asl a\n asl a')
  else:raise ValueError('COMBAT_HEALTH_OFFSET')
  put(f' sta ${dst:02X}')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd')
 put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6b0)
 for op,off in(('txa',8),('tya',10)):put(f' {op}\n cmp.l {work}+{off}');branch('bne')
 for at,v in((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),(sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Fault'],0),(sy['SourceSelf4086_GlobalHigh'],0x41),(sy['SourceFactors4086_Ready'],0xb5f1),(sy['SourceFactors4086_Models'],count),(sy['SourceScriptClone4086_Ready'],0xb5c1)):
  require(at,v)
 for off in(0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}');branch('beq');put(' cmp #129');branch('bcs')
 for src,off in((0,4),(2,6)):
  put(f' lda.l {work}+{off}\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(f' sta ${src:02X}')
  offset(src,80,4);put(' tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41)
  offset(src,64,6);put(f' tax\n lda.l $416800,x\n cmp #{count}');branch('bcs');put(' sta $10')
  put(f' lda ${src:02X}\n asl a\n asl a\n tax\n lda.l $43B902,x\n cmp #$B5F1');branch('bne');put(' lda.l $43B900,x\n cmp $10');branch('bne')
  offset(src,32,6);put(' tax');factor=0 if src==0 else 28
  require(f'$432800+{factor},x',0);require(f'$432802+{factor},x',0x3f80)
 offset(0,80,4);put(f' lda $04\n clc\n adc #$4000\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');branch('bne');put(' lda $04\n tax')
 for off,v in((32,1),(34,0),(64,1),(66,0),(8,2),(10,0)):require(f'$414000+{off},x',v)
 for src,dst in((36,12),(68,16),(12,20)):
  for off in(0,2):put(f' lda.l $414000+{src+off},x\n sta ${dst+off:02X}')
 offset(0,64,6);put(' tax')
 put(' lda.l $40902C,x\n cmp #2');branch('bcs')
 for off in(46,48,50,52,54):require(f'$409000+{off},x',0)
 # Animation-only initialized mask is allowed; all other script slots absent.
 # +44 can hold that animation bit and does not describe damage callbacks.
 # The immutable B5SC compiler rejects all non-animation script declarations.
 for off in(0,2):put(f' lda.l $416810+{off},x\n sta ${24+off:02X}')
 require(sy['SourceLifecycle4086_Ready'],0xb4fb)
 offset(0,64,6);put(' tax\n lda.l $416800,x\n sta $2C')
 offset(0,80,6);put(' tax');require('$43904A,x',0xb4fb);put(' lda.l $439048,x\n cmp $2C');branch('bne')
 put(' lda.l $439018,x\n sta $24\n lda.l $43901A,x\n sta $26')
 put(f' lda.l {work}+14\n clc\n adc #$80\n cmp #$100');branch('bcs')
 offset(0,80,4);put(f' tax\n lda $0C\n sec\n sbc.l {work}+12\n sta $1C\n lda $0E\n sbc.l {work}+14\n sta $1E');branch('bvs')
 # Signed full-width cap against the actual entity model maximum.
 put(' lda $1E\n eor #$8000\n sta $2A\n lda $12\n eor #$8000\n cmp $2A');branch('bcc','Cap');branch('bne','NoCap');put(' lda $10\n cmp $1C');branch('bcc','Cap');put(' jmp CombatHealth_NoCap')
 label('Cap');put(' lda $10\n sta $1C\n lda $12\n sta $1E')
 label('NoCap');put(' lda $1E');branch('bmi','Nonpositive');branch('bne','Commit');put(' lda $1C');branch('bne','Commit')
 label('Nonpositive');put(f' lda.l {work}+16\n ora.l {work}+18');branch('beq','Invincible');put(' lda #1\n sta $1C\n stz $1E\n jmp CombatHealth_Commit')
 label('Invincible');put(' lda $1A');branch('bmi','Commit')
 # Source PIT_DEPTH=-250, represented exactly in Q16.16.
 put(' lda $16\n eor #$8000\n cmp #$7F06');branch('bcc','Commit');put(' lda $26');branch('bne','Commit');put(' lda $24\n cmp #2');branch('beq','One');put(' cmp #3');branch('bne','Commit');put(' lda $10\n sta $1C\n lda $12\n sta $1E\n jmp CombatHealth_Commit')
 label('One');put(' lda #1\n sta $1C\n stz $1E')
 label('Commit');offset(0,80,4);put(' tax\n lda $1C\n sta.l $414024,x\n lda $1E\n sta.l $414026,x')
 for name,status,carry in(('Good',2,'clc'),('Bad',3,'sec')):
  label(name);put(f' lda #{status}\n sta.l {work}+2\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
 return '\n'.join(lines)+'\n'
