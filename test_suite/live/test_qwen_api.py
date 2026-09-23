"""Explicitly opt-in paid Qwen smoke. A skip leaves the live release gate blocked."""
import json
import os
from pathlib import Path

import pytest
from adapters.system_one import QwenAPIBackend, QwenAPIConfig


@pytest.mark.live
def test_real_qwen_api_typed_scores():
    if os.environ.get("QWEN_API_LIVE_TEST") != "1":
        pytest.skip("BLOCKED_API_SETUP: live paid calls need explicit QWEN_API_LIVE_TEST=1 and configured budget")
    config = QwenAPIConfig.from_env(Path(".env"), cache_dir=None)
    backend = QwenAPIBackend(config)
    policy = backend.score_relations("facility_access", {
        "ACCESS_FOR": "A road segment is on a verified access path to a facility.",
        "ADMIN_METADATA": "An entity appears in the same administrative file."})
    assert policy["provider_mode"] == "qwen_api"
    assert backend.last_provenance["api_call_this_run"]
    assert set(policy["scores"]) == {"ACCESS_FOR", "ADMIN_METADATA"}
    out = Path("evidence/wp3/systemone_api_live_protocol.json"); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"scope": "real paid API typed protocol only; graph/evaluation gate separate",
        "status": "PASS_PROTOCOL_ONLY", "policy": policy, "provenance": backend.last_provenance}, indent=2)+"\n")
