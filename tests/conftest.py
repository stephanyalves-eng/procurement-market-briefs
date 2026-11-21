import os, sys, shutil
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "pipeline"))


@pytest.fixture
def truth_copy(tmp_path, monkeypatch):
    """A private copy of data/synthetic and data/public, with pipeline/synthetic.py pointed at it, so a test can
    extend the truth without touching the repository."""
    import synthetic
    syn, pub = tmp_path / "synthetic", tmp_path / "public"
    shutil.copytree(os.path.join(ROOT, "data", "synthetic"), syn)
    shutil.copytree(os.path.join(ROOT, "data", "public"), pub)
    monkeypatch.setattr(synthetic, "SYN", str(syn))
    monkeypatch.setattr(synthetic, "TRUTH", str(syn / "_truth"))
    monkeypatch.setattr(synthetic, "PUB", str(pub))
    return tmp_path
