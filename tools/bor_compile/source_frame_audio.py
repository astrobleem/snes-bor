"""Compile the B4FE source sound namespace into provenanced TAD stream assets.

Uses the existing pinned production WAV normalization and one-effect BRR
compiler. This does not install runtime bindings or imply audible playback.
"""
import argparse
import hashlib
import io
import json
import subprocess
import shutil
import wave
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/audio'),str(ROOT/'soundwork/tad')]
from compiler import Source,key
from source_frame_effects_4086 import derive,pack,unpack
from production_sfx import canonical_wav,duration_ticks
from build_batch_b_audio import bracked_project,COMPILER
from rebuild import check_compiler_version

def stream_wav(raw,rate):
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise ValueError('SOURCE_FRAME_AUDIO_FFMPEG_REQUIRED')
    pcm=subprocess.run([ffmpeg,'-v','error','-i','pipe:0','-ac','1','-ar',str(rate),'-acodec','pcm_u8','-f','u8','pipe:1'],input=raw,capture_output=True,check=True).stdout
    frames=len(pcm);pcm+=bytes([128])*((-frames)%16)
    output=io.BytesIO()
    with wave.open(output,'wb')as w:w.setparams((1,1,rate,0,'NONE','not compressed'));w.writeframes(pcm)
    return output.getvalue(),frames,dict(tool='ffmpeg',tool_sha256=hashlib.sha256(Path(ffmpeg).read_bytes()).hexdigest(),policy='ACCEPTED_COMPAT full-duration mono PCM_u8 at existing fixed stream pitch; no clipping',rate_hz=rate,padded_frames=len(pcm)-frames)

def segmented_brr(wav,rate):
    with wave.open(io.BytesIO(wav),'rb')as w:pcm=w.readframes(w.getnframes())
    result=bytearray();segments=[]
    for offset in range(0,len(pcm),65520):
        part=pcm[offset:offset+65520];output=io.BytesIO()
        with wave.open(output,'wb')as w:w.setparams((1,1,rate,0,'NONE','not compressed'));w.writeframes(part)
        _,ticks,_=duration_ticks(output.getvalue(),rate)
        brr,common=bracked_project(ROOT,output.getvalue(),rate,ticks,'source_effect')
        # Each independently encoded first block uses filter0. This makes the
        # concatenation valid with the preceding decoder history unchanged.
        assert len(brr)==len(part)//16*9 and brr[0]&12==0
        assert all(brr[i]&3==0 for i in range(0,len(brr)-9,9))and brr[-9]&3==1
        start=len(result);result.extend(brr);result[-9]&=252
        segments.append(dict(sample_offset=offset,samples=len(part),brr_offset=start,brr_bytes=len(brr),first_filter=0,single_effect_common_bytes=common))
    result[-9]|=1
    assert sum(bool(result[i]&1)for i in range(0,len(result),9))==1
    return bytes(result),segments

def compile_assets(source,output,selected=None,stream_rate=None):
    output=output.resolve();output.mkdir(parents=True,exist_ok=True)
    data=pack(derive(source));namespace=unpack(data)['media']
    wanted=None if selected is None else {key(n)for n in selected}
    if wanted is not None and wanted-{key(n)for n in namespace}:
        raise ValueError('SOURCE_FRAME_AUDIO_UNKNOWN_ASSET')
    version=check_compiler_version(COMPILER);rows=[];physical={}
    for index,name in enumerate(namespace):
        if wanted is not None and key(name)not in wanted:continue
        raw=source.read(name);wav,rate=canonical_wav(raw);adaptation=None
        if stream_rate is not None:
            if stream_rate!=11025:raise ValueError('SOURCE_FRAME_AUDIO_EXISTING_STREAM_RATE_11025_REQUIRED')
            wav,unpadded,adaptation=stream_wav(raw,stream_rate);rate=stream_rate
        frames,ticks,seconds=duration_ticks(wav,rate)
        canonical_hash=hashlib.sha256(wav).hexdigest()
        if canonical_hash not in physical:
            try:
                if stream_rate is None:
                    brr,common_bytes=bracked_project(ROOT,wav,rate,ticks,'source_effect');segments=[]
                else:
                    brr,segments=segmented_brr(wav,rate);common_bytes=None
            except subprocess.CalledProcessError as error:
                failure=dict(source_path=name,sound_index=index,normalized_frames=frames,normalized_sample_rate=rate,compiler_stdout=error.stdout,compiler_stderr=error.stderr,classification='ONE_EFFECT_COMMON_COMPILATION_LIMIT',no_clipping_applied=True,resampling_policy=adaptation)
                (output/'compile-failure.json').write_text(json.dumps(failure,indent=2)+'\n')
                raise ValueError('SOURCE_FRAME_AUDIO_COMPILE_FAILED:'+name+':'+str(error.stderr))from error
            identity=hashlib.sha256(brr).hexdigest();filename=identity+'.brr'
            destination=output/filename
            if destination.exists()and destination.read_bytes()!=brr:
                raise ValueError('SOURCE_FRAME_AUDIO_HASH_COLLISION')
            destination.write_bytes(brr)
            physical[canonical_hash]=(identity,filename,len(brr),common_bytes,segments)
        identity,filename,size,common,segments=physical[canonical_hash]
        rows.append(dict(sound_index=index,source_path=name,source_sha256=hashlib.sha256(raw).hexdigest(),canonical_wav_sha256=canonical_hash,normalized_sample_rate=rate,normalized_frames=frames,duration_ticks=ticks,duration_seconds=seconds,brr_sha256=identity,brr_path=filename,brr_bytes=size,brr_blocks=size//9,single_effect_common_bytes=common,segments=segments,audio_adaptation=adaptation,backend='TAD_STREAM_VOICE0',loop=False))
    report=dict(schema='BYOR_SOURCE_FRAME_AUDIO_V1',source_frame_table_sha256=hashlib.sha256(data).hexdigest(),namespace=namespace,compiled=rows,uncompiled_indices=sorted(set(range(len(namespace)))-{r['sound_index']for r in rows}),compiler=str(COMPILER),compiler_version=version,compiler_sha256=hashlib.sha256(COMPILER.read_bytes()).hexdigest(),runtime_binding_installed=False,audible_playback_proven=False,no_pcm_copies=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--asset',action='append');p.add_argument('--stream-rate',type=int);a=p.parse_args()
    r=compile_assets(Source(a.source),a.output,a.asset,a.stream_rate)
    print(f"Compiled {len(r['compiled'])}/{len(r['namespace'])} source frame sounds; {sum(x['brr_bytes']for x in r['compiled'])} BRR bytes; runtime binding pending")

if __name__=='__main__':main()
