#!/usr/bin/env python3
"""BYOR — Bring Your Own Rage: supported BOR source to the SNES runtime."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'tools/bor_compile'), str(ROOT / 'tools/audio')]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'inventory', 'build'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--set', required=name != 'inspect',
                         dest='source_set')
        cmd.add_argument('--source', type=Path,
                         default=ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak',
                         help='source PACK archive to inspect or compile')
        cmd.add_argument('--output', type=Path, required=True,
                         help='inventory JSON file or new candidate directory')
        if name == 'build':
            cmd.add_argument('--reuse-audio-from',
                             help='Git ref with unchanged pinned audio inputs')
            cmd.add_argument('--source-image', type=Path,
                             help='resume a generated source image in the output directory')
            cmd.add_argument('--repack-media', action='store_true',
                             help='repack regenerated media while resuming the same source image')
    args = parser.parse_args(argv)
    from source_profile import inspect, write_survey, Source, document, discover, sha, resolve_profile
    try:
        source = Source(args.source)
        documents = {k: document(source, n) for k, (n, _) in source.index.items()
                     if k.endswith('.txt')}
        discovered = discover(source, documents)
        source_hash = sha(args.source.read_bytes())
    except (OSError, ValueError) as error:
        parser.error('SOURCE_READ_FAILED: ' + str(error))
    if args.command == 'inspect':
        report = inspect(args.source)
        matrix, summary = write_survey(report, args.output)
        print(json.dumps(dict(status=report['status'], source_sha256=source_hash,
            sets=[dict(id=s['id'], name=s['name'], ifcomplete=s['ifcomplete']) for s in report['sets']],
            survey=str(args.output), capability_matrix=str(matrix), summary=str(summary)), indent=2))
        return 0
    names = [s['name'] for s in discovered['sets']]
    if args.source_set not in names:
        parser.error(f'SOURCE_SET_UNKNOWN: {args.source_set!r}; discovered sets: {names}')
    from normal_coverage import PAK, inventory
    # The current production media/runtime adapter is source-profile bound.
    # Never accept another PAK while secretly building the configured source.
    profile = resolve_profile(source_hash)
    if profile is None:
        report = inspect(args.source)
        if args.command == 'inventory':
            write_survey(report, args.output)
            print(json.dumps(dict(status='CAPABILITIES_UNRESOLVED',
                source_sha256=source_hash, source_set=args.source_set,
                capability_counts=report['capability_counts'], output=str(args.output)), indent=2))
            return 2
        blockers = sorted(report['resource_limits'], key=lambda r: -r['required_colors']) + [r for r in report['capability_matrix'] if r['blocks_compilation']]
        examples = []
        seen = set()
        for row in blockers:
            code = row.get('code') or row['classification'] + ':' + row['directive']
            if code in seen:
                continue
            seen.add(code)
            examples.append(dict(code=code, source_path=row['source_path'], line=row['line'],
                value=row['values'], resolution=row['proposed_generic_resolution'],
                **({k: row[k] for k in ('required_colors', 'available_colors', 'minimum_palettes', 'available_palettes')}
                   if 'required_colors' in row else {})))
        print(json.dumps(dict(status='BUILD_CAPABILITY_GAPS', source_sha256=source_hash,
            source_set=args.source_set, diagnostics=examples, candidate_produced=False), indent=2), file=sys.stderr)
        return 2
    if args.source.resolve() != (ROOT / profile['canonical_source']).resolve():
        parser.error('SOURCE_MEDIA_LOCATION_UNBOUND: identical original source at an alternate '
                     'path is inspectable; the reviewed legacy media builder still requires its canonical location')
    if args.command == 'inventory':
        report = inventory(source_set=args.source_set)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return int(report['structural_coverage']['status'] != 'COMPLETE')
    from build_normal_sa1_candidate import build
    if args.source_image:
        if args.reuse_audio_from:
            parser.error('--source-image already contains compiled media; no audio reuse ref is needed')
        from build_normal_sa1_candidate import build_from_source
        options=dict(in_place=True,relink_source=True,source_set=args.source_set)
        if args.repack_media:options['repack_media']=True
        candidate, report = build_from_source(args.output,args.source_image,**options)
    else:
        if args.repack_media:
            parser.error('--repack-media requires --source-image')
        candidate, report = build(args.output, args.reuse_audio_from, source_set=args.source_set)
    print(json.dumps(dict(compiler='BYOR — Bring Your Own Rage', output=str(candidate),
                         source_set=args.source_set, **report['candidate']), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
