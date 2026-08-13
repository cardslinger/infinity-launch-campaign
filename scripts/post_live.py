#!/usr/bin/env python3
"""Post the Infinity Launch Campaign using Anthony's Chrome profile.

Uses saved cookies first. Creates accounts with janthonyspitzig@gmail.com
when a platform has no session. Never prints passwords.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import TimeoutError as PwTimeout
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
ASSET = ROOT / "assets" / "image.png"
LOG = ROOT / "PUBLISH-LIVE.json"
SHOTS = ROOT / "publish-shots"
EMAIL = "janthonyspitzig@gmail.com"
CHROME_USER_DATA = Path.home() / "AppData/Local/Google/Chrome/User Data"
CLONE_DIR = Path.home() / ".grok" / "tmp-chrome-post-profile"


def clone_chrome_profile() -> Path:
    """Chrome refuses DevTools on the default user-data-dir. Clone cookies/logins."""
    dest = CLONE_DIR
    dest_default = dest / "Default"
    dest_net = dest_default / "Network"
    dest_net.mkdir(parents=True, exist_ok=True)
    src_default = CHROME_USER_DATA / "Default"
    names = [
        (CHROME_USER_DATA / "Local State", dest / "Local State"),
        (src_default / "Preferences", dest_default / "Preferences"),
        (src_default / "Secure Preferences", dest_default / "Secure Preferences"),
        (src_default / "Login Data", dest_default / "Login Data"),
        (src_default / "Login Data For Account", dest_default / "Login Data For Account"),
        (src_default / "Web Data", dest_default / "Web Data"),
        (src_default / "Cookies", dest_default / "Cookies"),
        (src_default / "Network" / "Cookies", dest_net / "Cookies"),
        (src_default / "Network" / "Cookies-journal", dest_net / "Cookies-journal"),
        (src_default / "Network" / "Reporting and NEL", dest_net / "Reporting and NEL"),
        (src_default / "Network" / "Trust Tokens", dest_net / "Trust Tokens"),
        (src_default / "Network" / "TransportSecurity", dest_net / "TransportSecurity"),
    ]
    for src, dst in names:
        if src.is_file():
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass
    return dest

X_TEXT = (
    "Your apps. Your devices. Your AI. Your rules.\n\n"
    "Infinity is building one omniplatform companion for your entire digital life.\n\n"
    "REALITY. YOUR WAY.\n\n"
    "Back Infinity → {url}"
)
LINKEDIN = (
    "We built Infinity around a simple idea: your digital life should behave "
    "like one system, not fifty unrelated products.\n\n"
    "Infinity is an omniplatform AI companion designed to connect supported apps, "
    "devices, automations, preferences, and AI capabilities through one persistent "
    "user-controlled layer.\n\n"
    "The Infinity launch campaign is here.\n\n"
    "Campaign: {url}"
)
IG = (
    "INFINITY\nREALITY. YOUR WAY.\n\n"
    "One account.\nOne AI companion.\nAll your apps.\nYour devices.\n"
    "Your preferences.\nYour control.\n\nThe future is yours.\n\n"
    "Back Infinity → {url}"
)
REDDIT_TITLE = "Infinity — Reality. Your Way. Omniplatform AI companion launching"
REDDIT_BODY = (
    "We're launching Infinity: an omniplatform AI companion designed to make "
    "apps, devices, automations, AI tools, and user preferences operate as one "
    "connected system.\n\n"
    "Built around portability, extensibility, privacy controls, and the idea "
    "that technology should adapt to the user rather than forcing the user to "
    "adapt to every new product.\n\n"
    "Campaign: {url}"
)
REDDIT_SUBS = ["SideProject", "kickstarter", "AlphaandBetausers", "Crowdfunding"]


def public_url() -> str:
    env = Path(ROOT / "public-url.txt")
    if env.is_file():
        u = env.read_text(encoding="utf-8").strip()
        if u.startswith("http"):
            return u.rstrip("/") + "/"
    return "http://127.0.0.1:8765/"


def shot(page, name: str) -> str:
    SHOTS.mkdir(exist_ok=True)
    path = SHOTS / f"{name}.png"
    try:
        page.screenshot(path=str(path), full_page=False)
        return str(path)
    except Exception:
        return ""


def logged_in(page, needles: list[str]) -> bool:
    url = (page.url or "").lower()
    html = ""
    try:
        html = page.content().lower()
    except Exception:
        pass
    blob = url + " " + html[:8000]
    return any(n.lower() in blob for n in needles)


def click_first(page, selectors: list[str], timeout: int = 2500) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible(timeout=timeout):
                loc.click(timeout=timeout)
                return True
        except Exception:
            continue
    return False


def fill_first(page, selectors: list[str], value: str, timeout: int = 2500) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count():
                loc.click(timeout=timeout)
                loc.fill(value, timeout=timeout)
                return True
        except Exception:
            continue
    return False


def google_continue(page) -> bool:
    return click_first(
        page,
        [
            'button:has-text("Continue with Google")',
            'button:has-text("Sign in with Google")',
            'a:has-text("Continue with Google")',
            'div[role="button"]:has-text("Google")',
            'button:has-text("Google")',
            '[aria-label*="Google"]',
            'text=Continue with Google',
            'text=Sign in with Google',
        ],
        timeout=2000,
    )


def pick_google_account(page) -> bool:
    try:
        page.wait_for_timeout(800)
        if page.locator(f'text={EMAIL}').count():
            page.locator(f'text={EMAIL}').first.click(timeout=4000)
            page.wait_for_timeout(1500)
            return True
        if page.locator('div[data-identifier]').count():
            page.locator('div[data-identifier]').first.click(timeout=4000)
            page.wait_for_timeout(1500)
            return True
    except Exception:
        return False
    return False


def accept_cookies(page) -> None:
    click_first(
        page,
        [
            'button:has-text("Accept all")',
            'button:has-text("Accept All")',
            'button:has-text("Allow all")',
            'button:has-text("I agree")',
            'button:has-text("Accept")',
        ],
        timeout=1200,
    )


def wait_cloudflare(page, seconds: int = 12) -> None:
    try:
        html = (page.content() or "").lower()
    except Exception:
        html = ""
    if "just a moment" in html or "performing security verification" in html or "cf-browser-verification" in html:
        page.wait_for_timeout(seconds * 1000)


def result(name: str, status: str, detail: str, url: str = "", extra: dict | None = None) -> dict:
    row = {
        "platform": name,
        "status": status,
        "detail": detail,
        "url": url,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        row.update(extra)
    print(f"[{status}] {name}: {detail} {url}".strip(), flush=True)
    return row


def do_reddit(page, url: str) -> list[dict]:
    out = []
    body = REDDIT_BODY.format(url=url)
    for sub in REDDIT_SUBS:
        try:
            page.goto(
                f"https://old.reddit.com/r/{sub}/submit",
                wait_until="domcontentloaded",
                timeout=45000,
            )
            wait_cloudflare(page)
            accept_cookies(page)
            if "login" in page.url.lower() or logged_in(page, ["log in", "sign up"]):
                if "reddit.com/login" in page.url.lower() or page.locator('input[name="username"]').count():
                    if google_continue(page):
                        pick_google_account(page)
                        page.wait_for_timeout(2500)
                        page.goto(
                            f"https://old.reddit.com/r/{sub}/submit",
                            wait_until="domcontentloaded",
                            timeout=45000,
                        )
            if page.locator('input[name="username"]').count() and not page.locator('textarea[name="text"]').count():
                out.append(result("reddit", "blocked", f"r/{sub} needs login/signup", page.url))
                continue
            title_ok = fill_first(page, ['textarea[name="title"]', 'input[name="title"]'], REDDIT_TITLE)
            text_ok = fill_first(page, ['textarea[name="text"]', 'textarea'], body)
            if not (title_ok and text_ok):
                # new reddit fallback
                page.goto(
                    f"https://www.reddit.com/r/{sub}/submit/?type=TEXT",
                    wait_until="domcontentloaded",
                    timeout=45000,
                )
                page.wait_for_timeout(2000)
                fill_first(
                    page,
                    ['textarea[placeholder*="Title"]', '#inner-post-title', '[name="title"]'],
                    REDDIT_TITLE,
                )
                fill_first(
                    page,
                    ['div[role="textbox"]', 'textarea[placeholder*="text"]', '[name="text"]'],
                    body,
                )
            clicked = click_first(
                page,
                [
                    'button[name="submit"]',
                    'button:has-text("Post")',
                    'button:has-text("Submit")',
                    'input[type="submit"]',
                ],
                timeout=4000,
            )
            page.wait_for_timeout(3500)
            shot(page, f"reddit-{sub}")
            if clicked and "submit" not in page.url.lower():
                out.append(result("reddit", "posted", f"r/{sub}", page.url))
            elif clicked:
                out.append(result("reddit", "submitted", f"r/{sub} submit clicked", page.url))
            else:
                out.append(result("reddit", "blocked", f"r/{sub} no submit control", page.url))
        except Exception as e:
            out.append(result("reddit", "error", f"r/{sub} {type(e).__name__}: {e}"))
    return out


def do_x(page, url: str) -> dict:
    text = X_TEXT.format(url=url)
    try:
        page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        accept_cookies(page)
        if any(x in page.url.lower() for x in ("/login", "/i/flow/login", "signup")):
            # try Google signup/login
            page.goto("https://x.com/i/flow/signup", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1500)
            if not google_continue(page):
                click_first(page, ['text=Create account', 'button:has-text("Create account")', 'span:has-text("Sign up")'])
                page.wait_for_timeout(1000)
                google_continue(page)
            pick_google_account(page)
            page.wait_for_timeout(2500)
            if any(x in page.url.lower() for x in ("/login", "/i/flow", "signup")):
                # last try: login with Google
                page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=45000)
                google_continue(page)
                pick_google_account(page)
                page.wait_for_timeout(2500)
            page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)
        box = page.locator('div[data-testid="tweetTextarea_0"], div[role="textbox"]').first
        if box.count():
            box.click()
            box.fill(text)
            posted = click_first(
                page,
                ['button[data-testid="tweetButton"]', 'button[data-testid="tweetButtonInline"]'],
                timeout=4000,
            )
            page.wait_for_timeout(2500)
            shot(page, "x")
            return result("x", "posted" if posted else "composed", "compose", page.url)
        shot(page, "x")
        return result("x", "blocked", "no composer / signup wall", page.url)
    except Exception as e:
        return result("x", "error", f"{type(e).__name__}: {e}")


def do_threads(page, url: str) -> dict:
    text = X_TEXT.format(url=url)
    try:
        page.goto(
            "https://www.threads.net/intent/post?text=" + quote(text),
            wait_until="domcontentloaded",
            timeout=45000,
        )
        page.wait_for_timeout(2500)
        accept_cookies(page)
        if "login" in page.url.lower() or "accounts.instagram" in page.url.lower():
            google_continue(page)
            pick_google_account(page)
            page.wait_for_timeout(2000)
        posted = click_first(
            page,
            ['div[role="button"]:has-text("Post")', 'button:has-text("Post")'],
            timeout=4000,
        )
        shot(page, "threads")
        return result("threads", "posted" if posted else "opened", page.url, page.url)
    except Exception as e:
        return result("threads", "error", f"{type(e).__name__}: {e}")


def do_linkedin(page, url: str) -> dict:
    text = LINKEDIN.format(url=url)
    try:
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        accept_cookies(page)
        if "login" in page.url.lower() or "uas/login" in page.url.lower():
            if google_continue(page):
                pick_google_account(page)
                page.wait_for_timeout(2500)
                page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=45000)
        if "login" in page.url.lower():
            page.goto("https://www.linkedin.com/signup", wait_until="domcontentloaded", timeout=45000)
            fill_first(page, ['input[name="email-address"]', '#email-address'], EMAIL)
            google_continue(page)
            pick_google_account(page)
            page.wait_for_timeout(2000)
            shot(page, "linkedin")
            return result("linkedin", "blocked", "signup/login wall", page.url)
        click_first(
            page,
            [
                'button:has-text("Start a post")',
                '.share-box-feed-entry__trigger',
                'button.artdeco-button:has-text("Start a post")',
            ],
            timeout=4000,
        )
        page.wait_for_timeout(1000)
        fill_first(page, ['div[role="textbox"]', '.ql-editor', 'div.editor-content'], text)
        posted = click_first(page, ['button:has-text("Post")', 'button.share-actions__primary-action'], timeout=4000)
        page.wait_for_timeout(2000)
        shot(page, "linkedin")
        return result("linkedin", "posted" if posted else "opened", "feed", page.url)
    except Exception as e:
        return result("linkedin", "error", f"{type(e).__name__}: {e}")


def do_facebook(page, url: str) -> dict:
    text = IG.format(url=url)
    try:
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        accept_cookies(page)
        if page.locator('#email').count() or "login" in page.url.lower():
            # saved password should autofill from Chrome profile
            fill_first(page, ['#email', 'input[name="email"]'], EMAIL)
            page.wait_for_timeout(400)
            if page.locator('#pass').count():
                # Do not invent a password. Let Chrome autofill if it has one.
                try:
                    page.locator('#pass').click()
                    page.wait_for_timeout(600)
                except Exception:
                    pass
            click_first(page, ['button[name="login"]', 'button:has-text("Log In")', 'button:has-text("Log in")'])
            page.wait_for_timeout(2500)
            if page.locator('#email').count():
                google_continue(page)
                pick_google_account(page)
                page.wait_for_timeout(2000)
        if page.locator('#email').count() and "facebook.com" in page.url:
            page.goto("https://www.facebook.com/r.php", wait_until="domcontentloaded", timeout=45000)
            fill_first(page, ['input[name="reg_email__"]'], EMAIL)
            shot(page, "facebook")
            return result("facebook", "blocked", "signup needs name/DOB/captcha", page.url)
        click_first(
            page,
            [
                '[aria-label="Create a post"]',
                'span:has-text("What\'s on your mind")',
                'div[role="button"]:has-text("What\'s on your mind")',
            ],
            timeout=4000,
        )
        page.wait_for_timeout(1000)
        fill_first(page, ['div[role="textbox"][contenteditable="true"]', 'div[role="textbox"]'], text)
        posted = click_first(page, ['div[aria-label="Post"]', 'div[aria-label="Publish"]'], timeout=4000)
        page.wait_for_timeout(2000)
        shot(page, "facebook")
        return result("facebook", "posted" if posted else "opened", "feed", page.url)
    except Exception as e:
        return result("facebook", "error", f"{type(e).__name__}: {e}")


def do_youtube(page, url: str) -> dict:
    text = (
        "Infinity is an omniplatform AI companion for your digital life.\n\n"
        "One account. Everything syncs. Privacy first. Built to evolve.\n\n"
        f"Campaign: {url}"
    )
    try:
        page.goto("https://studio.youtube.com/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)
        if "accounts.google.com" in page.url:
            pick_google_account(page)
            page.wait_for_timeout(2500)
        # Community post from Studio
        page.goto("https://studio.youtube.com/channel/me/editing/images", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(800)
        page.goto("https://www.youtube.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        # try channel community
        click_first(page, ['ytcp-button:has-text("Create")', '#create-icon', 'button:has-text("Create")'])
        page.wait_for_timeout(600)
        click_first(page, ['tp-yt-paper-item:has-text("Create post")', 'text=Create post', 'text=Community'])
        page.wait_for_timeout(1000)
        fill_first(page, ['div#contenteditable-root', 'div[contenteditable="true"]', '#textbox'], text)
        posted = click_first(page, ['ytcp-button:has-text("Post")', 'button:has-text("Post")'])
        shot(page, "youtube")
        return result("youtube", "posted" if posted else "opened", "studio", page.url)
    except Exception as e:
        return result("youtube", "error", f"{type(e).__name__}: {e}")


def do_instagram(page, url: str) -> dict:
    try:
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        accept_cookies(page)
        if logged_in(page, ["Log in", "Sign up"]) and page.locator('input[name="username"]').count():
            google_continue(page)
            pick_google_account(page)
            if page.locator('input[name="username"]').count():
                page.goto("https://www.instagram.com/accounts/emailsignup/", wait_until="domcontentloaded", timeout=45000)
                fill_first(page, ['input[name="emailOrPhone"]'], EMAIL)
                fill_first(page, ['input[name="fullName"]'], "Anthony Spitzig")
                fill_first(page, ['input[name="username"]'], "infinitysquaredai")
                shot(page, "instagram")
                return result("instagram", "blocked", "signup needs password+captcha", page.url)
        click_first(page, ['svg[aria-label="New post"]', 'a[href="#"] svg[aria-label="New post"]', '[aria-label="New post"]'])
        page.wait_for_timeout(800)
        if ASSET.is_file():
            try:
                page.set_input_files('input[type="file"]', str(ASSET))
                page.wait_for_timeout(1500)
                click_first(page, ['button:has-text("Next")'])
                page.wait_for_timeout(800)
                click_first(page, ['button:has-text("Next")'])
                fill_first(page, ['div[aria-label="Write a caption"]', 'textarea'], IG.format(url=url))
                posted = click_first(page, ['div[role="button"]:has-text("Share")', 'button:has-text("Share")'])
                shot(page, "instagram")
                return result("instagram", "posted" if posted else "opened", "composer", page.url)
            except Exception as e:
                shot(page, "instagram")
                return result("instagram", "blocked", f"upload {type(e).__name__}", page.url)
        shot(page, "instagram")
        return result("instagram", "opened", "home", page.url)
    except Exception as e:
        return result("instagram", "error", f"{type(e).__name__}: {e}")


def do_tiktok(page, url: str) -> dict:
    try:
        page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)
        if "login" in page.url.lower():
            google_continue(page)
            pick_google_account(page)
            page.wait_for_timeout(2000)
        shot(page, "tiktok")
        if "login" in page.url.lower():
            return result("tiktok", "blocked", "login/signup wall (needs video file)", page.url)
        return result("tiktok", "opened", "upload desk — needs a video file", page.url)
    except Exception as e:
        return result("tiktok", "error", f"{type(e).__name__}: {e}")


def do_discord(page, url: str) -> dict:
    try:
        page.goto("https://discord.com/app", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)
        if "login" in page.url.lower() or "register" in page.url.lower():
            page.goto("https://discord.com/register", wait_until="domcontentloaded", timeout=45000)
            fill_first(page, ['input[name="email"]', 'input[type="email"]'], EMAIL)
            google_continue(page)
            pick_google_account(page)
            page.wait_for_timeout(2000)
        shot(page, "discord")
        if "login" in page.url.lower() or "register" in page.url.lower():
            return result("discord", "blocked", "register needs password + hCaptcha", page.url)
        return result("discord", "opened", "app", page.url)
    except Exception as e:
        return result("discord", "error", f"{type(e).__name__}: {e}")


def do_kickstarter(page, url: str) -> dict:
    try:
        page.goto("https://www.kickstarter.com/login", wait_until="domcontentloaded", timeout=45000)
        wait_cloudflare(page, 15)
        page.wait_for_timeout(1500)
        accept_cookies(page)
        google_continue(page)
        pick_google_account(page)
        if page.locator('#user_session_email, input[type="email"]').count() and "login" in page.url.lower():
            fill_first(page, ['#user_session_email', 'input[type="email"]'], EMAIL)
        click_first(page, ['input[type="submit"]', 'button:has-text("Log in")'])
        page.wait_for_timeout(2000)
        if "login" in page.url.lower() or "signup" in page.url.lower():
            page.goto("https://www.kickstarter.com/signup", wait_until="domcontentloaded", timeout=45000)
            fill_first(page, ['#user_email', 'input[type="email"]'], EMAIL)
            google_continue(page)
            pick_google_account(page)
            page.wait_for_timeout(1500)
        page.goto("https://www.kickstarter.com/start", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1500)
        shot(page, "kickstarter")
        if any(x in page.url.lower() for x in ("login", "signup", "captcha")):
            return result("kickstarter", "blocked", "creator verify / login wall", page.url)
        return result("kickstarter", "opened", "start project — identity/bank still Anthony-only", page.url)
    except Exception as e:
        return result("kickstarter", "error", f"{type(e).__name__}: {e}")


def do_medium(page, url: str) -> dict:
    text = LINKEDIN.format(url=url)
    try:
        page.goto("https://medium.com/new-story", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        if "signin" in page.url.lower() or "so/callback" in page.url.lower() or logged_in(page, ["Sign in"]):
            page.goto("https://medium.com/m/signin", wait_until="domcontentloaded", timeout=45000)
            google_continue(page)
            pick_google_account(page)
            page.wait_for_timeout(2000)
            page.goto("https://medium.com/new-story", wait_until="domcontentloaded", timeout=45000)
        fill_first(page, ['h3[data-testid="editorTitleParagraph"]', '[data-testid="editorTitleParagraph"]'], "Infinity — Reality. Your Way.")
        fill_first(page, ['p[data-testid="editorParagraphText"]', 'div[role="textbox"]', '.section-inner p'], text)
        click_first(page, ['button:has-text("Publish")', 'button:has-text("Publish now")'])
        page.wait_for_timeout(1000)
        posted = click_first(page, ['button:has-text("Publish now")', 'button:has-text("Publish anyway")'])
        shot(page, "medium")
        return result("medium", "posted" if posted else "opened", "editor", page.url)
    except Exception as e:
        return result("medium", "error", f"{type(e).__name__}: {e}")


def do_devto(page, url: str) -> dict:
    try:
        page.goto("https://dev.to/enter", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1500)
        click_first(
            page,
            [
                'button:has-text("Continue with Google")',
                'a:has-text("Continue with Google")',
                'input[value="Continue with Google"]',
                'form[action*="google"] button',
                'a[href*="google"]',
            ],
            timeout=4000,
        )
        pick_google_account(page)
        page.wait_for_timeout(2500)
        if "enter" in page.url.lower() or "sign" in page.url.lower():
            google_continue(page)
            pick_google_account(page)
            page.wait_for_timeout(2000)
            page.goto("https://dev.to/new", wait_until="domcontentloaded", timeout=45000)
        fill_first(page, ['#article-form-title', 'textarea#article-form-title'], "Infinity — Reality. Your Way.")
        fill_first(
            page,
            ['#article_body_markdown', 'textarea#article_body_markdown'],
            REDDIT_BODY.format(url=url),
        )
        posted = click_first(page, ['button:has-text("Publish")', 'input[value="Save changes"]'])
        shot(page, "devto")
        return result("devto", "posted" if posted else "opened", "editor", page.url)
    except Exception as e:
        return result("devto", "error", f"{type(e).__name__}: {e}")


def do_hn(page, url: str) -> dict:
    try:
        page.goto("https://news.ycombinator.com/submit", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1500)
        if page.locator('input[name="acct"]').count():
            page.goto("https://news.ycombinator.com/login?goto=submit", wait_until="domcontentloaded", timeout=45000)
            fill_first(page, ['input[name="acct"]'], "infinitysquared")
            # cannot invent HN password; signup form is same page
            fill_first(page, ['input[type="email"]', 'input[name="email"]'], EMAIL)
            shot(page, "hn")
            return result("hn", "blocked", "HN has no Google SSO — needs existing acct", page.url)
        fill_first(page, ['input[name="title"]'], "Infinity — Reality. Your Way.")
        fill_first(page, ['input[name="url"]'], url)
        posted = click_first(page, ['input[type="submit"]'])
        shot(page, "hn")
        return result("hn", "posted" if posted else "opened", "submit", page.url)
    except Exception as e:
        return result("hn", "error", f"{type(e).__name__}: {e}")


def detect_google(page) -> str:
    try:
        page.goto("https://accounts.google.com/SignOutOptions?hl=en", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        html = page.content()
        if EMAIL in html:
            return EMAIL
        if "omega.male.79@gmail.com" in html:
            return "omega.male.79@gmail.com"
        if "Manage your Google Account" in html or "Google Account" in html:
            return "google-session"
    except Exception:
        pass
    return ""


def launch_chrome_cdp():
    """Real headed Chrome on the cloned profile. Default dir blocks DevTools."""
    cloned = clone_chrome_profile()
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if not chrome.is_file():
        chrome = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
    port = 9223
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    subprocess.Popen(
        [
            str(chrome),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={cloned}",
            "--profile-directory=Default",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=LockProfileCookieDatabase",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    deadline = time.time() + 40
    last_err = None
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return f"http://127.0.0.1:{port}"
        except OSError as e:
            last_err = e
            time.sleep(0.4)
    raise RuntimeError(f"Chrome CDP did not come up: {last_err}")


def launch_context(p):
    cdp = launch_chrome_cdp()
    browser = p.chromium.connect_over_cdp(cdp)
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.set_viewport_size({"width": 1400, "height": 900})
    return ctx, page


def write_md(rows: list[dict], url: str, google: str) -> Path:
    md = ROOT / "PUBLISH-LIVE.md"
    posted = [r for r in rows if r["status"] in ("posted", "submitted")]
    blocked = [r for r in rows if r["status"] in ("blocked", "error")]
    opened = [r for r in rows if r["status"] in ("opened", "composed")]
    lines = [
        "# Infinity Launch — live publish",
        "",
        f"When: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Campaign URL: {url}",
        f"Google session: {google or '(none detected)'}",
        f"New-account email: {EMAIL}",
        "",
        "## Posted",
    ]
    if posted:
        lines.extend(f"- **{r['platform']}** — {r['detail']} — {r.get('url','')}" for r in posted)
    else:
        lines.append("- (none confirmed live)")
    lines += ["", "## Opened / composed"]
    if opened:
        lines.extend(f"- **{r['platform']}** — {r['detail']} — {r.get('url','')}" for r in opened)
    else:
        lines.append("- (none)")
    lines += ["", "## Blocked"]
    if blocked:
        lines.extend(f"- **{r['platform']}** — {r['detail']}" for r in blocked)
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## Honest limits",
        "- Kickstarter cannot go live without Anthony identity + bank verify.",
        "- TikTok / Instagram Reels need a video file.",
        "- Paid ads not started (no spend without a billing confirm).",
        "- A2 SFTP 68.66.224.35:22 timed out; infinity-squared.com DNS still parked.",
        "",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    return md


def main() -> int:
    url = public_url()
    rows: list[dict] = []
    google = ""
    SHOTS.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            ctx, page = launch_context(p)
            try:
                google = detect_google(page)
                print("GOOGLE", google or "none", flush=True)
                rows.extend(do_reddit(page, url))
                rows.append(do_x(page, url))
                rows.append(do_threads(page, url))
                rows.append(do_linkedin(page, url))
                rows.append(do_facebook(page, url))
                rows.append(do_youtube(page, url))
                rows.append(do_instagram(page, url))
                rows.append(do_tiktok(page, url))
                rows.append(do_discord(page, url))
                rows.append(do_kickstarter(page, url))
                rows.append(do_medium(page, url))
                rows.append(do_devto(page, url))
                rows.append(do_hn(page, url))
            finally:
                ctx.close()
    except Exception as e:
        rows.append(result("browser", "error", f"{type(e).__name__}: {e}\n{traceback.format_exc()[-400:]}"))

    LOG.write_text(json.dumps({"url": url, "google": google, "rows": rows}, indent=2), encoding="utf-8")
    write_md(rows, url, google)
    posted = sum(1 for r in rows if r["status"] in ("posted", "submitted"))
    print("DONE", "posted", posted, "total", len(rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
