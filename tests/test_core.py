import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config_store
import git_submit
from config_store import path_key, remote_fingerprint, validate_document
from inspect_repository import EXPORT_MARKER, inspect, normalize_remote, redact


class GovernedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ["STARLINE_GIT_SUBMIT_DATA_DIR"] = str(Path(self.temp.name) / "data")
        os.environ.pop("STARLINE_GIT_SUBMIT_DB_PATH", None)

    def tearDown(self):
        os.environ.pop("STARLINE_GIT_SUBMIT_DATA_DIR", None)
        os.environ.pop("STARLINE_GIT_SUBMIT_DB_PATH", None)
        self.temp.cleanup()

    def init_repo(self, name="repo", remote=None):
        repo = Path(self.temp.name) / name
        subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
        if remote:
            subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", remote], check=True)
        return repo

    def test_schema_tables_pragmas_and_audit(self):
        config_store.put("global", "global", {"default_remote": "origin"})
        con = sqlite3.connect(config_store.db_path())
        try:
            tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"schema_meta", "global_defaults", "host_profiles", "project_profiles", "audit_events"}.issubset(tables))
            self.assertEqual(con.execute("SELECT version FROM schema_meta").fetchone()[0], 1)
            self.assertGreaterEqual(con.execute("SELECT count(*) FROM audit_events").fetchone()[0], 1)
            self.assertEqual(con.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
        finally:
            con.close()

    def test_incompatible_schema_fails_loud(self):
        path = config_store.db_path()
        path.parent.mkdir(parents=True)
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE schema_meta(version INTEGER NOT NULL)")
        con.execute("INSERT INTO schema_meta VALUES(99)")
        con.commit()
        con.close()
        with self.assertRaisesRegex(RuntimeError, "incompatible config schema"):
            config_store.connect()

    def test_legacy_profiles_table_migrates(self):
        path = config_store.db_path()
        path.parent.mkdir(parents=True)
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE profiles(scope TEXT, identity TEXT, document TEXT)")
        con.execute("INSERT INTO profiles VALUES('global','global',?)", (json.dumps({"default_remote": "origin"}),))
        con.commit()
        con.close()
        migrated = config_store.connect()
        migrated.close()
        self.assertEqual(config_store.get("global", "global")["default_remote"], "origin")
        check = sqlite3.connect(path)
        try:
            self.assertIsNone(check.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'").fetchone())
        finally:
            check.close()

    def test_credential_reference_allowed_but_secrets_rejected(self):
        validate_document({"auth_method": "credential-helper", "credential_reference": "credential-helper:manager-core"})
        validate_document({"auth_method": "ssh-agent", "credential_reference": "ssh-agent:default"})
        with self.assertRaises(ValueError):
            validate_document({"token": "abc"})
        with self.assertRaises(ValueError):
            validate_document({"credential_reference": "https://user:secret@example.com"})
        with self.assertRaises(ValueError):
            validate_document({"proxy_env": {"https": "https://proxy"}})

    def test_db_path_guard_rejects_explicit_path_inside_repo(self):
        repo = self.init_repo()
        os.environ["STARLINE_GIT_SUBMIT_DB_PATH"] = str(repo / "config.db")
        with self.assertRaisesRegex(ValueError, "must not be inside"):
            config_store.db_path(repo)

    def test_remote_fingerprint_move_mismatch_and_ambiguous(self):
        fp = remote_fingerprint(["https://github.com/acme/repo"])
        key1 = path_key(str(Path(self.temp.name) / "a"), str(Path(self.temp.name) / "a/.git"))
        key2 = path_key(str(Path(self.temp.name) / "b"), str(Path(self.temp.name) / "b/.git"))
        config_store.put("project", key1, {"provider": "github"}, repo_path_hint="a", remote_fp=fp)
        moved = config_store.lookup_project(key2, fp)
        self.assertEqual(moved["status"], "moved")
        mismatch = config_store.lookup_project(key1, remote_fingerprint(["https://gitlab.com/other/repo"]))
        self.assertEqual(mismatch["status"], "mismatch")
        key3 = path_key(str(Path(self.temp.name) / "c"), str(Path(self.temp.name) / "c/.git"))
        config_store.put("project", key3, {"provider": "github"}, repo_path_hint="c", remote_fp=fp)
        key4 = path_key(str(Path(self.temp.name) / "d"), str(Path(self.temp.name) / "d/.git"))
        self.assertEqual(config_store.lookup_project(key4, fp)["status"], "ambiguous")

    def test_proxy_env_deep_merge(self):
        fp = remote_fingerprint(["https://github.com/acme/repo"])
        key = path_key(str(Path(self.temp.name) / "a"), str(Path(self.temp.name) / "a/.git"))
        config_store.put("global", "global", {"proxy_env": {"http": "HTTP_PROXY", "https": "HTTPS_PROXY"}})
        config_store.put("host", "github.com", {"proxy_env": {"no_proxy": "NO_PROXY"}})
        config_store.put("project", key, {"proxy_env": {"https": "PROJECT_HTTPS_PROXY"}}, repo_path_hint="a", remote_fp=fp)
        merged, match = config_store.merged(key, fp, "github.com")
        self.assertEqual(match["status"], "exact")
        self.assertEqual(merged["proxy_env"], {"http": "HTTP_PROXY", "https": "PROJECT_HTTPS_PROXY", "no_proxy": "NO_PROXY"})

    def test_url_redaction_and_normalization(self):
        self.assertEqual(redact("https://user:token@example.com/x.git"), "https://[REDACTED]@example.com/x.git")
        self.assertEqual(normalize_remote("https://user:token@GitHub.com/X/Y.git"), "https://github.com/X/Y")

    def test_export_outside_repo_marked_and_inside_rejected(self):
        repo = self.init_repo(remote="https://github.com/acme/repo.git")
        config_store.put("global", "global", {"default_remote": "origin"}, repo_root=str(repo))
        inside = type("A", (), {"action": "export", "scope": "global", "identity": "global", "repo": str(repo), "file": str(repo / "profile.json")})()
        with self.assertRaisesRegex(ValueError, "must not be inside"):
            git_submit.cmd_config(inside)
        outside_path = Path(self.temp.name) / "exports" / "profile.json"
        outside = type("A", (), {"action": "export", "scope": "global", "identity": "global", "repo": str(repo), "file": str(outside_path)})()
        result = git_submit.cmd_config(outside)
        payload = json.loads(outside_path.read_text())
        self.assertTrue(result["sensitive"])
        self.assertEqual(payload["_meta"]["marker"], EXPORT_MARKER)
        self.assertFalse(payload["_meta"]["commit_allowed"])

    def test_import_validates_wrapped_profile(self):
        export = Path(self.temp.name) / "profile.json"
        export.write_text(json.dumps({"_meta": {"marker": EXPORT_MARKER}, "profile": {"api_key": "bad"}}))
        args = type("A", (), {"action": "import", "scope": "global", "identity": "global", "repo": self.temp.name, "file": str(export)})()
        with self.assertRaises(ValueError):
            git_submit.cmd_config(args)

    def test_inspection_detects_staged_db_and_export_markers(self):
        repo = self.init_repo()
        (repo / "governed-git-submit.db-wal").write_bytes(b"x")
        (repo / "export.json").write_text(json.dumps({"_meta": {"marker": EXPORT_MARKER}}))
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        (repo / "export.json").write_text("{}")
        blockers = inspect(repo)["staged_blockers"]
        self.assertEqual(blockers, ["export.json", "governed-git-submit.db-wal"])

    def test_multiple_remotes_require_choice(self):
        info = self.fake_info(remotes={"origin": "https://github.com/a/b", "backup": "https://gitlab.com/a/b"})
        result = self.call_plan(info)
        self.assertFalse(result["ok"])
        self.assertTrue(any("require an explicit --remote" in error for error in result["errors"]))

    def test_plan_explicit_refspec_fetch_preview_and_described_github_release(self):
        info = self.fake_info()
        tag_message = "Add governed GitHub hygiene checks and require explicit release evidence for v1.2.3."
        release_notes = "## Changed\n- Add repository hygiene gates.\n- Require a reviewed release explanation before publishing.\n\n## Verification\n- Unit tests passed."
        config_store.put("global", "global", {"require_staged_changes": True, "allow_tag_plan": True, "provider": "github"})
        result = self.call_plan(
            info, tag="v1.2.3", confirm_tag="v1.2.3",
            tag_message=tag_message, confirm_tag_message=tag_message,
            release_notes=release_notes, confirm_release_notes=release_notes,
        )
        self.assertTrue(result["ok"], result["errors"])
        phases = {phase["phase"]: phase for phase in result["phases"]}
        self.assertEqual(phases["line-ending-config"]["argv"], ["git", "config", "core.autocrlf", "false"])
        self.assertFalse(phases["line-ending-config"]["executed"])
        self.assertEqual(phases["refresh-preview"]["argv"], ["git", "fetch", "--prune", "--no-tags", "origin"])
        self.assertFalse(phases["refresh-preview"]["executed"])
        self.assertEqual(
            phases["commit"]["argv"],
            ["git", "commit", "-m", "Add governed commit records", "-m", "Require a concrete summary and comment so GitHub history explains each change."],
        )
        self.assertEqual(phases["commit"]["record"]["summary"], "Add governed commit records")
        self.assertIn("refs/heads/main:refs/heads/main", phases["branch-push"]["argv"])
        self.assertEqual(phases["annotated-tag"]["argv"], ["git", "tag", "-a", "v1.2.3", "-m", tag_message])
        self.assertEqual(phases["tag-push"]["argv"][-1], "refs/tags/v1.2.3:refs/tags/v1.2.3")
        self.assertEqual(phases["github-release"]["argv"], ["gh", "release", "create", "v1.2.3", "--title", "Release v1.2.3", "--notes", release_notes])
        self.assertTrue(result["tracking_classification"]["stale_until_fetch"])

    def test_tag_requires_concrete_confirmed_description(self):
        config_store.put("global", "global", {"require_staged_changes": True, "allow_tag_plan": True})
        result = self.call_plan(
            self.fake_info(), tag="v1.2.3", confirm_tag="v1.2.3",
            tag_message="release", confirm_tag_message="release",
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("tag message is too vague" in error for error in result["errors"]))

    def test_hygiene_init_creates_only_missing_license_and_github_templates(self):
        repo = self.init_repo(remote="https://github.com/acme/repo.git")
        args = type("A", (), {
            "repo": str(repo), "license": "MIT", "confirm_license": "MIT",
            "copyright_holder": "Acme", "confirm_copyright_holder": "Acme",
            "confirm_hygiene": git_submit.HYGIENE_CONFIRMATION,
        })()
        result = git_submit.hygiene_init(args)
        self.assertTrue(result["ok"], result["errors"] if not result["ok"] else "")
        self.assertEqual(
            result["written"],
            ["LICENSE", ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/feature_request.yml", ".github/ISSUE_TEMPLATE/config.yml", ".github/PULL_REQUEST_TEMPLATE.md"],
        )
        self.assertIn("Copyright (c)", (repo / "LICENSE").read_text(encoding="utf-8"))
        self.assertIn("Bug report", (repo / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text(encoding="utf-8"))
        repeat = git_submit.hygiene_init(args)
        self.assertTrue(repeat["ok"])
        self.assertEqual(repeat["written"], [])

    def test_plan_blocks_missing_license_or_github_governance_files(self):
        info = self.fake_info()
        info["repository_hygiene"] = {
            "license": {"status": "missing", "paths": []},
            "github": {"applicable": True, "issue_templates": [], "pull_request_templates": [], "missing_files": [".github/PULL_REQUEST_TEMPLATE.md"]},
        }
        result = self.call_plan(info)
        self.assertFalse(result["ok"])
        self.assertTrue(any("license file is missing" in error for error in result["errors"]))
        self.assertTrue(any("governance files are missing" in error for error in result["errors"]))

    def test_invalid_ref_never_emits_commands(self):
        result = self.call_plan(self.fake_info(), push_branch="bad branch", confirm_push_branch="bad branch")
        self.assertFalse(result["ok"])
        self.assertEqual(result["phases"], [])

    def test_commit_record_requires_concrete_exact_summary_and_comment(self):
        vague = self.call_plan(
            self.fake_info(), commit_message="update", confirm_commit_message="update",
            commit_comment="修改", confirm_commit_comment="修改",
        )
        self.assertFalse(vague["ok"])
        self.assertTrue(any("too vague" in error for error in vague["errors"]))
        mismatch = self.call_plan(self.fake_info(), confirm_commit_comment="different")
        self.assertFalse(mismatch["ok"])
        self.assertTrue(any("commit-comment confirmation" in error for error in mismatch["errors"]))

    def test_push_branch_confirmation_and_protected_gate(self):
        info = self.fake_info()
        mismatch = self.call_plan(info, push_branch="release", confirm_push_branch="main")
        self.assertFalse(mismatch["ok"])
        config_store.put("global", "global", {"require_staged_changes": True, "protected_branches": ["main"]})
        blocked = self.call_plan(info)
        self.assertTrue(any("protected branch push is forbidden" in error for error in blocked["errors"]))
        config_store.put("global", "global", {"require_staged_changes": True, "protected_branches": ["main"], "allow_protected_branch_push": True})
        unconfirmed = self.call_plan(info)
        self.assertTrue(any("separate exact confirmation" in error for error in unconfirmed["errors"]))
        confirmed = self.call_plan(info, confirm_protected_branch="main")
        self.assertTrue(confirmed["ok"], confirmed["errors"])

    def test_conflict_and_stage_block_stop(self):
        info = self.fake_info()
        info["conflicts"] = ["UU f"]
        info["staged_blockers"] = ["governed-git-submit.db"]
        result = self.call_plan(info)
        self.assertFalse(result["ok"])
        self.assertEqual(result["phases"], [])

    def test_repo_create_plan_requires_four_exact_confirmations(self):
        args = self.create_args(confirm_visibility="private")
        result = self.call_create_plan(args, status="absent")
        self.assertFalse(result["ok"])
        self.assertEqual(result["phases"], [])
        self.assertTrue(any("visibility confirmation" in error for error in result["errors"]))

    def test_repo_create_plan_blocks_existing_or_unknown_target(self):
        existing = self.call_create_plan(self.create_args(), status="exists")
        self.assertFalse(existing["ok"])
        self.assertTrue(any("already exists" in error for error in existing["errors"]))
        unknown = self.call_create_plan(self.create_args(), status="unknown")
        self.assertFalse(unknown["ok"])
        self.assertTrue(any("could not be verified" in error for error in unknown["errors"]))

    def test_repo_create_plan_emits_single_visible_gh_command(self):
        result = self.call_create_plan(self.create_args(), status="absent")
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(len(result["phases"]), 1)
        self.assertEqual(
            result["phases"][0]["argv"],
            ["gh", "repo", "create", "FreeCodeCampXYG/ai-leadership-study-note", "--public"],
        )
        self.assertFalse(result["phases"][0]["executed"])
        self.assertIn("does not authorize commit or push", result["post_create_gate"])
        self.assertIn("refs/heads/main:refs/heads/main", result["post_create_gate"])

    def test_repo_create_plan_rejects_invalid_names_and_branch(self):
        args = self.create_args(owner="-bad", confirm_owner="-bad", default_branch="bad branch", confirm_default_branch="bad branch")
        result = self.call_create_plan(args, status="absent")
        self.assertFalse(result["ok"])
        self.assertEqual(result["phases"], [])
        self.assertTrue(any("invalid GitHub owner" in error for error in result["errors"]))
        self.assertTrue(any("invalid default branch" in error for error in result["errors"]))

    def fake_info(self, remotes=None):
        return {
            "repo_root": self.temp.name, "common_dir": str(Path(self.temp.name) / ".git"),
            "project_key": path_key(self.temp.name, str(Path(self.temp.name) / ".git")),
            "remote_fingerprint": remote_fingerprint(list((remotes or {"origin": "https://github.com/a/b"}).values())),
            "branch": "main", "detached": False, "upstream": None, "upstream_remote": None,
            "remotes": remotes or {"origin": "https://github.com/a/b"}, "status": ["M  f"],
            "conflicts": [], "clean": False, "staged": True, "unstaged": False, "untracked": False,
            "staged_blockers": [],
        }

    def call_plan(self, info, **overrides):
        defaults = {
            "repo": self.temp.name, "branch": "main", "confirm_branch": "main",
            "push_branch": "main", "confirm_push_branch": "main", "confirm_protected_branch": None,
            "tag": None, "confirm_tag": None, "tag_message": None, "confirm_tag_message": None,
            "release_notes": None, "confirm_release_notes": None, "remote": None,
            "commit_message": "Add governed commit records",
            "confirm_commit_message": "Add governed commit records",
            "commit_comment": "Require a concrete summary and comment so GitHub history explains each change.",
            "confirm_commit_comment": "Require a concrete summary and comment so GitHub history explains each change.",
        }
        defaults.update(overrides)
        old_info = git_submit.repo_info
        old_valid_branch = git_submit.valid_branch
        old_valid_tag = git_submit.valid_tag
        old_tracking = git_submit.tracking_classification
        old_github_ready = git_submit.github_cli_ready
        git_submit.repo_info = lambda path: info
        git_submit.valid_branch = lambda repo, branch: " " not in branch and bool(branch)
        git_submit.valid_tag = lambda repo, tag: " " not in tag and bool(tag)
        git_submit.tracking_classification = lambda info, remote, branch: {"state": "ahead", "stale_until_fetch": True}
        git_submit.github_cli_ready = lambda: True
        try:
            return git_submit.plan(type("Args", (), defaults)())
        finally:
            git_submit.repo_info = old_info
            git_submit.valid_branch = old_valid_branch
            git_submit.valid_tag = old_valid_tag
            git_submit.tracking_classification = old_tracking
            git_submit.github_cli_ready = old_github_ready

    def create_args(self, **overrides):
        defaults = {
            "owner": "FreeCodeCampXYG", "repo_name": "ai-leadership-study-note",
            "visibility": "public", "default_branch": "main",
            "confirm_owner": "FreeCodeCampXYG", "confirm_repo_name": "ai-leadership-study-note",
            "confirm_visibility": "public", "confirm_default_branch": "main",
        }
        defaults.update(overrides)
        return type("Args", (), defaults)()

    def call_create_plan(self, args, status):
        old_ready = git_submit.github_cli_ready
        old_status = git_submit.github_repo_status
        old_valid_branch = git_submit.valid_branch_name
        git_submit.github_cli_ready = lambda: True
        git_submit.github_repo_status = lambda owner, repo: status
        git_submit.valid_branch_name = lambda branch: " " not in branch and bool(branch)
        try:
            return git_submit.repo_create_plan(args)
        finally:
            git_submit.github_cli_ready = old_ready
            git_submit.github_repo_status = old_status
            git_submit.valid_branch_name = old_valid_branch


if __name__ == "__main__":
    unittest.main()
