"""Native VM regression for size-neutral direct raster IRQ routing.

Original BOR cold boot/selector/stage bootstrap plus a bounded call/branch/native
variant script. IRQ transfer and production presentation leases are separate.
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import m4_script_vm_native as vm
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from source_raster_direct_fetch import emit,transform


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('rom','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    sy=symbols(Path('src/main.sym'));original=a.rom.read_bytes();raw=bytearray(original)
    if raw[39*32768:40*32768]!=bytes(32768):raise ValueError('DIRECT_FETCH_PRIVATE_BANK_NOT_EMPTY')
    code='.snes\n.bank 39\n.org $8000\n'+emit(sy)+'''
.org $8100
SourceRasterDirectIrqPlaceholder:
.a16
.i16
 rti
'''
    pasm=folder/'fixture.pasm';pasm.write_text(code)
    run=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise ValueError('DIRECT_FETCH_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');binary=(folder/'fixture.bin').read_bytes()[39*32768:]
    if not 0<len(binary)<=32768:raise ValueError('DIRECT_FETCH_CODE_SIZE')
    raw[39*32768:39*32768+len(binary)]=binary
    transform(raw,sy,fs['SourceRasterDirectFetchLoop'],fs['SourceRasterDirectIrqPlaceholder'],offset)
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    media=folder/'bor.msu'
    if not media.exists():os.link(a.rom.with_suffix('.msu').resolve(),media)
    with patch.object(sys,'argv',['m4_script_vm_native.py','--rom',str(rom),'--output',str(folder)]):vm.main()
    path=folder/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_DIRECT_RASTER_FETCH_VM_NATIVE_V1',production_base_sha256=hashlib.sha256(original).hexdigest(),bank_zero_size_unchanged=True,bank_zero_substitutions_only=True,bank_zero_changed_offsets=[i for i,(x,y)in enumerate(zip(original[:32768],raw[:32768]))if x!=y],source_fetch_loop_migrated=True,actual_vm_fetch_source=True,irq_placeholder_only=True,production_irq_palette_transfer_proven=False,scope='Original BOR cold boot/selector/first-stage bootstrap and bounded native VM call/branch/parameter/return/variant proof with private direct-fetch routing. No raster transfer or MOTU gameplay admission.');path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
