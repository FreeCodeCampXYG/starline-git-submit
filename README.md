# Starline Git Submit

A local governed skill for safely creating a new GitHub repository when explicitly confirmed, or preparing an existing repository for a documented Git delivery. It checks for a license, supplies missing GitHub Issue/PR templates only after exact confirmation, and requires explanatory annotated tags and GitHub Release notes. It keeps configuration outside the skill directory in a platform user-data SQLite database and never stores credentials.

## What it does

- resolves JSON policy profiles in `global -> host -> project` order
- derives a path-specific project key and a separate normalized-remote fingerprint, reporting moved/mismatch/ambiguous matches
- inspects branch, upstream, staged/unstaged/untracked files, conflicts, and remotes
- redacts credentials embedded in remote URLs
- probes HTTPS credential-helper, SSH agent, and optional `gh`/`glab` readiness
- generates reviewable commands with exact branch confirmation and separate tag confirmation
- requires each commit to include a concrete subject and a staged-diff-derived modification comment
- stops submission when a root license file is missing, then writes only an explicitly confirmed MIT template with an explicitly confirmed copyright holder
- for GitHub remotes, creates missing Issue forms and a PR template without replacing project-maintained templates
- requires a concrete annotated-tag message; GitHub release plans also require separately confirmed release notes and preview `gh release create`
- plans GitHub repository creation only after exact owner/name/visibility/default-branch confirmation and a verified absence check

## What it does not do

It does not force push, reset, clean, auto-stash, resolve conflicts, overwrite repositories or governance files, guess a legal license, create repositories outside GitHub, publish packages, or execute opaque Git mutations. It does not automatically label, comment on, close, or merge an Issue/PR. Creation never includes source attachment or push, and does not authorize later Git operations. `run` deliberately returns the same governed action plan as `plan`; the interactive agent must execute confirmed mutations visibly.

## Requirements

- [ ] Python 3.9+ standard library: `python --version`
- [ ] Git available on `PATH`: `git --version`
- [ ] Optional: `ssh-add`, `gh`, or `glab` for richer readiness probes

## Quick start

```bash
python scripts/git_submit.py config init
python scripts/git_submit.py repo-create-plan --owner acme --repo-name demo --visibility private --default-branch main --confirm-owner acme --confirm-repo-name demo --confirm-visibility private --confirm-default-branch main
python scripts/git_submit.py inspect --repo .
python scripts/git_submit.py auth-status --repo .
python scripts/git_submit.py plan --repo . --branch my-branch --confirm-branch my-branch --push-branch my-branch --confirm-push-branch my-branch --commit-message "Add payment validation" --confirm-commit-message "Add payment validation" --commit-comment "Validate callback signatures and document rejected-request behavior." --confirm-commit-comment "Validate callback signatures and document rejected-request behavior."
```

Before the first submission, inspect and add missing governance files. A license choice is a legal decision, so the skill only supports exact-confirmed input and never guesses one:

```bash
python scripts/git_submit.py hygiene-plan --repo .
python scripts/git_submit.py hygiene-init --repo . --license MIT --confirm-license MIT --copyright-holder "Acme" --confirm-copyright-holder "Acme" --confirm-hygiene create-missing-governance-files
git diff --check
git add LICENSE .github
python scripts/git_submit.py inspect --repo .
```

`hygiene-init` creates only missing files, never stages them, and does not replace a repository's existing license or templates. For a GitHub remote it adds a bug report form, feature request form, Issue configuration, and PR template. It intentionally does not create, change, or close remote Issues/PRs.

Tagging requires an independent confirmation:

```bash
python scripts/git_submit.py plan --repo . --branch my-branch --confirm-branch my-branch --push-branch my-branch --confirm-push-branch my-branch --commit-message "Prepare v1.2.3" --confirm-commit-message "Prepare v1.2.3" --commit-comment "Update release metadata and verified delivery files for v1.2.3." --confirm-commit-comment "Update release metadata and verified delivery files for v1.2.3." --tag v1.2.3 --confirm-tag v1.2.3 --tag-message "Add payment validation, document the migration impact, and verify the release test suite." --confirm-tag-message "Add payment validation, document the migration impact, and verify the release test suite." --release-notes "## Changed\n- Add payment validation.\n\n## Compatibility\n- No breaking changes.\n\n## Verification\n- Release tests passed." --confirm-release-notes "## Changed\n- Add payment validation.\n\n## Compatibility\n- No breaking changes.\n\n## Verification\n- Release tests passed."
```

For GitHub remotes, the plan contains a final `gh release create` preview after the tag push. Its notes should cover the key changes, compatibility or migration impact, known risks, and verification. The agent must ask for a separate confirmation before executing that remote mutation.

## Configuration

Import JSON into one of three scopes:

```bash
python scripts/git_submit.py config import --scope global --file config/examples/global.json
python scripts/git_submit.py config import --scope host --identity github.com --file config/examples/host-github.json
python scripts/git_submit.py config import --scope project --repo . --file config/examples/project.json
```

Proxy configuration contains environment-variable names only, such as `HTTPS_PROXY`; values remain in the process environment and are never persisted or printed. Authentication policy may store only a governed reference such as `credential-helper:manager-core`, never credential material. The SQLite database is `governed-git-submit.db` in the platform user-data directory; explicit paths inside a repository are rejected. Configuration exports are marked sensitive/non-committable and must be written outside repositories.

## Validation

```bash
python scripts/validate_config.py config/examples/global.json
python -m unittest discover -s tests -v
python ../starline-meta-skill/scripts/validate_skill.py .
```

## Installation

```bash
npx skills add FreeCodeCampXYG/starline-git-submit
test -f ~/.agents/skills/starline-git-submit/SKILL.md
```

The package is installed locally at the user skill directory and requires no background service. Installation copies the complete skill including `SKILL.md`, `references/`, `scripts/`, `evals/`, and the bundled GitHub governance templates.

## 你可以直接这样说

- “检查这个仓库能不能安全提交并推送，先给计划，不要执行。”
- “确认推送当前分支到 GitHub，但不要打 tag。”
- “给 v0.2.0 做独立 tag 计划，分支和 tag 分开确认。”
- “检查没有 LICENSE 的 GitHub 项目，确认后补齐许可证、Issue 模板和 PR 模板。”
- “为 GitHub 发布 v1.0.0，tag 和 Release notes 必须说明本次变更和验证结果。”
- “检查 GitLab 的认证、代理和冲突状态。”

## Troubleshooting

- `target GitHub repository already exists`: choose a different name or use the existing-repository workflow; overwrite is forbidden.
- `target repository absence could not be verified`: fix GitHub authentication/network access and rerun; absence is never inferred.
- repository created but not pushed: expected—creation and push require separate confirmation phases.
- `not a Git repository`: pass an existing working tree with `--repo`.
- `branch confirmation mismatch`: copy the exact inspected branch into both `--branch` and `--confirm-branch`.
- `conflicts present`: resolve conflicts manually and re-run inspection.
- credential-helper absent: configure Git authentication outside this skill; never place a token in profile JSON.
- SSH agent unavailable: start an agent and load a key using platform-native tooling, then rerun `auth-status`.
- `license file is missing`: run `hygiene-plan`, choose a license and legal copyright holder, run the exact-confirmed `hygiene-init`, review/stage its files, then re-inspect.
- `GitHub issue/PR governance files are missing`: use the same hygiene flow; existing project templates are never overwritten.
- `tag message is too vague`: describe the principal changes, compatibility/risk, and verification. GitHub releases also require complete Release notes.

## License

MIT. See [LICENSE](LICENSE).

Copyright (c) 2026 Starline
