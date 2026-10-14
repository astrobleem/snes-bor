"""Immutable source-local occupancy admission; actual row composition is unchanged."""
import hashlib
import json
import struct
from phase_occupancy import compile_occupancy

DATA=0x343600
TABLE=0x34d100
END=0x34d700


def apply(lines,rom,authority,phases,occupancy):
    manifest=json.loads((occupancy/'occupancy-manifest.json').read_text())
    source=json.loads((phases/'manifest.json').read_text())
    if manifest['source_manifest_sha256']!=hashlib.sha256((phases/'manifest.json').read_bytes()).hexdigest():
        raise ValueError('OCCUPANCY_SOURCE_IDENTITY')
    if manifest['maximum_required_pairs']>768:raise ValueError('OCCUPANCY_CAPACITY')
    # One explicit, checked immutable lease, adjacent to but excluding F43000..F435FF.
    if len(rom)<END or any(rom[DATA:END]):raise ValueError('OCCUPANCY_ROM_LEASE')
    refs=bytes(rom[0x343000:DATA]);cursor=DATA;bounds={}
    for i,frame in enumerate(authority['frames']):
        role=frame['role'];table=bytearray();bound=0
        for entry in sorted(manifest['frames'][role]['x_phases'],key=lambda e:e['x_phase']):
            original=source['frames'][role]['phases'][entry['x_phase']]
            raw=(phases/original['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=original['sha256']:raise ValueError('OCCUPANCY_PHASE_IDENTITY')
            expected,g=compile_occupancy(raw,rows=original['row_count'],row_stride=original['row_stride'])
            data=(occupancy/entry['filename']).read_bytes()
            if data!=expected or hashlib.sha256(data).hexdigest()!=entry['sha256']:
                raise ValueError('OCCUPANCY_DATA_IDENTITY')
            if any(entry[k]!=g[k] for k in g):raise ValueError('OCCUPANCY_GEOMETRY')
            if not (0<g['cols']<256 and 0<g['tile_rows']<256):raise ValueError('OCCUPANCY_NATIVE_MULTIPLIER_DOMAIN')
            bound=max(bound,g['maximum_source_occupied_tiles'])
            if cursor+len(data)>TABLE:raise ValueError('OCCUPANCY_TABLE_CAPACITY')
            rom[cursor:cursor+len(data)]=data
            stride=entry['cols']*entry['tile_rows']
            for q in range(8):
                table+=(0xc00000+cursor+q*stride).to_bytes(3,'little')+bytes(1)+struct.pack('<2H',entry['cols'],entry['tile_rows'])
            cursor+=len(data)
        if len(table)!=512:raise ValueError('OCCUPANCY_PHASE_COUNT')
        bounds[role]=bound
        rom[TABLE+i*512:TABLE+(i+1)*512]=table
        # Existing X contains horizontal phase*8. Select q once per changed picture.
        start=lines.index(f'OnlineFrame{i}:');at=lines.index(' jmp OnlinePreflight',start)
        lines[at:at]=[' txa',' asl a',' asl a',' asl a',' sta $5C',' lda $4C',' and #7',' asl a',' asl a',' asl a',' clc',' adc $5C',' tax',
            f' lda.l ${0xc00000+TABLE+i*512:06X},x',' sta $66',f' lda.l ${0xc00002+TABLE+i*512:06X},x',' sta $68',
            f' lda.l ${0xc00004+TABLE+i*512:06X},x',' sta $6A',f' lda.l ${0xc00006+TABLE+i*512:06X},x',' sta $6C',
            ' lda $4C',' cmp #$8000',' ror a',' cmp #$8000',' ror a',' cmp #$8000',' ror a',' sta $6E']
    at=lines.index('WarmTestCoverage:');call=lines.index(' jsr OnlineCoverage',at)
    lines[call]=' jsr WarmSourcePresence'
    at=lines.index('.org $E000')
    lines[at:at]=[
        'WarmSourcePresence:','.a16','.i16',
        ' lda $18',' and #31',' sec',' sbc $4A',' cmp $6A',' bcs WarmPresenceAbsent',' sta $5C',
        ' lda $18',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' sec',' sbc $6E',' cmp $6C',' bcs WarmPresenceAbsent',
        ' sep #$20','.a8',' sta.l $004202',' lda $6A',' sta.l $004203',' nop',' nop',' nop',' nop',
        ' rep #$20','.a16',' lda.l $004216',' clc',' adc $5C',' tay',
        ' sep #$20','.a8',' lda [$66],y',' rep #$20','.a16',' and #255',' bra WarmPresenceDone',
        'WarmPresenceAbsent:','.a16','.i16',' lda #0','WarmPresenceDone:','.a16','.i16',' rts']
    maximum=source['backdrop_tiles']+max(bounds.values())
    if maximum>768 or maximum!=manifest['maximum_required_pairs']:raise ValueError('OCCUPANCY_CAPACITY_IDENTITY')
    if bytes(rom[0x343000:DATA])!=refs:raise ValueError('OCCUPANCY_REFCOUNT_CORRUPTION')
    return lines
