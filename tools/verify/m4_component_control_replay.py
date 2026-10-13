"""Replay a retained native component control without copying/linking media.

The retained ROM, compiler inputs and expected source pictures are immutable.
All new observers, screenshots and reports go to a fresh output directory.
This does not certify a live MOTU world or compositor.
"""
import argparse
import hashlib
import json
from pathlib import Path

from actor_s5_entity_fixture import symbols
from m4_component_production_sequence import verify


def retained_inputs(retained):
    retained=Path(retained).resolve()
    compiled=json.loads((retained/'compiled.json').read_text())
    prior=json.loads((retained/'result.json').read_text())
    rom=retained/'proof.sfc';raw=rom.read_bytes()
    if not prior.get('pass') or hashlib.sha256(raw).hexdigest()!=prior['rom_sha256']:
        raise ValueError('CONTROL_ROM_HASH_OR_PRIOR_FAILURE')
    for path,files in compiled['resources'].get('input_hashes',{}).items():
        for name,digest in files.items():
            if hashlib.sha256((Path(path)/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('CONTROL_INPUT_HASH:'+str(path)+'/'+name)
    return compiled,rom,raw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--symbols',type=Path,default=Path(__file__).resolve().parents[2]/'src/main.sym')
    args=parser.parse_args()
    retained=args.retained.resolve()
    output=args.output.resolve()
    if output.exists():raise ValueError('CONTROL_NEW_OUTPUT_REQUIRED')
    compiled,rom,raw=retained_inputs(retained)
    assets=[Path(p).resolve() for p in compiled['assets']]
    output.mkdir(parents=True)
    verify(raw,compiled['gates'],compiled['resources'],compiled['traces'],assets,rom,
           symbols(args.symbols),output,existing_rom=rom)


if __name__=='__main__':main()
