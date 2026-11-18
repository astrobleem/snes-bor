from pathlib import Path
r=Path('E:/gh/snes-bor');d=Path('bor-v141-source')
for name in ('source_visual_production.pasm','source_visual_actor_completed.pasm'):assert(r/'src/core'/name).read_bytes()==(d/(name+'.v140')).read_bytes()
assert not(r/'src/core/source_critical_completion.pasm').exists()
for name in ('source_visual_production.pasm','source_visual_actor_completed.pasm','source_critical_completion.pasm'):(r/'src/core'/name).write_bytes((d/name).read_bytes())
print('Applied bounded critical-player completion scheduling; normal palette/DMA/OAM/retirement path retained, no media/world changes.')
