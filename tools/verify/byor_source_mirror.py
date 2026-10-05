"""Opt-in read-only native source-mirror publication journal."""
import json
import os
from pathlib import Path


def observer_script(symbols):
    path=os.environ.get('BYOR_MIRROR_TRACE')
    if not path:
        return ''
    from game_s8_stage_bounds import lorom_offset
    offset=lorom_offset(symbols['SourceVisual_WriteMirror__emit'])
    target=Path(path).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    # Key low word encodes roster and animation role, not source map.
    fields=['Nmi_FrameCounter','Game_StageIndex','Stage_Mirror','SourceVisual_Key',
            'SourceVisual_EmitPieceX','SourceVisual_EmitPieceY','SourceVisual_EmitPieceWidth',
            'SourceVisual_EmitPieceHeight','OamSetSprite_Tile','OamSetSprite_Attr']
    addresses=','.join(str(symbols[f]) for f in fields)
    return f'''
local _byor_mirror=assert(io.open({json.dumps(target.as_posix())},'a'))
local _byor_mirror_fields={{{addresses}}}
emu.addMemoryCallback(function()
 local row={{}}
 for i,a in ipairs(_byor_mirror_fields) do
  row[i]=tostring(emu.read(a,emu.memType.snesMemory)+256*emu.read(a+1,emu.memType.snesMemory))
 end
 _byor_mirror:write(table.concat(row,'|'),string.char(10)); _byor_mirror:flush()
end,emu.callbackType.exec,{offset},{offset},emu.cpuType.snes,emu.memType.snesPrgRom)
'''


def resource_observer_script(symbols):
    """Read-only publication checks against catalog piece and resident bindings."""
    path=os.environ.get('BYOR_SOURCE_RESOURCE_TRACE')
    if not path:
        return ''
    from game_s8_stage_bounds import lorom_offset
    offset=lorom_offset(symbols['SourceVisual_WriteCurrentPiece'])
    target=Path(path).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    a={k:symbols[k] for k in ('SourceVisual_PieceIndex','SourceVisual_PieceTable',
        'SourceVisual_BaseTile','SourceVisual_Record','SourceVisual_State',
        'SourceVisual_ActorMapBase','SourceVisual_ActorPieceMap',
        'SourceVisual_BlockCache','SourceVisual_PaletteCache','OamSetSprite_Tile',
        'OamSetSprite_Attr','OamSetSprite_Hi','SourceVisual_EmitPieceX')}
    return f"""
local _byor_resources={json.dumps(target.as_posix())}
local _byor_count=0
local _byor_tile=0
local _byor_block=0
local _byor_palette=0
local _byor_hi=0
local _byor_faults=assert(io.open(_byor_resources..'.faults','w'))
local function _byor_rw(a) return emu.read(a,emu.memType.snesMemory)+256*emu.read(a+1,emu.memType.snesMemory) end
local function _byor_rb(a) return emu.read(a,emu.memType.snesMemory) end
emu.addMemoryCallback(function()
 _byor_count=_byor_count+1
 local piece={a['SourceVisual_PieceTable']}+16*_byor_rw({a['SourceVisual_PieceIndex']})
 local tile=_byor_rw(piece+14)%512
 if _byor_rb({a['OamSetSprite_Tile']})~=tile%256 or _byor_rb({a['OamSetSprite_Attr']})%2~=math.floor(tile/256) or _byor_rw({a['SourceVisual_BaseTile']})~=0 then _byor_tile=_byor_tile+1 end
 local slot=_byor_rb({a['SourceVisual_ActorPieceMap']}+_byor_rw({a['SourceVisual_ActorMapBase']})+_byor_rw({a['SourceVisual_PieceIndex']}))
 local cache={a['SourceVisual_BlockCache']}+slot*8
 if _byor_rw(cache)~=_byor_rw(piece+12) or _byor_rw(cache+2)~=2 then _byor_block=_byor_block+1 end
 local localpal=_byor_rb(piece+8)
 local physical=_byor_rb({a['SourceVisual_State']}+_byor_rw({a['SourceVisual_Record']})+16+localpal)-1
 if physical<0 or physical>7 or math.floor(_byor_rb({a['OamSetSprite_Attr']})/2)%8~=physical or _byor_rw({a['SourceVisual_PaletteCache']}+physical*8)~=_byor_rw(piece+10) or _byor_rb({a['SourceVisual_PaletteCache']}+physical*8+3)~=1 then _byor_palette=_byor_palette+1;_byor_faults:write(table.concat({{_byor_count,physical,_byor_rb({a['OamSetSprite_Attr']}),_byor_rw({a['SourceVisual_PaletteCache']}+physical*8),_byor_rw(piece+10),_byor_rb({a['SourceVisual_PaletteCache']}+physical*8+3)}},'|'),string.char(10));_byor_faults:flush() end
 local hi=_byor_rb({a['OamSetSprite_Hi']})
 local wanted=math.floor(_byor_rw({a['SourceVisual_EmitPieceX']})/256)%2+2*math.floor(_byor_rw(piece+14)/32768)
 if hi~=wanted then _byor_hi=_byor_hi+1 end
end,emu.callbackType.exec,{offset},{offset},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addEventCallback(function()
 local f=assert(io.open(_byor_resources,'w'))
 f:write(table.concat({{_byor_count,_byor_tile,_byor_block,_byor_palette,_byor_hi}},'|'),string.char(10));f:close()
end,emu.eventType.endFrame)
"""
