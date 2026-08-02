# Threat model

Assets include identities, grades, notes, portfolio evidence, answer keys, AI credentials, organization data, and lab infrastructure. Principal trust boundaries are browser/API, API/database, API/AI provider, control plane/lab worker, and tenant/tenant.

| Threat                      | Required control                                                            | Current status                                             |
| --------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------- |
| XSS/content injection       | Escaped rendering, content schema, CSP, upload sanitation                   | React escaping and container CSP; CMS sanitation future    |
| IDOR/cross-tenant access    | Deny-by-default server authorization and tenant query constraints           | Future API work                                            |
| Answer extraction           | Never send keys to the client; audit and rate limit                         | Verified-only API grading; identity-backed attempts future |
| Prompt injection/tool abuse | Trusted-content boundaries, allowlisted tools, policy and output validation | Basic deterministic gate; live tools future                |
| Lab escape                  | Dedicated workers/microVMs, quotas, egress deny, teardown                   | Legacy simulations blocked; no executable runtime          |
| Secret exposure             | Server secret store, rotation, redaction                                    | `.env` ignored; no runtime secrets used                    |
| Privacy leakage             | Minimization, consent, retention/deletion, private portfolios               | Local demo/private default; server workflows future        |

Residual risks: keyword rules are bypassable, local progress can be modified, in-memory rate limits are single-process, web fonts make a third-party request, and the client provides no identity assurance. Never issue credentials from this demo or expose it as a hostile public lab service.
