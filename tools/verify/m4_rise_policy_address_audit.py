"""Decode actual long indexed policy reads and compare loaded source words."""
import argparse,hashlib,json,re,struct
from pathlib import Path
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset

def audit(folder,policy):
 sy=symbols(folder/'fixture.sym');raw=(folder/'bor.sfc').read_bytes();named='CommonRise_InvincibilityLow'in sy
 start=offset(sy['CommonRise_Run']);end=offset(sy['CommonRise_InvincibilityLow'if named else'CommonRise_Invincibility'])
 reads=list(re.finditer(b'\xbf(.{3})\x85\x18\xbf(.{3})\x85\x1a',raw[start:end],re.S));assert len(reads)==1,'RISE_POLICY_READ_INSTRUCTION_SHAPE'
 loaded=[int.from_bytes(reads[0][i],'little')for i in (1,2)]
 expected=[sy['CommonRise_InvincibilityLow'],sy['CommonRise_InvincibilityHigh']]if named else[sy['CommonRise_Invincibility'],sy['CommonRise_Invincibility']+2]
 table=[]
 for i,m in enumerate(policy['models']):
  displacement=i*(2 if named else 4)
  lo,hi=(struct.unpack_from('<H',raw,offset(at)+displacement)[0]for at in loaded)
  table.append(dict(model_id=i,loaded_word=lo|(hi<<16),source_word=m['fields']['riseinv']&0xffffffff))
 ok=loaded==expected and all(r['loaded_word']==r['source_word']for r in table)
 return dict(proof=str(folder).replace('\\','/'),status='PASS'if ok else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),indexed_read_instruction_offset=start+reads[0].start(),loaded_addresses=loaded,expected_addresses=expected,named_word_tables=named,model_words=table)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--requirements',type=Path,required=True);p.add_argument('--proof',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();policy=json.loads(a.requirements.read_text());rows=[audit(f,policy)for f in a.proof];ok=all(r['status']=='PASS'for r in rows)
 r=dict(schema='BYOR_RISE_LOADED_POLICY_ADDRESS_AUDIT_V1',status='PASS'if ok else'FAIL',proofs=rows,requirements_sha256=hashlib.sha256(a.requirements.read_bytes()).hexdigest(),actual_rom_instructions_decoded=True,actual_rom_table_words_compared=True);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],'loaded indexed policy addresses',len(rows));raise SystemExit(0 if ok else 1)

if __name__=='__main__':main()
