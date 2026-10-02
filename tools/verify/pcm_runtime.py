"""Attach immutable MSU PCM sidecars without duplicating their bytes."""

from pathlib import Path
import os


def link_immutable_pcm(source_dir, target_dir, *, prefix="bor-"):
    """Hardlink canonical PCM sidecars into a disposable runtime directory.

    Copying the complete PCM set is intentionally forbidden: verifier output
    directories are disposable, while the canonical distribution media is the
    immutable source of truth.  A different filesystem is an infrastructure
    error, not permission to create another 176 GiB media tree.
    """
    source_dir = Path(source_dir).resolve()
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(source_dir.glob(f"{prefix}*.pcm"))
    if not sources:
        raise FileNotFoundError(f"no canonical PCM sidecars in {source_dir}")
    linked = []
    for source in sources:
        target = target_dir / source.name
        if target.exists():
            if not os.path.samefile(source, target):
                raise RuntimeError(f"refuse PCM replacement/copy: {target}")
            linked.append(target)
            continue
        try:
            os.link(source, target)
        except OSError as exc:
            raise RuntimeError(
                f"cannot hardlink immutable PCM {source} -> {target}; "
                "refusing a byte-copy fallback"
            ) from exc
        if not os.path.samefile(source, target):
            raise RuntimeError(f"PCM hardlink identity failed: {target}")
        linked.append(target)
    return linked


def assert_no_pcm_copy(source_dir, target_dir):
    """Verify every target PCM is the canonical inode, never a copied file."""
    source_dir = Path(source_dir).resolve()
    target_dir = Path(target_dir).resolve()
    sources = sorted(source_dir.glob("bor-*.pcm"))
    targets = sorted(target_dir.glob("bor-*.pcm"))
    if {p.name for p in sources} != {p.name for p in targets}:
        raise AssertionError("PCM sidecar name set differs from canonical media")
    for source in sources:
        if not os.path.samefile(source, target_dir / source.name):
            raise AssertionError(f"PCM is copied, not linked: {source.name}")
