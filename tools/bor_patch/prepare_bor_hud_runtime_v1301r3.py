"""Isolated static HUD/font relocation. Default is an in-memory integration proof.

No gameplay admission, file installation or native run is performed by this
script. The seven appended tiles are the verified original FONT.GIF overflow
pieces; ordinary glyphs retain their existing linear indices and CPU cost.
"""
from pathlib import Path
from types import MethodType
import re
import signal
import sys
import time

ROOT = Path('/home/chad/bor-v1131-20261113')
OLD = ROOT/'inputs/candidate-v1297r2'
FONT = 0x328000
BODY = 0x329000
OVERFLOW = bytes.fromhex(
    '00000000000000000000000000008000'
    '11000000000000000000000000000000'
    '20000000000000000000000000000000'
    '40000000000000000000000000000000'
    '60000000000000000000000000000000'
    '08000000000000000000000000000000'
    '30000000000000000000000000000000')


def symbols(folder):
    return {n: int(o,16) if len(o)>4 else int(b+o,16)
            for b,o,n in re.findall(r'^([\da-fA-F]{2}):([\da-fA-F]{4,6})\s+(\S+)',
                                    (folder/'main.sym').read_text(),re.M)}


def off(a):
    assert a & 0xffff >= 0x8000, hex(a)
    return (a >> 16)*32768 + (a & 65535)-32768


def remap(word):
    tile = word & 1023
    if tile < 12:
        return (word & ~1023) | (tile+640)
    if 32 <= tile < 288:
        return (word & ~1023) | (tile+624)
    if 288 <= tile < 383:
        return (word & ~1023) | (tile+632)
    raise AssertionError(('not an owned old BG3 tile',hex(word)))


def installer(s,drain):
    """Boot-only queue admission; original NMI owns physical completion.

    Unlike r2 this does not disable NMI or synchronously drain existing work.
    Caller sets the base/brightness shadows only after successful admission;
    the actual NMI drains the queue before writing either hardware register.
    """
    b=bytearray();labels={};fix=[]
    def e(op,v=None,n=2):
        b.append(op)
        if v is not None:b.extend(v.to_bytes(n,'little'))
    def lng(op,n):e(op,s[n] if isinstance(n,str) else n,3)
    def lab(n):labels['HudRegion1301r3_'+n]=BODY+len(b)
    def fail_if(op):
        e(op,4,1);e(0x5c);fix.append(len(b));b.extend(b'\0'*3)
    lab('Install');e(0x08);e(0xc2,0x31,1)
    lng(0xaf,'Nmi_ScreenBrightness');e(0x29,0x80);fail_if(0xd0)
    for name,value in [('DmaRequest_SourceAddrLow',FONT&65535),('DmaRequest_TargetAddr',0xf980),('DmaRequest_Length',1632)]:
        e(0xa9,value);lng(0x8f,name)
    e(0xe2,0x20,1);e(0xa9,FONT>>16,1);lng(0x8f,'DmaRequest_SourceBank')
    e(0xa9,0,1);lng(0x8f,'DmaRequest_TypeFlags');e(0xc2,0x31,1)
    lng(0x22,'Core_Dma_Enqueue_Long');fail_if(0xb0)
    lab('Accepted');e(0xe2,0x20,1);e(0xa9,4,1);e(0x8d,0x2121);e(0xc2,0x31,1);e(0xa2,0)
    lab('PaletteLoop');e(0xe2,0x20,1);lng(0xbf,'Font_PaletteData');e(0x8d,0x2122)
    e(0xc2,0x31,1);e(0xe8);e(0xe0,8);e(0xd0,(labels['HudRegion1301r3_PaletteLoop']-(BODY+len(b)+2))&255,1)
    e(0x28);e(0x6b)
    lab('Refuse');e(0xe2,0x20,1);e(0xa9,1,1);lng(0x8f,'Nmi_InterruptFlags');e(0x8d,0x4200)
    e(0xa9,0x80,1);lng(0x8f,'Nmi_ScreenBrightness');e(0x8d,0x2100)
    lab('RefusedBlank');e(0x80,0xfe,1)
    for at in fix:b[at:at+3]=labels['HudRegion1301r3_Refuse'].to_bytes(3,'little')
    return bytes(b),labels


def construct(raw,s):
    rom=bytearray(raw);changes=[];labels={}
    def patch(at,before,after,reason):
        assert len(before)==len(after) and raw[off(at):off(at)+len(before)]==before,(reason,hex(at),before.hex())
        assert not any(max(off(at),a)<min(off(at)+len(after),a+n) for a,n,_ in changes),reason
        rom[off(at):off(at)+len(after)]=after;changes.append((off(at),len(after),reason))
    def find(name,size,before,after,reason=None):
        lo=off(s[name]);hits=[i for i in range(lo,lo+size-len(before)+1) if raw.startswith(before,i)]
        assert len(hits)==1,(name,before.hex(),hits)
        at=(s[name]&0xff0000)|0x8000|(hits[0]%32768)
        patch(at,before,after,reason or name)
        return at
    def imm(name,size,op,old,new,width=2):
        find(name,size,bytes([op])+old.to_bytes(width,'little'),bytes([op])+new.to_bytes(width,'little'))
    def table(name,size):
        at=s[name];data=raw[off(at):off(at)+size]
        values=[int.from_bytes(data[i:i+2],'little') for i in range(0,size,2)]
        assert all(288<=v&1023<383 for v in values),name
        patch(at,data,b''.join(remap(v).to_bytes(2,'little') for v in values),name)

    # A separate immutable ROM bank; no existing code/data or payload table
    # is repurposed. Physical assets below remain byte-identical to source.
    assert not any(raw[off(0x328000):off(0x328000)+32768])
    assert not any(0x328000<=v<=0x32ffff for v in s.values())
    oldfont=raw[off(s['Font_TilesData']):off(s['Font_TilesData'])+1520]
    font=oldfont+OVERFLOW;assert len(font)==1632
    patch(FONT,b'\0'*len(font),font,'immutable 102-tile font owner')
    labels['HudRegion1301r3_Font']=FONT
    # Separate BG3 data from its character-base register. Normal BG2 and
    # legacy BG3 frontpanel owners remain disjoint from the resident font.
    for name,size in [('Bg_LoadScene__hud',-1),('Bg_LoadScene_Streaming__hud_seek_busy',30)]:
        if size<0:
            at=s[name]-40;temp=dict(s);s['_hud_static_search']=at;name='_hud_static_search';size=40
        at=find(name,size,b'\xa9\x00\x20\x8d\x16\x21',b'\xa9\x00\x74\x8d\x16\x21','HUD data destination')
        labels['HudRegion1301r3_Hud'+('Static' if name=='_hud_static_search' else 'Streaming')]=at
    for name in ('Bg_LoadSceneFp_Streaming__row_resolved','Core_StreamScrollFp_ResolveRows__resolved'):
        imm(name,25,0x69,32,656)
    for name in ('StageColumnFp_FetchTilePixels','Core_StreamScrollFp_ResolveRows'):
        imm(name,1200,0x69,0x2100,0x7480)
    # Startup already is forced blank. Hardware base changes only at the
    # installer's PhysicalDone boundary, not at the old early register write.
    find('scpu_boot__bg1sc_done',45,b'\xa9\x02\x8f'+s['Nmi_BgTilesVram34'].to_bytes(3,'little'),
         b'\xa9\x06\x8f'+s['Nmi_BgTilesVram34'].to_bytes(3,'little'))
    find('SceneVideo_StopFrameTest',110,b'\xa9\x05\x8f'+s['Nmi_BgTilesVram34'].to_bytes(3,'little'),
         b'\xa9\x06\x8f'+s['Nmi_BgTilesVram34'].to_bytes(3,'little'))
    for name in ('scpu_bg3_map','Stage_Load__bg3_clear','HudOpponent_Row__clear'):
        patch(s[name]-3,b'\xa9\x00\x00',b'\xa9\x80\x02',name+' blank')
    for name in ('Hud_Play__bar_clear','Hud_Play__2p_bar_clear','Hud_Play__boss_bar_clear'):
        imm(name,12,0xa9,0,640)
    patch(s['SourceQuit_BlankRows'],b'\0'*768,b'\x80\x02'*384,'End Game immutable blank rows')
    for name in ('Text_EmitGlyph__have','HudOpponent_Row__print','BorSetSelect_Emit__glyph'):
        imm(name,35,0x69,288,920)
    imm('BorSetSelect_Blank',30,0xa9,0x2520,0x2798)
    for name,have in [('Hud_DrawBar','Hud_DrawBar__have'),
                      ('Hud_Play__2p_drawbar','Hud_Play__2p_drawbar_have'),
                      ('Hud_Play__boss_bar_drawbar','Hud_Play__boss_bar_drawbar_have')]:
        imm(name,35,0xa9,10,138,1)
        imm(have,50,0x69,1,129,1)
        imm(have,50,0xa9,11,139,1)
        lo=off(s[name]);hi=lo+125
        needle=b'\xa9\x20\x9f'
        hits=[i for i in range(lo,hi) if raw.startswith(needle,i)]
        assert len(hits)==3,(name,hits)
        for i in hits:patch((s[name]&0xff0000)|0x8000|(i%32768),needle,b'\xa9\x22\x9f',name+' high byte')
    # Retained opponent helper contains 16-bit complete entries, not the
    # byte-wise bar encoding above. Carry/timing and all row writes stay exact.
    for name in ('HudOpponent_DrawBar','OpponentAlign1297r2'):
        size=150 if name=='HudOpponent_DrawBar' else 434
        lo=off(s[name]);part=raw[lo:lo+size]
        for before,after in [(b'\xa9\x0a\x20',b'\xa9\x8a\x22'),
                             (b'\xa9\x0b\x20',b'\xa9\x8b\x22'),
                             (b'\x69\x01\x00\x09\x00\x20',b'\x69\x81\x02\x09\x00\x20')]:
            hits=[i for i in range(len(part)-len(before)+1) if part.startswith(before,i)]
            assert hits,(name,before.hex())
            for i in hits:patch(s[name]+i,before,after,name+' complete entry')
    for name,size in [('StageTimerHost_TimerRows',1800),('StageTimerHost_TimeOverRow',18),
                       ('SourceScoreRom_P1Rows',6400),('SourceScoreRom_P2Rows',6400)]:table(name,size)
    # Replace only the boot initializer's own body, using its dead space for
    # a genuine bank-zero RTS/RTL bridge to the unchanged queue dispatcher.
    init=s['Core_Text_Init'];span=s['Text_EmitGlyph']-init;assert span==74
    drain=init+5;labels['HudRegion1301r3_DrainLong']=drain
    header=b'\x22'+BODY.to_bytes(3,'little')+b'\x60\x20'+(s['Core_Dma_ProcessQueue']&65535).to_bytes(2,'little')+b'\x6b'
    patch(init,raw[off(init):off(init)+span],header+b'\xea'*(span-len(header)),'boot initializer and drain bridge')
    body,newlabels=installer(s,drain);labels.update(newlabels)
    patch(BODY,b'\0'*len(body),body,'boot-only original-path admission')
    # No caller may enter the displaced old palette loop independently.
    palette=s['Core_Text_Init__pal_loop']
    for op,width in [(0x20,2),(0x22,3),(0x5c,3)]:
        needle=bytes([op])+palette.to_bytes(3,'little')[:width]
        assert needle not in raw[:32768],('unexpected independent palette caller',needle.hex())
    checksum=sum(rom)&65535
    rom[0x7fdc:0x7fe0]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    assert sum(rom)&65535==checksum
    return bytes(rom),labels,changes,font


def verify(s,raw,rom,labels,font):
    sys.path.insert(0,str(ROOT/'runner'))
    from bor_owned_cpu_v610 import Cpu
    paths={False:ROOT/'inputs/in-memory-v1301r3-old',True:ROOT/'inputs/in-memory-v1301r3-new'}
    sy=dict(s);sy.update(labels)
    for new,data in [(False,raw),(True,rom)]:
        Cpu.assets[str((paths[new]/'product').resolve())]=(data,sy)
    def cpu(new=True):
        q=Cpu(paths[new]);q.db=0;q.d=0xa00;q.p=4;q.s=0x1dff
        return q
    def blob(q,at,size):return bytes(q.byte(at+i) for i in range(size))
    def words(data):return [int.from_bytes(data[i:i+2],'little') for i in range(0,len(data),2)]
    count=0
    # Actual linked init and entire NMI; explicit boot-idle controls, modeled
    # PPU transport. No runtime/beam timing claim follows from this model.
    good=0
    for cursor in range(0,64,8):
        for row_slot in (-1,)+tuple(range(8)):
            for skip in (False,True):
                q=cpu();q.db=0;q.write(s['Nmi_InterruptFlags'],129,1);q.write(0x4200,129,1)
                q.write(s['Nmi_ScreenBrightness'],128,1);q.write(0x2100,128,1);q.write(0x210c,2,1)
                q.write(s['DmaQueue_CurrentSlot'],cursor)
                if row_slot>=0:
                    at=s['DmaQueue']+row_slot*8
                    for delta,value,width in [(0,64,2),(2,0xd100,2),(4,64,1),(5,0x2700,2),(7,0x7e,1)]:q.write(at+delta,value,width)
                    q.write(s['DmaQueue_BudgetTotal'],64)
                font_slot=cursor if cursor!=row_slot*8 else (cursor+8)%64
                write0=q.write;completed=[]
                def write(self,at,v,n=2):
                    at=self.phys(at);v&=(1<<(8*n))-1
                    if at==0x210c and v==6 or at==0x2100 and not v&128:
                        assert (FONT,0xf980,1632) in completed,'exposure before physical completion'
                    if at==s['DmaQueue']+font_slot+4 and v==0:
                        assert (FONT,0xf980,1632) in completed,'retirement before physical completion'
                    if at!=0x420b:return write0(at,v,n)
                    assert self.byte(0x2100)&128
                    assert v==128 and n==1 and self.byte(0x4370)==1 and self.byte(0x4371)==24 and self.byte(0x2115)==128
                    src=self.read(0x4372)|(self.byte(0x4374)<<16);size=self.read(0x4375);target=self.read(0x2116)*2
                    assert (src,target,size) in ((FONT,0xf980,1632),(s['TextStaging'],0xd100,64))
                    assert (src,target,size) not in completed
                    completed.append((src,target,size));self.media.append((src,target,size))
                    for i in range(size):self.m[0x800000+target+i]=self.byte(src+i)
                    write0(0x4372,(src+size)&65535);write0(0x4375,0);write0(0x2116,(target+size)//2)
                q.write=MethodType(write,q)
                before=(q.p,q.db,q.d,q.s)
                assert q.run('Core_Text_Init',long=False)=='return'
                assert (q.p,q.db,q.d,q.s)==before and not completed
                assert q.byte(s['DmaQueue']+font_slot+4)==64
                assert q.byte(0x210c)==2 and q.byte(0x4200)==129
                q.write(s['Nmi_BgTilesVram34'],6,1);q.write(s['Nmi_ScreenBrightness'],15,1)
                if skip:
                    q.write(s['Nmi_FrameBusy'],1,1)
                    assert q.run('Core_Nmi_Play',long=False)=='return'
                    assert not completed and q.byte(0x210c)==2 and q.byte(0x2100)==128
                    q.write(s['Nmi_FrameBusy'],0,1);q.write(s['Nmi_Busy'],0,1)
                assert q.run('Core_Nmi_Play',long=False)=='return'
                assert len(completed)==1+(row_slot>=0)
                assert bytes(q.m[0x800000+0xf980+i] for i in range(1632))==font
                assert q.byte(0x210c)==6 and q.byte(0x2100)==15
                assert q.read(s['DmaQueue_BudgetTotal'])==0
                good+=1
    bad=0
    for cause in ('live','full','reserved'):
        q=cpu();q.db=0;q.write(s['Nmi_InterruptFlags'],129,1);q.write(s['Nmi_ScreenBrightness'],128,1)
        if cause=='live':q.write(s['Nmi_ScreenBrightness'],15,1)
        else:
            for i in range(8):q.write(s['DmaQueue']+i*8+4,64 if cause=='full' else s['DMA_OPT_RESERVED'],1)
        queue=blob(q,s['DmaQueue'],64);budget=q.read(s['DmaQueue_BudgetTotal'])
        q.run('Core_Text_Init',long=False,stop=labels['HudRegion1301r3_RefusedBlank'])
        assert q.pc==labels['HudRegion1301r3_RefusedBlank'] and not q.media,(cause,hex(q.pc),q.media)
        assert blob(q,s['DmaQueue'],64)==queue and q.read(s['DmaQueue_BudgetTotal'])==budget
        assert 0x210c not in q.writes
        bad+=1
    print('PASS_LINKED_BOOT_NMI',good,bad,'real queue/init/whole-NMI; busy skip cannot expose base; full/reserved refusal')

    # Ordinary text: identical instruction count, source character selection
    # and staging bounds for all 256 inputs; only the owned tile ID changes.
    count=0
    for code in range(256):
        for offset in (0,62,64):
            a,b=cpu(False),cpu()
            for q in (a,b):q.a=code;q.write(s['Text_StagingOffset'],offset);q.run('Text_EmitGlyph',long=False)
            assert a.steps==b.steps and a.read(s['Text_StagingOffset'])==b.read(s['Text_StagingOffset'])
            if offset<64:assert b.read(s['TextStaging']+offset)==remap(a.read(s['TextStaging']+offset))
            else:assert not any(s['TextStaging']<=x<s['TextStaging']+64 for x in b.writes)
            count+=1
    print('PASS_TEXT_RELOCATION',count,'input/bounds cases; ordinary instruction count unchanged')

    # Two independently protected player rows, including no target, aliases,
    # health extremes, pending retry and physical half-row ownership.
    count=0
    for player in (0,1):
        for target in (0,267):
            for hp in (0,1,31,64,255):
                pair=[]
                for new in (False,True):
                    q=cpu(new)
                    for name,value,width in [('Game_CampaignId',3,1),('G13_TwoPlayerEnabled',1,1),
                        ('HudOpponent_Player',player*2,2),('HudOpponent_BufferOffset',player*64,2),
                        ('HudOpponent_Dirty',0x101,2)]:q.write(s[name],value,width)
                    q.write(s['HudOpponent_Targets']+player*2,target)
                    q.write(0x7e0a00+266+s['CHAR_HP'],hp,1)
                    q.write(0x7e0a00+266+s['CHAR_ROSTER_INDEX'],2,1)
                    q.run('HudOpponent_Row',long=False);pair.append(q)
                a,b=pair;base=s['HudOpponent_Rows']+player*64
                expected=b''.join(remap(v).to_bytes(2,'little') for v in words(blob(a,base,64)))
                assert blob(b,base,64)==expected,(player,target,hp,blob(b,base,64).hex(),expected.hex())
                assert a.steps==b.steps and blob(a,s['DmaQueue'],64)==blob(b,s['DmaQueue'],64)
                original=blob(b,s['HudOpponent_Rows'],128)
                b.write(0x7e0a00+266+s['CHAR_HP'],13,1);b.run('HudOpponent_Row',long=False)
                assert blob(b,s['HudOpponent_Rows'],128)==original
                write0=b.write
                def write(self,at,v,n=2):
                    at=self.phys(at);v&=(1<<(8*n))-1
                    if at!=0x420b:return write0(at,v,n)
                    src=self.read(0x4372)|(self.byte(0x4374)<<16)
                    size=self.read(0x4375);dst=self.read(0x2116)*2
                    assert size==32 and dst in (0xd100+player*32,0xd140+player*32)
                    assert self.byte(s['DmaQueue']+self.read(s['DmaQueue_CurrentSlot'])+4)==0x44
                    self.media.append((src,dst,size))
                    for i in range(size):self.m[0x800000+dst+i]=self.byte(src+i)
                    write0(0x4372,(src+size)&65535);write0(0x4375,0);write0(0x2116,(dst+size)//2)
                b.write=MethodType(write,b);b.run('Core_Dma_ProcessQueue',long=False)
                assert b.media==[(base,0xd100+player*32,32),(base+32,0xd140+player*32,32)]
                assert b.read(s['DmaQueue_BudgetTotal'])==0
                count+=1
    print('PASS_PROTECTED_ROWS',count,'both-player cases; glyph/bar/blank remapping exact; physical source lifetime unchanged')

    count=0
    for name,buffer in [('Hud_DrawBar','HudStaging'),('Hud_Play__2p_drawbar','HudP2Staging'),
                        ('Hud_Play__boss_bar_drawbar','HudBossStaging')]:
        for hp in range(256):
            a,b=cpu(False),cpu()
            for q in (a,b):q.a=hp;q.x=4;q.run(name,long=False)
            assert a.steps==b.steps and a.x==b.x and a.y==b.y and a.p==b.p,(name,hp)
            at=s[buffer]+6
            assert words(blob(b,at,20))==[remap(v) for v in words(blob(a,at,20))]
            count+=1
    for code in range(256):
        a,b=cpu(False),cpu()
        for q in (a,b):q.a=code;q.x=6;q.run('BorSetSelect_Emit',long=False)
        assert a.steps==b.steps and b.read(s['TextStaging']+6)==remap(a.read(s['TextStaging']+6))
        count+=1
    q=cpu();q.run('BorSetSelect_Blank',long=False)
    assert words(blob(q,s['TextStaging'],64))==[0x2798]*32;count+=1
    for slot in (0,127,255):
        for attr in range(32):
            a,b=cpu(False),cpu()
            for q in (a,b):
                q.write(s['StreamStageFp_Slot'],slot);q.write(s['StreamStageFp_Attr'],attr,1)
                q.write(s['StreamScrollFp_PendTile'],2)
                q.run('Core_StreamScrollFp_ResolveRows__resolved',long=False,
                      stop=s['Core_StreamScrollFp_ResolveRows__row'])
            assert a.steps==b.steps
            assert b.read(s['StreamScrollFp_ColBuf']+4)==remap(a.read(s['StreamScrollFp_ColBuf']+4))
            count+=1
    print('PASS_REMAINING_MAP_PRODUCERS',count,'health/bar, selection and legacy-frontpanel slot/attribute cases')

    # Actual immutable MSU records establish the static HUD extent and blank
    # tile contents; do not infer a maximum from an arbitrary address gap.
    with (ROOT/'inputs/media/bor.msu').open('rb') as f:
        header=f.read(16);n=header[10];f.seek(int.from_bytes(header[12:16],'little'));rows=f.read(n*40)
        payloads=[]
        for i in range(n):
            row=rows[i*40:(i+1)*40];assert row[5]==12
            f.seek(int.from_bytes(row[24:28],'little'));data=f.read(192)
            assert len(data)==192 and data[:16]==b'\0'*16
            payloads.append(data)
    for kind,end in [('Static','Bg_LoadScene__hud_done'),('Streaming','Bg_LoadScene_Streaming__hud_done')]:
        q=cpu();q.write(s['BgRecordStaging']+5,12,1)
        q.write(0x2100,128,1);q.write(0x4200,1,1);read0=q.byte;write0=q.write;index=[0];out=[]
        def read(self,at):
            if at==0x2001:
                assert index[0]<192
                v=payloads[0][index[0]];index[0]+=1;return v
            return read0(at)
        def write(self,at,v,n=2):
            if at in (0x2118,0x2119):
                assert n==1 and self.read(0x2116)==0x7400
                assert at==0x2118+len(out)%2
                out.append(v&255)
            return write0(at,v,n)
        q.byte=MethodType(read,q);q.write=MethodType(write,q)
        q.run('HudRegion1301r3_Hud'+kind,long=False,stop=s[end])
        assert bytes(out)==payloads[0] and index[0]==192
    for name in ('scpu_bg3_map','Stage_Load__bg3_clear'):
        q=cpu();q.a=640;q.x=1024;out=[];write0=q.write
        def write(self,at,v,n=2):
            if at==0x2118:out.append(v&65535)
            return write0(at,v,n)
        q.write=MethodType(write,q);q.run(name,long=False,stop=s[name]+6)
        assert out==[640]*1024
    print('PASS_STATIC_OWNERS',n,'actual MSU HUD extents/transparent tile0; both linked loaders and1024-word scene clears')
    # Scene video bounds in installed code: two character buffers with at most
    # 12,288 bytes plus one 32-byte blank; two 2,048-byte maps. Neither reaches
    # static HUD E800 or font F980. Palette fidelity after video remains a
    # distinct preexisting issue; this does not invent palette preservation.
    assert b'\xc9\x01\x30' in raw[off(s['SceneVideo_LoadFrame__map_ok']):off(s['SceneVideo_LoadFrame__tile_max_ok'])]
    assert max(0x4000+12288+32,0xc800+2048)<0xe800
    assert rom[off(s['SourceQuit_BlankRows']):off(s['SourceQuit_BlankRows'])+768]==b'\x80\x02'*384
    print('PASS_SCENE_RANGES video character/map bounds exclude static owners; immutable quit clear translated')


def save_isolated(raw,rom,s,labels):
    import ast
    import hashlib
    import shutil
    new=ROOT/'inputs/candidate-v1301r3'
    assert not new.exists()
    assert shutil.disk_usage(ROOT).free>18*2**30
    replacements=dict(labels,Font_TilesData=FONT,FONT_DATA_BANK=FONT>>16,
        FONT_TILE_BYTES=1632,FONT_TILES_VRAM_WORD=0x7cc0,FONT_TILE_INDEX_BASE=920,
        BG3_TILES_VRAM_WORD=0x6000,FP_TILES_VRAM_WORD=0x7480,FP_TILE_INDEX_BASE=656,
        HUD_TILE_BLANK=640,HUD_TILE_FILL_BASE=641,HUD_TILE_CAP_LEFT=650,HUD_TILE_CAP_RIGHT=651)
    sym=(OLD/'main.sym').read_text()
    # Replace existing definitions, rather than relying on ambiguous duplicate
    # labels in a debugger or replay parser. Retain all original ROM addresses.
    for name,value in replacements.items():
        line=f'{value>>16:02X}:{value&65535:04X} {name}'
        pattern=r'^[\da-fA-F]{2}:[\da-fA-F]{4,6}\s+'+re.escape(name)+r'\s*$'
        if name in s:
            sym,n=re.subn(pattern,line,sym,flags=re.M);assert n==1,(name,n)
        else:sym+='\n'+line
    workers=[]
    for mode in ('early','full'):
        text=(ROOT/f'runner/opponentalign1297r2_{mode}_worker.py').read_text()
        oldhash=hashlib.sha256(raw).hexdigest();assert text.count(oldhash)==1
        text=text.replace(oldhash,hashlib.sha256(rom).hexdigest(),1)
        ast.parse(text);out=ROOT/f'runner/hudregion1301r3_{mode}_worker.py'
        assert not out.exists();workers.append((out,text))
    new.mkdir();(new/'bor.sfc').write_bytes(rom);(new/'main.sym').write_text(sym+'\n')
    shutil.copyfile(OLD/'world.sym',new/'world.sym')
    for path,text in workers:path.write_text(text)
    print('ISOLATED_CANDIDATE_WRITTEN',str(new),'unchanged assets/deployment; native qualification REQUIRED')


def main():
    import contextlib
    import fcntl
    build=sys.argv[1:]==['--build']
    assert build or not sys.argv[1:]
    if build:
        sys.path.insert(0,str(ROOT/'runner'))
        from bor_linux_heavy_v1296 import inherited_fds
        from bor_linux_guard_v1132 import require_memory
        inherited_fds();print('BUILD_GUARDS',require_memory(start=True),flush=True)
    with (ROOT/'bor-mesen.lock').open('r+b') if build else contextlib.nullcontext() as lease:
        if build:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        execute(build)


def execute(build):
    signal.alarm(12);started=time.monotonic()
    s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes()
    rom,labels,changes,font=construct(raw,s)
    print('IN_MEMORY_INTEGRATION',len(changes),'asserted patch ranges;',len(font),'font bytes;',
          labels['HudRegion1301r3_RefusedBlank']+2-BODY,'boot-only helper bytes')
    verify(s,raw,rom,labels,font)
    if build:save_isolated(raw,rom,s,labels)
    else:print('NO_INSTALL no ROM/symbol/source/asset files written; native admission remains disabled')
    print('REMAINING guarded build/native startup, video return, actual PPU/gameplay; overflow-glyph emission and full-name packets still disabled')
    signal.alarm(0);print('SECONDS',round(time.monotonic()-started,3))


if __name__=='__main__':main()
