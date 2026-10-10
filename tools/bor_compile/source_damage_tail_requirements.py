"""Closed source policy and authored motion for the damage tail."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_damage_tail_model_policy import derive as policies
from source_lifecycle_inputs import derive as lifecycle
from source_hit_block_requirements import derive as attacks
from source_model_factors import derive as factors

def q16(value):
 value=struct.unpack('<f',struct.pack('<f',value))[0];scaled=value*65536
 if not -0x80000000<=scaled<=0x7fffffff:raise ValueError('DAMAGE_TAIL_MOTION_Q16_CAPABILITY_REQUIRED')
 return int(scaled)

def derive(source):
 p=policies(source);l=lifecycle(source);a=attacks(source);f=factors(source)
 for i,m in enumerate(p['models']):
  if any(x['models'][i]['id']!=i for x in (l,f)):raise ValueError('DAMAGE_TAIL_MODEL_PAIR')
  d=m['fields']
  if d['falldie']or d['escapehits']or d['nopain']or d['weaploss_type']not in (0,3):raise ValueError('DAMAGE_TAIL_ADDITIONAL_MODEL_SERVICES_REQUIRED')
  if l['models'][i]['fields']['knockdowncount']!=0 or f['models'][i]['defense'][3]!=0:raise ValueError('DAMAGE_TAIL_COUNT_OR_PAIN_STATE_REQUIRED')
 motion=[]
 for i,row in enumerate(a['attacks']):
  if row['grab']or row['no_pain']:raise ValueError('DAMAGE_TAIL_GRAB_OR_NOPAIN_REQUIRED')
  xyz=[q16(v)for v in row['dropv']]
  if xyz[0]==-0x80000000:raise ValueError('DAMAGE_TAIL_NEGATE_X_OVERFLOW')
  motion.append(dict(id=i+1,dropv_q16=xyz,source_dropv=row['dropv'],q16_error=[q/65536-v for q,v in zip(xyz,row['dropv'])],damage_on_landing=row['damage_on_landing'],attack_type=row['attack_type']))
 return dict(schema='BYOR_CLOSED_COMMON_DAMAGE_TAIL_REQUIREMENTS_V1',capability='SOURCE_ZERO_ESCAPE_FALLDIE_NOPAIN_COUNT_NO_TAIL_WEAPONLOSS_NO_GRAB',models=p['models'],model_authority_sha256=p['source_authority_sha256'],attacks=motion,collision_table_bytes=a['collision_table_bytes'],motion_representation='ACCEPTED_COMPAT_Q16_16; existing source numeric adaptation, truncate toward zero; per-component deviation retained, no arbitrary binary32-equivalence claim',generic_child_services=['ent_unlink','source_action_identity','toss','set_fall','set_pain','player_die/kill'],native_tail_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(req):
 # xyz vector uses source x,y,z order, then full landing marker.
 payload=b''.join(struct.pack('<4i',*a['dropv_q16'],a['damage_on_landing'])for a in req['attacks'])
 return payload

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);r=derive(Source(a.source));b=pack(r);(a.output/'motion.bin').write_bytes(b);r.update(packed_motion_bytes=len(b),packed_motion_sha256=hashlib.sha256(b).hexdigest());(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(len(r['models']),'closed source models',len(r['attacks']),'authored motion rows')
if __name__=='__main__':main()
