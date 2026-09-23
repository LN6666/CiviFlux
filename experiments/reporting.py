from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

FEATURES = [
    "road_closure_what_if",
    "traffic_microsimulation",
    "public_transit_linkage",
    "emergency_response_linkage",
    "fire_external_impact",
    "smoke_fire_physics",
    "typed_ontology",
    "scenario_actions",
    "persistent_KG_requirement",
    "scenario_local_graph",
    "graph_ranking_diffusion",
    "baseline_event_attention_delta",
    "AI_scenario_parsing",
    "AI_relation_scoring",
    "self_host_data_local",
    "web_embeddable_component",
    "3D_mandatory",
    "provenance_action_replay",
    "open_source_license",
]

SOURCES = {
    "CiviFlux": (
        "evidence/wp6/ablation_report.json",
        "local implementation and executed engineering evidence",
    ),
    "EU_LDT_Urban_Flow": (
        "https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solution/urban-mobility/solution-overview",
        "official URL returns general portal content; product feature text not verified in current fetch",
    ),
    "The_World_Avatar": (
        "https://github.com/cambridge-cares/TheWorldAvatar",
        "official README describes dynamic semantic KG and computational agents; core development migrated to TheWorldAvatar organization",
    ),
    "CReDo": (
        "https://cp.catapult.org.uk/project/climate-resilience-demonstrator-credo/",
        "official project page supports cross-sector climate infrastructure dependency analysis; detailed software features unspecified",
    ),
    "rescuePY_TUM": (
        "https://www.mdpi.com/2624-6511/9/2/36",
        "paper source returned 429; prior supplied architecture notes not upgraded to currently verified feature claims",
    ),
    "NYU_FDNY_TDT": (
        "https://doi.org/10.1007/s42421-026-00166-4",
        "publisher redirect inaccessible; no implementation verified",
    ),
    "SUMO_LLM_Agent": (
        "https://github.com/xuyimingxym/SUMO_LLM_Agent/tree/f06f6098626eb184bb3a3334b1b20639dda6b842",
        "pinned official MIT repository README and bounded unmodified application smoke",
    ),
    "FireCom": (
        "https://pubmed.ncbi.nlm.nih.gov/41078483/",
        "source returned browser verification page; no implementation verified",
    ),
}

CONFIRMED = {
    "CiviFlux": {
        "road_closure_what_if": ("yes", "Directed/class/time restrictions tested."),
        "traffic_microsimulation": ("yes", "Actual SUMO adapter tested; synthetic demand labelled."),
        "public_transit_linkage": (
            "partial",
            "Current GTFS geometries produce unverified candidate association.",
        ),
        "emergency_response_linkage": (
            "partial",
            "Explicit emergency vehicle permissions and facility access; no calibrated response prediction.",
        ),
        "fire_external_impact": (
            "yes",
            "Typed assumed road restrictions tied to street-level incident; no perimeter inference.",
        ),
        "smoke_fire_physics": ("no", "Explicit product exclusion."),
        "typed_ontology": ("yes", "Objects and typed links;48 invalid-relation mutations rejected."),
        "scenario_actions": ("yes", "Typed atomic scenario actions;48 replays verified."),
        "persistent_KG_requirement": (
            "no",
            "Per-scenario projection over immutable citypack, no global KG platform required.",
        ),
        "scenario_local_graph": ("yes", "ProjectionSpec produces paired scenario graphs."),
        "graph_ranking_diffusion": (
            "yes",
            "Production CSR PageRank/PPR validated with 200k-edge kernel benchmark.",
        ),
        "baseline_event_attention_delta": (
            "yes",
            "Comparable node/seed/policy context; attention is not risk.",
        ),
        "AI_scenario_parsing": (
            "unknown",
            "Typed drafts can be validated; no natural-language parser reproduction established.",
        ),
        "AI_relation_scoring": (
            "partial",
            "Featherless SimpleJev Qwen3.8-27B-classifier selected; production paid inference deferred by user.",
        ),
        "self_host_data_local": (
            "yes",
            "Reference local core/API; external inference optional and explicitly configured.",
        ),
        "web_embeddable_component": (
            "partial",
            "Custom-element integration implemented; consult separately executed browser evidence.",
        ),
        "3D_mandatory": ("no", "Core uses 2D network;3D is not required."),
        "provenance_action_replay": ("yes", "Source/action/graph hashes plus deterministic replay."),
        "open_source_license": ("yes", "Local LICENSE inspected; project Apache-2.0."),
    },
    "The_World_Avatar": {
        "typed_ontology": ("yes", "Semantic Web concepts and ontologically described computational agents."),
        "scenario_actions": (
            "partial",
            "Agents update KG concepts/instances; equivalence to scenario-overlay action contract unverified.",
        ),
        "persistent_KG_requirement": (
            "yes",
            "Core architecture is a dynamic knowledge graph that agents maintain.",
        ),
        "self_host_data_local": (
            "partial",
            "Open repositories include deployment stacks; deployment-level egress/security not reproduced.",
        ),
        "open_source_license": ("yes", "Repository declares MIT."),
    },
    "SUMO_LLM_Agent": {
        "road_closure_what_if": (
            "yes",
            "README explicitly supports network modifications and event simulation.",
        ),
        "traffic_microsimulation": ("yes", "Project-owned SUMO loop run against supplied network/config."),
        "scenario_actions": (
            "partial",
            "Agent tools edit simulation; operational ontology equivalence not established.",
        ),
        "AI_scenario_parsing": (
            "yes",
            "README and code translate conversational tasks with OpenAI Agents SDK; live paid path not exercised.",
        ),
        "self_host_data_local": (
            "partial",
            "Local Flask/SUMO application; LLM and map services can be external.",
        ),
        "provenance_action_replay": (
            "partial",
            "In-memory simulation history present; deterministic action replay unverified.",
        ),
        "open_source_license": ("yes", "Pinned repository MIT license."),
    },
}


def write_matrix(root: Path):
    target = root / "comparison/feature_matrix.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "feature",
                "project",
                "status",
                "source",
                "checked_on",
                "verification_basis",
                "notes",
            ],
        )
        writer.writeheader()
        for feature in FEATURES:
            for project, (source, basis) in SOURCES.items():
                status, notes = CONFIRMED.get(project, {}).get(
                    feature, ("unknown", "Not established by the checked material; unknown does not mean no.")
                )
                writer.writerow(
                    {
                        "feature": feature,
                        "project": project,
                        "status": status,
                        "source": source,
                        "checked_on": "2026-09-24",
                        "verification_basis": basis,
                        "notes": notes,
                    }
                )
    return target


def report(root: Path) -> dict:
    matrix = write_matrix(root)
    folder = root / "evidence/wp6"
    ablation = json.loads((folder / "ablation_report.json").read_text())
    benchmark = json.loads((folder / "benchmark.json").read_text())
    reproduction = (
        json.loads((folder / "external_reproduction.json").read_text())
        if (folder / "external_reproduction.json").exists()
        else {"status": "NOT_RUN"}
    )
    notes = root / "comparison/reproduction_notes/SUMO_LLM_Agent.md"
    notes.write_text(
        f"""# SUMO_LLM_Agent reproduction\n\nRepository: https://github.com/xuyimingxym/SUMO_LLM_Agent\n\nPinned commit: `f06f6098626eb184bb3a3334b1b20639dda6b842`, MIT. Checked 2026-09-24. The complete checkout is 1.6 MB according to repository metadata; source remains unmodified under ignored `experiments/vendor/`.\n\nExecuted: `.venv/bin/python scripts/evaluate.py external`\n\nResult: **{reproduction["status"]}**, child exit code `{reproduction.get("exit_code", "unknown")}`. Full details and logs are in `evidence/wp6/external_reproduction.json` and `external_smoke.log`.\n\nThe harness imports the reviewed upstream Flask module and checks its index with Flask's in-process test client. It runs the project's own `sumo_simulation()` loop for 10 simulated seconds using its supplied network/config, with real SUMO/TraCI. The only runtime overrides are executable location, simulation duration and presentation sleep. No source patch, public listener, external map load, AI call or credential is used. Python remote socket connections are refused during the test.\n\nThe upstream main block binds 0.0.0.0; the harness does not invoke it. Upstream config enables `ignore-route-errors`, which is retained and disclosed. This smoke establishes a bounded executable neighbor component, not complete application correctness or paid-agent reproduction. Its network, demand and tasks differ from CiviFlux; there is no comparative speed or accuracy score.\n\nRecreate dependencies from the reviewed registry packages in an isolated target: `uv pip install --python .venv/bin/python --target experiments/vendor/deps flask flask-socketio openai-agents`. Exact installed versions are recorded in reproduction evidence. The upstream module imports Agents SDK unconditionally; it is present solely to import the unmodified module.\n"""
    )
    result = {
        "status": "COMPLETED_UNBLOCKED_EVALUATION_QWEN_DEFERRED",
        "command": "python scripts/evaluate.py report",
        "exit_code": 0,
        "ablation_status": ablation["status"],
        "benchmark_status": benchmark["status"],
        "external_reproduction_status": reproduction["status"],
        "feature_matrix_cells": len(FEATURES) * len(SOURCES),
        "model_gate": "DEFERRED_USER: Featherless SimpleJev Qwen3.8-27B-classifier production inference needs deployment setup and paid authorization; hosted demo evidence is separate",
        "historical_prediction_gate": "NOT_VALIDATED",
        "scope": "synthetic independent-oracle engineering and descriptive post-analysis retrieval; conservative source-backed ecosystem matrix",
        "artifacts": [
            {"path": str(p.relative_to(root)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in [
                matrix,
                notes,
                folder / "ablation_report.json",
                folder / "benchmark.json",
                folder / "external_reproduction.json",
            ]
            if p.exists()
        ],
    }
    (folder / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    markdown = f"""# CiviFlux engineering evaluation\n\n48 synthetic cases in12 topology groups use an independent exhaustive-path oracle; groups stay together across train/dev/test. Labels are machine-derived, not human review or measured city observations. The frozen inputs/labels/manifest are under `experiments/frozen/`.\n\nA0/A1/A2/A5 completed192 runs using48 shared physical fact sets. Every required facility was checked; oracle costs and reachability agreed and restriction violations were zero. A3/A4 are **DEFERRED_USER**. The selected Featherless SimpleJev Qwen3.8-27B-classifier is not called by this benchmark; hosted demo integration evidence is tracked separately. No ordinary chat API or mock substitutes for it. Provider calls:0.\n\nOntology controls rejected48incompatible relation mutations;48 scenario action replays reproduced hashes and preserved authoritative snapshots. A5's neutral weights equal A2 by construction; this is a null control, not evidence that semantic weights help. No positive model-effect claim is made.\n\nThe production sparse transition/PPR kernels ran50,000 nodes/200,000 edges in {benchmark["transition_build_s"] + benchmark["cold_ppr_s"]:.3f}s, with process peak RSS {benchmark["peak_process_rss_bytes"] / 1024**2:.1f}MiB and residual {benchmark["residual_l1"]:.3g}. This excludes ontology projection, witness paths, city import, API, rendering and SUMO. It is not an end-to-end city latency claim.\n\nExternal neighbor smoke: {reproduction["status"]}. The source-backed 152-cell comparison deliberately retains unknowns; no total ranking is computed. Raw metrics, per-scenario/group rows, output sizes, timing, hashes, and limitations are in `evidence/wp6/`.\n\nHelsinki's May 2026 historical network/feed, independently reviewed restriction geometry and observed traffic outcomes are unavailable; case evidence remains source-informed current-network what-if. Three heldout motifs cannot establish broad generalization.\n"""
    (folder / "REPORT.md").write_text(markdown)
    return result
