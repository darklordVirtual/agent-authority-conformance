"""Version-dispatched, offline assessment validation; no evidence execution."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {"0.1": "assessment.schema.json", "0.2": "assessment-v0.2.schema.json"}


def load_validator(filename):
    schema = json.loads((ROOT / "schema" / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_assessment(document):
    if not isinstance(document, dict):
        raise ValidationError("Assessment must be an object")
    version = document.get("spec_version")
    if not isinstance(version, str) or version not in SCHEMAS:
        raise ValidationError("Unsupported assessment spec_version")
    load_validator(SCHEMAS[version]).validate(document)
    if version == "0.2":
        for row in document["properties"]:
            boundary = row.get("execution_boundary")
            if boundary and boundary["evaluation_scope"] != row.get("evaluation_scope"):
                raise ValidationError("execution_boundary scope must match evaluation_scope")
