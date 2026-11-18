"""One guarded assembly candidate; restore source/generated loans, no backup."""
from pathlib import Path
import ast,hashlib,json,msvcrt,os,re,subprocess,sys
import bor_host_memory_guard
from bor_host_memory_guard import require_memory
import edit_bor_restart_v900 as edit
W=Path(__file__).resolve().parent;R=edit.R
RUN=W/'BOR-RESTART-v900r1-build'
PROCESS_TEMP=None
DISK_GUARD=None
WRAPPER=Path('C:/Users/chad/Documents/Codex/toolchains/gcc-ucrt64.py')
REAL_POPEN=subprocess.Popen

def guarded_argv(argv):
    if isinstance(argv,(list,tuple)):
        name=Path(str(argv[0])).name.lower()
        if name in ('gcc','gcc.exe'):
            argv=[sys.executable,str(WRAPPER),*argv[1:]]
        elif name in ('g++','g++.exe'):
            raise RuntimeError('GCC_CXX_REQUIRES_WRAPPER_DRIVER_REVIEW')
        if name in ('dotnet','dotnet.exe','gcc','gcc.exe'):
            require_memory(start=True)
    elif re.search(r'(?i)(?:^|[\\/\s])(?:gcc|g\+\+)(?:\.exe)?(?:\s|$)',str(argv)):
        raise RuntimeError('STRING_GCC_ENTRYPOINT_REFUSED')
    return argv

class GuardedPopen(REAL_POPEN):
    def __init__(self,argv,*args,**kwargs):
        super().__init__(guarded_argv(argv),*args,**kwargs)

def main():
    print('BUILD_MEMORY',require_memory(start=True),flush=True)
    assert WRAPPER.is_file() and not RUN.exists()
    p=W/'build_bor_quit_cleanup_v837r1.py';code=p.read_text()
    assert code.count("RUN=W/'BOR-QUIT-CLEANUP-v837r1-build'")==1
    # RUN may be on a different volume from W and the retained inputs.
    code=code.replace("RUN=W/'BOR-QUIT-CLEANUP-v837r1-build'","RUN=Path("+repr(str(RUN.resolve()))+")")
    if PROCESS_TEMP is not None:
        anchor="TEMP=str(RUN/'temp'),TMP=str(RUN/'temp')"
        assert code.count(anchor)==1
        value=repr(str(Path(PROCESS_TEMP).resolve()))
        code=code.replace(anchor,'TEMP='+value+',TMP='+value)
    code=code.replace('min(free().values())>16*1024**3','min(free().values())>17*1024**3')
    if DISK_GUARD is not None:
        anchor='min(free().values())>17*1024**3'
        assert code.count(anchor)==1
        code=code.replace(anchor,'disk_guard(start=True)')
    anchor=' for n,d in O.items():assert sha(ROOT/n)==d,n\n'
    assert code.count(anchor)==1
    code=code.replace(anchor,
        " for n in "+repr(tuple(edit.ORIGINAL))+":O[n]=sha(ROOT/n)\n"+anchor)
    code=code.replace("  state['candidate_rom']=sha(TARGET/'bor.sfc')","  candidate_rom=sha(TARGET/'bor.sfc')")
    code=code.replace("'msu_before':msu,",'')
    code=code.replace("'target_before':sha(TARGET/'bor.sfc'),",'')
    if getattr(edit,'RETAIN_WORKER',False):
        anchor="('world.sym',TARGET/'world.sym')]:shutil.copy2(p,RUN/'product'/n)"
        assert code.count(anchor)==1
        code=code.replace(anchor,"('world.sym',TARGET/'world.sym'),('worker.sym',TARGET/'worker.sym'),('worker.pasm',TARGET/'worker.pasm')]:shutil.copy2(p,RUN/'product'/n)")
    compile(code,str(p),'exec')
    with (R/'out/bor-mesen.lock').open('r+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        applied=False
        try:
            edit.change();applied=True
            subprocess.Popen=GuardedPopen
            # Pure Python source plus existing Poppy/dotnet assembly path;
            # unexpected GCC is forced through the mandatory wrapper.
            exec(compile(code,str(p),'exec'),{'__file__':str(p),'__name__':'__main__','disk_guard':DISK_GUARD})
        finally:
            subprocess.Popen=REAL_POPEN
            try:
                if applied:edit.change(reverse=True)
            finally:
                lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_UNLCK,1)
    print('SOURCE_AND_LEASE_RESTORED',flush=True)

if __name__=='__main__':main()
