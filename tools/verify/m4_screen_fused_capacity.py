"""Measure compiled exact SCREEN-to-palette LUT storage before native execution.

Tables are indexed by compiler RGB8 underlay identity, grouped by source colour
and destination scanline. Unresident HIGH results are explicit zero admissions.
This is a two-pose offline storage proof, not live palette allocation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from compiler import Source
from source_screen_lookup import derive,matrix
from m4_screen_grouped_native import capture_plane
from m4_underlay_spans_sa1_native import compile_inputs
import m4_screen_sa1_native as source_capture


def compile_tables(source,stage,contexts,window,context_vocabulary=False):
 catalog=derive(source);global_di={tuple(c):i for i,c in enumerate(catalog['destinations'])};x,y,w,h=window
 destinations=catalog['destinations']
 if context_vocabulary:
  background,_,pixels,_,_,derived_window=compile_inputs(source,stage,contexts[0]['scene'],catalog,True)
  if tuple(window)!=derived_window:raise ValueError('FUSED_TYPED_WINDOW_MISMATCH')
  ids=sorted(set(map(int,np.frombuffer(background+pixels,dtype='<u2')//2)));destinations=[destinations[i]for i in ids]
 di={tuple(c):i for i,c in enumerate(destinations)}
 tables=bytearray();unique={};groups=[];reports=[];errors=0
 for phase,report in enumerate(contexts):
  scene=report['scene'];pairs,metadata=source_capture.capture(source,stage,scene);samples=pairs.reshape(-1,3,2)
  if report['source_layers']!=metadata['layers']:raise ValueError('FUSED_PALETTE_SOURCE_CONTEXT_MISMATCH')
  effect=next(v for v in catalog['effects']if all(tuple(map(int,c))in v['colors']for c in samples[:,:,0]));si={tuple(c):i for i,c in enumerate(effect['colors'])};rgb=matrix(effect['colors'],destinations)
  _,addresses=capture_plane(source,stage,scene,global_di);screen_y=addresses//2//256;source_ids=[si[tuple(map(int,c))]for c in samples[:,:,0]]
  by_row_color={}
  for i,key in enumerate(zip(map(int,screen_y),source_ids)):by_row_color.setdefault(key,[]).append(i)
  states=[];state=[0]*256
  for v in report['bg_schedule']['initial']:state[v['slot']]=v['color']or 0
  updates={v['scanline']:v for v in report['bg_schedule']['trace']};reserved=set(report['obj_palette_cgram_reserved']);physical=report['bg_owned_obj_transparent_entries']+[i for i in range(4,240)if i not in reserved and i not in report['bg_owned_obj_transparent_entries']]
  aliases={v['color']:v['slot']for v in report['bg_exact_obj_palette_aliases']}
  for line in range(224):
   if line in updates:
    v=updates[line];state[v['cgram_start']:v['cgram_start']+len(v['values'])]=[c or 0 for c in v['values']]
   mapping={state[slot]:slot for slot in physical};mapping.update(aliases);states.append((list(state),mapping))
  admitted=0;phase_groups=[]
  for(line,index),positions in sorted(by_row_color.items()):
   state,mapping=states[line];words=rgb[index];high=words&0x7bdf;low=((words>>5)&1)|(((words>>10)&1)<<1)
   indices=np.array([mapping.get(int(c),0)for c in high],dtype=np.uint16);values=np.where(indices,indices|(low<<8),0).astype('<u2');data=values.tobytes();digest=hashlib.sha256(data).digest()
   if digest not in unique:
    if len(tables)%0x100000+len(data)>0x100000:tables.extend(bytes(0x100000-len(tables)%0x100000))
    unique[digest]=len(tables);tables.extend(data)
   offset=unique[digest];phase_groups.append(dict(scanline=line,source_color=index,positions=positions,table_offset=offset,MMC_value=2+offset//0x100000,table_pointer=0xe00000+offset%0x100000))
   for i in positions:
    destination=di[tuple(map(int,samples[i,:,1]))]
    value=int(values[destination]);slot=value&255;lo=value>>8
    if slot<4 or state[slot]+[0,32,1024,1056][lo]!=int(words[destination]):errors+=1
   admitted+=int(np.count_nonzero(indices))
  groups.append(phase_groups);reports.append(dict(phase=phase,opaque_pixels=len(source_ids),row_source_color_groups=len(phase_groups),admitted_underlay_results=admitted))
 return dict(schema='BYOR_FUSED_SCREEN_PALETTE_CAPACITY_V1',status='TABLE_STORAGE_PROVEN'if len(tables)<=0x600000 and errors==0 else'TABLE_STORAGE_LIMIT'if len(tables)>0x600000 else'PALETTE_IDENTITY_FAIL',unique_tables=len(unique),table_bytes=len(tables),available_table_bytes=0x600000,palette_identity_errors=errors,underlay_vocabulary=destinations,underlay_vocabulary_count=len(destinations),context_opaque_vocabulary=context_vocabulary,phases=reports,no_color_reduction=True,native_execution=False,CHR_publication=False,production_ROM_allocation=False),bytes(tables),groups


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--stage',required=True);p.add_argument('--native-proof',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--context-opaque-vocabulary',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 receipt=json.loads((a.native_proof/'report.json').read_text());contexts=[json.loads((a.native_proof/('palette-context-%d'%i)/'report.json').read_text())for i in range(2)]
 report,tables,groups=compile_tables(Source(a.source),a.stage,contexts,receipt['window'],a.context_opaque_vocabulary);report['table_sha256']=hashlib.sha256(tables).hexdigest()
 if report['status']=='TABLE_STORAGE_PROVEN':(a.output/'tables.bin').write_bytes(tables);(a.output/'groups.json').write_text(json.dumps(groups)+'\n')
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
