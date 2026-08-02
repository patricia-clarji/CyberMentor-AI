from typing import Any

SOC_PROFILE_VERSION = "junior-soc-1.0.0"

SKILLS: list[tuple[str, str, str, list[str], float]] = [
    (
        "security-foundations",
        "Security foundations",
        "Core defensive principles and evidence-based reasoning.",
        [],
        0.8,
    ),
    (
        "tcp-ip-reasoning",
        "TCP/IP reasoning",
        "Interpret security-relevant transport and network behavior.",
        ["security-foundations"],
        0.7,
    ),
    (
        "dns",
        "DNS evidence",
        "Interpret DNS records and resolution evidence in investigations.",
        ["tcp-ip-reasoning"],
        0.7,
    ),
    (
        "http",
        "HTTP evidence",
        "Interpret HTTP requests, responses, and security-relevant metadata.",
        ["tcp-ip-reasoning"],
        0.6,
    ),
    (
        "linux-navigation",
        "Linux navigation",
        "Navigate an authorized Linux host and locate relevant evidence.",
        ["security-foundations"],
        0.6,
    ),
    (
        "linux-permissions",
        "Linux permissions",
        "Interpret Linux ownership and access controls.",
        ["linux-navigation"],
        0.5,
    ),
    (
        "linux-processes",
        "Linux processes",
        "Inspect Linux process evidence and parent-child relationships.",
        ["linux-navigation"],
        0.7,
    ),
    (
        "linux-logs",
        "Linux logs",
        "Locate and interpret Linux authentication and service logs.",
        ["linux-navigation"],
        0.8,
    ),
    (
        "windows-processes",
        "Windows processes",
        "Interpret Windows process creation and ancestry evidence.",
        ["security-foundations"],
        0.7,
    ),
    (
        "windows-events",
        "Windows events",
        "Interpret security-relevant Windows event records.",
        ["security-foundations"],
        0.8,
    ),
    (
        "authentication-events",
        "Authentication events",
        "Correlate successful and failed authentication evidence.",
        ["linux-logs", "windows-events"],
        0.9,
    ),
    (
        "email-analysis",
        "Email analysis",
        "Analyze headers, links, sender alignment, and attachment metadata.",
        ["dns", "http"],
        0.9,
    ),
    (
        "ioc-analysis",
        "Indicator analysis",
        "Evaluate indicators with context, confidence, and source provenance.",
        ["dns", "http"],
        0.8,
    ),
    (
        "siem-query-reasoning",
        "SIEM query reasoning",
        "Form and interpret scoped queries without relying on one vendor syntax.",
        ["authentication-events"],
        0.9,
    ),
    (
        "alert-triage",
        "Alert triage",
        "Prioritize alerts using evidence, asset context, and business impact.",
        ["security-foundations"],
        1.0,
    ),
    (
        "evidence-preservation",
        "Evidence preservation",
        "Collect and document evidence while preserving integrity and provenance.",
        ["security-foundations"],
        0.9,
    ),
    (
        "incident-severity",
        "Incident severity",
        "Assign defensible severity from scope, confidence, and impact.",
        ["alert-triage"],
        1.0,
    ),
    (
        "escalation-writing",
        "Escalation writing",
        "Escalate clearly with known facts, uncertainty, impact, and next actions.",
        ["incident-severity"],
        1.0,
    ),
    (
        "incident-reporting",
        "Incident reporting",
        "Produce a reproducible professional incident report.",
        ["evidence-preservation", "escalation-writing"],
        1.0,
    ),
]

DIAGNOSTIC_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "soc-diag-network-1",
        "skill": "tcp-ip-reasoning",
        "type": "single_choice",
        "prompt": (
            "A host sends TCP SYN packets to several service ports and receives no replies. "
            "Which conclusion is best supported?"
        ),
        "options": [
            "The host is definitely compromised",
            "Connection attempts occurred; the available evidence does not prove compromise",
            "Every destination service accepted a connection",
            "DNS resolution failed",
        ],
        "answer": {"choice": 1},
        "explanation": (
            "A SYN without a completed handshake supports an attempted connection, "
            "not compromise or acceptance."
        ),
    },
    {
        "key": "soc-diag-dns-1",
        "skill": "dns",
        "type": "ordering",
        "prompt": "Order the investigation steps from least assumptive to most conclusive.",
        "options": [
            "Compare the domain with approved business services",
            "Inspect the DNS query and response",
            "Correlate the resolved address with endpoint and proxy events",
        ],
        "answer": {"order": [1, 0, 2]},
        "explanation": (
            "Start with the raw resolution evidence, add business context, "
            "then correlate independent telemetry."
        ),
    },
    {
        "key": "soc-diag-linux-1",
        "skill": "linux-logs",
        "type": "command_interpretation",
        "prompt": (
            "Which command safely reads recent SSH service logs on a systemd host "
            "without changing the host?"
        ),
        "options": [
            "journalctl -u ssh --since '1 hour ago'",
            "chmod 777 /var/log/auth.log",
            "rm /var/log/auth.log",
            "systemctl disable ssh",
        ],
        "answer": {"choice": 0},
        "explanation": (
            "journalctl reads the scoped service journal; the other choices modify "
            "or destroy system state."
        ),
    },
    {
        "key": "soc-diag-linux-2",
        "skill": "linux-processes",
        "type": "log_interpretation",
        "prompt": (
            "Process evidence shows parent=mail-reader child=powershell command='-enc ...'. "
            "What is the most appropriate first action?"
        ),
        "options": [
            "Declare ransomware with certainty",
            "Preserve the process command and ancestry, then correlate endpoint and email evidence",
            "Delete all mail immediately",
            "Ignore it because PowerShell is legitimate software",
        ],
        "answer": {"choice": 1},
        "explanation": (
            "The ancestry is suspicious but requires preservation and correlation "
            "before a final classification."
        ),
    },
    {
        "key": "soc-diag-windows-1",
        "skill": "windows-events",
        "type": "multiple_choice",
        "prompt": "Which two fields most directly help correlate a Windows process-creation event?",
        "options": ["Process ID", "Parent process ID", "Desktop wallpaper", "Screen brightness"],
        "answer": {"choices": [0, 1]},
        "explanation": "Process and parent identifiers support process-tree correlation.",
    },
    {
        "key": "soc-diag-auth-1",
        "skill": "authentication-events",
        "type": "log_interpretation",
        "prompt": (
            "Five failed MFA events follow a successful sign-in from a new address. "
            "What should the analyst do first?"
        ),
        "options": [
            "Close the alert because the sign-in succeeded",
            "Correlate user, source, device, and MFA events before deciding",
            "Publish the source address as malicious",
            "Reset every company account",
        ],
        "answer": {"choice": 1},
        "explanation": (
            "Correlation establishes scope and confidence without prematurely "
            "closing or overreacting."
        ),
    },
    {
        "key": "soc-diag-email-1",
        "skill": "email-analysis",
        "type": "multiple_choice",
        "prompt": "Which two observations are useful phishing evidence?",
        "options": [
            "Return-Path conflicts with the claimed sender",
            "The visible link text differs from the destination domain",
            "The message uses a common font",
            "The recipient has an inbox",
        ],
        "answer": {"choices": [0, 1]},
        "explanation": (
            "Sender-path and destination mismatches are evidence; generic presentation "
            "facts are not."
        ),
    },
    {
        "key": "soc-diag-siem-1",
        "skill": "siem-query-reasoning",
        "type": "scenario_decision",
        "prompt": (
            "A broad query returns 80,000 events. Which refinement best tests "
            "a phishing endpoint hypothesis?"
        ),
        "options": [
            "Remove the time window",
            "Filter by the reported user, endpoint, and incident time range",
            "Search every tenant",
            "Select one random event",
        ],
        "answer": {"choice": 1},
        "explanation": (
            "A scoped subject, asset, and time window tests the hypothesis while "
            "reducing unrelated noise."
        ),
    },
    {
        "key": "soc-diag-triage-1",
        "skill": "alert-triage",
        "type": "scenario_decision",
        "prompt": (
            "An alert affects a finance workstation and has corroborating email and "
            "process evidence. What raises priority most defensibly?"
        ),
        "options": [
            "The alert title sounds severe",
            "Corroborated evidence plus sensitive asset and business impact",
            "The analyst is busy",
            "The event occurred on a Tuesday",
        ],
        "answer": {"choice": 1},
        "explanation": (
            "Priority follows evidence, asset criticality, and impact rather than "
            "wording or unrelated context."
        ),
    },
    {
        "key": "soc-diag-preserve-1",
        "skill": "evidence-preservation",
        "type": "ordering",
        "prompt": "Order these evidence-handling actions.",
        "options": [
            "Record source, time, and acquisition method",
            "Acquire the authorized evidence",
            "Verify and record its integrity value",
        ],
        "answer": {"order": [0, 1, 2]},
        "explanation": (
            "Document provenance, acquire within authorization, then verify and record integrity."
        ),
    },
    {
        "key": "soc-diag-severity-1",
        "skill": "incident-severity",
        "type": "scenario_decision",
        "prompt": (
            "Evidence suggests one endpoint executed a suspicious attachment, "
            "but impact is not confirmed. Which classification is most defensible?"
        ),
        "options": [
            "Confirmed enterprise-wide breach",
            (
                "Suspected endpoint compromise requiring escalation; "
                "scope and impact still under investigation"
            ),
            "False positive",
            "No incident because impact is unknown",
        ],
        "answer": {"choice": 1},
        "explanation": (
            "The classification states the supported concern while preserving "
            "uncertainty about scope and impact."
        ),
    },
    {
        "key": "soc-diag-report-1",
        "skill": "escalation-writing",
        "type": "scenario_decision",
        "prompt": "Which escalation sentence is strongest?",
        "options": [
            "Everything is hacked",
            (
                "User device FIN-14 executed a suspicious encoded child process after "
                "opening the reported attachment; isolation approval is requested while "
                "authentication scope is checked"
            ),
            "This looks bad",
            "Please fix ASAP",
        ],
        "answer": {"choice": 1},
        "explanation": (
            "The statement identifies evidence, asset, sequence, requested action, "
            "and remaining investigation."
        ),
    },
]

ROADMAP_ACTIVITIES: list[dict[str, Any]] = [
    {
        "id": "soc-foundations-course",
        "title": "SOC Analyst Foundations",
        "type": "course",
        "skills": ["security-foundations", "alert-triage"],
        "difficulty": "foundation",
        "minutes": 240,
    },
    {
        "id": "linux-investigation-refresh",
        "title": "Linux Investigation Refresh",
        "type": "guided_practice",
        "skills": ["linux-navigation", "linux-processes", "linux-logs"],
        "difficulty": "guided",
        "minutes": 45,
    },
    {
        "id": "linux-through-network-evidence",
        "title": "Linux Evidence Through Network Reasoning",
        "type": "worked_example",
        "skills": ["tcp-ip-reasoning", "linux-logs"],
        "difficulty": "guided",
        "minutes": 25,
    },
    {
        "id": "advanced-network-correlation",
        "title": "Advanced Network Correlation",
        "type": "independent_practice",
        "skills": ["tcp-ip-reasoning", "dns", "http"],
        "difficulty": "advanced",
        "minutes": 40,
    },
    {
        "id": "phishing-triage-practice",
        "title": "Phishing Triage Practice",
        "type": "guided_practice",
        "skills": ["email-analysis", "ioc-analysis", "alert-triage"],
        "difficulty": "guided",
        "minutes": 50,
    },
    {
        "id": "flagship-phishing-endpoint-mission",
        "title": "Cedars Health Phishing Investigation",
        "type": "mission",
        "skills": [
            "email-analysis",
            "windows-processes",
            "authentication-events",
            "incident-severity",
            "escalation-writing",
        ],
        "difficulty": "standard",
        "minutes": 90,
    },
]
