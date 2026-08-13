from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "post_live.py"


def _load():
    spec = importlib.util.spec_from_file_location("post_live", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_script_exists():
    assert SCRIPT.is_file()


def test_copy_has_placeholder():
    mod = _load()
    assert "{url}" in mod.X_TEXT
    assert "{url}" in mod.REDDIT_BODY
    assert "janthonyspitzig@gmail.com" == mod.EMAIL
    assert len(mod.REDDIT_SUBS) >= 3


def test_public_url_file(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    (tmp_path / "public-url.txt").write_text("https://example.test/\n", encoding="utf-8")
    assert mod.public_url() == "https://example.test/"
