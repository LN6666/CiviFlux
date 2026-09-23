#!/usr/bin/env python3
"""Offline SimpleJev setup check; --live permits one already-authorized API call.

The selected Qwen-based Jev is Featherless SimpleJev's hosted typed classifier.
No local model, weight download, paid authorization or automatic retry is performed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.system_one import BlockedEnvironment, ProtocolError, SimpleJevBackend, SimpleJevConfig
from adapters.system_one.simplejev import SCORE_SEMANTICS


def preflight(config: SimpleJevConfig, *, live: bool = False) -> dict:
    blockers = []
    paid = config.provider_mode == "simplejev_api"
    if paid and not config.api_key:
        blockers.append("PRODUCTION_CREDENTIALS_MISSING")
    if not config.allow_egress:
        blockers.append("ABSTRACT_DATA_EGRESS_NOT_AUTHORIZED")
    if not config.max_calls:
        blockers.append("REMOTE_CALL_BUDGET_NOT_AUTHORIZED")
    report = {
        "schema_version": "1.1",
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": "simplejev_configuration_and_optional_one_call_protocol",
        "status": "DEFERRED_USER" if blockers else "CONFIG_READY_NOT_LIVE_VERIFIED",
        "provider_mode": config.provider_mode,
        "provider": "Featherless SimpleJev",
        "model": config.model,
        "ontology_version": config.ontology_version,
        "endpoint_host": urlsplit(config.base_url).hostname,
        "credentials_required": paid,
        "credentials_present": bool(config.api_key),
        "egress_authorized": config.allow_egress,
        "authorized_max_calls": config.max_calls,
        "max_questions_per_call": config.max_questions,
        "score_semantics": SCORE_SEMANTICS,
        "blockers": blockers,
        "downloads_performed": False,
        "local_models_launched": False,
        "live_api_calls_performed": 0,
        "paid_api_calls_performed": 0,
        "product_gate_complete": False,
        "documentation_url": "https://simple-jev.featherless.ai/docs",
        "release_remaining": [
            "real response applied to graph/PPR with transition hash",
            "UrbanRelationEval held-out expert labels and evaluation",
            "hosted server and weights revisions unreported",
        ],
    }
    if live and not blockers:
        backend = SimpleJevBackend(config)
        try:
            policy = backend.score_relations(
                "facility_access",
                {
                    "ACCESS_FOR": "A road segment is on a verified access path to a facility.",
                    "ADMIN_METADATA": "An entity appears in the same administrative file.",
                },
            )
            report.update(policy=policy, provenance=backend.last_provenance)
            report["status"] = "PASS_PROTOCOL_ONLY" if backend.attempted_calls else "CACHE_REPLAY_ONLY"
        except BlockedEnvironment as exc:
            report["status"] = "BLOCKED_API_SETUP_OR_BUDGET"
            report["error"] = str(exc)
        except ProtocolError as exc:
            report["status"] = "FAIL_TYPED_PROTOCOL"
            report["error"] = str(exc)
        finally:
            report["live_api_calls_performed"] = backend.attempted_calls
            report["paid_api_calls_performed"] = backend.attempted_calls if paid else 0
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--env-file", type=Path, default=ROOT / ".env")
    ap.add_argument("--output", type=Path, default=ROOT / "evidence/wp0/systemone_preflight.json")
    ap.add_argument("--live", action="store_true", help="perform one call within a pre-authorized budget")
    args = ap.parse_args()
    manifest = json.loads((ROOT / "ontology/manifest.yaml").read_text())
    config = SimpleJevConfig.from_env(args.env_file, ontology_version=manifest["ontology_version"])
    report = preflight(config, live=args.live)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({"status": report["status"], "blockers": report["blockers"], "evidence": str(args.output)})
    )
    return (
        2
        if report["status"].startswith(("BLOCKED", "DEFERRED"))
        else 3
        if report["status"].startswith("FAIL")
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
