"""Offline guard tests only; never imports or starts an emulator."""
import os
from pathlib import Path
import tempfile
import unittest

from game_s8_stage_bounds import assembly_dependencies, admission_script, read_admissions, symbols, ROOT, Proof, lorom_offset
from game_s8_ramon import native_landed, observer, FIELDS, parse_log, check_birth


class ProbeGuards(unittest.TestCase):
    def test_recursive_dependencies_and_freshness(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'sub').mkdir()
            main=root/'main.pasm'; child=root/'sub/child.pasm'
            blob=root/'asset.bin'; unrelated=root/'fp.pasm'
            main.write_text('.include "sub/child.pasm"\n; .include "missing"\n')
            child.write_text('.incbin "../asset.bin"\n')
            blob.write_bytes(b'\0'); unrelated.write_text('; not included')
            for path in (main,child,blob): os.utime(path,ns=(100,100))
            os.utime(unrelated,ns=(300,300))
            deps=assembly_dependencies(main)
            self.assertEqual(set(deps),{main,child,blob})
            self.assertFalse([p for p in deps if p.stat().st_mtime_ns>200])
            for path in (child,blob):
                os.utime(path,ns=(300,300))
                self.assertIn(path,[p for p in deps if p.stat().st_mtime_ns>200])

    def test_missing_and_cycles_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            main=Path(folder)/'main.pasm'
            main.write_text('.incbin "missing.bin"')
            with self.assertRaises(FileNotFoundError): assembly_dependencies(main)
            main.write_text('.include "main.pasm"')
            with self.assertRaises(AssertionError): assembly_dependencies(main)

    def test_landing_requires_real_ground_and_recovery(self):
        for state in range(8):
            self.assertEqual(native_landed(dict(zpos=0,zvel=0,selected=state)),state in (0,1))
        self.assertFalse(native_landed(dict(zpos=0x7800,zvel=0,selected=1)))
        self.assertFalse(native_landed(dict(zpos=0,zvel=0xff80,selected=0)))

    def test_observer_records_native_drop_without_state_writes(self):
        names={n for n,_ in FIELDS.values()}
        names.update(('PlayerEntity_DpBase','CHAR_ZP_LEN','Spawn_Index','Msu1_StreamBusy',
                      'AnimHeaderStaging','Spawn_Play__environment_done','Game_CampaignId',
                      'Game_StageIndex','Spawn_ScratchSlotOfs','Anim_Play__dispatch','Msu1_LoadFrame',
                      'Character_Throw_Play','Character_Throw_Play__still_air','StageDrop_State',
                      'Spawn_ScratchIdx','Spawn_ScratchKind','Spawn_ScratchSubtype','Spawn_ScratchRosterIdx','SpawnTable_Wram'))
        syms={name:i+1 for i,name in enumerate(sorted(names))}
        lua=observer(syms,dict(stage=31,roster=45,queue_index=8))
        self.assertIn('zpos=',lua); self.assertIn('stream_busy=',lua)
        self.assertEqual(lua.count('emu.write('),1)  # existing journaled POS loop only
        live=observer(syms,dict(stage=31,roster=45,queue_index=8),Path('birth.log'))
        self.assertIn('io.open("birth.log",\'a\')',live)
        self.assertIn("out:write(table.concat(p,'|'),'\\n');out:close()",live)
        self.assertEqual(parse_log('S8R|frame|zpos=30720|selected=6|frame=255')[0]['zpos'],30720)

    def test_ramon_birth_exact_record_and_index_not_postfixture_count(self):
        record=bytes.fromhex('0000e00088015d06002d')
        spec=dict(queue_index=8,queue=(bytes(80)+record).hex(),roster=45,hp=6)
        birth=dict(queue=8,admitted_index=8,kind=5,subtype=2,roster=45,bound_roster=45,hp=6,
                   **{'q'+str(i):b for i,b in enumerate(record)})
        self.assertIs(check_birth([birth],spec),birth)
        for change in ({'queue':64},{'admitted_index':9},{'subtype':0},{'q9':7},{'roster':7}):
            with self.assertRaises(AssertionError): check_birth([dict(birth,**change)],spec)

    def test_completed_spawn_observer_is_read_only_and_checks_existence(self):
        lua=admission_script(symbols(ROOT/'src/main.sym'),Path('admissions'))
        self.assertNotIn('emu.write',lua)
        self.assertNotIn('breakExecution',lua)
        self.assertIn('emu.cpuType.snes,emu.memType.snesPrgRom',lua)
        self.assertIn(str(lorom_offset(symbols(ROOT/'src/main.sym')['Spawn_Play__environment_done'])),lua)
        for term in ('local obj=', 'local present=0', 'present=1', 'for i=0,9', "'a'"):
            self.assertIn(term,lua)

    def test_shared_lorom_callback_contract(self):
        self.assertEqual(lorom_offset(0x038cd5),0x18cd5)
        self.assertEqual(lorom_offset(0x838cd5),0x18cd5)
        with self.assertRaises(ValueError): lorom_offset(0x7e8cd5)

    def test_traversal_uses_complete_script_api_without_rewrites(self):
        syms=symbols(ROOT/'src/main.sym')
        lua=admission_script(syms,Path('records.txt'),include_controls=True,traversal_fields=True,
                             status_path=Path('records.status'),heartbeat_symbol='Spawn_Play')
        self.assertIn('if kind==255 then return end',lua)
        self.assertNotIn('if kind==2 or',lua)
        self.assertIn('row[#row+1]=bosses[slot]',lua)
        self.assertIn("status('READY')",lua)
        self.assertIn('pcall(admission)',lua)
        self.assertIn(str(lorom_offset(syms['Spawn_Play'])),lua)
        self.assertEqual(lua.count('emu.addMemoryCallback('),2)

    def test_first_bad_admission_fails_instead_of_picking_match(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'admissions'
            # First completed enemy has no OOP existence; a later matching
            # live actor must not conceal the first event's failure.
            path.write_text('3 24 0 133 0 0 6 2 7 2 8 '+'0 '*9+'0\n'+
                            '3 24 1 266 0 1 6 2 45 4 9 '+'0 '*9+'0\n')
            self.assertEqual(len(read_admissions(path)),2)
            from types import SimpleNamespace
            proof=object.__new__(Proof)
            proof.m=SimpleNamespace(bounds_admissions=path)
            proof.s={'CHAR_ZP_LEN':133}; proof.report={}
            proof.wait=lambda predicate: self.assertTrue(predicate())
            def need(name,passed):
                if not passed: raise AssertionError(name)
            proof.need=need
            with self.assertRaisesRegex(AssertionError,'live physical object'):
                proof.npc(dict(physical=24,campaign=3),0)
            self.assertEqual(proof.report['npc_admissions'][0]['roster'],7)


if __name__=='__main__': unittest.main()
