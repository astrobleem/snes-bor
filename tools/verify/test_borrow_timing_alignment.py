import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import borrow_timing_alignment as stats

class WaitAccountingTests(unittest.TestCase):
    def rows(self):
        before=dict(a=0x3512,x=3,y=4,d=0x3400,dbr=0x42,sp=0x1ff0,ps=0x4d,counter=7)
        after=dict(before,a=0x3580,ps=0xcd)
        return [dict(kind='TA_WAIT_BEGIN',clock=100,frame=10,scanline=100,
            data=['1','4',str(0x39a100),*[str(before[k]) for k in stats.REGISTERS]]),
            dict(kind='TA_WAIT_END',clock=500,frame=11,scanline=225,
            data=['1','4','400',str(0x39a100),*[str(after[k]) for k in stats.REGISTERS]])]
    def parse(self,rows):
        with patch.object(stats.evidence.ready,'events',return_value=rows):
            return stats.parse_waits(Path('unused'),{0x39a100})
    def test_exact_poll_body_flags_preserved_registers_and_clock_accounting(self):
        waits=self.parse(self.rows());self.assertEqual(waits[0]['master_clocks'],400)
        transaction=dict(transaction=4,committed=True,start=50,finish=550,master_clocks=500,fields=2)
        row=stats.decompose(transaction,waits);self.assertEqual(row['non_poll_residual_clocks'],100)
        current=dict(row,total_clocks=596,wait_body_clocks=508,non_poll_residual_clocks=88)
        comparison=stats.compare(row,current)
        self.assertEqual((comparison['total_clocks_delta'],comparison['wait_body_clocks_delta'],
            comparison['non_poll_residual_clocks_delta']),(96,108,-12))
        self.assertFalse(comparison['strict_transaction_gate_pass'])
    def test_missing_duplicate_wrong_caller_and_bad_abi_reject(self):
        rows=self.rows()
        for changed in (rows[:1],rows+rows[1:],rows[::-1]):
            with self.assertRaises(ValueError):self.parse(changed)
        for index,value in ((3,'1'),(4,'0'),(9,'0'),(10,'0'),(11,'0')):
            changed=self.rows();changed[1]['data'][index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):self.parse(changed)
    def test_waits_must_fit_recorded_boundary_and_comparison_inventory(self):
        waits=self.parse(self.rows())
        with self.assertRaisesRegex(ValueError,'WAIT_NOT_WITHIN'):
            stats.decompose(dict(transaction=4,committed=True,start=101,finish=550,master_clocks=449,fields=2),waits)
        row=stats.decompose(dict(transaction=4,committed=True,start=50,finish=550,master_clocks=500,fields=2),waits)
        with self.assertRaisesRegex(ValueError,'COMPARISON_INVENTORY'):
            stats.compare(row,dict(row,wait_calls=2))
        with self.assertRaisesRegex(ValueError,'DECOMPOSITION_SUM'):
            stats.compare(row,dict(row,total_clocks=501))
    def test_actual_native_log_reader_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'mesen.log'
            path.write_text('\n'.join('NB_'+row['kind']+'|'+str(row['clock'])+'|'+str(row['frame'])+
                '|225|'+'|'.join(row['data']) for row in self.rows()))
            rows=stats.parse_waits(path,{0x39a100})
            self.assertEqual((rows[0]['entry_frame'],rows[0]['exit_frame'],rows[0]['master_clocks']),(10,11,400))
    def test_leaf_pairing_is_diagnostic_and_preserves_exact_inputs(self):
        row=dict(sequence=1,transaction='3',home=1,count=41,prepared=1,input_sha256='a'*64,
            return_pc=0x39b526,caller_return_pc=0x39a1a9,master_clocks=100)
        self.assertEqual(stats.pair_leafs([dict(row,master_clocks=196)],[row])['3']['clock_delta'],96)
        with self.assertRaisesRegex(ValueError,'LEAF_INPUT_DRIFT'):
            stats.pair_leafs([dict(row,home=2)],[row])
if __name__=='__main__':unittest.main()
