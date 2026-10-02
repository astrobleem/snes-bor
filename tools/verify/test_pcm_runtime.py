import os
import tempfile
import unittest
from pathlib import Path

try:
    from .pcm_runtime import assert_no_pcm_copy, link_immutable_pcm
except ImportError:
    from pcm_runtime import assert_no_pcm_copy, link_immutable_pcm


class PcmRuntimeTests(unittest.TestCase):
    def test_links_preserve_canonical_identity_and_survive_target_delete(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            canonical = root / "distribution"
            runtime = root / "run"
            canonical.mkdir()
            (canonical / "bor-1.pcm").write_bytes(b"one")
            (canonical / "bor-2.pcm").write_bytes(b"two")
            linked = link_immutable_pcm(canonical, runtime)
            self.assertEqual([p.name for p in linked], ["bor-1.pcm", "bor-2.pcm"])
            assert_no_pcm_copy(canonical, runtime)
            if os.name == "nt":
                self.assertTrue(os.path.samefile(canonical / "bor-1.pcm", runtime / "bor-1.pcm"))
            for path in runtime.glob("bor-*.pcm"):
                path.unlink()
            self.assertEqual((canonical / "bor-1.pcm").read_bytes(), b"one")
            self.assertEqual((canonical / "bor-2.pcm").read_bytes(), b"two")


if __name__ == "__main__":
    unittest.main()
