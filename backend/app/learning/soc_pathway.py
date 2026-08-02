# ruff: noqa: E501

from typing import Any

PATHWAY_ID = "junior-soc-analyst-pathway"
PATHWAY_VERSION = "1.0.0"
REVIEW_STATE = "internally-checked-pending-external-review"

SOURCES: dict[str, dict[str, str]] = {
    "nist-ir": {
        "publisher": "NIST",
        "title": "Computer Security Incident Handling Guide",
        "url": "https://csrc.nist.gov/pubs/sp/800/61/r2/final",
        "retrieved_at": "2026-07-30",
        "source_date": "2012-08",
    },
    "nist-logs": {
        "publisher": "NIST",
        "title": "Guide to Computer Security Log Management",
        "url": "https://csrc.nist.gov/pubs/sp/800/92/final",
        "retrieved_at": "2026-07-30",
        "source_date": "2006-09",
    },
    "cisa-phishing": {
        "publisher": "CISA",
        "title": "Recognize and Report Phishing",
        "url": "https://www.cisa.gov/secure-our-world/recognize-and-report-phishing",
        "retrieved_at": "2026-07-30",
        "source_date": "current web guidance",
    },
    "mitre": {
        "publisher": "MITRE",
        "title": "MITRE ATT&CK Enterprise Matrix",
        "url": "https://attack.mitre.org/matrices/enterprise/",
        "retrieved_at": "2026-07-30",
        "source_date": "current web release",
    },
    "ms-events": {
        "publisher": "Microsoft",
        "title": "Audit process creation",
        "url": "https://learn.microsoft.com/windows-server/identity/ad-ds/manage/component-updates/command-line-process-auditing",
        "retrieved_at": "2026-07-30",
        "source_date": "current web guidance",
    },
    "linux-journal": {
        "publisher": "freedesktop.org",
        "title": "journalctl manual",
        "url": "https://www.freedesktop.org/software/systemd/man/latest/journalctl.html",
        "retrieved_at": "2026-07-30",
        "source_date": "current manual",
    },
}


def lesson(
    lesson_id: str,
    title: str,
    minutes: int,
    skills: list[str],
    why: str,
    objectives: list[str],
    concept: str,
    evidence: str,
    worked_example: str,
    terms: dict[str, str],
    misconception: str,
    guided_practice: str,
    reflection: str,
    source_ids: list[str],
) -> dict[str, Any]:
    return {
        "id": lesson_id,
        "version": PATHWAY_VERSION,
        "title": title,
        "minutes": minutes,
        "review_state": REVIEW_STATE,
        "why_it_matters": why,
        "prerequisites": [],
        "objectives": objectives,
        "concept": concept,
        "worked_example": worked_example,
        "evidence_artifact": evidence,
        "terminology": [{"term": key, "definition": value} for key, value in terms.items()],
        "common_misconception": misconception,
        "guided_practice": guided_practice,
        "reflection_question": reflection,
        "practical_relevance": (
            "Use the distinction in a triage note: separate what the evidence shows, "
            "what remains a hypothesis, and which safe action would reduce uncertainty."
        ),
        "linked_skills": skills,
        "references": [SOURCES[source_id] for source_id in source_ids],
    }


MODULES: list[dict[str, Any]] = [
    {
        "id": "soc-01-foundations",
        "title": "SOC foundations and evidence reasoning",
        "purpose": "Establish defensible SOC decisions without turning alerts into unsupported conclusions.",
        "prerequisite_skills": [],
        "objectives": [
            "Distinguish event, alert, investigation, and incident.",
            "State observations separately from hypotheses.",
        ],
        "linked_skills": ["security-foundations", "alert-triage"],
        "estimated_minutes": 70,
        "lessons": [
            lesson(
                "soc-01-l1",
                "From events to defensible SOC decisions",
                35,
                ["security-foundations", "alert-triage"],
                "A SOC analyst is judged by the quality of the decision and its evidence, not by how alarming an alert title sounds.",
                [
                    "Classify a record as an event, alert, investigation, or incident.",
                    "Write an evidence statement that preserves uncertainty.",
                ],
                "An event is an observed record. A detection rule may turn one or more events into an alert. An analyst opens an investigation to test competing explanations. An incident is declared only when the available evidence and organizational criteria support that decision. Asset criticality and business impact affect priority, but they do not change what the raw evidence says.",
                "09:14:02Z auth success user=salma source=198.51.100.24 device=FIN-14; 09:16:44Z MFA denied user=salma source=198.51.100.24 count=5",
                "The analyst records: “A successful sign-in from a previously unseen source was followed by five denied MFA prompts for the same user. This supports suspicious authentication activity; device ownership and user intent are not yet confirmed.” The next step is to correlate device, identity, and user-report evidence.",
                {
                    "event": "A recorded occurrence from a system or service.",
                    "alert": "A signal created by detection logic for review.",
                    "hypothesis": "A testable explanation that is not yet a finding.",
                },
                "An alert is not proof of compromise. It is a prompt to inspect evidence under a defined process.",
                "Underline each direct observation in the synthetic authentication record, then write one hypothesis and one fact that would disprove it.",
                "What wording would you remove from a triage note if it implied certainty the evidence did not support?",
                ["nist-ir", "nist-logs"],
            )
        ],
        "practice": {
            "id": "soc-01-practice",
            "type": "scenario_decision",
            "title": "Classify the authentication signal",
            "scenario": "Use the synthetic FIN-14 sign-in and MFA records from the lesson.",
            "objective": "Choose the conclusion best supported by the evidence.",
            "prompt": "Which statement belongs in the initial triage record?",
            "options": [
                "FIN-14 is confirmed fully compromised.",
                "Suspicious authentication is supported; ownership and impact require correlation.",
                "The activity is harmless because one sign-in succeeded.",
            ],
            "private_answer": {"choice": 1},
            "feedback": "Preserve uncertainty and identify the correlation still required.",
            "linked_skills": ["alert-triage"],
        },
    },
    {
        "id": "soc-02-network-web",
        "title": "Networking, DNS, and HTTP evidence",
        "purpose": "Use network and web records to test an investigation hypothesis.",
        "prerequisite_skills": ["security-foundations"],
        "objectives": [
            "Interpret transport, DNS, and HTTP records together.",
            "Avoid treating one indicator as a verdict.",
        ],
        "linked_skills": ["tcp-ip-reasoning", "dns", "http", "ioc-analysis"],
        "estimated_minutes": 80,
        "lessons": [
            lesson(
                "soc-02-l1",
                "Correlating DNS and HTTP evidence",
                40,
                ["tcp-ip-reasoning", "dns", "http", "ioc-analysis"],
                "A domain lookup alone rarely proves what a process requested or whether content was delivered.",
                [
                    "Correlate DNS, connection, and HTTP timestamps.",
                    "Explain what an IOC match can and cannot establish.",
                ],
                "DNS evidence maps a queried name to a response at a point in time. Transport evidence records an attempted or completed connection. HTTP evidence can add host, method, path, status, referrer, and user-agent context. Correlation needs compatible time, subject, and asset fields. A threat-intelligence match raises a lead; its age, provenance, and local context determine its weight.",
                "10:02:11Z dns host=FIN-14 q=login-check.example answer=203.0.113.80; 10:02:13Z proxy host=FIN-14 method=GET host=login-check.example path=/update status=200 bytes=8421",
                "The two records share host, domain, and a two-second window. They support resolution followed by an HTTP response, but not execution. Endpoint process and file evidence is needed before claiming payload execution.",
                {
                    "DNS response": "A resolver answer valid for a bounded time.",
                    "HTTP status": "A server response category, not proof of safe content.",
                    "indicator": "An observable value used as a lead with context and provenance.",
                },
                "A 200 response proves only that the server returned a successful HTTP response; it does not prove the content executed.",
                "Build a three-row timeline from the evidence and add the endpoint event you would request next.",
                "When would the same domain match be weak evidence rather than strong evidence?",
                ["nist-logs", "mitre"],
            )
        ],
        "practice": {
            "id": "soc-02-practice",
            "type": "ordering",
            "title": "Build a correlation sequence",
            "scenario": "Synthetic FIN-14 DNS, proxy, and endpoint records are available.",
            "objective": "Order the least-assumptive investigation sequence.",
            "prompt": "Place the actions in order.",
            "options": [
                "Correlate the endpoint process at the matching time.",
                "Inspect the DNS response and TTL.",
                "Confirm the HTTP host, path, status, and asset.",
            ],
            "private_answer": {"order": [1, 2, 0]},
            "feedback": "Start from the raw resolution, add web context, then test execution.",
            "linked_skills": ["dns", "http"],
        },
    },
    {
        "id": "soc-03-operating-systems",
        "title": "Linux and Windows host evidence",
        "purpose": "Navigate host evidence safely and interpret processes, permissions, logs, and event records.",
        "prerequisite_skills": ["security-foundations", "tcp-ip-reasoning"],
        "objectives": [
            "Use read-only commands to inspect Linux evidence.",
            "Correlate Windows process creation with parent and user context.",
        ],
        "linked_skills": [
            "linux-navigation",
            "linux-permissions",
            "linux-processes",
            "linux-logs",
            "windows-processes",
            "windows-events",
        ],
        "estimated_minutes": 95,
        "lessons": [
            lesson(
                "soc-03-l1",
                "Read-only host investigation",
                50,
                [
                    "linux-navigation",
                    "linux-permissions",
                    "linux-processes",
                    "linux-logs",
                    "windows-processes",
                    "windows-events",
                ],
                "Host evidence can explain which user and process produced network activity, but careless commands can alter the evidence being investigated.",
                [
                    "Interpret process ancestry and permission metadata.",
                    "Select read-only Linux and Windows evidence sources.",
                ],
                "On Linux, pwd, ls -la, ps, stat, and journalctl can establish location, metadata, processes, and journal records without intentionally changing state. On Windows, process-creation auditing records executable, command line when enabled, account, process ID, and parent context. Event 4688 is evidence to correlate, not a maliciousness label. Record time zones and stable identifiers before building a cross-host timeline.",
                "Linux: uid=1004 process=curl parent=bash cmd='curl -o /tmp/u login-check.example/update'; Windows 4688: NewProcess=powershell.exe ParentProcess=OUTLOOK.EXE CommandLine='powershell -enc ...' User=SALMA",
                "Both chains connect a user-facing parent to a network-capable child. The Windows chain is suspicious because of the mail-client parent and encoded command. The Linux chain still needs user, purpose, hash, destination, and surrounding log context. Preserve both command lines exactly and do not execute them.",
                {
                    "process ancestry": "The parent-child relationship among executing processes.",
                    "permission mode": "Owner, group, and other access bits on a Unix-like system.",
                    "event 4688": "A Windows audit event for new process creation.",
                },
                "A legitimate binary name does not make every invocation benign; behavior and context matter.",
                "Choose the fields needed to join either process record to the DNS and HTTP evidence from the prior module.",
                "Which command or action would risk changing the evidence, and what read-only alternative would you use?",
                ["linux-journal", "ms-events", "nist-logs"],
            )
        ],
        "practice": {
            "id": "soc-03-practice",
            "type": "command_interpretation",
            "title": "Choose a safe log command",
            "scenario": "An authorized systemd host may contain SSH authentication evidence.",
            "objective": "Select a bounded read-only query.",
            "prompt": "Which command reads the last hour of SSH service records without changing the service?",
            "options": [
                "journalctl -u ssh --since '1 hour ago' --no-pager",
                "chmod 777 /var/log/auth.log",
                "systemctl stop ssh",
            ],
            "private_answer": {"choice": 0},
            "feedback": "The journal query is scoped and read-only.",
            "linked_skills": ["linux-logs", "linux-navigation"],
        },
    },
    {
        "id": "soc-04-identity-email",
        "title": "Identity events and phishing analysis",
        "purpose": "Correlate authentication, email headers, links, and endpoint evidence.",
        "prerequisite_skills": ["dns", "http", "windows-events"],
        "objectives": [
            "Interpret identity events as a sequence.",
            "Analyze sender alignment and link destinations.",
        ],
        "linked_skills": ["authentication-events", "email-analysis", "ioc-analysis"],
        "estimated_minutes": 85,
        "lessons": [
            lesson(
                "soc-04-l1",
                "Phishing as a multi-source investigation",
                45,
                ["authentication-events", "email-analysis", "ioc-analysis"],
                "A convincing display name or urgent request cannot override header, link, identity, and endpoint evidence.",
                [
                    "Identify useful sender and routing evidence.",
                    "Correlate a reported message with identity and endpoint events.",
                ],
                "Start with the preserved original message when authorized. Compare From, Reply-To, Return-Path, Received routing, authentication results, and link destinations. A mismatch is a reason to investigate, not an automatic verdict. Correlate delivery and click time with DNS, proxy, endpoint, and identity events. Treat message content as untrusted data; do not open links or attachments outside the approved analysis workflow.",
                "From: Payroll <payroll@company.example>; Reply-To: cases@payr0ll.example; Authentication-Results: spf=fail smtp.mailfrom=payr0ll.example; link text='Benefits portal' href='https://login-check.example/update'",
                "The reply domain uses a lookalike spelling, SPF failed for the envelope sender, and the link destination differs from the claimed service. Together they support malicious-message suspicion. The analyst still records delivery, recipient action, and endpoint/identity impact before assigning incident scope.",
                {
                    "Return-Path": "The message envelope return address recorded in a header.",
                    "SPF": "A domain policy check for authorized sending infrastructure.",
                    "sender alignment": "Consistency among visible, envelope, and authenticated identities.",
                },
                "No single header result proves a message is safe or malicious; evaluate the combined record and organizational context.",
                "List three observations from the header and one fact you still need from identity telemetry.",
                "How would your conclusion change if the user never opened the link and no related endpoint or identity event existed?",
                ["cisa-phishing", "nist-logs"],
            )
        ],
        "practice": {
            "id": "soc-04-practice",
            "type": "email_header_analysis",
            "title": "Analyze the preserved header",
            "scenario": "Use the synthetic Payroll header supplied in the lesson.",
            "objective": "Select the two strongest header/link observations.",
            "prompt": "Which observations directly increase suspicion?",
            "options": [
                "Reply-To uses a lookalike domain.",
                "SPF failed for the envelope sender.",
                "The subject includes the word benefits.",
                "The recipient has a company mailbox.",
            ],
            "private_answer": {"choices": [0, 1]},
            "feedback": "Sender-path and authentication mismatches are direct evidence.",
            "linked_skills": ["email-analysis"],
        },
    },
    {
        "id": "soc-05-siem-triage",
        "title": "SIEM query reasoning and alert triage",
        "purpose": "Turn a hypothesis into a bounded query and prioritize the resulting evidence.",
        "prerequisite_skills": ["authentication-events", "linux-logs", "windows-events"],
        "objectives": [
            "Write a vendor-neutral scoped query plan.",
            "Prioritize using confidence, asset value, scope, and impact.",
        ],
        "linked_skills": ["siem-query-reasoning", "alert-triage", "incident-severity"],
        "estimated_minutes": 85,
        "lessons": [
            lesson(
                "soc-05-l1",
                "Queries that test a hypothesis",
                45,
                ["siem-query-reasoning", "alert-triage", "incident-severity"],
                "A broad search can produce volume without answering the investigation question.",
                [
                    "Define subject, time, data source, and expected fields before querying.",
                    "Explain a severity decision from evidence and impact.",
                ],
                "Begin with a question such as: did user Salma’s FIN-14 endpoint contact the reported domain and then create suspicious authentication activity? Define a UTC window, user and host identifiers, the necessary DNS/proxy/endpoint/identity sources, and the fields needed to correlate. Expand the window or entities only when the results justify it. Severity combines supported likelihood, affected asset, current scope, and plausible impact; uncertainty must remain visible.",
                "Query plan: time 09:45–10:30Z; entities user=salma, host=FIN-14, domain=login-check.example; sources=dns, proxy, endpoint, identity; return timestamp, host, user, process, destination, result",
                "The query yields a DNS lookup, successful download, encoded PowerShell child of Outlook, and a new-source sign-in. Corroboration and a finance asset justify urgent escalation, while the current scope remains one endpoint and one user until broader evidence appears.",
                {
                    "query scope": "The bounded time, entities, sources, and fields searched.",
                    "corroboration": "Independent evidence supporting the same explanation.",
                    "severity": "A defensible priority based on likelihood and impact.",
                },
                "More events are not automatically better evidence; relevance and independent corroboration matter.",
                "Remove one source from the query plan and explain which claim can no longer be supported.",
                "What evidence would justify expanding the search from one user to the whole organization?",
                ["nist-logs", "nist-ir"],
            )
        ],
        "practice": {
            "id": "soc-05-practice",
            "type": "log_interpretation",
            "title": "Interpret a scoped SIEM result",
            "scenario": "The scoped search returned DNS, proxy, endpoint, and identity records for FIN-14.",
            "objective": "Choose the next defensible action.",
            "prompt": "What should the analyst do next?",
            "options": [
                "Escalate suspected endpoint and identity compromise with the supported scope and request containment approval.",
                "Declare every company endpoint compromised.",
                "Close the alert because PowerShell is installed by default.",
            ],
            "private_answer": {"choice": 0},
            "feedback": "Escalate the supported concern while keeping the known scope explicit.",
            "linked_skills": ["siem-query-reasoning", "alert-triage"],
        },
    },
    {
        "id": "soc-06-preserve-escalate",
        "title": "Evidence preservation, severity, and escalation",
        "purpose": "Preserve authorized evidence and communicate a proportionate response.",
        "prerequisite_skills": ["alert-triage", "ioc-analysis"],
        "objectives": [
            "Record provenance and integrity for acquired evidence.",
            "Write an escalation with facts, uncertainty, impact, and requested action.",
        ],
        "linked_skills": ["evidence-preservation", "incident-severity", "escalation-writing"],
        "estimated_minutes": 85,
        "lessons": [
            lesson(
                "soc-06-l1",
                "Preserve first, then escalate clearly",
                45,
                ["evidence-preservation", "incident-severity", "escalation-writing"],
                "An escalation that cannot be traced back to preserved evidence is difficult to verify or act on.",
                [
                    "Describe source, acquisition, time, custody, and integrity.",
                    "Request a proportionate action without overstating scope.",
                ],
                "Work within authorization and record the original source, collector, UTC time, acquisition method, destination, access history, and an integrity value where appropriate. Preserve originals and analyze controlled copies. An escalation should state the supported classification, affected identities/assets, concise timeline, evidence identifiers, uncertainty, impact, actions already taken, and the decision requested from the authorized responder.",
                "Artifact CM-EV-004: exported endpoint event bundle from FIN-14 EDR at 10:42Z by analyst trainee; SHA-256 recorded; original read-only export retained; working copy CM-EV-004-W1",
                "A useful escalation says: “Suspected compromise of FIN-14 and Salma’s account is supported by message, proxy, process, and identity records. Current evidence does not establish lateral movement. Request approval to isolate FIN-14 and revoke Salma’s active sessions while the scoped hunt continues.”",
                {
                    "provenance": "The traceable origin and handling history of evidence.",
                    "integrity value": "A digest used to detect later changes to a digital artifact.",
                    "requested action": "The specific authorized decision needed from the recipient.",
                },
                "Hashing a file does not prove it was collected correctly; provenance and authorized handling are also required.",
                "Rewrite an alarmist escalation so it states one supported scope, one uncertainty, and one requested action.",
                "Which evidence-handling detail would another analyst need to reproduce your result?",
                ["nist-ir"],
            )
        ],
        "practice": {
            "id": "soc-06-practice",
            "type": "short_written_response",
            "title": "Write a concise escalation",
            "scenario": "FIN-14 has corroborated email, proxy, process, and identity evidence; lateral movement is not established.",
            "objective": "Write a bounded escalation summary.",
            "prompt": "In 2–4 sentences, include the affected asset, supported concern, uncertainty, and requested action.",
            "private_answer": {
                "keywords": ["fin-14", "suspected", "lateral", "isolate"],
                "minimum_matches": 3,
                "minimum_length": 80,
            },
            "feedback": "Name the asset, supported concern, remaining uncertainty, and requested authorization.",
            "linked_skills": ["escalation-writing", "incident-severity"],
        },
    },
    {
        "id": "soc-07-reporting",
        "title": "Incident reporting and reproducibility",
        "purpose": "Transform investigation records into a reproducible incident report.",
        "prerequisite_skills": ["evidence-preservation", "escalation-writing"],
        "objectives": [
            "Build a fact-based incident timeline.",
            "Separate findings, limitations, decisions, and follow-up actions.",
        ],
        "linked_skills": ["incident-reporting", "evidence-preservation", "escalation-writing"],
        "estimated_minutes": 80,
        "lessons": [
            lesson(
                "soc-07-l1",
                "A report another analyst can reproduce",
                45,
                ["incident-reporting", "evidence-preservation", "escalation-writing"],
                "A report is professional evidence only when its claims can be traced to artifacts and repeated.",
                [
                    "Link timeline claims to evidence identifiers.",
                    "Document limitations and rejected alternatives.",
                ],
                "A defensible report includes scope and authorization, executive summary, sources and method, normalized timeline, findings with evidence references, alternative explanations, confidence and limitations, response decisions, current status, and follow-up. Keep direct observations distinct from interpretation. Record query parameters and content versions so another analyst can reproduce the result without receiving a hidden answer key.",
                "10:02:11Z CM-EV-001 DNS resolution; 10:02:13Z CM-EV-002 HTTP 200; 10:03:04Z CM-EV-003 Outlook→PowerShell process; 10:14:02Z CM-EV-005 new-source sign-in",
                "The report links each timestamp to an artifact and explains the correlation fields. It rejects “DNS only” as insufficient, notes that the process chain and identity event add independent support, and states that no evidence source in the authorized dataset establishes lateral movement.",
                {
                    "finding": "A conclusion supported by cited investigation evidence.",
                    "limitation": "A boundary on what the available method or data can establish.",
                    "reproducibility": "The ability to repeat the method and obtain comparable results.",
                },
                "A polished narrative without evidence references is not a reproducible report.",
                "For each timeline row, add the artifact ID, correlation fields, and the conclusion it supports.",
                "Which part of your conclusion is most sensitive to missing telemetry?",
                ["nist-ir", "nist-logs"],
            )
        ],
        "practice": {
            "id": "soc-07-practice",
            "type": "matching",
            "title": "Match claims to evidence",
            "scenario": "Four synthetic artifacts support different parts of the FIN-14 timeline.",
            "objective": "Match the claim sequence to its strongest artifacts.",
            "prompt": "Choose the correct evidence sequence: resolution, download, execution, identity activity.",
            "options": [
                "CM-EV-001, CM-EV-002, CM-EV-003, CM-EV-005",
                "CM-EV-005, CM-EV-003, CM-EV-002, CM-EV-001",
                "CM-EV-002, CM-EV-001, CM-EV-005, CM-EV-003",
            ],
            "private_answer": {"choice": 0},
            "feedback": "Each claim should point to the artifact that directly supports it.",
            "linked_skills": ["incident-reporting"],
        },
    },
    {
        "id": "soc-08-mission-readiness",
        "title": "Flagship mission preparation",
        "purpose": "Integrate evidence reasoning, triage, preservation, escalation, and reporting before the Harbor Light mission.",
        "prerequisite_skills": [
            "siem-query-reasoning",
            "evidence-preservation",
            "escalation-writing",
            "incident-reporting",
        ],
        "objectives": [
            "Plan a safe independent investigation.",
            "Recognize when evidence is insufficient and request the right next source.",
        ],
        "linked_skills": [
            "alert-triage",
            "siem-query-reasoning",
            "incident-severity",
            "incident-reporting",
        ],
        "estimated_minutes": 75,
        "lessons": [
            lesson(
                "soc-08-l1",
                "Mission readiness: decide, preserve, explain",
                40,
                [
                    "alert-triage",
                    "siem-query-reasoning",
                    "incident-severity",
                    "incident-reporting",
                ],
                "The flagship mission measures independent reasoning across evidence sources, not memorized vocabulary.",
                [
                    "Plan an investigation that stays inside the supplied authorization.",
                    "Use uncertainty and evidence gaps to choose the next action.",
                ],
                "Read the mission briefing, authorization, business context, and available resources before acting. Form a hypothesis but keep alternatives open. Inspect the least invasive relevant evidence, record what changed your view, use hints only when needed, and preserve the final rationale. A strong submission states classification, known scope, uncertainty, impact, recommendation, next steps, and reflection. The deterministic evaluator and replay use your recorded actions; Sentinel may explain concepts but is not the grading authority.",
                "Mission briefing: a fictional shipping organization reports a suspicious message and unusual endpoint/identity activity. Only the supplied synthetic evidence and listed decisions are authorized.",
                "A prepared analyst first identifies the affected user and asset, opens the message and endpoint evidence, correlates time and entities, then chooses a proportionate decision. They avoid retaliation, arbitrary scanning, destructive action, or conclusions that extend beyond the evidence.",
                {
                    "authorization": "The explicit boundary defining allowed investigation actions.",
                    "independence": "The degree to which evidence was produced without escalating help.",
                    "replay": "A chronological record of evidence, decisions, feedback, and remediation.",
                },
                "Speed is not the same as readiness; a fast unsupported conclusion is weaker than a deliberate reproducible decision.",
                "Write a five-step mission plan and mark the step where you will reassess your original hypothesis.",
                "What evidence or decision would cause you to stop and escalate instead of continuing independently?",
                ["nist-ir", "mitre"],
            )
        ],
        "practice": {
            "id": "soc-08-practice",
            "type": "guided_investigation",
            "title": "Choose the mission opening",
            "scenario": "The Harbor Light briefing supplies a suspicious message, endpoint event, identity record, and asset context.",
            "objective": "Choose the first bounded investigation step.",
            "prompt": "Which opening action is most defensible?",
            "options": [
                "Review the authorization and briefing, then inspect the supplied evidence relevant to the reported user and asset.",
                "Scan public targets for similar behavior.",
                "Declare a breach and retaliate against the sender.",
            ],
            "private_answer": {"choice": 0},
            "feedback": "Start with scope, context, and supplied evidence.",
            "linked_skills": ["alert-triage", "incident-reporting"],
        },
    },
]

for position, module in enumerate(MODULES, start=1):
    module["position"] = position
    module["version"] = PATHWAY_VERSION
    module["review_state"] = REVIEW_STATE
    module["required_lessons"] = [item["id"] for item in module["lessons"]]
    module["required_practices"] = [module["practice"]["id"]]
    module["required_assessment"] = f"{module['id']}-assessment"
    module["completion_rules"] = {
        "all_required_lessons_completed": True,
        "all_required_practices_passed": True,
        "assessment_minimum_score": 0.7,
    }
    module["assessment"] = {
        "id": module["required_assessment"],
        "version": PATHWAY_VERSION,
        "title": f"{module['title']} assessment",
        "retake_policy": "Unlimited formative retakes; every submitted attempt is retained.",
        "questions": [
            {
                "id": f"{module['id']}-q1",
                "type": module["practice"]["type"],
                "prompt": module["practice"]["prompt"],
                "options": module["practice"].get("options", []),
                "private_answer": module["practice"]["private_answer"],
                "explanation": module["practice"]["feedback"],
                "skill": module["linked_skills"][0],
                "weight": 0.5,
            },
            {
                "id": f"{module['id']}-q2",
                "type": "scenario_decision",
                "prompt": (
                    f"Which response best demonstrates the objectives of {module['title']}?"
                ),
                "options": [
                    "State the supported observation, preserve uncertainty, and choose a bounded next step.",
                    "Treat the first alert label as a confirmed root cause.",
                    "Take an unapproved destructive action to save time.",
                ],
                "private_answer": {"choice": 0},
                "explanation": (
                    "A defensible SOC response separates evidence from inference and stays "
                    "inside authorization."
                ),
                "skill": module["linked_skills"][-1],
                "weight": 0.5,
            },
        ],
    }

LESSONS = {item["id"]: item for module in MODULES for item in module["lessons"]}
PRACTICES = {module["practice"]["id"]: module["practice"] for module in MODULES}
ASSESSMENTS = {module["assessment"]["id"]: module["assessment"] for module in MODULES}

PATHWAY = {
    "id": PATHWAY_ID,
    "version": PATHWAY_VERSION,
    "title": "Junior SOC Analyst Pathway",
    "purpose": "Prepare a learner to investigate and communicate a bounded workplace SOC case.",
    "review_state": REVIEW_STATE,
    "estimated_minutes": sum(module["estimated_minutes"] for module in MODULES),
    "module_count": len(MODULES),
    "modules": MODULES,
}


def public_pathway() -> dict[str, Any]:
    modules = []
    for module in MODULES:
        modules.append(
            {
                key: value
                for key, value in module.items()
                if key not in {"practice", "assessment", "lessons"}
            }
            | {
                "lessons": [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "minutes": item["minutes"],
                        "linked_skills": item["linked_skills"],
                        "review_state": item["review_state"],
                    }
                    for item in module["lessons"]
                ],
                "practice": {
                    key: value
                    for key, value in module["practice"].items()
                    if key != "private_answer"
                },
                "assessment": {
                    "id": module["assessment"]["id"],
                    "title": module["assessment"]["title"],
                    "version": module["assessment"]["version"],
                    "retake_policy": module["assessment"]["retake_policy"],
                },
            }
        )
    return {**PATHWAY, "modules": modules}
