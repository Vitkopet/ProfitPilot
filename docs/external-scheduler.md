# ProfitPilot external 5-minute scheduler (cron-job.org)

## Goal
Use cron-job.org to trigger the existing `.github/workflows/scanner.yml` on `main` every 5 minutes through GitHub's workflow_dispatch API. Keep the existing GitHub schedule enabled as a fallback until the external schedule has been verified. This may create duplicate runs; monitor before disabling the fallback.

## 1. Create a narrowly scoped GitHub token
- GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token.
- Resource owner: Vitkopet.
- Repository access: Only select repositories > ProfitPilot.
- Repository permissions: Actions = Read and write. Keep other permissions at their minimum.
- Choose a short expiration and set a reminder to renew it.
- Copy the token directly into cron-job.org's custom Authorization header. Never put it in repository files, workflow logs, issues, screenshots, or chat.

## 2. Create the external job
- Sign in to https://cron-job.org and create a cronjob.
- Title: ProfitPilot external 5-minute dispatch
- URL: https://api.github.com/repos/Vitkopet/ProfitPilot/actions/workflows/scanner.yml/dispatches
- HTTP method: POST
- Frequency: Every 5 minutes (00,05,10,15,... UTC; local time is irrelevant for an every-5-minute cadence).
- Custom headers:
  - Authorization: Bearer <FINE_GRAINED_GITHUB_TOKEN>
  - Accept: application/vnd.github+json
  - Content-Type: application/json
  - X-GitHub-Api-Version: 2022-11-28
- Request body:
  {"ref":"main"}
- Save the job and use the service's test-run function.
- Expected successful dispatch HTTP response: 204 No Content. A 204 means GitHub accepted the dispatch, not that the scan completed.

## 3. Verify actual runs
- Open https://github.com/Vitkopet/ProfitPilot/actions/workflows/scanner.yml
- New externally triggered runs should show event `workflow_dispatch` (rather than `schedule` or `push`).
- Verify the steps `Unit tests`, `Scan public markets`, `Archive report to Google Drive`, and `Save report` all complete successfully.
- Compare timestamps of at least 12 consecutive external dispatches (1 hour); ideally check 24 dispatches (2 hours).
- Check cron-job.org execution history for HTTP errors, and compare with GitHub run history.
- The existing `reports/schedule_diagnostics.json` in each GitHub artifact records workflow creation and step time; it does not by itself measure the difference between scheduled time and GitHub creation time.

## 4. Avoid duplicates and monitor
- Keep the native `schedule: '*/5 * * * *'` only while validating the external job. The fallback may occasionally trigger the same minute as the external scheduler.
- Once the external scheduler is verified and authorized by the owner, remove the native schedule to avoid duplicate scans and Drive uploads.
- cron-job.org success indicates an accepted API request; configure notifications and separately check GitHub job outcomes.
- The GitHub token is stored with the external service; review that trust decision and rotate/revoke the token if exposed.
- This is PAPER-only. Do not enable real orders or modify MICRO v1.1 or LONG_WATCH thresholds.

References:
- https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
- https://docs.cron-job.org/creating-cron-jobs.html
