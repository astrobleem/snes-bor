"""Pain role selection after actual synchronized model/cache services."""
import argparse, hashlib, json, re, struct, sys
from pathlib import Path
from unittest.mock import patch
import m4_model_current_pipeline_native as current
import m4_model_services_pipeline_native as parent
from actor_s5_entity_fixture import symbols
from compiler import Source
from source_foreign_state_layout import layout
from source_set_pain_select_native import derive,emit


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();req=derive(Source(a.source));sy=symbols(Path('src/main.sym'))
    work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='common_idle_controls')
    original=parent.run_fixture
    def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
        nominal=[c for c in rows if not c['fault']]
        rows[:]=[dict(c,pain_type=t)for c in nominal for t in (0,1,19,-1,20,65536)]
        from source_animation_init_4086 import derive as animations
        directory=animations(Source(a.source))['animations']
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
        kw.setdefault('probes',{})['PAINSELECT']='SetPainSelect_Run'
        lua+='\nemu.addMemoryCallback(function()emu.log("PAINCACHE|"..word(INDEX))end,emu.callbackType.exec,PAINSELECT,PAINSELECT,emu.cpuType.snes,mt)\n'
        raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
        calls=[int(l.split('PAINCACHE|')[1])for l in log.splitlines()if'PAINCACHE|'in l]
        reporter.check('selection retries and three invalid requests recover after real native model/cache services',calls==[i for i in range(len(rows))for _ in range(6)])
        return raw,log
    argv=['m4_model_current_pipeline_native.py','--source',a.source,'--rom',str(a.rom),'--output',str(a.output)]
    with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',argv):
        try:current.main()
        except SystemExit as e:
            if e.code not in (None,0):raise
    path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_SET_PAIN_CURRENT_CACHE_NATIVE_V1',pain_selection_requirements=req,actual_mutable_model_cache_queried=True,source_animation_resolve_bound=True,actor_animation_begin_bound=False,source_pain_flags_bound=False,source_unfreeze_bound=False,onpain_bound=False,source_audio_bound=False,full_damage_callback_bound=False,new_foreign_arena_bytes=0)
    path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
