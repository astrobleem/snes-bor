from pathlib import Path
import hashlib,json
p=Path('E:/gh/snes-bor/src/core/source_visual_production.pasm');d=Path('bor-v137-source');before=d/'source_visual_production.pasm.v135r2';assert p.read_bytes()==before.read_bytes()
p.write_bytes((d/p.name).read_bytes());print(json.dumps(dict(applied=True,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),PCM_MSU_modified=False,beforeimage=str(before))))
