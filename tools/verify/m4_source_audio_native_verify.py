"""Validate the bounded private source-stream proof, without gameplay claims."""
import argparse
import hashlib
import json
import math
import wave
from pathlib import Path


def verify(folder, assets, require_dsp_trace=False):
    trace=json.loads((folder/'audio-stream-trace.json').read_text())
    source=trace['source']
    payload=(assets/source['brr_path']).read_bytes()
    assert hashlib.sha256(payload).hexdigest()==source['brr_sha256']
    chunks=trace['received_chunks'];observations=trace['observations']
    expected=math.ceil(len(payload)/144)
    assert [r['chunk'] for r in chunks]==list(range(expected))
    # Every acknowledged chunk must still have a distinct resident ring slot
    # at observation. A burst of up to eight is safe to inspect; a larger gap
    # would overwrite a slot and make its earlier contents unobservable.
    assert all(1<=r['observer_gap']<=8 for r in chunks)
    assert sum(r['meaningful_bytes'] for r in chunks)==len(payload)
    assert all(r['mismatched_bytes']==0 and r['sha256']==r['expected_sha256'] for r in chunks),'SOURCE_STREAM_TRANSPORT_BYTES:'+str([(r['chunk'],r['mismatched_bytes'])for r in chunks if r['mismatched_bytes']][:12])
    assert observations[-1]['producer_done'] and observations[-1]['chunks_accepted']==expected
    underruns=[r['field'] for r in observations if not r['producer_done'] and r['consumer_chunk']>r['chunks_accepted']]
    assert not underruns,'SOURCE_STREAM_CONSUMER_UNDERRUN:'+str(underruns[:12])
    active=[r for r in observations if r['voice0']['envelope']]
    assert active and observations[-1]['voice0']['envelope']==0
    assert [r['field'] for r in active]==list(range(active[0]['field'],active[-1]['field']+1))
    assert all(r['voice0']['sampleSrc']==33 and r['voice0']['pitch']==1411 and r['voice0']['adsr1']==0 and r['voice0']['gain']==127 for r in active)
    assert active[0]['chunks_accepted']>=8
    # Local Mesen authority: Spc.h's 32000Hz, SnesConsole.cpp's NTSC
    # 21477270Hz and SnesPpu.cpp's 1364-clock lines / odd short line.
    # Frame sampling bounds the observed start/end to two fields.
    fields_per_second=21477270/(1364*262-2)
    effective_rate=32000*1411/4096
    expected_fields=source['normalized_frames']/effective_rate*fields_per_second
    observed_fields=len(active)
    assert abs(observed_fields-expected_fields)<=2
    fingerprint=json.loads((folder/'audio-fingerprint.json').read_text())
    wav=folder/'source-energy.wav'
    with wave.open(str(wav),'rb') as recording:
        pcm=recording.readframes(recording.getnframes())
    assert hashlib.sha256(pcm).hexdigest()==fingerprint['sha256']
    assert fingerprint['peakAmplitude']>0 and all(v>0 for v in fingerprint['rmsLevels'])
    dsp_trace=folder/'voice0.raw.trace'
    block_proof=None
    if require_dsp_trace or dsp_trace.exists():
        metadata=json.loads((folder/'voice0.raw.json').read_text())
        assert metadata['voice']==0 and metadata['sample_rate']==32000
        assert metadata['kon_sample']==0 and metadata['koff_sample'] is None
        assert metadata['endx_sample']==metadata['sample_count']
        captured=(folder/'voice0.raw').read_bytes()
        assert len(captured)==metadata['sample_count']*4
        traversed=[];count=0
        with dsp_trace.open() as lines:
            for i,line in enumerate(lines):
                sample,address,header,fingerprint_=line.strip().split(',')
                assert int(sample)==i
                item=(int(address,16),int(header,16),int(fingerprint_,16))
                if not traversed or traversed[-1]!=item:traversed.append(item)
                count=i+1
        assert count==metadata['sample_count']
        expected_blocks=[]
        for i in range(len(payload)//9):
            block=bytearray(payload[i*9:i*9+9])
            if i%128==127 and i!=len(payload)//9-1:block[0]|=3
            value=2166136261
            for byte in block:value=((value^byte)*16777619)&0xffffffff
            expected_blocks.append((0x121a+(i%128)*9,block[0],value))
        assert traversed==expected_blocks,'SOURCE_STREAM_DSP_BLOCKS:'+str(dict(expected=len(expected_blocks),actual=len(traversed),first_mismatch=next((i for i,(a,b)in enumerate(zip(traversed,expected_blocks))if a!=b),None)))
        block_proof=dict(source_blocks=len(expected_blocks),observed_blocks=len(traversed),
            skipped_blocks=0,repeated_blocks=0,block_fingerprint_mismatches=0,
            dsp_samples=count,endx_sample=metadata['endx_sample'],
            voice_pcm_sha256=hashlib.sha256(captured).hexdigest(),
            trace_sha256=hashlib.sha256(dsp_trace.read_bytes()).hexdigest())
    result=dict(schema='BYOR_SOURCE_STREAM_PRIVATE_NATIVE_V1',status='PASS',
        source_path=source['source_path'],source_sha256=source['source_sha256'],
        compiled_brr_sha256=source['brr_sha256'],compiled_brr_bytes=len(payload),
        chunks=expected,meaningful_byte_mismatches=0,padding_byte_mismatches=0,
        observer_peak_chunk_gap=max(r['observer_gap']for r in chunks),observed_consumer_underruns=0,
        first_active_field=active[0]['field'],last_active_field=active[-1]['field'],
        active_fields=observed_fields,expected_active_fields=expected_fields,
        effective_sample_rate_hz=effective_rate,start_latency_observation='First envelope observation relative to post-request native observer; not source-event exact timing',
        prefill_chunks=7,voice0_srcn=33,voice0_pitch=1411,voice0_gain=127,
        final_voice0_envelope=0,audio_recording_pcm_sha256=fingerprint['sha256'],
        audio_recording_file_sha256=hashlib.sha256(wav.read_bytes()).hexdigest(),
        dsp_source_block_traversal=block_proof,
        policy=source['audio_adaptation'],private_runtime_only=True,
        legacy_gameplay_paused=trace['legacy_gameplay_paused'],
        sample_exact_recording_proven=False,concurrent_audio_proven=False,
        production_binding_installed=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'audio-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--require-dsp-trace',action='store_true')
    a=p.parse_args();r=verify(a.folder,a.assets,a.require_dsp_trace)
    print('Private source stream:',r['status'],r['chunks'],'chunks;',r['active_fields'],'active fields')


if __name__=='__main__':main()
