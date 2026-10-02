"""Generator-only production render-hook regression; no assembly or emulator."""
import ast
import unittest
from unittest.mock import patch

import source_publication_native as native


def depth(target):
    return ('Character_RenderPass:\nCharacter_RenderPass__render_live:\n'
            '    sep #$20\n.a8\n    jsl '+target+'\n'
            'Character_RenderPass__render_done:\n    rtl\n')


class RenderHookTests(unittest.TestCase):
    def test_both_targets_and_real_production(self):
        for target in ('Character_RenderFrame','StageTimerHost_RenderFrame'):
            hooked,actual=native.hook_render_live(depth(target))
            self.assertEqual(actual,target)
            self.assertEqual(hooked.count('jsl S7Publisher_RenderOrCompat'),1)
            self.assertNotIn('jsl '+target,hooked)
        hooked,target=native.hook_render_live((native.ROOT/'src/core/depth_sort.pasm').read_text())
        self.assertIn(target,('Character_RenderFrame','StageTimerHost_RenderFrame'))
        self.assertEqual(hooked.count('jsl S7Publisher_RenderOrCompat'),1)

    def test_missing_unknown_duplicate_and_outside_block_fail_closed(self):
        base=depth('Character_RenderFrame')
        bad=[base.replace('    jsl Character_RenderFrame\n',''),
             depth('Unknown_RenderFrame'),
             base.replace('    jsl Character_RenderFrame','    jsl StageTimerHost_RenderFrame\n    jsl Character_RenderFrame'),
             base+'    jsl StageTimerHost_RenderFrame\n',
             base.replace('Character_RenderPass__render_live:', 'Wrong_Label:'),
             base+base]
        for code in bad:
            with self.subTest(code=code),self.assertRaises(ValueError):
                native.hook_render_live(code)

    def test_emit_and_deferred_admission_preserve_current_fallback(self):
        publisher=(native.ROOT/'src/core/actor_source_publisher.pasm').read_text()
        for target in ('Character_RenderFrame','StageTimerHost_RenderFrame'):
            def read(path,*args,**kwargs):
                return depth(target) if path.name=='depth_sort.pasm' else publisher
            with patch.object(native.Path,'read_text',read):
                result=native.emit_code({target:0x123456},0,0,[],b'',b'')
                deferred=native.emit_code({target:0x123456},0,0,[],b'',b'',_defer_compat=True)
                template=native.emit_code({},0,0,[],b'',b'')
            self.assertEqual(template['compat_renderer'],'Character_RenderFrame')
            self.assertIn('    plp\n    jml Character_RenderFrame\n',template['assembly'])
            self.assertIn('    jml '+target+'\n',result['assembly'])
            self.assertEqual(result['imports'][target],0x123456)
            legacy='    plp\n    jml Character_RenderFrame\n'
            self.assertEqual(deferred['assembly'].count(legacy),1)
            guarded=deferred['assembly'].replace(legacy,'    ; owner checks\n'+legacy)
            bound=native.bind_compat_renderer(guarded,target)
            self.assertIn('    ; owner checks\n    plp\n    jml '+target+'\n',bound)
            for malformed in ('',legacy+legacy):
                with self.assertRaises(ValueError):native.bind_compat_renderer(malformed,target)

    def test_prepare_keeps_legacy_assert_before_late_binding(self):
        # Protect the established admission transform ordering without preparing media.
        source=(native.ROOT/'tools/bor_compile/source_publication_native.py').read_text()
        tree=ast.parse(source)
        prepare=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='prepare')
        section=ast.get_source_segment(source,prepare)
        self.assertIn('_defer_compat=True',section)
        self.assertLess(section.index('assert code.count(legacy)==1'),
                        section.index("code=bind_compat_renderer(code,result['compat_renderer'])"))
        self.assertLess(section.index("code=code.replace(legacy,"),
                        section.index("code=bind_compat_renderer(code,result['compat_renderer'])"))


if __name__=='__main__':unittest.main()
