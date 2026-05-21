# OpenSSF Scorecard triage

This note records the operational handling for the Scorecard alerts tracked in issue #31. These alerts are repository governance signals, not manuscript-integrity findings.

## 2026-05-22 status

- `CodeReviewID`: `main` branch protection is enabled and enforced for admins. It requires pull request reviews, code owner review, stale-review dismissal, conversation resolution, linear history, and required CI/status checks before merge.
- `MaintainedID`: the repository was created on 2026-05-17, so the "created within the last 90 days" signal cannot be fixed by code. Recheck on or after 2026-08-15.
- `CIIBestPracticesID`: the OpenSSF Best Practices Badge project list was queried on 2026-05-22 with `q=openri`; no OpenRI project entry was returned. Do not add a badge until OpenRI is registered and the correct project URL is known.

## Verification commands

```bash
gh api repos/yasufumi-nakata/openri/branches/main/protection
curl -L --silent 'https://www.bestpractices.dev/en/projects.json?q=openri'
gh run list --repo yasufumi-nakata/openri --workflow scorecard.yml --limit 5
```

After this change is merged to `main`, rerun the OpenSSF Scorecard workflow and verify whether Code Scanning still reports Scorecard alerts. If GitHub's Code Scanning API is unavailable to the current token, record that API limitation in the issue comment instead of claiming alert closure.
