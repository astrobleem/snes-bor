"""Package native-computed mixed BRR for a private production transport test.

The aggregate is a proof identity, not an authored WAV namespace admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
from source_frame_audio_rom import pack


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native-proof',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--packed',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 proof_path=a.native_proof/'report.json';proof=json.loads(proof_path.read_text());payload=(a.native_proof/'native.brr').read_bytes()
 if proof['status']!='PASS'or hashlib.sha256(payload).hexdigest()!=proof['brr_sha256']:raise ValueError('NATIVE_MIXED_BRR_IDENTITY')
 identity='private-proof/mixed-source-channels';digest=hashlib.sha256(proof_path.read_bytes()).hexdigest();brr_digest=hashlib.sha256(payload).hexdigest();name=brr_digest+'.brr'
 (a.output/name).write_bytes(payload)
 row=dict(sound_index=0,source_path=identity,source_kind='computed real-source C-equivalent mixer output',source_sha256=digest,brr_path=name,brr_sha256=brr_digest,brr_bytes=len(payload),normalized_sample_rate=11025,normalized_frames=proof['frames'],audio_adaptation='ACCEPTED_COMPAT 11025 mono source mixer output with predictive BRR encoding; no sample-exact recording claim',contributing_source_channels=proof['channels'])
 report=dict(schema='BYOR_PRIVATE_MIXED_STREAM_FIXTURE_V1',namespace=[identity],source_frame_table_sha256=digest,compiled=[row],native_producer_proof=str(proof_path),private_aggregate_identity=True,authored_namespace_admitted=False,no_pcm_copies=True,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');packed=pack(a.output,a.packed,cpu_base=0xe80000);print('PRIVATE_MIXED_STREAM_PACKED',packed['meaningful_brr_bytes'],'bytes')


if __name__=='__main__':main()
