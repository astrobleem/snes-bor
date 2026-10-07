"""Validate the bounded private source-stream proof, without gameplay claims."""
import argparse
import hashlib
import json
import math
import wave
from pathlib import Path


def verify(folder, assets):
    trace=json.loads((folder/'audio-stream-trace.json').read_text())
    source=trace['source']
    payload=(assets/source['brr_path']).read_bytes()
    assert hashlib.sha256(payload).hexdigest()==source['brr_sha256']
    chunks=trace['received_chunks'];observations=trace['observations']
    expected=math.ceil(len(payload)/144)
    assert [r['chunk'] for r in chunks]==list(range(expected))
    assert all(r['observer_gap']==1 for r in chunks)
    assert sum(r['meaningful_bytes'] for r in chunks)==len(payload)
    assert all(r['mismatched_bytes']==0 and r['sha256']==r['expected_sha256'] for r in chunks)
    assert observations[-1]['producer_done'] and observations[-1]['chunks_accepted']==expected
    underruns=[r['field'] for r in observations if not r['producer_done'] and r['consumer_chunk']>r['chunks_accepted']]
    assert not underruns
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
    result=dict(schema='BYOR_SOURCE_STREAM_PRIVATE_NATIVE_V1',status='PASS',
        source_path=source['source_path'],source_sha256=source['source_sha256'],
        compiled_brr_sha256=source['brr_sha256'],compiled_brr_bytes=len(payload),
        chunks=expected,meaningful_byte_mismatches=0,padding_byte_mismatches=0,
        observer_peak_chunk_gap=1,observed_consumer_underruns=0,
        first_active_field=active[0]['field'],last_active_field=active[-1]['field'],
        active_fields=observed_fields,expected_active_fields=expected_fields,
        effective_sample_rate_hz=effective_rate,start_latency_observation='First envelope observation relative to post-constructor observer; not source-event exact timing',
        prefill_chunks=7,voice0_srcn=33,voice0_pitch=1411,voice0_gain=127,
        final_voice0_envelope=0,audio_recording_pcm_sha256=fingerprint['sha256'],
        audio_recording_file_sha256=hashlib.sha256(wav.read_bytes()).hexdigest(),
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
    a=p.parse_args();r=verify(a.folder,a.assets)
    print('Private source stream:',r['status'],r['chunks'],'chunks;',r['active_fields'],'active fields')


if __name__=='__main__':main()
