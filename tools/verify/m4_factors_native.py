"""Exact independent native uniform factor snapshots and lease guards."""
import argparse,hashlib,itertools,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from script_callback_owner import derive,pack
from source_script_clone import derive as clone,pack as pack_clone
from source_model_factors import derive as factors,pack as pack_factors
from m4_script_clone_native import LUA as CLONE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols
LUA=CLONE_LUA.replace("local ranges={{0x40c000", "local ranges={{0x432800,4096},{0x43b900,512},{0x40c000")
LUA=LUA.replace(" set('SourceDefaultPlayer4086_Ready',0xb503)","""
 set('SourceFactors4086_Ready',0xb5f1);set('SourceFactors4086_Status',0);set('SourceFactors4086_Base',0x8000+CLONEBYTES);set('SourceFactors4086_Bank',59);set('SourceFactors4086_Bytes',FACTORBYTES);set('SourceFactors4086_Models',16);set('SourceFactors4086_Attacks',20)
 set('SourceDefaultPlayer4086_Ready',0xb503)""")
LUA=LUA.replace(" if c.bad=='ready'then", """ if c.bad=='factor_ready'then set('SourceFactors4086_Ready',0)
 elseif c.bad=='factor_sticky'then set('SourceFactors4086_Status',3)
 elseif c.bad=='factor_models'then set('SourceFactors4086_Models',15)
 elseif c.bad=='factor_attacks_low'then set('SourceFactors4086_Attacks',19)
 elseif c.bad=='factor_attacks_high'then set('SourceFactors4086_Attacks',256)
 elseif c.bad=='factor_attacks_pair'then set('SourceFactors4086_Attacks',21)
 elseif c.bad=='factor_table'then set('SourceFactors4086_Base',0x8000)
 elseif c.bad=='factor_bank'then set('SourceFactors4086_Bank',0)
 elseif c.bad=='factor_bytes'then set('SourceFactors4086_Bytes',FACTORBYTES-2)
 elseif c.bad=='ready'then""")
start=LUA.index(' if c.fault==0 then');end=LUA.index(' local s=emu.getState()',start)
LUA=LUA[:start]+""" if c.fault==0 then
 for j,value in ipairs(c.vector)do before[0x432800+c.slot*32+j-1]=value end
 before[0x43b900+c.slot*4]=c.model;before[0x43b901+c.slot*4]=0;before[0x43b902+c.slot*4]=241;before[0x43b903+c.slot*4]=181
 end
"""+LUA[end:]
LUA=LUA.replace("word(sy.SourceScriptClone4086_Status)","word(sy.SourceFactors4086_Status)")
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);s=Source(a.source);ct=pack_clone(clone(s));cb,*_=derive(s);bt=pack(cb);fr=factors(s);ft=pack_factors(fr)
 # Distinct immutable uniform vectors exercise bit copies, including signed
 # zero and negative values; fixture variants do not relabel authored models.
 fixture=json.loads(json.dumps(fr))
 for i,m in enumerate(fixture['models']):m['vector_hex']=struct.pack('<6fif',float(i+1),-0.0,1.25,-2.5,0,0,i-8,float(i)/16).hex()
 ft=pack_factors(fixture);base=dict(level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=0,mode=0,oldmask=0)
 rows=[dict(base,slot=slot,model=m['id'],alive=alive,vector=list(bytes.fromhex(m['vector_hex'])))for slot,m,alive in itertools.product((0,1,127),fixture['models'],(0,1))]
 for slot,bad in itertools.product((0,127),('factor_ready','factor_sticky','factor_models','factor_attacks_low','factor_attacks_high','factor_attacks_pair','factor_table','factor_bank','factor_bytes','ready','clone_sticky','world','pool','side','count','clone_slot','token','token_high','models','model','table','bank','bytes','vars','vars_count','callback','callback_models')):rows.append(dict(rows[0],slot=slot,bad=bad,fault=1))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('MODE',str(0x7ffd88)).replace('CLONEBYTES',str(len(ct))).replace('FACTORBYTES',str(len(ft))).replace('CALLBACKBYTES',str(len(bt))).replace('PROGRAMS',str(cb['program_count']))
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 entry=sy['SourceFactors4086_Apply'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-UNIFORM-FACTORS',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceFactors4086_Apply','SourceFactors4086_Ready',0xb5f1,[(59,0,ct+ft),(60,0,bt)],lua,r,batch_size=4)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line];r.check('independent exact binary32/int32 factor vectors, paired lease and attack identity, guards, untouched entity/variable/cache state and CPU context',results==[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)])
 d=dict(schema='BYOR_4086_UNIFORM_FACTORS_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,fixture_distinct_uniform_vectors=True,authored_vectors=fr,entity_snapshot_start=0x432800,entity_snapshot_bytes=4096,slot_identity_start=0x43b900,slot_identity_bytes=512,mutation_api_admitted=False,native_combat_bound=False,full_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
