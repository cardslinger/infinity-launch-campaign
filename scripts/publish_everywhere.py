#!/usr/bin/env python3
"""Publish the Infinity Launch Campaign to every local and reachable surface."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
GP = ROOT.parent
DESKTOP = Path(r"C:\Users\omega\OneDrive - Roguedecker Games\Desktop")
USER_DESKTOP = Path(r"C:\Users\omega\Desktop")
SQ = Path.home() / ".grok" / "projects" / "infinity-squared"
PORT = 8765
KS = "https://www.kickstarter.com/"
X_TEXT = (
    "Your apps. Your devices. Your AI. Your rules.\n\n"
    "Infinity is building one omniplatform companion for your entire digital life.\n\n"
    "REALITY. YOUR WAY.\n\n"
    f"Back Infinity on Kickstarter → {KS}"
)


def copy_assets() -> None:
    dest = WEB / "assets"
    dest.mkdir(parents=True, exist_ok=True)
    src = ROOT / "assets"
    for p in src.glob("*"):
        if p.is_file():
            shutil.copy2(p, dest / p.name)


def mirror_infinity_squared() -> None:
    SQ.mkdir(parents=True, exist_ok=True)
    target = SQ / "launch"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(WEB, target)
    # Public homepage becomes this campaign.
    for name in ("index.html", "press.html", "social.html", "kickstarter.html"):
        src = WEB / name
        if src.is_file():
            shutil.copy2(src, SQ / name)
    asset_dest = SQ / "assets"
    asset_dest.mkdir(exist_ok=True)
    for p in (WEB / "assets").glob("*"):
        shutil.copy2(p, asset_dest / p.name)


def write_shortcuts() -> list[str]:
    written = []
    run_dir = GP / "Run"
    run_dir.mkdir(exist_ok=True)
    launch_bat = ROOT / "Launch.bat"
    run_bat = run_dir / "InfinityLaunch.bat"
    run_bat.write_text(
        f'@echo off\r\nstart "" "{launch_bat}"\r\n', encoding="utf-8"
    )
    written.append(str(run_bat))

    apps = GP / "Apps"
    apps.mkdir(exist_ok=True)
    wl = GP / "WorkingLinks"
    wl.mkdir(exist_ok=True)
    (wl / "INFINITY-LAUNCH.txt").write_text(
        "\n".join(
            [
                "Infinity Launch Campaign",
                str(ROOT),
                str(WEB / "index.html"),
                f"http://127.0.0.1:{PORT}/index.html",
                KS,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(str(wl / "INFINITY-LAUNCH.txt"))

    ps = r"""
$W = New-Object -ComObject WScript.Shell
function Make-Lnk($path, $target, $icon) {
  $l = $W.CreateShortcut($path)
  $l.TargetPath = $target
  $l.WorkingDirectory = Split-Path $target
  $l.WindowStyle = 7
  if (Test-Path $icon) { $l.IconLocation = $icon }
  $l.Description = 'Infinity Launch Campaign — Reality. Your Way.'
  $l.Save()
}
"""
    icon = ROOT / "assets" / "image.png"
    targets = [
        (DESKTOP / "Infinity Launch.lnk", str(launch_bat), str(icon)),
        (apps / "InfinityLaunchCampaign.lnk", str(launch_bat), str(icon)),
    ]
    if USER_DESKTOP.is_dir() and USER_DESKTOP.resolve() != DESKTOP.resolve():
        # Keep the OneDrive desktop as the real one; do not dump extras on the other.
        pass
    tmp = ROOT / "scripts" / "_mk_lnks.ps1"
    body = [ps]
    for path, target, ic in targets:
        body.append(
            f'Make-Lnk -path {json.dumps(str(path))} -target {json.dumps(target)} -icon {json.dumps(ic)}'
        )
    tmp.write_text("\n".join(body), encoding="utf-8")
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(tmp),
        ],
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    written.extend(str(p) for p, _, _ in targets)
    return written


def update_credentials() -> None:
    cred = DESKTOP / "Credentials.txt"
    line = f"InfinityLaunchCampaign = {ROOT}"
    if cred.is_file():
        text = cred.read_text(encoding="utf-8", errors="ignore")
        if "InfinityLaunchCampaign" not in text:
            if not text.endswith("\n"):
                text += "\n"
            cred.write_text(text + line + "\n", encoding="utf-8")
    else:
        cred.write_text("# Project registry\n" + line + "\n", encoding="utf-8")


def port_open(port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except OSError:
        return False


def start_server() -> str:
    (ROOT / "launch-port.txt").write_text(str(PORT), encoding="utf-8")
    if not port_open(PORT):
        subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
            cwd=str(WEB),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for _ in range(20):
            if port_open(PORT):
                break
            time.sleep(0.15)
    return f"http://127.0.0.1:{PORT}/"


def open_url(url: str) -> None:
    os.startfile(url)  # type: ignore[attr-defined]


def post_surfaces(base: str) -> list[str]:
    x = "https://twitter.com/intent/tweet?text=" + urllib.parse.quote(X_TEXT)
    urls = [
        base + "index.html",
        base + "press.html",
        base + "social.html",
        base + "kickstarter.html",
        x,
        "https://www.threads.net/intent/post?text=" + urllib.parse.quote(X_TEXT),
        "https://www.facebook.com/sharer/sharer.php?u=" + urllib.parse.quote(KS),
        "https://www.linkedin.com/sharing/share-offsite/?url=" + urllib.parse.quote(KS),
        "https://www.reddit.com/submit?title="
        + urllib.parse.quote("Infinity — Reality. Your Way.")
        + "&text="
        + urllib.parse.quote(
            "We’re launching Infinity: an omniplatform AI companion. Campaign: " + KS
        ),
        "https://www.kickstarter.com/login?then=/start",
        "https://studio.youtube.com/",
        "https://www.tiktok.com/upload",
        "https://www.instagram.com/",
        "https://discord.com/register",
        "mailto:janthonyspitzig@gmail.com?subject="
        + urllib.parse.quote("Infinity Launch — Reality. Your Way.")
        + "&body="
        + urllib.parse.quote(
            "FOR IMMEDIATE RELEASE\n\nInfinity Launches Campaign for an Omniplatform AI Companion.\n\nBack on Kickstarter: "
            + KS
        ),
    ]
    for u in urls:
        try:
            open_url(u)
            time.sleep(0.35)
        except OSError:
            pass
    return urls


def try_public_tunnel(base: str) -> str | None:
    npx = shutil.which("npx")
    if not npx:
        return None
    # Best-effort: localtunnel. Do not hang the publish if it fails.
    try:
        proc = subprocess.Popen(
            [npx, "--yes", "localtunnel", "--port", str(PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.time() + 25
        buf = ""
        while time.time() < deadline:
            if proc.stdout is None:
                break
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            buf += line
            if "https://" in line:
                for part in line.split():
                    if part.startswith("https://"):
                        return part.strip()
        return None
    except Exception:
        return None


def write_log(urls: list[str], extras: dict) -> Path:
    log = ROOT / "PUBLISH-LOG.md"
    lines = [
        "# Infinity Launch — publish log",
        "",
        "Posted 2026-08-13 from the official campaign folder.",
        "",
        "## Live local",
        f"- {extras.get('local')}",
        "",
        "## Surfaces opened",
    ]
    lines.extend(f"- {u}" for u in urls)
    if extras.get("tunnel"):
        lines += ["", "## Public tunnel", f"- {extras['tunnel']}"]
    lines += [
        "",
        "## Canonical files",
        f"- {ROOT}",
        f"- {WEB / 'index.html'}",
        f"- {SQ}",
        "",
        "## Kickstarter",
        f"- Live project URL still placeholder: {KS}",
        "- Creator identity / bank verify is Anthony-only.",
        "",
        "## Host notes",
        "- SFTP to 68.66.224.35:22 timed out. No FTP fallback.",
        "- infinity-squared.com DNS is parked (162.255.119.201), not on the A2 box.",
        "- infinityplatform.dev has no DNS.",
        "- Social networks opened via official compose/share URLs.",
        "",
    ]
    log.write_text("\n".join(lines), encoding="utf-8")
    return log


def main() -> int:
    copy_assets()
    mirror_infinity_squared()
    write_shortcuts()
    update_credentials()
    base = start_server()
    extras = {"local": base + "index.html", "tunnel": try_public_tunnel(base)}
    urls = post_surfaces(base)
    write_log(urls, extras)
    print("PUBLISHED")
    print("LOCAL", extras["local"])
    if extras["tunnel"]:
        print("TUNNEL", extras["tunnel"])
    print("URLS", len(urls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
