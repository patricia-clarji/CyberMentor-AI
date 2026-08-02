# Learning Milestone Verification

## Automated verification

Verification commands for this milestone:

```powershell
cd backend
.venv\Scripts\pytest.exe
.venv\Scripts\python.exe -m mypy app --strict
.venv\Scripts\ruff.exe check app tests

cd ..
npm test
npm run typecheck
npm run lint
npm run validate-content
npm run build
```

The focused backend suite additionally verifies the ordered pathway contract, source metadata, deterministic partial credit, learner-payload answer isolation, enrollment, lesson resume, notes, bookmarks, practice persistence, idempotency, module completion, assessment retakes/history, evidence creation, bounded mastery, and cross-tenant isolation.

## Browser workflow

The browser check must use a development-only learner and verify:

1. sign in and open the real dashboard;
2. inspect the adaptive roadmap;
3. enroll in the Junior SOC pathway;
4. open the first module and lesson;
5. save a note and bookmark;
6. complete the lesson, practice, and module assessment;
7. inspect feedback, skill evidence, and the new recommendation reason;
8. restart the services and confirm the same state;
9. repeat the route check on a mobile viewport;
10. inspect console and required network requests;
11. confirm a second learner cannot read the first learner's records.

Exact execution results and any environmental limitation are recorded here after the final verification run.

## Results on 2026-07-30

- Backend tests: **35 passed** (`.venv\Scripts\pytest.exe -q`).
- Backend strict type check: **passed**, 56 source files, zero issues.
- Backend Ruff lint: **passed**.
- JavaScript/TypeScript regression runner: **13 files passed, 113 tests passed**.
- Frontend type check: **passed**.
- ESLint: **passed**.
- Content validation tests: **11 passed**.
- Published content validation: **488 publications**, zero errors, zero warnings.
- Production build: **passed**, 1,840 modules transformed; JavaScript 345.36 kB (102.82 kB gzip), CSS 35.91 kB (8.58 kB gzip).

The running trusted API completed a development-learner flow with one enrollment, one completed lesson, one note, one bookmark, a passed deterministic practice, a 100% module assessment, three skill-evidence records, six reasoned recommendations, and the first module computed complete.

After stopping and restarting the local services, a read-only query of the same durable development database confirmed one enrollment, one lesson-progress record, one note, one bookmark, two activity attempts, and three skill-evidence records for that learner.

The automated cross-tenant API test passed: a second learner received a distinct attempt and could see only their own evidence.

## Browser limitation

Real-browser verification is **not passed**. The browser-control runtime reported that no in-app browser or Chrome browser was connected, so visual desktop/mobile inspection, browser-console inspection, and required-request inspection could not be executed.

During the restart check, the documented coordinated launcher completed preparation but exited before its services became ready. Starting the three existing services directly produced listening ports, but the Windows environment then stopped returning HTTP responses. Persistence was confirmed from the durable database, but the post-restart browser/API resume step remains unverified. The verification services were stopped cleanly afterward.

## Known limits

- Eight required lessons provide one coherent foundational pass, not the final 18-course/360-lesson academy target.
- External accountable review remains pending.
- Time-on-task is not inferred; only explicit persisted activity timestamps are recorded.
- The existing wider-catalogue checks and labs remain on the Node content service; the trusted engine is authoritative for the new Junior SOC pathway.
- No production provider, hosting, public deployment, or executable hostile-workload lab is claimed.
