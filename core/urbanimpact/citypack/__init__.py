"""Versioned data-local citypack import and audit."""

from pathlib import Path


def load_citypack(path: Path):
    from urbanimpact.contracts import CityPack

    return CityPack.model_validate_json(Path(path).read_text())


__all__ = ["load_citypack"]
