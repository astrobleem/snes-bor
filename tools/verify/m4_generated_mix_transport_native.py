"""Production ASAD/SPC traversal of a native-generated mixed BRR stream.

A private transport descriptor is not an authored sound namespace identity.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
from source_frame_audio_rom import pack
import m4_source_audio_rom_native as parent


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','producer','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);producer=json.loads(a.producer.read_text());assert producer['status']=='PASS'and producer['full_asset_lifetimes_and_native_codec_bound'];brr=(a.producer.parent/'native.brr').read_bytes();assert hashlib.sha256(brr).hexdigest()==producer['BRR_sha256'];assets=out/'assets';assets.mkdir(exist_ok=True);(assets/'generated.brr').write_bytes(brr);identity=hashlib.sha256(a.producer.read_bytes()).hexdigest();path='native-generated-mixed-stream'
 row=dict(sound_index=0,source_path=path,source_sha256=identity,brr_path='generated.brr',brr_sha256=producer['BRR_sha256'],brr_bytes=len(brr),normalized_sample_rate=11025,normalized_frames=producer['jobs']*producer['frames_per_job'],audio_adaptation='ACCEPTED_COMPAT source mono/11025 Hz normalization and predictive BRR; two equal-output-side source effects mixed with pinned C semantics')
 manifest=dict(schema='BYOR_GENERATED_MIX_TRANSPORT_INPUT_V1',namespace=[path],compiled=[row],source_frame_table_sha256=identity,native_producer_report_sha256=identity,source_identities=producer['source_identities'],authored_namespace=False,no_PCM_files_copied=True);(assets/'report.json').write_text(json.dumps(manifest,indent=2)+'\n');packed=out/'packed';pack(assets,packed)
 original=parent.run_fixture
 def fixture(*args,**kw):kw['link_pcm']=False;return original(*args,**kw)
 argv=['m4_source_audio_rom_native.py','--rom',str(a.rom),'--assets',str(assets),'--packed',str(packed),'--output',str(out),'--sound-index','0']
 with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',argv):
  try:parent.main()
  except SystemExit as e:
   if e.code not in(None,0):raise
 report=out/'report.json';r=json.loads(report.read_text());r.update(schema='BYOR_NATIVE_GENERATED_MIX_SPC_TRANSPORT_V1',namespace_derived=False,private_transport_descriptor=True,native_producer_report_sha256=identity,source_identities=producer['source_identities'],source_event_admission_bound=False,concurrent_realtime_mixer_bound=False,joint_graphics_bound=False,production_memory_lease=False,complete_backend_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_PCM_files_copied=True);report.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
