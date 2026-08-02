# Operations runbook

Development start: `npm install` then `npm run dev`; open `http://localhost:5173`. Verified production-style local start: `npm run build` then `npm start`; open `http://127.0.0.1:8080`. Health is `/healthz` and readiness is `/readyz`. Container rollback redeploys the previous immutable image; content rollback uses the separately authorized immutable-version command documented in the ingestion pipeline.

Before commercial release, add relational backups and restore drills, expand/contract migrations, structured logs and request IDs, SLO dashboards, dead-letter handling, AI circuit breakers, secret management, email controls, and on-call procedures. Lab cleanup must be idempotent, time-bounded, observable, and run from an isolated plane. AI outages switch to demo mode without blocking core learning.
