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
    for name in ('inventory', 'build'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--set', choices=('Easy', 'Normal', 'Hard', 'Bonus'), required=True,
                         dest='source_set')
        cmd.add_argument('--source', type=Path,
                         default=ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak',
                         help='configured original BOR source PAK')
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
    from normal_coverage import PAK, inventory
    # The current production media/runtime adapter is source-profile bound.
    # Never accept another PAK while secretly building the configured source.
    if args.source.resolve() != PAK.resolve():
        parser.error('SOURCE_PROFILE_UNCONFIGURED: this build adapter requires the '
                     'original BOR PAK; other games require explicit capability/media bindings')
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
