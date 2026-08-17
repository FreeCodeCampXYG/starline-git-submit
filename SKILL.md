---
name: starline-git-submit
description: "Safely inspect Git delivery readiness, prepare missing LICENSE and GitHub issue/PR governance files after exact confirmation, plan confirmed commit/push/tag/Release actions, and create a new GitHub repository only after exact owner, name, visibility, and default-branch confirmation plus an absence check. Use for governed GitHub/GitLab/Gitee/generic submission, GitHub repository hygiene, release-tag documentation, or explicitly requested GitHub repository creation. Do not use for force pushes, destructive history rewrites, automatic stashing, repository overwrite, unreviewed license selection, automatic issue/PR closure or merge, non-GitHub repository creation, package publication, or opaque unattended mutation."
metadata:
  author: Starline
  version: "0.4.1"
---

# Starline Git Submit

Create a reviewable Git submission plan before any mutation. This skill separates inspection, policy resolution, authentication readiness, and human-confirmed execution.

## Hard boundaries

- Never force push, reset, clean, auto-stash, rewrite history, bypass hooks, or resolve conflicts automatically.
- Stop on unresolved conflicts.
- Never store secrets. Configuration may name environment variables but may not contain tokens, passwords, private keys, credential URLs, or proxy values.
- Confirm the exact branch separately from any tag. A branch confirmation never authorizes a tag.
- Every commit must carry a concrete one-line subject and a separate modification comment derived from the staged diff. The comment summarizes what changed and why or its impact; generic text such as `update`, `fix`, `修改`, or `更新` is not acceptable.
- Before submission, inspect for a root license file. If it is missing, stop the submission plan; `hygiene-init` may create only the explicitly confirmed, supported license template and never guesses a legal license or copyright holder.
- For GitHub remotes, inspect Issue and PR templates. Missing governance files stop submission until `hygiene-init` creates the packaged files after exact confirmation; it never overwrites existing templates, creates labels remotely, closes issues, comments, merges PRs, or stages files.
- A tag requires an exact, concrete annotated-tag message. A GitHub release also requires separately confirmed release notes; vague messages, placeholder text, and unexplained tags are rejected.
- On Windows or mixed-editor worktrees, set the target repository-local `core.autocrlf=false` before copying, staging, committing, fetching, or pushing. This is a required guard against CRLF-only diffs in skill and documentation packages.
- Treat `run` as plan generation. The interactive agent executes only the individually confirmed Git commands; the Python tool does not hide mutations.
- Repository creation is GitHub-only and requires exact owner, repository name, visibility, and default branch confirmations in the same request, a successful `gh` authentication check, and a read-only proof that the target does not exist. Existing or uncertain targets are hard stops.
- A repository-creation confirmation authorizes only the single visible `gh repo create OWNER/REPO --VISIBILITY` command. It never authorizes commit, remote replacement, push, Pages enablement, package publication, or deletion; re-inspect and confirm those phases separately.

## Workflow

1. For a new GitHub repository, run `repo-create-plan` with all four exact confirmations, review the single non-executed command, ask the user to confirm creation once more, execute only that command visibly, then verify the repository and return to normal inspection. Otherwise start with inspection.
2. Run `python scripts/git_submit.py inspect --repo <path>` and `hygiene-plan`. If the license or GitHub Issue/PR files are missing, ask for the MIT selection and copyright holder, run the exact-confirmed `hygiene-init`, review/stage the new files explicitly, and re-inspect. Read [GitHub governance](references/github-governance.md).
3. Resolve global, host, and stable project profiles from the external SQLite database. Read [Configuration](references/config.md).
4. Run `python scripts/git_submit.py auth-status --repo <path>` and report capability only; never print credential material.
5. Stop if the repository is conflicted, detached when a branch push is intended, hygiene is incomplete, or the requested branch differs from the inspected branch.
6. Before staging or reviewing a Windows worktree, run `git config core.autocrlf false` in the target repository, then use `git diff --check` and staged diffs to separate real content changes from line-ending noise.
7. Review `git diff --cached`, draft a concise commit subject and a modification comment covering the main changed areas plus purpose/impact, and show both to the user. Do not copy secrets, full diffs, generated file inventories, or unsupported claims into the comment.
8. Run `python scripts/git_submit.py plan --repo <path> --branch <current> --confirm-branch <current> --push-branch <target> --confirm-push-branch <target> --commit-message <subject> --confirm-commit-message <subject> --commit-comment <summary> --confirm-commit-comment <summary> [--tag <tag> --confirm-tag <tag> --tag-message <description> --confirm-tag-message <description> --release-notes <notes> --confirm-release-notes <notes>]`.
9. Review the non-executed line-ending config, fetch preview, commit subject/comment, tag and release record, stale tracking classification, explicit refspecs, and reasons. Ask the user to confirm each mutation phase.
10. Execute confirmed Git mutations directly and visibly, one phase at a time. Re-inspect before push/tag if repository state changed. For GitHub releases, execute `gh release create` only after tag push and a separate final confirmation.

Use `python scripts/git_submit.py run ...` only as an alias for governed plan generation. It never executes commit, push, or tag.

GitHub repository creation plan:

```text
python scripts/git_submit.py repo-create-plan --owner <owner> --repo-name <name> --visibility <public|private|internal> --default-branch <branch> --confirm-owner <owner> --confirm-repo-name <name> --confirm-visibility <visibility> --confirm-default-branch <branch>
```

## Configuration commands

```text
python scripts/git_submit.py config init
python scripts/git_submit.py config list
python scripts/git_submit.py config show --scope global
python scripts/git_submit.py config import --scope host --identity github.com --file profile.json
python scripts/git_submit.py config export --scope project --repo . --file profile.json
python scripts/git_submit.py config delete --scope host --identity github.com
```

Profiles are JSON documents stored in `governed-git-submit.db` under the platform user-data directory. Project matching keeps a path-specific key separate from a normalized-remote fingerprint and reports exact, moved, mismatch, or ambiguous states; no machine-specific path is embedded in this package.

## Decision rules

- HTTPS: report configured Git credential-helper presence; do not invoke credential fill or expose credentials.
- SSH: check agent availability with `ssh-add -l`; do not read key files.
- Optional provider CLI: check `gh auth status` or `glab auth status` when installed. Gitee and generic remotes rely on Git HTTPS/SSH readiness.
- GitHub creation uses `gh api --include repos/OWNER/REPO` only to classify the target as existing, confirmed absent, or unknown. Only a confirmed 404 permits planning; unknown network/auth responses block creation.
- Proxy profiles store environment-variable names only. Resolve their values only in the interactive execution environment and never serialize or print them.
- Remote selection order is explicit request, tracking remote, governed project/global profile, then a sole remote. Multiple otherwise-unselected remotes are a hard stop.
- Preview `git fetch --prune --no-tags <remote>` but never execute network operations. Classify current tracking refs as stale until the interactive caller executes the previewed fetch.
- Always include a local line-ending configuration phase before fetch/commit/push plans: `git config core.autocrlf false`. Treat this as repository-local hygiene, not a global Git preference change.
- Push with an explicit `refs/heads/<local>:refs/heads/<target>` refspec. Confirm the destination push branch independently; protected branches require policy allowance and separate exact confirmation.
- A tag plan requires an exact independent tag confirmation, a concrete annotated-tag message, and an exact `refs/tags/<tag>:refs/tags/<tag>` push refspec. GitHub tags additionally require concrete, exactly confirmed release notes and emit an explicit `gh release create` preview after tag push.
- Build the commit record from staged changes only. Use `git commit -m <subject> -m <comment>` so GitHub shows a scannable subject and a useful body; if unrelated changes cannot be summarized coherently, split them into separately confirmed commits instead of writing a vague comment.

## References

- [Workflow](references/workflow.md)
- [Configuration](references/config.md)
- [Authentication](references/auth.md)
- [Proxy handling](references/proxy.md)
- [Safety](references/safety.md)
- [GitHub governance](references/github-governance.md)
