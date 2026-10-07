"""Bounded joint hybrid pixels / ASAD bytes / DSP block traversal proof.

The source sound request and fixed scene are instrumented. This is resource
admission evidence, not live MOTU world, moving compositor or event timing.
"""
import argparse,json,math
from pathlib import Path
from actor_s5_entity_fixture import symbols
from m4_component_production_sequence import build,verify
from m4_projectile_audio_fixture import configure


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('sequence','residency','prepared-sequence','rom','assets','packed','output'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--sound-index',type=int,default=16)
    p.add_argument('--early-packet-staging',action='store_true')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    sy=symbols(Path(__file__).resolve().parents[2]/'src/main.sym')
    manifest=json.loads((a.assets/'report.json').read_text())
    row=next(r for r in manifest['compiled']if r['sound_index']==a.sound_index)
    sink={}
    row,transform,before,closeout=configure(folder,a.assets.resolve(),row['source_path'],prefill=True,
        generic_rom=a.packed.resolve(),external_observer=sink)
    rom,gates,resources,traces,frames=build(a.sequence,a.residency,a.residency/'report.json',
        a.rom.read_bytes(),sy,folder,True,True,True,True,True,True,a.prepared_sequence,True,a.sound_index,a.early_packet_staging)
    raw=bytearray(rom);transform(raw,sy);rom=bytes(raw)
    resources['audio_rom_reservation']=json.loads((a.packed/'report.json').read_text())
    resources['sound_request_instrumented']=True
    (folder/'compiled.json').write_text(json.dumps(dict(resources=resources,gates=gates,
        assets=[str(p)for p in frames],traces=traces),indent=2)+'\n')
    fields=max(120,math.ceil(row['normalized_frames']/(32000*1411/4096)*60.1)+40)
    if fields>200:raise ValueError('JOINT_AUDIO_PROOF_DURATION_BOUND: select a bounded source asset')
    hooks=dict(before=before,closeout=closeout,sample=sink['sample'],assets=a.assets.resolve(),fields=fields,
        env={'MESEN_VOICE_CAPTURE_PATH':str(folder/'voice0.raw'),'MESEN_VOICE_CAPTURE_VOICE':'0',
             'MESEN_VOICE_CAPTURE_ARM_FILE':str(folder/'voice0.raw.arm')})
    print('JOINT_HYBRID_ASAD_COMPILED',flush=True)
    verify(rom,gates,resources,traces,frames,a.rom.resolve(),sy,folder,hooks)


if __name__=='__main__':main()
