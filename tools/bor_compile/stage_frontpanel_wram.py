"""Full FP allocation admission against actual include closure and queue arena.

Separate from image encoding: a WRAM-only relocation must not invalidate all
content-addressed images. Called before build environment materialization.
"""
import re
from pathlib import Path
from compiler import ROOT
import queue_abi


def include_closure(root):
    root=Path(root).resolve();texts={}
    def visit(path):
        path=path.resolve()
        if path in texts:return
        text=path.read_text();texts[path]=text
        for line in text.splitlines():
            match=re.match(r'\s*\.include\s+"([^"]+)"',line.split(';',1)[0])
            if match:visit(path.parent/match[1])
    visit(root/'src/main.pasm')
    # Pre-integration preparation must admit the prospective module too.
    visit(root/'src/core/stage_frontpanel_bg2.pasm')
    visit(root/'src/core/stage_frontpanel.pasm')
    return texts


def allocation_proof(root=ROOT, *, texts=None, queue_spec=None):
    root=Path(root).resolve()
    texts=include_closure(root) if texts is None else texts
    spec=queue_abi.SPEC if queue_spec is None else queue_spec
    def literal(name):
        matches=[]
        for text in texts.values():
            for line in text.splitlines():
                m=re.fullmatch(r'\s*'+name+r'\s*=\s*(\$[0-9a-fA-F]+|\d+)\s*',line.split(';',1)[0])
                if m:matches.append(int(m[1][1:],16) if m[1].startswith('$') else int(m[1]))
        if len(matches)!=1:raise ValueError('FRONTPANEL_WRAM_UNBOUND: '+name)
        return matches[0]
    regions=[(name,literal(name),size) for name,size in (
        ('StageFp_BG2TileBuf',64),('StageFp_BG2ColBuf',56),('StageFp_BG2State',34),
        ('StageFp_BG2History',34*28*2),('StageFp_BG2Refs',257*2),('StageFp_BG2Columns',34*2))]
    vm_end=literal('VmCode_Wram')+literal('VM_CODE_MAX')
    guard_end=literal('VmGuardLo')+literal('VM_GUARD_LEN')
    trace=literal('G12_AnimTrace_Ring')
    owners=[('VM code',literal('VmCode_Wram'),vm_end),('VM guard',literal('VmGuardLo'),guard_end),
        ('G12 trace',trace,trace+64),('queue entire reserved arena',spec['arena_base'],spec['arena_end_exclusive']),
        ('dynamic allocator',literal('WramBuffer'),literal('WramBuffer')+
            literal('WRAM_ALLOCATION_BLOCKS')*literal('WRAM_ALLOCATION_BLOCKSIZE')),
        ('BG1 upload buffers',literal('StreamScroll_TileBufN'),literal('StreamScroll_TileBufN')+
            literal('STREAM_SCROLL_BUDGET_MAX')*32),
        ('Easy FP upload buffers',literal('StreamScrollFp_TileBufN'),literal('StreamScrollFp_TileBufN')+
            literal('STREAM_SCROLLFP_BUDGET_MAX')*16)]
    for i,(name,start,size) in enumerate(regions):
        end=start+size
        if not max(vm_end,guard_end)<=start<end<=trace or start>>16!=0x7E:
            raise ValueError('FRONTPANEL_WRAM_OUTSIDE_AUDITED_GAP: '+name)
        for other,a,b in owners+[(n,a,a+size) for n,a,size in regions[:i]]:
            if max(a,start)<min(b,end):raise ValueError('FRONTPANEL_WRAM_OVERLAP: '+name+'/'+other)
    if literal('StageFp_BG2HistoryEnd')!=regions[-1][1]+regions[-1][2]:
        raise ValueError('FRONTPANEL_WRAM_HISTORY_EXTENT')
    tile=literal('StageFp_BG2TileBuf')
    if literal('StageFp_BG2TileBank')!=tile>>16 or (tile&65535)+64>65536:
        raise ValueError('FRONTPANEL_WRAM_DMA_BANK')
    code=texts[(root/'src/core/stage_frontpanel_bg2.pasm').resolve()]
    if not re.search(r'lda #StageFp_BG2TileBank\s+sta\.l DmaRequest_SourceBank',code):
        raise ValueError('FRONTPANEL_WRAM_DMA_BANK_UNBOUND')
    # Other live literal owners/references may not enter the entire new block,
    # including alignment gaps. Indexed owners above are checked by extent.
    block_start=min(a for _,a,_ in regions);block_end=literal('StageFp_BG2HistoryEnd')
    for path,text in texts.items():
        if path==(root/'src/core/stage_frontpanel_bg2.pasm').resolve():continue
        for line in text.splitlines():
            code=line.split(';',1)[0]
            for raw in re.findall(r'\$([0-9a-fA-F]{6})\b',code):
                if block_start<=int(raw,16)<block_end:
                    raise ValueError('FRONTPANEL_WRAM_FOREIGN_OWNER: '+str(path)+': '+code.strip())
    # Existing camera/water/FP-cache tail remains independent and unchanged.
    scratch=literal('StageFp_Work')
    water=literal('StageWater_Work')
    if not (literal('StreamCacheFp_Slot2Tile')+literal('STREAM_FP_CACHE_SLOTS')*2<=water
            and water+1380==scratch and scratch+28<=literal('StreamCacheFp_SlotStamp')):
        raise ValueError('FRONTPANEL_WRAM_CACHE_TAIL')
    return dict(status='PASS',block_start=block_start,block_end_exclusive=block_end,
        allocated_bytes=sum(size for _,_,size in regions),span_bytes=block_end-block_start,
        regions=[dict(name=n,start=a,end_exclusive=a+size,bytes=size) for n,a,size in regions],
        adjacent_owners=[dict(name=n,start=a,end_exclusive=b) for n,a,b in owners],
        dma_bank=literal('StageFp_BG2TileBank'),camera_start=scratch,camera_end_exclusive=scratch+28,
        queue_target_capacity=queue_abi.TARGET_CAPACITY,include_files=len(texts))


if __name__=='__main__':
    import json
    print(json.dumps(allocation_proof(),indent=2))
