"""Private due-tick owner after real parent sound/frame completion.

The caller must execute the source audio service before this tick; it may not
clear pending frame state to manufacture an idle actor owner.
"""

ASM=r'''
ScriptedProjectileBeforeArrow:
.a16
.i16
 nop
 jsl ARROWAIRUN
 bcs ScriptedProjectileFixtureBad
 cmp #0
 bne ScriptedProjectileFixtureBad
ScriptedProjectileAfterArrow:
.a16
.i16
 nop
'''

OBSERVER=r'''
local arrow_before={}
emu.addMemoryCallback(function()
 local cs=word(sy.SourceNamedKnife4086_Child);local v=0x414000+cs*80;local side=0x416800+cs*64
 local t=dw(side+20)
 arrow_before={x=dw(v+52),z=dw(v+60),a=dw(v+12),vz=dw(side+40),speed=dw(side+60),nextthink=t,parent=dw(sy.SourceSelf4086_GlobalLow)}
 set('VmSourceWorld_Time',t,4);set('SourceClock4086_TimeLo',t,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Phase',6);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Slot',cs);set('SourceWorldTick4086_TimeLo',t,4)
 set('SourceSelf4086_GlobalLow',v,4);set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',0);set('SourceAI4086_Endgame',0,4);set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104)
 set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);set('SourceCommonRun4086_Ready',0xb5e9);set('SourceCommonRun4086_State',0);set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',0);set('SourceAIReadonly4086_Ready',0xb5e8);set('SourceAIReadonly4086_Status',0);set('SourceArrowMove4086_Ready',0xb616);set('SourceArrowMove4086_Status',0);set('SourceRetirement4086_Ready',0xb4f8)
end,emu.callbackType.exec,BEFOREARROW,BEFOREARROW,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local cs=word(sy.SourceNamedKnife4086_Child);local v=0x414000+cs*80;local side=0x416800+cs*64
 local changed=0;for _,pair in ipairs({{dw(v+52),arrow_before.x},{dw(v+60),arrow_before.z},{dw(v+12),arrow_before.a},{dw(side+40),arrow_before.vz},{dw(side+60),arrow_before.speed}})do if pair[1]~=pair[2]then changed=changed+1 end end
 emu.log('AUTHOREDARROW|'..word(INDEX)..'|'..cs..'|'..dw(v+28)..'|'..dw(side+60)..'|'..dw(side+36)..'|'..dw(side+20)..'|'..arrow_before.nextthink..'|'..changed..'|'..word(sy.SourceArrowMove4086_Status)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State))
 set('SourceSelf4086_GlobalLow',arrow_before.parent,4);set('SourceWorldTick4086_Ready',0)
end,emu.callbackType.exec,AFTERARROW,AFTERARROW,emu.cpuType.snes,mt)
for _,k in ipairs({'SourceAI4086_PreflightBad','SourceAIRun4086_Bad','SourceCommonRun4086_Bad','SourceAIReadonly4086_Bad','SourceArrowMove4086_Bad'})do
 emu.addMemoryCallback(function()emu.log('ARROWFAULT|'..k..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceCommonThink4086_State)..'|'..word(sy.SourceAIReadonly4086_Status)..'|'..word(sy.SourceArrowMove4086_Status))end,emu.callbackType.exec,sy[k],sy[k],emu.cpuType.snes,mt)
end
'''

BINDINGS=dict(ARROWAIRUN='SourceAIRun4086_Begin')
PROBES=dict(BEFOREARROW='ScriptedProjectileBeforeArrow',AFTERARROW='ScriptedProjectileAfterArrow')
