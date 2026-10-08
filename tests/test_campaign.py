from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class LocalReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.urls.append(value)


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
    assert "Prototype today. Bigger vision ahead." in html
    assert "roadmap concepts, not shipped products" in html


def test_public_pages_do_not_send_supporters_to_kickstarter_home():
    for folder in (ROOT / "web", ROOT / "docs", ROOT / "mobile"):
        for page in folder.rglob("*.html"):
            html = page.read_text(encoding="utf-8")
            assert 'href="https://www.kickstarter.com/"' not in html, page
            assert "https%3A%2F%2Fwww.kickstarter.com%2F" not in html, page


def test_public_mobile_shell_links_resolve():
    shell = ROOT / "docs" / "mobile" / "index.html"
    html = shell.read_text(encoding="utf-8")
    for target in ("manifest.json", "../assets/image.png", "../kickstarter.html", "../index.html"):
        assert target in html
        assert (shell.parent / target).resolve().is_file(), target
    assert 'href="mobile/index.html"' in (ROOT / "docs" / "index.html").read_text(encoding="utf-8")


def test_cursor_reward_preview_is_honest_and_deployed():
    for folder in (ROOT / "web", ROOT / "docs"):
        page = folder / "cursor-preview.html"
        html = page.read_text(encoding="utf-8")
        index = (folder / "index.html").read_text(encoding="utf-8")
        assert 'href="cursor-preview.html"' in index
        assert 'id="sample"' in html
        assert 'id="particles"' in html
        assert 'prefers-reduced-motion' in html
        assert 'not a working system-wide cursor utility' in html


def test_campaign_concept_images_are_labeled():
    for folder in (ROOT / "web", ROOT / "docs"):
        html = (folder / "index.html").read_text(encoding="utf-8")
        assert html.count("<figcaption>") == 3
        assert html.count("AI-generated campaign concept artwork") == 2
        assert "not a screenshot of working software" in html
    for page in (ROOT / "mobile" / "index.html", ROOT / "docs" / "mobile" / "index.html"):
        html = page.read_text(encoding="utf-8")
        assert "A planned omniplatform AI companion" in html
        assert "Campaign concept artwork, not a screenshot of working software" in html


def test_social_drafts_distinguish_prototype_from_roadmap():
    for page in (ROOT / "social" / "Launch-Posts.md", ROOT / "web" / "social.html", ROOT / "docs" / "social.html"):
        text = page.read_text(encoding="utf-8")
        assert "Infinity Zero is the current desktop prototype" in text
        assert "We built Infinity" not in text
        assert "We’re launching Infinity" not in text
        assert "not a list of features already shipping" in text


def test_press_preview_states_current_verification_limits():
    for page in (ROOT / "press" / "Press-Release.md", ROOT / "web" / "press.html", ROOT / "docs" / "press.html"):
        text = page.read_text(encoding="utf-8")
        assert "current installed build completed a live local-model gateway chat test" in text
        assert "on-screen WebView composer and broader integrations still need end-to-end verification" in text
        assert "roadmap concepts, not shipping products" in text


def test_launch_checklist_keeps_publication_gates_explicit():
    text = (ROOT / "launch" / "Launch-Day-Checklist.md").read_text(encoding="utf-8")
    assert "on-screen composer and cross-app features still require demonstration" in text
    assert "Kickstarter project, social launch posts, and paid ads are **not** verified live" in text
    assert "cost every reward" in text


def test_publish_log_distinguishes_previews_from_live_launch():
    text = (ROOT / "PUBLISH-LOG.md").read_text(encoding="utf-8")
    assert "public campaign preview is deployed" in text
    assert "Kickstarter project is **not verified live**" in text
    assert "Opening a compose window is not a post" in text
    assert "custom-domain deployment is **not verified**" in text


def test_local_site_links_and_images_exist():
    for folder in (ROOT / "web", ROOT / "docs", ROOT / "mobile"):
        for page in folder.rglob("*.html"):
            parser = LocalReferences()
            parser.feed(page.read_text(encoding="utf-8"))
            for url in parser.urls:
                parts = urlsplit(url)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                target = page.parent / unquote(parts.path)
                assert target.is_file(), f"{page}: missing {url}"


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
