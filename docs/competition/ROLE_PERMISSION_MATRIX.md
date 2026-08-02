# Role and permission matrix

Permissions are resolved through membership roles in the active organization and enforced by API handlers. UI visibility is supplementary, not an authorization boundary.

| Role                     | Principal permissions                                                                                                |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| organization_owner       | Full organization, membership, cohort, assignment, review, report, company-training, sharing, and audit permissions  |
| organization_admin       | Organization and membership management; cohorts, assignments, reports, company training, sharing requests, and audit |
| instructor               | Cohort and detailed learner progress; assignments; review queue and human review; reports view                       |
| reviewer                 | Cohort/learner summaries, assignment view, and human review                                                          |
| cohort_manager           | Cohort creation/management, enrolment, curriculum and assignment management, detailed progress, reports view         |
| company_manager          | Employee cohorts, enrolment, assignments, aggregate company training, and protected exports                          |
| recruiter                | Learner-approved evidence view/request and report view                                                               |
| learner                  | Own learning, missions, portfolio, organization view, assignments, notifications, and evidence sharing               |
| platform_admin           | Platform, content, and audit permissions                                                                             |
| platform_content_manager | Content management                                                                                                   |
| platform_support         | Organization view only                                                                                               |
| platform_auditor         | Audit-log view                                                                                                       |

Implemented permission keys include all milestone keys: `organization.view`, `organization.manage`, member view/invite/manage, cohort view/create/manage/assign, learner summary/detailed-progress/enrolment, assignment view/create/manage, review view/perform, report view/export, company training, recruiter evidence view/request, audit-log view, content management, and platform management.

Private learner notes are not granted to instructor, company-manager, recruiter, or cohort-manager roles. No portal endpoint returns Sentinel conversations.
