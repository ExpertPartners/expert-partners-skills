#!/usr/bin/env python3
"""validate_record.py -- validate visual-assets register records before filing.

Part of the visual-clearance skill. Checks each record against
../schemas/asset-record.schema.json (a JSON Schema subset interpreted here so
no third-party validator is needed) and then the cross-field rules the schema
cannot express:

  * an approved named-place asset must be VERIFIED with recorded evidence
  * a grade above UNVERIFIED must carry location evidence
  * attribution required means attribution text is recorded
  * the approver is a named human, never an AI surface or skill
  * no secrets, email addresses, phone numbers or correspondence bodies

Records are YAML (PyYAML) or JSON. Exit 0 when every record is valid.

Usage:
  validate_record.py RECORD [RECORD ...]
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from clearance_rules import AI_ACTORS  # noqa: E402

SCHEMA_PATH = HERE.parent / "schemas" / "asset-record.schema.json"
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
SECRET = re.compile(
    r"(api[_-]?key|secret|passw(or)?d|token|bearer)\s*[:=]|"
    r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})",
    re.I,
)
TYPES = {
    "string": str, "integer": int, "boolean": bool, "array": list, "object": dict, "null": type(None),
}


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise SystemExit("PyYAML is required for YAML records (pip install pyyaml), or use JSON")
        return yaml.safe_load(text)
    return json.loads(text)


def _type_ok(value, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, TYPES[name])


def _as_date_str(value):
    return value.isoformat() if isinstance(value, dt.date) else value


def check_schema(value, schema: dict, path: str, errors: list[str]) -> None:
    value = _as_date_str(value)
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
        return
    wanted = schema.get("type")
    if wanted:
        names = wanted if isinstance(wanted, list) else [wanted]
        if not any(_type_ok(value, n) for n in names):
            errors.append(f"{path}: expected {'/'.join(names)}, got {type(value).__name__}")
            return
    if value is None:
        return
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if schema.get("format") == "date":
            try:
                dt.date.fromisoformat(value)
            except ValueError:
                errors.append(f"{path}: {value!r} is not an ISO date")
    if isinstance(value, int) and not isinstance(value, bool) and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: below {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        for index, item in enumerate(value):
            if "items" in schema:
                check_schema(item, schema["items"], f"{path}[{index}]", errors)
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required")
        for key, item in value.items():
            if key in props:
                check_schema(item, props[key], f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: not allowed by the schema")


def _strings(value, path="record"):
    value = _as_date_str(value)
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")


def check_rules(record: dict, errors: list[str]) -> None:
    status = record.get("status")
    grade = record.get("location_confidence")
    evidence = record.get("location_evidence") or []
    usages = record.get("usages") or []
    named = bool(record.get("place_key")) or any(u.get("represents_named_place") for u in usages if isinstance(u, dict))
    if status == "approved" and named and grade != "VERIFIED":
        errors.append(f"record: approved named-place asset is {grade}; only VERIFIED may represent a named place")
    if grade in ("VERIFIED", "PROBABLE") and not evidence:
        errors.append(f"record: {grade} grade has no recorded location evidence")
    if grade == "VERIFIED":
        kinds = {e.get("type") for e in evidence if isinstance(e, dict)}
        if "landmark_match_official" not in kinds or not kinds & {"source_metadata", "map_corroboration", "independent_corroboration"}:
            errors.append("record: VERIFIED needs a landmark match against an official source plus an independent confirmation")
    if record.get("attribution_required") and not (record.get("attribution_text") or "").strip():
        errors.append("record: attribution is required but attribution_text is empty")
    if record.get("permission_type") in ("email", "contract", "license_purchase", "work_for_hire"):
        if not (record.get("permission_scope") or {}).get("uses"):
            errors.append("record: a permission or purchased license needs a recorded scope of uses")
    approver = (record.get("approval") or {}).get("approved_by", "")
    if AI_ACTORS.search(approver or ""):
        errors.append(f"record: approval.approved_by {approver!r} names an AI surface; approval must be a named human")
    for usage in usages:
        if isinstance(usage, dict) and usage.get("represents_named_place") and grade != "VERIFIED":
            errors.append(f"record: usage at {usage.get('where')!r} represents a named place but the asset is {grade}")
    brands = set(record.get("brand_scope") or [])
    for usage in usages:
        if isinstance(usage, dict) and usage.get("brand") not in brands:
            errors.append(f"record: usage brand {usage.get('brand')!r} is outside brand_scope")
    for path, text in _strings(record):
        if EMAIL.search(text):
            errors.append(f"{path}: contains an email address; store a pointer to the system of record instead")
        if PHONE.search(text):
            errors.append(f"{path}: contains a phone number; store a pointer instead")
        if SECRET.search(text):
            errors.append(f"{path}: looks like a credential; secrets never enter the register")


def validate(record, schema: dict | None = None) -> list[str]:
    schema = schema or json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record: not a mapping"]
    check_schema(record, schema, "record", errors)
    check_rules(record, errors)
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    failed = False
    for name in argv:
        errors = validate(load(Path(name)), schema)
        if errors:
            failed = True
            print(f"INVALID {name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"VALID   {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
