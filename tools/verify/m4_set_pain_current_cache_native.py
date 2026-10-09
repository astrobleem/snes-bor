"""Pain role selection after actual synchronized model/cache services."""
import argparse, hashlib, json, re, struct, sys
from pathlib import Path
from unittest.mock import patch
import m4_model_current_pipeline_native as current
import m4_model_services_pipeline_native as parent
from actor_s5_entity_fixture import symbols
from compiler import Source
from source_foreign_state_layout import layout
from source_set_pain_select_native import derive,emit,emit_begin,emit_frame_prefix,emit_frame_owner


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--begin-animation',action='store_true');p.add_argument('--frame-zero-prefix',action='store_true');p.add_argument('--frame-zero-owner',action='store_true')
    a=p.parse_args();a.frame_zero_prefix=a.frame_zero_prefix or a.frame_zero_owner;a.begin_animation=a.begin_animation or a.frame_zero_prefix;a.output=a.output.resolve();req=derive(Source(a.source));sy=symbols(Path('src/main.sym'))
    work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls')
    original=parent.run_fixture
    def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
        nominal=[c for c in rows if not c['fault']]
        rows[:]=[dict(c,pain_type=t)for c in nominal for t in (0,1,19,-1,20,65536)]
        from source_animation_init_4086 import derive as animations
        directory=animations(Source(a.source))['animations']
        if a.frame_zero_prefix:
            from source_frame_effects_4086 import derive as frame_effects
            effects=frame_effects(Source(a.source))['animations']
        for c in rows:
            requested=req['grabbed']if c['pain_type']==-1 or c['pain_type']>=len(req['pains'])else req['pains'][c['pain_type']]
            cache=c['wanted_animation'];selected=65535;handle=0;count=0
            # Directory frame counts are source-derived, and wanted_animation
            # is the actual default-inherited mutable cache from the parent.
            for candidate in (requested,req['pains'][0],req['idle']):
                h=struct.unpack_from('<H',bytes(cache),candidate*2)[0]
                if h and directory[h-1]['numframes']:
                    selected=candidate;handle=h;count=directory[h-1]['numframes'];break
            c.update(pain_requested=requested,pain_selected=selected,pain_handle=handle,pain_count=count)
            if a.frame_zero_prefix:
                c['pain_nextanim']=48+effects[handle-1]['frames'][0]['delay_ticks']
                c['pain_sound']=effects[handle-1]['frames'][0]['sound']
        needle=' ply\n plx\n plp\n clc\n rtl\nModelPipeline_EntryBad:'
        assert kw['append'].count(needle)==1
        call=f''' lda #$B6B5
 sta.l {work}
 lda #0
 sta.l {work}+2
 sta.l {work}+22
 lda #1
 sta.l {work}+10
 ldx #1
 ldy #0
 jsl SetPainSelect_Run
 bcs SetPainCacheBad
 ldx #1
 ldy #0
 jsl SetPainSelect_Run
 bcs SetPainCacheBad
 lda.l {work}+6
 pha
 lda.l {work}+8
 pha
 lda #$FFFE
 sta.l {work}+6
 lda #$FFFF
 sta.l {work}+8
 lda #0
 sta.l {work}+2
 jsl SetPainSelect_Run
 bcs SetPainCacheNegativeRejected
 jmp ModelPipeline_EntryBad
SetPainCacheNegativeRejected:
.a16
.i16
 pla
 sta.l {work}+8
 pla
 sta.l {work}+6
 lda #0
 sta.l {work}
 sta.l {work}+2
 jsl SetPainSelect_Run
 bcs SetPainCacheDisabledRejected
 jmp ModelPipeline_EntryBad
SetPainCacheDisabledRejected:
.a16
.i16
 lda #$B6B5
 sta.l {work}
 lda #0
 sta.l {work}+2
 ldx #2
 ldy #0
 jsl SetPainSelect_Run
 bcs SetPainCacheGenerationRejected
 jmp ModelPipeline_EntryBad
SetPainCacheGenerationRejected:
.a16
.i16
 lda #0
 sta.l {work}+2
 ldx #1
 ldy #0
 jsl SetPainSelect_Run
 bcs SetPainCacheBad
'''
        # Use a local long error jump so the expanded wrapper remains bounded.
        call=call.replace(' bcs SetPainCacheBad',' bcc SetPainCacheNext1\n jmp ModelPipeline_EntryBad\nSetPainCacheNext1:\n.a16\n.i16',1)
        call=call.replace(' bcs SetPainCacheBad',' bcc SetPainCacheNext2\n jmp ModelPipeline_EntryBad\nSetPainCacheNext2:\n.a16\n.i16',1)
        call=call.replace(' bcs SetPainCacheBad',' bcc SetPainCacheNext3\n jmp ModelPipeline_EntryBad\nSetPainCacheNext3:\n.a16\n.i16',1)
        serial=0
        def far_error(match):
            nonlocal serial
            serial+=1;skip='SetPainCacheWrapperSkip'+str(serial)
            return ' bcc '+skip+'\n jmp ModelPipeline_EntryBad\n'+skip+':\n.a16\n.i16'
        kw['append']=kw['append'].replace(needle,call+needle)+emit(work,req,sy)
        kw['append']=re.sub(r' bcs ModelPipeline_EntryBad',far_error,kw['append'])
        if a.begin_animation:
            lua=lua.replace('local ranges={','local ranges={{0x41f500,2560},{0x43e000,512},{0x43eb00,4096},')
            prefix=''
            for i in range(2):
                prefix+=f''' ldx #1
 ldy #0
 jsl SetPainBegin_Run
 bcc SetPainBeginCacheContinue{i}
 jmp ModelPipeline_EntryBad
SetPainBeginCacheContinue{i}:
.a16
.i16
 cmp #1
 beq SetPainBeginCachePending{i}
 jmp ModelPipeline_EntryBad
SetPainBeginCachePending{i}:
.a16
.i16
'''
                if i==0:
                    prefix+=f'''SetPainCacheMutateVelocity:
.a16
.i16
 lda.l {sy['SourceAnimationInit4086_Side']}
 tax
 lda #0
 sta.l $410024,x
 sta.l $410028,x
 sta.l $41002C,x
 lda #1
 sta.l $410026,x
 lda #2
 sta.l $41002A,x
 lda #3
 sta.l $41002E,x
'''
            assert kw['append'].count(needle)==1
            kw['append']=kw['append'].replace(needle,prefix+needle)+emit_begin(work,sy)
            if a.frame_zero_prefix:
                kw['append']=kw['append'].replace(needle,''' ldx #1
 ldy #0
 jsl SetPainFrame_Run
 bcc SetPainFrameCacheNext1
 jmp ModelPipeline_EntryBad
SetPainFrameCacheNext1:
.a16
.i16
 jsl SetPainFrame_Run
 bcc SetPainFrameCacheNext2
 jmp ModelPipeline_EntryBad
SetPainFrameCacheNext2:
.a16
.i16
'''+needle)+emit_frame_prefix(work,sy)
                if a.frame_zero_owner:
                    kw['append']=kw['append'].replace(' jsl SetPainFrame_Run',' jsl SetPainFrameOwner_Run')+emit_frame_owner(sy)
                    kw['probes']['PAINOWNERRETURN']='SetPainFrameCacheNext2'
                kw.setdefault('bindings',{})['PAINSTARTFRAME']='SourceAnimationInit4086_StartFrame'
            kw['probes']['BEGINENTRY']='SetPainBegin_Run'
            kw['probes']['MUTATEVELOCITY']='SetPainCacheMutateVelocity'
            kw.setdefault('bindings',{})['ANIMBEGIN']='SourceAnimationInit4086_Begin'
        anchor=' before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1
        lua=lua.replace(anchor,f' put({work}+4,c.slot);put({work}+6,c.pain_type,4)\n'+anchor)
        anchor=' local c=rows[word(INDEX)+1]\n local function expect';assert lua.count(anchor)==1
        # Control bytes are caller-owned scratch. Actor/cache fields still use
        # the parent's complete native before/after checks.
        lua=lua.replace('local ranges={',f'local ranges={{{{{work},24}},')
        anchor=' local n=0;for a,v in pairs(before)';assert lua.count(anchor)==1
        expected=f''' for j=0,23 do before[{work}+j]=emu.read({work}+j,mt)end
 if word({work}+2)~=2 or word({work}+12)~=c.pain_requested or word({work}+14)~=c.pain_selected or word({work}+16)~=c.pain_handle or word({work}+18)~=c.pain_count then before[{work}+2]=255 end
'''
        lua=lua.replace(anchor,expected+anchor)
        if a.begin_animation:
            lua=lua.replace(f'word({work}+2)~=2',f'word({work}+2)~=3 or word(sy.SourceAnimationInit4086_State)~=1 or word(sy.SourceAnimationInit4086_Issued)~=0')
            lua=lua.replace('value(side+4,c.wanted_handle,2);','value(side+4,c.pain_handle,2);').replace('value(side+4,c.wanted_idle_handle,2);','value(side+4,c.pain_handle,2);')
            lua=lua.replace('value(view+36,c.wanted_hp,4);','value(view+20,c.pain_selected,4);value(view+36,c.wanted_hp,4);')
            extra=''' local side=0x416800+c.slot*64;local core=0x40c000+c.slot*96;value(core+84,11,4)
 for off=36,44,4 do value(side+off,(1+(off-36)//4)*65536,4)end
 value(0x41f508+c.slot*20,0,4);value(0x41f510+c.slot*20,1,2);value(0x43e000+(c.pain_handle-1)*4,0,4)
'''
            lua=lua.replace(' local n=0;for a,v in pairs(before)',extra+' local n=0;for a,v in pairs(before)')
            lua+='''
local painBeginActive=false;local painVelocityWrites=0
emu.addMemoryCallback(function()painBeginActive=true;emu.log("PAINBEGIN|"..word(INDEX))end,emu.callbackType.exec,BEGINENTRY,BEGINENTRY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if painBeginActive then emu.log("PAINANIM|"..word(INDEX))end end,emu.callbackType.exec,ANIMBEGIN,ANIMBEGIN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()painBeginActive=false;local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64;local n=0;for j=36,47 do if emu.read(side+j,mt)~=0 then n=n+1 end end;emu.log("PAINZERO|"..word(INDEX).."|"..n)end,emu.callbackType.exec,MUTATEVELOCITY,MUTATEVELOCITY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function(address)if painBeginActive then local c=rows[word(INDEX)+1];local first=0x416824+c.slot*64;if address>=first and address<first+12 then painVelocityWrites=painVelocityWrites+1 end end end,emu.callbackType.write,0x416800,0x4187ff,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()painBeginActive=false;emu.log("PAINWRITES|"..word(INDEX).."|"..painVelocityWrites);painVelocityWrites=0 end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
        if a.frame_zero_prefix:
            lua=lua.replace('word(sy.SourceAnimationInit4086_Issued)~=0','word(sy.SourceAnimationInit4086_Issued)~=1')
            lua=lua.replace('value(side+8,c.wanted_idle_nextanim,4);','value(side+8,c.pain_nextanim,4);')
            lua=lua.replace('word(sy.SourceSelf4086_Active)~=0 or word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*((c.slot+1)%128)','word(sy.SourceSelf4086_Active)~=1 or word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*c.slot')
            start=lua.index(' if c.fault==0 and (word(sy.SourceUpdateFrame4086_State)')
            end=lua.index(" emu.log('PIPELINERESULT|'",start)
            lua=lua[:start]+''' if word(sy.SourceUpdateFrame4086_State)~=1 or word(sy.SourceUpdateFrame4086_Pending)~=(PAINPENDING) or word(sy.SourceUpdateFrame4086_Handle)~=c.pain_handle or word(sy.SourceUpdateFrame4086_Request)~=0 then n=n+1 end
'''+lua[end:]
            lua+='\nemu.addMemoryCallback(function()emu.log("PAINFRAMEISSUE|"..word(INDEX))end,emu.callbackType.exec,PAINSTARTFRAME,PAINSTARTFRAME,emu.cpuType.snes,mt)\n'
        if a.frame_zero_prefix:lua=lua.replace('PAINPENDING',str(2 if a.frame_zero_owner else 1))
        if a.frame_zero_owner:
            lua+='''
emu.addMemoryCallback(function()local s=emu.getState();emu.log("PAINEFFECTTICKET|"..word(INDEX).."|"..s['cpu.a'].."|"..word(sy.SourceFrameEffectPlan4086_Service).."|"..word(sy.SourceFrameEffectPlan4086_Acknowledged))end,emu.callbackType.exec,PAINOWNERRETURN,PAINOWNERRETURN,emu.cpuType.snes,mt)
'''
        kw.setdefault('probes',{})['PAINSELECT']='SetPainSelect_Run'
        lua+='\nemu.addMemoryCallback(function()emu.log("PAINCACHE|"..word(INDEX))end,emu.callbackType.exec,PAINSELECT,PAINSELECT,emu.cpuType.snes,mt)\n'
        raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
        calls=[int(l.split('PAINCACHE|')[1])for l in log.splitlines()if'PAINCACHE|'in l]
        reporter.check('selection retries and three invalid requests recover after real native model/cache services',calls==[i for i in range(len(rows))for _ in range(7 if a.begin_animation else 6)])
        if a.begin_animation:
            calls=[int(l.split('PAINBEGIN|')[1])for l in log.splitlines()if'PAINBEGIN|'in l]
            reporter.check('real animation begins once and retains frame-zero debt under retry',calls==[i for i in range(len(rows))for _ in range(4 if a.frame_zero_prefix else 2)])
            actual=[int(l.split('PAINANIM|')[1])for l in log.splitlines()if'PAINANIM|'in l]
            reporter.check('actual animation initializer executes exactly once per pain request',actual==list(range(len(rows))))
            zero=[l.split('PAINZERO|')[1]for l in log.splitlines()if'PAINZERO|'in l]
            writes=[l.split('PAINWRITES|')[1]for l in log.splitlines()if'PAINWRITES|'in l]
            reporter.check('velocity clears once before the injected pending child mutation',zero==[str(i)+'|0'for i in range(len(rows))]and writes==[str(i)+'|12'for i in range(len(rows))])
        if a.frame_zero_prefix:
            issued=[int(l.split('PAINFRAMEISSUE|')[1])for l in log.splitlines()if'PAINFRAMEISSUE|'in l]
            reporter.check('actual frame-zero prefix issues once across two native retries',issued==list(range(len(rows))))
        if a.frame_zero_owner:
            tickets=[l.split('PAINEFFECTTICKET|')[1]for l in log.splitlines()if'PAINEFFECTTICKET|'in l]
            reporter.check('actual pain script and frame effects retain unacknowledged source SOUND ticket',tickets==[str(i)+'|9|9|0'for i in range(len(rows))])
        return raw,log
    argv=['m4_model_current_pipeline_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
    if a.frame_zero_prefix:argv+=['--nested-idle']
    with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',argv):
        try:current.main()
        except SystemExit as e:
            if e.code not in (None,0):raise
    path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_SET_PAIN_CURRENT_CACHE_NATIVE_V1',pain_selection_requirements=req,actual_mutable_model_cache_queried=True,source_animation_resolve_bound=True,actor_animation_begin_bound=False,source_pain_flags_bound=False,source_unfreeze_bound=False,onpain_bound=False,source_audio_bound=False,full_damage_callback_bound=False,new_foreign_arena_bytes=0)
    path.write_text(json.dumps(r,indent=2)+'\n')
    if a.begin_animation:
        r.update(schema='BYOR_SET_PAIN_ANIMATION_BEGIN_NATIVE_V1',actor_animation_begin_bound=True,source_velocity_clear_once=True,frame_zero_debt_retained=True,observer_acknowledgements=False)
        r.update(native_injected_pending_child_velocity_mutation=True,actual_source_frame_zero_execution=False,source_flags_deferred_until_frame_child_complete=True)
        path.write_text(json.dumps(r,indent=2)+'\n')

    if a.frame_zero_prefix:
        r.update(schema='BYOR_SET_PAIN_FRAME_ZERO_PREFIX_NATIVE_V1',actual_source_frame_zero_prefix=True,actual_source_frame_zero_execution=False,source_animation_script_debt_pending=True,observer_acknowledgements=False)
        path.write_text(json.dumps(r,indent=2)+'\n')

    if a.frame_zero_owner:
        r.update(schema='BYOR_SET_PAIN_FRAME_ZERO_OWNER_NATIVE_V1',actual_source_animation_script=True,actual_source_frame_motion=True,actual_source_frame_effect_owner=True,source_audio_ticket_pending=True,source_audio_bound=False,pain_flags_applied=False)
        path.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
