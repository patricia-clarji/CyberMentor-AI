# Instructor portal

Routes under `/instructor` use the shared authenticated shell and active-organization switcher.

The dashboard reports active cohorts, active learner enrolments, pending review workload, active assignments, and assignment completion rate from persisted organization rows. Empty denominators render as insufficient data.

Instructors can view assigned organization cohorts, rosters, pinned curriculum versions, authorized learner skill estimates and completion records, assignments, and review queues. Learner details explicitly exclude private notes, Sentinel conversations, and activity outside the organization.

Assignment submissions preserve revisions through parent links. Human reviews record learner, reviewer, content version, timestamps, rubric scores, feedback, decision, revision count, and state history. Original learner response bodies are never changed by review. AI suggestions are stored separately and cannot create a final decision.

Review states implemented for assignments are pending, in review, revision requested, resubmitted, approved, rejected, and cancelled-compatible storage. Project review continues to use the existing published project rubric and human reviewer evidence flow.
