# Development accounts

> **LOCAL DEVELOPMENT ONLY.** Never copy these credentials to a shared, staging, or
> production environment. Production configuration rejects
> `CYBERMENTOR_DEV_SEED_ENABLED=true`.

## Create or refresh the accounts

From the repository root in PowerShell:

```powershell
$env:CYBERMENTOR_DEV_SEED_ENABLED = "true"
npm run db:seed-dev
Remove-Item Env:CYBERMENTOR_DEV_SEED_ENABLED
```

The command is idempotent. It creates missing fixtures and restores the documented
passwords, verified-email state, memberships, and roles for existing fixtures. It
will run only when `CYBERMENTOR_ENVIRONMENT=development` and
`CYBERMENTOR_DEV_SEED_ENABLED=true`.

Every account uses this local-only password:

```text
Local-Only-CyberMentor-42!
```

| Account                                | Seeded role                               | Organization                    | Start page            | Representative access                                                                                       |
| -------------------------------------- | ----------------------------------------- | ------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------- |
| `learner@local.cybermentor`            | `learner`                                 | CyberMentor University          | `/academy`            | Learner onboarding, diagnostic, roadmap, pathway, labs, mission, project, Sentinel, portfolio sharing       |
| `instructor@local.cybermentor`         | `instructor`                              | CyberMentor University          | `/instructor`         | Cohorts, learner evidence, assignments, human reviews, reports                                              |
| `reviewer@local.cybermentor`           | `reviewer`                                | CyberMentor University          | `/instructor/reviews` | Review queue and review decisions; no assignment or cohort management                                       |
| `university-admin@local.cybermentor`   | `organization_owner`                      | CyberMentor University          | `/university`         | University analytics/programmes plus organization, cohort, assignment, review, report, and audit operations |
| `organization-admin@local.cybermentor` | `organization_admin`                      | CyberMentor Training Provider   | `/organization`       | Organization settings, members, invitations, cohorts, assignments, reports, and audit                       |
| `company-manager@local.cybermentor`    | `company_manager`                         | CyberMentor Company             | `/company`            | Company cohorts, training assignments, skills analytics, and reports                                        |
| `recruiter@local.cybermentor`          | `recruiter`                               | CyberMentor Recruiter Network   | `/recruiter`          | Recruiter dashboard, evidence requests, and reports                                                         |
| `platform-admin@local.cybermentor`     | `platform_admin` plus platform-admin flag | CyberMentor Platform Operations | `/organization`       | Platform-authorized organization inspection, audit access, and content/platform permissions                 |
| `content-manager@local.cybermentor`    | `platform_content_manager`                | CyberMentor Platform Operations | `/organization`       | Organization inspection and repository content-management authority                                         |

These fixtures are already email-verified so role testing can begin immediately.
They intentionally bypass the normal verification email only for development.
Use a newly registered address to test registration, email verification, password
reset, and invitations.

## Denial checks

The API is the authority; a visible route is not proof of authorization. Confirm
at least one denial for each role:

| Role                       | Permitted check                                      | Must be denied                                           |
| -------------------------- | ---------------------------------------------------- | -------------------------------------------------------- |
| learner                    | Complete learner work under `/academy`               | Create a cohort or invite an organization member         |
| instructor                 | Create/manage an assignment and perform a review     | Change organization settings or send invitations         |
| reviewer                   | Approve, reject, or request revision on queued work  | Create an assignment or cohort                           |
| organization owner         | Invite members and perform reviews                   | Platform-only management outside the active organization |
| organization administrator | Invite/manage members and view audit                 | Perform a final human-review decision                    |
| company manager            | Create company cohorts and training assignments      | Invite organization members or perform human reviews     |
| recruiter                  | View recruiter analytics and request shared evidence | Manage cohorts, assignments, or members                  |
| platform administrator     | Use platform-level authority and content permission  | Learner progress writes without a learner membership     |
| content manager            | Run the repository content workflow                  | Manage organization membership or learner submissions    |

Use the browser UI for the permitted action. Use
`http://127.0.0.1:8010/api/docs` for a precise denied API operation; sign in in
the application first so the session cookies exist, copy the `cm_csrf` cookie
value into the `X-CSRF-Token` header for mutations, and expect HTTP `403`.

## Verification status

The seed command was run twice against the local database with identical results.
All nine accounts then returned HTTP `200` from login and from one representative
role route. The same learner and platform-administrator logins were also verified
from the disposable clean-checkout database.
