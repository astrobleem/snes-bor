"""Keep existing legacy-CGRAM exclusion valid across source-host rebinding."""
from pathlib import Path
import fcntl,shutil,hashlib,ast
from build_verify_bor_pin_slice_v1134 import symbols,off,cpu,regs,clean
from bor_linux_guard_v1132 import require_memory

ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1246';NEW=ROOT/'inputs/candidate-v1249'

def main():
    print('GUARDS',require_memory(True),flush=True);assert shutil.disk_usage(ROOT).free>18*2**30
    with (ROOT/'bor-mesen.lock').open('r+b') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);assert not NEW.exists()
        s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes();rom=bytearray(raw)
        start=off(s['SourceVisual_AllowCgramRequest']);needle=bytes.fromhex('af60177ec90100')
        at=raw.find(needle,start,start+100);assert at>=0
        rom[at:at+7]=b'\xaf'+s['SourceVisual_CompletedMagic'].to_bytes(3,'little')+bytes.fromhex('c94dc0')
        c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');assert sum(rom)&65535==c
        assert all(a==b or at<=i<at+7 or 0x7fdc<=i<0x7fe0 for i,(a,b) in enumerate(zip(raw,rom)))
        NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom)
        for name in ('main.sym','world.sym'):shutil.copyfile(OLD/name,NEW/name)
        n=0
        for campaign in (0,1,3):
          for magic in (0,0x1a60):
           for completed in (0,0xc04d):
            for mode in (0,1,2,3):
             for slot in range(8):
              for bank,source,target in ((0x7e,0x2300,0x100),(0x7e,0x2300,0x1e0),(0x7e,0x4900,0x100),(0x7e,0x2300,0xe0),(0x7e,0x2300,0x200),(0x10,0x2300,0x100)):
                q=cpu(NEW);q.a=0xab02;q.x=slot*8;q.y=123;q.d=0xa85;q.db=0;q.p=0x25
                q.write(s['Game_CampaignId'],campaign);q.write(s['SourceInput_Magic'],magic);q.write(s['SourceVisual_CompletedMagic'],completed);q.write(0x7e1760,mode)
                a=s['DmaQueue']+slot*8;q.write(a+7,bank,1);q.write(a+5,source);q.write(a+2,target)
                before=clean(q);initial=regs(q);q.run('SourceVisual_AllowCgramRequest')
                reject=campaign==3 and magic==0x1a60 and completed==0xc04d and bank==0x7e and source==0x2300 and 0x100<=target<0x200
                assert bool(q.p&1)!=reject and regs(q)[:5]==initial[:5] and q.s==initial[-1] and q.p&~1==initial[-2]&~1
                after=clean(q)
                if reject:after.pop(s['SourceVisual_LegacyCgramDrops'],None)
                assert after==before and not q.media
                if mode==1 and completed==0xc04d:
                    o=cpu(OLD,before);o.a,o.x,o.y,o.db,o.d,o.p,o.s=initial;o.run('SourceVisual_AllowCgramRequest')
                    assert regs(q)==regs(o) and clean(q)==clean(o) and q.steps==o.steps
                n+=1
        print('PASS',n,'linked dispatch cases; source transfers/BG/other campaigns unaffected; active-path instruction count and ABI exact; no queue/pin/ACK mutation',flush=True)
        for tag in ('early','full'):
            text=(ROOT/'runner'/f'head1246_{tag}_worker.py').read_text();old=hashlib.sha256(raw).hexdigest();new=hashlib.sha256(rom).hexdigest();assert text.count(old)==1
            text=text.replace(old,new,1);ast.parse(text);p=ROOT/'runner'/f'palette1249_{tag}_worker.py';assert not p.exists();p.write_text(text)
        print('BUILT: only stable completed-publication epoch substitutes transient worker mode; startup producer candidate1248 excluded',flush=True)

if __name__=='__main__':main()
