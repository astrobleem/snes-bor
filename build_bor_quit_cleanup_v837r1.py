"""Bounded linked build of v574, restoring borrowed generated outputs."""
from pathlib import Path
import contextlib, hashlib, io, json, os, shutil, sys, traceback
ROOT=Path('E:/gh/snes-bor'); W=Path(__file__).resolve().parent
RUN=W/'BOR-QUIT-CLEANUP-v837r1-build'
PRE=W/'bor-actor-cache-validation-v418-20261102/preimages'
TARGET=ROOT/'build/byor-easy'
O={'src/core/source_visual_production.pasm': '16372157c4f11ffb4ef7fdb73180cdbfc505eafbc4bd9c6f983b4e3a7f930259', 'src/core/source_packet_geometry.pasm': 'da85090285f6d08b426167adb8da1621517bed2e797f457b49b4211026e3f3e6', 'src/core/source_attack_owned_v606.pasm': 'e35675ec4524ac3cac9d5f5f7335ec42fe71e868c7622c1bfb86039776da9035', 'src/core/source_attack_before_compose.pasm': '0fec90d8126a6f6b7bb8dbd128833cd284881090694f18bca130980ef5281f5c', 'src/core/source_attack_template_v598.pasm': 'fdc96087049d49950c99aed1c8d1cdecc01b751a2d2a8b2e7a6242da87ab660b', 'src/core/source_fp_window.pasm': '4e92fb29c8fcea0574d2d9978b3ac13be5025c8c0e9d0da5fa2ec291b6382131', 'src/core/source_attack_prewarm.pasm': '3a3acffc613449d81d13ebdda58235d80efb9233da4b00b94014304b1eb2f141', 'src/core/source_attack_before_compose_v583.pasm': 'ca9725887395c19bf8ddb68e1627d737a40fef62e00bcfa7e1300e0ddd270f31', 'src/core/source_rom_payloads.pasm': '215fd017bace3662dfe88851026af04bd435694e0cb9e4a66a4c41b66482472b', 'src/main.pasm': '48d7033db5733c3be330a90f0f16962186f304eb9a0aba661f5b3f92266c50e1', 'src/core/source_prefetch_plan.pasm': '0a1b96e006ffe09e6a2886a121a85527a04fec4d68a6c38b702e5b820db48752', 'src/core/audio_idle_wait.pasm': 'f6e2a8902b57746256e2745636f2fb7e66c30d2b1f1851547ea623ec065d0d0f', 'src/core/source_original_packet.pasm': '590e673baaf2c5446bdd7076610ac7b52496529a5248372630383a8cd3c9e2c5', 'src/core/source_reserved_idle.pasm': 'e2f2548b7aba2f323b78037f7c329845eeb43c5d20ba7b1564d76f2da1e9ae1d', 'src/core/source_second_idle.pasm': 'b16f36a4ded06c243158ab3181fffc8215244f3b41076b6cc2da39dc909edfad', 'src/core/dma.pasm': '9fb0038cc30fceb34064003aa9a60ef3872e4f68ef704cbbe60ba1e48f58ce45', 'src/core/hud_2p.pasm': '42aa74faa3affac54100a8799ecab139908a86692c5f734d8ce339c781a94c97', 'src/core/player2_context.pasm': 'b9718b62ba2bba435a7e8ae21bddd33e1910b17da59660ee2cb4eb856625ad48', 'tools/verify/actor_s7_persistent_worker.py': '32c5e77b7610380bbab630f22f6c6e351c3707f9625e050ec10e5f0296befb33', 'src/core/pausemenu.pasm': 'b845574d1c9e50d89d5c923830ff446690f6098f06fafc437fbd7f9be50ab08c'}
M=json.loads((W/'bor-precompose-v583-manifest.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def free():return {d:shutil.disk_usage(d+':/').free for d in ('C','E')}
def main():
 assert not RUN.exists() and min(free().values())>16*1024**3
 for n,d in O.items():assert sha(ROOT/n)==d,n
 V0=json.loads((W/'bor-attack-template-v598-manifest.json').read_text())
 V=json.loads((W/'bor-attack-owned-v606-manifest.json').read_text())
 assert V['status']=='INSTALLED'
 for n,d in M['after'].items():
  if n not in V['after'] and n not in V0['after']:assert sha(ROOT/n)==O.get(n.replace(chr(92),'/'),d),n
 for n,d in V0['after'].items():
  if n not in V['after']:assert sha(ROOT/n)==O.get(n.replace(chr(92),'/'),d),n
 for n,d in V['after'].items():assert sha(ROOT/n)==O.get(n.replace(chr(92),'/'),d),n
 for n,d in M['new'].items():assert sha(ROOT/n)==O.get(n.replace(chr(92),'/'),d),n
 sys.path[:0]=[str(ROOT),str(ROOT/'tools/verify'),str(ROOT/'tools/bor_compile')]
 from pcm_runtime import preflight_immutable_pcm, assert_no_pcm_copy
 from build_normal_sa1_candidate import build_from_source
 preflight_immutable_pcm(ROOT/'distribution',TARGET);assert_no_pcm_copy(ROOT/'distribution',TARGET)
 pcm={p.name:(p.stat().st_ino,p.stat().st_nlink,p.stat().st_size) for p in TARGET.glob('bor-*.pcm')}
 msu=sha(TARGET/'bor.msu')
 out=[ROOT/'src'/('main'+s) for s in ('.bin','.sym','.pansy')]
 out += [p for p in TARGET.iterdir() if p.is_file() and p.suffix!='.pcm' and p.name!='bor.msu']
 assert sum(p.stat().st_size for p in out)<256*1024**2
 for p in out:
  old=PRE/p.relative_to(ROOT)
  assert old.is_file() and sha(p)==sha(old) and p.stat().st_nlink==1,str(p)
 RUN.mkdir();(RUN/'temp').mkdir();(RUN/'product').mkdir()
 os.environ.update(PYTHONDONTWRITEBYTECODE='1',DOTNET_CLI_HOME=str(RUN/'dotnet-home'),TEMP=str(RUN/'temp'),TMP=str(RUN/'temp'))
 state={'status':'STARTED','free_before':free(),'pcm_before':pcm,'msu_before':msu,'target_before':sha(TARGET/'bor.sfc'),'restored':False}
 def save():(RUN/'result.json').write_text(json.dumps(state,indent=2)+'\n')
 save();captured=io.StringIO()
 try:
  os.chdir(ROOT)
  with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
   build_from_source(TARGET,TARGET,in_place=True,relink_source=True,source_set='Easy')
  bridge=[line for line in (ROOT/'src/main.sym').read_text().splitlines() if line.endswith(' SourcePacket_UnrolledBudgetBridge')]
  assert len(bridge)==1 and bridge[0].startswith('10:')
  assert int(bridge[0][3:7],16)<=0xFFFC,bridge[0]
  state['bank10_bridge']=bridge[0]
  state['candidate_rom']=sha(TARGET/'bor.sfc')
  assert sha(TARGET/'bor.msu')==msu
  for n,p in [('bor.sfc',TARGET/'bor.sfc'),('main.sym',ROOT/'src/main.sym'),('world.sym',TARGET/'world.sym')]:shutil.copy2(p,RUN/'product'/n)
  state['status']='LINKED_CANDIDATE'
 except BaseException:
  state['status']='BUILD_FAILED';state['exception']=traceback.format_exc()
 finally:
  (RUN/'build.log').write_text(captured.getvalue())
  for p in out:
   old=PRE/p.relative_to(ROOT)
   if sha(p)!=sha(old):shutil.copy2(old,p)
   assert sha(p)==sha(old),str(p)
  assert sha(TARGET/'bor.msu')==msu
  assert {p.name:(p.stat().st_ino,p.stat().st_nlink,p.stat().st_size) for p in TARGET.glob('bor-*.pcm')}==pcm
  state['restored']=True;state['free_after']=free();save()
 print(json.dumps(state))
 if state['status']!='LINKED_CANDIDATE':raise RuntimeError('linked build failed')
if __name__=='__main__':main()
