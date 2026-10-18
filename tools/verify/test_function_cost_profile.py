"""Regression checks for read-only attribution boundaries."""
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import m4_function_cost_native as profile

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'out/byor-motu-exact-coverage-v1/success'


class FunctionCostProfileTests(unittest.TestCase):
    def test_preloading_matches_original_post_store_observer(self):
        contract=json.loads((FIXTURE/'contract.json').read_text())
        tags=profile.manifest(FIXTURE/'native',contract)
        actual=[pc for pc,tag in tags.items() if tag.get('preloading')]
        lua=(FIXTURE/'native/callback_owner.lua').read_text()
        expected=re.findall(r"nbLog\('PHASE','NbPreloading\|'.*?callbackType.exec,(\d+),(\d+)",lua)
        self.assertEqual(len(expected),1)
        self.assertEqual(expected[0][0],expected[0][1])
        self.assertEqual(actual,[int(expected[0][0])])
        self.assertEqual(actual,[0x39A140])

    def test_source_drift_rejects_preloading_boundary(self):
        contract=json.loads((FIXTURE/'contract.json').read_text())
        source=(FIXTURE/'native/publisher.pasm').read_text()
        anchor=' lda #2\n sta.l $42D600'
        self.assertEqual(source.count(anchor),1)
        with patch.object(Path,'read_text',return_value=source.replace(anchor,' lda #3\n sta.l $42D600')):
            with self.assertRaisesRegex(ValueError,'PRELOADING_BOUNDARY'):
                profile.manifest(FIXTURE/'native',contract)


if __name__=='__main__':unittest.main()
