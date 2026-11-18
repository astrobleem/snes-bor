from pathlib import Path
p=Path('E:/gh/snes-bor/src/core/source_packet_geometry.pasm');d=Path('bor-v138-source');assert p.read_bytes()==(d/(p.name+'.v137r1')).read_bytes();p.write_bytes((d/p.name).read_bytes());print('Applied reversible private-position fast path and guarded late publication; media/world/resources untouched.')
