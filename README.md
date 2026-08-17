# Starline Git Submit

[![Stars](https://img.shields.io/github/stars/FreeCodeCampXYG/starline-git-submit?style=flat-square&label=Stars)](https://github.com/FreeCodeCampXYG/starline-git-submit/stargazers)
[![License](https://img.shields.io/github/license/FreeCodeCampXYG/starline-git-submit?style=flat-square)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/FreeCodeCampXYG/starline-git-submit?style=flat-square)](https://github.com/FreeCodeCampXYG/starline-git-submit/commits/main)
[![Release](https://img.shields.io/github/v/release/FreeCodeCampXYG/starline-git-submit?style=flat-square)](https://github.com/FreeCodeCampXYG/starline-git-submit/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/FreeCodeCampXYG/starline-git-submit/ci.yml?style=flat-square&label=CI)](https://github.com/FreeCodeCampXYG/starline-git-submit/actions)

> A governed Git delivery skill: reviewable plans, exact-confirmed mutations, and safe GitHub publishing — for agents and humans.
>
> 受治理的 Git 交付技能：可审查的计划、精确确认的变更与安全的 GitHub 发布 —— 适用于 Agent 与人类。

---

## English

A local governed skill for safely creating a new GitHub repository when explicitly confirmed, or preparing an existing repository for a documented Git delivery. It checks for a license, supplies missing GitHub Issue/PR templates only after exact confirmation, and requires explanatory annotated tags and GitHub Release notes. It keeps configuration outside the skill directory in a platform user-data SQLite database and never stores credentials.

### What it does

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

### What it does not do

It does not force push, reset, clean, auto-stash, resolve conflicts, overwrite repositories or governance files, guess a legal license, create repositories outside GitHub, publish packages, or execute opaque Git mutations. It does not automatically label, comment on, close, or merge an Issue/PR. Creation never includes source attachment or push, and does not authorize later Git operations. `run` deliberately returns the same governed action plan as `plan`; the interactive agent must execute confirmed mutations visibly.

### Requirements

- [ ] Python 3.9+ standard library: `python --version`
- [ ] Git available on `PATH`: `git --version`
- [ ] Optional: `ssh-add`, `gh`, or `glab` for richer readiness probes

### Quick start

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

### Configuration

Import JSON into one of three scopes:

```bash
python scripts/git_submit.py config import --scope global --file config/examples/global.json
python scripts/git_submit.py config import --scope host --identity github.com --file config/examples/host-github.json
python scripts/git_submit.py config import --scope project --repo . --file config/examples/project.json
```

Proxy configuration contains environment-variable names only, such as `HTTPS_PROXY`; values remain in the process environment and are never persisted or printed. Authentication policy may store only a governed reference such as `credential-helper:manager-core`, never credential material. The SQLite database is `governed-git-submit.db` in the platform user-data directory; explicit paths inside a repository are rejected. Configuration exports are marked sensitive/non-committable and must be written outside repositories.

### Validation

```bash
python scripts/validate_config.py config/examples/global.json
python -m unittest discover -s tests -v
python ../starline-meta-skill/scripts/validate_skill.py .
```

### Installation

```bash
npx skills add FreeCodeCampXYG/starline-git-submit
test -f ~/.agents/skills/starline-git-submit/SKILL.md
```

The package is installed locally at the user skill directory and requires no background service. Installation copies the complete skill including `SKILL.md`, `references/`, `scripts/`, `evals/`, and the bundled GitHub governance templates.

### Troubleshooting

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

---

## 中文

一个本地受治理的 Skill：在明确确认时安全地创建新的 GitHub 仓库，或为既有仓库准备有记录的 Git 交付。它会检查许可证、仅在精确确认后补齐缺失的 GitHub Issue/PR 模板，并要求带说明的 annotated tag 与 GitHub Release notes。配置存放在 Skill 目录之外的平台用户数据 SQLite 数据库中，绝不保存凭据。

### 功能

- 按 `global -> host -> project` 顺序解析 JSON 策略档案
- 为路径生成专属项目键，并另存归一化远端指纹，报告 moved / mismatch / ambiguous 匹配状态
- 检查分支、上游、暂存/未暂存/未跟踪文件、冲突与远端
- 对远端 URL 中内嵌的凭据做脱敏
- 探测 HTTPS credential-helper、SSH agent 及可选的 `gh` / `glab` 就绪状态
- 生成可审查的命令，分支确认与 tag 确认相互独立
- 要求每次提交包含具体主题行与由暂存差异推导的修改说明
- 根许可证缺失时停止提交流程，仅在明确确认 MIT 与版权主体后写入模板
- 对 GitHub 远端，补齐缺失的 Issue 表单与 PR 模板，且不覆盖项目自维护的模板
- 要求具体的 annotated-tag 消息；GitHub release 计划额外要求独立确认的 Release notes 与 `gh release create` 预览
- 仅在精确确认 owner/name/visibility/默认分支并完成可验证的缺失检查后，才计划创建 GitHub 仓库

### 不做的事

不 force push、reset、clean、auto-stash、不自动解决冲突、不覆盖仓库或治理文件、不猜测法律许可、不创建 GitHub 之外的仓库、不发布包、不执行不透明的 Git 变更。不自动给 Issue/PR 打标签、评论、关闭或合并。创建操作从不包含源码附加或推送，也不授权后续 Git 操作。`run` 与 `plan` 一样只输出受治理的行动计划；交互式 Agent 必须显式执行经过确认的变更。

### 环境要求

- [ ] Python 3.9+ 标准库：`python --version`
- [ ] `PATH` 中存在 Git：`git --version`
- [ ] 可选：`ssh-add`、`gh` 或 `glab`（更丰富的就绪探测）

### 快速开始

```bash
python scripts/git_submit.py config init
python scripts/git_submit.py repo-create-plan --owner acme --repo-name demo --visibility private --default-branch main --confirm-owner acme --confirm-repo-name demo --confirm-visibility private --confirm-default-branch main
python scripts/git_submit.py inspect --repo .
python scripts/git_submit.py auth-status --repo .
python scripts/git_submit.py plan --repo . --branch my-branch --confirm-branch my-branch --push-branch my-branch --confirm-push-branch my-branch --commit-message "Add payment validation" --confirm-commit-message "Add payment validation" --commit-comment "Validate callback signatures and document rejected-request behavior." --confirm-commit-comment "Validate callback signatures and document rejected-request behavior."
```

首次提交前先检查并补齐缺失的治理文件。许可证选择是法律决策，本 Skill 只接受精确确认的输入，绝不猜测：

```bash
python scripts/git_submit.py hygiene-plan --repo .
python scripts/git_submit.py hygiene-init --repo . --license MIT --confirm-license MIT --copyright-holder "Acme" --confirm-copyright-holder "Acme" --confirm-hygiene create-missing-governance-files
git diff --check
git add LICENSE .github
python scripts/git_submit.py inspect --repo .
```

`hygiene-init` 只创建缺失文件、不暂存、不覆盖仓库已有许可证或模板。对 GitHub 远端会补齐 bug 报告表单、功能请求表单、Issue 配置与 PR 模板；刻意不创建、修改或关闭远端 Issue/PR。

打 tag 需要独立的确认：

```bash
python scripts/git_submit.py plan --repo . --branch my-branch --confirm-branch my-branch --push-branch my-branch --confirm-push-branch my-branch --commit-message "Prepare v1.2.3" --confirm-commit-message "Prepare v1.2.3" --commit-comment "Update release metadata and verified delivery files for v1.2.3." --confirm-commit-comment "Update release metadata and verified delivery files for v1.2.3." --tag v1.2.3 --confirm-tag v1.2.3 --tag-message "Add payment validation, document the migration impact, and verify the release test suite." --confirm-tag-message "Add payment validation, document the migration impact, and verify the release test suite." --release-notes "## Changed\n- Add payment validation.\n\n## Compatibility\n- No breaking changes.\n\n## Verification\n- Release tests passed." --confirm-release-notes "## Changed\n- Add payment validation.\n\n## Compatibility\n- No breaking changes.\n\n## Verification\n- Release tests passed."
```

对 GitHub 远端，tag push 后计划包含最终的 `gh release create` 预览。其说明应覆盖主要变更、兼容性或迁移影响、已知风险与验证。执行该远端变更前，Agent 必须请求单独的确认。

### 配置

将 JSON 导入三个作用域之一：

```bash
python scripts/git_submit.py config import --scope global --file config/examples/global.json
python scripts/git_submit.py config import --scope host --identity github.com --file config/examples/host-github.json
python scripts/git_submit.py config import --scope project --repo . --file config/examples/project.json
```

代理配置只保存环境变量名（如 `HTTPS_PROXY`）；值保留在进程环境中，从不持久化或打印。认证策略只能保存受治理的引用（如 `credential-helper:manager-core`），绝不保存凭据材料。SQLite 数据库 `governed-git-submit.db` 位于平台用户数据目录；拒绝仓库内显式路径。配置导出标记为敏感/不可提交，必须写入仓库之外。

### 验证

```bash
python scripts/validate_config.py config/examples/global.json
python -m unittest discover -s tests -v
python ../starline-meta-skill/scripts/validate_skill.py .
```

### 安装

```bash
npx skills add FreeCodeCampXYG/starline-git-submit
test -f ~/.agents/skills/starline-git-submit/SKILL.md
```

包安装到本地用户技能目录，无需后台服务。安装会复制完整 Skill，包括 `SKILL.md`、`references/`、`scripts/`、`evals/` 与内置的 GitHub 治理模板。

### 你可以直接这样说

- “检查这个仓库能不能安全提交并推送，先给计划，不要执行。”
- “确认推送当前分支到 GitHub，但不要打 tag。”
- “给 v0.2.0 做独立 tag 计划，分支和 tag 分开确认。”
- “检查没有 LICENSE 的 GitHub 项目，确认后补齐许可证、Issue 模板和 PR 模板。”
- “为 GitHub 发布 v1.0.0，tag 和 Release notes 必须说明本次变更和验证结果。”
- “检查 GitLab 的认证、代理和冲突状态。”

### 故障排查

- `target GitHub repository already exists`：换一个名称或走既有仓库流程；禁止覆盖。
- `target repository absence could not be verified`：修复 GitHub 认证/网络后重试；缺失状态绝不推断。
- 仓库已创建但未推送：符合预期——创建与推送是独立确认阶段。
- `not a Git repository`：用 `--repo` 传入现有工作树。
- `branch confirmation mismatch`：把检查到的分支原样填入 `--branch` 与 `--confirm-branch`。
- `conflicts present`：手动解决冲突后重新检查。
- credential-helper 缺失：在本 Skill 之外配置 Git 认证；绝不在档案 JSON 中放 token。
- SSH agent 不可用：用平台原生工具启动 agent 并加载密钥，再重跑 `auth-status`。
- `license file is missing`：运行 `hygiene-plan`，选择许可证与法律版权主体，运行精确确认的 `hygiene-init`，审阅/暂存其文件后重新检查。
- `GitHub issue/PR governance files are missing`：使用同样的 hygiene 流程；绝不覆盖项目既有模板。
- `tag message is too vague`：描述主要变更、兼容性/风险与验证；GitHub release 还要求完整的 Release notes。

---

## License / 许可证

MIT. See [LICENSE](LICENSE). / 详见 [LICENSE](LICENSE)。

Copyright (c) 2026 Starline
