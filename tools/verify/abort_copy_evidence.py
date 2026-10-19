"""Native abort-copy exact ABI, byte bus ordering and owner-close proof."""
from __future__ import annotations
import ref_rebuild_evidence as reference


def require(ok,code):
    if not ok:raise ValueError('ABORT_COPY:'+code)


def expected_bus(committed,path):
    require(len(committed)==2048 and path in ('fast','legacy'),'BUS_INPUT')
    trace=[];bus=[]
    for index,value in enumerate(committed):trace.append(f'{0xc000+index:04x}{value:02x}')
    if path=='legacy':
        for index,value in enumerate(committed):
            bus.extend((f'R{0xc800+index:04x}{value:02x}',f'W{0xc000+index:04x}{value:02x}'))
    else:
        for index in range(0,2048,2):
            bus.extend((f'R{0xc800+index:04x}{committed[index]:02x}',f'R{0xc801+index:04x}{committed[index+1]:02x}',
                f'W{0xc000+index:04x}{committed[index]:02x}',f'W{0xc001+index:04x}{committed[index+1]:02x}'))
    return ''.join(trace),''.join(bus)


def native_copies(path):
    aborts=[];entries={};paths={};scans={};closed={}
    for event in reference.ready.events(path):
        data=event['data'];kind=event['kind']
        if kind=='PHASE' and data[0]=='NbAbort':aborts.append((data[1],event['clock']))
        elif kind=='CA_ENTRY':
            require(len(data)==14 and data[1]==str(len(entries)+1),'ENTRY_INVENTORY')
            key=data[1];require(key not in entries and len(aborts)==len(entries)+1,'ABORT_ENTRY_INVENTORY')
            require(aborts[-1][0]==data[0] and aborts[-1][1]<event['clock'],'ABORT_ENTRY_PHASE')
            before=reference.ready._registers(data[2:10])
            require(before['d']==0x3400 and 0x1000<=before['sp']<0x2000 and before['ps']&0x30==0,'ENTRY_ABI')
            require(len(bytes.fromhex(data[10]))==len(bytes.fromhex(data[11]))==2048
                and len(bytes.fromhex(data[12]))==1536,'INPUT_ARRAY_INVENTORY')
            owner=int(data[13]);require(0<=owner<=65535,'OWNER_WORD')
            entries[key]=(event['clock'],data[0],before,data[11],data[12],owner)
        elif kind=='CA_PATH':
            require(len(data)==3 and data[1] in entries and data[1] not in paths,'PATH_INVENTORY')
            key=data[1];entry=entries[key]
            require(data[0]==entry[1] and data[2]==('fast' if 1<=entry[5]<=4 else 'legacy'),'PATH_OWNER')
            require(event['clock']>entry[0],'PATH_CLOCK')
            paths[key]=(event['clock'],data[2])
        elif kind=='CA_SCAN':
            require(len(data)==17 and data[1] in entries and data[1] in paths and data[1] not in scans,'SCAN_INVENTORY')
            key=data[1];start,txn,before,committed,refs,owner=entries[key]
            require(data[0]==txn and int(data[2])==event['clock']-start>0,'SCAN_CLOCK')
            require(paths[key][0]<event['clock'],'PATH_SCAN_ORDER')
            after=reference.ready._registers(data[3:11])
            require(after['a']==0 and after['x']==0xd000 and after['y']==0xc800,'EXIT_REGISTERS')
            require(after['ps']==((before['ps']&0x7d)|2) and all(after[k]==before[k]
                for k in ('d','dbr','sp','counter')),'EXIT_CONTEXT')
            require(data[11]==data[12]==committed and data[13]==refs,'MAP_RESTORE_OR_FROZEN_SOURCE')
            trace,bus=expected_bus(bytes.fromhex(committed),paths[key][1])
            require(data[14]==trace and int(data[15])==2048,'ORDERED_MAP_WRITES_OR_READ_COUNT')
            require(data[16]==bus,'ORDERED_BUS_INTERLEAVING')
            scans[key]=dict(transaction=int(txn),master_clocks=int(data[2]),path=paths[key][1],owner=owner,
                source_byte_reads=2048,pending_byte_writes=2048,exact_abi=True,source_and_refs_unchanged=True,
                exact_bus_interleaving=True,scan_clock=event['clock'])
        elif kind=='CA_CLOSED':
            require(len(data)==4 and data[1] in scans and data[1] not in closed,'CLOSE_INVENTORY')
            key=data[1]
            require(data[0]==str(scans[key]['transaction']) and data[2]=='d60000d60100' and data[3]=='0','CLOSE_STORE')
            require(event['clock']>scans[key]['scan_clock'],'CLOSE_CLOCK_ORDER')
            closed[key]=event['clock'];scans[key]['owner_close_guarded']=True
    require(len(aborts)==len(entries) and set(entries)==set(paths)==set(scans)==set(closed),'COMPLETE_ABORT_COPY_INVENTORY')
    return scans
