"""Focused S8 source-set prompt checks. Isolated assembly only; no emulator.

Engine imports use the existing symbol file as link addresses, not callback
stubs. No distribution ROM, generated gate, or shared runtime file is built.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from compiler import ROOT, Source, project


CAMPAIGN = ROOT/'src/core/campaign.pasm'
SELECTOR = ROOT/'src/core/set_select.pasm'
CONFIG = ROOT/'tools/audio/campaign_config.pasm'


def reset_body():
    return (ROOT/'src/core/ending.pasm').read_text().split('Game_State_NewGameReset:', 1)[1].split('ENDING_ROW_LINE1 =', 1)[0]


class SetSelectTests(unittest.TestCase):
    def test_source_menu_and_generated_names(self):
        source = (ROOT/'out/bor_compile_s6/BOR.C').read_text()
        menu = source.split('int choose_difficulty(){', 1)[1].split('void soundcard_options()', 1)[0]
        for fragment in ('int selector = 0;', 'selector = i;', 'selector = 0;',
                         'set_names[i]', 'savedata.times_completed >= ifcomplete[selector]', 'return -1;'):
            self.assertIn(fragment, menu)
        sets = project(Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')).sets
        rows = CONFIG.read_text().split('BorSet_Names:', 1)[1].split('\n\n', 1)[0]
        names = [bytes(map(int, line.split('.db ', 1)[1].split(','))).split(b'\0')[0].decode()
                 for line in rows.splitlines() if '.db ' in line]
        self.assertEqual(names, [s.name for s in sets])
        text = SELECTOR.read_text()
        self.assertIn('lda.l BorSet_Names,x', text)
        self.assertIn('adc #BOR_SET_NAME_WIDTH', text)
        self.assertNotIn('.db "Easy', text)
        self.assertNotRegex(text, r'^\w+\s*=\s*\$7[Ee]', 'selector must not allocate WRAM')

    def test_full_counter_predicate_and_clean_index(self):
        body = CAMPAIGN.read_text().split('BorSet_IsUnlocked:', 1)[1].split('BorSet_IsAvailable:', 1)[0]
        offsets = [int(x) for x in re.findall(r'(?:lda|ora)\.l Bor_TimesCompleted\+(\d)', body)]
        self.assertEqual(offsets, [1, 2, 3])
        self.assertRegex(body, r'and #\$00FF\s+tax\s+sep #\$20')
        for count in (0, 1, 254, 255, 256, 257, 65535, 65536, 0x1000000, 0xffffffff):
            for threshold in (0, 1, 2, 255):
                cells = count.to_bytes(4, 'little')
                result = any(cells[i] for i in offsets) or cells[0] >= threshold
                self.assertEqual(result, count >= threshold, (count, threshold))
        self.assertIn('BorSet_IsUnlocked__true:\n    sec', body)

    def test_gate_conjunction_and_compiler_complete_normal_is_available(self):
        text = CAMPAIGN.read_text()
        available = text.split('BorSet_IsAvailable:', 1)[1].split('BorSet_IsSelectable:', 1)[0]
        self.assertIn('lda.l BorSet_ContentAvailable,x', available)
        self.assertIn('cmp #BOR_SET_UNMAPPED', available)
        selectable = text.split('BorSet_IsSelectable:', 1)[1].split('BorSet_BeginEasyRun:', 1)[0]
        self.assertIn('jsl BorSet_IsUnlocked', selectable)
        self.assertIn('jsl BorSet_IsAvailable', selectable)
        flags = CONFIG.read_text().split('BorSet_ContentAvailable:', 1)[1].splitlines()[1]
        # The compiler exposes Normal only after its complete authored set is valid.
        self.assertEqual([int(x) for x in flags.split('.db ', 1)[1].split(',')][1], 1)
        # Both failed predicates must stop confirmation before phase 2.
        prompt = SELECTOR.read_text().split('BorSetSelect_Play:', 1)[1].split('BorSetSelect_Finish:', 1)[0]
        self.assertIn('jsl BorSet_IsSelectable\n    bcc BorSetSelect_Play__draw', prompt)

    def test_prompt_only_and_real_confirmation_retained(self):
        charselect = (ROOT/'src/core/charselect.pasm').read_text()
        block = charselect.split('Game_State_Play__charselect_draw_difficulty:', 1)[1].split('; --- Draw/clear', 1)[0]
        for call in ('Begin', 'Play', 'Finish'):
            self.assertIn('jsl BorSetSelect_'+call, block)
        self.assertNotIn('Text_Str_Difficulty', block)
        self.assertIn('and #$0010', charselect.split('Game_State_Play__charselect_p2_start:', 1)[1])
        self.assertNotIn('sta.l BorSelect_P2Ready', SELECTOR.read_text())
        self.assertNotIn('sta.l G13_TwoPlayerEnabled', SELECTOR.read_text())
        title = (ROOT/'src/core/game_state.pasm').read_text().split('Game_State_Play__title_wait:', 1)[1].split('Game_State_Play__paused:', 1)[0]
        self.assertNotIn('BorSetSelect_', title)
        self.assertIn('jsl G13_EnableP2Session', title)

    def test_selected_run_resolves_typed_entry_and_fail_closed(self):
        run = CAMPAIGN.read_text().split('BorSet_BeginSelectedRun:', 1)[1].split('; BOR.C load_levelorder()', 1)[0]
        for fragment in ('jsl BorSet_IsSelectable', 'lda.l BorSet_CampaignMap,x',
                         'lda #$FF', 'jsl Game_Campaign_ResolveNext'):
            self.assertIn(fragment, run)
        self.assertNotIn('sta.l BorSet_Selected', run)
        body = reset_body()
        self.assertIn('jsl BorSet_BeginSelectedRun', body)
        self.assertNotIn('jsl BorSet_BeginEasyRun', body)
        self.assertIn('lda.l Game_Campaign_ResolvedValue\n    and #$00FF\n    sta.l Game_StageIndex', body)
        self.assertIn('jsl Game_Campaign_DispatchResolved', body)
        self.assertNotRegex(body, r'lda #(?:0|22)\s+sta.l Game_StageIndex')
        # Independently resolve the actual first source stage through the
        # catalog, rather than naming physical 0/22 in the startup contract.
        sys.path.insert(0, str(ROOT))
        import build_rom
        source_sets = project(Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')).sets
        for source_name, prefix in (('Easy', 'Bor'), ('Normal', 'BorNormalDev')):
            first = next(s for s in source_sets if s.name == source_name).entries[0]
            normalize = lambda p: str(p).replace('\\', '/').lower()
            physical = [i for i, c in enumerate(build_rom.STAGE_CONFIGS)
                        if normalize(c.get('source_level', '')) == normalize(first.source_path)]
            self.assertEqual(len(physical), 1)
            generated = CONFIG.read_text().split('Campaign_'+prefix+'_EntryValues:', 1)[1].splitlines()[1]
            self.assertEqual(int(generated.split('.db ', 1)[1].split(',')[0]), physical[0])

    def test_width_directives(self):
        sys.path.insert(0, str(ROOT/'tools/rom_audit'))
        from check_width_directives import flatten, scan
        for path in (SELECTOR, CAMPAIGN):
            violations, count = scan(flatten(str(path)))
            self.assertGreater(count, 10)
            self.assertEqual(violations, [], str(path))

    def test_isolated_actual_modules_assemble(self):
        dotnet = os.environ.get('DOTNET', r'C:\Users\chad\.dotnet\dotnet.exe')
        poppy = os.environ.get('POPPY_DLL', r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')
        if not Path(dotnet).is_file() or not Path(poppy).is_file():
            self.skipTest('Poppy unavailable')
        bodies = '\n'.join((CAMPAIGN.read_text(), SELECTOR.read_text(), CONFIG.read_text(),
                            (ROOT/'src/core/charselect.pasm').read_text(),
                            'Game_State_NewGameReset:'+reset_body()))
        owned = set(re.findall(r'^([A-Za-z_]\w*)\s*(?::|=)', bodies, re.M))
        used = set(re.findall(r'\b[A-Za-z_]\w*\b', bodies))
        imports = []
        for line in (ROOT/'src/main.sym').read_text().splitlines():
            match = re.match(r'([\da-fA-F]{2}):([\da-fA-F]{4,6})\s+(\w+)$', line)
            if not match:
                continue
            bank, raw, name = match.groups()
            if name in used and name not in owned:
                value = int(raw, 16) if len(raw) > 4 else int(bank, 16)*65536+int(raw, 16)
                imports.append(f'{name} = ${value:06X}')
        fixture = '\n'.join(['.snes', *imports, '.bank 12', '.org $8000',
                             f'.include "{CAMPAIGN.as_posix()}"', '.bank 17', '.org $8000',
                             f'.include "{SELECTOR.as_posix()}"', '.bank 5', '.org $8000',
                             f'.include "{(ROOT/"src/core/charselect.pasm").as_posix()}"',
                             '.bank 13', '.org $8000', 'Game_State_NewGameReset:'+reset_body()])
        with tempfile.TemporaryDirectory(prefix='s8_set_select_') as tmp:
            path, output = Path(tmp)/'selector.pasm', Path(tmp)/'selector.bin'
            path.write_text(fixture)
            run = subprocess.run([dotnet, poppy, str(path), '-o', str(output)],
                                 cwd=tmp, text=True, capture_output=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            self.assertIn(bytes.fromhex('22008011'), output.read_bytes())  # actual CHARSELECT -> Begin


if __name__ == '__main__':
    unittest.main()
