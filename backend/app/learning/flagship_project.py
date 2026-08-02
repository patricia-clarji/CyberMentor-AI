from typing import Any

FLAGSHIP_PROJECT_VERSION = "soc-report-1.0.0"

FLAGSHIP_PROJECT: dict[str, Any] = {
    "stable_key": "junior-soc-incident-escalation-project",
    "publication_id": "course-4-project",
    "title": "Professional SOC Incident Escalation",
    "description": (
        "Produce a reproducible incident escalation from supplied or completed "
        "workplace-mission evidence. A human reviewer applies the published rubric."
    ),
    "milestones": [
        (
            "Problem and scope",
            "State the authorized scope, affected entities, business context, and question.",
        ),
        (
            "Evidence and reasoning",
            "Separate observations from inferences and compare plausible explanations.",
        ),
        (
            "Decision and response",
            "Recommend a proportionate defensive action with authority and verification.",
        ),
        (
            "Reflection",
            "Explain learning, limitations, rewarding work, and challenging work.",
        ),
    ],
    "criteria": [
        {
            "key": "problem-definition",
            "description": "Defines the problem, scope, affected entity, and business impact.",
            "weight": 0.2,
            "pass_standard": "All four elements are explicit and internally consistent.",
        },
        {
            "key": "evidence-reasoning",
            "description": "Separates direct evidence, inference, alternatives, and uncertainty.",
            "weight": 0.3,
            "pass_standard": "Claims are traceable and at least one alternative is considered.",
        },
        {
            "key": "defensive-response",
            "description": "Recommends authorized, proportionate containment and verification.",
            "weight": 0.2,
            "pass_standard": (
                "The response is scoped, safe, reversible where possible, and verified."
            ),
        },
        {
            "key": "documentation",
            "description": "Provides sufficient steps for another analyst to reproduce the work.",
            "weight": 0.15,
            "pass_standard": "Sources, sequence, decisions, and limitations are clear.",
        },
        {
            "key": "reflection",
            "description": "Documents learning, rewarding work, challenges, and next growth step.",
            "weight": 0.15,
            "pass_standard": "Reflection is specific to the completed work and identifies growth.",
        },
    ],
}
