#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess

from inspect_repository import remote_host

SCRIPT_INTERFACE = "internal-module"


def run(*args: str) -> dict:
    process = subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace")
    return {"available": process.returncode == 0, "returncode": process.returncode}


def probe(info: dict) -> dict:
    hosts = sorted({remote_host(url) for url in info.get("remotes", {}).values() if remote_host(url) != "generic"})
    result = {
        "hosts": hosts,
        "https_credential_helper": run("git", "config", "--get-all", "credential.helper") if shutil.which("git") else {"available": False},
        "ssh_agent": {"available": bool(os.environ.get("SSH_AUTH_SOCK"))},
    }
    if result["ssh_agent"]["available"] and shutil.which("ssh-add"):
        result["ssh_agent"].update(run("ssh-add", "-l"))
    for provider, command, default_host in (("github", "gh", "github.com"), ("gitlab", "glab", "gitlab.com")):
        status = {"installed": bool(shutil.which(command)), "available": False}
        if status["installed"] and default_host in hosts:
            status.update(run(command, "auth", "status"))
        result[f"{provider}_cli"] = status
    return result
