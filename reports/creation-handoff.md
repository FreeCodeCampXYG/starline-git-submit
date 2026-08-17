# Creation handoff

## v0.4.1

README made bilingual (English + 中文) with GitHub stars/license/CI badges; version bumped from 0.4.0. Package structure, gates, and Python sources unchanged.

## v0.4.0

Reference skills studied: local `starline-meta-skill` for Governed action, trust, rollback, evidence, and resource-boundary gates; remote `openclaw/openclaw:skills/github` root `SKILL.md` for its separation of local Git from GitHub CLI Issue/PR/Release work. GitHub Docs for license, Issue templates, PR templates, and Release notes were read as platform-primary references. The unified two-catalog prior-art runner could not start `npx` on this Windows environment, so cross-catalog adoption/maintenance evidence is **missing evidence**.

Kept: inspect-first workflow, `git` for local delivery, `gh` only for a separately visible GitHub Release phase, and template-backed Issue/PR context. Adapted: GitHub templates are local package assets copied only when absent; the remote platform remains unchanged until the user confirms a specific action. Rejected: auto-merge, automatic Issue/PR labels/comments/closure, generated or vague Release notes, template overwrite, and a guessed license/copyright holder. Invented: a hard license/community-file submission gate, exact-confirmed MIT bootstrap, concrete tag-message validation, and exact-confirmed GitHub Release notes.

Design advantage: legal selection, repository governance files, Git delivery, tag creation, and GitHub Release creation are separate authority gates. Validated advantage: 24/24 unit tests passed locally, including missing-hygiene blocks, non-overwriting template bootstrap, concrete tag text, and explicit GitHub Release preview. Hypothesis: a required local Issue/PR template baseline will make future triage/review more consistent; real maintainer usability and remote-workflow evidence are **missing evidence**.

Rollback boundary: existing files are never overwritten; all later Git, GitHub Release, Issue, and PR mutations remain separately confirmed. Trust boundary: packaged text files are the only automatic local output, and remote Release creation is a non-executed `gh` argv preview. No remote Issue, PR, label, merge, release, or repository mutation was executed during this update.

## v0.3.0

Version 0.3.0 requires every planned commit to carry an exactly confirmed one-line subject and a separate staged-diff-derived modification comment. The planner emits `git commit -m <subject> -m <comment>` and rejects empty or generic records such as `update`, `fix`, `修改`, or `更新`, making GitHub history easier to distinguish without storing full diffs.

## v0.2.0

Reference skills studied: local `starline-meta-skill` for Governed permission, rollback, trust, evidence, and validation gates. Remote prior-art discovery was attempted with its unified runner, but the current Windows environment could not start the required `npx` executable; candidate-specific remote evidence is `missing evidence`.

Kept: explicit visible mutation phases, exact confirmations, secret rejection, conflict stops, and the separation between plan generation and execution. Adapted: the former absolute repository-creation ban into one GitHub-only exception guarded by exact owner, repository name, visibility, and default-branch confirmations plus authenticated `gh` and confirmed target absence. Rejected: GitLab/Gitee/generic repository creation, overwrite, guessed absence, combined `--source`/`--remote`/`--push`, automatic deletion rollback, and treating creation as authorization for later commit or push.

Design advantage: repository creation and first push are separate authority gates, while an existing or uncertain target emits no command. Validated advantage: 20/20 unit tests pass, including confirmation mismatch, existing/unknown target blocks, invalid names/branches, one-command output, and no implicit push; a live read-only GitHub CLI smoke test classified a random name as absent and emitted a non-executed command only. Hypothesis: four-field confirmation reduces accidental account, visibility, or branch mistakes in real operator use; human usability evidence is missing.

Rollback boundary: repository deletion is intentionally outside the skill because creation is not safely reversible. Trust boundary: only authenticated GitHub CLI status, an exact repository existence query, and one separately confirmed `gh repo create` command cross the provider boundary. No repository was created during validation.

## v0.1.0

Reference skills studied: local `starline-meta-skill` for governed package structure, evidence boundaries, and root entrypoint isolation; local Starline production maintainer skills for minimal operational workflows.

Kept: one root SKILL.md, interface contract, manifest, references, evals, and reports. Adapted: external versioned SQLite JSON profile storage and explicit Git safety planning. Rejected: publication, repository creation, opaque mutation scripts, credential persistence, force/destructive operations, automatic stash/conflict handling, implicit multi-remote selection, lightweight tags, and unvalidated shell command strings.

Design advantage: project identity separates a path-specific key from a normalized-remote fingerprint and reports exact, moved, mismatch, or ambiguous matches. Validated advantage: 21/21 unit tests cover schema migration/version failure, path guards, safe credential references, secret rejection, deep profile merge, export/stage blocking, remote selection, protected branches, invalid refs, fetch preview, concrete confirmed commit records, explicit branch/tag refspecs, repository-creation gates, and annotated tags; trigger evaluation passed 22/22 with no false positives or false negatives. Hypothesis: provider CLI probes and persisted project profiles reduce authentication/configuration friction on later submissions; no live cross-provider or human usability evidence yet.

Limits: no live auth success, provider network, Git mutation, publication, or human usability evidence. `run` remains plan-only.
