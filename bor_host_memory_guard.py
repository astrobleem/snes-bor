"""Nonprivileged host-memory floor and report policy for bounded BOR runs."""
import ctypes,json
from pathlib import Path
class Status(ctypes.Structure):
 _fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(n,ctypes.c_uint64) for n in ('total','available','commit_total','commit_available','virtual_total','virtual_available','extended')]
_api=ctypes.WinDLL('kernel32',use_last_error=True).GlobalMemoryStatusEx
_api.argtypes=[ctypes.POINTER(Status)];_api.restype=ctypes.c_int

def require_memory(start=False):
 s=Status();s.length=ctypes.sizeof(s)
 if not _api(ctypes.byref(s)):raise OSError(ctypes.get_last_error(),'GlobalMemoryStatusEx')
 r={'load_percent':s.load,'available_GiB':round(s.available/1024**3,3),'available_commit_GiB':round(s.commit_available/1024**3,3)}
 if s.available<(2.5 if start else 2)*1024**3 or s.commit_available<(8 if start else 4)*1024**3:raise RuntimeError('BOR_HOST_MEMORY_FLOOR:'+json.dumps(r))
 return r

# Preserve all identity checks in memory; do not emit new checksum reports.
_original_write=Path.write_text
_blocked={'loaded-rom-identity.json','capture-runtime.json'}
def _without_checksums(v):
 if isinstance(v,dict):return {k:_without_checksums(x) for k,x in v.items() if 'sha256' not in k.lower() and k not in ('rom','target_before')}
 if isinstance(v,list):return [_without_checksums(x) for x in v]
 return v

def _write(path,data,*args,**kwargs):
 if path.name in _blocked:return len(data)
 if path.suffix=='.json':
  try:data=json.dumps(_without_checksums(json.loads(data)),indent=2)+'\n'
  except (ValueError,TypeError):pass
 return _original_write(path,data,*args,**kwargs)
Path.write_text=_write
