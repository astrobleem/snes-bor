"""set_rise mutations after real ent_set_anim; global self remains distinct."""
from source_engine_function_ids import function_id
from source_hit_contact_layout import layout as contact_layout
from source_hit_state_layout import layout as identity_layout
from source_recovery_state_layout import layout as recovery_layout

def emit(work,req,sy):
 if not req['source_zero_juggle_max']:raise ValueError('SET_RISE_LIVE_JUGGLE_MAX_OWNER_REQUIRED')
 models=req['models'];cp=contact_layout();hp=identity_layout();capacity=recovery_layout()['chr_capacity'];h=hp['controls'];c=cp['controls'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('SetRiseFlags_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;l='SetRiseFlags_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp SetRiseFlags_'+n+'\n'+l+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 def offset(stride,dst):
  put(' lda $00\n asl a\n asl a')
  if stride in (8,16,64):
   for _ in range(stride.bit_length()-3):put(' asl a')
  elif stride in (20,24,80):
   shift={20:0,24:1,80:2}[stride]
   for _ in range(shift):put(' asl a')
   put(' sta $0E')
   for _ in range(1 if stride==24 else 2):put(' asl a')
   put(' clc\n adc $0E')
  else:raise ValueError('SET_RISE_FLAGS_STRIDE')
  put(f' sta ${dst:02X}')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #32\n tcs\n inc a\n tcd\n stx $14\n sty $16\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6c3)
 put(f' lda.l {work}+2\n cmp #6');branch('beq','Validate');put(' cmp #5');branch('bne')
 label('Validate')
 for at,v in ((sy['SourceAnimationInit4086_State'],2),(sy['SourceUpdateFrame4086_State'],2),(sy['SourceUpdateFrame4086_Pending'],0),(sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Active'],0),(sy['SourcePhysicsState4086_Ready'],0xb61c),(sy['SourceDamageEffectsState4086_Ready'],0xb62f),(sy['SourceLifecycle4086_Ready'],0xb4fb),(sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800)):require(at,v)
 for src,dst in ((sy['SourceAnimationInit4086_Slot'],work+4),(sy['SourceAnimationInit4086_Number'],work+14),(sy['SourceAnimationInit4086_Handle'],work+16),(sy['SourceAnimationInit4086_Count'],work+18)):
  put(f' lda.l {src}\n cmp.l {dst}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00')
 for stride,dst in ((80,2),(64,4),(16,6),(20,8),(24,10),(8,24),(16,26)):offset(stride,dst)
 put(' ldx $02');require('$43904A,x',0xb4fb);put(' lda.l $439048,x\n ldx $04\n cmp.l $416800,x');branch('bne');put(f' cmp #{len(models)}');branch('bcs');put(' sta $1C\n ldx $0A');require('$7EF114,x',0xb62f);put(' lda.l $7EF116,x\n cmp $1C');branch('bne');put(' ldx $08');require('$437E10,x',0xb5fb);require('$437E12,x',0)
 for at,v in ((h,0xb6a0),(h+16,hp['base']&65535),(h+18,0x42),(h+22,128),(c,0xb6a3),(c+16,cp['base']&65535),(c+18,0x42),(c+22,128)):require(at,v)
 for owner in (h,c):
  put(f' lda.l {owner}+20');branch('beq');put(f' cmp #{capacity+1}');branch('bcs')
  for off,dst in ((8,20),(10,22)):put(f' lda.l {owner}+{off}\n cmp ${dst:02X}');branch('bne')
 put(' ldx $1A');require(f'{hp["base"]}+12,x',0xb6a1);put(f' lda.l {hp["base"]}+14,x\n cmp $00');branch('bne')
 for off,dst in ((8,20),(10,22)):put(f' lda.l {hp["base"]}+{off},x\n cmp ${dst:02X}');branch('bne')
 # Resolve the original global self without replacing it with iRise. Pointer
 # arithmetic is bounded by the actual published pool count and exact stride.
 require(sy['SourceSelf4086_GlobalLow']+2,0x41);put(f' lda.l {sy["SourceSelf4086_GlobalLow"]}\n cmp #$4000');branch('bcc');put(' sec\n sbc #$4000\n sta $10\n lda #0\n sta $12')
 label('SelfSlot');put(' lda $10\n cmp #80');branch('bcc','SelfFound');put(' sec\n sbc #80\n sta $10\n inc $12\n lda $12');put(f' cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' jmp SetRiseFlags_SelfSlot')
 label('SelfFound');put(' lda $10');branch('bne');put(' lda $12');put(f' cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $0C')
 put(f' lda.l {work}+2\n cmp #6');branch('beq','Good')
 # Exact source order: action, drop, falling, projectile, nograb, target X,
 # global self Z/Y, and model juggle current.
 put(f' ldx $02\n lda #{function_id("common_rise")}\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n ldx $08\n sta.l $437E00,x\n sta.l $437E02,x\n ldx $06\n sta.l $42D800,x\n sta.l $42D802,x\n ldx $0A\n sta.l $7EF100,x\n sta.l $7EF102,x\n ldx $02\n sta.l $439010,x\n sta.l $439012,x\n ldx $04\n sta.l $416824,x\n sta.l $416826,x\n ldx $0C\n sta.l $416828,x\n sta.l $41682A,x\n sta.l $41682C,x\n sta.l $41682E,x\n ldx $18\n sta.l {cp["base"]}+4,x\n sta.l {cp["base"]}+6,x\n lda #6\n sta.l {work}+2')
 label('Good');put(' tsc\n clc\n adc #32\n tcs\n pld\n lda #1\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #32\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
