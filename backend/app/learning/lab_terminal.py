import fnmatch
import posixpath
import re
import shlex
from dataclasses import dataclass
from typing import Any

FORBIDDEN_SYNTAX = re.compile(r"[;|><`]|\$\(")


@dataclass(frozen=True)
class TerminalResult:
    exit_code: int
    output: str
    cwd: str
    command: str


def _resolve(cwd: str, path: str) -> str:
    resolved = posixpath.normpath(path if path.startswith("/") else posixpath.join(cwd, path))
    return resolved if resolved.startswith("/") else f"/{resolved}"


def _directories(files: list[dict[str, Any]]) -> set[str]:
    result = {"/"}
    for item in files:
        parent = posixpath.dirname(item["path"])
        while parent and parent not in result:
            result.add(parent)
            parent = posixpath.dirname(parent)
    return result


def _file(files: list[dict[str, Any]], path: str) -> dict[str, Any] | None:
    return next((item for item in files if item["path"] == path), None)


def _error(command: str, message: str, cwd: str, code: int = 1) -> TerminalResult:
    return TerminalResult(code, f"{command}: {message}", cwd, command)


def _listing(path: str, files: list[dict[str, Any]]) -> list[str]:
    prefix = "/" if path == "/" else f"{path}/"
    names = {
        item["path"][len(prefix) :].split("/", 1)[0]
        for item in files
        if item["path"].startswith(prefix) and item["path"] != path
    }
    return sorted(names)


def execute_terminal(
    raw: str,
    *,
    cwd: str,
    files: list[dict[str, Any]],
    processes: list[dict[str, Any]],
    connections: list[dict[str, Any]],
    allowed_tools: set[str],
) -> TerminalResult:
    if not raw.strip():
        return TerminalResult(0, "", cwd, "")
    if FORBIDDEN_SYNTAX.search(raw):
        return _error("shell", "operators and expansion are disabled in this simulation", cwd, 2)
    try:
        args = shlex.split(raw)
    except ValueError as error:
        return _error("shell", str(error), cwd, 2)
    if not args:
        return TerminalResult(0, "", cwd, "")
    command, operands = args[0], args[1:]
    if command not in allowed_tools:
        return _error(command, "command is not available in this simulation", cwd, 127)
    directories = _directories(files)

    if command == "pwd":
        return TerminalResult(0, cwd, cwd, command)
    if command == "cd":
        if len(operands) > 1:
            return _error(command, "too many arguments", cwd)
        target = _resolve(cwd, operands[0] if operands else "/home/analyst")
        if target not in directories:
            return _error(command, f"{target}: No such directory", cwd)
        return TerminalResult(0, "", target, command)
    if command == "ls":
        long = "-l" in operands
        paths = [item for item in operands if item != "-l"]
        target = _resolve(cwd, paths[0] if paths else ".")
        direct_file = _file(files, target)
        if direct_file:
            value = posixpath.basename(target)
            if long:
                value = (
                    f"{direct_file['mode']} {direct_file['owner']} "
                    f"{direct_file['group']} {len(direct_file['content'])} {value}"
                )
            return TerminalResult(0, value, cwd, command)
        if target not in directories:
            return _error(command, f"cannot access '{target}': No such file or directory", cwd, 2)
        names = _listing(target, files)
        if long:
            lines = []
            for name in names:
                child = _resolve(target, name)
                item = _file(files, child)
                lines.append(
                    f"{item['mode']} {item['owner']} {item['group']} {len(item['content'])} {name}"
                    if item
                    else f"d0755 root root 0 {name}"
                )
            return TerminalResult(0, "\n".join(lines), cwd, command)
        return TerminalResult(0, "  ".join(names), cwd, command)
    if command == "cat":
        if not operands:
            return _error(command, "missing file operand", cwd)
        output = []
        for operand in operands:
            target = _resolve(cwd, operand)
            item = _file(files, target)
            if item is None:
                return _error(command, f"{operand}: No such file or directory", cwd)
            output.append(item["content"])
        return TerminalResult(0, "\n".join(output), cwd, command)
    if command in {"head", "tail"}:
        count = 10
        values = list(operands)
        if len(values) >= 2 and values[0] == "-n":
            try:
                count = max(0, min(1000, int(values[1])))
            except ValueError:
                return _error(command, f"invalid number of lines: '{values[1]}'", cwd)
            values = values[2:]
        if len(values) != 1:
            return _error(command, "expected one file operand", cwd)
        item = _file(files, _resolve(cwd, values[0]))
        if item is None:
            return _error(command, f"{values[0]}: No such file or directory", cwd)
        lines = item["content"].splitlines()
        selected = lines[:count] if command == "head" else lines[-count:]
        return TerminalResult(0, "\n".join(selected), cwd, command)
    if command == "grep":
        insensitive = "-i" in operands
        values = [item for item in operands if item != "-i"]
        if len(values) < 2:
            return _error(command, "usage: grep [-i] PATTERN FILE", cwd, 2)
        pattern, paths = values[0], values[1:]
        matches = []
        for path in paths:
            item = _file(files, _resolve(cwd, path))
            if item is None:
                return _error(command, f"{path}: No such file or directory", cwd, 2)
            for line in item["content"].splitlines():
                haystack = line.casefold() if insensitive else line
                needle = pattern.casefold() if insensitive else pattern
                if needle in haystack:
                    matches.append(line)
        return TerminalResult(0 if matches else 1, "\n".join(matches), cwd, command)
    if command == "find":
        values = list(operands)
        root = _resolve(cwd, values.pop(0) if values and values[0] != "-name" else ".")
        pattern = "*"
        if values:
            if len(values) != 2 or values[0] != "-name":
                return _error(command, "usage: find [PATH] [-name PATTERN]", cwd, 2)
            pattern = values[1]
        if root not in directories and _file(files, root) is None:
            return _error(command, f"'{root}': No such file or directory", cwd)
        found = [
            item["path"]
            for item in files
            if (item["path"] == root or item["path"].startswith(f"{root.rstrip('/')}/"))
            and fnmatch.fnmatch(posixpath.basename(item["path"]), pattern)
        ]
        return TerminalResult(0, "\n".join(sorted(found)), cwd, command)
    if command == "ps":
        lines = ["PID USER COMMAND"]
        lines.extend(f"{item['pid']} {item['user']} {item['command']}" for item in processes)
        return TerminalResult(0, "\n".join(lines), cwd, command)
    if command in {"netstat", "ss"}:
        lines = ["Proto Local Address Remote Address State Process"]
        lines.extend(
            f"{item['protocol']} {item['local']} {item['remote']} {item['state']} {item['process']}"
            for item in connections
        )
        return TerminalResult(0, "\n".join(lines), cwd, command)
    if command == "journalctl":
        unit = None
        if "-u" in operands:
            index = operands.index("-u")
            if index + 1 >= len(operands):
                return _error(command, "option requires an argument -- 'u'", cwd)
            unit = operands[index + 1].casefold()
        sources = [
            item
            for item in files
            if item["path"].startswith("/var/log/")
            and (unit is None or unit in item["content"].casefold())
        ]
        return TerminalResult(
            0,
            "\n".join(item["content"] for item in sources) or "-- No entries --",
            cwd,
            command,
        )
    if command == "chmod":
        if len(operands) != 2 or not re.fullmatch(r"[0-7]{3,4}", operands[0]):
            return _error(command, "usage: chmod OCTAL_MODE FILE", cwd)
        item = _file(files, _resolve(cwd, operands[1]))
        if item is None:
            return _error(command, f"cannot access '{operands[1]}': No such file", cwd)
        item["mode"] = operands[0].zfill(4)
        return TerminalResult(0, "", cwd, command)
    if command == "chown":
        if len(operands) != 2 or not operands[0].strip(":"):
            return _error(command, "usage: chown OWNER[:GROUP] FILE", cwd)
        item = _file(files, _resolve(cwd, operands[1]))
        if item is None:
            return _error(command, f"cannot access '{operands[1]}': No such file", cwd)
        owner, separator, group = operands[0].partition(":")
        if owner:
            item["owner"] = owner
        if separator and group:
            item["group"] = group
        return TerminalResult(0, "", cwd, command)
    return _error(command, "unsupported command state", cwd, 127)
