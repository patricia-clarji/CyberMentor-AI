# Organization model

CyberMentor uses one shared organization boundary for learner, academic, company, and recruiter workflows. A user may hold different roles in multiple organizations. The active organization is stored on the authenticated session and may be changed only to an active membership.

Tenant-owned records carry `organization_id`; APIs filter it server-side before returning or mutating an object. Changing organizations clears organization-specific frontend query caches.

Organization kinds are personal, university, training provider, company, and recruiter. Organization owners and administrators can manage permitted profile metadata, settings, members, invitations, cohorts, assignments, reports, and audit history. Optimistic version checks protect organization profile changes.

Invitations use a random single-use token stored only as a hash. They bind organization, intended email, assigned role, inviter, expiration, status, and response time. Acceptance requires an authenticated account with the intended email. Invitation input cannot assign owner or platform roles. Cancellation, acceptance, rejection, member role changes, deactivation, and reactivation are auditable.

Membership deactivation prevents authentication in that organization without deleting historical learning evidence.

Current limitations:

- Ownership transfer and protected organization archival are not exposed yet.
- Invitation delivery uses the configured existing email backend; development responses expose the acceptance token for testability.
- Bulk enrolment accepts up to 500 known user IDs; CSV import is not implemented.
