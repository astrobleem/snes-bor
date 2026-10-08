"""Execute the checked inactive-air gravity branch on the actual child row."""
ASM=r'''
ScriptedProjectileBeforeGravity:
.a16
.i16
 nop
 jsl SOURCEGRAVITY
 bcs ScriptedProjectileFixtureBad
ScriptedProjectileAfterGravity:
.a16
.i16
 nop
'''
OBSERVER=r'''
local gravity_before={}
emu.addMemoryCallback(function()
 local cs=word(sy.SourceNamedKnife4086_Child)
 gravity_before={toss=dw(0x41f300+cs*4),mark=dw(0x42e024+cs*40)}
 set('SourceGravityIdle4086_Ready',0xb618);set('SourceGravityIdle4086_Status',0);set('SourceToss4086_Ready',0xb4e2)
end,emu.callbackType.exec,BEFOREGRAVITY,BEFOREGRAVITY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local cs=word(sy.SourceNamedKnife4086_Child)
 emu.log('AUTHOREDGRAVITY|'..word(INDEX)..'|'..cs..'|'..gravity_before.toss..'|'..dw(0x41f300+cs*4)..'|'..gravity_before.mark..'|'..dw(0x42e024+cs*40)..'|'..dw(0x416830+cs*64)..'|'..dw(0x41400c+cs*80)..'|'..dw(0x41682c+cs*64)..'|'..word(sy.SourceGravityIdle4086_Status))
end,emu.callbackType.exec,AFTERGRAVITY,AFTERGRAVITY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local cs=word(sy.SourceNamedKnife4086_Child)
 emu.log('GRAVITYFAULT|'..word(sy.SourceWorldTick4086_Phase)..'|'..word(sy.SourceGravityIdle4086_Status)..'|'..word(sy.SourceModelEntityCopy4086_Ready)..'|'..word(sy.SourceModelEntityCopy4086_Entities)..'|'..word(sy.VmSourceWorld_Count)..'|'..dw(0x40c024+cs*96))
end,emu.callbackType.exec,sy.SourceGravityIdle4086_Bad,sy.SourceGravityIdle4086_Bad,emu.cpuType.snes,mt)
'''
BINDINGS=dict(SOURCEGRAVITY='SourceGravityIdle4086_Execute')
PROBES=dict(BEFOREGRAVITY='ScriptedProjectileBeforeGravity',AFTERGRAVITY='ScriptedProjectileAfterGravity')
