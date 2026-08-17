# Configuration

The database is `governed-git-submit.db` under the platform user-data directory. An explicit `STARLINE_GIT_SUBMIT_DB_PATH` is rejected when it points inside the inspected repository. SQLite uses `busy_timeout`, requests WAL mode when supported, and maintains `schema_meta`, `global_defaults`, `host_profiles`, `project_profiles`, and `audit_events`. A newer incompatible schema fails loudly; the v0 legacy `profiles` table is migrated once.

Scope precedence is `global -> host -> project`; nested `proxy_env` objects deep-merge. Profiles may declare `auth_method` and a non-secret `credential_reference` such as `credential-helper:manager-core` or `ssh-agent:default`. They may not contain tokens, passwords, private keys, credential-bearing URLs, or proxy values.

A project has a path-specific key from the resolved repository root and Git common directory, plus a separate normalized-remote fingerprint. Exact path and fingerprint matches apply directly. A unique remote match reports `moved`; changed remotes report `mismatch`; multiple same-remote candidates report `ambiguous`. Mismatch and ambiguous states stop planning instead of silently reusing policy.

Exports are marked sensitive and non-committable and are rejected inside a Git repository by default. Imports accept plain profile JSON or a governed export wrapper and always revalidate the profile schema.
