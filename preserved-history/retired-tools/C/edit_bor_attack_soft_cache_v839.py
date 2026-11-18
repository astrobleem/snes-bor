from pathlib import Path
import sys
R=Path('E:/gh/snes-bor');W=Path(__file__).resolve().parent
p=R/'src/core/source_visual_production.pasm';s=p.read_bytes();nl=b'\r\n' if b'\r\n' in s else b'\n'
a=b'    jsr SVActor_ProtectBlocks\n    bcs SourceVisual_AllocateBlock__next8\n    rep #$31\n.a16\n.i16\n    bra SourceVisual_AllocateBlock__claim'.replace(b'\n',nl)
b=b'    jsr SVActor_ProtectBlocks\n    bcs SourceVisual_AllocateBlock__next8\n    jml SourceAttackCache_SoftVictim\n.a16\n.i16'.replace(b'\n',nl)
main=R/'src/main.pasm';m=main.read_bytes();n=b'\r\n' if b'\r\n' in m else b'\n';chunk=n+(W/'bor_attack_soft_cache_v839.pasm').read_text().replace('\n',n.decode()).encode()
restore='--restore' in sys.argv
if restore:
 assert s.count(b)==1 and m.endswith(chunk);s=s.replace(b,a);m=m[:-len(chunk)]
else:
 assert s.count(a)==1 and b'SourceAttackCache_SoftVictim' not in m;s=s.replace(a,b);m+=chunk
p.write_bytes(s);main.write_bytes(m);print('Restored v838 candidate' if restore else 'Applied soft attack-residency preference; all normal pin and fallback rules retained')
