"""Recreate accepted derived queues without reading historical dirty inputs.

Owner: source compiler's accepted ten-byte lowering adapter. All candidates
are validated against the hash-pinned accepted MSU before any write occurs.
Default output is a separate tree; --install updates only proven BOR queues.
"""
import argparse
import json
from pathlib import Path

from compiler import ROOT, Source, baseline, compile_project, digest, key
from certify import BASE, MSU_SHA
from environment_semantics import extend_legacy_queue_maps
from compiler import stage


def generate(source, msu_path, sha=MSU_SHA, ref=BASE):
    report,queues=compile_project(source,ref,msu_path,sha)
    if not report['golden_production_pass']:
        raise ValueError('refuse generation: source queues do not reproduce accepted MSU')
    cfg,_=baseline(ref)
    candidates={s['spawn']:queues[key(s['source_level'])] for s in cfg['STAGE_CONFIGS'] if s['family']=='bor-original'}
    return candidates


def install(candidates, root):
    root=Path(root).resolve()
    targets=[]
    for rel,data in candidates.items():
        path=(root/rel).resolve()
        if not path.is_relative_to(root) or not rel.startswith('out/spawn_') or path.name!='spawn_table.bin':
            raise ValueError(f'not an owned derived queue: {rel}')
        targets.append((path,data))
    changed=[]
    for path,data in targets:
        if not path.exists() or path.read_bytes()!=data:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data);changed.append(path.relative_to(root).as_posix())
    return changed


def generate_environment_queues(source, msu_path, ref=BASE):
    # First prove the unchanged legacy candidate against accepted production.
    candidates = generate(source, msu_path, ref=ref)
    cfg, _ = baseline(ref)
    for s in cfg['STAGE_CONFIGS']:
        if s['family'] == 'bor-original':
            candidates[s['spawn']] = extend_legacy_queue_maps(stage(source, s['source_level']), candidates[s['spawn']])
    return candidates


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source')
    p.add_argument('--output',type=Path);p.add_argument('--install',action='store_true')
    p.add_argument('--environment-v1',action='store_true',help='derive S4 selectors after pinned legacy reproduction')
    p.add_argument('--msu',type=Path,default=ROOT/'distribution/bor.msu');args=p.parse_args()
    if bool(args.output)==args.install: p.error('choose either --output DIR or --install')
    generator = generate_environment_queues if args.environment_v1 else generate
    candidates=generator(Source(args.source),args.msu)
    root=ROOT if args.install else args.output
    changed=install(candidates,root)
    print(json.dumps(dict(count=len(candidates),changed=changed,sha256={p:digest(b) for p,b in candidates.items()}),indent=2))


if __name__=='__main__': main()
