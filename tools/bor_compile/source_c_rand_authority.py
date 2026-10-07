"""Measured Windows CRT rand compatibility; separate from pinned engine rand32."""
import argparse,ctypes,hashlib,json,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1')
 consumers={n:extract(text,n)for n in ('common_try_grab','common_trymove')}
 assert all('rand()'in f for f in consumers.values())and 'srand('not in text
 runtime=ctypes.CDLL('msvcrt.dll');runtime.srand.argtypes=[ctypes.c_uint];runtime.rand.restype=ctypes.c_int
 rows=[]
 for seed in (0,1,2,32767,32768,65535,0x7fffffff,0xffffffff):
  runtime.srand(seed);state=seed
  for index in range(64):
   before=state;state=(state*214013+2531011)&0xffffffff;actual=runtime.rand();expected=(state>>16)&32767
   rows.append(dict(initial_seed=seed,index=index,seed_before=before,seed_after=state,actual=actual,expected=expected));assert actual==expected
 dll=Path('C:/Windows/System32/msvcrt.dll')
 report=dict(schema='BYOR_4086_C_RUNTIME_RAND_WIN32_AUTHORITY_V1',status='PASS',engine_commit=ENGINE_COMMIT,profile='ACCEPTED_COMPAT_C_RUNTIME_RAND_WIN32',profile_id=1,multiplier=214013,increment=2531011,shift=16,mask=32767,default_seed=1,cases=len(rows),inputs=rows,source_consumer_sha256={n:hashlib.sha256(f.encode()).hexdigest()for n,f in consumers.items()},source_engine_has_srand_call=False,measured_library=str(dll),measured_library_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),measurement_process_bits=ctypes.sizeof(ctypes.c_void_p)*8,original_2014_engine_binary_crt_verified=False,platform_policy='Explicit measured Windows CRT compatibility; no universal C rand sequence or original binary equivalence claim',engine_rand32_stream_shared=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(rows),'measured Windows CRT values; explicit compatibility profile')
if __name__=='__main__':main()
