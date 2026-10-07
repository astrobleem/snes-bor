"""Generic source attack-role profile and weighted choice reference."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_profile import document
from source_animation_ids import configure
from source_actor_numeric import random32_step
from dialect_4086 import ENGINE_COMMIT
from source_animation_energy_4086 import derive as energy,pack as pack_energy

CAPACITY=64

def derive(source):
 config=configure(document(source,'data/models.txt')['directives']);enums=config['authority']['enum']
 normal=config['arrays']['normal_attacks'];special=config['arrays']['freespecials']
 animations=energy(source);pack_energy(animations)
 if len(normal)+len(special)+3>CAPACITY:raise ValueError('ATTACK_CHOICE_ROLE_CAPACITY')
 return dict(schema='BYOR_4086_ATTACK_CHOICE_PROFILE_V1',engine_authority=ENGINE_COMMIT,
             maximum_animations=config['max_animations'],frame_handles=len(animations['animations']),positive_frame_counts_required=True,normal_roles=normal,special_roles=special,
             extra_roles=[enums['ANI_THROWATTACK'],enums['ANI_JUMPATTACK'],enums['ANI_UPPER']],
             normal_weights=[max(5-i,0)*3+1 for i in range(len(normal))],capacity=CAPACITY,
             runtime_bound=False,motu_gameplay_proven=False)

def pack(report):
 normal,special=report['normal_roles'],report['special_roles'];roles=normal+special+report['extra_roles']
 if len(roles)>CAPACITY or len(report['extra_roles'])!=3 or not 1<=report['maximum_animations']<=1024 or not 1<=report['frame_handles']<=2047 or any(not 0<=role<report['maximum_animations']for role in roles):raise ValueError('ATTACK_CHOICE_PROFILE_DOMAIN')
 return struct.pack('<4s6H',b'B4AC',1,len(normal),len(special),report['maximum_animations'],CAPACITY,report['frame_handles'])+struct.pack('<'+'H'*len(roles),*roles)

def choose(profile,valid,range_ok,energy_ok,projectile,testonly,seed,target_present=True):
 choices=[]
 for i,role in enumerate(profile['normal_roles']):
  if role in valid and(not target_present or role in range_ok):choices.append((role,max(5-i,0)*3+1))
 for role in profile['special_roles']:
  if role in valid and role in energy_ok and(not target_present or role in range_ok):choices.append((role,1))
 throw,jump,upper=profile['extra_roles']
 if throw in valid and projectile and(not target_present or throw in range_ok):choices.append((throw,1))
 # The pinned function returns from testonly BEFORE jump/upper fallback.
 if not testonly:
  for role in (jump,upper):
   if role in valid and(not target_present or role in range_ok):choices.append((role,1))
 total=sum(w for _,w in choices)
 if not total:return dict(result=-1,seed_after=seed,calls=0,total=0,choices=choices)
 after,value=random32_step(seed);index=(value&65535)%total
 for role,weight in choices:
  if index<weight:return dict(result=role,seed_after=after,calls=1,total=total,choices=choices)
  index-=weight
 raise AssertionError('ATTACK_CHOICE_SELECTION')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));table=pack(r);r.update(table_bytes=len(table),table_sha256=hashlib.sha256(table).hexdigest());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');a.output.with_suffix('.b4ac').write_bytes(table);print('Derived',len(r['normal_roles']),'normal and',len(r['special_roles']),'special roles;',len(table),'bytes')

if __name__=='__main__':main()
