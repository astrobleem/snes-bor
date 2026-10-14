"""Source-owned epoch-16/17 precheck candidate; historical fixtures untouched."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from early_capacity import transform
from m4_conditional_capacity_native import CAP,audit_capacity,observer,evidence
import m4_restore_spill_capacity_native as control

def build(folder):
    n=folder/'native';n.mkdir(parents=True,exist_ok=True)
    lines=transform((CAP/'publisher.pasm').read_text().splitlines());(n/'publisher.pasm').write_text('\n'.join(lines)+'\n')
    p=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(n/'publisher.pasm'),'--output',str(n/'publisher.bin'),'--symbols',str(n/'publisher.sym'),'--no-pansy'],capture_output=True,text=True)
    (n/'publisher-build.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('EARLY_POPPY_BUILD')
    sy=symbols(n/'publisher.sym');rom=bytearray((CAP/'bor.sfc').read_bytes());start=offset(sy['NbBegin']);end=offset(sy['NbCodeEnd']);rom[start:end]=(n/'publisher.bin').read_bytes()[start:end];audit_capacity(rom,n);(n/'bor.sfc').write_bytes(rom)
    c=json.loads((CAP.parent/'contract.json').read_text());c['native_symbols']={k:v for k,v in sy.items() if k.startswith(('Nb','Online','Astra','Warm','Capacity','Spill'))};c['early_capacity_admission']=True;c['temporary_bitmap']=[0x3480,0x34cc];(folder/'contract.json').write_text(json.dumps(c,indent=2)+'\n');shutil.copyfile(CAP/'callback_owner.lua',n/'callback_owner.lua')
    if not (n/'bor.msu').exists():os.link(CAP/'bor.msu',n/'bor.msu')

def certify(folder,fields,mode):
    with patch.object(control,'audit',audit_capacity):r=control.certify(folder,fields,mode)
    r['conditional_capacity']=evidence(folder,17,124,True)
    r['classification']='CONDITIONAL_CAPACITY_NATIVE_CORRECT' if mode==0 else 'CONDITIONAL_CAPACITY_ROLLBACK_PASS'
    return r

def run(folder,mode=0):
    original=control.certify
    def checked(folder,fields,mode):
        with patch.object(control,'certify',original):return certify(folder,fields,mode)
    with patch.object(control,'audit',audit_capacity),patch.object(control,'observer',observer),patch.object(control,'certify',checked):control.run(folder,mode)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--run-existing',action='store_true');p.add_argument('--fault-mode',type=int,choices=range(5),default=0);p.add_argument('--build-only',action='store_true');a=p.parse_args();folder=a.output.resolve()
    if not a.run_existing:build(folder)
    if not a.build_only:run(folder,a.fault_mode)
