"""Abort copy model/ROM admission, bus ordering and cold-path fault tests."""
import copy,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import m4_abort_copy_native as native
import abort_copy_evidence as evidence


class AdapterTests(unittest.TestCase):
    def rows(self,owner=2):
        before=dict(a=456,x=9,y=10,d=0x3400,dbr=0x7e,sp=0x1fe0,ps=0xcd,counter=0x55aa)
        after=dict(before,a=0,x=0xd000,y=0xc800,ps=0x4f)
        committed=bytes(i*17%256 for i in range(2048));refs=bytes(i*19%256 for i in range(1536))
        path='fast' if 1<=owner<=4 else 'legacy';trace,bus=evidence.expected_bus(committed,path)
        order=evidence.reference.REGISTERS
        return [dict(kind='PHASE',clock=50,data=['NbAbort','3']),
            dict(kind='CA_ENTRY',clock=100,data=['3','1',*[str(before[k]) for k in order],bytes(2048).hex(),committed.hex(),refs.hex(),str(owner)]),
            dict(kind='CA_PATH',clock=150,data=['3','1',path]),
            dict(kind='CA_SCAN',clock=300,data=['3','1','200',*[str(after[k]) for k in order],committed.hex(),committed.hex(),refs.hex(),trace,'2048',bus]),
            dict(kind='CA_CLOSED',clock=350,data=['3','1','d60000d60100','0'])]

    def parse(self,rows):
        with patch.object(evidence.reference.ready,'events',return_value=rows):return evidence.native_copies(Path('unused'))

    def test_fast_and_legacy_bus_interleaving_owner_and_close(self):
        for owner in (0,1,2,3,4,5,65535):
            r=self.parse(self.rows(owner))['1']
            self.assertEqual(r['path'],'fast' if 1<=owner<=4 else 'legacy')
            self.assertTrue(r['owner_close_guarded'])
        self.assertEqual(self.parse([]),{})
        fast=self.rows();legacy=self.rows(0)
        self.assertNotEqual(fast[3]['data'][16],legacy[3]['data'][16])
        bad=copy.deepcopy(fast);bad[3]['data'][16]=legacy[3]['data'][16]
        with self.assertRaisesRegex(ValueError,'ORDERED_BUS_INTERLEAVING'):self.parse(bad)
        bad=copy.deepcopy(legacy);bad[2]['data'][2]='fast'
        with self.assertRaisesRegex(ValueError,'PATH_OWNER'):self.parse(bad)

    def test_frozen_arrays_cpu_and_write_trace_faults_reject(self):
        for index,value in ((3,'1'),(7,'0'),(9,'0'),(10,'0'),(11,'ff'*2048),(12,'00'*2048),(13,'00'*1536),(14,''),(15,'2047')):
            bad=self.rows();bad[3]['data'][index]=value
            with self.assertRaises(ValueError):self.parse(bad)
        bad=self.rows();bad[1]['data'][7]=str(0x346f)
        with self.assertRaisesRegex(ValueError,'ENTRY_ABI'):self.parse(bad)

    def test_inventory_and_closing_boundary_faults_reject(self):
        for bad in (self.rows()[:-1],self.rows()+[self.rows()[-1]],self.rows()[1:]):
            with self.assertRaises(ValueError):self.parse(bad)
        bad=self.rows();bad[-1]['clock']=300
        with self.assertRaisesRegex(ValueError,'CLOSE_CLOCK'):self.parse(bad)
        for index,value in ((0,'4'),(2,'d60000'),(3,'1')):
            bad=self.rows();bad[-1]['data'][index]=value
            with self.assertRaises(ValueError):self.parse(bad)

    def test_independent_literal_and_pc_map(self):
        code,labels,access=native.independent_code()
        self.assertEqual(len(code),256);self.assertEqual(labels['CaLegacyCopy'],0x39a34d)
        self.assertEqual(code[:18],bytes.fromhex('08af00d642d0034c38afc9050090034c38af'))
        self.assertEqual(code[-8:],bytes.fromhex('288ba9ff074c4da3'))
        self.assertEqual(len(access),64)
        for pc,(kind,_) in access.items():self.assertEqual(code[pc-0x39ae40-3],0xbd if kind=='read' else 0x9d)
        self.assertEqual(access[0x39ae5f],('read',0));self.assertEqual(access[0x39ae62],('write',0))

    def test_whole_rom_and_disabled_control(self):
        folder=Path('out/byor-motu-abort-copy-static-v2/candidate/native');rom=(folder/'bor.sfc').read_bytes()
        result=native.audit_rom(rom,folder)
        self.assertEqual(result['abort_copy']['code_bytes'],256)
        self.assertEqual(result['abort_copy']['branch_sites'],321)
        self.assertEqual(native.capture.sha(Path('out/byor-motu-abort-copy-static-v2/control/native/bor.sfc')),native.accepted.BASE_SHA)
        from m4_input_controller_native import offset
        for pc in (0x39a349,0x39a34d,0x39a35a,0x39ab00,0x39ae40,0x39af3f,0x39a200):
            changed=bytearray(rom);changed[offset(pc)]^=1
            with self.assertRaises(ValueError):native.audit_rom(changed,folder)

    def test_existing_pass_receipt_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'abort-copy-receipt.json';path.write_bytes(b'KEEP')
            with patch.object(native.capture,'verify_capture',side_effect=AssertionError('TOO_LATE')):
                with self.assertRaisesRegex(ValueError,'EXISTING_PASS_RECEIPT_MUST_BE_RETAINED'):
                    native.collect_suite(root,None)
            self.assertEqual(path.read_bytes(),b'KEEP')

    def test_emitted_lua_guards_entry_interval_paths_and_owner_close(self):
        # Execute the emitted guard code, rather than a Python reimplementation.
        # Host Lua5.1 lacks '&': for nonnegative 24-bit bus addresses, masking
        # to16 bits equals modulo65536. This is the only syntax substitution.
        lua=Path(os.environ.get('LUA_EXE','C:/Program Files (x86)/Lua/5.1/lua.exe'))
        self.assertTrue(lua.is_file())
        path=Path('out/byor-motu-abort-copy-static-v2/candidate/native/observer-preflight-v3.lua')
        emitted=path.read_text().split('local caGuard=false;',1)[1]
        emitted=('local caGuard=false;'+emitted).replace('a&0xffff','(a%65536)')
        self.assertNotIn('&',emitted)
        stub="""
local callbacks={};local faults={};local state={};local owner=2
nbTxn=3
function nbWord(a)if a==0x42d600 then return owner end return 0 end
function cpDump(a,n)return string.rep('00',n)end
function nbLog(kind,data)if kind=='FAULT' then faults[#faults+1]=data end end
emu={callbackType={exec='exec',read='read',write='write'},cpuType={snes='snes',sa1='sa1'},memType={snesMemory=1,snesSaveRam=2}}
function emu.getState()return state end
function emu.addMemoryCallback(fn,kind,lo,hi,cpu,mem)
 callbacks[kind..':'..cpu..':'..lo]=fn
end
local function call(kind,cpu,lo,...)
 local fn=callbacks[kind..':'..cpu..':'..lo];assert(fn,'CALLBACK_MISSING');fn(...)
end
local function resetState()
 state={masterClock=100,['cpu.a']=1,['cpu.x']=0,['cpu.y']=0,['cpu.d']=0x3400,
  ['cpu.dbr']=0x42,['cpu.sp']=0x1fe0,['cpu.ps']=1,['cpu.pc']=0xae40,['cpu.k']=0x39}
end
"""
        scenarios=[
            "call('read','sa1',0x2c000,0x42c800,17);assert(#faults==1,'ENTRY_READ_ESCAPED')",
            "state['cpu.pc']=0xa35e;call('write','snes',0x2d600,0x42d600,0);assert(#faults==1,'PREMATURE_CLOSE_ESCAPED')",
            "call('write','sa1',0x2d600,0x42d600,0);assert(#faults==1,'ENTRY_OWNER_ESCAPED')",
            """
call('exec','snes',0x39ae52)
state['cpu.pc']=0xae5f;call('read','snes',0x2c000,0x42c800,17)
call('read','snes',0x2c000,0x42c801,34)
state['cpu.pc']=0xae62;call('write','snes',0x2c000,0x42c000,17)
call('write','snes',0x2c000,0x42c001,34)
state.masterClock=300;call('exec','snes',0x39a35a)
state['cpu.pc']=0xa35e
call('write','snes',0x2d600,0x42d600,0);call('write','snes',0x2d600,0x42d601,0)
owner=0;state.masterClock=350;call('exec','snes',0x39a35e)
assert(#faults==0,'VALID_FAST_PATH_FAULT')
call('read','sa1',0x2c000,0x42c800,17);assert(#faults==0,'CLOSED_GUARD_REMAINED_ARMED')
""",
            """
call('exec','snes',0x39af38)
state['cpu.pc']=0xa356;state['cpu.x']=0xc800;state['cpu.y']=0xc000
call('read','snes',0x2c000,0x42c800,17);call('write','snes',0x2c000,0x42c000,17)
assert(#faults==0,'VALID_LEGACY_BYTE_FAULT')
call('read','snes',0x2c000,0x42c801,17);assert(#faults==1,'LEGACY_WRONG_BYTE_ESCAPED')
""",
        ]
        with tempfile.TemporaryDirectory() as directory:
            for index,scenario in enumerate(scenarios):
                script=Path(directory)/f'guard-{index}.lua'
                setup="resetState();owner=0;call('exec','snes',0x39ae40)\n" if index==4 else "resetState();call('exec','snes',0x39ae40)\n"
                script.write_text(stub+emitted+'\n'+setup+scenario+'\nprint("GUARD_CASE_PASS")\n')
                result=subprocess.run([str(lua),str(script)],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('GUARD_CASE_PASS',result.stdout)


if __name__=='__main__':unittest.main()
