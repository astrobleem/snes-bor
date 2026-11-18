from pathlib import Path
r=Path('E:/gh/snes-bor');d=Path('bor-v140-source')
for name in ('source_packet_geometry.pasm','source_original_packet.pasm'):assert(r/'src/core'/name).read_bytes()==(d/(name+'.v139')).read_bytes()
for name in ('source_packet_geometry.pasm','source_original_packet.pasm'):(r/'src/core'/name).write_bytes((d/name).read_bytes())
print('Applied exact source-copy-race repair; original failed-enqueue resource-retirement path retained. No media or world writes.')
