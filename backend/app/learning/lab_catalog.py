import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.core.errors import AppError

SUPPORTED_LAB_TYPES = {
    "guided",
    "independent",
    "investigation",
    "incident-response",
    "detection",
    "secure-configuration",
    "threat-hunting",
}
SUPPORTED_TOOLS = {
    "pwd",
    "ls",
    "cd",
    "cat",
    "grep",
    "find",
    "ps",
    "netstat",
    "ss",
    "journalctl",
    "tail",
    "head",
    "chmod",
    "chown",
}
PRIVATE_KEYS = {"virtualEnvironment", "validation", "expertSolution"}
CATALOG_PATH = Path(__file__).resolve().parents[3] / "content" / "labs" / "soc-practical-labs.json"


def load_lab_document(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        if path.suffix.casefold() in {".yaml", ".yml"}:
            value = yaml.safe_load(source)
        elif path.suffix.casefold() == ".json":
            value = json.load(source)
        else:
            raise ValueError("Lab definitions must use JSON, YAML, or YML.")
    if not isinstance(value, dict):
        raise ValueError("A lab definition document must be an object.")
    return value


def validate_lab_catalog(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    labs = document.get("labs")
    if document.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if not isinstance(labs, list) or not labs:
        return [*errors, "labs must be a non-empty list"]
    identifiers: set[str] = set()
    required = {
        "id",
        "version",
        "title",
        "labType",
        "category",
        "difficulty",
        "estimatedMinutes",
        "prerequisites",
        "linkedSkills",
        "objectives",
        "scenario",
        "learnerInstructions",
        "availableTools",
        "virtualEnvironment",
        "validation",
        "hints",
        "reflectionQuestions",
        "completionCriteria",
        "generatedEvidence",
        "portfolioEligibility",
        "expertSolution",
    }
    for index, lab in enumerate(labs):
        prefix = f"labs[{index}]"
        if not isinstance(lab, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = sorted(required - set(lab))
        if missing:
            errors.append(f"{prefix} is missing: {', '.join(missing)}")
        lab_id = lab.get("id")
        if not isinstance(lab_id, str) or not lab_id.startswith("soc-lab-"):
            errors.append(f"{prefix}.id must start with soc-lab-")
        elif lab_id in identifiers:
            errors.append(f"{prefix}.id is duplicated")
        else:
            identifiers.add(lab_id)
        if lab.get("labType") not in SUPPORTED_LAB_TYPES:
            errors.append(f"{prefix}.labType is unsupported")
        tools = lab.get("availableTools", [])
        if not isinstance(tools, list) or not set(tools).issubset(SUPPORTED_TOOLS):
            errors.append(f"{prefix}.availableTools contains an unsupported command")
        hints = lab.get("hints", [])
        levels = [hint.get("level") for hint in hints if isinstance(hint, dict)]
        if levels != [1, 2, 3, 4, 5]:
            errors.append(f"{prefix}.hints must contain levels 1 through 5")
        environment = lab.get("virtualEnvironment", {})
        files = environment.get("files", []) if isinstance(environment, dict) else []
        for file_index, item in enumerate(files):
            path = item.get("path") if isinstance(item, dict) else None
            if not isinstance(path, str) or not path.startswith("/"):
                errors.append(
                    f"{prefix}.virtualEnvironment.files[{file_index}] needs an absolute path"
                )
    return errors


@lru_cache(maxsize=1)
def catalog_document() -> dict[str, Any]:
    document = load_lab_document(CATALOG_PATH)
    errors = validate_lab_catalog(document)
    if errors:
        raise RuntimeError("Invalid lab catalog: " + "; ".join(errors))
    return document


def get_lab(lab_id: str) -> dict[str, Any]:
    lab = next((item for item in catalog_document()["labs"] if item["id"] == lab_id), None)
    if lab is None:
        raise AppError(404, "lab_not_found", "The requested practical lab was not found.")
    return copy.deepcopy(lab)


def public_lab(lab: dict[str, Any], *, detail: bool = False) -> dict[str, Any]:
    value = {key: copy.deepcopy(item) for key, item in lab.items() if key not in PRIVATE_KEYS}
    if not detail:
        for key in (
            "scenario",
            "learnerInstructions",
            "objectives",
            "reflectionQuestions",
            "checkpoints",
        ):
            value.pop(key, None)
    value["safetyNotice"] = (
        "Authorized defensive training only. Every system, address, person, and event is synthetic."
    )
    return value


def public_catalog() -> list[dict[str, Any]]:
    return [public_lab(lab) for lab in catalog_document()["labs"]]
