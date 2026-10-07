"""Actual WAIT/role collector/camera handoff against pinned C output vectors."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from actor_s5_entity_fixture import symbols
from m4_camera_bounds_native import LUA as BOUNDS_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

INIT=r'''
 for i=0,127 do put(0x414004+i*80,0,4);put(0x40c048+i*96,0,4)end
 set('SourceCameraMotion4086_Ready',0xb5db);set('SourceCameraMotion4086_Status',0)
 for _,pair in ipairs({{'Direction','direction'},{'Width','width'},{'Height','height'},{'HRes','hres'},{'VRes','vres'},{'Rocking','rocking'}})do set('SourceCameraMotion4086_'..pair[1],c[pair[2]])end
 for _,pair in ipairs({{'Speed','speed'},{'OffsetX','offsetx'},{'OffsetZ','offsetz'},{'MinX','minx'},{'MaxX','maxx'},{'MinZ','minz'},{'MaxZ','maxz'},{'Blockade','blockade'}})do set('SourceCameraMotion4086_'..pair[1],c[pair[2]],4)end
 set('VmSourceWorld_AdvanceX',c.x,4);set('VmSourceWorld_AdvanceY',c.y,4);set('VmSourceWorld_ScrollAxis',0);set('VmSourceWorld_Time',c.time,4)
 set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_State',2);set('SourceScrollerPrefix4086_ScrollDX',0,4);set('SourceScrollerPrefix4086_ScrollDY',0,4)
 set('SourceStageProducer4086_Ready',0xb5d6);set('SourceStageProducer4086_State',4);set('SourceStageProducer4086_Position',c.pos,4);set('SourceStageProducer4086_Waiting',c.waiting);set('SourceStageProducer4086_GoTime',c.go_time,4)
 set('SourceWait4086_Ready',0xb5d9);set('SourceWait4086_Status',0);set('SourceWait4086_NoReset',c.noreset,4);set('SourceWait4086_SetTime',c.settime,4);set('SourceWait4086_TimeLeft',c.timeleft,4)
 put(0x414004+100*80,c.enemies,4);put(0x40c048+100*96,2,4)
 if c.motion_bad=='ready'then set('SourceCameraMotion4086_Ready',0)
 elseif c.motion_bad=='width'then set('SourceCameraMotion4086_Width',0)
 elseif c.motion_bad=='axis'then set('VmSourceWorld_ScrollAxis',1)end
'''
OBS=r'''
 emu.log('CAMERAMOTION|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceCameraMotion4086_Status)..'|'..dw(sy.VmSourceWorld_AdvanceX)..'|'..dw(sy.VmSourceWorld_AdvanceY)..'|'..dw(sy.SourceScrollerPrefix4086_ScrollDX)..'|'..dw(sy.SourceScrollerPrefix4086_ScrollDY)..'|'..dw(sy.SourceStageProducer4086_Position)..'|'..word(sy.SourceStageProducer4086_Waiting)..'|'..dw(sy.SourceWait4086_TimeLeft)..'|'..dw(sy.SourceStageProducer4086_GoTime)..'|'..returned)
'''

def q(bits):return int(struct.unpack('<f',struct.pack('<I',bits))[0]*65536)&0xffffffff
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';paired=list(zip(authority['inputs'],authority['actual']));rows=[]
    for i,(c,v)in enumerate(paired):
        if c['direction']not in (2,3)or(i%47 and i<len(paired)-384):continue
        r=dict(c);r['players']=[dict(live=int(p is not None),slot=(127,0,63,1)[j],**{k:int((p or dict(x=0,z=0,a=0))[k]*65536)for k in ('x','z','a')})for j,p in enumerate(c['players'])]
        for k in ('x','y','speed','offsetx','offsetz','minx','maxx','minz','maxz','blockade'):r[k]=int(c[k]*65536)
        r.update(bad='',motion_bad='',fault=0,expected=[*[q(n)for n in v[:4]],*[n&0xffffffff for n in v[4:]],int(any(c['players'][:c['maxplayers']]))]);rows.append(r)
    base=dict(rows[1],waiting=0,enemies=0)
    for bad in ('ready','width','axis'):rows.append(dict(base,motion_bad=bad,fault=1))
    for field,value in (('direction',8),('speed',-65536),('hres',0),('height',32768)):rows.append(dict(base,**{field:value},fault=1))
    sy=symbols(Path('src/main.sym'))
    lua=BOUNDS_LUA.replace(' before={};for _,r',INIT+'\n before={};for _,r')
    start=lua.index(" emu.log('CAMERABOUNDS|");end=lua.index('\nend,emu.callbackType.exec,RESULT',start);lua=lua[:start]+OBS+lua[end:]
    # Capture context at the private wrapper entry, covering all three real services.
    lua+="\nemu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)\n"
    append='''
SourceCameraFixture_Apply:
.a16
.i16
 jsl WAITENTRY
 bcs SourceCameraFixture_Return
 jsl BOUNDSENTRY
 bcs SourceCameraFixture_Return
 jsl MOTIONENTRY
SourceCameraFixture_Return:
.a16
.i16
 rtl
'''
    r=Reporter('M4-CAMERA-MOTION',kind='GATE');rom,log=run_fixture(a.rom,a.output,rows,'SourceCameraFixture_Apply','SourceCameraMotion4086_Ready',0xb5db,[],lua,r,batch_size=2,append=append,bindings=dict(WAITENTRY='SourceWait4086_Release',BOUNDSENTRY='SourceCameraBounds4086_Collect',MOTIONENTRY='SourceCameraMotion4086_Move'))
    results=[list(map(int,line.split('CAMERAMOTION|',1)[1].split('|')))for line in log.splitlines()if 'CAMERAMOTION|'in line]
    failures=[]
    for i,(v,c)in enumerate(zip(results,rows)):
        ok=v[:3]==[i,0,0]and(v[3]==3 and v[4:9]==[c['x']&0xffffffff,c['y']&0xffffffff,0,0,c['pos']]if c['fault']else v[3]==2 and v[4:]==c['expected'])
        if not ok:failures.append(dict(index=i,input=c,actual=v))
    r.check('C-paired actual WAIT/bounds/motion, source viewport, scrolling deltas/position and readonly pool/CPU',len(results)==len(rows)and not failures)
    d=dict(schema='BYOR_4086_CAMERA_MOTION_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(rom).hexdigest(),numeric_policy='Admitted Q16 coordinates; arithmetic overflow and nonrepresentable half quantum fail explicitly',supported_directions=[2,3],native_roles_and_wait_bound=True,moving_rendering_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
