#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from config_store import path_key, remote_fingerprint

BLOCKED_STAGE_NAMES = {"governed-git-submit.db", "governed-git-submit.db-wal", "governed-git-submit.db-shm"}
EXPORT_MARKER = "starline-git-submit-export"
LICENSE_NAMES = {"license", "license.md", "license.txt", "licence", "licence.md", "licence.txt", "copying", "copying.md", "copying.txt", "unlicense", "unlicense.txt"}
GITHUB_PR_TEMPLATE_PATHS = (
    ".github/PULL_REQUEST_TEMPLATE.md",
    "PULL_REQUEST_TEMPLATE.md",
    "docs/PULL_REQUEST_TEMPLATE.md",
)


def normalize_remote(url: str) -> str:
    value = re.sub(r"(://)([^/@\s]+)@", r"\1", url.strip())
    value = re.sub(r"^([^@/\s]+)@([^:/\s]+):", r"ssh://\2/", value)
    value = value.rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*://)([^/]+)(/.*)?$", value)
    if match:
        value = match.group(1).lower() + match.group(2).lower() + (match.group(3) or "")
    return value


def remote_host(url: str) -> str:
    match = re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://([^/]+)", normalize_remote(url))
    return match.group(1).split(":", 1)[0] if match else "generic"


def redact(url: str) -> str:
    return re.sub(r"(://)([^/@\s]+)@", r"\1[REDACTED]@", url)


def git(repo: str | Path, *args: str, check: bool = True) -> str:
    process = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and process.returncode:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip())
    return process.stdout.strip()


def _staged_blockers(root: Path) -> list[str]:
    blockers = []
    staged = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines()
    for relative in staged:
        path = root / relative
        if path.name in BLOCKED_STAGE_NAMES:
            blockers.append(relative)
            continue
        try:
            staged_content = subprocess.run(
                ["git", "-C", str(root), "show", f":{relative}"],
                capture_output=True,
            ).stdout
            if EXPORT_MARKER.encode("ascii") in staged_content:
                blockers.append(relative)
        except (OSError, RuntimeError):
            continue
    return sorted(set(blockers))


def repository_hygiene(root: Path, remotes: dict[str, str]) -> dict:
    """检查许可证与 GitHub Issue、PR 维护文件是否已就绪。"""
    license_paths = sorted(
        entry.name for entry in root.iterdir()
        if entry.is_file() and entry.name.casefold() in LICENSE_NAMES
    )
    is_github = any(remote_host(url) == "github.com" for url in remotes.values())
    issue_dir = root / ".github" / "ISSUE_TEMPLATE"
    issue_templates = []
    if issue_dir.is_dir():
        issue_templates = sorted(
            str(path.relative_to(root)).replace("\\", "/")
            for path in issue_dir.iterdir()
            if path.is_file() and path.name.casefold() != "config.yml"
        )
    pr_templates = sorted(
        relative for relative in GITHUB_PR_TEMPLATE_PATHS
        if (root / relative).is_file()
    )
    missing_files = []
    if is_github:
        if not issue_templates:
            missing_files.extend([
                ".github/ISSUE_TEMPLATE/bug_report.yml",
                ".github/ISSUE_TEMPLATE/feature_request.yml",
                ".github/ISSUE_TEMPLATE/config.yml",
            ])
        if not pr_templates:
            missing_files.append(".github/PULL_REQUEST_TEMPLATE.md")
    return {
        "license": {
            "status": "present" if license_paths else "missing",
            "paths": license_paths,
        },
        "github": {
            "applicable": is_github,
            "issue_templates": issue_templates,
            "pull_request_templates": pr_templates,
            "missing_files": missing_files,
        },
    }


def inspect(repo: str | Path) -> dict:
    repo = Path(repo).resolve()
    root = Path(git(repo, "rev-parse", "--show-toplevel"))
    common = Path(git(repo, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = (root / common).resolve()
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False) or None
    remotes = {}
    for line in git(root, "remote", "-v").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(fetch)":
            remotes[parts[0]] = normalize_remote(parts[1])
    status_lines = git(root, "status", "--porcelain=v1", "-b").splitlines()
    entries = [line for line in status_lines[1:] if line]
    conflicts = [line for line in entries if line[:2] in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}]
    upstream = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False) or None
    upstream_remote = upstream.split("/", 1)[0] if upstream and "/" in upstream else None
    return {
        "repo_root": str(root),
        "common_dir": str(common),
        "project_key": path_key(str(root), str(common)),
        "remote_fingerprint": remote_fingerprint(list(remotes.values())),
        "branch": branch,
        "detached": branch is None,
        "upstream": upstream,
        "upstream_remote": upstream_remote,
        "remotes": remotes,
        "status": entries,
        "conflicts": conflicts,
        "clean": not entries,
        "staged": any(line[0] not in {" ", "?"} for line in entries),
        "unstaged": any(len(line) > 1 and line[1] not in {" ", "?"} for line in entries),
        "untracked": any(line.startswith("??") for line in entries),
        "staged_blockers": _staged_blockers(root),
        "repository_hygiene": repository_hygiene(root, remotes),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    print(json.dumps(inspect(args.repo), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
