# Workflow

1. If the user explicitly requests a new GitHub repository, capture owner, repository name, visibility, and default branch. Require exact confirmation of all four values.
2. Verify `gh` is authenticated, query the exact target read-only, and stop if it exists or absence is uncertain. Emit only `gh repo create OWNER/REPO --VISIBILITY` as a non-executed phase.
3. Ask for a final creation confirmation. Execute that one command visibly; do not combine `--source`, `--remote`, or `--push`. Verify the new repository, initialize/inspect locally, and separately confirm later Git mutations.
4. Inspect without network or mutation, then run `hygiene-plan`. A missing license is a hard stop. Do not infer its legal terms: obtain exact confirmation of the supported license and copyright holder, run `hygiene-init`, review the new files, stage deliberately, and re-inspect.
5. For GitHub remotes, a missing Issue form/PR template is also a hard stop. `hygiene-init` creates only missing packaged files; it neither replaces project templates nor mutates remote Issues, labels, comments, PRs, reviews, or merge state.
6. Resolve global, host, and project profiles and review project match status.
7. Probe authentication capability without revealing credential material.
8. Select a remote explicitly, from tracking configuration, from a governed profile, or from a sole remote. Multiple ungoverned remotes require an explicit choice.
9. Confirm the current branch and the destination push branch independently. Protected branches require policy allowance and a separate exact confirmation.
10. Inspect `git diff --cached`; draft and exactly confirm a one-line commit subject plus a separate modification comment that states the principal changes and their purpose or impact. Reject generic records such as `update` or `修改`.
11. Preview `git fetch --prune --no-tags <remote>` without executing it. Tracking classification uses current local remote-tracking refs and is labelled stale until that fetch is interactively executed.
12. A tag requires an independent exact confirmation plus a concrete annotated-tag message. GitHub tags require independent, concrete Release notes and an authenticated `gh`; preview `gh release create` after tag push. Execute every mutation only after its own confirmation and re-inspect after state changes.

Existing/uncertain creation targets, missing license or GitHub governance files, confirmation mismatches, conflicts, detached HEAD, invalid refs, vague release text, forbidden staged DB/export artifacts, project mismatch/ambiguity, or policy failures are hard stops.
