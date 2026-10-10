"""Generic check_ai bridge for compiled pain/fall/grabbed/block/land owners.

One existing common-idle control region is borrowed only while a source action
is outstanding. Real child tickets remain visible; no frame/sound ack is made.
"""
import re
from source_engine_function_ids import function_id

ACTIONS=(('common_fall','CommonFallFrame_Run',0xb6bb),('common_pain','CommonPainFrame_Run',0xb6b8),('common_grabbed','CommonGrabbedFrame_Run',0xb6b9),('common_block','CommonBlockFrame_Run',0xb6ba),('common_land','CommonLandFrame_Run',0xb6bd))


def emit(work,sy,*,actions=ACTIONS,fallback_dispatch=None,fallback_continue=None):
 if not 0<=work<=0x1000000-24 or not actions:raise ValueError('COMMON_AI_ACTION_LAYOUT')
 supported={n:(entry,tag)for n,entry,tag in ACTIONS};seen=set()
 for name,entry,tag in actions:
  if name not in supported or tag!=supported[name][1]or not re.fullmatch(r'[A-Za-z_]\w*',entry)or name in seen:raise ValueError('COMMON_AI_ACTION_CAPABILITY')
  seen.add(name)
 for target in(fallback_dispatch,fallback_continue):
  if target is not None and not(isinstance(target,int)and 0<=target<=0xffffff or isinstance(target,str)and re.fullmatch(r'[A-Za-z_]\w*',target)):raise ValueError('COMMON_AI_FALLBACK')
 state=sy['SourceAIRun4086_State'];pending=sy['SourceAIRun4086_PendingKind'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonAIRun_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='CommonAIRun_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp CommonAIRun_'+n+'\n'+k+':\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');branch('bne')
 def prologue():put(' php\n rep #$39\n phx\n phy');require(sy['SourceAIRun4086_Ready'],0xb5e6)
 label('Begin');prologue();put(f' lda.l {state}');branch('beq','BeginReady');put(' cmp #2');branch('bne')
 label('BeginReady');put(f' jsl {sy["SourceAI4086_Begin"]}');branch('bcs');put(' jmp CommonAIRun_Dispatch')
 label('Continue');prologue();require(state,1);put(f' lda.l {pending}')
 for name,entry,tag in actions:put(f' cmp #{0x0600|function_id(name)}');branch('beq','Resume_'+name)
 put(f' jml {fallback_continue if fallback_continue is not None else sy["SourceAIRun4086_Far10"]}')
 label('Dispatch');put(' pha');put(f' lda.l {sy["SourceAI4086_State"]}\n cmp #1');branch('bne','Fallback');put(f' lda.l {sy["SourceAI4086_Callback"]}+2');branch('bne','Fallback');put(f' lda.l {sy["SourceAI4086_Callback"]}')
 for name,entry,tag in actions:put(f' cmp #{function_id(name)}');branch('beq','Begin_'+name)
 label('Fallback');put(f' pla\n jml {fallback_dispatch if fallback_dispatch is not None else sy["SourceAIRun4086_Dispatch"]}')
 for name,entry,tag in actions:
  label('Begin_'+name);put(' pla');require(work,0xb680);put(f' lda.l {work}+2');branch('beq','Capture_'+name);put(' cmp #2');branch('bne')
  label('Capture_'+name);put(f' lda #{tag}\n sta.l {work}\n lda #0')
  for off in(2,6,12,14,20,22):put(f' sta.l {work}+{off}')
  put(f' lda.l {sy["SourceAI4086_Slot"]}\n sta.l {work}+4')
  for off in(0,2):put(f' lda.l {sy["SourceForeignWork_Generation"]}+{off}\n sta.l {work}+{8+off}\n lda.l {sy["VmSourceWorld_Time"]}+{off}\n sta.l {work}+{16+off}')
  put(f' lda #{0x0600|function_id(name)}\n sta.l {pending}\n jmp CommonAIRun_Run_'+name)
  label('Resume_'+name);require(sy['SourceAI4086_State'],1);require(sy['SourceAI4086_Callback'],function_id(name));require(sy['SourceAI4086_Callback']+2,0)
  # The real frame owner can still be active during a child ticket. The
  # ordinary AI CheckOwner requires frame/self idle, so validate this captured
  # world-action lease directly before entering the retained frame owner.
  for at,v in ((sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],6),(sy['SourceWorldTick4086_Pending'],1)):require(at,v)
  put(f' lda.l {sy["SourceWorldTick4086_Slot"]}\n cmp.l {sy["SourceAI4086_Slot"]}');branch('bne')
  for off in(0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {work}+{16+off}');branch('bne')
  put(f' lda.l {work}+4\n cmp.l {sy["SourceAI4086_Slot"]}');branch('bne')
  label('Run_'+name);put(f' lda.l {work}+8\n tax\n lda.l {work}+10\n tay\n jsl {entry}');branch('bcs');put(' cmp #0');branch('beq','ActionComplete')
  # A is the actual source-frame service ticket, including VM yield $8001.
  put(f' pha\n lda #1\n sta.l {state}\n pla\n jmp CommonAIRun_Exit')
 label('ActionComplete');put(' lda #0')
 for off in range(2,24,2):put(f' sta.l {work}+{off}')
 put(f' lda #$B680\n sta.l {work}\n lda #0\n sta.l {pending}\n lda #1\n jsl {sy["SourceAI4086_Continue"]}');branch('bcs');put(' jmp CommonAIRun_Dispatch')
 label('Exit');put(' ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #3\n sta.l {state}\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
