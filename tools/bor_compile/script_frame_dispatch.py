"""Offline animation/frame routing for the source-derived 4086 wrappers.

Empty routes require a valid installed source context before skipping the VM.
Inline scripts retain their entire source-order body and runtime frame guards:
they may mutate the local frame snapshot, so filtering their commands is unsafe.
This compiler does not bind the production dispatcher or engine APIs.
"""
import argparse
import json
import hashlib
import struct
import zlib
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from script_dispatch_4086 import compile_source
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from script_native_link import link


def compile_frames(source):
    original=compile_source(source)
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs)
    handles={(h['model'],h['role']):h['handle'] for h in original['animation_handles']}
    programs=[]
    for model in structure['models']:
        if not model['scripts'] and not model['inline_scripts']:continue
        functions=source.read(model['scripts'][0]['values'][0]).decode('latin1') if model['scripts'] else ''
        parsed=parse_script(functions,model['source_path'])
        if 'main' in parsed['functions']:raise ValueError('FRAME_DISPATCH_AUTHORED_MAIN_UNSUPPORTED')
        blocks={b['line']:b for b in model['inline_scripts']}
        groups=[];group=None;frame=0
        for row in docs[key(model['source_path'])]['directives']:
            name=row['directive'];values=row['values']
            if name=='anim':
                group=dict(role=' '.join(values),events=[],frames=0,inline=False);groups.append(group);frame=0
            elif name=='frame':frame+=1;group['frames']=frame
            elif name=='@cmd':
                if group is None:raise ValueError('SCRIPT_FRAME_COMMAND_OUTSIDE_ANIMATION')
                group['events'].append((frame,values[0]+'('+','.join(values[1:])+');',False))
            elif name=='@script':
                if group is None:raise ValueError('SCRIPT_GLOBAL_INLINE_WRAPPER_UNSUPPORTED')
                group['inline']=True;group['events'].append((frame,'\n'.join(blocks[row['line']]['text']),True))
        roots={'__byor_empty':''};routes=[];body_roots={}
        for group in groups:
            handle=handles[model['declaration'],group['role']]
            if any(f>=group['frames'] for f,_,inline in group['events'] if not inline):
                raise ValueError('FRAME_DISPATCH_COMMAND_AFTER_LAST_FRAME')
            frame_roots=[]
            for f in range(group['frames']):
                if group['inline']:
                    body='int frame=getlocalvar("frame");int animhandle=getlocalvar("animhandle");\n'
                    body+='\n'.join(text if inline else 'if(frame=='+str(at)+'){'+text+'}'
                                    for at,text,inline in group['events'])
                else:
                    selected=[text for at,text,_ in group['events'] if at==f]
                    body='\n'.join(selected)
                    if body:
                        probe=parse_script('void __probe(){'+body+'}',model['source_path'])
                        def ids(node):
                            return ({node['name']} if node['kind']=='ID' else set())|set().union(
                                *(ids(c['node']) for c in node['children']))
                        referenced=ids(probe['functions']['__probe']['ast'])
                        prefix=''.join('int '+name+'='+str(value)+';\n' for name,value in
                                       [('frame',f),('animhandle',handle)] if name in referenced)
                        body=prefix+body
                if not body:frame_roots.append(None);continue
                if body not in body_roots:
                    root='__byor_frame_'+str(len(body_roots))
                    if root in parsed['functions']:raise ValueError('FRAME_DISPATCH_RESERVED_NAME_COLLISION')
                    body_roots[body]=root;roots[root]=body
                frame_roots.append(body_roots[body])
            routes.append(dict(animation_handle=handle,role=group['role'],frames=frame_roots,
                               inline_body_preserved=group['inline']))
        if '__byor_empty' in parsed['functions']:raise ValueError('FRAME_DISPATCH_RESERVED_NAME_COLLISION')
        text=functions+'\n'+'\n'.join('void '+name+'(){\n'+body+'\n}' for name,body in roots.items())
        library=compile_library(parse_script(text,model['source_path']+'#frame-dispatch'),
                                next(p['program']['builtin_requirements'] for p in original['programs'] if p['model']==model['declaration']))
        programs.append(dict(model=model['declaration'],source_path=model['source_path'],program=library,
                             roots=list(roots),routes=routes))
    counts={(m['declaration'],a['role']):len(a['frames']) for m in structure['models'] for a in m['animations']}
    return dict(schema='BYOR_4086_FRAME_DISPATCH_V1',programs=programs,
                animation_handles=[dict(h,frame_count=counts[h['model'],h['role']]) for h in original['animation_handles']],empty_route_requires_valid_context=True,
                native_dispatch_bound=False,entity_api_bound=False,motu_gameplay_proven=False)


def link_frames(report):
    inputs=[];lowered=[]
    for item in report['programs']:
        blob,detail=lower(item['program'],entry='__byor_empty',export_roots=item['roots'],
                          numeric_policy=POLICY,rom_link_input=True)
        inputs.append((dict(model=item['model'],source_path=item['source_path']),blob));lowered.append(detail)
    code,metadata,linked=link(inputs)
    for item,detail,location in zip(report['programs'],lowered,linked['programs']):
        base=location['entry_ip']
        location['export_entries']={k:base+v for k,v in detail['export_entries'].items()}
        location['routes']=[dict(r,entry_ips=[None if root is None else location['export_entries'][root] for root in r['frames']])
                            for r in item['routes']]
    linked['frame_dispatch_bound']=False
    linked['empty_route_requires_valid_context']=True
    return code,metadata,linked


def pack_dispatch(source,linked,code,metadata):
    """ROM-only u16 routes; 0xffff is empty, never an executable entry IP."""
    handles=source['animation_handles'];programs=linked['programs'];n=len(handles)
    if [h['handle'] for h in handles]!=list(range(1,n+1)):raise ValueError('FRAME_DISPATCH_HANDLE_LAYOUT')
    body=bytearray(struct.pack('<'+'H'*n,*(h['frame_count'] for h in handles)))
    directory=len(body);body.extend(b'\xff\xff'*(n*len(programs)))
    for index,program in enumerate(programs):
        for route in program['routes']:
            handle=route['animation_handle'];entries=route['entry_ips']
            if len(entries)!=handles[handle-1]['frame_count']:raise ValueError('FRAME_DISPATCH_FRAME_COUNT')
            struct.pack_into('<H',body,directory+2*(index*n+handle-1),24+len(body))
            body.extend(struct.pack('<'+'H'*len(entries),*(0xffff if ip is None else ip for ip in entries)))
    header=struct.pack('<4sHHHHIII',b'B4FD',1,len(programs),n,0,
                       zlib.crc32(code)&0xffffffff,zlib.crc32(metadata)&0xffffffff,zlib.crc32(body)&0xffffffff)
    table=header+body
    if len(code)+len(table)>32768:raise ValueError('FRAME_DISPATCH_ROM_BANK_CAPACITY')
    return table


def select_frame(table,program,handle,frame,*,context_valid):
    """Host contract for a future native dispatcher: validate before empty."""
    if not context_valid:raise ValueError('FRAME_DISPATCH_CONTEXT_REQUIRED')
    if len(table)<24:raise ValueError('FRAME_DISPATCH_TABLE_HEADER')
    magic,version,programs,handles,reserved,_,_,crc=struct.unpack_from('<4sHHHHIII',table)
    if magic!=b'B4FD' or version!=1 or reserved or zlib.crc32(table[24:])&0xffffffff!=crc:
        raise ValueError('FRAME_DISPATCH_TABLE_ABI')
    if not 0<=program<programs or not 1<=handle<=handles:raise ValueError('FRAME_DISPATCH_IDENTITY')
    minimum=24+2*handles*(programs+1)
    if len(table)<minimum:raise ValueError('FRAME_DISPATCH_TABLE_LAYOUT')
    count=struct.unpack_from('<H',table,24+2*(handle-1))[0]
    if not 0<=frame<count:raise ValueError('FRAME_DISPATCH_FRAME_RANGE')
    offset=struct.unpack_from('<H',table,24+2*handles+2*(program*handles+handle-1))[0]
    if offset==0xffff:return None
    if offset<minimum or offset+2*count>len(table):raise ValueError('FRAME_DISPATCH_TABLE_LAYOUT')
    entry=struct.unpack_from('<H',table,offset+2*frame)[0]
    return None if entry==0xffff else entry


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    report=compile_frames(Source(a.source));code,metadata,linked=link_frames(report)
    table=pack_dispatch(report,linked,code,metadata)
    linked.update(dispatch_table_bytes=len(table),dispatch_table_sha256=hashlib.sha256(table).hexdigest(),
                  dispatch_rom_offset=len(code),total_rom_reservation_bytes=len(code)+len(table))
    (a.output/'programs.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.output/'instructions.bin').write_bytes(code);(a.output/'metadata.b48r').write_bytes(metadata)
    (a.output/'dispatch.b4fd').write_bytes(table)
    (a.output/'report.json').write_text(json.dumps(linked,indent=2)+'\n')
    print(json.dumps({k:linked[k] for k in ('instruction_count','slot_count','metadata_bytes')}))


if __name__=='__main__':main()
