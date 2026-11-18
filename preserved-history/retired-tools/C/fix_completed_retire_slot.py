from pathlib import Path
root=Path(r'E:\gh\snes-bor')
p=root/'src/core/source_visual_production.pasm'
b=p.read_bytes();s=b.decode().replace('\r\n','\n')
old='    tya\n    bne SourceVisual_QueueRetireEntityOffset__completed_done'
assert s.count(old)==1
save=Path(__file__).parent/'bor-completed-packet-20261028/pre-retire-slot-fix.pasm'
assert not save.exists();save.write_bytes(b)
s=s.replace(old,'    txa\n    bne SourceVisual_QueueRetireEntityOffset__completed_done')
p.write_bytes(s.replace('\n','\r\n' if b'\r\n' in b else '\n').encode())
