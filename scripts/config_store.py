#!/usr/bin/env python3
"""Governed external SQLite profile store. Python standard library only."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

SCRIPT_INTERFACE = "internal-module"
SCHEMA_VERSION = 1
DB_FILENAME = "governed-git-submit.db"
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
REFERENCE = re.compile(r"^(credential-helper|ssh-agent|gh|glab|env):[A-Za-z0-9_.-]+$")
HOST = re.compile(r"^[A-Za-z0-9.-]+$")
REMOTE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
FORBIDDEN_KEY = re.compile(r"^(token|password|passwd|secret|api[_-]?key|private[_-]?key|authorization|cookie|proxy_url)$", re.I)
SECRET_VALUE = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:ghp|glpat|gitee)_[A-Za-z0-9_-]{12,}|https?://[^/@\s]+@)", re.I)
ALLOWED_KEYS = {
    "default_remote", "allowed_hosts", "provider", "auth_method", "credential_reference",
    "require_clean_worktree", "require_staged_changes", "allow_tag_plan", "proxy_env",
    "protected_branches", "allow_protected_branch_push",
}
TABLES = {"global": "global_defaults", "host": "host_profiles", "project": "project_profiles"}


def data_dir() -> Path:
    override = os.environ.get("STARLINE_GIT_SUBMIT_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "starline-git-submit"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/starline-git-submit"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "starline-git-submit"


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def db_path(repo_root: str | Path | None = None) -> Path:
    explicit = os.environ.get("STARLINE_GIT_SUBMIT_DB_PATH")
    path = Path(explicit).expanduser() if explicit else data_dir() / DB_FILENAME
    if explicit and repo_root and _inside(path, Path(repo_root)):
        raise ValueError("explicit config database path must not be inside the Git repository")
    return path


def path_key(repo_root: str, common_dir: str) -> str:
    payload = "\n".join((os.path.normcase(str(Path(repo_root).resolve())), os.path.normcase(str(Path(common_dir).resolve()))))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def remote_fingerprint(remotes: list[str]) -> str | None:
    normalized = sorted(set(value.strip() for value in remotes if value.strip()))
    if not normalized:
        return None
    return hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest()[:32]


def stable_id(repo_root: str, common_dir: str, remotes: list[str]) -> str:
    """Backward-compatible name for the path-specific project key."""
    return path_key(repo_root, common_dir)


def validate_document(document: Any) -> None:
    if not isinstance(document, dict):
        raise ValueError("profile must be a JSON object")
    unknown = set(document) - ALLOWED_KEYS
    if unknown:
        raise ValueError("unknown profile fields: " + ", ".join(sorted(unknown)))
    for key, value in document.items():
        if FORBIDDEN_KEY.fullmatch(str(key)):
            raise ValueError(f"forbidden secret field: {key}")
        if isinstance(value, str) and SECRET_VALUE.search(value):
            raise ValueError(f"forbidden secret-like value in {key}")
    provider = document.get("provider")
    if provider not in (None, "github", "gitlab", "gitee", "generic"):
        raise ValueError("unsupported provider")
    auth_method = document.get("auth_method")
    if auth_method not in (None, "credential-helper", "ssh-agent", "gh", "glab"):
        raise ValueError("unsupported auth_method")
    reference = document.get("credential_reference")
    if reference is not None and (not isinstance(reference, str) or not REFERENCE.fullmatch(reference)):
        raise ValueError("credential_reference must be a non-secret governed reference")
    if "default_remote" in document and (not isinstance(document["default_remote"], str) or not REMOTE_NAME.fullmatch(document["default_remote"])):
        raise ValueError("invalid default_remote")
    hosts = document.get("allowed_hosts", [])
    if not isinstance(hosts, list) or any(not isinstance(host, str) or not HOST.fullmatch(host) for host in hosts):
        raise ValueError("allowed_hosts must contain host names")
    protected = document.get("protected_branches", [])
    if not isinstance(protected, list) or any(not isinstance(branch, str) or not branch for branch in protected):
        raise ValueError("protected_branches must contain branch names")
    for key in ("require_clean_worktree", "require_staged_changes", "allow_tag_plan", "allow_protected_branch_push"):
        if key in document and not isinstance(document[key], bool):
            raise ValueError(f"{key} must be boolean")
    proxy = document.get("proxy_env", {})
    if not isinstance(proxy, dict) or set(proxy) - {"http", "https", "no_proxy"}:
        raise ValueError("invalid proxy_env fields")
    for key, value in proxy.items():
        if not isinstance(value, str) or not ENV_NAME.fullmatch(value):
            raise ValueError(f"proxy_env.{key} must be an environment variable name")


def _initialize(con: sqlite3.Connection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS schema_meta(version INTEGER NOT NULL)")
    row = con.execute("SELECT version FROM schema_meta LIMIT 1").fetchone()
    if row and row[0] > SCHEMA_VERSION:
        raise RuntimeError(f"incompatible config schema version {row[0]}; supported version is {SCHEMA_VERSION}")
    legacy = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'").fetchone()
    con.executescript("""
      CREATE TABLE IF NOT EXISTS global_defaults(identity TEXT PRIMARY KEY CHECK(identity='global'), document TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS host_profiles(host TEXT PRIMARY KEY, document TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE IF NOT EXISTS project_profiles(path_key TEXT PRIMARY KEY, remote_fingerprint TEXT, repo_path_hint TEXT NOT NULL, document TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
      CREATE INDEX IF NOT EXISTS idx_project_remote_fingerprint ON project_profiles(remote_fingerprint);
      CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, scope TEXT, identity TEXT, detail TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)
    if row is None:
        con.execute("INSERT INTO schema_meta(version) VALUES(?)", (SCHEMA_VERSION,))
    elif row[0] < SCHEMA_VERSION:
        con.execute("UPDATE schema_meta SET version=?", (SCHEMA_VERSION,))
    if legacy:
        for scope, identity, document in con.execute("SELECT scope,identity,document FROM profiles"):
            if scope == "global":
                con.execute("INSERT OR IGNORE INTO global_defaults(identity,document) VALUES('global',?)", (document,))
            elif scope == "host":
                con.execute("INSERT OR IGNORE INTO host_profiles(host,document) VALUES(?,?)", (identity, document))
            elif scope == "project":
                con.execute("INSERT OR IGNORE INTO project_profiles(path_key,remote_fingerprint,repo_path_hint,document) VALUES(?,NULL,'legacy',?)", (identity, document))
        con.execute("DROP TABLE profiles")
        _audit(con, "schema_migration", None, None, {"from": "legacy", "to": SCHEMA_VERSION})
    con.commit()


def connect(repo_root: str | Path | None = None) -> sqlite3.Connection:
    path = db_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=5.0)
    con.execute("PRAGMA busy_timeout=5000")
    try:
        con.execute("PRAGMA journal_mode=WAL").fetchone()
    except sqlite3.DatabaseError:
        pass
    try:
        _initialize(con)
    except Exception:
        con.close()
        raise
    return con


def _audit(con: sqlite3.Connection, event: str, scope: str | None, identity: str | None, detail: dict[str, Any]) -> None:
    con.execute("INSERT INTO audit_events(event_type,scope,identity,detail) VALUES(?,?,?,?)", (event, scope, identity, json.dumps(detail, sort_keys=True)))


def put(scope: str, identity: str, document: dict[str, Any], *, repo_path_hint: str = "", remote_fp: str | None = None, repo_root: str | None = None) -> None:
    validate_document(document)
    raw = json.dumps(document, sort_keys=True, separators=(",", ":"))
    con = connect(repo_root)
    try:
        if scope == "global":
            con.execute("INSERT INTO global_defaults(identity,document) VALUES('global',?) ON CONFLICT(identity) DO UPDATE SET document=excluded.document,updated_at=CURRENT_TIMESTAMP", (raw,))
            identity = "global"
        elif scope == "host":
            con.execute("INSERT INTO host_profiles(host,document) VALUES(?,?) ON CONFLICT(host) DO UPDATE SET document=excluded.document,updated_at=CURRENT_TIMESTAMP", (identity.lower(), raw))
        elif scope == "project":
            con.execute("INSERT INTO project_profiles(path_key,remote_fingerprint,repo_path_hint,document) VALUES(?,?,?,?) ON CONFLICT(path_key) DO UPDATE SET remote_fingerprint=excluded.remote_fingerprint,repo_path_hint=excluded.repo_path_hint,document=excluded.document,updated_at=CURRENT_TIMESTAMP", (identity, remote_fp, repo_path_hint, raw))
        else:
            raise ValueError("invalid scope")
        _audit(con, "profile_put", scope, identity, {"keys": sorted(document)})
        con.commit()
    finally:
        con.close()


def get(scope: str, identity: str, repo_root: str | None = None) -> dict[str, Any] | None:
    con = connect(repo_root)
    try:
        if scope == "global":
            row = con.execute("SELECT document FROM global_defaults WHERE identity='global'").fetchone()
        elif scope == "host":
            row = con.execute("SELECT document FROM host_profiles WHERE host=?", (identity.lower(),)).fetchone()
        elif scope == "project":
            row = con.execute("SELECT document FROM project_profiles WHERE path_key=?", (identity,)).fetchone()
        else:
            raise ValueError("invalid scope")
        return json.loads(row[0]) if row else None
    finally:
        con.close()


def lookup_project(current_path_key: str, current_remote_fp: str | None, repo_root: str | None = None) -> dict[str, Any]:
    con = connect(repo_root)
    try:
        exact = con.execute("SELECT remote_fingerprint,repo_path_hint,document FROM project_profiles WHERE path_key=?", (current_path_key,)).fetchone()
        if exact:
            if exact[0] == current_remote_fp:
                return {"status": "exact", "document": json.loads(exact[2]), "source_path_key": current_path_key, "repo_path_hint": exact[1]}
            return {"status": "mismatch", "document": None, "source_path_key": current_path_key, "stored_remote_fingerprint": exact[0], "current_remote_fingerprint": current_remote_fp}
        if not current_remote_fp:
            return {"status": "none", "document": None}
        rows = con.execute("SELECT path_key,repo_path_hint,document FROM project_profiles WHERE remote_fingerprint=?", (current_remote_fp,)).fetchall()
        if len(rows) == 1:
            return {"status": "moved", "document": json.loads(rows[0][2]), "source_path_key": rows[0][0], "repo_path_hint": rows[0][1]}
        if len(rows) > 1:
            return {"status": "ambiguous", "document": None, "candidate_path_keys": [row[0] for row in rows]}
        return {"status": "none", "document": None}
    finally:
        con.close()


def delete(scope: str, identity: str, repo_root: str | None = None) -> int:
    con = connect(repo_root)
    try:
        table, column = {"global": ("global_defaults", "identity"), "host": ("host_profiles", "host"), "project": ("project_profiles", "path_key")}[scope]
        count = con.execute(f"DELETE FROM {table} WHERE {column}=?", ("global" if scope == "global" else identity,)).rowcount
        _audit(con, "profile_delete", scope, identity, {"deleted": count})
        con.commit()
        return count
    finally:
        con.close()


def list_profiles(repo_root: str | None = None) -> list[dict[str, Any]]:
    con = connect(repo_root)
    try:
        rows = []
        rows.extend({"scope": "global", "identity": row[0], "updated_at": row[1]} for row in con.execute("SELECT identity,updated_at FROM global_defaults"))
        rows.extend({"scope": "host", "identity": row[0], "updated_at": row[1]} for row in con.execute("SELECT host,updated_at FROM host_profiles"))
        rows.extend({"scope": "project", "identity": row[0], "remote_fingerprint": row[1], "updated_at": row[2]} for row in con.execute("SELECT path_key,remote_fingerprint,updated_at FROM project_profiles"))
        return sorted(rows, key=lambda row: (row["scope"], row["identity"]))
    finally:
        con.close()


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def merged(project_key: str, remote_fp: str | None, host: str, repo_root: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    result: dict[str, Any] = {}
    result = deep_merge(result, get("global", "global", repo_root) or {})
    result = deep_merge(result, get("host", host, repo_root) or {})
    match = lookup_project(project_key, remote_fp, repo_root)
    if match["status"] in {"exact", "moved"} and match.get("document"):
        result = deep_merge(result, match["document"])
    return result, match
