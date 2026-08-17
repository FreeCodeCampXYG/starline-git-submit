# Authentication

HTTPS readiness reports whether Git has a credential helper configured; it never calls credential fill or prints credentials. SSH readiness reports agent presence and, when available, `ssh-add -l` capability without reading key files. `glab auth status` remains an optional status probe. `gh auth status --hostname github.com` is mandatory before GitHub repository creation; the skill never prints token material. Gitee and generic remotes use Git's configured HTTPS/SSH mechanisms and cannot use the repository-creation flow.
