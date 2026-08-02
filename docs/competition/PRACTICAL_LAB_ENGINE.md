# Practical lab engine

CyberMentor's trusted practical lab engine runs authenticated, tenant-scoped,
synthetic cybersecurity scenarios. It never passes learner input to a host
shell. The terminal interpreter operates only on the virtual files, processes,
and connections stored with the lab session.

## Authoring contract

Lab catalogs may be authored as JSON, YAML, or YML and loaded through
`app.learning.lab_catalog.load_lab_document`. The production catalog is
`content/labs/soc-practical-labs.json`; its reusable JSON Schema is
`content/schema/lab.schema.json`.

Every lab defines:

- stable ID, semantic version, title, type, category, difficulty, duration,
  prerequisites, and linked skills;
- objectives, stages, optional or bonus work, scenario, learner instructions,
  tools, checkpoints, evidence requirements, private validation, progressive
  hints, reflection questions, completion rules, generated evidence, and
  portfolio eligibility;
- a scenario-specific virtual filesystem with file contents, modes, owners,
  groups, synthetic process records, and synthetic connection records;
- required command paths, accepted alternative paths, submission checks, and
  an expert solution revealed only after completion.

The content pipeline rejects missing contract fields, duplicate or malformed
IDs, unknown skills, unsupported terminal commands, relative virtual file
paths, and hint ladders that do not contain levels one through five.

## Runtime boundaries

Supported commands are `pwd`, `ls`, `cd`, `cat`, `grep`, `find`, `ps`,
`netstat`, `ss`, `journalctl`, `tail`, `head`, `chmod`, and `chown`.
Shell operators, expansion, pipes, and redirection are rejected. Unsupported
commands return a deterministic simulated-shell error.

The server owns all validation, grading, hints, state changes, completion
records, and portfolio artifacts. Browser values are treated only as learner
input. Active sessions persist in the database and resume for the same user,
organization, and lab.

## Assessment and replay

Submissions receive separate bands for correctness, efficiency, evidence
quality, independence, decision quality, and report quality. A failed
submission records partial success and leaves the lab active for recovery.
Successful completion:

1. finalizes required objectives;
2. records practical skill evidence and rebuilds adaptive recommendations;
3. creates a versioned private portfolio artifact;
4. issues a scoped practical-lab completion record; and
5. exposes a replay containing actions, mistakes, corrections, hints, elapsed
   time, alternative paths, and the expert solution.

This evidence verifies only completion of the named synthetic lab. It is not an
industry certification or a claim of job readiness.
