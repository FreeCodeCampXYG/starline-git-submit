# Prior-art research

研究日期：2026-08-11

## 检索状态

统一 prior-art runner 已尝试以下查询：

- `safe git commit push workflow`
- `git branch reconciliation conflict safety`
- `git proxy remote policy`

当前 Windows 环境缺少 runner 所需的外部 `npx` 可执行入口，检索在 skills.sh 阶段以 `FileNotFoundError` 退出。因此远程目录候选、安装量、仓库 stars、维护状态和许可对比均为 **missing evidence**；没有安装或执行任何第三方候选代码。

## 实际检查的参考实现

### 1. 本地 `starline-meta-skill`

- 进入短名单原因：Governed 包结构、权限/回滚/秘密/发布门禁与证据边界的本地权威。
- 保留：单根 `SKILL.md`、references/scripts/evals/reports 分层、trigger eval、Skill IR、creation handoff、明确 missing evidence。
- 适配：把发布边界改为 Git 提交事务边界；配置写入、branch push、tag 创建和 tag push 分别确认。
- 拒绝：GitHub-only 发布器、`gh` 强依赖、PR/Release 作为通用 Git 核心。
- 落点：`SKILL.md`、`agents/interface.yaml`、`reports/skill-ir.json`、`reports/creation-handoff.md`。

### 2. 本地 `finishing-a-development-branch`

- 进入短名单原因：提供结构化分支收尾选择和破坏性操作确认。
- 保留：先验证、再给明确选择；冲突和删除等高风险步骤交给人工。
- 适配：扩展为 remote、当前 branch、目标 branch、protected branch、tag 的独立确认。
- 拒绝：普通 `git pull`、仅按 main/master 推断目标、自动删除分支。
- 落点：`references/workflow.md`、`scripts/git_submit.py` 的独立确认门。

### 3. 本地 curated `yeet`

- 进入短名单原因：完整 Git 提交/推送触发边界和认证前置检查。
- 保留：只有用户明确要求完整提交链时触发；先看分支和认证状态。
- 适配：不假定 GitHub 或 `origin`，支持 GitLab、Gitee、generic remote 和 SQLite 项目配置。
- 拒绝：自动 `git add -A`、认证失败后 pull master 再重试、隐式 remote/branch。
- 落点：`scripts/inspect_repository.py`、`scripts/auth_probe.py`、`scripts/git_submit.py`。

### 4. 本地 advanced Git workflow reference

- 进入短名单原因：merge/rebase/abort/recovery 与共享历史风险说明。
- 保留：冲突停止、abort 指引、共享历史不可随意重写。
- 适配：v0.1.0 只做 plan，fetch 后重新分类；不自动继续 merge/rebase。
- 拒绝：包括 `--force-with-lease` 在内的所有 force push、自动 reset/rebase/冲突处理。
- 落点：`references/safety.md` 和硬禁止规则。

## Keep / adapt / reject / invent

- **Keep**：inspect-first、显式目标、冲突 hard stop、secret scan、远端核验思想、独立 tag gate。
- **Adapt**：GitHub-only 发布流程改成 host-neutral Git 核心；平台 CLI 只做可选认证探测。
- **Reject**：普通 `git pull` 黑盒、隐式 `origin`、`git add -A`、force push、auto-stash、自动冲突解决、认证失败后修改历史重试。
- **Invent**：仓库外 SQLite JSON profile；path key 与 remote fingerprint 分离；exact/moved/mismatch/ambiguous 项目匹配；DB/WAL/SHM/export 暂存阻断；argv 形式 fetch/branch/tag preview；配置只保存代理环境变量名和 credential reference。

## Evidence boundary

本报告证明已检查上述本地参考并记录具体机制。远程 catalog 研究、跨实现质量比较、真实安装量/维护/许可证据仍为 **missing evidence**。

# v0.4.0 repository hygiene and release-record extension

研究日期：2026-08-16

## 检索与来源

`starline-meta-skill` 的统一 runner 以许可证、Issue/PR 模板和 Release notes 的意图查询再次运行；它在 skills.sh 阶段因当前 Windows 环境无法启动 `npx` 而失败。该目录的候选安装量和全量交叉目录对比仍为 **missing evidence**。直接 SkillsMP 查询成功，候选 `openclaw/openclaw:skills/github`（catalog 显示 386158 GitHub repository stars；这是源仓库 star，不是安装量、技能质量或用户评分）被读取其根 `SKILL.md`；该实现使用 `gh` 处理远端 Issue、PR、检查与 Release，用 `git` 处理本地提交/分支。

同时只读检查了 GitHub Docs 的仓库许可、Issue templates、PR templates、自动 Release notes 页面。它们证明 GitHub 支持本地模板文件和 Release notes 工作流，但没有被当作本技能的运行时依赖。

## Keep / adapt / reject / invent

- **Keep**：本地 Git 与远端 `gh` 分离；在修改前读取 Issue/PR 状态；模板化收集 issue 与 PR 的必要上下文。
- **Adapt**：GitHub 的模板放入 package assets，通过仓库本地的 `hygiene-init` 仅创建缺失文件；GitHub Release 仍保持独立、显式的 `gh release create` preview。
- **Reject**：自动 merge、自动关闭/评论/标记 Issue 或 PR、生成后不审阅的 Release notes、把某个开源许可证当成无须确认的默认法律选择。
- **Invent**：许可证缺失和 GitHub Issue/PR 文件缺失都阻断提交；MIT 和版权主体经精确确认后可自动补齐；tag message 与 GitHub Release notes 均有具体性与精确确认门。

## Evidence boundary

本轮只验证了本地 Python 单元测试、模板文件和计划输出。没有执行 `hygiene-init` 以外的真实用户仓库写入、远端标签/Issue/PR 维护、GitHub Release 创建或人工可用性评审；这些运行时与人类证据均为 **missing evidence**。
# v0.2.0 repository-creation extension

On 2026-08-12 the `starline-meta-skill` unified prior-art runner was attempted with intent-shaped queries for safe confirmed GitHub creation and no-overwrite governance. It failed before catalog access because the current Windows environment could not start its external `npx` executable. Remote candidate evidence is therefore `missing evidence`. The local meta-skill's Governed gates were used for permission, rollback, trust, secret, and claim boundaries; no untrusted code was executed.
