"""Pipelines de orquestração ETL."""

from src.pipelines.run_pipeline import (
    run_bcb_extraction,
    run_coingecko_extraction,
    run_consolidation,
    run_all,
)

__all__ = [
    "run_bcb_extraction",
    "run_coingecko_extraction",
    "run_consolidation",
    "run_all",
]
