from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_required_files_exist():
    required = [
        ROOT / "README.md",
        ROOT / "Launch.bat",
        ROOT / "KICKSTARTER_URL.txt",
        ROOT / "copy" / "Kickstarter-Campaign-Copy.md",
        ROOT / "press" / "Press-Release.md",
        ROOT / "social" / "Launch-Posts.md",
        WEB / "index.html",
        WEB / "press.html",
        WEB / "social.html",
        WEB / "kickstarter.html",
        ROOT / "mobile" / "index.html",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    assert not missing, missing


def test_campaign_message():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert "REALITY. YOUR WAY." in html
    assert "Campaign preview" in html
    assert 'href="kickstarter.html"' in html
    assert 'href="https://www.kickstarter.com/"' not in html


def test_public_pages_do_not_send_supporters_to_kickstarter_home():
    for folder in (ROOT / "web", ROOT / "docs"):
        for page in folder.glob("*.html"):
            html = page.read_text(encoding="utf-8")
            assert 'href="https://www.kickstarter.com/"' not in html, page
            assert "https%3A%2F%2Fwww.kickstarter.com%2F" not in html, page


def test_no_equity_language():
    text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in ROOT.rglob("*")
        if p.suffix.lower() in {".html", ".md", ".txt"} and "assets" not in p.parts
    ).lower()
    # Exclusion language is required ("no investment return"). Fail only if we sell equity.
    forbidden = ["buy equity", "equity stake", "roi for backers", "loan interest"]
    hits = [w for w in forbidden if w in text]
    assert "no equity" in text or "excludes equity" in text
    assert not hits, hits


def test_assets_present():
    assets = list((ROOT / "assets").glob("*.png"))
    assert len(assets) >= 3
