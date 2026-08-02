# Local verification checklist

Use PowerShell from the repository root. Complete setup is documented in
`COMPLETE_LOCAL_RUNBOOK.md`.

## Clean start

- [x] Windows 11 Pro 64-bit host identified.
- [x] Node.js `24.13.0`, npm `11.14.1`, Python `3.13.14`, and Git
      `2.50.0.windows.1` detected.
- [x] A disposable source-only copy was made without `.env`, `node_modules`,
      `backend/.venv`, the SQLite database, or build output.
- [x] `npm install` completed with 262 packages and 0 vulnerabilities.
- [x] `$env:CYBERMENTOR_DEV_SEED_ENABLED="true"; npm run setup:local`
      created `.env`, generated secrets, created `backend/.venv`, installed backend
      dependencies, migrated to `20260730_0005`, seeded the learning model, seeded all
      development users, and generated 488 content publications.
- [x] `npm run dev` started the frontend, trusted API, and retained content API.
- [x] Frontend returned HTTP `200`.
- [x] Trusted readiness returned `ready` with database, migrations, and seed all
      `ready`.
- [x] Content readiness returned `ready` with 144 lessons, 80 labs, and 12
      projects.
- [x] Learner and platform-administrator fixtures logged in successfully in the
      disposable copy.
- [x] The recorded process tree stopped cleanly and ports 5173, 8010, and 8787
      were released.

## Database and accounts

```powershell
npm run db:status
npm run db:verify
$env:CYBERMENTOR_DEV_SEED_ENABLED = "true"
npm run db:seed-dev
Remove-Item Env:CYBERMENTOR_DEV_SEED_ENABLED
```

Expected:

- [ ] Migration output is `20260730_0005 (head)`.
- [ ] Schema verification reports `database_verified`, migration
      `20260730_0005`, and 89 tables.
- [ ] The development seed lists nine accounts.
- [ ] Running the development seed again succeeds without duplicates.

## Live health

With `npm run dev` running:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/healthz
Invoke-RestMethod http://127.0.0.1:8010/readyz
Invoke-RestMethod http://127.0.0.1:8787/readyz
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173/).StatusCode
```

- [ ] Liveness is `ok`.
- [ ] Trusted readiness and every dependency are `ready`.
- [ ] Content readiness is `ready`.
- [ ] Frontend status is `200`.

## Automated quality gates

```powershell
npm run test:backend
npm test
npm run typecheck:backend
npm run typecheck
npm run lint:backend
npm run lint
npm run format:backend
npm run format
npm run validate-content
npm run build
```

Final verified results are recorded in the runbook's “Test commands” section.

- [x] Backend: 56 passed.
- [x] Node/React: 15 files and 121 tests passed.
- [x] Sentinel: 54 tests passed within the full suite.
- [x] Content: 12 tests passed and repository validation succeeded.
- [x] Backend strict typing reported no issues in 70 source files.
- [x] Frontend type checking, backend/frontend lint, changed-file formatting,
  and production build passed.

Targeted commands:

```powershell
npm run test:backend -- tests/test_dev_seed.py tests/test_identity.py
npm run test:backend -- tests/test_operations.py tests/test_projects.py
npm exec vitest -- run src/features/portals/PortalApp.test.tsx --pool=vmThreads --maxWorkers=1
npm exec vitest -- run src/features/competition/LabWorkspace.test.tsx src/features/portals/PortalApp.test.tsx --pool=vmThreads --maxWorkers=1
npm run evaluate-ai
```

- [ ] Development seed and identity tests pass.
- [ ] Tenant-scoped operations/projects tests pass.
- [ ] Portal denial tests pass.
- [ ] Lab and portal accessibility-oriented UI tests pass.
- [ ] Sentinel safety, grounding, and evaluation tests pass.

## Manual authentication

- [ ] Register a unique learner.
- [ ] Open the verification link printed by the trusted API (or Mailpit in the
      optional Compose profile).
- [ ] Sign in and complete onboarding.
- [ ] Sign out and sign in again.
- [ ] Request a password reset.
- [ ] Open the reset link and choose a new password.
- [ ] Confirm the old password fails and the new password works.
- [ ] Confirm a mutation without `X-CSRF-Token` is rejected.

## Roles and features

- [ ] Every account in `DEVELOPMENT_ACCOUNTS.md` can log in.
- [ ] Every role passes one permitted-action check.
- [ ] Every role receives a permission denial for one prohibited action.
- [ ] Learner completes onboarding and the 12-question diagnostic.
- [ ] Roadmap, pathway lesson, notes, bookmarks, practice, and assessment work.
- [ ] A lab starts, resumes, records terminal actions/notes/hints, validates
      evidence, and exposes replay.
- [ ] Harbor Light mission records evidence/actions, grades a submission, exposes
      replay, and creates verifiable completion when passed.
- [ ] Sentinel shows reviewed citations and refuses answer-key and unsafe requests.
- [ ] Project submission enters human review; reviewer requests revision; learner
      resubmits; reviewer approves.
- [ ] Eligible evidence appears in portfolio sharing and a share can be revoked.
- [ ] Organization invitations, cohorts, assignments, notifications, reports,
      and audit logs work within the active tenant.
- [ ] Content validation passes and learner bundles contain no private answer keys.

## Known local boundary

- [x] Docker is not installed on the verification host. The optional PostgreSQL,
      Redis, Mailpit, worker, and MinIO Compose profile is therefore documented from
      the checked-in Compose file but not marked runtime-verified.
- [x] Account deletion is not implemented.
- [x] Content authoring/publishing is repository CLI based; there is no
      content-manager CMS page.
- [x] Notifications are implemented through the API but have no dedicated
      notification-center page.
- [x] There is no separate platform-admin page; platform authority is enforced by
      API permissions and the organization operations surface.
