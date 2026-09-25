from datetime import timedelta

import pytest

from scripts.freeze_berlin_incremental_probe import CUTOFF, freeze


@pytest.mark.parametrize("when", [CUTOFF, CUTOFF + timedelta(seconds=1)])
def test_pre_onset_probe_refuses_retroactive_freeze(tmp_path, when):
    with pytest.raises(ValueError, match="window has closed"):
        freeze(tmp_path, now=when)
    assert not (tmp_path / "evidence/events/berlin-2026-incremental-pre-onset-probe.json").exists()
