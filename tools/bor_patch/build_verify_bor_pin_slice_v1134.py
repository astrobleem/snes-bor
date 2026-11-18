"""Isolated linked-immediate build; execute unchanged pin/queue instructions."""
from pathlib import Path
import fcntl,shutil,sys,re
from bor_owned_cpu_v610 import Cpu

ROOT=Path('/home/chad/bor-v1131-20261113')
sys.path.insert(0,str(ROOT/'runner'))
from bor_linux_guard_v1132 import require_memory

def symbols(folder):
    result={}
    for line in (folder/'main.sym').read_text().splitlines():
        m=re.match(r'([\da-fA-F]{2}):([\da-fA-F]{4,6})\s+(\S+)',line)
        if m:
            b,o,n=m.groups();result[n]=int(o,16) if len(o)>4 else int(b+o,16)
    return result

def off(at):return (at>>16)*32768+(at&65535)-32768

def cpu(folder,mem=None):
    key=str((folder/'product').resolve())
    if key not in Cpu.assets:Cpu.assets[key]=((folder/'bor.sfc').read_bytes(),symbols(folder))
    return Cpu(folder,mem)

def regs(q):return q.a,q.x,q.y,q.db,q.d,q.p,q.s
def clean(q):return {a:v for a,v in q.m.items() if v and not 0x7e1c00<=a<=0x7e1fff}

def seed(folder):
    q=cpu(folder);s=q.sy
    for n,v in [('PPBoot',1),('Game_CampaignId',3),('Nmi_ObjSel',0xc2),('PPEpoch',1)]:q.write(s[n],v)
    q.write(0x7e1760,1);q.write(0x7e175e,2)
    for i in (0,1):
        a=0x411900+i*256;q.write(a+0xe6,9);q.write(a+0xf6,1)
        a=0x7e0a00+i*133
        for n,v in [('CHAR_INPUT_DRIVEN',1),('CHAR_ROSTER_INDEX',22),('CHAR_HP',64)]:q.write(a+s[n],v,1)
    q.write(0x43a840,0x5343)
    p=s['PPPreplan'];q.write(p,0x4e50);q.write(p+2,12);q.write(p+4,1);q.write(p+6,3);q.write(p+12,1)
    for i in range(12):
        row=i*8;identity=100+i;q.write(p+32+i*4,row);q.write(p+34+i*4,identity)
        c=s['SourceVisual_BlockCache']+row
        for o,v in [(0,identity),(2,2),(4,0x400),(6,1)]:q.write(c+o,v)
        q.write(s['SVActor_HeldBlocks']+row,1)
    q.write(p+96,0);q.write(p+98,500)
    q.write(s['SourceVisual_PaletteCache'],500);q.write(s['SourceVisual_PaletteCache']+3,1,1)
    q.write(s['SVActor_HeldPalettes'],1)
    # Existing physical hold/receipt must not be consumed by preparation.
    q.write(s['SourceAttackOwned_Hold'],1);q.write(s['SourceAttackOwned_SavedPending'],7)
    return q

def verify(old,new):
    cases=0
    # Every flags value in every real queue position. Nonempty admitted rows
    # retain the old budget3; rejected/owned/malformed rows stay rejected.
    for slot in range(8):
      for flag in range(256):
        a=cpu(old);b=cpu(new)
        for q in (a,b):
            row=q.sy['DmaQueue']+slot*8
            q.write(row,32);q.write(row+4,flag,1);q.write(row+5,0x6000);q.write(row+7,0x7e,1)
            q.run('PPPreplanQueueBudget')
        assert regs(a)==regs(b)
        am,bm=clean(a),clean(b)
        if a.p&1 and not flag&0x40:
            assert a.read(a.sy['PPRootControl']+18)==5 and b.read(b.sy['PPRootControl']+18)==7
            for at in (a.sy['PPRootControl']+18,a.sy['PPRootControl']+19):am.pop(at,None);bm.pop(at,None)
        assert am==bm,(slot,flag)
        cases+=1
    a=seed(old);b=seed(new);initial=regs(b);steps=[]
    for expected in (7,12):
        before=b.steps;b.run('PPPreplanNmi');steps.append(b.steps-before)
        assert b.read(b.sy['PPRootActive']+2)==expected
        assert b.read(b.sy['PPRootActive'])==(0x5230 if expected==7 else 0x524c)
        assert regs(b)==initial and not b.media
    for _ in range(3):a.run('PPPreplanNmi')
    am,bm=clean(a),clean(b)
    for at in (a.sy['PPRootControl']+18,a.sy['PPRootControl']+19):am.pop(at,None);bm.pop(at,None)
    assert am==bm,'final ownership/image/ACK state must match the old three visits'
    cases+=1
    print('PIN_SLICES',steps,'instructions; timing requires native evidence',flush=True)
    for row in range(12):
      for delta,value in [(0,999),(2,1),(4,0x401),(6,3)]:
        q=seed(new);cache=q.sy['SourceVisual_BlockCache']+row*8;q.write(cache+delta,value)
        for _ in range(2):
            q.run('PPPreplanNmi')
            if not q.read(q.sy['PPRootActive']):break
        assert not q.read(q.sy['PPRootActive']) and not q.media
        for i in range(12):assert q.read(q.sy['SVActor_HeldBlocks']+i*8)==1
        cases+=1
    for actor in (0,1):
      for field,value in [(0xe4,7),(0xe6,8),(0xf6,0),(0xfc,1),(6,3)]:
        q=seed(new);q.run('PPPreplanNmi');q.write(0x411900+actor*256+field,value)
        q.run('PPPreplanNmi');assert not q.read(q.sy['PPRootActive']) and not q.media
        assert q.read(q.sy['SourceAttackOwned_Hold'])==1 and q.read(q.sy['SourceAttackOwned_SavedPending'])==7
        for i in range(12):assert q.read(q.sy['SVActor_HeldBlocks']+i*8)==1
        cases+=1
    print('PASS_LINKED_PIN_SLICE',cases,'queue matrix, exact final ownership/ABI, each-row identity/readiness/format/owner, both-player cancellation',flush=True)

def main():
    assert Path(__file__).resolve().parent==ROOT/'runner'
    print('BUILD_GUARDS',require_memory(start=True),flush=True)
    assert shutil.disk_usage(ROOT).free>18*1024**3
    with (ROOT/'bor-mesen.lock').open('r+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=ROOT/'inputs/candidate';new=ROOT/'inputs/candidate-v1134'
        assert not new.exists()
        s=symbols(old);rom=bytearray((old/'bor.sfc').read_bytes())
        at=off(s['PPQMain989_Long387'])
        assert rom[at:at+4]==b'\xa9\x05\x00\x82'
        target=at+6+int.from_bytes(rom[at+4:at+6],'little',signed=True)
        assert target==off(s['PPPreplanQueueReady'])
        rom[at+1]=7
        checksum=sum(rom)&65535
        rom[0x7fdc:0x7fe0]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
        assert sum(rom)&65535==checksum
        original=(old/'bor.sfc').read_bytes()
        assert all(a==b or i==at+1 or 0x7fdc<=i<0x7fe0 for i,(a,b) in enumerate(zip(original,rom)))
        new.mkdir();(new/'bor.sfc').write_bytes(rom)
        for name in ('main.sym','world.sym'):shutil.copyfile(old/name,new/name)
        print('BUILT_ONE_IMMEDIATE',hex(s['PPQMain989_Long387']),5,7,flush=True)
        verify(old,new)

if __name__=='__main__':main()
