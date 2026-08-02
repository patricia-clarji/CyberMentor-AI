# Professional Development Evidence Model

The career workspace at `/career` is a view over tenant-scoped, persisted
learning activity. It does not accept manual skills, achievements, projects,
missions, certificates, or timeline claims.

## Trusted sources

- `skill_evidence` and `learner_skill_states` produce the Skill Passport;
- reviewed project artifacts, mission/lab artifacts, and current completion
  records produce portfolio evidence;
- a certificate can be issued only from a non-revoked `completion_records`
  row owned by the active learner;
- transcript, resume, readiness, and role mapping read those same records.

Reflections are learner-authored, versioned records. They are intentionally
separate from achievements and are never treated as verified performance.

## Privacy and access

Professional profile fields carry per-field visibility values. The public
portfolio endpoint exposes only fields marked `public`, and only when the
portfolio itself is public. Public profiles contain a derived Skill Passport,
not internal learner analytics, notes, reviewer queues, or Sentinel history.

Existing recruiter evidence-sharing remains the controlled recruiter path:
learners explicitly select eligible artifacts and completion records, shares
expire, and revocation removes access. Organization reports require the
existing `reports.view` permission and report only tenant-scoped aggregates.

## Certificates and exports

Certificates have durable IDs, verification codes, immutable completion facts,
status, and a SHA-256 integrity signature over their issuance facts. The public
verification endpoint never returns the verification secret or signature.
Transcript PDF export is generated from current trusted records and labels its
absence of hours when no authoritative duration total exists. The resume JSON
contains verified skills, reviewed projects, completion records, and
certificates; it does not manufacture employment history.

## Deliberate limitations

- A certificate is a platform completion credential, not an accredited award
  or a job-readiness guarantee.
- QR payload rendering, branded certificate artwork, certificate revocation
  administration, and multi-template printable resume layouts are not yet
  available. The verification URL is exposed as QR-ready data.
- Public portfolio rendering is API-first. The learner workspace exposes its
  public URL, while a dedicated unauthenticated branded portfolio page remains
  future work.
- University/company reports currently expose verified aggregate counts. They
  do not expose private learner analytics or create cross-organization views.
