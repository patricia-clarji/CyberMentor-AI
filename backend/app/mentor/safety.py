import hashlib
import re
from dataclasses import dataclass

POLICY_VERSION = "sentinel-safety-1.0.0"

PROMPT_MANIPULATION = re.compile(
    r"\b(ignore|override|discard|reveal|print|repeat|show)\b.{0,80}"
    r"\b(system|developer|policy|instruction|prompt|hidden|secret)\b",
    re.IGNORECASE | re.DOTALL,
)
GRADED_ANSWER = re.compile(
    r"\b(answer key|give me (?:the )?(?:answer|solution)|complete my (?:quiz|exam)|"
    r"solve my (?:quiz|exam|assignment)|do my project|correctoption|"
    r"mission answer|lab answer|hidden evidence|grading bypass)\b",
    re.IGNORECASE,
)
OFFENSIVE_ACTION = re.compile(
    r"\b(exploit|attack|phish|steal|bypass|masscan|sqlmap|metasploit|"
    r"dump credentials|exfiltrate|crack)\b",
    re.IGNORECASE,
)
REAL_TARGET = re.compile(
    r"\b(real|public|production|someone else|company network|without permission)\b|"
    r"\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|gov|edu)\b",
    re.IGNORECASE,
)
SECRET_MATERIAL = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\b(?:sk|api)[-_][a-z0-9]{16,}\b|"
    r"\b(?:password|token|secret)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
MALWARE_OR_DESTRUCTIVE = re.compile(
    r"\b(write|build|create|generate|deploy|send|give me).{0,60}"
    r"\b(malware|ransomware|keylogger|credential stealer|reverse shell|"
    r"destructive payload|wiper|delete all|disable antivirus)\b",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class SafetyDecision:
    blocked: bool
    category: str | None
    response: str | None


def classify(question: str) -> SafetyDecision:
    if SECRET_MATERIAL.search(question):
        return SafetyDecision(
            True,
            "secret_material",
            (
                "I won’t process or repeat credentials or secret material. Revoke or rotate "
                "anything real that was exposed, then ask again using a synthetic placeholder."
            ),
        )
    if PROMPT_MANIPULATION.search(question):
        return SafetyDecision(
            True,
            "prompt_manipulation",
            (
                "I can’t reveal or override hidden instructions. I can explain the "
                "learner-visible SOC material or help you reason from supplied evidence."
            ),
        )
    if MALWARE_OR_DESTRUCTIVE.search(question):
        return SafetyDecision(
            True,
            "malware_or_destructive_payload",
            (
                "I can’t create malware, credential theft tooling, or destructive payloads. "
                "I can help analyze synthetic indicators, design detections, explain safe "
                "containment, or build a non-deployable defensive simulation."
            ),
        )
    if GRADED_ANSWER.search(question):
        return SafetyDecision(
            True,
            "graded_answer_request",
            (
                "I won’t provide graded answers or complete assessed work. Share your current "
                "reasoning and I can offer a concept reminder or a smaller ungraded hint."
            ),
        )
    if OFFENSIVE_ACTION.search(question) and REAL_TARGET.search(question):
        return SafetyDecision(
            True,
            "unsafe_real_target",
            (
                "I can’t help target real systems or people. I can help with an authorized "
                "local simulation, defensive detection, remediation, or rules of engagement."
            ),
        )
    return SafetyDecision(False, None, None)


def redacted_hash(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()
