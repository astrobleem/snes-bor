from pathlib import Path
import sys
R=Path('E:/gh/snes-bor');W=Path(__file__).resolve().parent
p=R/'src/core/source_attack_owned_v606.pasm';s=p.read_bytes();n=b'\r\n' if b'\r\n' in s else b'\n'
a=b'SourceRewarm_ArmGuard7:\n.a16\n.i16\n    lda #0\n    sta.l SourcePrefetch_Cursor'.replace(b'\n',n)
b=b'SourceRewarm_ArmGuard7:\n.a16\n.i16\n    jsl SourceAttackMissing_First\n    nop\n    nop\n    nop'.replace(b'\n',n)
main=R/'src/main.pasm';m=main.read_bytes();nl=b'\r\n' if b'\r\n' in m else b'\n';chunk=nl+(W/'bor_attack_missing_first_v840.pasm').read_text().replace('\n',nl.decode()).encode()
if '--restore' in sys.argv:
 assert s.count(b)==1 and m.endswith(chunk);s=s.replace(b,a);m=m[:-len(chunk)]
else:
 assert s.count(a)==1 and b'SourceAttackMissing_First' not in m;s=s.replace(a,b);m+=chunk
p.write_bytes(s);main.write_bytes(m);print('Updated pressure-recovery cursor only; existing loader and DMA bounds preserved')
