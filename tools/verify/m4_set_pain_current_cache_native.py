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
    p.add_argument('--finish-uninitialized-onpain',action='store_true');p.add_argument('--pain-flags',action='store_true');p.add_argument('--frame-sound-admission',action='store_true');p.add_argument('--assets',type=Path);p.add_argument('--begin-animation',action='store_true');p.add_argument('--frame-zero-prefix',action='store_true');p.add_argument('--frame-zero-owner',action='store_true')
    a=p.parse_args();a.pain_flags=a.pain_flags or a.finish_uninitialized_onpain;a.frame_sound_admission=a.frame_sound_admission or a.pain_flags;a.frame_zero_owner=a.frame_zero_owner or a.frame_sound_admission;a.frame_zero_prefix=a.frame_zero_prefix or a.frame_zero_owner;a.begin_animation=a.begin_animation or a.frame_zero_prefix;a.output=a.output.resolve();req=derive(Source(a.source));sy=symbols(Path('src/main.sym'))
    if a.frame_sound_admission and a.assets is None:raise ValueError('FRAME_SOUND_NAMESPACE_REQUIRED')
    namespace=None
    if a.frame_sound_admission:
        from source_pcm8_namespace import compile_namespace
        manifest=json.loads((a.assets/'report.json').read_text())
        namespace,pcm_metadata,pcm_payload=compile_namespace(Source(a.source),manifest)
    onpain_requirements=None
    if a.finish_uninitialized_onpain:
        from source_uninitialized_onpain import derive as derive_onpain
        onpain_requirements=derive_onpain(Source(a.source))
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
        for row_index,c in enumerate(rows):
            c['frozen']=(-3,0,1)[row_index%3]
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
        if a.frame_sound_admission:
            from source_sound_admission_native import emit as admit_sound
            from source_sound_pcm8_descriptors_native import emit as bind_pcm
            from source_frame_sound_admission_native import emit as frame_sound
            from m4_animation_init_native import luav
            owner,request,channels,lengths,bases=0x413000,0x413020,0x413100,0x4132e0,0x413310
            frame_table=next(data for bank,at,data in tables if bank==60 and at==0)
            assert hashlib.sha256(frame_table).hexdigest()==manifest['source_frame_table_sha256']
            meta_at=max(at+len(data)for bank,at,data in tables if bank==58);meta_at=(meta_at+1)&~1
            assert meta_at+len(pcm_metadata)<=32768
            tables.append((58,meta_at,pcm_metadata));meta=0x3a8000+meta_at
            kw['append']+=admit_sound(request,channels,sy)+bind_pcm(request,channels,lengths,bases,meta,sy)+frame_sound(owner,request,meta,sy)
            consume=''
            for i in range(2):consume+=f''' ldx #1
 ldy #0
 jsl FrameSound_Admit
 bcc PainSoundAdmitGood{i}
 jmp ModelPipeline_EntryBad
PainSoundAdmitGood{i}:
.a16
.i16
'''
            consume+=f'''PainSoundBeforeAck:
.a16
.i16
 nop
 ldx #1
 ldy #0
 jsl FrameSound_Ack
 bcc PainSoundAckGood
 jmp ModelPipeline_EntryBad
PainSoundAckGood:
.a16
.i16
 jsl {sy['SourceFrameOwner4086_Run']}
 bcc PainSoundFrameGood
 jmp ModelPipeline_EntryBad
PainSoundFrameGood:
.a16
.i16
 cmp #0
 beq PainSoundFrameZero
 jmp ModelPipeline_EntryBad
PainSoundFrameZero:
.a16
.i16
 jsl {sy['SourceAnimationInit4086_Ack']}
 bcc PainSoundAnimationGood
 jmp ModelPipeline_EntryBad
PainSoundAnimationGood:
.a16
.i16
'''
            if a.pain_flags:
                from source_set_pain_flags_native import emit as flags
                from source_current_colourmap import layout as palette_layout
                pal=palette_layout()
                kw['append']+=flags(work,req,pal,sy)
                for i in range(2):consume+=f''' ldx #1
 ldy #0
 jsl SetPainFlags_Run
 bcc PainFlagsGood{i}
 jmp ModelPipeline_EntryBad
PainFlagsGood{i}:
.a16
.i16
'''
                consume+='PainFlagsComplete:\n.a16\n.i16\n nop\n'
                if a.finish_uninitialized_onpain:
                    from source_uninitialized_onpain import emit as finish_pain
                    kw['append']+=finish_pain(work,onpain_requirements,sy)
                    for i in range(2):consume+=f''' ldx #1
 ldy #0
 jsl SetPainFinish_Run
 bcc PainFinishGood{i}
 jmp ModelPipeline_EntryBad
PainFinishGood{i}:
.a16
.i16
 cmp #1
 beq PainFinishReturn{i}
 jmp ModelPipeline_EntryBad
PainFinishReturn{i}:
.a16
.i16
'''
                    consume+='PainFinishComplete:\n.a16\n.i16\n nop\n'
            assert kw['append'].count(needle)==1;kw['append']=kw['append'].replace(needle,consume+needle)
            original_hook=kw.get('rom_transform')
            def install_pcm(raw,linked):
                if original_hook:original_hook(raw,linked)
                start=namespace['cpu_base']-0xc00000;end=start+len(pcm_payload)
                assert raw[start:end]==bytes(end-start);raw[start:end]=pcm_payload
            kw['rom_transform']=install_pcm
            lua='local soundSymbols='+luav({k:v for k,v in sy.items()if k.startswith('SourceSoundChannels4086_')})+'\nfor k,v in pairs(soundSymbols)do sy[k]=v end\n'+lua
            init=f''' for i=0,479 do put({channels}+i,0,1)end
 for i=0,95 do put(0x7eff88+i,0,1);put({lengths}+i,0,1)end
 for i=0,63 do put({owner}+i,0,1)end
 put({owner},0xb63d);put({request},0xb63b);put({request}+12,4096,4);put({request}+16,64,4);put({request}+20,64,4);put({request}+30,0xb63c)
 put(sy.SourceSoundChannels4086_Ready,0xb63a);put(sy.SourceSoundChannels4086_Count,12)
'''
            if a.pain_flags:
                init+=f''' put(0x42e000+c.slot*40,c.frozen,4);put(0x42e004+c.slot*40,0x12345678,4)
 put(sy.SourceFreeze4086_Ready,0xb5df);put(sy.SourcePhysicsState4086_Ready,0xb61c);put(sy.SourceDamageEffectsState4086_Ready,0xb62f)
 put(0x437e10+c.slot*20,0xb5fb);put(0x7ef114+c.slot*24,0xb62f)
'''
                from m4_animation_init_native import luav
                lua='local flagSymbols='+luav({k:v for k,v in sy.items()if k.startswith(('SourceFreeze4086_','SourcePhysicsState4086_','SourceDamageEffectsState4086_'))})+'\nfor k,v in pairs(flagSymbols)do sy[k]=v end\n'+lua
                lua=lua.replace('local ranges={','local ranges={{0x42e000,5120},{0x42d800,2048},{0x7ef100,3072},{0x437e00,2560},')
                lua=lua.replace(f'word({work}+2)~=3',f'word({work}+2)~='+str(7 if a.finish_uninitialized_onpain else 6))
                expected=f''' local fl=0x43eb00+c.slot*32
 for _,off in ipairs({{0,8,12,16,20}})do value(fl+off,0,4)end
 value(fl+4,c.pain_requested=={req['grabbed']} and 0 or 1,4)
 value(0x42d800+c.slot*16,0,4);value(0x7ef100+c.slot*24,0,4);value(0x437e00+c.slot*20,0,4);value(0x40c058+c.slot*96,0,4)
 value(0x42e000+c.slot*40,0,4);value(0x42e004+c.slot*40,0,4)
'''
                lua=lua.replace(' local n=0;for a,v in pairs(before)',expected+' local n=0;for a,v in pairs(before)')
                kw['probes'].update(FLAGSFINAL='PainFlagsComplete',FLAGSFAULT='SetPainFlags_Bad',FLAGSCURRENT='CurrentPalette_Run')
                lua+='''\nlocal restoreCalls=0
emu.addMemoryCallback(function()restoreCalls=restoreCalls+1 end,emu.callbackType.exec,FLAGSCURRENT,FLAGSCURRENT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];emu.log("PAINFLAGSFAULT|"..word(INDEX).."|"..word(sy.SourceFreeze4086_Ready))end,emu.callbackType.exec,FLAGSFAULT,FLAGSFAULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];emu.log("PAINFLAGSDONE|"..word(INDEX).."|"..word(0x42e000+c.slot*40).."|"..word(0x42e004+c.slot*40).."|"..restoreCalls);restoreCalls=0 end,emu.callbackType.exec,FLAGSFINAL,FLAGSFINAL,emu.cpuType.snes,mt)
'''
            anchor=' before={};for _,r in ipairs(ranges)';assert lua.count(anchor)==1;lua=lua.replace(anchor,init+anchor)
            lua=lua.replace('word(sy.SourceAnimationInit4086_State)~=1','word(sy.SourceAnimationInit4086_State)~=2')
            lua=lua.replace('word(sy.SourceUpdateFrame4086_State)~=1 or word(sy.SourceUpdateFrame4086_Pending)~=(2)','word(sy.SourceUpdateFrame4086_State)~=2 or word(sy.SourceUpdateFrame4086_Pending)~=0')
            lua=lua.replace('word(sy.SourceSelf4086_Active)~=1 or word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*c.slot','word(sy.SourceSelf4086_Active)~=0 or word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*((c.slot+1)%128)')
            guards=re.findall(r'^(FrameSound_Guard\d+):',kw['append'],re.M)
            for i,n in enumerate(guards):kw['probes']['SG'+str(i)]=n
            kw['probes'].update(SOUNDFAULT='FrameSound_Bad',SOUNDADMISSIONFAULT='SoundAdmission_Bad',SOUNDDESCRIPTORFAULT='SoundPCM8Descriptor_Bad')
            lua+='\nlocal lastSoundGuard=-1\nfor i,pc in ipairs({'+','.join('SG'+str(i)for i in range(len(guards)))+'})do emu.addMemoryCallback(function()lastSoundGuard=i end,emu.callbackType.exec,pc,pc,emu.cpuType.snes,mt)end\n'
            lua+='\nemu.addMemoryCallback(function()emu.log("PAINSOUNDFAULT|"..word(INDEX).."|"..lastSoundGuard.."|"..word(0x413002).."|"..word(0x413022).."|"..word(sy.SourceFrameEffectPlan4086_Service).."|"..word(sy.SourceFrameEffectPlan4086_Acknowledged))end,emu.callbackType.exec,SOUNDFAULT,SOUNDFAULT,emu.cpuType.snes,mt)\n'
            lua+='emu.addMemoryCallback(function()emu.log("PAINSOUNDADMISSIONFAULT|"..word(INDEX))end,emu.callbackType.exec,SOUNDADMISSIONFAULT,SOUNDADMISSIONFAULT,emu.cpuType.snes,mt)\n'
            lua+='emu.addMemoryCallback(function()emu.log("PAINSOUNDDESCRIPTORFAULT|"..word(INDEX))end,emu.callbackType.exec,SOUNDDESCRIPTORFAULT,SOUNDDESCRIPTORFAULT,emu.cpuType.snes,mt)\n'
            kw['probes'].update(SOUNDADMITTED='PainSoundBeforeAck',SOUNDDONE='PainSoundAnimationGood')
            lua+='''\nemu.addMemoryCallback(function()emu.log("PAINSOUNDADMITTED|"..word(INDEX).."|"..word(0x413002).."|"..word(0x413022).."|"..word(0x413038).."|"..word(0x413024).."|"..word(sy.SourceFrameEffectPlan4086_Service).."|"..word(sy.SourceFrameEffectPlan4086_Acknowledged))end,emu.callbackType.exec,SOUNDADMITTED,SOUNDADMITTED,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local b={};for i=0,479 do b[#b+1]=string.format("%02x",emu.read(0x413100+i,mt))end;emu.log("PAINSOUNDDONE|"..word(INDEX).."|"..word(0x413002).."|"..word(sy.SourceAnimationInit4086_State).."|"..word(sy.SourceUpdateFrame4086_State).."|"..word(sy.SourceUpdateFrame4086_Pending).."|"..table.concat(b))end,emu.callbackType.exec,SOUNDDONE,SOUNDDONE,emu.cpuType.snes,mt)
'''
        if a.finish_uninitialized_onpain:
            kw['probes']['PAINFINISH']='PainFinishComplete'
            lua+='\nemu.addMemoryCallback(function()emu.log("PAINFINISHED|"..word(INDEX).."|"..word('+str(work+2)+').."|"..emu.getState()["cpu.a"])end,emu.callbackType.exec,PAINFINISH,PAINFINISH,emu.cpuType.snes,mt)\n'
        raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
        if a.finish_uninitialized_onpain:
            finished=[l.split('PAINFINISHED|')[1]for l in log.splitlines()if'PAINFINISHED|'in l]
            reporter.check('source uninitialized onpain completes set_pain and returns one without replaying frame or flags',finished==[str(i)+'|7|1'for i in range(len(rows))])
        if a.pain_flags:
            flags_done=[l.split('PAINFLAGSDONE|')[1]for l in log.splitlines()if'PAINFLAGSDONE|'in l]
            # Two palette reset calls belong to model transition; only frozen
            # source pain adds the third, and a painflags retry adds none.
            reporter.check('literal painflags clear frozen/deadline unconditionally and restore map only for frozen truth',flags_done==[f'{i}|0|0|'+str(2+int(c['frozen']!=0))for i,c in enumerate(rows)])
        if a.frame_sound_admission:
            before=[l.split('PAINSOUNDADMITTED|')[1]for l in log.splitlines()if'PAINSOUNDADMITTED|'in l]
            after=[l.split('PAINSOUNDDONE|')[1]for l in log.splitlines()if'PAINSOUNDDONE|'in l]
            wanted=[];wanted_after=[]
            for i,c in enumerate(rows):
                index=manifest['namespace'].index(c['pain_sound']);asset=next(r for r in manifest['compiled']if r['sound_index']==index)
                wanted.append(f'{i}|1|2|1|{index}|9|0')
                channel=bytearray(480);struct.pack_into('<10I',channel,440,1,0,index,0,1,64,64,1,(44%asset['normalized_frames'])*4096,4096)
                wanted_after.append(f'{i}|2|2|2|0|'+channel.hex())
            reporter.check('actual pain SOUND commits once under retry before its native cursor acknowledgement',before==wanted)
            reporter.check('exact logical rows, frame completion and animation acknowledgement follow source SOUND admission',after==wanted_after)
            (folder/'pain-sound-observations.json').write_text(json.dumps(dict(admitted=before,completed=after,expected_admitted=wanted,expected_completed=wanted_after),indent=2)+'\n')
        calls=[int(l.split('PAINCACHE|')[1])for l in log.splitlines()if'PAINCACHE|'in l]
        reporter.check('selection retries and three invalid requests recover after real native model/cache services',calls==[i for i in range(len(rows))for _ in range(7 if a.begin_animation else 6)])
        if a.begin_animation:
            calls=[int(l.split('PAINBEGIN|')[1])for l in log.splitlines()if'PAINBEGIN|'in l]
            reporter.check('real animation begins once and retains frame-zero debt under retry',calls==[i for i in range(len(rows))for _ in range(5 if a.pain_flags else 4 if a.frame_zero_prefix else 2)])
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

    if a.finish_uninitialized_onpain:
        r.update(schema='BYOR_SET_PAIN_UNINITIALIZED_ONPAIN_NATIVE_V1',source_set_pain_bound=True,source_pain_flags_bound=True,source_unfreeze_bound=True,source_onpain_uninitialized_branch_bound=True,onpain_requirements=onpain_requirements,source_onpain_initialized_branch_bound=False,full_set_pain_for_closed_source_capability=True,source_set_pain_return=1,source_sound_admission_bound=True,source_frame_completion_bound=True,production_SPC_consumption_bound=False,production_memory_lease=False,full_damage_callback_bound=False)
        path.write_text(json.dumps(r,indent=2)+'\n')
    elif a.pain_flags:
        r.update(schema='BYOR_SET_PAIN_FLAGS_AFTER_FRAME_NATIVE_V1',source_pain_flags_bound=True,source_unfreeze_bound=True,source_colourmap_restore_conditional=True,source_freeze_deadline_clear_unconditional=True,painflags_once_under_retry=True,actual_source_frame_completion=True,actual_source_sound_admission=True,onpain_pending=True,onpain_bound=False,production_SPC_consumption_bound=False,production_memory_lease=False)
        path.write_text(json.dumps(r,indent=2)+'\n')
    elif a.frame_sound_admission:
        r.update(schema='BYOR_SET_PAIN_FRAME_SOUND_ADMISSION_NATIVE_V1',actual_source_sound_admission=True,source_sound_retry_once=True,actual_source_frame_completion=True,actual_animation_initializer_ack=True,full_PCM_namespace_in_ROM=True,private_source_sound_controls=[0x413000,0x413040],private_logical_channels=[0x413100,0x4132e0],private_PCM_descriptors=[0x4132e0,0x413340],production_SPC_consumption_bound=False,production_memory_lease=False,pain_flags_applied=False)
        path.write_text(json.dumps(r,indent=2)+'\n')
    elif a.frame_zero_owner:
        r.update(schema='BYOR_SET_PAIN_FRAME_ZERO_OWNER_NATIVE_V1',actual_source_animation_script=True,actual_source_frame_motion=True,actual_source_frame_effect_owner=True,source_audio_ticket_pending=True,source_audio_bound=False,pain_flags_applied=False)
        path.write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':main()
