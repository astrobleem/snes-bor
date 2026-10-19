"""Exact pending-jump storage; caller must own the reduced CHR workspace.

The emitter checks actor/model identity and its supplied lifetime generation.
It does not publish a production graphics lease or run tryjump/dojump.
"""


def emit(plan,work,symbols):
    base=plan['base'];end=plan['end'];count=plan['entities']
    rehosted=plan.get('storage_profile')=='RETIRED_SCENE_VIDEO_STAGING'
    if rehosted:
        from source_pending_jump_layout import rehost
        if plan!=rehost(count,base):raise ValueError('PENDING_JUMP_NATIVE_REHOST_PLAN')
    elif plan['stride']!=24 or end!=0x42d800 or base!=end-count*24 or not 1<=count<=128:raise ValueError('PENDING_JUMP_NATIVE_PLAN')
    if not 0<=work<=0xffffff-63 or work<end and base<work+64:raise ValueError('PENDING_JUMP_NATIVE_CONTROLS')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PendingJump_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PendingJump_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PendingJump_'+n+'\n'+skip+':\n.a16\n.i16')
    def entry(n):
        label(n);put(f' php\n rep #$39\n pha\n phx\n phy\n lda #{1 if n=="ClearBirth"else 0}\n sta.l {work}+30\n jsr PendingJump_Bind');branch('bcs')
    def row():put(f' lda.l {work}+28\n tax')
    def snapshot():
        row();put(f' lda.l {work}+6\n inc a\n sta.l {base}+16,x\n lda #$B691\n sta.l {base}+18,x\n lda.l {work}+8\n sta.l {base}+20,x\n lda.l {work}+10\n sta.l {base}+22,x')
    def live(check_model=True):
        row();put(f' lda.l {base}+18,x\n cmp #$B691');branch('bne')
        put(f' lda.l {base}+20,x\n cmp.l {work}+8');branch('bne')
        put(f' lda.l {base}+22,x\n cmp.l {work}+10');branch('bne')
        if check_model:
            put(f' lda.l {work}+6\n inc a\n cmp.l {base}+16,x');branch('bne')
        else:
            put(f' lda.l {base}+16,x');branch('beq');put(' dec a')
            put(f' cmp.l {work}+22');branch('bcs')
    entry('ClearBirth');row();put(' lda #0')
    for at in range(0,16,2):put(f' sta.l {base}+{at},x')
    snapshot();put(' jmp PendingJump_Good')
    entry('CopyModel');live(False);snapshot();put(' jmp PendingJump_Good')
    entry('Read');live()
    for at in range(0,16,2):put(f' lda.l {base}+{at},x\n sta.l {work}+{32+at}')
    put(' jmp PendingJump_Good')
    entry('Write');live()
    for at in range(0,16,2):put(f' lda.l {work}+{32+at}\n sta.l {base}+{at},x')
    put(' jmp PendingJump_Good')
    label('Good');put(f' lda #2\n sta.l {work}+2\n ply\n plx\n pla\n plp\n clc\n rtl')
    label('Bad');put(f' lda #3\n sta.l {work}+2\n ply\n plx\n pla\n plp\n sec\n rtl')
    label('Bind');put(f' lda.l {work}\n cmp #$B691');branch('bne','BindBad')
    put(f' lda.l {work}+8\n ora.l {work}+10');branch('beq','BindBad')
    put(f' lda.l {work}+8\n cmp.l {work}+12');branch('bne','BindBad')
    put(f' lda.l {work}+10\n cmp.l {work}+14');branch('bne','BindBad')
    put(f' lda.l {work}+16\n cmp #{base&65535}');branch('bne','BindBad')
    put(f' lda.l {work}+18\n cmp #${base>>16:02X}');branch('bne','BindBad')
    put(f' lda.l {work}+20');branch('beq','BindBad')
    put(f' cmp #{plan["chr_capacity"]+1 if rehosted else base-0x420000+1}');branch('bcs','BindBad')
    put(f' lda.l {symbols["VmSourceWorld_Ready"]}\n cmp #$B4A3');branch('bne','BindBad')
    for key,value in(('VmSourceWorld_PoolBase',0x4000),('VmSourceWorld_SideBase',0x6800)):
        put(f' lda.l {symbols[key]}\n cmp #{value}');branch('bne','BindBad')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq','BindBad');put(f' cmp #{count+1}');branch('bcs','BindBad')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs','BindBad')
    put(f' lda.l {work}+22');branch('beq','BindBad');put(' cmp #17');branch('bcs','BindBad')
    put(f' lda.l {work}+6\n cmp.l {work}+22');branch('bcs','BindBad')
    put(f' lda.l {work}+4\n asl a\n asl a\n asl a\n sta.l {work}+26\n asl a\n clc\n adc.l {work}+26\n sta.l {work}+28')
    # Source birth clears the descriptor before exists publication, before the
    # fresh model copier runs. The constructor owns its checked model input.
    put(f' lda.l {work}+30');branch('bne','Bound')
    put(f' lda.l {work}+4\n asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n tax\n lda.l $416800,x\n cmp.l {work}+6');branch('bne','BindBad')
    label('Bound');put(' clc\n rts');label('BindBad');put(' sec\n rts')
    return '\n'.join(lines)+'\n'


def emit_constructor_bridge(work,symbols):
    """Optional birth/copy helpers; the real constructor owns checked inputs."""
    code=[]
    for name,leaf in(('Birth','ClearBirth'),('Copy','CopyModel')):
        code.append(f'''PendingJump_Constructor{name}:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda.l {work}
 beq PendingJump_Constructor{name}Done
 cmp #$B691
 bne PendingJump_Constructor{name}Bad
 lda.l {symbols['SourceScriptClone4086_Slot']}
 sta.l {work}+4
 lda.l {symbols['SourceScriptClone4086_Model']}
 sta.l {work}+6
 jsl PendingJump_{leaf}
 bcs PendingJump_Constructor{name}Bad
PendingJump_Constructor{name}Done:
.a16
.i16
 ply
 plx
 pla
 plp
 clc
 rtl
PendingJump_Constructor{name}Bad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
''')
    return '\n'.join(code)
