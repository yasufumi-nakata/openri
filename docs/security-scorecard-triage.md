# Security Scorecard triage

This page records the public operational response for OpenSSF Scorecard alerts that are not ordinary code defects. It is intentionally evidence-based: OpenRI should not hide residual risk, and it should not add badges or claims before the external service state proves them.

## 2026-05-22 alert register

Issue: [#31 OpenSSF Scorecard の残留 alert を運用対応する](https://github.com/yasufumi-nakata/openri/issues/31)

Repository creation date from GitHub REST metadata: `2026-05-17T15:07:49Z`.

The current authenticated maintenance session could not read private security alert APIs without additional repository administration scope. Public triage therefore uses the issue record, repository files, and repeatable commands below as evidence.

## CodeReviewID

Alert: `Found 0/15 approved changesets -- score normalized to 0`.

Repository-side mitigation added:

- `.github/CODEOWNERS` assigns all paths to `@yasufumi-nakata`.
- `.github/workflows/pr-review-gate.yml` fails a PR until at least one `APPROVED` review exists.
- `docs/maintainer-guide.md` lists the required `main` branch protection settings and includes `Require approved PR review` in the required checks.

Required GitHub setting after this PR is merged:

- Protect `main`.
- Require a pull request before merging.
- Require at least one approval.
- Dismiss stale approvals on new commits.
- Require conversation resolution.
- Require status checks including `Require approved PR review` and the existing CI checks.

The GitHub branch protection rule itself is not a git-tracked file. The Scorecard workflow has a `branch_protection_rule` trigger and a `workflow_dispatch` trigger so maintainers can rerun Scorecard immediately after applying the setting.

## MaintainedID

Alert: `Repository was created within the last 90 days.`

This is repository-age based and cannot be corrected by a code change. The repository was created on `2026-05-17T15:07:49Z`, so the first full 90-day recheck window starts after `2026-08-15T15:07:49Z`. Recheck on `2026-08-16` UTC or later and keep the alert open only if Scorecard still reports the repository as too new.

## CIIBestPracticesID

Alert: `no effort to earn an OpenSSF best practices badge detected`.

Verification on `2026-05-22`:

- Searching `https://www.bestpractices.dev/en/projects?q=openri` returned `Zero Projects`.
- No OpenRI project URL or passing badge ID exists yet.

Do not add an OpenSSF Best Practices badge to `README.md` until a real `bestpractices.dev/projects/<id>` entry exists for `yasufumi-nakata/openri`. The correct follow-up is to register the project, complete the criteria truthfully, then add the real badge link.

## Recheck commands

```bash
gh api repos/yasufumi-nakata/openri --jq '{created_at,default_branch,pushed_at}'
gh workflow run scorecard.yml --repo yasufumi-nakata/openri --ref main
gh run list --repo yasufumi-nakata/openri --workflow "OpenSSF Scorecard" --limit 5
gh api repos/yasufumi-nakata/openri/code-scanning/alerts --paginate
```

If the code scanning API returns `403`, ask a repository administrator to run the command or refresh `gh` with the required security-administration scope. Do not treat an unreadable alert list as resolved.
