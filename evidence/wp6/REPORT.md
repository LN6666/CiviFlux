# CiviFlux engineering evaluation

48 synthetic cases in12 topology groups use an independent exhaustive-path oracle; groups stay together across train/dev/test. Labels are machine-derived, not human review or measured city observations. The frozen inputs/labels/manifest are under `experiments/frozen/`.

A0/A1/A2/A5 completed192 runs using48 shared physical fact sets. Every required facility was checked; oracle costs and reachability agreed and restriction violations were zero. A3/A4 are **DEFERRED_USER**. The selected Featherless SimpleJev Qwen3.8-27B-classifier is not called by this benchmark; hosted demo integration evidence is tracked separately. No ordinary chat API or mock substitutes for it. Provider calls:0.

Ontology controls rejected48incompatible relation mutations;48 scenario action replays reproduced hashes and preserved authoritative snapshots. A5's neutral weights equal A2 by construction; this is a null control, not evidence that semantic weights help. No positive model-effect claim is made.

The production sparse transition/PPR kernels ran50,000 nodes/200,000 edges in 0.270s, with process peak RSS 192.7MiB and residual 7.76e-13. This excludes ontology projection, witness paths, city import, API, rendering and SUMO. It is not an end-to-end city latency claim.

External neighbor smoke: PASS_BOUNDED_EXTERNAL_SMOKE. The source-backed 152-cell comparison deliberately retains unknowns; no total ranking is computed. Raw metrics, per-scenario/group rows, output sizes, timing, hashes, and limitations are in `evidence/wp6/`.

Helsinki's May 2026 historical network/feed, independently reviewed restriction geometry and observed traffic outcomes are unavailable; case evidence remains source-informed current-network what-if. Three heldout motifs cannot establish broad generalization.
