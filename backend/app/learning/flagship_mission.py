from typing import Any

FLAGSHIP_MISSION_VERSION = "harbor-light-1.0.0"
EVALUATOR_VERSION = "soc-mission-evaluator-1.0.0"

# This scenario is original, synthetic training material. Names, domains, users,
# addresses, and telemetry are fictional and are not intended to identify a real entity.
FLAGSHIP_MISSION: dict[str, Any] = {
    "stable_key": "harbor-light-phishing-investigation",
    "title": "Harbor Light: Phishing-to-Endpoint Investigation",
    "description": (
        "Investigate a reported message, correlate email, endpoint, authentication, "
        "and DNS evidence, then write a defensible SOC escalation."
    ),
    "safety_classification": "defensive-synthetic-local-only",
    "fictional_organization": "Cedar Harbor Cooperative",
    "business_context": (
        "Cedar Harbor Cooperative is a fictional regional logistics organization. "
        "Its finance team is closing the monthly books when a user reports an unusual "
        "document-sharing message. Learners work only with supplied synthetic evidence."
    ),
    "briefing": (
        "You are the junior analyst on duty. Determine what the evidence supports, "
        "preserve uncertainty, recommend proportionate containment, and prepare an "
        "escalation another analyst can reproduce."
    ),
    "stages": [
        {
            "key": "email-intake",
            "title": "Triage the reported message",
            "objective": "Identify defensible email indicators without assuming compromise.",
            "skill": "email-analysis",
            "required_action": "flag_sender_mismatch",
            "resources": [
                {
                    "id": "email-header-01",
                    "label": "Message header",
                    "classification": "synthetic-email",
                    "content": (
                        "From: Cedar Files <share@cedar-files.example>\n"
                        "Return-Path: notices@cedar-share.example\n"
                        "To: maya.saleh@cedar-harbor.example\n"
                        "Subject: Updated port invoice\n"
                        "Received: from 198.51.100.42 by mail.cedar-harbor.example"
                    ),
                }
            ],
            "actions": [
                {"id": "flag_sender_mismatch", "label": "Record the sender-path mismatch"},
                {"id": "declare_breach", "label": "Declare an organization-wide breach"},
                {"id": "delete_message", "label": "Delete the message without preserving it"},
            ],
            "hints": [
                "Separate an observation from a conclusion.",
                "Compare the visible sender with the envelope sender.",
                "The Return-Path and From domains do not match.",
                "Record the mismatch as evidence; do not call it proof of compromise.",
                "Open the header, compare From and Return-Path, then record the mismatch.",
            ],
        },
        {
            "key": "endpoint-correlation",
            "title": "Correlate endpoint activity",
            "objective": (
                "Connect the reported message to process evidence on the recipient device."
            ),
            "skill": "linux-processes",
            "required_action": "preserve_process_chain",
            "resources": [
                {
                    "id": "endpoint-event-07",
                    "label": "Endpoint process event",
                    "classification": "synthetic-edr",
                    "content": (
                        "2026-06-14T09:18:31Z host=FIN-14 user=maya.saleh "
                        "parent=mail-reader.exe child=powershell.exe "
                        'command="powershell.exe -enc SQBFAFgA..." disposition=observed'
                    ),
                }
            ],
            "actions": [
                {
                    "id": "preserve_process_chain",
                    "label": "Preserve the command and parent-child process chain",
                },
                {"id": "wipe_host", "label": "Wipe the workstation immediately"},
                {
                    "id": "ignore_powershell",
                    "label": "Ignore the event because PowerShell is valid",
                },
            ],
            "hints": [
                "Legitimate tools can appear in suspicious sequences.",
                "Focus on ancestry, command context, and timing.",
                "Preserve the encoded command and its parent-child relationship.",
                "Correlate before making a final malware classification.",
                "Record mail-reader.exe → powershell.exe and preserve the encoded command.",
            ],
        },
        {
            "key": "identity-scope",
            "title": "Check identity scope",
            "objective": "Use authentication evidence to bound the incident without overclaiming.",
            "skill": "authentication-events",
            "required_action": "correlate_identity_events",
            "resources": [
                {
                    "id": "identity-events-03",
                    "label": "Authentication events",
                    "classification": "synthetic-identity",
                    "content": (
                        "09:20Z success user=maya.saleh source=203.0.113.77 device=unknown\n"
                        "09:22Z mfa_denied user=maya.saleh source=203.0.113.77 count=3\n"
                        "09:24Z success user=maya.saleh source=10.20.4.18 device=FIN-14"
                    ),
                }
            ],
            "actions": [
                {
                    "id": "correlate_identity_events",
                    "label": "Correlate source, device, user, and MFA sequence",
                },
                {"id": "reset_all_accounts", "label": "Reset every organization account"},
                {"id": "close_identity_alert", "label": "Close because one sign-in succeeded"},
            ],
            "hints": [
                "A success and later denials can coexist.",
                "Compare source, device, user, and time.",
                "The external success and MFA denials need correlation with FIN-14.",
                "Scope the affected identity before recommending broad action.",
                "Record the external source sequence and compare it with the known FIN-14 event.",
            ],
        },
        {
            "key": "decision-escalation",
            "title": "Choose a proportionate response",
            "objective": "Escalate supported risk and request a proportionate defensive action.",
            "skill": "escalation-writing",
            "required_action": "request_scoped_isolation",
            "resources": [
                {
                    "id": "asset-context-02",
                    "label": "Asset and business context",
                    "classification": "synthetic-cmdb",
                    "content": (
                        "FIN-14 owner=maya.saleh department=Finance criticality=high "
                        "month_end_close=true isolation_authority=incident_commander"
                    ),
                }
            ],
            "actions": [
                {
                    "id": "request_scoped_isolation",
                    "label": "Request approval to isolate FIN-14 and preserve evidence",
                },
                {"id": "attack_external_host", "label": "Attack the external source"},
                {"id": "publish_ioc", "label": "Publicly attribute the source as malicious"},
            ],
            "hints": [
                "Match the response to evidence, impact, and authority.",
                "The affected finance asset is important, but scope remains uncertain.",
                "Request a reversible, scoped defensive action.",
                "Isolation requires approval and should preserve evidence.",
                "Request authorized isolation of FIN-14 while identity scope is investigated.",
            ],
        },
    ],
}
