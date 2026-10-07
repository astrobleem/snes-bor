"""Drive actual source frame owners from frame zero to the projectile yield.

The private foreground harness supplies due world ticks. It never changes the
actor's frame, nextanim, altitude, script IP, or native request during advancement.
"""
from source_animation_step import derive, pack, validate_update_frame_pairing
from source_update_animation_inputs import derive as inputs, pack as pack_inputs

PRELUDE=r'''
ScriptedProjectileNaturalCallback:
.a16
.i16
 jsl CALLBACKRUN
 bcs ScriptedProjectileFixtureBad
 cmp #3
 beq ScriptedProjectileNaturalCallback
 cmp #4
 bne ScriptedProjectileFixtureBad
 lda #1
 jsl FRAMEACK
 bcs ScriptedProjectileFixtureBad
 jsl EFFECTRUN
 bcs ScriptedProjectileFixtureBad
 cmp #0
 bne ScriptedProjectileFixtureBad
 lda.l TIMEDSTATE
 cmp #1
 bne ScriptedProjectileNaturalTick
 jsl TIMEDCONTINUE
 bcs ScriptedProjectileFixtureBad
ScriptedProjectileNaturalTick:
.a16
.i16
 nop
 jsl TIMEDBEGIN
 bcs ScriptedProjectileFixtureBad
 cmp #1
 bne ScriptedProjectileFixtureBad
 jsl CALLBACKBEGIN
 bcs ScriptedProjectileFixtureBad
 lda.l FRAMEREQUEST
 cmp #6
 bne ScriptedProjectileNaturalCallback
'''

def resources(source,frame_bytes):
    timed=pack(derive(source));prefix=pack_inputs(inputs(source))
    validate_update_frame_pairing(timed,frame_bytes)
    setup=f'''
 set('SourceUpdateFrame4086_Request',0);put(side+6,0)
 set('SourceUpdateAnimation4086_Ready',0xb60f);set('SourceUpdateAnimation4086_State',0)
 set('SourceUpdateAnimation4086_Base',32768);set('SourceUpdateAnimation4086_Bank',60);set('SourceUpdateAnimation4086_Bytes',{len(timed)})
 set('SourceUpdateAnimationPrefix4086_Ready',0xb60d);set('SourceUpdateAnimationPrefix4086_Status',0)
 set('SourceUpdateAnimationPrefix4086_Base',{32768+len(timed)});set('SourceUpdateAnimationPrefix4086_Bank',60);set('SourceUpdateAnimationPrefix4086_Bytes',{len(prefix)});set('SourceUpdateAnimationPrefix4086_Models',16);set('SourceUpdateAnimationPrefix4086_SleepID',80)
 for j=0,5119 do emu.write(0x42e000+j,0,mt)end
'''
    observer=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local s=c.slot;local side=0x416800+s*64;local v=0x414000+s*80
 local t=dw(side+8)
 emu.log('NATURALFRAME|'..word(INDEX)..'|'..word(side+6)..'|'..dw(sy.VmSourceWorld_Time)..'|'..t..'|'..dw(v+12)..'|'..dw(side+48)..'|'..word(sy.SourceUpdateFrame4086_Pending))
 -- The foreground tick supplier advances only world time and its dispatch lease.
 set('VmSourceWorld_Time',t,4);set('SourceClock4086_TimeLo',t,4);set('SourceCtorState4086_Time',t,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',7)
 set('SourceWorldTick4086_Slot',s);set('SourceWorldTick4086_View',v&65535);set('SourceWorldTick4086_Side',side&65535);set('SourceWorldTick4086_TimeLo',t,4)
end,emu.callbackType.exec,NATURALTICK,NATURALTICK,emu.cpuType.snes,mt)
'''
    return setup,observer,(60,0,timed+prefix)

BINDINGS=dict(TIMEDSTATE='SourceUpdateAnimation4086_State',TIMEDBEGIN='SourceUpdateAnimation4086_Begin',TIMEDCONTINUE='SourceUpdateAnimation4086_Continue',FRAMEREQUEST='SourceUpdateFrame4086_Request')
