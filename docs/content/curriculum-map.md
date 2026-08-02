# Curriculum map

`src/data/courses.ts` contains a legacy planning inventory: 12 course shells, 48 module shells, 144 repeated lesson templates, 12 short project placeholders, and 10 fixed-evidence exercise prototypes. None is approved curriculum. The learner application filters those records out and accepts only current publications from `content/published/` through the server API.

The publication manifest is currently empty. This is intentional: the repository has no enrolled human reviewers, and substantial independently researched course material must not be synthesized or approved by the application team or an LLM. The required technical, instructional, accessibility, licensing, safety-when-dual-use, and publication decisions therefore remain a production release blocker.

Five roadmap shells remain available for planning: Cybersecurity Beginner, SOC Analyst, Penetration Tester, Cloud Security Engineer, and AI Security Engineer. They do not prove the underlying curriculum is complete. Content is publishable only through the versioned workflow documented in [the ingestion pipeline](ingestion-pipeline.md).
