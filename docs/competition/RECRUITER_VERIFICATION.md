# Recruiter verification

Learners create shares under `/portfolio/sharing`, explicitly select eligible artifacts and completion records, choose a display name, decide whether to include email, and set expiration.

Only a hash of the high-entropy share token is stored. Public `/verify/:shareToken` access requires an active, unexpired, unrevoked share. Each access is recorded without storing the token. Revocation takes effect immediately.

The public response reconstructs evidence from current tenant-owned records, so revoked artifacts or completion records disappear. It never returns private notes, Sentinel history, memberships, internal risk flags, full account data, or unselected evidence.

Verification shows transparent dimensions: demonstrated skill evidence, evidence depth, human-reviewed item count, and recency. Missing evidence is shown as insufficient data. No opaque hire score or employment guarantee is produced.

Recruiter evidence requests require an authenticated recruiter permission and create a safe in-application notification for the learner.
