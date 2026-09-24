from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PRICING_FILE = Path(__file__).parent.parent / "data" / "pricing.json"

# Vendor-specific prefixes seen in session logs, e.g. "anthropic.claude-opus-5"
# on Bedrock or "vertex/claude-sonnet-5" on Google Cloud.
_VENDOR_PREFIXES = ("anthropic.", "anthropic/", "vertex/", "vertex_ai/", "bedrock/", "us.", "eu.", "global.")


@dataclass(frozen=True)
class Pricing:
    """USD per 1M tokens for one model, plus how it was resolved."""

    input: float
    output: float
    cache_write: float
    cache_read: float
    match: str  # "exact" | "prefix" | "family" | "default"

    @property
    def is_known(self) -> bool:
        return self.match != "default"


@lru_cache(maxsize=1)
def _table() -> dict:
    return json.loads(PRICING_FILE.read_text())


def _normalize(model: str) -> str:
    name = model.strip().lower()
    for prefix in _VENDOR_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Bedrock/Vertex suffixes: claude-haiku-4-5@20251001, ...-v1:0
    for sep in ("@", ":"):
        name = name.split(sep)[0]
    return name


@lru_cache(maxsize=256)
def resolve_pricing(model: str | None) -> Pricing:
    """Resolve prices for a model id, falling back to its family, then a default.

    Model ids are pinned snapshots (``claude-sonnet-4-5-20250929``), so an exact
    table entry is rare; matching the longest known prefix keeps dated ids and
    future point releases priced correctly.
    """
    table = _table()
    models: dict[str, dict[str, float]] = table["models"]

    if model:
        name = _normalize(model)
        if name in models:
            return Pricing(**models[name], match="exact")
        for key in sorted(models, key=len, reverse=True):
            if name.startswith(key):
                return Pricing(**models[key], match="prefix")
        for family, prices in table["families"].items():
            if family in name:
                return Pricing(**prices, match="family")

    return Pricing(**table["default"], match="default")


def calculate_cost(
    tokens_in: int,
    tokens_out: int,
    model: str | None = None,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """Calculate cost in USD. Prices are per 1M tokens."""
    prices = resolve_pricing(model)
    return (
        tokens_in * prices.input
        + tokens_out * prices.output
        + cache_creation_tokens * prices.cache_write
        + cache_read_tokens * prices.cache_read
    ) / 1_000_000


def default_model() -> str:
    return _table()["default_model"]


def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 characters per token."""
    return max(1, len(text) // 4)
