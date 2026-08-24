"""Configuration loading and project path resolution.

A single ``Config`` object is threaded through the pipeline so that no module
hard-codes a fiscal year, a filesystem path, or an analytical assumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "pipeline.yml"


@dataclass(frozen=True)
class Config:
    """Immutable view over ``config/pipeline.yml`` plus derived project paths."""

    raw: dict[str, Any]
    root: Path

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, path: Path | str | None = None) -> Config:
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not cfg_path.exists():
            raise FileNotFoundError(f"Pipeline config not found: {cfg_path}")
        with cfg_path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return cls(raw=raw, root=cfg_path.parent.parent)

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    # ------------------------------------------------------------ shortcuts
    @property
    def fiscal_years(self) -> list[int]:
        return list(self.raw["project"]["fiscal_years"])

    @property
    def base_fy(self) -> int:
        return int(self.raw["project"]["base_fiscal_year"])

    @property
    def latest_fy(self) -> int:
        return int(self.raw["project"]["latest_fiscal_year"])

    @property
    def award_type_codes(self) -> list[str]:
        return list(self.raw["source"]["award_type_codes"])

    # --------------------------------------------------------------- paths
    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "raw" / "_api_cache"

    @property
    def interim_dir(self) -> Path:
        return self.data_dir / "interim"

    @property
    def curated_dir(self) -> Path:
        return self.data_dir / "curated"

    @property
    def samples_dir(self) -> Path:
        return self.data_dir / "samples"

    @property
    def outputs_dir(self) -> Path:
        return self.root / "outputs"

    @property
    def figures_dir(self) -> Path:
        return self.outputs_dir / "figures"

    @property
    def tables_dir(self) -> Path:
        return self.outputs_dir / "tables"

    @property
    def docs_dir(self) -> Path:
        return self.root / "docs"

    @property
    def warehouse_path(self) -> Path:
        return self.curated_dir / "fedspend.duckdb"

    # -------------------------------------------------------- code lookups
    @cached_property
    def competed_codes(self) -> list[str]:
        return list(self.raw["competition"]["competed"])

    @cached_property
    def not_competed_codes(self) -> list[str]:
        return list(self.raw["competition"]["not_competed"])

    @cached_property
    def all_competition_codes(self) -> list[str]:
        return self.competed_codes + self.not_competed_codes

    @cached_property
    def pricing_bucket_by_code(self) -> dict[str, str]:
        """Map every FPDS pricing code to its risk bucket name."""
        out: dict[str, str] = {}
        for bucket, codes in self.raw["pricing_risk"].items():
            for code in codes:
                out[str(code)] = bucket
        return out

    @cached_property
    def all_pricing_codes(self) -> list[str]:
        return list(self.pricing_bucket_by_code)

    @property
    def setaside_codes(self) -> list[str]:
        return list(self.raw["small_business_setaside_codes"])

    def ensure_dirs(self) -> None:
        for d in (
            self.raw_dir,
            self.cache_dir,
            self.interim_dir,
            self.curated_dir,
            self.samples_dir,
            self.figures_dir,
            self.tables_dir,
            self.docs_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
