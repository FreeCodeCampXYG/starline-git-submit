# Safety

No force push, reset, clean, history rewrite, automatic stash, conflict resolution, repository overwrite, non-GitHub repository creation, or hidden mutation is permitted. GitHub repository creation is the sole exception: exact owner/name/visibility/default-branch confirmation, authenticated `gh`, and confirmed target absence are mandatory. The planner validates repository fields plus branch and tag refs before emitting argv arrays.

Creation is not rollback-safe: GitHub repository deletion is never automatic and remains outside this skill. Therefore the pre-create gate is strict, and the resulting authorization covers one visible `gh repo create` command only. It excludes `--source`, `--remote`, `--push`, deletion, settings changes, Pages configuration, and all later Git mutations.

The plan previews fetch, commit, branch push, annotated tag, and tag push phases but executes none. Branch push uses `refs/heads/<local>:refs/heads/<target>`; tag push uses `refs/tags/<tag>:refs/tags/<tag>`. Lightweight tags are not planned.

A missing license blocks submission. The only automatic local remediation is `hygiene-init`, which requires exact confirmation of the file-creation action and, when no license exists, the MIT selection plus copyright holder. It never guesses legal terms, overwrites an existing license/template, stages files, or changes remote settings. For GitHub remotes it may create missing packaged Issue forms and a PR template; it never creates/edits labels, comments, issues, PRs, reviews, or merge state.

Annotated tags require a concrete confirmed message. For GitHub repositories, a tag plan also requires an independently confirmed Release-notes record and authenticated `gh`; it previews a separate `gh release create` after tag push. The agent must not use generated notes, automatic merge, or an empty/vague release description as a substitute for the confirmed record.

Inspection blocks staged `governed-git-submit.db`, WAL/SHM companions, and files containing the governed export marker. Configuration exports are sensitive, non-committable metadata and must remain outside repositories.
