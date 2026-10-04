"""Offline project onboarding. Configuration and discovery are not verdicts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

from jsonschema import Draft202012Validator, ValidationError
import yaml

ROLES = ("producer", "consumer", "verifier", "reproduction")
CEILING = "Configuration validation and local Git metadata only; no evidence admission, property verdict, independence credit or certification."
MAX_CONFIG_BYTES = 1024 * 1024


class ProjectError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ProjectError(message)


class ProjectLoader(yaml.SafeLoader):
    def __init__(self, stream):
        super().__init__(stream)
        self.nesting = 0

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ProjectError("YAML aliases are not allowed in project configuration")
        if self.nesting >= 64:
            raise ProjectError("project configuration nesting exceeds the 64-level limit")
        self.nesting += 1
        try:
            return super().compose_node(parent, index)
        finally:
            self.nesting -= 1

    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in mapping:
                raise ProjectError("project mappings require unique string keys")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def validator(name):
    installed = Path(__file__).resolve().parent / "schemas" / name
    source = Path(__file__).resolve().parents[1] / "schema" / name
    schema = json.loads((installed if installed.is_file() else source).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_project(document):
    validator("aacp-project-v1.schema.json").validate(document)
    identifiers = set()
    for surface in document["surfaces"]:
        if surface["id"] in identifiers:
            raise ProjectError("surface IDs must be unique")
        identifiers.add(surface["id"])
        if surface["role"] not in document["roles"]:
            raise ProjectError("every surface role must be declared in roles")


def load_project(path):
    with path.open("rb") as source:
        raw = source.read(MAX_CONFIG_BYTES + 1)
    if len(raw) > MAX_CONFIG_BYTES:
        raise ProjectError("project configuration exceeds the 1 MiB limit")
    document = yaml.load(raw.decode("utf-8"), Loader=ProjectLoader)
    validate_project(document)
    return document, hashlib.sha256(raw).hexdigest()


def local_revision(root):
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
         "-C", str(root), "rev-parse", "--verify", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    revision = result.stdout.strip()
    if result.returncode == 0 and len(revision) == 40 and all(
        character in "0123456789abcdef" for character in revision.lower()
    ):
        return revision
    return None


def execute(arguments):
    path = Path(arguments.project)
    if arguments.command == "init":
        document = {
            "schema_version": "aacp-project-v1",
            "project": {"name": arguments.name or path.resolve().parent.name,
                        "repository": "UNKNOWN", "revision": "AUTO"},
            "roles": arguments.role or ["consumer"],
            "surfaces": [],
            "claims": {"discovery": "assisted"},
            "execution": {"external_code": "deny_by_default", "network": "deny_by_default"},
            "review": {"publication": "PRIVATE_UNTIL_APPROVED"},
        }
        validate_project(document)
        with path.open("x", encoding="utf-8") as output:
            output.write(yaml.safe_dump(document, sort_keys=False))
        data = {"project_file": str(path), "project": document}
        action = "validate_configuration"
        command = shlex.join(["aacp", "validate", "--project", str(path), "--json"])
    else:
        document, digest = load_project(path)
        data = {"project_file": str(path), "config_sha256": digest, "project": document}
        action = "inspect_declared_surfaces"
        command = shlex.join(["aacp", "inspect", "--project", str(path), "--json"])
        if arguments.command == "inspect":
            revision = local_revision(path.resolve().parent)
            declared = document["project"]["revision"]
            pin_state = "UNKNOWN" if revision is None else "KNOWN"
            if declared not in {"AUTO", "UNKNOWN"} and revision and declared.lower() != revision.lower():
                pin_state = "MISMATCH"
            data["subject_pin"] = {"declared": declared, "local_head": revision,
                                   "state": pin_state, "worktree_content_checked": False}
            data["discovery_scope"] = "Declared configuration and local HEAD only; no source evidence discovery."
            action = "freeze_subject_pin" if declared in {"AUTO", "UNKNOWN"} or pin_state != "KNOWN" else "select_bounded_profile"
            command = None
    return data, {"action": action, "command": command,
                  "output_schema": "aacp-command-result-v1" if command else "aacp-project-v1"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    json_output = "--json" in argv
    parser = Parser(prog="aacp", description="Offline, non-verdict project onboarding")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--project", default="aacp-project.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "validate", "inspect"):
        command_parser = commands.add_parser(name)
        command_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        command_parser.add_argument("--project", default=argparse.SUPPRESS)
        if name == "init":
            command_parser.add_argument("--name")
            command_parser.add_argument("--role", action="append", choices=ROLES)
    command = next((value for value in argv if value in {"init", "validate", "inspect"}), "UNKNOWN")
    result = {
        "schema_version": "aacp-command-result-v1", "command": command,
        "status": "OK", "verification_status": "NOT_RUN", "property_verdict": None,
        "data": {}, "errors": [],
        "next_action": {"action": "correct_configuration", "command": None,
                        "output_schema": "aacp-project-v1"},
        "claim_ceiling": CEILING,
    }
    exit_code = 0
    try:
        arguments = parser.parse_args(argv)
        result["command"] = arguments.command
        result["data"], result["next_action"] = execute(arguments)
    except (ProjectError, ValidationError, yaml.YAMLError, UnicodeError) as error:
        message = error.message if isinstance(error, ValidationError) else str(error)
        result.update(status="INVALID_INPUT", errors=[{"code": "INVALID_CONFIGURATION", "message": message}])
        exit_code = 2
    except FileExistsError:
        result.update(status="INVALID_INPUT", errors=[{"code": "ALREADY_EXISTS", "message": "Project file exists; refusing to overwrite it."}])
        exit_code = 2
    except FileNotFoundError as error:
        result.update(status="INVALID_INPUT", errors=[{"code": "MISSING_INPUT", "message": str(error)}])
        exit_code = 2
    except OSError as error:
        result.update(status="ERROR", errors=[{"code": "LOCAL_IO_ERROR", "message": str(error)}])
        exit_code = 3
    validator("aacp-command-result-v1.schema.json").validate(result)
    if json_output:
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    else:
        print(f"{result['command']}: {result['status']} (verification NOT_RUN; no property verdict)")
        for error in result["errors"]:
            print(f"{error['code']}: {error['message']}")
        if result["data"]:
            print(json.dumps(result["data"], indent=2, ensure_ascii=True))
        print(f"Next: {result['next_action']['command'] or result['next_action']['action']}")
    return exit_code