# Dependabot Maintenance Guide

This repository uses [GitHub Dependabot](https://docs.github.com/en/code-security/dependabot) to keep dependencies for the JavaScript, Python, and CI workflows up to date.

## Update coverage and cadence

Dependabot is configured in [`.github/dependabot.yml`](../.github/dependabot.yml) with the following rules:

| Ecosystem         | Directory | Schedule             | Notes |
| ----------------- | --------- | -------------------- | ----- |
| npm               | `/`       | Weekly on Mondays at 08:00 UTC | Covers the front-end build tooling defined in `package.json`. |
| pip               | `/`       | Weekly on Mondays at 08:00 UTC | Tracks Python dependencies managed through `pyproject.toml`, `uv.lock`, and related requirement files. |
| GitHub Actions    | `/`       | Weekly on Mondays at 08:00 UTC | Keeps reusable workflow actions up to date. |

The staggered schedule ensures that automated dependency updates arrive at a predictable time, making it easier to plan review time and to coordinate with deployment windows.

## Maintainer workflow

When Dependabot opens a pull request:

1. **Review the change summary.** Confirm that the automated changelog and release notes look safe and that the scope is appropriate for the release cycle.
2. **Run automated checks.** Allow CI to run. If additional project-specific smoke tests are required, run them locally before approving.
3. **Verify compatibility.** For backend dependencies, focus on breaking changes that may affect Python services. For frontend dependencies, confirm that build scripts still succeed and that relevant integration tests pass.
4. **Merge or schedule follow-up.** If everything looks good, squash-merge the pull request. If the update needs coordination (e.g., major version bumps), assign an owner, capture the context in the pull request, and schedule any manual work.
5. **Monitor production.** After deployment, keep an eye on monitoring dashboards for regressions related to the updated packages.

Following this checklist keeps the dependency graph healthy while minimizing the risk of regressions.
