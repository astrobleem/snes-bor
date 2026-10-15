"""Candidate-specific borrowing audit; historical renderer auditors unchanged."""
import json,inspect
from pathlib import Path
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from home_borrow import transform,JOURNAL,END
import m4_source_safepoint_native as safe
from source_safepoint import transform as sp_transform
from m4_restore_spill_native import audit_branches

BASE=Path('out/byor-motu-source-safepoint-candidate-v5/native')
BASE_SHA='7cf213a9aaa467c7c1248dc0e40d35027f8dbd56a6ac3e9f81d373d216cc431b'

def audit_rom(rom,native):
    old=(BASE/'bor.sfc').read_bytes()
    if safe.sha(old)!=BASE_SHA:raise ValueError('BH_ACCEPTED_ROM_IDENTITY')
    wanted=transform((BASE/'publisher.pasm').read_text().splitlines())
    if (native/'publisher.pasm').read_text().splitlines()!=wanted:raise ValueError('BH_EXACT_SOURCE_TRANSFORM')
    sy=symbols(native/'publisher.sym');compiled=(native/'publisher.bin').read_bytes()
    branches=audit_branches([' iny' if s.strip()=='dey' else s for s in wanted],sy,compiled)
    oldsy=symbols(BASE/'publisher.sym')
    if not sy['NbCodeEnd']<0x39b000==sy['SpReadyBoundary']<sy['SpCodeEnd']<=0x39b300==sy['BhInitialize']<sy['BhCodeEnd']<0x39c000:raise ValueError('BH_CODE_COLLISION')
    expected=bytearray(old)
    ranges=[(0x398000,sy['OnlineReject']+8),(0x39a000,sy['NbCodeEnd']),
            (0x39b000,sy['SpCodeEnd']),(0x39b300,sy['BhCodeEnd'])]
    if any(old[offset(0x39b300):offset(sy['BhCodeEnd'])]):raise ValueError('BH_ROM_LEASE_NOT_ZERO')
    if any(old[offset(oldsy['NbCodeEnd']):offset(sy['NbCodeEnd'])]):raise ValueError('BH_A_CODE_EXTENSION_NOT_ZERO')
    for start,end in ranges:expected[offset(start):offset(end)]=compiled[offset(start):offset(end)]
    if expected!=rom:raise ValueError('BH_UNAUTHORIZED_ROM_CHANGE')
    with patch.object(safe,'transform',lambda src:transform(sp_transform(src))):
        count=safe.audit_movement_clone(rom,native)
    # The retained source build has physics at D800 and no enabled pending-jump
    # rows. Source/worker runtime writes to the new lease are independently trapped.
    source=symbols(Path('src/main.sym'))
    if source['SOURCE_ENTITY_PHYSICS']!=0x42d800 or any('PENDINGJUMP' in name.replace('_','').upper() for name in source):raise ValueError('BH_SOURCE_MEMORY_AUTHORITY_DRIFT')
    if any(0x42d700<=value<END for value in source.values()):raise ValueError('BH_JOURNAL_SYMBOL_CONFLICT')
    return dict(status='PASS',branches_verified=branches,movement_instructions_identical=count,
                authorized_code_ranges=ranges,journal_lease=[0x42d700,END],journal_records=64,
                source_physics_start=source['SOURCE_ENTITY_PHYSICS'],all_other_rom_bytes_identical=True)

def run(folder,source,sy,contract):
    run_case(folder,source,sy,contract)
    from m4_home_borrow_evidence import certify
    result=certify(folder)
    print(result['classification'],flush=True)

def observer(script,contract):
    import m4_consecutive_up_native as up
    up.observer(script,contract);sy=contract['native_symbols']
    with script.open('a') as f:
        f.write('local bhLease=false;local bhCanary=nil;local bhFlags={}\n')
        def cb(name,body):f.write(f"emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n")
        for name in ('BhBegin','BhPrepare','BhPreparePoolOK','BhPrepareBad','BhPrepareOK','BhRollbackEmpty','BhInvalidateFound','BhRollback','BhRestorationFenced','BhRollbackFinished','BhCommit'):
            cb(name,f"nbLog('BH_PHASE','{name}|'..nbTxn..'|'..nbWord(0x42d700)..'|'..nbWord(0x42d704)..'|'..nbWord(0x42d706)..'|'..cpDump(0x42d700,144)..'|'..cpDump(0x42d000,1536)..'|'..cpDump(0x42c000,2048)..'|'..cpDump(0x42c800,2048))")
        for name in ('BhInvalidate','BhInvalidateOK','BhInvalidateBad','BhTake','BhShouldAbort','BhNoFault','BhVerifyReady','BhReadyOK','BhReadyBad'):
            cb(name,f"nbLog('BH_COST','{name}|'..nbTxn)")
        cb('WarmCopyBackdrop',"if nbTxn>0 then nbLog('BH_BACKDROP',nbTxn..'|'..nbWord(0x342c)..'|'..nbWord(0x3464)..'|'..nbWord(0x42d70c))end")
        cb('BhTake',"local c=nbWord(0x42d704);if c<nbWord(0x42d700)then nbLog('BH_RESERVE',nbTxn..'|'..c..'|'..nbWord(0x42d710+c*2))end")
        cb('NbBegin',"if not bhLease then bhLease=true;bhCanary=cpDump(0x42d790,112);for i=0,595 do bhFlags[i]=emu.read(0x2d001+2*i,emu.memType.snesSaveRam)end end")
        for cpu in ('snes','sa1'):
            f.write("emu.addMemoryCallback(function(a,v)if bhLease then local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];if '"+cpu+"'~='snes' or pc<"+str(sy['BhInitialize'])+" or pc>="+str(sy['BhCodeEnd'])+" then nbLog('FAULT','BH_JOURNAL_OWNER:"+cpu+"|'..a..'|'..pc)end end end,emu.callbackType.write,0x2d700,0x2d78f,emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")
            f.write("emu.addMemoryCallback(function(a,v)if bhLease then nbLog('FAULT','BH_CANARY_WRITE:"+cpu+"|'..a)end end,emu.callbackType.write,0x2d790,0x2d7ff,emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")
        f.write("emu.addEventCallback(function()if bhLease and cpDump(0x42d790,112)~=bhCanary then nbLog('FAULT','BH_CANARY_CHANGED')end end,emu.eventType.endFrame)\n")
        f.write('''
emu.addMemoryCallback(function(a,v)
 if not bhLease or a%2==0 then return end
 -- Callback selection is physical; Mesen supplies the CPU bus address.
 local home=((a&0xffff)-0xd000)//2
 local before=bhFlags[home];bhFlags[home]=v
 if before==nil then nbLog('FAULT','BH_FLAG_MIRROR_UNINITIALIZED:'..a);return end
 if (before&128)~=0 and (v&128)==0 then
  local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k']
  nbLog('BH_VALID_CLEAR',nbTxn..'|'..home..'|'..pc)
  if nbWord(0x42d70c)~=2 or pc<'''+str(sy['BhClearValidity'])+''' or pc>='''+str(sy['BhRollbackFinished'])+''' then nbLog('FAULT','BH_EARLY_VALID_CLEAR')end
 end
end,emu.callbackType.write,0x2d000,0x2d4a7,emu.cpuType.snes,emu.memType.snesSaveRam)
emu.addMemoryCallback(function(a,v)
 if nbTxn<=0 then return end
 local target=emu.read(0x4371,emu.memType.snesMemory)
 local word=emu.getState()['ppu.vramAddress'];local at=word*2
 if target~=0x18 or at>=61440 then return end
 local slot=at<49152 and at//64 or (at-49152)//16
 if slot>=596 then return end
 local state=nbWord(0x42d70c);local entry=nil
 for i=0,nbWord(0x42d700)-1 do local n=nbWord(0x42d710+2*i);if (n&0x3fff)==slot then entry=n end end
 local refs=nbWord(0x42d000+2*slot);local uses=0
 for i=0,1023 do
  local h=emu.read(61440+2*i,emu.memType.snesVideoRam)+256*emu.read(61441+2*i,emu.memType.snesVideoRam)
  local l=emu.read(63488+2*i,emu.memType.snesVideoRam)+256*emu.read(63489+2*i,emu.memType.snesVideoRam)
  if h==slot or l==slot then uses=uses+1 end
 end
 nbLog('BH_HOME_DMA',nbTxn..'|'..slot..'|'..state..'|'..tostring(entry)..'|'..refs..'|'..uses..'|'..word)
 if uses~=0 or (refs&0x3fff)~=0 or (refs&0x8000)==0 or entry==nil or (entry&0x4000)==0 or state~=1 and state~=2 or state==2 and (entry&0x8000)~=0 then nbLog('FAULT','BH_HOME_DMA_AUTHORITY')end
end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
''')

def run_case(folder,source,sy,contract,policy=0,fault=0,limit=64,mode=0,valid_limit=64,later_restore=False):
    import m4_consecutive_up_native as up
    import m4_nonblank_component_native as control
    # Keep the real UP driver and independent per-field source oracle. Only
    # experiment control words and bounded observation count differ.
    body=inspect.getsource(up.run).replace('def run(folder, source, sy, contract):','def execute_home(folder, source, sy, contract):')
    body=body.replace("        m.release_input(port=0);m.write_u16(REQUEST,0xb4e9)",f"        m.write_u16(0x42d70e,{valid_limit});m.write_u16(0x42d702,{policy});m.write_u16(0x42d708,{fault});m.write_u16(0x42d70a,{limit});m.write_u16(MODE,{mode})\n        m.release_input(port=0);m.write_u16(REQUEST,0xb4e9)")
    # This replacement is inside the source string of up.run: preserve escaped
    # newlines when exec evaluates the dynamically constructed inner driver.
    body=body.replace("    with patch.object(control,'observer',observer)","    body=body.replace('range(350)','range(1200)')\n    with patch.object(control,'observer',observer)")
    if later_restore:
        at=body.rfind('        m.release_input(port=0)')
        if at<0:raise ValueError('BH_LATER_RESTORATION_DRIVER_DRIFT')
        extension="""
        if not succeeded:raise ValueError('BH_CANNOT_TEST_RESTORATION_WITHOUT_SECOND_COMMIT')
        current=next_image;next_image=None;switched=False
        field('idle-input');field('idle-input');m.write_u16(REQUEST,0xb4e8)
        for i in range(10):
            field('idle-seal')
            if startup.u16(m,SNAPSHOT+144)==4:break
        else:raise ValueError('BH_IDLE_SOURCE_SEAL_TIMEOUT')
        next_image,restoration=capture('restoration')
        if np.array_equal(current,next_image):raise ValueError('BH_IDLE_SOURCE_UNCHANGED')
        for i in range(1200):
            field('restoration',True)
            if startup.u16(m,DISPLAY_EPOCH)==4 or startup.u16(m,0x7ffb84)==1:break
        else:raise ValueError('BH_RESTORATION_TIMEOUT')
        save_checkpoint('after-restoration');field('restored-visible',True)
        if startup.u16(m,DISPLAY_EPOCH)!=4:raise ValueError('BH_RESTORATION_NOT_PUBLISHED')
"""
        body=body[:at]+body[at:].replace('        m.release_input(port=0)','        m.release_input(port=0)'+extension,1)
    ns=dict(up.__dict__,observer=observer,certify=certify_capture)
    import _harness
    # Retry only an unfinished tool advance; never repeat completed fields.
    with patch.object(_harness,'run_frames_exact',control.run_frames_exact):
        exec(body,ns);ns['execute_home'](folder,source,sy,contract)

def certify_capture(folder,contract,fields):
    import m4_consecutive_up_native as up
    r=up.certify(folder,contract,fields)
    r['classification']='HOME_BORROW_NATIVE_CAPTURE_COMPLETE'
    r['rom_sha256']=safe.sha((folder/'native/bor.sfc').read_bytes())
    return r

def run_right_control(folder,source,sy,contract):
    original=safe.observer
    def observed(script,c):
        with patch.object(safe,'observer',original):observer(script,c)
    with patch.object(safe,'audit_rom',audit_rom),patch.object(safe,'observer',observed):
        safe.run(folder,source,sy,contract)


def main():
    import argparse
    from compiler import Source
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--policy',type=int,choices=(0,1),default=0)
    p.add_argument('--fault',type=int,choices=(0,1),default=0)
    p.add_argument('--limit',type=int,default=64)
    p.add_argument('--mode',type=int,choices=(0,1,2,3),default=0)
    p.add_argument('--valid-limit',type=int,default=64)
    p.add_argument('--later-restore',action='store_true')
    p.add_argument('--right-control',action='store_true')
    a=p.parse_args();folder=a.folder.resolve()
    source=Source(Path('Masters of the Universe [v.3.0 Build 4086].pak'));sy=symbols(Path('src/main.sym'));contract=json.loads((folder/'contract.json').read_text())
    if a.right_control:run_right_control(folder,source,sy,contract)
    else:
        run_case(folder,source,sy,contract,a.policy,a.fault,a.limit,a.mode,a.valid_limit,a.later_restore)
        from m4_home_borrow_evidence import certify
        print(certify(folder)['classification'])

if __name__=='__main__':main()
