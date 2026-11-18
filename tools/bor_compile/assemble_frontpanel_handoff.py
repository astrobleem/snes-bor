"""Assemble a flattened, patched snapshot to isolated outputs; never main.bin/sym."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from compiler import ROOT
sys.path.insert(0,str(ROOT))
import build_rom


def run(output):
    output = Path(output).resolve()
    patch = (ROOT/'docs/s8_frontpanel_bg2_hooks.patch').read_text()
    sources = {}
    for section in patch.split('--- a/')[1:]:
        filename = section.splitlines()[0]
        path = ROOT/filename
        text = path.read_text()
        for match in re.finditer(r'^@@[^\n]*\n(.*?)(?=^@@|\Z)',section,re.M|re.S):
            lines = match.group(1).splitlines()
            old = '\n'.join(line[1:] for line in lines if line.startswith(('-', ' ')))
            new = '\n'.join(line[1:] for line in lines if line.startswith(('+', ' ')))
            if text.count(old) != 1:
                raise ValueError(f'isolated patch no longer applies uniquely: {filename}: {old[:60]}')
            text = text.replace(old,new,1)
        sources[path.resolve()] = text
    protected = [ROOT/'src/main.bin',ROOT/'src/main.sym',ROOT/'src/main.pasm',ROOT/'src/core/nmi.pasm']
    before = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    generated = output/'generated'
    def flatten(path):
        path = path.resolve()
        override = generated/path.name
        if path.parent == ROOT/'src/generated' and override.exists(): path = override
        text = sources.get(path)
        if text is None: text = path.read_text(encoding='utf-8-sig')
        lines = []
        for line in text.splitlines():
            include = re.match(r'\s*\.include\s+"([^"]+)"',line)
            binary = re.match(r'(\s*\.incbin\s+)"([^"]+)"(.*)',line)
            if include: lines.append(flatten(path.parent/include[1]))
            elif binary: lines.append(binary[1]+'"'+(path.parent/binary[2]).resolve().as_posix()+'"'+binary[3])
            else: lines.append(line)
        return '\n'.join(lines)+'\n'
    snapshot = output/'fp_candidate_snapshot.pasm'
    snapshot.write_text(flatten(ROOT/'src/main.pasm'),encoding='utf-8')
    command = [build_rom.DOTNET,build_rom.POPPY_DLL,str(snapshot),'-o',str(output/'fp_candidate.bin'),'-s',str(output/'fp_candidate.sym')]
    result = subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
    (output/'assembly.log').write_text(result.stdout+result.stderr)
    after = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    report = dict(exit_code=result.returncode,command=command,protected_before=before,
                  protected_after=after,protected_unchanged=before==after,
                  snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest())
    (output/'assembly_report.json').write_text(json.dumps(report,indent=2)+'\n')
    # Independent ABI/encoding check against the current symbol snapshot.
    # This is NOT a substitute for successful combined layout assembly.
    modules = [ROOT/'src/core'/name for name in ('stage_frontpanel_host.pasm',
        'stage_frontpanel.pasm','stage_frontpanel_bg2.pasm','stage_frontpanel_legacy.pasm')]
    body = '\n'.join(p.read_text() for p in modules)+(generated/'stage_frontpanel_tables.pasm').read_text()
    defined = set(re.findall(r'^\s*([A-Za-z_]\w*)\s*(?:=|:)',body,re.M))
    tokens = set(re.findall(r'\b[A-Za-z_]\w*\b', '\n'.join(line.split(';')[0] for line in body.splitlines())))
    symbols = build_rom._load_poppy_symbols(ROOT/'src/main.sym')
    external = '\n'.join(f'{name} = ${symbols[name]:06X}' for name in sorted(tokens-defined) if name in symbols)
    module_source = '.snes\n'+external+'\n.bank 0\n.org $8000\n'+modules[0].read_text()
    module_source += '\n.bank 18\n.org $8000\n'+'\n'.join(p.read_text() for p in modules[1:])
    module_source += (generated/'stage_frontpanel_tables.pasm').read_text()
    module_path = output/'fp_modules.pasm'
    module_path.write_text(module_source)
    module_result = subprocess.run([build_rom.DOTNET,build_rom.POPPY_DLL,str(module_path),
        '-o',str(output/'fp_modules.bin'),'-s',str(output/'fp_modules.sym')],capture_output=True,text=True,cwd=ROOT)
    (output/'module_assembly.log').write_text(module_result.stdout+module_result.stderr)
    report['module_exit_code'] = module_result.returncode
    report['module_source_sha256'] = hashlib.sha256(module_path.read_bytes()).hexdigest()
    (output/'assembly_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('FP module assembly:',module_result.returncode,module_result.stdout+module_result.stderr)
    print(result.stdout+result.stderr)
    print(json.dumps(report,indent=2))
    assert before == after
    return result.returncode


if __name__ == '__main__': sys.exit(run(sys.argv[1]))
