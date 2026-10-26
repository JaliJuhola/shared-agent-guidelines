#!/usr/bin/env python3
"""Mirror skills from the agent-guidelines server into a local skills folder.

Standard library only (Python 3.9+). Safe to run before every task or session.

    python sync_skills.py            update if the server has a newer version
    python sync_skills.py --check    compare versions only; never writes
    python sync_skills.py --json     machine-readable result on stdout (for orchestrators)

Environment:
    GUIDELINES_URL   default http://localhost:3333
    SKILLS_DIR       default .github/skills   (repo-level Copilot skills)

Exit codes:
    0  up to date, updated, or server unreachable (existing skills are kept)
    3  --check and a newer version exists
    1  unexpected error

Only skills listed in the manifest (.agent-guidelines.json) are ever replaced or
deleted, so your own skills in the same folder are left alone.
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_NAME = ".agent-guidelines.json"
TMP_PREFIX = ".agent-guidelines-tmp-"
SAFE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TIMEOUT_S = 3


def _read_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": None, "skills": []}


def _get(url: str, etag: str | None) -> tuple[int, dict | None] | None:
    """Return (status, json_body) or None if the server is unreachable."""
    req = urllib.request.Request(url, headers={"If-None-Match": f'"{etag}"'} if etag else {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return 304, None
        return e.code, None
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return None


def _safe_rel(p: str) -> str:
    """Reject paths that could escape the skill directory."""
    norm = posixpath.normpath(p)
    if norm.startswith(("/", "..")) or "\0" in norm or ":" in norm.split("/")[0]:
        raise ValueError(f"unsafe path in export: {p}")
    return norm


def sync(server: str, skills_dir: Path, check: bool) -> tuple[dict, int]:
    manifest_path = skills_dir / MANIFEST_NAME
    manifest = _read_manifest(manifest_path)
    current = manifest.get("version")
    shown = current or "(none)"

    if check:
        r = _get(f"{server}/version", current)
        if r is None:
            return {"status": "unreachable", "version": current, "message": f"server unreachable; local {shown}"}, 0
        status, body = r
        if status == 304:
            return {"status": "current", "version": current, "message": f"up to date @ {current}"}, 0
        if status != 200 or not body:
            return {"status": "error", "version": current, "message": f"version check failed (HTTP {status})"}, 1
        latest = body["version"]
        return {"status": "outdated", "version": current, "latest": latest,
                "message": f"newer version available: {shown} -> {latest}"}, 3

    r = _get(f"{server}/export", current)
    if r is None:
        return {"status": "unreachable", "version": current,
                "message": f"server unreachable; keeping existing skills @ {shown}"}, 0
    status, body = r
    if status == 304:
        return {"status": "current", "version": current, "message": f"skills up to date @ {current}"}, 0
    if status != 200 or not body:
        return {"status": "error", "version": current,
                "message": f"export failed (HTTP {status}); keeping existing skills"}, 0

    version = body["version"]
    skills = body["skills"]
    skills_dir.mkdir(parents=True, exist_ok=True)

    owned = {n for n in manifest.get("skills", []) if SAFE_NAME.match(n)}
    to_write, skipped = [], []
    for s in skills:
        if not SAFE_NAME.match(s["name"]):
            raise ValueError(f"unsafe skill name in export: {s['name']}")
        if (skills_dir / s["name"]).exists() and s["name"] not in owned:
            skipped.append(s["name"])  # never overwrite a skill we don't own
        else:
            to_write.append(s)

    # 1. Write everything to a temp dir first, so agents never see half-written skills
    tmp = Path(tempfile.mkdtemp(prefix=TMP_PREFIX, dir=skills_dir))
    try:
        for s in to_write:
            for rel, content in s["files"].items():
                target = tmp / s["name"] / _safe_rel(rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
        # 2. Remove previously synced skills (also removes skills deleted on the server)
        for name in owned:
            shutil.rmtree(skills_dir / name, ignore_errors=True)
        # 3. Move new ones in and record what we own
        for s in to_write:
            os.replace(tmp / s["name"], skills_dir / s["name"])
        manifest_path.write_text(
            json.dumps(
                {"version": version, "server": server,
                 "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "skills": [s["name"] for s in to_write]},
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    warn = f" (skipped, name taken by a local skill: {', '.join(skipped)})" if skipped else ""
    return {"status": "updated", "version": version, "previous": current, "skills": len(to_write),
            "skipped": skipped,
            "message": f"skills updated {shown} -> {version}: {len(to_write)} skills{warn}"}, 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only compare versions; never write")
    ap.add_argument("--json", action="store_true", help="print a JSON result")
    args = ap.parse_args(argv)

    server = os.environ.get("GUIDELINES_URL", "http://localhost:3333").rstrip("/")
    skills_dir = Path(os.environ.get("SKILLS_DIR", ".github/skills")).resolve()

    try:
        result, code = sync(server, skills_dir, args.check)
    except Exception as e:  # noqa: BLE001 - report any failure in the same output format
        result, code = {"status": "error", "message": f"sync failed: {e}"}, 1

    print(json.dumps(result) if args.json else result["message"])
    return code


if __name__ == "__main__":
    sys.exit(main())
