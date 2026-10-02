"""Read-only bounded production DMA trace. No budget or ROM modification."""
import json
import argparse
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from actor_s5_entity_fixture import symbols
from actor_s5_isolated import ROOT,sha
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact
from game_bor_startup_select import cold_to_title,select_case


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world-control',action='store_true')
    parser.add_argument('--profile',action='store_true',help='Read-only inclusive call/return costs')
    parser.add_argument('--detail',action='store_true',help='Bounded traversal labels and outside service calls')
    parser.add_argument('--bg-detail',action='store_true',help='Read-only BG picker/cache/commit dependency trace')
    parser.add_argument('--bg-validity',action='store_true',help='Private BG no-eviction validity lease')
    parser.add_argument('--bg-control',action='store_true',help='Same validity hooks, fast return disabled')
    parser.add_argument('--replay-dir',type=Path,help='Reobserve an unchanged private ROM and symbols')
    parser.add_argument('--phase-only',action='store_true')
    parser.add_argument('--schedule-detail',action='store_true',help='Read-only scheduling and consumed-publication boundary observer')
    parser.add_argument('--continuous',action='store_true',help='Private fixture: disable only observer stop; 128 physical-field horizon')
    parser.add_argument('--source-tick-horizon',type=int,default=0,help='Stop continuous S-CPU trace at first NMI boundary after this completed source tick')
    parser.add_argument('--burst-profile',action='store_true',help='Observe ticks220..250 costs,241/247 events; end observation306')
    parser.add_argument('--collision-body',action='store_true',help='Private source collision body-only scratch path')
    parser.add_argument('--deadline-wait',action='store_true',help='Private pending-field A/B')
    parser.add_argument('--enemy-copies',type=int,default=1)
    parser.add_argument('--resident',action='store_true')
    parser.add_argument('--layout-dispatch',action='store_true')
    parser.add_argument('--fetch-detail',action='store_true')
    parser.add_argument('--fetch-unroll',action='store_true')
    parser.add_argument('--fetch-address',action='store_true')
    parser.add_argument('--worker',action='store_true',help='Private SA-1 ordered-pass pilot')
    parser.add_argument('--persistent-worker',action='store_true',help='Private persistent SA-1 source-world owner')
    parser.add_argument('--persistent-production',action='store_true',
                        help='Install production input capture/protocol over the same bounded fixture')
    parser.add_argument('--persistent-installed',action='store_true',
                        help='Replay an already-installed persistent runtime without rewriting its worker or input hooks')
    parser.add_argument('--semantic-prefix',type=int,default=0,help='Capture the first N persistent-worker semantic rows')
    args=parser.parse_args()
    worker_mode=args.worker or args.persistent_worker
    persistent=args.persistent_worker
    assert not (args.worker and args.persistent_worker)
    assert not args.persistent_production or args.persistent_worker
    assert not args.persistent_installed or args.persistent_worker and args.replay_dir
    assert args.semantic_prefix>=0
    if args.burst_profile:
        assert args.continuous
        args.profile=True
        args.detail=True
    if args.continuous:
        assert args.world_control and not args.worker
    assert args.source_tick_horizon>=0
    assert not args.source_tick_horizon or args.continuous and not worker_mode
    folder=Path(tempfile.mkdtemp(prefix='actor_s7_dma_',dir=ROOT/'out'))
    if args.replay_dir:
        assert args.world_control and (not worker_mode or args.persistent_worker)
        replay_names=('world.sym','world.pasm','bg-validity.sym','link.json',
                      'worker.sym','worker.pasm','worker.bin','worker-manifest.json')
        for path in args.replay_dir.iterdir():
            if path.name in replay_names or path.suffix in ('.sfc','.msu','.pcm'):
                if args.continuous and path.suffix=='.sfc':shutil.copy2(path,folder/path.name)
                else:os.link(path,folder/path.name)
        if args.persistent_worker and not args.persistent_installed:
            from actor_s7_persistent_worker import install
            install(folder, production_runtime=args.persistent_production)
        if args.persistent_installed:
            manifest=json.loads((folder/'worker-manifest.json').read_text())
            assert manifest.get('status')=='OPT_IN_PERSISTENT_SOURCE_WORLD_RUNTIME', \
                'PERSISTENT_INSTALLED_REPLAY_REQUIRES_OPT_IN_RUNTIME'
    elif args.world_control:
        from actor_s6_production_world import build
        build(folder,'kula',deadline_wait=args.deadline_wait,enemy_copies=args.enemy_copies,resident=args.resident,layout_dispatch=args.layout_dispatch)
        if args.persistent_worker:
            assert args.resident
            from actor_s7_persistent_worker import install
            install(folder, production_runtime=args.persistent_production)
        elif args.worker:
            assert args.resident
            from actor_s7_worker import install
            install(folder)
        if args.bg_validity:
            assert not worker_mode
            from actor_s7_bg_validity import install
            install(folder,enabled=not args.bg_control)
        if args.fetch_unroll or args.fetch_address:
            from actor_s7_fetch_unroll import install
            install(folder,address=args.fetch_address)
    else:
        for path in (ROOT/'distribution').glob('bor*'):
            if path.suffix in ('.sfc','.msu','.pcm'):
                os.link(path,folder/path.name)
    sym=symbols(ROOT/'src/main.sym')
    if args.continuous:
        recorded = args.replay_dir / 'continuous.json' if args.replay_dir else None
        if not worker_mode and recorded and recorded.exists():
            report=json.loads(recorded.read_text())
            assert report['fixture_sha256']==sha(folder/'bor.sfc'), 'CONTINUOUS_REPLAY_ROM_MISMATCH'
            shutil.copy2(recorded,folder/'continuous.json')
        else:
            from actor_s7_continuous import disable_stop
            disable_stop(folder)
    if args.collision_body:
        assert args.continuous
        from actor_s7_collision_body import install
        install(folder)
    hooks={name:sym[name] for name in ('Core_Nmi_Play','Core_Nmi_Play__do_commit','Core_Dma_ProcessQueue',
             'Core_Dma_ProcessQueue__done','Core_Nmi_Play__done')}
    lua=folder/'observer.lua'
    script='''local mt=emu.memType.snesMemory
local function w(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
local once=false
local function sample(name)
 local s=emu.getState()
 if not once then
  for k,v in pairs(s) do
   if string.find(k,"scanline") or string.find(k,"cycleCount") or string.find(k,"frameCount") or string.find(k,"masterClock") then
    emu.log("S7KEY|"..k.."|"..tostring(v))
   end
  end
  once=true
 end
 local row={"S7DMA",name,tostring(w('''+str(sym['Nmi_FrameCounter'])+''')),
 tostring(s["ppu.scanline"]),tostring(s["masterClock"]),tostring(s["cpu.cycleCount"]),
 tostring(emu.read(0x4212,mt)),tostring(w('''+str(sym['DmaQueue_BudgetTotal'])+''')),
 tostring(emu.read('''+str(sym['Nmi_FrameBusy'])+''',mt))}
 emu.log(table.concat(row,"|"))
 if name=="Core_Nmi_Play" then
  for k,v in pairs(s) do
   if string.find(k,"cart.coprocessor.cpu") and
      (string.find(k,"pc") or string.find(k,"cycleCount") or string.find(k,".k")) then
    emu.log("S7SA1|"..s["masterClock"].."|"..k.."|"..tostring(v))
   end
  end
 end
end
'''
    if args.fetch_detail:
        from actor_s7_fetch_observer import script as fetch_script
        script += fetch_script(sym,(folder/'bor.sfc').read_bytes())
    for name,address in hooks.items():
        offset=(address>>16)*32768+(address&65535)-32768
        script+=f'emu.addMemoryCallback(function() sample("{name}") end,emu.callbackType.exec,{offset},{offset},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    if args.world_control:
        world_symbols=symbols(folder/'world.sym')
        if args.continuous:
            nmi_offset=(sym['Core_Nmi_Play__done']>>16)*32768+(sym['Core_Nmi_Play__done']&65535)-32768
            if args.persistent_installed and 'SourceVisual_State' in sym:
                sv=sym
                script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();local row={{"S7SOURCEVISUAL","NMI",s["ppu.frameCount"],
  w({sv['SourceVisual_CallCount']}),w({sv['SourceVisual_RenderPassCount']}),
  w({sv['SourceVisual_HostCallCount']}),emu.read({sv['SourceVisual_Error']},mt),
  emu.read({sv['SourceVisual_DebugLastError']},mt),w({sv['SourceVisual_DebugIndex']}),
  w({sv['SourceVisual_ChunkCount']}),w({sv['SourceVisual_PresentationMask']}),
  w(0x7e53a0),w(0x7e53a2),w(0x7e53c8)}}
 for i=0,3 do local a={sv['SourceVisual_State']}+i*8
  for o=0,6,2 do row[#row+1]=w(a+o) end
 end
 emu.log(table.concat(row,"|"))
end,emu.callbackType.exec,{nmi_offset},{nmi_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
            elif 'S7Pub_State' in world_symbols:
                publisher_state=world_symbols['S7Pub_State']
                script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log(table.concat({{"S7PUB","NMI",s["ppu.frameCount"],
  w({publisher_state}),w({publisher_state}+2),w({publisher_state}+4),
  w({publisher_state}+6),w({publisher_state}+0xE2),w({publisher_state}+0xE4),
  w({publisher_state}+0xE6),w({publisher_state}+0xE8),w({publisher_state}+0xEA),
  w({publisher_state}+0xF0),w({publisher_state}+0xF2),w({publisher_state}+0xFE)}} ,"|"))
end,emu.callbackType.exec,{nmi_offset},{nmi_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
            else:
                raise KeyError('CONTINUOUS_PUBLISHER_STATE_NOT_FOUND')
        if args.continuous and not args.persistent_worker:
            from actor_s7_continuous import observer
            script += observer({**sym,**world_symbols},source_tick_horizon=args.source_tick_horizon)
            if args.burst_profile:
                script=script.replace('if name=="Core_Nmi_Play__done" then\n  committing=false',
                    'if name=="S6Host_Tick__return" and completed==306 then row[2]="HORIZON";emu.log(table.concat(row,"|"));finished=true end\n if name=="Core_Nmi_Play__done" then\n  committing=false')
        if args.schedule_detail:
            from actor_s7_schedule_observer import script as schedule_script
            script += schedule_script({**sym,**world_symbols},(folder/'bor.sfc').read_bytes())
        if args.bg_validity:world_symbols.update(symbols(folder/'bg-validity.sym'))
        if worker_mode:
            worker_symbols=symbols(folder/'worker.sym')
            world_symbols.update(worker_symbols)
            script+='''
local rawword=w
w=function(a)
 if rawword(0x7e175c)==1 then
  if a>=0x7e1900 and a<0x7e1f00 then
   local value=rawword(a-0x3d0000)
   local off=a%256
   if (off==0x34 or off==0x36) and value~=0 then value=value-0x6000 end
   return value
  elseif a>=0x7e1700 and a<=0x7e1722 then
   return rawword(a-0x3d0000)
  end
 end
 return rawword(a)
end
'''
            if args.persistent_worker:
                script+='''
local persistent_sync={flush_calls=0,flush_clock=0,flush_cpu=0,tick_wait=0,
 snapshot_wait=0,snapshot_requests=0,queue_calls=0,queue_clock=0,
 queue_cpu=0,relay_calls=0,relay_clock=0,relay_cpu=0,acquire_calls=0,
 acquire_clock=0,acquire_cpu=0}
local flush_start,flush_cpu_start,request_clock,request_cpu
local queue_start,queue_cpu_start,relay_start,relay_cpu_start,acquire_start,acquire_cpu_start
'''
                event_push=world_symbols['S6_EventPush']
                event_push_return=world_symbols['S6_EventPush__return']
                event_push_offset=(event_push>>16)*32768+(event_push&65535)-32768
                event_push_return_offset=(event_push_return>>16)*32768+(event_push_return&65535)-32768
                script+=f'''local event_transport={{calls=0,cycles=0,bytes=0,kinds={{[1]=0,[2]=0,[3]=0}}}}
local event_push_cycle,event_push_kind
emu.addMemoryCallback(function()
 local s=emu.getState()
 event_push_cycle=s["cart.coprocessor.cpu.cycleCount"]
 event_push_kind=(s["cart.coprocessor.cpu.a"] or 0)%65536
end,emu.callbackType.exec,{event_push_offset},{event_push_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 local s=emu.getState()
 if event_push_cycle then
  event_transport.calls=event_transport.calls+1
  event_transport.cycles=event_transport.cycles+s["cart.coprocessor.cpu.cycleCount"]-event_push_cycle
  event_transport.bytes=event_transport.bytes+16
  event_transport.kinds[event_push_kind]=(event_transport.kinds[event_push_kind] or 0)+1
  event_push_cycle=nil
 end
end,emu.callbackType.exec,{event_push_return_offset},{event_push_return_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
'''
                trace_symbols={**sym,**world_symbols}
                trace_tags=('Worker_Enter','Worker_Tick','Worker_RingFault','Worker_Execute','Worker_Complete','Worker_FaultWait',
                            'Relay_Run','Relay_Acquire','Relay_AcquireDone','Relay_Queue',
                            'Relay_Queued',
                            'Relay_Failed','Relay_Flush','Relay_Flush_Owned','Relay_Request_Snapshot',
                            'Relay_Snapshot_Ready','Relay_Commit_A','Relay_Commit_B',
                            'Relay_Flush_Return','Relay_Timeout','S6Game_PlayRender__measure',
                            'S6Clock_ClockAdvance','S6Clock_HostSourceTick',
                            'S6Clock_HostSourceTick__running','S6Clock_HostSourceTick__done',
                            'S6Game_PlayRender__return','Character_RenderPass',
                            'Character_RenderPass__render_done','Core_Oop_Play',
                            'Core_Oop_Play__done','Game_State_Play__playing',
                            'Game_State_Play__no_out_continue','Game_State_Play__no_pause_press',
                            'Game_State_Play__no_death','Game_State_Play__no_all_out',
                            'Game_State_Play__done')
                if args.persistent_installed:
                    trace_tags=tuple(tag for tag in trace_tags if tag!='Worker_FaultWait')
                for tag in trace_tags:
                    if tag not in trace_symbols:continue
                    address=trace_symbols[tag]
                    offset=(address>>16)*32768+(address&65535)-32768
                    cpu='sa1' if tag.startswith('Worker_') else 'snes'
                    pckey='cart.coprocessor.cpu.pc' if cpu=='sa1' else 'cpu.pc'
                    script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState()
 local now=s["masterClock"]
 local cycles=s["{ 'cart.coprocessor.cpu.cycleCount' if cpu=='sa1' else 'cpu.cycleCount' }"]
 if "{tag}"=="Relay_Run" then
  persistent_sync.relay_calls=persistent_sync.relay_calls+1;relay_start=now;relay_cpu_start=cycles
 elseif "{tag}"=="Relay_Queue" then
  queue_start=now;queue_cpu_start=cycles
 elseif "{tag}"=="Relay_Queued" then
  if queue_start then persistent_sync.queue_calls=persistent_sync.queue_calls+1
   persistent_sync.queue_clock=persistent_sync.queue_clock+now-queue_start
   persistent_sync.queue_cpu=persistent_sync.queue_cpu+cycles-queue_cpu_start end
  if relay_start then persistent_sync.relay_clock=persistent_sync.relay_clock+now-relay_start
   persistent_sync.relay_cpu=persistent_sync.relay_cpu+cycles-relay_cpu_start;relay_start=nil end
 elseif "{tag}"=="Relay_Acquire" then
  persistent_sync.acquire_calls=persistent_sync.acquire_calls+1;acquire_start=now;acquire_cpu_start=cycles
 elseif "{tag}"=="Relay_AcquireDone" then
  if acquire_start then persistent_sync.acquire_clock=persistent_sync.acquire_clock+now-acquire_start
   persistent_sync.acquire_cpu=persistent_sync.acquire_cpu+cycles-acquire_cpu_start;acquire_start=nil end
 elseif "{tag}"=="Relay_Flush" then
  persistent_sync.flush_calls=persistent_sync.flush_calls+1;flush_start=now;flush_cpu_start=cycles
 elseif "{tag}"=="Relay_Request_Snapshot" then
  persistent_sync.snapshot_requests=persistent_sync.snapshot_requests+1
  if flush_start then persistent_sync.tick_wait=persistent_sync.tick_wait+now-flush_start end
  request_clock=now;request_cpu=cycles
 elseif "{tag}"=="Relay_Snapshot_Ready" then
  if request_clock then persistent_sync.snapshot_wait=persistent_sync.snapshot_wait+now-request_clock end
 elseif "{tag}"=="Relay_Flush_Return" then
  if flush_start then persistent_sync.flush_clock=persistent_sync.flush_clock+now-flush_start
   persistent_sync.flush_cpu=persistent_sync.flush_cpu+cycles-flush_cpu_start;flush_start=nil end
 end
 emu.log(table.concat({{"S7PTRACE","{tag}",s["masterClock"],s["ppu.frameCount"],tostring(s["{pckey}"]),
  emu.read(0x3025,mt),emu.read(0x3026,mt),emu.read(0x3027,mt),
  w(0x7e175c),w(0x7e1764),w(0x7e173c),w(0x412002),w(0x412004),emu.read(0x41200A,mt),
  emu.read(0x12002,emu.memType.snesSaveRam),emu.read(0x12004,emu.memType.snesSaveRam),
  emu.read(0x1200A,emu.memType.snesSaveRam)}},"|"))
end,emu.callbackType.exec,{offset},{offset},emu.cpuType.{cpu},emu.memType.snesPrgRom)
'''
                if args.persistent_installed:
                    fault_offsets={}
                    for name in ('Worker_WorldFault','Worker_FaultWait'):
                        address=worker_symbols[name]
                        fault_offsets[name]=(address>>16)*32768+(address&65535)-32768
                    script+=f'''local persistent_fault_detail_seen=false
local function persistent_fault_detail(where)
 if persistent_fault_detail_seen then return end
 persistent_fault_detail_seen=true
 local s=emu.getState()
 local d=s["cart.coprocessor.cpu.d"]
 local row={{"S7PERSIST","FAULTDETAIL",where,s["masterClock"],s["ppu.frameCount"],
  s["cart.coprocessor.cpu.a"],d,s["cart.coprocessor.cpu.pc"],s["cart.coprocessor.cpu.sp"],
  emu.read((d+0x36)&0xFFFF,mt),emu.read((d+0x38)&0xFFFF,mt),
  emu.read((d+0x3A)&0xFFFF,mt),w(0x412008),w(0x41200A),w(0x7e173c),
  w(0x412002),w(0x412004),w(0x412430),w(0x412432),w(0x412434)}}
 for slot=0,5 do table.insert(row,w(0x7e19FC+slot*256)) end
 emu.log(table.concat(row,"|"))
 emu.breakExecution()
end
emu.addMemoryCallback(function() persistent_fault_detail("WorldFault") end,
 emu.callbackType.exec,{fault_offsets['Worker_WorldFault']},{fault_offsets['Worker_WorldFault']},
 emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() persistent_fault_detail("FaultWait") end,
 emu.callbackType.exec,{fault_offsets['Worker_FaultWait']},{fault_offsets['Worker_FaultWait']},
 emu.cpuType.sa1,emu.memType.snesPrgRom)
'''
        script+='local tick_active=false\nlocal tick_return=false\n'
        for tag in ('S6Host_Tick','S6Host_Tick__return'):
            address=world_symbols[tag]
            offset=(address>>16)*32768+(address&65535)-32768
            guard='tick_active=true;tick_return=false;' if tag=='S6Host_Tick' else 'tick_return=tick_active;if not tick_active then return end;tick_active=false;'
            script+='emu.addMemoryCallback(function() '+guard+' local s=emu.getState(); emu.log(table.concat({"S7CPU","'+tag+'",tostring(s["ppu.frameCount"]),tostring(s["masterClock"]),tostring(w(0x7e173c)),tostring(w(0x7e1760)),tostring(w(0x7e1764)),tostring(w(0x7e173a))},"|")) end,emu.callbackType.exec,'+str(offset)+','+str(offset)+',emu.cpuType.snes,emu.memType.snesPrgRom)\n'
        address=world_symbols['S6Host_Tick__return']
        offset=(address>>16)*32768+(address&65535)-32768
        script+='''
local semantic_offsets={0x06,0x08,0x10,0x12,0x14,0x16,0x18,0x1a,0x34,
 0x70,0xb4,0xb6,0xc2,0xc4,0xd0,0xd2,0xd4,0xd6,0xd8,0xda,0xdc,0xde,
 0xe0,0xe4,0xe6,0xe8,0xea,0xec,0xee,0xf0,0xf2,0xf4,0xf6,0xfa,0xfc,0xfe}
local function semantic()
 if not tick_return then return end
 if w(0x7e1760)~=1 then return end
 local row={"S7SEMANTIC",w(0x7e173c)}
 for a=0x7e1700,0x7e1722,2 do table.insert(row,w(a)) end
 for slot=0,5 do
  for _,o in ipairs(semantic_offsets) do table.insert(row,w(0x7e1900+slot*256+o)) end
 end
 emu.log(table.concat(row,"|"))
end
emu.addMemoryCallback(semantic,emu.callbackType.exec,'''+str(offset)+','+str(offset)+''',emu.cpuType.snes,emu.memType.snesPrgRom)
'''
        if args.persistent_worker:
            complete=world_symbols['Worker_Complete']
            complete_offset=(complete>>16)*32768+(complete&65535)-32768
            if args.semantic_prefix:
                script+=f'''
local semantic_prefix={args.semantic_prefix}
local function persistent_semantic()
 -- Worker_Complete is entered after the Nth request body returns but before
 -- its mailbox completion index advances; this captures the canonical SA-1
 -- state for that exact source tick, not the asynchronously lagging S-CPU
 -- request cursor.
 local n=rawword(0x412004)+1
 if n>semantic_prefix then return end
 local row={{"S7PERSISTSEMANTIC",n}}
 for a=0x411700,0x411722,2 do table.insert(row,w(a)) end
 for slot=0,5 do
  local base=0x411900+slot*256
  for _,o in ipairs(semantic_offsets) do
   local value=w(base+o)
   if (o==0x34 or o==0x36) and value~=0 then value=value-0x6000 end
   table.insert(row,value)
  end
 end
 emu.log(table.concat(row,"|"))
end
emu.addMemoryCallback(persistent_semantic,emu.callbackType.exec,{complete_offset},{complete_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
'''
            nmi_done=(sym['Core_Nmi_Play__done']>>16)*32768+(sym['Core_Nmi_Play__done']&65535)-32768
            oam_done=(sym['Core_Oam_Play__done']>>16)*32768+(sym['Core_Oam_Play__done']&65535)-32768
            commit=(sym['Core_Nmi_Play__do_commit']>>16)*32768+(sym['Core_Nmi_Play__do_commit']&65535)-32768
            dma_done=(sym['Core_Dma_ProcessQueue__done']>>16)*32768+(sym['Core_Dma_ProcessQueue__done']&65535)-32768
            script+=f'''
local persistent_prepared=0
local persistent_published=0
local persistent_commit=false
local persistent_presented=false
emu.addMemoryCallback(function()
 if emu.read(0x7e53a2,mt)~=0 then persistent_prepared=persistent_prepared+1 end
end,emu.callbackType.exec,{oam_done},{oam_done},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() persistent_commit=true end,emu.callbackType.exec,{commit},{commit},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 if persistent_commit and emu.read(0x7e53a2,mt)~=0 then persistent_published=persistent_published+1 end
end,emu.callbackType.exec,{dma_done},{dma_done},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 if w(0x7e175c)~=1 then return end
 local s=emu.getState()
 local due=w(0x7e173c);local done=w(0x412004);local debt=due-done
 emu.log(table.concat({{"S7CLOCK",s["ppu.frameCount"],s["masterClock"],w(0x7e178c),
  w(0x7e1784)+65536*w(0x7e1786),w(0x7e5023),w(0x7e1772),done}},"|"))
 emu.log(table.concat({{"S7PERSIST","NMI",s["ppu.frameCount"],s["masterClock"],due,done,debt,w(0x412002),w(0x412006),w(0x412007),persistent_prepared,persistent_published,emu.read(0x7e53a2,mt),emu.read(0x3025,mt),emu.read(0x3026,mt),emu.read(0x3027,mt),w(0x7e1760),w(0x7e1764),w(0x7e173a),s["cpu.pc"],s["cpu.k"],s["cpu.sp"],w({sym['Game_State']}),emu.read({sym['PlayerEntity_Hp']},mt),emu.read({sym['G13_P1Out']},mt)}},"|"))
 if emu.read(0x41200A,mt)~=0 then emu.log("S7PERSIST|FAULT|"..done.."|"..w(0x412008)) end
 if done==306 and persistent_published>0 and not persistent_presented then
  persistent_presented=true
  emu.log(table.concat({{"S7PERSIST","PRESENT",done,s["ppu.frameCount"],s["masterClock"],due,persistent_prepared,persistent_published,emu.read(0x41200A,mt)}},"|"))
  emu.log(table.concat({{"S7SYNC",persistent_sync.flush_calls,persistent_sync.snapshot_requests,
   persistent_sync.tick_wait,persistent_sync.snapshot_wait,persistent_sync.flush_clock,persistent_sync.flush_cpu,
   persistent_sync.acquire_calls,persistent_sync.acquire_clock,persistent_sync.acquire_cpu,
   persistent_sync.queue_calls,persistent_sync.queue_clock,persistent_sync.queue_cpu,
   persistent_sync.relay_calls,persistent_sync.relay_clock,persistent_sync.relay_cpu}},"|"))
  emu.log(table.concat({{"S7EVENTCOST",event_transport.calls,event_transport.bytes,
   event_transport.cycles,2*event_transport.cycles,event_transport.kinds[1],
   event_transport.kinds[2],event_transport.kinds[3]}} ,"|"))
  emu.write(0x7e1760,4,mt)
 end
 persistent_commit=false
end,emu.callbackType.exec,{nmi_done},{nmi_done},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
            state_addr=sym['Game_State']
            script+=f'''
local lastmainfield=-1
local function maintrace(name)
 local s=emu.getState()
 local f=s["ppu.frameCount"]
 if f==nil or f<285 or f==lastmainfield then return end
 lastmainfield=f
 emu.log(table.concat({{"S7MAIN",name,f,s["masterClock"],s["cpu.pc"],s["cpu.sp"],
  w({sym['Game_State']}),w({sym['Game_StatePrev']}),w(0x7e175c),w(0x7e1764)}} ,"|"))
end
emu.addMemoryCallback(function() maintrace("SCMAIN") end,emu.callbackType.exec,
 {(sym['scpu_main_loop']>>16)*32768+(sym['scpu_main_loop']&65535)-32768},
 {(sym['scpu_main_loop']>>16)*32768+(sym['scpu_main_loop']&65535)-32768},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() maintrace("WAIT") end,emu.callbackType.exec,
 {(sym['Core_Nmi_WaitFrame']>>16)*32768+(sym['Core_Nmi_WaitFrame']&65535)-32768},
 {(sym['Core_Nmi_WaitFrame']>>16)*32768+(sym['Core_Nmi_WaitFrame']&65535)-32768},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() maintrace("OAM_INIT") end,emu.callbackType.exec,
 {(sym['Core_Oam_Init']>>16)*32768+(sym['Core_Oam_Init']&65535)-32768},
 {(sym['Core_Oam_Init']>>16)*32768+(sym['Core_Oam_Init']&65535)-32768},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() maintrace("OAM_INIT_TAIL") end,emu.callbackType.exec,
 {(sym['Core_Oam_Init']+32>>16)*32768+((sym['Core_Oam_Init']+32)&65535)-32768},
 {(sym['Core_Oam_Init']+32>>16)*32768+((sym['Core_Oam_Init']+32)&65535)-32768},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function(a,v)
 local s=emu.getState()
 emu.log(table.concat({{"S7STATEWRITE",s["masterClock"],s["ppu.frameCount"],a,v,
  w({sym['Game_State']}),w({sym['Game_StatePrev']}),s["cpu.pc"],s["cpu.sp"]}},"|"))
end,emu.callbackType.write,{state_addr&0xFFFF},{state_addr&0xFFFF},emu.cpuType.snes,emu.memType.snesWorkRam)
'''
        if args.profile:
            script+='''
local returns={}
local serial=0
local profile_depth=0
local function point(kind,name,id,s)
 emu.log(table.concat({"S7PROFILE",kind,name,id,s["masterClock"],s["ppu.frameCount"],
  s["ppu.scanline"],w(0x7e173c),w(0x7e1738),w(0x7e1906)},"|"))
end
local function leave(offset)
 local pending=returns[offset]
 if pending==nil then return end
 local s=emu.getState()
 local current=s["cpu.sp"]
 while #pending>0 and pending[#pending].sp==current do
  local item=table.remove(pending)
  point("return",item.name,item.id,s)
  profile_depth=profile_depth-1
 end
end
local function enter(name,short)
 if w(0x7e1760)~=1 and profile_depth==0 then
  if (name~="S7Resident_Flush" and name~="Relay_Flush") or w(0x7e175e)~=2 then return end
 end
 local s=emu.getState()
 local sp=s["cpu.sp"]
 if sp==nil then error("CPU_SP_KEY_REQUIRED") end
 local bank=short and s["cpu.k"] or emu.read(sp+3,mt)
 local address=(w(sp+1)+1)%65536+bank*65536
 local offset=math.floor(address/65536)*32768+address%65536-32768
 serial=serial+1
 local id=serial
 point("enter",name,id,s)
 profile_depth=profile_depth+1
 if returns[offset]==nil then returns[offset]={} end
 table.insert(returns[offset],{name=name,id=id,sp=sp+(short and 2 or 3)})
end
'''
            names=['S6Host_Tick','S7Resident_Flush','S6Bridge_Import','S6Bridge_Export',
                   'S6Bridge_Project','S6Bridge_Unproject',
                   'S6_UpdateWorld','S6_UpdateWorldBound','S6_WorldLost','S6_WorldGravity','S6_ThinkPass',
                   'S6_AnimationPass','S6_WorldAttack','S6_WorldHealth',
                   'S6_SetRole','S5_LoadFrame','Character_RenderPass','S6Game_PlayRender',
                   'S7Publisher_Entry','S7Publisher_RenderOrCompat',
                   'S7Publisher_Capture','S7Publisher_EmitPieces','S7Packet_Submit','S7Packet_Poll',
                   'SourceVisual_RenderCurrent','SourceVisual_LoadResources',
                   'SourceVisual_QueueSheet','SourceVisual_QueuePalettes',
                   'SourceVisual_ReadPalettePayload','SourceVisual_Emit','Msu1_LoadFrame']
            combined={**sym,**world_symbols,**(worker_symbols if persistent else {})}
            shorts=[]
            if persistent:
                names += ['Relay_DrainEvents','Relay_QueueRemove']
            if args.persistent_installed:
                names += ['Tad_StreamFrameService','Tad_StreamLatePump','Core_Input_Poll',
                          'S6Clock_ClockAdvance','S6Clock_HostSourceTick','Stage_ScrollPlay',
                          'Spawn_Play','Spawn_RevealPendingItems','G13_Pickup_CheckPlayers',
                          'G13_HandleOutContinue','Game_State_Pause_CheckEntry',
                          'Game_State_TickExtraActorTimers','Game_State_AnyActorAlive']
                shorts += ['Game_State_Play','Core_Oop_Play','Core_Oam_Play','Core_Oam_ClearAll',
                           'Hud_Play','Core_Text_G1Demo','Core_Screen_Play','Vm_Run',
                           'Core_StreamScroll_ClampCamera','Core_StreamScroll_Play',
                           'Core_StreamScrollFp_Play']
                shorts=[name for name in shorts if name in combined]
                names += shorts
            if args.burst_profile:
                script=script.replace('local function enter(name,short)\n',
                    'local function enter(name,short)\n if profile_depth==0 and (w(0x7e173c)<220 or w(0x7e173c)>250) then return end\n')
                names+=['S5_ActivateAttack','S6_TryHitOne','S6_SourceCollision','S5_CheckCollision',
                        'S6_CheckPolicy','S6_EnemyDecision','S6_EnemyAttack','S6_SelectTarget',
                        'S6_GroundDamage','S6_RecoveryThink','S6_Think','S6_HitEffects']
                names+=['S6Bridge_Import','S6Bridge_Import__numeric','S6Bridge_Import__linked',
                        'S6Bridge_Resolve','S6Bridge_Resolve__bad']
            if args.detail:
                names += ['Tad_StreamFrameService','Tad_StreamLatePump','Core_Input_Poll']
                names += ['S6Clock_ClockAdvance','S6Clock_HostSourceTick','Stage_ScrollPlay',
                          'Spawn_Play','Spawn_RevealPendingItems','G13_Pickup_CheckPlayers',
                          'G13_HandleOutContinue','Game_State_Pause_CheckEntry',
                          'Game_State_TickExtraActorTimers','Game_State_AnyActorAlive']
                shorts=['Game_State_Play','Core_Oop_Play','Core_Oam_Play','Core_Oam_ClearAll','Hud_Play','Core_Text_G1Demo',
                        'Core_Screen_Play','Vm_Run','Core_StreamScroll_ClampCamera','Core_StreamScroll_Play','Core_StreamScrollFp_Play']
                if 'S7Publisher_EmitPieces' in combined:
                    shorts.append('S7Publisher_EmitPieces')
                shorts=[n for n in shorts if n in combined]
                if args.bg_detail:
                    shorts += ['Core_StreamScroll_PickColumn','Core_StreamScroll_SeekColumn',
                               'Core_StreamScroll_ResolveRows','Core_StreamScroll_FetchTileToBuffer',
                               'Core_StreamCache_AllocateSlot']
                names+=shorts
            if args.persistent_installed:
                measured={'Relay_DrainEvents','Relay_QueueRemove','Relay_Run',
                          'Relay_Acquire','Relay_Flush','Core_Input_Poll',
                          'Tad_StreamFrameService','Tad_StreamLatePump',
                          'Core_StreamScroll_Play','Hud_Play'}
                names=[name for name in names if name in measured]
                shorts=[name for name in shorts if name in names]
            names=[name for name in names if name in combined]
            if worker_mode:names+=['Relay_Run','Relay_Acquire','Relay_Flush']
            if args.phase_only:names=[]
            for name in names:
                address=combined[name]
                offset=(address>>16)*32768+(address&65535)-32768
                short='true' if name in shorts else 'false'
                script+=f'emu.addMemoryCallback(function() enter("{name}",{short}) end,emu.callbackType.exec,{offset},{offset},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
            # Install once before execution. Registering emulator callbacks
            # recursively from a callback is not a trustworthy observer.
            rom_bytes=(folder/'bor.sfc').read_bytes()
            return_offsets=set()
            for name in [*names,'S6Game_PlayRender'] if names else []:
                needle=(b'\x20'+(combined[name]&65535).to_bytes(2,'little')) if name in shorts else b'\x22'+combined[name].to_bytes(3,'little')
                at=0
                while (at:=rom_bytes.find(needle,at))!=-1:
                    return_offsets.add(at+len(needle))
                    at+=4
            for offset in sorted(return_offsets):
                script+=f'emu.addMemoryCallback(function() leave({offset}) end,emu.callbackType.exec,{offset},{offset},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
            if args.detail and not args.burst_profile:
                for name,address in world_symbols.items():
                    if not name.startswith('S6_UpdateWorld'):continue
                    offset=(address>>16)*32768+(address&65535)-32768
                    script+=f'emu.addMemoryCallback(function() if w(0x7e1760)~=1 then return end;local s=emu.getState();emu.log(table.concat({{"S7BLOCK","{name}",s["masterClock"],s["cpu.d"],s["cpu.sp"],tostring(s["cpu.dbr"]),tostring(s["cpu.ps"]) }},"|")) end,emu.callbackType.exec,{offset},{offset},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
            if args.bg_detail:
                bg_fields=['Screen_TargetX','Screen_PosX','StreamScroll_StagedLo','StreamScroll_StagedHi',
                           'StreamScroll_DesiredLo','StreamScroll_DesiredHi','StreamScroll_PendCol',
                           'StreamScroll_PendTile','StreamScroll_ColPending','StreamCache_CurrentStamp',
                           'StreamStage_TileId','StreamCache_Chosen','StreamCache_OldTile',
                           'StreamStage_ColStrideLo','StreamScroll_HeightTiles','StreamScroll_RepairCur']
                script+='local bg_addrs={'+','.join(str(sym[n]) for n in bg_fields)+'}\n'
                bg_hooks=['Core_StreamScroll_Play','Core_StreamScroll_PickColumn',
                          'Core_StreamScroll_PickColumn__repair','Core_StreamScroll_SeekColumn',
                          'Core_StreamScroll_ResolveRows','Core_StreamScroll_ResolveRows__hit',
                          'Core_StreamScroll_ResolveRows__is_miss','Core_StreamScroll_ResolveRows__enqueued',
                          'Core_StreamScroll_ResolveRows__committed','Core_StreamScroll_FetchTileToBuffer',
                          'Core_StreamCache_AllocateSlot__allocate','Core_StreamScroll_CommitColumn__go',
                          'Core_StreamScroll_CommitColumn__done']
                if args.bg_validity:bg_hooks+=['S7BG_AfterPick','S7BG_Fast','S7BG_Slow','S7BG_Invalidate']
                for name in bg_hooks:
                    address=combined[name];offset=(address>>16)*32768+(address&65535)-32768
                    script+=f'''emu.addMemoryCallback(function()
 if w(0x7e1760)~=1 then return end
 local s=emu.getState();local row={{"S7BG","{name}",s["masterClock"],s["cpu.a"],s["cpu.x"]}}
 for i,a in ipairs(bg_addrs) do
  table.insert(row,(i==9 or i==10) and emu.read(a,mt) or w(a))
 end
 table.insert(row,w({sym['StreamCache_Slot2Tile']}+2*w({sym['StreamCache_Chosen']})))
 emu.log(table.concat(row,"|"))
end,emu.callbackType.exec,{offset},{offset},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
            phase_hooks={name:sym[name] for name in ('Core_Nmi_WaitFrame','Core_Nmi_Play',
                        'Core_Nmi_Play__done','scpu_main_loop','Game_State_Play')}
            phase_hooks['Core_Nmi_WaitFrame_RETURN']=sym['Core_Nmi_WaitFrame__loop']+6
            phase_hooks['WORLD_RENDER_ENTRY']=world_symbols['S6Game_PlayRender']
            phase_hooks['WORLD_RENDER_RETURN']=world_symbols['S6Game_PlayRender__return']
            # Keep the two observer modes separate. The combined high-density
            # instrumentation stalled in Mesen and is not timing evidence.
            if not args.phase_only:phase_hooks={}
            for name,address in phase_hooks.items():
                offset=(address>>16)*32768+(address&65535)-32768
                script+='emu.addMemoryCallback(function() if w(0x7e1760)~=1 then return end; local s=emu.getState();emu.log(table.concat({"S7PHASE","'+name+'",s["masterClock"],s["ppu.frameCount"],s["ppu.scanline"],w(0x7e173c),w('+str(sym['Nmi_FrameCounter'])+'),w(0x7e1772)},"|")) end,emu.callbackType.exec,'+str(offset)+','+str(offset)+',emu.cpuType.snes,emu.memType.snesPrgRom)\n'
        event_names=['FrameChanged','HitEffects']
        for suffix in event_names:
            name=('W6_' if worker_mode else 'S6_')+suffix
            address=world_symbols[name]
            offset=(address>>16)*32768+(address&65535)-32768
            cpu='sa1' if worker_mode else 'snes'
            dkey='cart.coprocessor.cpu.d' if worker_mode else 'cpu.d'
            base=0x40a000 if worker_mode else 0x7e0000
            normalize=0x6000 if worker_mode else 0
            script+=f'''emu.addMemoryCallback(function()
 if w(0x7e1760)~=1 then return end
local s=emu.getState();local d=s["{dkey}"];local a={base}+d
 if {str(args.burst_profile).lower()} and "{suffix}"=="FrameChanged" and
    ((w({0x41173c if args.persistent_worker else 0x7e173c})==241 and d==0x1a00) or (w({0x41173c if args.persistent_worker else 0x7e173c})==247 and d==0x1b00)) then
  emu.log(table.concat({{"S7BURST_EVENT",s["masterClock"],w({0x41173c if args.persistent_worker else 0x7e173c}),d,w(a+0xe4),w(a+6),w(0x7e175e)}},"|"))
 end
 local target=w(a+0x34);if target~=0 then target=target-{normalize} end
 emu.log(table.concat({{"S7EVENT","{suffix}",w({0x41173c if args.persistent_worker else 0x7e173c}),d-{normalize},w(a+6),w(a+0xe4),target,w(a+0x4c)}},"|"))
end,emu.callbackType.exec,{offset},{offset},emu.cpuType.{cpu},emu.memType.snesPrgRom)
'''
        if worker_mode:
            script+='''
local worker_stack_low=512
local worker_stack_writes=0
local protected_writes=0
emu.addMemoryCallback(function(a,v)
 if rawword(0x7e175c)~=1 then return end
 worker_stack_low=math.min(worker_stack_low,a)
 worker_stack_writes=worker_stack_writes+1
end,emu.callbackType.write,0,511,emu.cpuType.sa1,emu.memType.sa1InternalRam)
local function protected(a,v)
 if rawword(0x7e175e)==2 then protected_writes=protected_writes+1 end
end
'''
            for cpu in ('snes','sa1'):
                for lo,hi in ((0,7),(0x3000,0x6eff)):
                    script+=f'emu.addMemoryCallback(protected,emu.callbackType.write,{lo},{hi},emu.cpuType.{cpu},emu.memType.snesSaveRam)\n'
            worker_trace_names=(('Worker_Execute','Worker_Complete')
                                if args.persistent_installed else
                                ('Worker_Execute','Worker_Complete','W6_WorldLost',
                                 'W6_WorldGravity','W6_ThinkPass','W6_AnimationPass',
                                 'W6_WorldAttack','W6_WorldHealth'))
            for name in worker_trace_names:
                a=world_symbols[name];off=(a>>16)*32768+(a&65535)-32768
                script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log(table.concat({{"S7WORKER","{name}",s["masterClock"],w(0x41173c),s["cart.coprocessor.cpu.d"],s["cart.coprocessor.cpu.sp"],s["cart.coprocessor.cpu.cycleCount"],s["ppu.frameCount"],w(0x412004)+1}},"|"))
 if "{name}"=="Worker_Complete" then
  emu.log(table.concat({{"S7GUARD",worker_stack_low,worker_stack_writes,protected_writes,
   tostring(s["cart.coprocessor.charConvDmaActive"]),tostring(s["cart.coprocessor.sa1BwBank"])}},"|"))
 end
end,emu.callbackType.exec,{off},{off},emu.cpuType.sa1,emu.memType.snesPrgRom)
'''
            if args.persistent_installed:
                complete_poll=worker_symbols['Worker_Complete__Poll']
                complete_poll_off=(complete_poll>>16)*32768+(complete_poll&65535)-32768
                script+=f'''emu.addMemoryCallback(function()
 if w(0x412004)~=306 then return end
 local s=emu.getState()
 emu.log(table.concat({{"S7PERSIST","COMPLETE",306,s["ppu.frameCount"],s["masterClock"],
  w(0x7e173c),w(0x412004),w(0x7e173c)-w(0x412004),w(0x412002),w(0x412004),
  w(0x412430),w(0x412432),w(0x412434),w(0x412006),w(0x412007),
  w({sym['SourceVisual_CallCount']}),w({sym['SourceVisual_RenderPassCount']}),
  w({sym['SourceVisual_HostCallCount']}),emu.read({sym['SourceVisual_Error']},mt),
  w(0x7e53a2),w(0x7e175c),w(0x7e1764)}} ,"|"))
 emu.breakExecution()
end,emu.callbackType.exec,{complete_poll_off},{complete_poll_off},emu.cpuType.sa1,emu.memType.snesPrgRom)
'''
    script+='''emu.addMemoryCallback(function()
 if w(0x7e1760)~=1 then return end
 local s=emu.getState()
 emu.log(table.concat({"S7WORLD",tostring(s["ppu.frameCount"]),tostring(w(0x7e5023)),
 tostring(w(0x7e173c)),tostring(w(0x7e1906)),tostring(w(0x7e19e4))},"|"))
end,emu.callbackType.write,0x1774,0x1774,emu.cpuType.snes,emu.memType.snesWorkRam)
'''
    lua.write_text(script)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            proxy=SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)
            with patch.object(module,'subprocess',proxy):return super().__enter__()
    with Observed(rom=folder/'bor.sfc',mesen=MESEN_EXE,cwd=folder,
                  port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        reporter=Reporter('S7-DMA')
        import game_bor_startup_select as startup
        def startup_frames(session,count):
            remaining=count
            while remaining:
                request=min(30,remaining)
                result=session.run_frames(request)
                advanced=result.get('framesAdvanced',0)
                assert 0<=advanced<=request,result
                remaining-=advanced
                if advanced==0:
                    assert result.get('timedOut'),result
        with patch.object(m,'reset_emulator',lambda:None), \
             patch.object(startup,'run_frames_exact',startup_frames):
            cold_to_title(m,reporter)
            select_case(m,reporter,'KULA','KULA')
        if args.world_control:
            m.write_memory('snesMemory',0x7e1700,bytes(256).hex())
            m.write_memory('snesMemory',0x7e1900,bytes(1536).hex())
            m.write_u16(0x7e1770,1)
        start=len(m._stderr_lines)
        # MCP allows only2x real time +200ms per request. Dense debugger
        # inspection exceeds2x wall time, not emulated clock time. One-field
        # steps retain exact progress while giving the observer its fixed
        # request allowance; no writes/inputs occur between these steps.
        if args.continuous or args.schedule_detail or (args.profile and not args.phase_only):
            if args.continuous and args.persistent_installed:
                field_limit=600
                fields_advanced=0
                log_cursor=start
                persistent_owned=False
                last_persist_row=''
                while fields_advanced<field_limit:
                    if not persistent_owned:
                        owner=m.read_memory('snesMemory',0x7e175c,2)
                        persistent_owned=int.from_bytes(owner,'little')==1
                    request=(1 if persistent_owned else min(30,field_limit-fields_advanced))
                    halted_at_horizon=False
                    for attempt in range(200):
                        result=m.run_frames(request)
                        current=list(m._stderr_lines)
                        new_lines=current[log_cursor:]
                        log_cursor=len(current)
                        new_text=''.join(x.decode(errors='replace') if isinstance(x,bytes) else x
                                         for x in new_lines)
                        for line in new_text.splitlines():
                            if 'S7PERSIST|NMI|' in line:
                                last_persist_row=line[line.index('S7PERSIST|'):].strip()
                        if ('S7PERSIST|COMPLETE|306|' in new_text or
                                'S7PERSIST|PRESENT|306|' in new_text or
                                'S7PERSIST|FAULTDETAIL|' in new_text or
                                'S7PERSIST|FAULT|' in new_text):
                            halted_at_horizon=True
                            break
                        advanced=result.get('framesAdvanced',0)
                        assert 0<=advanced<=request,result
                        if advanced:
                            fields_advanced+=advanced
                            if fields_advanced and fields_advanced%30==0:
                                host=m.read_memory('snesMemory',0x7e1730,64)
                                shared=m.read_memory('snesMemory',0x412000,64)
                                def word(data,offset):
                                    return int.from_bytes(data[offset:offset+2],'little')
                                print('PRODUCTION_PROGRESS|{}|owner={}|due={}|done={}|'
                                      'tick_head={}|event_head={}|event_tail={}|overflow={}|last={}'.format(
                                          fields_advanced,word(host,0x2c),word(host,0x0c),
                                          word(shared,4),word(shared,2),word(shared,0x30),
                                          word(shared,0x32),word(shared,0x34),last_persist_row),
                                      flush=True)
                            if not persistent_owned:
                                owner=m.read_memory('snesMemory',0x7e175c,2)
                                persistent_owned=int.from_bytes(owner,'little')==1
                            break
                        assert result.get('timedOut'),result
                    else:
                        raise AssertionError('PERSISTENT_PRODUCTION_NO_FIELD_PROGRESS')
                    if halted_at_horizon:
                        break
                if fields_advanced>=field_limit:
                    partial={'status':'HORIZON_EXHAUSTED_NOT_A_RESULT',
                             'fields_advanced':fields_advanced,
                             'field_limit':field_limit,
                             'last_persist_row':last_persist_row}
                    (folder/'partial-horizon.json').write_text(json.dumps(partial,indent=2)+'\n')
                    raise AssertionError('PERSISTENT_PRODUCTION_TICK306_HORIZON_EXHAUSTED '
                                         +json.dumps(partial,separators=(',',':')))
            else:
                for _ in range(260 if args.continuous else 120):
                    if not args.detail and not args.schedule_detail and not args.continuous:
                        run_frames_exact(m,1)
                        continue
                    # Detailed read-only observer can exceed MCP's wall-time cap
                    # within one field. Resume the incomplete field without input
                    # writes; count only actual completed fields, never a timeout.
                    halted_at_horizon=False
                    for attempt in range(200):
                        result=m.run_frames(1)
                        if args.continuous:
                            recent=''.join(x.decode(errors='replace') if isinstance(x,bytes) else x for x in list(m._stderr_lines)[start:])
                            marker=('S7PERSIST|PRESENT|306|' if args.persistent_worker else
                                    'S7CONT|HORIZON|')
                            if marker in recent:
                                halted_at_horizon=True
                                break
                        if result.get('framesAdvanced')==1:break
                        assert result.get('framesAdvanced')==0 and result.get('timedOut'),result
                    else:raise AssertionError('DETAIL_OBSERVER_NO_FIELD_PROGRESS')
                    if halted_at_horizon:break
                    if args.continuous:
                        recent=''.join(x.decode(errors='replace') if isinstance(x,bytes) else x for x in list(m._stderr_lines)[start:])
                        if args.persistent_worker:
                            prefix_done=args.semantic_prefix and f'S7PERSISTSEMANTIC|{args.semantic_prefix}|' in recent
                            if ((args.semantic_prefix and args.semantic_prefix<306 and prefix_done) or
                                'S7PERSIST|PRESENT|306|' in recent or 'S7PERSIST|FAULT|' in recent):break
                        elif 'S7CONT|HORIZON|' in recent or 'S7CONT|FAULT|' in recent:break
        elif args.semantic_prefix:
            for _ in range(320):
                run_frames_exact(m,1)
                recent=''.join(x.decode(errors='replace') if isinstance(x,bytes) else x for x in list(m._stderr_lines)[start:])
                if f'S7PERSISTSEMANTIC|{args.semantic_prefix}|' in recent or 'S7PERSIST|FAULT|' in recent:break
            else:raise AssertionError('PERSISTENT_SEMANTIC_PREFIX_INCOMPLETE')
        else:
            for _ in range(4):run_frames_exact(m,30)
        host_snapshot=m.read_memory('snesMemory',0x7e1700,256).hex()
        mailbox=m.read_memory('snesMemory',0x3020,8).hex()
        world_entities=m.read_memory('snesMemory',0x7e0a00,6*sym['CHAR_ZP_LEN'])
        world_environment=m.read_memory('snesMemory',sym['StageEnv_Actors'],6*sym['CHAR_ZP_LEN'])
        actors=[]
        for slot in range(6):
            offset=slot*sym['CHAR_ZP_LEN']
            actors.append(dict(slot=slot,roster=world_entities[offset+sym['CHAR_ROSTER_INDEX']],
                hp=world_entities[offset+sym['CHAR_HP']],
                policy=world_environment[offset+64],exists=world_environment[offset+65]))
        logs=[line.decode(errors='replace') if isinstance(line,bytes) else line
              for line in list(m._stderr_lines)[start:]]
        if args.continuous:
            if args.persistent_worker:
                if args.semantic_prefix:
                    assert any(f'S7PERSISTSEMANTIC|{args.semantic_prefix}|' in line or 'S7PERSIST|FAULT|' in line for line in logs), 'PERSISTENT_SEMANTIC_PREFIX_INCOMPLETE'
                else:
                    assert any('S7PERSIST|COMPLETE|306|' in line or
                               'S7PERSIST|PRESENT|306|' in line or
                               'S7PERSIST|FAULTDETAIL|' in line or
                               'S7PERSIST|FAULT|' in line for line in logs), 'PERSISTENT_TICK306_PRESENTATION_INCOMPLETE'
            else:
                assert any('S7CONT|HORIZON|' in line or 'S7CONT|FAULT|' in line for line in logs), 'CONTINUOUS_OBSERVATION_INCOMPLETE'
        rows=[line[line.index('S7DMA|'):].strip().split('|') for line in logs if 'S7DMA|' in line]
        world=[line[line.index('S7WORLD|'):].strip().split('|') for line in logs if 'S7WORLD|' in line]
        cpu=[line[line.index('S7CPU|'):].strip().split('|') for line in logs if 'S7CPU|' in line]
        profile=[line[line.index('S7PROFILE|'):].strip().split('|') for line in logs if 'S7PROFILE|' in line]
        phases=[line[line.index('S7PHASE|'):].strip().split('|') for line in logs if 'S7PHASE|' in line]
        semantics=[line[line.index('S7SEMANTIC|'):].strip().split('|') for line in logs if 'S7SEMANTIC|' in line]
        persistent_semantics=[line[line.index('S7PERSISTSEMANTIC|'):].strip().split('|') for line in logs if 'S7PERSISTSEMANTIC|' in line]
        persistent_rows=[line[line.index('S7PERSIST|'):].strip().split('|') for line in logs if 'S7PERSIST|' in line]
        clock_rows=[line[line.index('S7CLOCK|'):].strip().split('|') for line in logs if 'S7CLOCK|' in line]
        sync_rows=[line[line.index('S7SYNC|'):].strip().split('|') for line in logs if 'S7SYNC|' in line]
        debt_rows=[line[line.index('S7DEBT|'):].strip().split('|') for line in logs if 'S7DEBT|' in line]
        sa1=[line[line.index('S7SA1|'):].strip().split('|') for line in logs if 'S7SA1|' in line]
        events=[line[line.index('S7EVENT|'):].strip().split('|') for line in logs if 'S7EVENT|' in line]
        worker=[line[line.index('S7WORKER|'):].strip().split('|') for line in logs if 'S7WORKER|' in line]
        guards=[line[line.index('S7GUARD|'):].strip().split('|') for line in logs if 'S7GUARD|' in line]
        keys=[line.decode(errors='replace') if isinstance(line,bytes) else line
              for line in m._stderr_lines]
        keys=[line for line in keys if 'S7KEY|' in line]
    result=dict(status='MEASURED_BOUNDED_TRACE_NOT_BUDGET_EXPANSION',
                fields_requested=(fields_advanced if args.continuous and args.persistent_installed
                                  else 128 if args.continuous else 120),
                rom_sha256=sha(folder/'bor.sfc'),msu_sha256=sha(folder/'bor.msu'),
                symbols_sha256=sha(ROOT/'src/main.sym'),hooks=hooks,rows=rows,state_keys=keys,
                world_control=args.world_control,world_rows=world,cpu_rows=cpu,
                profile_rows=profile,
                schedule_rows=[line[line.index('S7SCHEDULE|'):].strip().split('|') for line in logs if 'S7SCHEDULE|' in line],
                continuous_rows=[line[line.index('S7CONT|'):].strip().split('|') for line in logs if 'S7CONT|' in line],
                continuous=args.continuous,
                burst_events=[line[line.index('S7BURST_EVENT|'):].strip().split('|') for line in logs if 'S7BURST_EVENT|' in line],
                fetch_rows=[line[line.index('S7FETCH|'):].strip().split('|') for line in logs if 'S7FETCH|' in line],
                clear_rows=[line[line.index('S7CLEAR|'):].strip().split('|') for line in logs if 'S7CLEAR|' in line],
                msu_rows=[line[line.index('S7MSU|'):].strip().split('|') for line in logs if 'S7MSU|' in line],
                block_rows=[line[line.index('S7BLOCK|'):].strip().split('|') for line in logs if 'S7BLOCK|' in line],
                bg_fields=bg_fields if args.bg_detail else [],
                bg_rows=[line[line.index('S7BG|'):].strip().split('|') for line in logs if 'S7BG|' in line],
                phase_rows=phases,
                semantic_rows=semantics,
                persistent_semantic_rows=persistent_semantics,
                persistent_rows=persistent_rows,
                publisher_rows=[line[line.index('S7PUB|'):].strip().split('|') for line in logs if 'S7PUB|' in line],
                source_visual_rows=[line[line.index('S7SOURCEVISUAL|'):].strip().split('|')
                                    for line in logs if 'S7SOURCEVISUAL|' in line],
                clock_rows=clock_rows,
                sync_rows=sync_rows,
                debt_rows=debt_rows,
                sa1_rows=sa1,
                event_rows=events,worker_rows=worker,mailbox=mailbox,
                event_transport_rows=[line[line.index('S7EVENTCOST|'):].strip().split('|')
                                      for line in logs if 'S7EVENTCOST|' in line],
                guard_rows=guards,
                resident=args.resident,worker=worker_mode,persistent_worker=args.persistent_worker,
                host_snapshot=host_snapshot,
                actors=actors,expected_births=args.enemy_copies,
                production_changed=False,new_source_publication_proven=False)
    if args.world_control:
        from frame_deadline_trace import analyze_world_trace
        try:result['world_deadline_analysis']=analyze_world_trace(result)
        except ValueError as error:
            result['world_deadline_analysis']={'status':'INVALID_TRACE','error':str(error)}
    (folder/'dma.json').write_text(json.dumps(result,indent=2)+'\n')
    print(folder);print('rows',len(rows));print(keys)
    print(rows[:4])


if __name__=='__main__':main()
