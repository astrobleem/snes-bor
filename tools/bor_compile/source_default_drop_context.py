"""Immutable horizontal default-drop context, derived without model-name rules.

Owner must pair B4D1 stage identity and current world camera with this context.
Vertical arithmetic and script mutation of global drop policy remain explicit
gaps. The caller grants ROM/data identity from this compiler's hashes.
"""
import argparse,hashlib,json,re,struct,subprocess,zlib
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from dialect_4086 import ENGINE_COMMIT
from source_random_float_4086 import unpack

STRIDE=32
def derive(source,engine=Path('E:/gh/openbor-bcec')):
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1')
 assert 'level->scrolldir = SCROLL_RIGHT;'in raw
 assert re.search(r'case CMD_MODELSTXT_NODROPSPAWN:\s*nodropspawn = 1;',raw)
 video_block=re.search(r'VIDEOMODES:\s*switch\s*\(videoMode\)\s*\{.*?case 0:(.*?)break;',raw,re.S).group(1)
 width=int(re.search(r'videomodes.hRes\s*=\s*(\d+)',video_block).group(1));height=int(re.search(r'videomodes.vRes\s*=\s*(\d+)',video_block).group(1))
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs)
 if structure['video'].get('video',['0'])!=['0']:raise ValueError('SOURCE_DEFAULT_DROP_OTHER_VIDEO_MODE_UNBOUND')
 mutations=[]
 for k,(n,_)in source.index.items():
  if k.endswith('.c')and re.search(r'\bchangeopenborvariant\s*\(',source.read(n).decode('latin1'),re.I):mutations.append(n)
 for d in docs.values():
  for row in d['directives']:
   if row['directive']=='@cmd'and re.search(r'\bchangeopenborvariant\s*\(',' '.join(row['values']),re.I):mutations.append(d['source_path']+':'+str(row['line']))
  for block in d['inline_scripts']:
   if re.search(r'\bchangeopenborvariant\s*\(','\n'.join(block['text']),re.I):mutations.append(d['source_path']+':'+str(block['line']))
 if mutations:raise ValueError('SOURCE_DEFAULT_DROP_GLOBAL_MUTATION_REQUIRES_OWNER:'+','.join(mutations))
 model_doc=docs[key(structure['models_path'])];nodrop=int(any(r['directive']=='nodropspawn'for r in model_doc['directives']))
 stages=[];seen=set()
 for group in structure['sets']:
  for e in group['entries']:
   if e['kind']!='STAGE'or key(e['source_path'])in seen:continue
   seen.add(key(e['source_path']));d=docs[key(e['source_path'])];directions=[r for r in d['directives']if r['directive']=='direction']
   direction=directions[-1]['values']if directions else['right']
   if direction not in(['right'],['left']):raise ValueError('SOURCE_DEFAULT_DROP_VERTICAL_ARITHMETIC_UNBOUND:'+d['source_path'])
   stages.append(dict(stage_id=len(stages)+1,source_path=d['source_path'],source_sha256=d['sha256'],source_crc32=zlib.crc32(source.read(d['source_path']))&0xffffffff,scroll=direction[0],native_scroll_axis=0,nodropspawn=nodrop,source_width=width,source_height=height,model_count=len(structure['models']),random_maximum=40))
 if not stages:raise ValueError('SOURCE_DEFAULT_DROP_NO_STAGES')
 return dict(schema='BYOR_4086_HORIZONTAL_DEFAULT_DROP_CONTEXT_V1',status='PASS',engine_commit=ENGINE_COMMIT,video_case0_sha256=hashlib.sha256(video_block.encode('latin1')).hexdigest(),models_file_sha256=model_doc['sha256'],stages=stages,global_policy_readonly_required=True,current_stage_and_camera_owner_bound=False,drop_native_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(report,table_address):
 if table_address>>16 not in range(1,64)or not 0x8000<=table_address&65535<=0x8ab8:raise ValueError('SOURCE_DROP_CONTEXT_TABLE_ADDRESS')
 output=bytearray()
 for r in report['stages']:
  if not 1<=r['stage_id']<=65535 or not 1<=r['model_count']<=128 or not 1<=r['source_width']<=32767 or not 0<r['source_height']<32768:raise ValueError('SOURCE_DROP_CONTEXT_FIELD_DOMAIN')
  output.extend(struct.pack('<4s10HII',b'B5DC',1,STRIDE,r['stage_id'],0,r['nodropspawn'],r['source_width'],r['source_height'],r['model_count'],r['random_maximum'],0,table_address,r['source_crc32']))
 return bytes(output)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--table-authority',type=Path,required=True);p.add_argument('--bank',type=int,default=59);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 report=derive(Source(a.source),a.engine);authority=json.loads(a.table_authority.read_text());assert authority['status']=='PASS';sourcebits=json.loads((a.table_authority.parent/'source_values.json').read_text());table=(a.table_authority.parent/'randf.b5rf').read_bytes();unpack(table,sourcebits)
 assert all(r['source_height']==authority['source_height']and r['random_maximum']==authority['constant_randf_argument']for r in report['stages'])
 table_address=(a.bank<<16)+0x8000+STRIDE*len(report['stages']);contexts=pack(report,table_address);bundle=contexts+table
 if len(bundle)>32768:raise ValueError('SOURCE_DROP_CONTEXT_BUNDLE_BANK_CAPACITY')
 (a.output/'dropcontext.b5dc').write_bytes(contexts);(a.output/'bundle.bin').write_bytes(bundle)
 report.update(table_authority_sha256=hashlib.sha256(a.table_authority.read_bytes()).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),table_address=table_address,bundle_bytes=len(bundle),bundle_sha256=hashlib.sha256(bundle).hexdigest(),context_bytes=len(contexts),context_sha256=hashlib.sha256(contexts).hexdigest())
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='stages'}))

if __name__=='__main__':main()
