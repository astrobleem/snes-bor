"""Focused production OBJ init/clear/retirement probe; preserves every run."""
import json
import hashlib
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from _harness import McpSession, MESEN_EXE, _free_tcp_port, Reporter, exact_input_edge, run_frames_exact
from game_bor_startup_select import cold_to_title, title_to_charselect, wait_state, PLAYING

ROOT=Path(__file__).resolve().parents[2]

def symbols(path):
    return {n:(int(b,16)<<16)+int(a,16) for b,a,n in re.findall(
        r'(?m)^([\da-fA-F]{2}):([\da-fA-F]{4,6}) (\S+)$',Path(path).read_text())}

def offset(a):
    assert a & 65535 >= 0x8000 and a < 0x400000
    return (a>>16)*0x8000+(a&65535)-0x8000

def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    out=Path(tempfile.mkdtemp(prefix='oam_contract_',dir=ROOT/'out'))
    sy=symbols(ROOT/'src/main.sym')
    rom=ROOT/'distribution/bor.sfc'
    data=rom.read_bytes()
    # Skip the fixture's normal emission by entering a verified bank-0 RTS.
    done=offset(sy['Core_Oam_Play__done'])
    assert data[done]==0x60
    values=dict(setSprite=offset(sy['Core_Oam_SetSprite']),
        rts=sy['Core_Oam_Play__done']&65535, play=offset(sy['Core_Oam_Play']),
        clearAll=sy['Core_Oam_ClearAll']&65535,gameState=sy['Game_State'],playing=PLAYING,
        clearReturn=offset(sy['Core_Oam_ClearActive'])-1,
        dma=offset(sy['Core_Dma_TransferOam']),queue=sy['DmaQueue'],
        buffer=sy['Oam_Buffer'],expanded=sy['Oam_ExpandedHi'],cursor=sy['Oam_CurrentSlot'],
        guard=sy['OamShadow_End'])
    lua=out/'probe.lua'
    lua.write_text(Path(__file__).with_suffix('.lua').read_text().replace(
        '@SYMS@','{'+','.join(k+'='+str(v) for k,v in values.items())+'}'))
    class Session(McpSession):
        def __enter__(self):
            import mesen_mcp.session as sm
            def launch(argv,**kwargs): return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(sm,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    report={'status':'FAIL','rom_sha256':file_sha(rom),'msu_sha256':file_sha(ROOT/'distribution/bor.msu')}
    try:
        with Session(rom=str(rom),mesen=MESEN_EXE,boot_wait=2,port=_free_tcp_port(),stderr_log=out/'mesen.log') as m:
            with patch.object(m,'reset_emulator',lambda: {}): cold_to_title(m,Reporter('OAM-BOOT',kind='EXPERIMENT'))
            title_to_charselect(m,False)
            exact_input_edge(m,m.BTN_START,1,port=0)
            assert wait_state(m,PLAYING,300)
            seen=set()
            for _ in range(70):
                run_frames_exact(m,1)
                lines=[b.decode().strip() for b in list(m._stderr_lines) if b.startswith(b'OAMPROOF|')]
                hardware=[x.split('|') for x in lines if '|HARDWARE|' in x]
                if hardware:
                    p=int(hardware[-1][2])
                    if p not in seen:
                        shot=m.take_screenshot()
                        for k in ('path','filePath','file_path'):
                            if isinstance(shot,dict) and shot.get(k) and Path(shot[k]).exists():
                                shutil.copyfile(shot[k],out/f'phase-{p}.png');break
                        seen.add(p)
                if 36 in seen: break
            report['trace']=lines
            assert any('|OBSEL|' in x and x.endswith('|194,true') for x in lines),'forced-blank init write absent'
            assert hardware and all(x[3:6]==['16384','6','4096'] for x in hardware),'OBJ decode'
            known=next(x.split('|')[6] for x in lines if '|KNOWN|' in x)
            report['known_oam']=known
            for p,i,hi in ((21,127,2),(31,0,0)):
                rows=[r for r in hardware if int(r[2])==p]
                assert rows, f'active subject not captured {p}'
                oam=bytes.fromhex(rows[-1][6])
                assert oam[4*i:4*i+2]==bytes([64,80])
                assert (oam[512+i//4]>>((i%4)*2))&3==hi
            cleared=[x.split('|') for x in lines if '|CLEARED|' in x]
            assert len(cleared)==2,'real ClearAll acknowledgements'
            for row in cleared:
                low,expanded,guard=row[6].split(',')
                assert bytes.fromhex(low)==bytes([192,224,0,0])*128+bytes([85])*32
                assert bytes.fromhex(expanded)==bytes([1])*128
            returned=[x.split('|') for x in lines if '|CLEAR_RETURN|' in x]
            assert len(returned)==2 and all(r[6]=='a5a6a7a8a9' for r in returned),'adjacent scratch sentinel'
            for p in (23,33,36):
                rows=[r for r in hardware if int(r[2])==p]
                assert rows and bytes.fromhex(rows[-1][6])==bytes([192,224,0,0])*128+bytes([85])*32,f'hide all hardware {p}'
                status=[x.split('|') for x in lines if '|STATUS77|' in x and int(x.split('|')[2])==p]
                assert status and int(status[-1][6]) & 0xC0 == 0,'hidden OBJ range/time overflow'
            dma=[bytes.fromhex(x.split('|')[6]) for x in lines if '|DMA|' in x]
            assert any(x[:4]==bytes.fromhex('00020000') and x[5:8]==bytes.fromhex('00517e') for x in dma)
            assert any(x[:4]==bytes.fromhex('20000001') and x[5:8]==bytes.fromhex('00537e') for x in dma)
            report['dma']='512 bytes at word 0 + 32 bytes at word 0x100; channel 7 production consumer'
            report['status']='PASS'
    finally:
        (out/'proof.json').write_text(json.dumps(report,indent=2))
        print(out/'proof.json')


if __name__=='__main__': main()
