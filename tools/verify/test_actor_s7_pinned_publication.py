"""Focused code-generation boundary; native ownership is covered by live traces."""
import unittest
from unittest.mock import patch
from actor_s7_native_publisher import emit_code


class NativeTemplateTests(unittest.TestCase):
    def test_template_requires_no_fixture_asset_or_model(self):
        with patch('actor_s7_native_publisher.parse_model',side_effect=AssertionError('fixture lookup')):
            result=emit_code({},77,12,[{}],b'',b'',stream=True)
        self.assertIn('S7Publisher_RenderOrCompat',result['assembly'])
        self.assertIn('cmp.l S7Pub_State+28',result['assembly'])
        self.assertNotIn('data/chars/kula',result['assembly'])


if __name__=='__main__':unittest.main()
