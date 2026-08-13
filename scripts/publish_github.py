#!/usr/bin/env python3
"""Publish the campaign as a public GitHub gist using saved git credentials.

Never prints the secret.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUT = ROOT / "GITHUB-PUBLISH.json"


def cred_read_windows(target: str) -> tuple[str, str]:
    import ctypes
    from ctypes import wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    cred_ptr = ctypes.POINTER(CREDENTIAL)()
    ok = adv.CredReadW(target, 1, 0, ctypes.byref(cred_ptr))
    if not ok:
        raise RuntimeError(f"CredRead failed for {target} err={ctypes.get_last_error()}")
    try:
        cred = cred_ptr.contents
        user = cred.UserName or ""
        n = cred.CredentialBlobSize
        blob = ctypes.string_at(cred.CredentialBlob, n)
        secret = blob.decode("utf-8", errors="strict").rstrip("\x00")
        return user, secret
    finally:
        adv.CredFree(cred_ptr)


def git_cred() -> tuple[str, str]:
    targets = [
        "GitHub - https://api.github.com/cardslinger",
        "git:https://github.com",
        "gh:github.com",
        "LegacyGeneric:target=GitHub - https://api.github.com/cardslinger",
    ]
    last = None
    for t in targets:
        try:
            user, secret = cred_read_windows(t)
            if secret:
                return user or "cardslinger", secret
        except Exception as e:
            last = e
    raise RuntimeError(f"no github cred: {last}")


def api(token: str, method: str, url: str, body: dict | None = None) -> tuple[int, dict | list | str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "InfinityLaunchCampaign",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed: dict | list | str
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = raw
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = raw
        return e.code, parsed


def files_for_gist() -> dict:
    files = {}
    for rel in ("index.html", "press.html", "social.html", "kickstarter.html"):
        p = WEB / rel
        if p.is_file():
            files[rel] = {"content": p.read_text(encoding="utf-8", errors="replace")}
    readme = ROOT / "README.md"
    posts = ROOT / "social" / "Launch-Posts.md"
    press = ROOT / "press" / "Press-Release.md"
    for p in (readme, posts, press):
        if p.is_file():
            files[p.name] = {"content": p.read_text(encoding="utf-8", errors="replace")}
    return files


def main() -> int:
    try:
        user, token = git_cred()
    except Exception as e:
        OUT.write_text(json.dumps({"ok": False, "error": str(e)}), encoding="utf-8")
        print("CRED_FAIL", type(e).__name__, flush=True)
        return 1

    me_status, me = api(token, "GET", "https://api.github.com/user")
    login = me.get("login") if isinstance(me, dict) else None
    print("AUTH", me_status, login or "no-login", flush=True)
    if me_status >= 400:
        OUT.write_text(
            json.dumps({"ok": False, "auth_status": me_status, "detail": "auth failed"}),
            encoding="utf-8",
        )
        return 1

    gist_body = {
        "description": "Infinity Launch Campaign — Reality. Your Way.",
        "public": True,
        "files": files_for_gist(),
    }
    gs, gist = api(token, "POST", "https://api.github.com/gists", gist_body)
    gist_url = gist.get("html_url") if isinstance(gist, dict) else None
    print("GIST", gs, gist_url or "no-url", flush=True)

    repo_name = "infinity-launch-campaign"
    rs, repo = api(
        token,
        "POST",
        "https://api.github.com/user/repos",
        {
            "name": repo_name,
            "description": "Infinity Launch Campaign — Reality. Your Way.",
            "homepage": "https://orange-lights-clap.loca.lt/",
            "private": False,
            "has_issues": False,
            "auto_init": False,
        },
    )
    repo_url = repo.get("html_url") if isinstance(repo, dict) else None
    print("REPO", rs, repo_url or (repo.get("message") if isinstance(repo, dict) else "no-url"), flush=True)

    OUT.write_text(
        json.dumps(
            {
                "ok": gs < 300 or rs < 300,
                "user": login or user,
                "gist_status": gs,
                "gist_url": gist_url,
                "repo_status": rs,
                "repo_url": repo_url,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0 if (gs < 300 or rs < 300) else 2


if __name__ == "__main__":
    raise SystemExit(main())
