"""Explicit dated prices; estimates are planning aids, not billing guarantees."""

import math

import tiktoken

from .storage import dumps

# USD per million tokens; https://developers.openai.com/api/docs/pricing, 2026-09-14.
# Deliberately use inexpensive, snapshot-pinned baselines; selection is empirical.
PROFILES = {
    "nano": {"model": "gpt-5-nano-2025-08-07", "input": 0.05, "output": 0.40, "reasoning": "low"},
    "nano-baseline": {"model": "gpt-4.1-nano-2025-04-14", "input": 0.10, "output": 0.40},
    "mini": {"model": "gpt-5-mini-2025-08-07", "input": 0.25, "output": 2.00, "reasoning": "low"},
    "mini-baseline": {"model": "gpt-4.1-mini-2025-04-14", "input": 0.40, "output": 1.60},
    "luna": {"model": "gpt-5.6-luna", "input": 0.20, "output": 1.20, "reasoning": "medium"},
    "reviewer": {"model": "gpt-5.4-2026-03-05", "input": 2.50, "output": 15.00, "reasoning": "low"},
    "reviewer-baseline": {"model": "gpt-4.1-2025-04-14", "input": 2.00, "output": 8.00},
}
PRICE_DATE = "2026-09-14"


def profile(name, model=None, input_rate=None, output_rate=None):
    selected = dict(PROFILES[name])
    if model:
        if input_rate is None or output_rate is None:
            raise ValueError(
                "Custom models require --input-rate and --output-rate (standard USD/1M)"
            )
        selected.update(model=model, input=input_rate, output=output_rate)
        selected.pop("reasoning", None)
    elif input_rate is not None or output_rate is not None:
        raise ValueError("Use --model when overriding prices")
    if any(not math.isfinite(selected[k]) or selected[k] < 0 for k in ("input", "output")):
        raise ValueError("Token prices must be finite and nonnegative")
    return selected


def estimate(requests, rates, batch=True):
    encoding = tiktoken.get_encoding("o200k_base")
    # Count the full serialized body (including schema); add 15% and per-request overhead.
    inputs = sum(
        int(len(encoding.encode(dumps(r["body"]), disallowed_special=())) * 1.15) + 128
        for r in requests
    )
    outputs = sum(r["body"]["max_output_tokens"] for r in requests)
    factor = 0.5 if batch else 1.0
    return {
        "requests": len(requests),
        "input_tokens_estimate": inputs,
        "output_token_cap": outputs,
        "estimated_usd_at_output_cap": round(
            (inputs * rates["input"] + outputs * rates["output"]) / 1_000_000 * factor, 6
        ),
        "pricing_date": PRICE_DATE,
        "batch": batch,
        "note": "Padded tokenizer estimate plus output cap; not an API-enforced dollar limit. No cache discount assumed.",
    }


def usage_cost(usage, rates, batch):
    return (
        (
            usage.get("input_tokens", 0) * rates["input"]
            + usage.get("output_tokens", 0) * rates["output"]
        )
        / 1_000_000
        * (0.5 if batch else 1)
    )
