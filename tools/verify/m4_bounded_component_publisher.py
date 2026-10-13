"""Bind sealed native world tuples to admitted component compiler contexts.

Finite context admission, explicit miss fault, forced-blank publication. Reuses
the unchanged component renderer's generated bootstrap/DMA bytes. No palette
solver, artwork transformation, per-epoch pose injection or renderer rewrite.
"""
import json
from pathlib import Path
import struct
import subprocess
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_bg_components_native import compile_rom
from m4_live_ground_owner import SNAPSHOT

READY=0x7ffb96
DISPLAY_EPOCH=0x7ffb98
KEY_OFFSETS=(12,14,28,30,52,54,60,62,80,84,86)


def build(original,sy,folder,assets,samples):
    rom=bytearray(original)
    if rom[57*32768:58*32768]!=bytes(32768):raise ValueError('BOUNDED_PUBLISHER_CODE_LEASE')
    lines=['.snes','.bank 57','.org $8000','BoundedPublish:','.a16','.i16',
           ' php',' rep #$30',' pha',' phx',' phy',' phb',' phd',' lda #0',' tcd',
           ' sep #$20','.a8',' pha',' plb',' rep #$20','.a16']
    def longbranch(op,label,n):
        lines.extend([f' {dict(bne="beq",beq="bne")[op]} BoundedSkip{n}',f' jmp {label}',
                      f'BoundedSkip{n}:','.a16','.i16'])
    serial=0
    for i,sample in enumerate(samples):
        raw=Path(sample['snapshot']).read_bytes()
        lines.extend([f'BoundedMatch{i}:','.a16','.i16'])
        for at in KEY_OFFSETS:
            serial+=1
            value=struct.unpack_from('<H',raw,at)[0]
            lines.extend([f' lda.l {SNAPSHOT+at}',f' cmp #{value}'])
            longbranch('bne',f'BoundedMatch{i+1}',serial)
        lines.extend([f' jmp BoundedDraw{i}'])
    lines.extend([f'BoundedMatch{len(samples)}:','.a16','.i16',
                  ' pld',' plb',' ply',' plx',' pla',' plp',' sec',' rtl'])
    manifest=[]
    for i,asset in enumerate(assets):
        report=json.loads((asset/'report.json').read_text())
        # The bounded sample has a static source palette. General raster
        # contexts must retain the existing continuous production publisher.
        if any(row['updates'] for row in report['trace'][1:]):raise ValueError('BOUNDED_PUBLISHER_STATIC_PALETTE_REQUIRED')
        raw,_,resources=compile_rom(report,asset,offset_alias=True)
        pos=(64+4*i)*32768
        data=raw[0x10000:0x30000]
        if pos+len(data)>len(rom) or rom[pos:pos+len(data)]!=bytes(len(data)):
            raise ValueError('BOUNDED_PUBLISHER_DATA_LEASE')
        rom[pos:pos+len(data)]=data
        code=bytearray(raw[0x8000:0x8400]);marker=code.find(bytes.fromhex('a9 0f 8d 00 21'))
        if marker<11:raise ValueError('COMPONENT_BOOTSTRAP_CONTRACT')
        code=code[11:marker+5] # omit reset/mode/stack setup; retain all DMA/PPU setup
        first_bank=0xe0+2*i
        # Change only DMA/HDMA source-bank immediates. Data bytes and native
        # component publication instructions remain the compiler's originals.
        for j in range(len(code)-14):
            if code[j]==0xa9 and code[j+2:j+5]==bytes.fromhex('8d 72 43') and code[j+5]==0xa9 and code[j+7:j+10]==bytes.fromhex('8d 73 43') and code[j+10]==0xa9 and code[j+12:j+15]==bytes.fromhex('8d 74 43'):
                old=code[j+11]
                if old not in (2,3,4,5):raise ValueError('BOUNDED_DMA_BANK_DOMAIN')
                address=code[j+1]|(code[j+6]<<8)
                address-=0x8000 if old%2==0 else 0
                code[j+1]=address&255;code[j+6]=address>>8
                code[j+11]=first_bank+(old-2)//2
        for reg in range(0x4304,0x4375,16):
            needle=bytes([0xa9,5,0x8d,reg&255,reg>>8])
            code=code.replace(needle,bytes([0xa9,first_bank+1,0x8d,reg&255,reg>>8]))
        lines.extend([f'BoundedDraw{i}:','.a16','.i16',' sep #$20','.a8'])
        # The source bootstrap used side windows. These are dependencies of
        # the full-canvas context and must be retired at this owner handoff.
        lines.append(' lda #0')
        lines.extend(f' sta.l ${reg:06X}' for reg in (*range(0x2123,0x212c),0x212e,0x212f))
        lines.extend(' .db '+','.join(f'${b:02X}' for b in code[j:j+16]) for j in range(0,len(code),16))
        lines.extend([' rep #$20','.a16',f' lda #{0xb4b8}',f' sta.l {READY}',
                      f' lda.l {SNAPSHOT+144}',f' sta.l {DISPLAY_EPOCH}',
                      ' pld',' plb',' ply',' plx',' pla',' plp',' clc',' rtl'])
        manifest.append(dict(index=i,key=[struct.unpack_from('<H',Path(samples[i]['snapshot']).read_bytes(),at)[0] for at in KEY_OFFSETS],
                             rom_data_offset=pos,resources=resources))
    # Keep the production bootstrap NMI until the component owner takes over.
    # The original bank-zero JSR return remains bank zero on the ordinary path.
    entry=sy['nmi_handler'];at=offset(entry);prior=bytes(rom[at:at+8])
    if prior[0]!=0x22 or prior[4]!=0x20 or prior[7]!=0x40:raise ValueError('BOUNDED_NMI_HANDOFF_PROLOGUE')
    stage=int.from_bytes(prior[1:4],'little');core=int.from_bytes(prior[5:7],'little')
    lines.extend(['.org $F000','BoundedNmi:','.a16','.i16',' php',' rep #$30',' pha',
                  f' lda.l {READY}',f' cmp #{0xb4b8}',' beq BoundedNmiOwned',
                  ' pla',' plp',f' jsl ${stage:06X}',f' pea ${entry+6:04X}',f' jml ${core:06X}',
                  'BoundedNmiOwned:','.a16','.i16',' lda.l $004210',' pla',' plp',' rti'])
    path=folder/'publisher.pasm';path.write_text('\n'.join(lines)+'\n')
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(path),'--output',str(folder/'publisher.bin'),'--symbols',str(folder/'publisher.sym'),'--no-pansy'],capture_output=True,text=True)
    (folder/'publisher-build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('BOUNDED_PUBLISHER_ASSEMBLY')
    fs=symbols(folder/'publisher.sym');blob=(folder/'publisher.bin').read_bytes()[57*32768:58*32768]
    if len(blob)>32768:raise ValueError('BOUNDED_PUBLISHER_CODE_OVERFLOW')
    rom[57*32768:57*32768+len(blob)]=blob
    rom[at:at+4]=bytes([0x5c])+fs['BoundedNmi'].to_bytes(3,'little')
    return bytes(rom),dict(contexts=manifest,key_offsets=KEY_OFFSETS,context_miss_fault=True,
                          host_writes_positions=False,publication='forced blank; sealed snapshot tuple selects complete component context')
