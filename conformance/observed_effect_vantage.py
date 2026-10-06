"""Neutral observation-vantage inference for bounded observed-effect claims.

The rule is intentionally narrow. It decides only whether supplied facts
establish an independent observation vantage. It does not decide whether the
observed effect itself is true, complete, causal, or sufficient for any AACP
A-G property.

Trust material is runner-owned input. A producer's own ``declared_independence``
flag is retained for provenance but is never an establishment basis.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Collection, Mapping


class VantageResult(StrEnum):
    ESTABLISHED = "ESTABLISHED"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class VantageVerdict:
    result: VantageResult
    unmet_obligation: str | None
    reason: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "result": self.result.value,
            "unmet_obligation": self.unmet_obligation,
            "reason": self.reason,
        }


def _identifier(record: Mapping[str, Any], name: str) -> str | None:
    value = record.get(name)
    if type(value) is not str or not value.strip():
        return None
    return value


def evaluate_observation_vantage(
    record: Mapping[str, Any],
    *,
    trusted_control_domains: Collection[str] = (),
) -> VantageVerdict:
    """Derive whether the observation vantage is independent.

    ``trusted_control_domains`` is supplied by the verifier/runner and therefore
    sits outside the producer record. Merely naming another control domain does
    not establish independence unless that domain is in this trust set.
    """
    if not isinstance(record, Mapping):
        return VantageVerdict(
            VantageResult.INVALID_INPUT, None, "record-not-an-object"
        )

    observer_id = _identifier(record, "observer_id")
    observed_party = _identifier(record, "observed_party")
    if observer_id is None or observed_party is None:
        return VantageVerdict(
            VantageResult.INVALID_INPUT, None, "observer-identity-invalid"
        )

    declared = record.get("declared_independence", False)
    if type(declared) is not bool:
        return VantageVerdict(
            VantageResult.INVALID_INPUT, None, "declared-independence-not-boolean"
        )

    # RFC189 OE-08 discriminator: self-vantage can never be upgraded by a
    # declaration, key possession, a different textual control-domain label,
    # or missing facts.
    if observer_id == observed_party:
        return VantageVerdict(
            VantageResult.NOT_ESTABLISHED,
            "observation_vantage",
            "authoritative-vantage-not-independent",
        )

    can_forge = record.get("can_observed_party_forge")
    can_suppress = record.get("can_observed_party_suppress")
    if can_forge is not None and type(can_forge) is not bool:
        return VantageVerdict(
            VantageResult.INVALID_INPUT, None, "forge-capability-not-boolean"
        )
    if can_suppress is not None and type(can_suppress) is not bool:
        return VantageVerdict(
            VantageResult.INVALID_INPUT, None, "suppress-capability-not-boolean"
        )
    if can_forge is True or can_suppress is True:
        return VantageVerdict(
            VantageResult.NOT_ESTABLISHED,
            "observation_vantage",
            "authoritative-vantage-not-independent",
        )

    control_domain = _identifier(record, "control_domain")
    observed_control_domain = _identifier(record, "observed_control_domain")
    if control_domain is None or observed_control_domain is None:
        return VantageVerdict(
            VantageResult.NOT_ESTABLISHED,
            "observation_vantage",
            "observation-vantage-not-established",
        )

    if control_domain == observed_control_domain:
        return VantageVerdict(
            VantageResult.NOT_ESTABLISHED,
            "observation_vantage",
            "authoritative-vantage-not-independent",
        )

    if control_domain not in set(trusted_control_domains):
        return VantageVerdict(
            VantageResult.NOT_ESTABLISHED,
            "observation_vantage",
            "observation-vantage-not-established",
        )

    # Absence of explicit forge/suppress facts is not positive evidence.
    if can_forge is not False or can_suppress is not False:
        return VantageVerdict(
            VantageResult.NOT_ESTABLISHED,
            "observation_vantage",
            "observation-vantage-not-established",
        )

    return VantageVerdict(
        VantageResult.ESTABLISHED,
        None,
        "independent-vantage-established",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the AACP bounded observation-vantage profile."
    )
    parser.add_argument("case", type=Path)
    args = parser.parse_args(argv)

    try:
        document = json.loads(args.case.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("case file must be a JSON object")
        record = document["input"] if "input" in document else document
        trust = document.get("runner_trust", {})
        if not isinstance(trust, dict):
            raise ValueError("runner_trust must be an object")
        domains = trust.get("trusted_control_domains", ())
        if not isinstance(domains, list) or not all(type(x) is str for x in domains):
            raise ValueError("trusted_control_domains must be a list of strings")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "result": VantageResult.INVALID_INPUT.value,
            "unmet_obligation": None,
            "reason": "case-load-invalid",
            "detail": str(exc),
        }, sort_keys=True))
        return 2

    verdict = evaluate_observation_vantage(
        record, trusted_control_domains=tuple(domains)
    )
    print(json.dumps(verdict.as_dict(), sort_keys=True))
    return 2 if verdict.result is VantageResult.INVALID_INPUT else 0


if __name__ == "__main__":
    raise SystemExit(main())
