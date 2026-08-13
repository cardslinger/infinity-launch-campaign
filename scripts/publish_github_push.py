#!/usr/bin/env python3
"""Push the campaign to the public GitHub repo and enable Pages."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from publish_github import cred_read_windows, api  # type: ignore

REPO = "infinity-launch-campaign"
OWNER = "cardslinger"


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "git fail")[-400:])


def main() -> int:
    user, token = cred_read_windows("GitHub - https://api.github.com/cardslinger")
    user = user or OWNER
    remote = f"https://{user}:{token}@github.com/{OWNER}/{REPO}.git"

    if not (ROOT / ".git").exists():
        run(["git", "init", "-b", "main"], ROOT)
        run(["git", "config", "user.name", "cardslinger"], ROOT)
        run(["git", "config", "user.email", "omega.male.79@gmail.com"], ROOT)

    gitignore = ROOT / ".gitignore"
    if not gitignore.is_file():
        gitignore.write_text(
            "\n".join(
                [
                    ".pytest_cache/",
                    "__pycache__/",
                    "*.pyc",
                    "launch-port.txt",
                    "public-url.txt",
                    "GITHUB-PUBLISH.json",
                    "PUBLISH-LIVE.json",
                    "publish-shots/",
                    ".git-credentials",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    run(["git", "add", "-A"], ROOT)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=str(ROOT)
    )
    if staged.returncode != 0:
        run(["git", "commit", "-m", "Infinity Launch Campaign — Reality. Your Way."], ROOT)

    # rewrite remote without storing token in config permanently
    subprocess.run(["git", "remote", "remove", "origin"], cwd=str(ROOT), capture_output=True)
    run(["git", "remote", "add", "origin", f"https://github.com/{OWNER}/{REPO}.git"], ROOT)
    push = subprocess.run(
        ["git", "push", "-u", remote, "main"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    print("PUSH_MAIN", push.returncode, flush=True)
    if push.returncode != 0:
        print((push.stderr or push.stdout)[-300:], flush=True)
        return 1

    # GitHub Pages from /web
    status, body = api(
        token,
        "POST",
        f"https://api.github.com/repos/{OWNER}/{REPO}/pages",
        {"source": {"branch": "main", "path": "/web"}},
    )
    if status == 409:
        status, body = api(
            token,
            "PUT",
            f"https://api.github.com/repos/{OWNER}/{REPO}/pages",
            {"source": {"branch": "main", "path": "/web"}},
        )
    pages_url = ""
    if isinstance(body, dict):
        pages_url = body.get("html_url") or ""
    if not pages_url:
        pages_url = f"https://{OWNER}.github.io/{REPO}/"
    print("PAGES", status, pages_url, flush=True)
    out = ROOT / "GITHUB-PUBLISH.json"
    prev = {}
    if out.is_file():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    prev.update(
        {
            "pushed": push.returncode == 0,
            "pages_status": status,
            "pages_url": pages_url,
            "repo_url": f"https://github.com/{OWNER}/{REPO}",
        }
    )
    out.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    print("OK", pages_url, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
