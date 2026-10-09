"""Isolated actual source 1UP audio acceptance before lives/score publication."""
import argparse,hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
import m4_source_audio_rom_native as parent
from compiler import Source
from actor_s5_entity_fixture import symbols
from source_sound_namespace_4086 import derive
from source_score_extra_life_native import emit


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for k in('rom','assets','packed','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();sy=symbols(Path('src/main.sym'));ns=derive(Source(a.source));sample=ns['specials']['SAMPLE_1UP']['sound_index'];assert sample>=0;original=parent.run_fixture;observed={}
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw):
  anchor=' lda #ASSETINDEX\n jsl STARTSOURCE' # parent has already substituted this asset index
  anchor=f' lda #{sample}\n jsl STARTSOURCE';assert kw['append'].count(anchor)==1
  kw['append']=kw['append'].replace(anchor,' jsl ScoreExtraLifeProbe')
  probe='ScoreExtraLifeProbe:\n.a16\n.i16\n php\n rep #$39\n phx\n phy\n'
  for name,value,n in(('Ready',0xb631,2),('StatsReady',0xb633,2),('NoScriptsReady',0xb632,2),('LifeScore',50000,4),('ScriptMask',0,2),('Index',0,4),('Add',70,4)):
   for off in range(0,n,2):probe+=f' lda #{(value>>(8*off))&65535}\n sta.l {sy["SourceScore4086_"+name]}+{off}\n'
  for at,value in((0x7fbfa0,49999),(0x7fbfb0,3)):
   for off in(0,2):probe+=f' lda #{(value>>(8*off))&65535}\n sta.l {at}+{off}\n'
  probe+=f' jsl {sy["SourceScore4086_Execute"]}\n bcs ScoreExtraLifeProbe_Bad\n lda.l {sy["SourceScore4086_Status"]}\n cmp #1\n bne ScoreExtraLifeProbe_Bad\n jsl ScoreExtraLife_Resume\n bcs ScoreExtraLifeProbe_Bad\n lda.l {sy["SourceScore4086_Status"]}\n bne ScoreExtraLifeProbe_Bad\n ply\n plx\n plp\n clc\n rtl\nScoreExtraLifeProbe_Bad:\n.a16\n.i16\n ply\n plx\n plp\n sec\n rtl\n'
  kw['append']+=probe+emit(sy,sample)
  kw.setdefault('probes',{})['LIFEACCEPT']='ScoreExtraLife_SoundAccepted'
  kw.setdefault('bindings',{}).update(UPAUDIO='SourceAudio_StartPreparedNear')
  lua+=f'''
local mt=emu.memType.snesMemory
local function upword(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
emu.addMemoryCallback(function()if upword({sy['SourceScore4086_Ready']})==0xb631 then emu.log('UPORDER|audio|'..upword(0x7fbfb0)..'|'..upword(0x7fbfa0))end end,emu.callbackType.exec,UPAUDIO,UPAUDIO,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('UPORDER|life|'..upword(0x7fbfb0)..'|'..upword(0x7fbfa0))end,emu.callbackType.exec,LIFEACCEPT,LIFEACCEPT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('UPORDER|done|'..upword(0x7fbfb0)..'|'..upword(0x7fbfa0)..'|'..upword({sy['SourceScore4086_Status']}))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  events=[l.split('UPORDER|')[1].strip()for l in log.splitlines()if'UPORDER|'in l];wanted=['audio|3|49999','life|3|49999','done|4|50069|0'];reporter.check('actual ASAD acceptance precedes life increment and final score publication',events==wanted);observed['events']=events;return raw,log
 args=['m4_source_audio_rom_native.py','--rom',str(a.rom),'--assets',str(a.assets),'--packed',str(a.packed),'--output',str(a.output),'--sound-index',str(sample)]
 with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_SCORE_EXTRA_LIFE_ASAD_NATIVE_V1',source_1up_binding=ns['specials']['SAMPLE_1UP'],source_namespace_sha256=hashlib.sha256(json.dumps(ns,sort_keys=True).encode()).hexdigest(),source_score_order_events=observed['events'],capability='ISOLATED_IDLE_SINGLE_ASAD_SOUND_CHILD',concurrent_source_mixer_bound=False,source_effect_volume_projection_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False);path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
