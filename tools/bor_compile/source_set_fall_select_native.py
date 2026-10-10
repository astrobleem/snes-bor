"""Source set_fall selection through the checked mutable animation cache."""
from compiler import key
from source_profile import document,discover
from source_animation_ids import configure
from dialect_4086 import ENGINE_COMMIT

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};st=discover(source,docs);ids=configure(docs[key(st['models_path'])]['directives'])
 return dict(schema='BYOR_SET_FALL_SELECTION_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,falls=ids['arrays']['falls'],maximum=ids['max_animations'],full_set_fall_bound=False)

def emit(work,requirements,sy,code_bank=39):
 if not 0<=work<=0x1000000-24:raise ValueError('FALL_SELECT_NATIVE_EXTENT')
 falls=requirements['falls'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('SetFallSelect_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='SetFallSelect_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl')[op]+' '+k+'\n jmp SetFallSelect_'+n+'\n'+k+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(' php\n rep #$39\n phx\n phy');put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6b6)
 put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('bne')
 label('Ready');require(work+22,0);put(f' lda.l {work}+10\n cmp #2');branch('bcs')
 put(f' lda.l {work}+4\n sta.l {sy["SourceAnimationInit4086_Slot"]}\n lda #0\n sta.l {sy["SourceAnimationInit4086_Reset"]}')
 put(f' lda.l {work}+8');branch('bne','Fallback');put(f' lda.l {work}+6\n cmp #{len(falls)}');branch('bcs','Fallback')
 put(f' sta.l {work}+20\n asl a\n tax\n lda.l SetFallSelect_Falls+{code_bank<<16},x\n sta.l {work}+12\n sta.l {work}+14\n jmp SetFallSelect_Query')
 label('Fallback');put(f' lda #0\n sta.l {work}+20\n lda #{falls[0]}\n sta.l {work}+12\n sta.l {work}+14')
 label('Query');put(f' lda.l {work}+14\n sta.l {sy["SourceAnimationInit4086_Number"]}\n jsl {sy["SourceAnimationInit4086_Resolve"]}');branch('bcs')
 put(f' lda.l {sy["SourceAnimationInit4086_Count"]}');branch('bne','Found')
 put(f' lda.l {work}+20');branch('beq','Absent');put(f' lda #0\n sta.l {work}+20\n lda #{falls[0]}\n sta.l {work}+14\n jmp SetFallSelect_Query')
 label('Absent');put(f' lda #$FFFF\n sta.l {work}+14\n lda #0\n sta.l {work}+16\n sta.l {work}+18\n jmp SetFallSelect_Done')
 label('Found');put(f' sta.l {work}+18\n lda.l {sy["SourceAnimationInit4086_Handle"]}\n sta.l {work}+16')
 label('Done');put(f' lda #2\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n lda #3\n ply\n plx\n plp\n sec\n rtl')
 label('Falls');put(' .dw '+','.join(map(str,falls)))
 return '\n'.join(lines)+'\n'


def emit_begin(work,sy):
 """Real initializer; fall preserves incoming velocity, including toss lift."""
 from source_set_pain_select_native import emit_begin as begin
 return begin(work,sy,prefix="SetFall",select="SetFallSelect_Run",magic=0xb6b6,clear_velocity=False)


def emit_frame_prefix(work,sy):
 from source_set_pain_select_native import emit_frame_prefix as frame
 return frame(work,sy,prefix="SetFall")


def emit_frame_owner(sy):
 from source_set_pain_select_native import emit_frame_owner as owner
 return owner(sy,prefix="SetFall")
