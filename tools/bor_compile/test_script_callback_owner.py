from pathlib import Path
import struct
import unittest
from compiler import Source
from script_callback_owner import derive,pack,unpack,installed_local_writes,validate_pair,NULL_PROGRAM
from source_model_registry import derive as model_registry,pack as pack_registry
from script_ir_4086 import parse_script


class CallbackOwner(unittest.TestCase):
    def test_shared_installed_namespace_cannot_use_entry_snapshot_when_mutable(self):
        for body in ('setlocalvar("frame",99);','setlocalvar(key,99);',
                     'setlocalvar("f"+suffix,99);','setlocalvar(""+suffix,99);'):
            self.assertTrue(installed_local_writes(parse_script('void main(){'+body+'}','probe.c')))
        for body in ('setlocalvar("Loop",42);','setlocalvar("Loop"+self,42);',
                     'setlocalvar("T"+self,NULL());','setlocalvar("frame#"+self,42);',
                     'setlocalvar("Frame",42);'):
            self.assertEqual(installed_local_writes(parse_script('void main(){'+body+'}','probe.c')),[])

    def test_all_model_programs_and_initializer_ranges_pair_to_source(self):
        source=Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak')
        report,code,metadata,dispatch=derive(source);data=pack(report)
        rows=validate_pair(data,pack_registry(model_registry(source)),code,metadata,dispatch)
        self.assertEqual(len(rows),16);self.assertEqual(report['program_count'],7)
        self.assertEqual(sum(r[1]!=NULL_PROGRAM for r in rows),7)
        for expected,row in zip(report['models'],rows):
            self.assertEqual(list(row[:6]),[expected[n] for n in ('id','program','slot_base','slot_count','initializers_offset','capability')])
            if row[1]!=NULL_PROGRAM:
                source_slots=metadata[row[4]:row[4]+8*row[3]]
                self.assertEqual(len(source_slots),8*row[3])
        for bad in (data[:-1],data+b'\0'):
            with self.assertRaises(ValueError):unpack(bad)
        bad=bytearray(data);struct.pack_into('<H',bad,32,99)
        with self.assertRaises(ValueError):unpack(bad)
        with self.assertRaises(ValueError):validate_pair(data,pack_registry(model_registry(source)),code+b'\0',metadata,dispatch)


if __name__=='__main__':unittest.main()
