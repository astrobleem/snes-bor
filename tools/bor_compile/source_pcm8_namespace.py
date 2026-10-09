"""Compile the complete normalized PCM8 namespace without copying PCM media.

Payload is returned in memory for ROM installation. Normalization retains the
existing explicit mono/11025 PCM_u8 adaptation, independent of model identity.
"""
import hashlib,io,struct,wave
from source_frame_audio import stream_wav

def compile_namespace(source,manifest,*,cpu_base=0xeb0000):
 rows=sorted(manifest['compiled'],key=lambda r:r['sound_index'])
 if not rows or len(rows)>32767 or [r['sound_index']for r in rows]!=list(range(len(manifest['namespace'])))or not 0xe00000<=cpu_base<0x1000000 or cpu_base&1:
  raise ValueError('PCM8_NAMESPACE_DOMAIN')
 payload=bytearray();metadata=bytearray(struct.pack('<4sHH',b'PC8D',1,len(rows)));assets=[]
 for row in rows:
  raw=source.read(row['source_path'])
  if hashlib.sha256(raw).hexdigest()!=row['source_sha256']:raise ValueError('PCM8_SOURCE_HASH')
  normalized,meaningful,policy=stream_wav(raw,11025)
  if hashlib.sha256(normalized).hexdigest()!=row['canonical_wav_sha256']:raise ValueError('PCM8_NORMALIZED_HASH')
  with wave.open(io.BytesIO(normalized),'rb')as f:
   if (f.getnchannels(),f.getsampwidth(),f.getframerate())!=(1,1,11025):raise ValueError('PCM8_NORMALIZED_FORMAT')
   pcm=f.readframes(f.getnframes())
  if len(pcm)!=row['normalized_frames']or not 0<len(pcm)<=0xfffff:raise ValueError('PCM8_NORMALIZED_LENGTH')
  pointer=cpu_base+len(payload);words=struct.pack('<'+'H'*len(pcm),*pcm)
  if pointer+len(words)>0x1000000:raise ValueError('PCM8_NAMESPACE_ROM_CAPACITY')
  payload.extend(words);metadata.extend(struct.pack('<II',len(words),pointer))
  assets.append(dict(sound_index=row['sound_index'],source_path=row['source_path'],source_sha256=row['source_sha256'],normalized_pcm_sha256=hashlib.sha256(pcm).hexdigest(),normalized_frames=len(pcm),meaningful_frames=meaningful,word_bytes=len(words),cpu_pointer=pointer,crosses_bank=pointer>>16!=(pointer+len(words)-1)>>16,normalization_policy=policy))
 report=dict(schema='BYOR_PCM8_NAMESPACE_ROM_V1',status='PASS',namespace_count=len(rows),assets=assets,cpu_base=cpu_base,cpu_end=cpu_base+len(payload),CPU_pool_capacity=0x1000000-cpu_base,payload_bytes=len(payload),payload_sha256=hashlib.sha256(payload).hexdigest(),descriptor_bytes=len(metadata),descriptor_sha256=hashlib.sha256(metadata).hexdigest(),pool_free_bytes=0x1000000-cpu_base-len(payload),no_PCM_files_copied=True,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
 return report,bytes(metadata),bytes(payload)
