"""ASAD admission, bank-crossing addressing and transfer-tail invariants."""
import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from source_frame_audio_rom import pack,unpack,install,ROM_BASE,CPU_BASE


class AudioRomTests(unittest.TestCase):
    def test_long_asset_and_padding(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);assets=folder/'assets';assets.mkdir();rows=[]
            for index,length in enumerate([76509,8073]):
                brr=bytearray(length);brr[-9]=1;filename=f'{index}.brr';(assets/filename).write_bytes(brr)
                rows.append(dict(sound_index=index,brr_path=filename,brr_bytes=length,brr_sha256=hashlib.sha256(brr).hexdigest(),source_path=f'{index}.wav',source_sha256='source'))
            (assets/'report.json').write_text(json.dumps(dict(namespace=['0.wav','1.wav'],compiled=rows,source_frame_table_sha256='table')))
            result=pack(assets,folder/'packed');self.assertTrue(result['assets'][0]['crosses_64k_bank'])
            table=(folder/'packed/descriptors.bin').read_bytes();data=(folder/'packed/payload.bin').read_bytes();raw=bytearray(4*1024*1024)
            install(raw,table,data,60*32768+16384)
            for descriptor,row in zip(unpack(table),rows):
                at=ROM_BASE+descriptor['cpu_pointer']-CPU_BASE
                self.assertEqual(raw[at:at+row['brr_bytes']],(assets/row['brr_path']).read_bytes())
            with self.assertRaisesRegex(ValueError,'RESERVATION_NOT_EMPTY'):install(raw,table,data,60*32768+16384)

    def test_reject_bad_count_length_overlap_and_padding(self):
        with self.assertRaisesRegex(ValueError,'NAMESPACE_COUNT'):
            unpack(struct.pack('<4sHH',b'ASAD',1,2048)+bytes(2048*8))
        header=struct.pack('<4sHH',b'ASAD',1,2)
        row=CPU_BASE.to_bytes(3,'little')+(9).to_bytes(3,'little')+struct.pack('<H',1)
        with self.assertRaisesRegex(ValueError,'OVERLAP'):unpack(header+row+row)
        with self.assertRaisesRegex(ValueError,'HEADER_OR_LENGTH'):unpack(header+row)
        with self.assertRaisesRegex(ValueError,'LENGTH_OR_CHUNKS'):unpack(struct.pack('<4sHH',b'ASAD',1,1)+row[:-2]+bytes(2))
        table=struct.pack('<4sHH',b'ASAD',1,1)+row
        raw=bytearray(4*1024*1024);payload=bytes(9)+b'\1'+bytes(134)
        with self.assertRaisesRegex(ValueError,'TRANSFER_PADDING'):install(raw,table,payload,0x1e0000)
        self.assertFalse(any(raw))


if __name__=='__main__':unittest.main()
