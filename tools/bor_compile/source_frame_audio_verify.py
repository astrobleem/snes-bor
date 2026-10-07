"""Verify source namespace, full-duration stream assets and BRR segment joins."""
import argparse,hashlib,io,json,wave
from fractions import Fraction
from pathlib import Path
from compiler import Source,key
from source_frame_effects_4086 import derive,pack,unpack

def verify(source,folder):
    report=json.loads((folder/'report.json').read_text());table=pack(derive(source))
    assert report['source_frame_table_sha256']==hashlib.sha256(table).hexdigest()
    assert report['namespace']==unpack(table)['media']
    rows=[]
    for row in report['compiled']:
        assert key(report['namespace'][row['sound_index']])==key(row['source_path'])
        raw=source.read(row['source_path']);assert hashlib.sha256(raw).hexdigest()==row['source_sha256']
        with wave.open(io.BytesIO(raw),'rb')as wav:
            rate=wav.getframerate();frames=wav.getnframes();channels=wav.getnchannels()
        brr=(folder/row['brr_path']).read_bytes()
        assert len(brr)==row['brr_bytes']==row['brr_blocks']*9
        assert hashlib.sha256(brr).hexdigest()==row['brr_sha256']
        assert row['normalized_frames']==row['brr_blocks']*16
        assert all(brr[i]&3==0 for i in range(0,len(brr)-9,9))and brr[-9]&3==1
        sample_cursor=brr_cursor=0
        for segment in row['segments']:
            assert segment['sample_offset']==sample_cursor and segment['brr_offset']==brr_cursor
            assert segment['samples']<=65520 and segment['samples']%16==0
            assert segment['brr_bytes']==segment['samples']//16*9
            assert brr[brr_cursor]&12==0
            sample_cursor+=segment['samples'];brr_cursor+=segment['brr_bytes']
        assert(sample_cursor,brr_cursor)==(row['normalized_frames'],len(brr))
        difference=Fraction(row['normalized_frames'],row['normalized_sample_rate'])-Fraction(frames,rate)
        assert abs(difference)<=Fraction(16,row['normalized_sample_rate'])
        rows.append(dict(source_path=row['source_path'],source_frames=frames,source_rate_hz=rate,source_channels=channels,stream_samples=row['normalized_frames'],stream_rate_hz=row['normalized_sample_rate'],duration_difference_seconds=float(difference),brr_bytes=len(brr),segments=len(row['segments']),intermediate_end_flags=0,loop_flags=0))
    result=dict(schema='BYOR_SOURCE_FRAME_AUDIO_VERIFY_V1',status='PASS',cases=len(rows),assets=rows,source_colors_unmodified=True,audio_policy='ACCEPTED_COMPAT mono PCM_u8/11025Hz then TAD BRR; full duration within one padded block; independent segments begin filter0',native_playback_proven=False)
    (folder/'verification.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--folder',required=True,type=Path);a=p.parse_args()
    print('Source frame audio verified:',verify(Source(a.source),a.folder)['cases'],'assets')

if __name__=='__main__':main()
