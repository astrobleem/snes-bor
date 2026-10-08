"""Private due movement subservices on the actual scripted arrow child.

Runs real velocity accumulation and direct check_move. Gravity and full world
post-update completion are separate; the fixture never acknowledges phase11.
"""
ASM=r'''
ScriptedProjectileBeforeMove:
.a16
.i16
 nop
 jsl SOURCEVELOCITY
 bcs ScriptedProjectileFixtureBad
 lda #11
 sta.l TICKPHASE
 jsl SOURCECHECKMOVE
 bcs ScriptedProjectileFixtureBad
ScriptedProjectileAfterMove:
.a16
.i16
 nop
'''

OBSERVER=r'''
local move_before={}
emu.addMemoryCallback(function()
 local cs=word(sy.SourceNamedKnife4086_Child);local v=0x414000+cs*80;local side=0x416800+cs*64
 local t=dw(sy.VmSourceWorld_Time)
 move_before={x=dw(v+52),z=dw(v+60),a=dw(v+12),mark=dw(0x42e024+cs*40),parent=dw(sy.SourceSelf4086_GlobalLow)}
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Phase',10);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Slot',cs);set('SourceWorldTick4086_Fault',0);set('SourceWorldTick4086_TimeLo',t,4)
 set('SourceSelf4086_GlobalLow',v,4);set('SourceVelocity4086_Ready',0xb5de);set('SourceVelocity4086_Status',0);set('SourceCheckMove4086_Ready',0xb617);set('SourceCheckMove4086_Status',0)
end,emu.callbackType.exec,BEFOREMOVE,BEFOREMOVE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local cs=word(sy.SourceNamedKnife4086_Child);local v=0x414000+cs*80;local side=0x416800+cs*64;local aux=0x41f500+cs*20;local mark=0x42e024+cs*40
 emu.log('AUTHOREDMOVE|'..word(INDEX)..'|'..cs..'|'..move_before.x..'|'..dw(v+52)..'|'..move_before.z..'|'..dw(v+60)..'|'..move_before.a..'|'..dw(v+12)..'|'..dw(aux)..'|'..dw(aux+4)..'|'..dw(side+24)..'|'..move_before.mark..'|'..dw(mark)..'|'..word(sy.SourceVelocity4086_Status)..'|'..word(sy.SourceCheckMove4086_Status))
 set('SourceSelf4086_GlobalLow',move_before.parent,4);set('SourceWorldTick4086_Ready',0)
end,emu.callbackType.exec,AFTERMOVE,AFTERMOVE,emu.cpuType.snes,mt)
for _,k in ipairs({'SourceVelocity4086_Bad','SourceCheckMove4086_Bad','SourceEmptyInitEnvironment4086_Bad','SourceFreeze4086_QueryBad'})do
 emu.addMemoryCallback(function()emu.log('MOVEFAULT|'..k..'|'..word(sy.SourceWorldTick4086_Phase)..'|'..word(sy.SourceVelocity4086_Status)..'|'..word(sy.SourceCheckMove4086_Status))end,emu.callbackType.exec,sy[k],sy[k],emu.cpuType.snes,mt)
end
'''
BINDINGS=dict(SOURCEVELOCITY='SourceVelocity4086_Apply',SOURCECHECKMOVE='SourceCheckMove4086_Execute',TICKPHASE='SourceWorldTick4086_Phase')
PROBES=dict(BEFOREMOVE='ScriptedProjectileBeforeMove',AFTERMOVE='ScriptedProjectileAfterMove')
