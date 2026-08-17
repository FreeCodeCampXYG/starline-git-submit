#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth_probe import probe
from config_store import (  # noqa: E402
    connect, db_path, delete, get, list_profiles, lookup_project, merged, put, validate_document,
)
from inspect_repository import git, inspect, remote_host  # noqa: E402

EXPORT_MARKER = "starline-git-submit-export"
GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
VAGUE_COMMIT_TEXT = {"change", "changes", "fix", "update", "updates", "修改", "更新", "修复"}
VAGUE_RELEASE_TEXT = VAGUE_COMMIT_TEXT | {"release", "发布", "版本发布"}
SUPPORTED_LICENSES = {"MIT"}
HYGIENE_CONFIRMATION = "create-missing-governance-files"
ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets" / "github"


def out(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def repo_info(path: str) -> dict:
    return inspect(path)


def optional_repo_root(path: str) -> str | None:
    process = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"], text=True, capture_output=True)
    return process.stdout.strip() if process.returncode == 0 else None


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _project_context(repo: str) -> tuple[dict, str]:
    info = repo_info(repo)
    return info, info["project_key"]


def _read_import(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and payload.get("_meta", {}).get("marker") == EXPORT_MARKER:
        payload = payload.get("profile")
    validate_document(payload)
    return payload


def cmd_config(args) -> dict | list:
    repo_root = optional_repo_root(args.repo)
    if args.action == "init":
        con = connect(repo_root)
        con.close()
        return {"ok": True, "db": str(db_path(repo_root)), "schema_version": 1}
    if args.action == "list":
        return list_profiles(repo_root)
    identity = args.identity
    info = None
    if args.scope == "global":
        identity = "global"
    elif args.scope == "project":
        info, identity = _project_context(args.repo)
    if args.action == "show":
        if args.scope == "project":
            match = lookup_project(identity, info["remote_fingerprint"], info["repo_root"])
            return {"match": match, "effective_identity": identity}
        return {"profile": get(args.scope, identity, repo_root) or {}, "identity": identity}
    if args.action == "delete":
        return {"deleted": delete(args.scope, identity, repo_root)}
    if args.action == "export":
        destination = Path(args.file).expanduser().resolve()
        if repo_root and _inside(destination, Path(repo_root)):
            raise ValueError("config export destination must not be inside the Git repository")
        if args.scope == "project":
            match = lookup_project(identity, info["remote_fingerprint"], info["repo_root"])
            if match["status"] in {"mismatch", "ambiguous"}:
                raise ValueError(f"project profile export requires review: {match['status']}")
            profile = match.get("document") or {}
        else:
            profile = get(args.scope, identity, repo_root) or {}
        document = {
            "_meta": {
                "marker": EXPORT_MARKER,
                "sensitive": True,
                "commit_allowed": False,
                "notice": "Governed configuration export. Keep outside repositories and do not commit.",
            },
            "profile": profile,
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"exported": str(destination), "sensitive": True, "commit_allowed": False}
    document = _read_import(Path(args.file))
    if args.scope == "project":
        put("project", identity, document, repo_path_hint=info["repo_root"], remote_fp=info["remote_fingerprint"], repo_root=info["repo_root"])
    else:
        put(args.scope, identity, document, repo_root=repo_root)
    return {"imported": True, "scope": args.scope, "identity": identity}


def valid_branch(repo: str, branch: str) -> bool:
    return bool(branch) and subprocess.run(["git", "-C", repo, "check-ref-format", "--branch", branch], capture_output=True).returncode == 0


def valid_tag(repo: str, tag: str) -> bool:
    return bool(tag) and subprocess.run(["git", "-C", repo, "check-ref-format", f"refs/tags/{tag}"], capture_output=True).returncode == 0


def validate_commit_record(message: str | None, comment: str | None) -> list[str]:
    """校验可区分本次修改的提交主题与修改摘要。"""
    errors: list[str] = []
    normalized_message = (message or "").strip()
    normalized_comment = (comment or "").strip()
    if not normalized_message or "\n" in normalized_message or "\r" in normalized_message:
        errors.append("commit message must be a non-empty single-line summary")
    elif normalized_message.casefold() in VAGUE_COMMIT_TEXT:
        errors.append("commit message is too vague; summarize the concrete change")
    if not normalized_comment:
        errors.append("commit comment is required and must summarize what changed and why or its impact")
    elif normalized_comment.casefold() in VAGUE_COMMIT_TEXT:
        errors.append("commit comment is too vague; summarize what changed and why or its impact")
    return errors


def validate_release_text(value: str | None, label: str) -> list[str]:
    """校验 tag 与 GitHub Release 的可读变更说明。"""
    normalized = (value or "").strip()
    if not normalized:
        return [f"{label} is required and must explain the release changes"]
    if normalized.casefold() in VAGUE_RELEASE_TEXT or len(normalized) < 40:
        return [f"{label} is too vague; describe the main changes, compatibility or risk, and verification"]
    return []


def _write_new_file(destination: Path, content: str) -> None:
    """以 UTF-8 和 LF 写入新治理文件，拒绝覆盖已有文件。"""
    if destination.exists():
        raise ValueError(f"refusing to overwrite existing file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def mit_license(copyright_holder: str) -> str:
    """生成经明确确认后可写入仓库的 MIT 许可证文本。"""
    return f"""MIT License

Copyright (c) {date.today().year} {copyright_holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def hygiene_plan(args) -> dict:
    """生成许可证和 GitHub 协作文件的只读补齐计划。"""
    info = repo_info(args.repo)
    hygiene = info["repository_hygiene"]
    required_inputs = []
    if hygiene["license"]["status"] == "missing":
        required_inputs.extend(["--license MIT", "--copyright-holder <legal holder>", "exact license and holder confirmations"])
    return {
        "ok": True,
        "repository": info["repo_root"],
        "hygiene": hygiene,
        "required_inputs": required_inputs,
        "next_command": (
            "python scripts/git_submit.py hygiene-init --repo . --license MIT "
            "--confirm-license MIT --copyright-holder <legal-holder> "
            "--confirm-copyright-holder <legal-holder> "
            f"--confirm-hygiene {HYGIENE_CONFIRMATION}"
        ),
        "mutation_boundary": "plan-only; license selection and copyright holder are legal inputs that must be explicitly confirmed before missing files are written",
    }


def hygiene_init(args) -> dict:
    """在精确确认后仅创建缺失的许可证和 GitHub 协作模板。"""
    info = repo_info(args.repo)
    root = Path(info["repo_root"])
    hygiene = info["repository_hygiene"]
    errors: list[str] = []
    if args.confirm_hygiene != HYGIENE_CONFIRMATION:
        errors.append("exact governance-file confirmation is required")
    license_missing = hygiene["license"]["status"] == "missing"
    if license_missing:
        if args.license not in SUPPORTED_LICENSES:
            errors.append("a supported explicit license selection is required: MIT")
        if args.confirm_license != args.license:
            errors.append("exact license confirmation is required and must match")
        holder = (args.copyright_holder or "").strip()
        if not holder or "\n" in holder or "\r" in holder:
            errors.append("copyright holder must be a non-empty single line")
        if args.confirm_copyright_holder != args.copyright_holder:
            errors.append("exact copyright-holder confirmation is required and must match")
    if errors:
        return {"ok": False, "errors": errors, "hygiene": hygiene, "written": []}

    written: list[str] = []
    if license_missing:
        _write_new_file(root / "LICENSE", mit_license(args.copyright_holder.strip()))
        written.append("LICENSE")
    for relative in hygiene["github"]["missing_files"]:
        source = ASSET_ROOT / relative
        if not source.is_file():
            raise RuntimeError(f"missing packaged governance template: {relative}")
        _write_new_file(root / relative, source.read_text(encoding="utf-8"))
        written.append(relative)
    return {
        "ok": True,
        "written": written,
        "skipped_existing": hygiene["license"]["paths"] + hygiene["github"]["issue_templates"] + hygiene["github"]["pull_request_templates"],
        "next_step": "Review the new files, stage the intended files explicitly, then re-run inspect and plan. This command never stages, commits, pushes, or changes remote settings.",
    }


def valid_branch_name(branch: str) -> bool:
    return bool(branch) and subprocess.run(["git", "check-ref-format", "--branch", branch], capture_output=True).returncode == 0


def github_cli_ready() -> bool:
    if not shutil.which("gh"):
        return False
    return subprocess.run(
        ["gh", "auth", "status", "--hostname", "github.com"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    ).returncode == 0


def github_repo_status(owner: str, repo_name: str) -> str:
    """只读确认 GitHub 仓库是否存在；网络或权限不确定时拒绝猜测。"""
    process = subprocess.run(
        ["gh", "api", "--include", f"repos/{owner}/{repo_name}"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    output = f"{process.stdout}\n{process.stderr}"
    if process.returncode == 0:
        return "exists"
    if re.search(r"(?:HTTP/\S+\s+404|HTTP\s+404|\(HTTP 404\))", output, re.IGNORECASE):
        return "absent"
    return "unknown"


def repo_create_plan(args) -> dict:
    errors: list[str] = []
    if not GITHUB_OWNER_RE.fullmatch(args.owner or ""):
        errors.append("invalid GitHub owner")
    if not GITHUB_REPO_RE.fullmatch(args.repo_name or "") or args.repo_name in {".", ".."}:
        errors.append("invalid GitHub repository name")
    if not valid_branch_name(args.default_branch):
        errors.append("invalid default branch ref name")
    confirmations = (
        (args.confirm_owner, args.owner, "owner"),
        (args.confirm_repo_name, args.repo_name, "repository name"),
        (args.confirm_visibility, args.visibility, "visibility"),
        (args.confirm_default_branch, args.default_branch, "default branch"),
    )
    for confirmed, requested, label in confirmations:
        if confirmed != requested:
            errors.append(f"exact {label} confirmation is required and must match")
    if not github_cli_ready():
        errors.append("GitHub CLI is unavailable or not authenticated for github.com")

    status = "not-checked"
    if not errors:
        status = github_repo_status(args.owner, args.repo_name)
        if status == "exists":
            errors.append("target GitHub repository already exists; overwrite is forbidden")
        elif status != "absent":
            errors.append("target repository absence could not be verified; creation is blocked")

    phases = []
    if not errors:
        phases.append({
            "phase": "repository-create",
            "network": True,
            "executed": False,
            "argv": ["gh", "repo", "create", f"{args.owner}/{args.repo_name}", f"--{args.visibility}"],
        })
    return {
        "ok": not errors,
        "errors": errors,
        "provider": "github",
        "owner": args.owner,
        "repository": args.repo_name,
        "visibility": args.visibility,
        "requested_default_branch": args.default_branch,
        "repository_status": status,
        "phases": phases,
        "post_create_gate": (
            f"Creation does not authorize commit or push. Re-inspect, then make the first explicit push to "
            f"refs/heads/{args.default_branch}:refs/heads/{args.default_branch} and verify GitHub's default branch."
        ),
        "mutation_boundary": "plan-only; execute the single confirmed gh command visibly, then re-enter the normal submission workflow",
    }


def choose_remote(info: dict, requested: str | None, project_default: str | None, global_default: str | None) -> tuple[str | None, str]:
    if requested:
        return requested, "explicit"
    if info.get("upstream_remote"):
        return info["upstream_remote"], "upstream"
    for value, source in ((project_default, "project-profile"), (global_default, "global-profile")):
        if value:
            return value, source
    if len(info["remotes"]) == 1:
        return next(iter(info["remotes"])), "sole-remote"
    return None, "required"


def tracking_classification(info: dict, remote: str, push_branch: str) -> dict:
    tracking_ref = f"refs/remotes/{remote}/{push_branch}"
    # Use the current local remote-tracking ref only; the result remains stale until fetch.
    process = subprocess.run(["git", "-C", info["repo_root"], "rev-parse", "--verify", tracking_ref], text=True, capture_output=True)
    if process.returncode != 0:
        return {"state": "tracking-ref-missing", "tracking_ref": tracking_ref, "stale_until_fetch": True}
    counts = git(info["repo_root"], "rev-list", "--left-right", "--count", f"HEAD...{tracking_ref}").split()
    ahead, behind = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (None, None)
    state = "diverged" if ahead and behind else "ahead" if ahead else "behind" if behind else "equal"
    return {"state": state, "ahead": ahead, "behind": behind, "tracking_ref": tracking_ref, "stale_until_fetch": True}


def plan(args) -> dict:
    info = repo_info(args.repo)
    errors: list[str] = []
    if info["conflicts"]:
        errors.append("unresolved conflicts present")
    if info["staged_blockers"]:
        errors.append("staged governed database/export artifacts are forbidden")
    if info["detached"]:
        errors.append("detached HEAD cannot produce a branch push plan")
    hygiene = info.get("repository_hygiene")
    if hygiene and hygiene["license"]["status"] == "missing":
        errors.append("license file is missing; run hygiene-plan and hygiene-init, then re-inspect before submission")
    if hygiene and hygiene["github"]["applicable"] and hygiene["github"]["missing_files"]:
        errors.append("GitHub issue/PR governance files are missing; run hygiene-plan and hygiene-init, then re-inspect before submission")
    if args.branch != info["branch"] or args.confirm_branch != args.branch:
        errors.append("exact current branch confirmation does not match inspected branch")
    if not valid_branch(info["repo_root"], args.branch):
        errors.append("invalid current branch ref name")
    if args.confirm_push_branch != args.push_branch:
        errors.append("exact push-branch confirmation is required and must match")
    if not valid_branch(info["repo_root"], args.push_branch):
        errors.append("invalid push branch ref name")
    if args.tag:
        if args.confirm_tag != args.tag:
            errors.append("exact tag confirmation is required and must match")
        if not valid_tag(info["repo_root"], args.tag):
            errors.append("invalid tag ref name")
        errors.extend(validate_release_text(args.tag_message, "tag message"))
        if args.confirm_tag_message != args.tag_message:
            errors.append("exact tag-message confirmation is required and must match")
    elif args.confirm_tag:
        errors.append("confirm-tag supplied without tag")
    if info["staged"]:
        errors.extend(validate_commit_record(args.commit_message, args.commit_comment))
        if args.confirm_commit_message != args.commit_message:
            errors.append("exact commit-message confirmation is required and must match")
        if args.confirm_commit_comment != args.commit_comment:
            errors.append("exact commit-comment confirmation is required and must match")

    global_cfg = get("global", "global", info["repo_root"]) or {}
    project_match = lookup_project(info["project_key"], info["remote_fingerprint"], info["repo_root"])
    project_cfg = project_match.get("document") or {}
    remote, remote_source = choose_remote(info, args.remote, project_cfg.get("default_remote"), global_cfg.get("default_remote"))
    if not remote:
        errors.append("multiple or absent remotes require an explicit --remote or governed profile choice")
    elif remote not in info["remotes"]:
        errors.append("selected remote is unknown")
    host = remote_host(info["remotes"].get(remote, "")) if remote else "generic"
    cfg, project_match = merged(info["project_key"], info["remote_fingerprint"], host, info["repo_root"])
    if project_match["status"] in {"mismatch", "ambiguous"}:
        errors.append(f"project profile match requires review: {project_match['status']}")
    if cfg.get("allowed_hosts") and host not in cfg["allowed_hosts"]:
        errors.append("remote host is not allowed by policy")
    if cfg.get("require_clean_worktree", False) and not info["clean"]:
        errors.append("policy requires a clean worktree")
    if cfg.get("require_staged_changes", True) and not info["staged"]:
        errors.append("policy requires staged changes")
    if args.tag and not cfg.get("allow_tag_plan", False):
        errors.append("policy does not allow tag plans")
    if args.tag and cfg.get("provider") == "github":
        errors.extend(validate_release_text(args.release_notes, "GitHub release notes"))
        if args.confirm_release_notes != args.release_notes:
            errors.append("exact release-notes confirmation is required and must match")
        if not github_cli_ready():
            errors.append("GitHub CLI is unavailable or not authenticated for github.com release creation")
    protected = args.push_branch in cfg.get("protected_branches", [])
    if protected and not cfg.get("allow_protected_branch_push", False):
        errors.append("protected branch push is forbidden by policy")
    if protected and args.confirm_protected_branch != args.push_branch:
        errors.append("protected branch requires a separate exact confirmation")

    phases = []
    classification = None
    if not errors:
        classification = tracking_classification(info, remote, args.push_branch)
        phases.append({
            "phase": "line-ending-config",
            "network": False,
            "executed": False,
            "argv": ["git", "config", "core.autocrlf", "false"],
            "reason": "Keep skill and documentation diffs LF-stable on Windows before staging, committing, or pushing.",
        })
        phases.append({"phase": "refresh-preview", "network": True, "executed": False, "argv": ["git", "fetch", "--prune", "--no-tags", remote]})
        if info["staged"]:
            phases.append({
                "phase": "commit",
                "network": False,
                "executed": False,
                "argv": ["git", "commit", "-m", args.commit_message.strip(), "-m", args.commit_comment.strip()],
                "record": {"summary": args.commit_message.strip(), "comment": args.commit_comment.strip()},
            })
        branch_refspec = f"refs/heads/{args.branch}:refs/heads/{args.push_branch}"
        push_argv = ["git", "push"]
        if not info["upstream"] and args.branch == args.push_branch:
            push_argv.append("--set-upstream")
        push_argv.extend([remote, branch_refspec])
        phases.append({"phase": "branch-push", "network": True, "executed": False, "argv": push_argv})
        if args.tag:
            phases.append({"phase": "annotated-tag", "network": False, "executed": False, "argv": ["git", "tag", "-a", args.tag, "-m", args.tag_message.strip()], "record": {"tag": args.tag, "message": args.tag_message.strip()}})
            phases.append({"phase": "tag-push", "network": True, "executed": False, "argv": ["git", "push", remote, f"refs/tags/{args.tag}:refs/tags/{args.tag}"]})
            if cfg.get("provider") == "github":
                phases.append({"phase": "github-release", "network": True, "executed": False, "argv": ["gh", "release", "create", args.tag, "--title", f"Release {args.tag}", "--notes", args.release_notes.strip()], "record": {"tag": args.tag, "notes": args.release_notes.strip()}})
    return {
        "ok": not errors,
        "errors": errors,
        "repository": info,
        "project_profile_match": project_match,
        "selected_remote": remote,
        "remote_selection_source": remote_source,
        "provider": cfg.get("provider", "generic"),
        "effective_config": {key: value for key, value in cfg.items() if key != "proxy_env"},
        "tracking_classification": classification,
        "phases": phases,
        "mutation_boundary": "plan-only; fetch, commit, push, tag, and GitHub Release creation are previews for individually confirmed interactive execution",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    config_parser = sub.add_parser("config")
    config_sub = config_parser.add_subparsers(dest="action", required=True)
    for name in ("init", "list"):
        item = config_sub.add_parser(name)
        item.add_argument("--repo", default=".")
    for name in ("show", "delete", "export", "import"):
        item = config_sub.add_parser(name)
        item.add_argument("--scope", required=True, choices=["global", "host", "project"])
        item.add_argument("--identity", default="global")
        item.add_argument("--repo", default=".")
        item.add_argument("--file", required=name in ("export", "import"))
    for name in ("inspect", "auth-status"):
        item = sub.add_parser(name)
        item.add_argument("--repo", default=".")
    hygiene_plan_parser = sub.add_parser("hygiene-plan")
    hygiene_plan_parser.add_argument("--repo", default=".")
    hygiene_init_parser = sub.add_parser("hygiene-init")
    hygiene_init_parser.add_argument("--repo", default=".")
    hygiene_init_parser.add_argument("--license")
    hygiene_init_parser.add_argument("--confirm-license")
    hygiene_init_parser.add_argument("--copyright-holder")
    hygiene_init_parser.add_argument("--confirm-copyright-holder")
    hygiene_init_parser.add_argument("--confirm-hygiene", required=True)
    for name in ("plan", "run"):
        item = sub.add_parser(name)
        item.add_argument("--repo", default=".")
        item.add_argument("--branch", required=True)
        item.add_argument("--confirm-branch", required=True)
        item.add_argument("--push-branch", required=True)
        item.add_argument("--confirm-push-branch", required=True)
        item.add_argument("--confirm-protected-branch")
        item.add_argument("--commit-message")
        item.add_argument("--confirm-commit-message")
        item.add_argument("--commit-comment")
        item.add_argument("--confirm-commit-comment")
        item.add_argument("--tag")
        item.add_argument("--confirm-tag")
        item.add_argument("--tag-message")
        item.add_argument("--confirm-tag-message")
        item.add_argument("--release-notes")
        item.add_argument("--confirm-release-notes")
        item.add_argument("--remote")
    create_parser = sub.add_parser("repo-create-plan")
    create_parser.add_argument("--owner", required=True)
    create_parser.add_argument("--repo-name", required=True)
    create_parser.add_argument("--visibility", required=True, choices=["public", "private", "internal"])
    create_parser.add_argument("--default-branch", required=True)
    create_parser.add_argument("--confirm-owner", required=True)
    create_parser.add_argument("--confirm-repo-name", required=True)
    create_parser.add_argument("--confirm-visibility", required=True, choices=["public", "private", "internal"])
    create_parser.add_argument("--confirm-default-branch", required=True)
    args = parser.parse_args()
    try:
        if args.cmd == "config":
            result = cmd_config(args)
        elif args.cmd == "inspect":
            result = repo_info(args.repo)
        elif args.cmd == "auth-status":
            result = probe(repo_info(args.repo))
        elif args.cmd == "repo-create-plan":
            result = repo_create_plan(args)
        elif args.cmd == "hygiene-plan":
            result = hygiene_plan(args)
        elif args.cmd == "hygiene-init":
            result = hygiene_init(args)
        else:
            result = plan(args)
    except (ValueError, RuntimeError, json.JSONDecodeError, OSError) as exc:
        result = {"ok": False, "errors": [str(exc)]}
    out(result)
    return 0 if not isinstance(result, dict) or result.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
