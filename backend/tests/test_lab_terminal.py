import copy

from app.learning.lab_catalog import (
    SUPPORTED_LAB_TYPES,
    catalog_document,
    get_lab,
    load_lab_document,
    validate_lab_catalog,
)
from app.learning.lab_service import _objective_state
from app.learning.lab_terminal import execute_terminal


def run(
    command: str,
    *,
    lab_id: str = "soc-lab-linux-auth-triage",
    cwd: str | None = None,
    files: list[dict[str, object]] | None = None,
):
    lab = get_lab(lab_id)
    environment = lab["virtualEnvironment"]
    return execute_terminal(
        command,
        cwd=cwd or environment["cwd"],
        files=files if files is not None else copy.deepcopy(environment["files"]),
        processes=environment["processes"],
        connections=environment["connections"],
        allowed_tools=set(lab["availableTools"]),
    )


def test_catalog_contract_covers_every_supported_lab_type() -> None:
    document = catalog_document()
    assert validate_lab_catalog(document) == []
    assert {lab["labType"] for lab in document["labs"]} == SUPPORTED_LAB_TYPES
    invalid = copy.deepcopy(document)
    invalid["labs"][0]["hints"] = invalid["labs"][0]["hints"][:4]
    assert "levels 1 through 5" in " ".join(validate_lab_catalog(invalid))


def test_lab_authoring_loader_accepts_json_and_yaml(tmp_path) -> None:
    json_path = tmp_path / "lab.json"
    json_path.write_text('{"schemaVersion": 1, "labs": []}', encoding="utf-8")
    yaml_path = tmp_path / "lab.yaml"
    yaml_path.write_text("schemaVersion: 1\nlabs: []\n", encoding="utf-8")
    assert load_lab_document(json_path) == load_lab_document(yaml_path)


def test_terminal_navigation_search_and_realistic_errors_are_deterministic() -> None:
    listing = run("ls /var/log")
    assert listing.exit_code == 0
    assert "auth.log" in listing.output
    filtered = run("grep 'Failed password' /var/log/auth.log")
    assert filtered.exit_code == 0
    assert filtered.output.count("203.0.113.42") == 3
    missing = run("cat /var/log/missing.log")
    assert missing.exit_code == 1
    assert "No such file" in missing.output
    blocked = run("cat /var/log/auth.log | find /")
    assert blocked.exit_code == 2
    assert "disabled" in blocked.output
    host_command = run("whoami")
    assert host_command.exit_code == 127
    assert "not available in this simulation" in host_command.output


def test_terminal_virtual_permissions_mutate_only_supplied_filesystem() -> None:
    lab = get_lab("soc-lab-sshd-hardening")
    files = copy.deepcopy(lab["virtualEnvironment"]["files"])
    first = run(
        "chmod 0644 /etc/ssh/sshd_config",
        lab_id=lab["id"],
        files=files,
    )
    assert first.exit_code == 0
    second = run(
        "chown root:root /etc/ssh/sshd_config",
        lab_id=lab["id"],
        files=files,
    )
    assert second.exit_code == 0
    assert files[0]["mode"] == "0644"
    assert files[0]["owner"] == "root"
    assert files[0]["group"] == "root"


def test_synthetic_process_network_and_file_views() -> None:
    assert "sshd" in run("ps").output
    assert "0.0.0.0:22" in run("ss").output
    assert "Failed password" in run("journalctl -u ssh").output
    found = run("find /var -name '*.log'")
    assert "/var/log/auth.log" in found.output


def test_scenario_objectives_accept_authored_alternative_branches() -> None:
    lab = get_lab("soc-lab-linux-auth-triage")
    primary = _objective_state(lab, ["pwd", "grep"])
    alternative = _objective_state(lab, ["journalctl"])
    unresolved = _objective_state(lab, ["ls"])
    assert primary["activeBranch"] == "primary"
    assert alternative["activeBranch"] == "alternative-3"
    assert alternative["requiredCompleted"] == 1
    assert unresolved["activeBranch"] == "unresolved"
