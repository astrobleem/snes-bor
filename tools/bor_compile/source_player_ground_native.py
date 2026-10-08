"""Compile ground movement over a typed 128-byte caller snapshot/continuation.

This is not an implicit canonical actor allocation. A controller binder must
capture/publish the named live fields at each source boundary and execute every
requested service. Readonly validity queries must not mutate that snapshot.
Finite Q16 speed operands must be exactly divisible by two when used for Z.
"""
from source_player_run_4086 import KEYS


def emit(work):
    if not 0 <= work <= 0x1000000-128:
        raise ValueError('PLAYER_GROUND_NATIVE_EXTENT')
    lines=[];serial=0
    prefix='SourceGround_'
    def put(text):lines.extend(text.strip().splitlines())
    def label(name):put(prefix+name+':\n.a16\n.i16')
    def jump(name):put(' jmp '+prefix+name)
    def conditional(op,name):
        nonlocal serial
        serial+=1;skip=prefix+'Skip'+str(serial)
        inverse={'beq':'bne','bne':'beq','bcc':'bcs','bcs':'bcc','bmi':'bpl','bpl':'bmi'}[op]
        put(f' {inverse} {skip}\n jmp {prefix+name}\n{skip}:\n.a16\n.i16')
    def zero(offset):put(f' lda.l W+{offset}\n ora.l W+{offset+2}')
    def set32(offset,value):put(f' lda #{value&65535}\n sta.l W+{offset}\n lda #{value>>16&65535}\n sta.l W+{offset+2}')
    def copy32(source,dest):put(f' lda.l W+{source}\n sta.l W+{dest}\n lda.l W+{source+2}\n sta.l W+{dest+2}')
    def query(role,continuation):
        put(f' lda #{role}\n sta.l W+6\n lda #{continuation}\n sta.l W+4')
        jump('QueryPending')
    def service(kind,role,continuation,state=3):
        put(f' lda #{kind}\n sta.l W+90\n lda #{role}\n sta.l W+6\n lda #{continuation}\n sta.l W+4\n lda #{state}')
        jump('PublishPending')
    for entry,dest in (('Begin','Start'),('Resume','Continue')):
        label(entry);put(' php\n rep #$39\n phx\n phy\n lda.l W\n cmp #$B679');conditional('bne','Fault');jump(dest)
    label('Start')
    put(' lda.l W+2');conditional('beq','StartReady');put(' cmp #2');conditional('bne','Fault')
    label('StartReady');put(' lda #1\n sta.l W+2\n lda #0\n sta.l W+86\n sta.l W+88')
    put(' lda.l W+20');conditional('beq','DuckQuery')
    put(f' lda.l W+16\n and #{KEYS["moveup"]}');conditional('bne','UpQuery')
    put(f' lda.l W+16\n and #{KEYS["movedown"]}');conditional('bne','DownQuery')
    set32(56,0);jump('Horizontal')
    label('UpQuery');query(0,1)
    label('DownQuery');query(1,2)
    label('DuckQuery');query(2,3)
    label('Continue')
    put(' lda.l W+2\n cmp #3');conditional('beq','AckService')
    put(' cmp #4');conditional('beq','AckService')
    put(' cmp #5');conditional('bne','Fault')
    label('AckService')
    put(' lda.l W+8\n cmp #$B67A');conditional('bne','Fault')
    put(' lda.l W+12\n cmp.l W+90');conditional('bne','Fault')
    put(' lda.l W+14\n cmp.l W+6');conditional('bne','Fault')
    put(' lda #0\n sta.l W+8\n lda #1\n sta.l W+2\n lda.l W+4')
    for continuation,dest in ((1,'Vertical'),(2,'Vertical'),(3,'DuckResult'),(4,'TurnResult'),(5,'BackResult'),(10,'DuckDone'),(11,'Complete'),(12,'ItemDone'),(13,'Complete')):
        put(f' cmp #{continuation}');conditional('beq',dest)
    jump('Fault')
    label('Vertical');zero(10);conditional('beq','VerticalOrdinary');zero(24);conditional('bne','VerticalRun')
    put(' lda.l W+4\n inc a\n sta.l W+86');copy32(44,96);jump('VerticalSpeed')
    label('VerticalOrdinary');zero(24);conditional('bne','VerticalRun');put(' lda #1\n sta.l W+86');copy32(44,96);jump('VerticalSpeed')
    label('VerticalRun');put(' lda #4\n sta.l W+86');copy32(48,96)
    label('VerticalSpeed');put(' lda.l W+96\n and #1');conditional('bne','Fault')
    put(' lda.l W+98\n cmp #$8000\n ror a\n sta.l W+58\n lda.l W+96\n ror a\n sta.l W+56\n lda.l W+4\n cmp #1');conditional('bne','Horizontal')
    copy32(56,96);put(' jsr '+prefix+'Negate');copy32(96,56)
    jump('Horizontal')
    label('DuckResult');zero(10);conditional('beq','Horizontal')
    put(f' lda.l W+16\n and #{KEYS["movedown"]}');conditional('beq','Horizontal')
    put(' lda.l W+22');conditional('beq','Horizontal');service(1,2,10)
    label('DuckDone');set32(52,0);set32(56,0);jump('Complete')
    label('Horizontal');put(f' lda.l W+16\n and #{KEYS["moveleft"]}');conditional('bne','Left')
    put(f' lda.l W+16\n and #{KEYS["moveright"]}');conditional('bne','Right')
    set32(52,0);set32(32,0);jump('Item')
    label('Left');put(' lda #0\n sta.l W+102\n lda.l W+30');conditional('bne','SameFacing');put(' lda.l W+28\n cmp #1');conditional('bne','SameFacing');jump('TurnCheck')
    label('Right');put(' lda #1\n sta.l W+102');zero(28);conditional('bne','SameFacing')
    label('TurnCheck');zero(36);conditional('beq','TimerCheck');zero(32);conditional('bne','TimerCheck')
    put(' clc\n lda.l W+40\n adc.l W+36\n sta.l W+32\n lda.l W+42\n adc.l W+38\n sta.l W+34');jump('HorizontalSpeed')
    label('TimerCheck');zero(32);conditional('beq','NoDelayCheck')
    put(' lda.l W+42\n cmp.l W+34');conditional('bcc','NoDelayCheck');conditional('bne','Expired')
    put(' lda.l W+40\n cmp.l W+32');conditional('bcc','NoDelayCheck')
    label('Expired');set32(32,0);query(3,4)
    label('NoDelayCheck');zero(36);conditional('beq','TurnQuery');zero(32);conditional('bne','HorizontalSpeed');jump('Flip')
    label('TurnQuery');query(3,4)
    label('TurnResult');zero(10);conditional('beq','TurnUnavailable')
    # 42 is the explicit snapshot wire identity for common_turn, not a runtime pointer.
    set32(60,42);set32(68,1);set32(64,0);set32(52,0);set32(56,0);service(1,3,11)
    label('TurnUnavailable');zero(32);conditional('bne','HorizontalSpeed')
    label('Flip');put(' lda.l W+102\n sta.l W+28\n lda #0\n sta.l W+30');jump('HorizontalSpeed')
    label('SameFacing');set32(32,0)
    label('HorizontalSpeed');zero(24);conditional('beq','WalkingSpeed')
    put(' lda #4\n sta.l W+86');copy32(48,96);jump('HorizontalSign')
    label('WalkingSpeed');put(' lda.l W+86\n cmp #2');conditional('beq','WalkingCopy');put(' cmp #3');conditional('beq','WalkingCopy');put(' lda #1\n sta.l W+86')
    label('WalkingCopy');copy32(44,96)
    label('HorizontalSign');put(' lda.l W+102');conditional('bne','HorizontalStore');put(' jsr '+prefix+'Negate')
    label('HorizontalStore');copy32(96,52)
    label('Item');service(2,65535,12,4)
    label('ItemDone');put(' lda.l W+86');conditional('beq','ActionDispatch');set32(60,0);set32(64,1)
    label('ActionDispatch');put(' lda.l W+86\n cmp #1');conditional('beq','BackQuery')
    for action,kind,role in ((2,5,0),(3,6,1),(4,1,5)):
        put(f' cmp #{action}');conditional('beq','Dispatch'+str(action))
    zero(64);conditional('beq','Complete');service(7,65535,13)
    for action,kind,role in ((2,5,0),(3,6,1),(4,1,5)):
        label('Dispatch'+str(action));service(kind,role,13)
    label('BackQuery');put(' lda.l W+76');conditional('beq','Walk');query(4,5)
    label('BackResult');zero(10);conditional('beq','Walk')
    # Exact facing int32 comparisons, including unusual signed values.
    def equals(offset,value,dest):
        nonlocal serial
        serial+=1;nextname='EqNext'+str(serial)
        put(f' lda.l W+{offset+2}');conditional('bne',nextname)
        put(f' lda.l W+{offset}\n cmp #{value}');conditional('beq',dest);label(nextname)
    equals(72,1,'FaceRight');equals(78,1,'FaceRight');equals(72,2,'FaceLeft');equals(78,1,'FaceLeft')
    equals(72,3,'FaceLevel');equals(78,3,'FaceLevel');jump('BackTimer')
    label('FaceRight');zero(28);conditional('beq','Backwalk');jump('Walk')
    label('FaceLeft');zero(28);conditional('bne','Backwalk');jump('Walk')
    label('FaceLevel');put(' lda.l W+82\n and #8');conditional('beq','ScrollRight');zero(28);conditional('beq','Backwalk')
    label('ScrollRight');put(' lda.l W+82\n and #2');conditional('beq','BackTimer');equals(28,1,'Backwalk')
    label('BackTimer');zero(32);conditional('beq','Walk');zero(36);conditional('bne','Backwalk')
    label('Walk');service(3,65535,13)
    label('Backwalk');service(4,65535,13)
    label('QueryPending');put(' lda #0\n sta.l W+90\n sta.l W+10\n sta.l W+12\n lda #5')
    label('PublishPending');put(' sta.l W+2\n lda #0\n sta.l W+8\n sta.l W+92\n ply\n plx\n plp\n clc\n rtl')
    label('Complete');put(' lda #2\n sta.l W+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Fault');put(' lda #6\n sta.l W+2\n lda #$FFFF\n ply\n plx\n plp\n sec\n rtl')
    label('Negate');put(' lda.l W+98\n cmp #$8000');conditional('bne','NegateValid');put(' lda.l W+96');conditional('bne','NegateValid')
    # Discard this helper's return address before the public fault epilogue.
    put(' pla');jump('Fault')
    label('NegateValid');put(' sec\n lda #0\n sbc.l W+96\n sta.l W+96\n lda #0\n sbc.l W+98\n sta.l W+98\n rts')
    return '\n'.join(lines).replace('W+',str(work)+'+').replace(' W\n',' '+str(work)+'\n')+'\n'
