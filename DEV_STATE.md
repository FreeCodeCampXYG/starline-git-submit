# DEV_STATE

## Current Goal
- 将 `starline-git-submit` 的提交流程扩展为成熟 GitHub 仓库治理：许可证、Issue/PR 模板与可读 Release 记录均在提交前受控检查。

## Completed Work
- `inspect` 现在报告根许可证和 GitHub Issue/PR 模板状态；提交计划会因缺失项停止。
- `hygiene-plan` 只读输出补齐方案；`hygiene-init` 在 MIT、copyright holder 与文件创建动作均精确确认后，仅创建缺失的 LICENSE 和 GitHub 模板，不覆盖、不暂存、不推送。
- GitHub 模板覆盖 bug/feature Issue 表单、公开安全提示与 PR 的关联 Issue、验证、兼容性/风险清单。
- tag 计划必须有精确确认的具体说明；GitHub tag 额外要求 Release notes 并在 tag push 后预览独立的 `gh release create`。
- 保留目标仓库 `core.autocrlf=false` 的本地行尾防护。

## Key Decisions
- 许可证是法律选择，不根据仓库名称、语言或可见性猜测；当前仅内置 MIT，且必须明确确认版权主体。
- GitHub 的本地协作模板可自动补齐；远端 Issue/PR 的标签、评论、关闭、审批和合并都必须由用户就具体对象与动作再次确认。
- Release 记录不接受版本号、`release` 或其他笼统文本；具体变更、兼容性/风险和验证是最低要求。

## Verification
- 已通过：`python -m compileall -q scripts tests`。
- 已通过：`python -m unittest discover -s tests -v`，24 个测试全部通过。
- 已通过：3 个 `config/examples/*.json` 的 `scripts/validate_config.py` 校验。
- 已通过：`starline-meta-skill/scripts/export_skill_ir.py`、`validate_skill.py` 和 `trigger_eval.py`；触发评估为 29/29，无误触发或漏触发。
- 已运行：`release_check.py --phase local --run-tests`；包校验、版本/报告一致性、秘密扫描和单测通过。因该安装目录不是 Git 仓库，`git diff --check` 与 feature-branch 门禁无法适用，发布就绪结论仍为 blocked/missing evidence。

## Known Issues
- 当前 skill 目录不是独立 Git 仓库；如需发布到 GitHub，需要从对应远端仓库克隆或建立发布工作区后同步。
- 远端 labels 与 Issue/PR 实际维护仍是逐对象、逐动作确认的交互流程；本版只提供本地模板与安全维护规则，不批量修改远端协作状态。
- 尚未执行真实 GitHub Release、远端 Issue/PR 维护或隔离安装验证；这些均为 missing evidence，未作为已验证能力宣传。
