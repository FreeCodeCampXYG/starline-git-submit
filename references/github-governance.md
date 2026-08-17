# GitHub Issue and Pull Request Governance

## Bootstrap boundary

Run `hygiene-plan` after local inspection. If no root license exists, select the legal terms and copyright holder explicitly; `hygiene-init` currently supports the MIT template only. It creates files only when absent and never stages them. For a GitHub remote, the packaged files are:

- `.github/ISSUE_TEMPLATE/bug_report.yml`: reproducibility, environment, and redacted evidence.
- `.github/ISSUE_TEMPLATE/feature_request.yml`: problem, proposal, alternatives, and acceptance criteria.
- `.github/ISSUE_TEMPLATE/config.yml`: disables unstructured blank issues. Configure a project-specific private security-reporting contact before directing reporters to one.
- `.github/PULL_REQUEST_TEMPLATE.md`: linked issue, verification, compatibility/risk, and reviewer checklist.

Existing project templates remain authoritative and are never replaced. Re-inspect and explicitly stage the intended new files before submission.

## Issue maintenance

Before changing an Issue, inspect its title, body, labels, author, linked PRs, and public comments with `gh issue view`. Triage into this minimal, project-local taxonomy when the repository has agreed to it:

- type: `type: bug`, `type: feature`, `type: documentation`, `type: security`
- status: `status: needs-triage`, `status: needs-reproduction`, `status: blocked`, `status: ready`
- priority: `priority: critical`, `priority: high`, `priority: normal`, `priority: low`

Never create labels, assign people, add comments, close/reopen, or mark duplicates without the exact Issue number, requested action, and user confirmation. Security reports must not be moved into public Issue comments.

The bundled forms do not attach labels automatically, because a label may be absent or have different project semantics. After the repository owner explicitly adopts the taxonomy, create or modify each remote label only with a separately confirmed remote action.

## Pull request maintenance

Before reviewing or modifying a PR, inspect its diff, commits, checks, review decision, linked Issue, and requested changes. Require a focused scope, verification evidence, no secrets or unrelated artifacts, and an explicit compatibility/risk statement. Do not auto-approve, merge, rebase, force-push, or dismiss reviews. If checks, conflicts, or requested changes remain, report the blocker and leave resolution to the confirmed workflow.

## Release record

An annotated tag message must explain the principal changes, compatibility or migration impact, risks, and verification. For GitHub, release notes use the same content plus any contributor or issue links needed by the project. Do not replace this record with a bare version number, `release`, `update`, generated prose, or a changelog that has not been reviewed.
