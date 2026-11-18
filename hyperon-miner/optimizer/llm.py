"""LLM-backed configuration proposal with an explicit offline fallback.

Main responsibility: request valid experiment configurations from supported
providers; offline fallback is available only to callers that explicitly opt in.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Any

from .miner import deterministic_candidates, validate_config
from .models import Config, DatasetProfile, RunResult


SUPPORTED_LLM_PROVIDERS = {"gemini", "openai", "auto"}


# Read and validate the requested provider.
def configured_llm_provider() -> str:
    provider = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    if provider not in SUPPORTED_LLM_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
        raise ValueError(f"LLM_PROVIDER must be one of: {supported}")
    return provider


# Resolve credentials while respecting provider priority.
def llm_api_key() -> tuple[str | None, str]:
    provider = configured_llm_provider()
    if provider in {"gemini", "auto"}:
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            return gemini_key, "gemini"
    if provider in {"openai", "auto"}:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            return openai_key, "openai"
    return None, provider


# Ask the provider for configurations. The CLI requires a real provider response
# by default; direct callers can leave ``require_live`` false for offline tests
# or explicitly local fallback workflows.
def llm_candidates(
    profile: DatasetProfile,
    previous: list[RunResult],
    limit: int,
    *,
    require_live: bool = False,
) -> tuple[list[Config], dict[str, Any]]:
    key, provider_kind = llm_api_key()
    if not key:
        if require_live:
            raise RuntimeError(
                f"{provider_kind} credentials are required for a live LLM experiment"
            )
        return deterministic_candidates(profile, limit), {
            "provider": "deterministic-fallback",
            "requested_provider": provider_kind,
            "real_llm": False,
        }
    prompt = {
        "dataset": asdict(profile),
        # Keep the provider on configuration/run metadata only. In particular,
        # do not send parsed supports, pattern identities, or raw miner output.
        "previous_runs": [
            {
                "config": run.config,
                "status": run.status,
                "elapsed_seconds": run.elapsed_seconds,
                "peak_memory_mb": run.peak_memory_mb,
                "has_error": run.error is not None,
            }
            for run in previous
        ],
        "schema": {"configurations": [{"min_support": 1, "depth": 0,
                                        "mode": "none", "normalization": "none",
                                        "db_ratio": "none", "conj_exp": True,
                                        "init_pattern": "$x"}]},
        "instruction": "Return JSON only. Suggest valid PeTTa miner configurations; do not invent mining results.",
    }
    default_model = "gemini-3.1-flash-lite" if provider_kind == "gemini" else "gpt-4o-mini"
    model_variable = "GEMINI_MODEL" if provider_kind == "gemini" else "OPENAI_MODEL"
    model = os.environ.get(model_variable, default_model)
    if provider_kind == "gemini":
        model = model.removeprefix("models/")
        endpoint = os.environ.get(
            "GEMINI_BASE_URL",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        )
        body = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": (
                "You are a cautious experiment planner. "
                "Return JSON only. Do not invent mining results.\n"
                + json.dumps(prompt)
            )}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "maxOutputTokens": 512,
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "configurations": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "min_support": {"type": "INTEGER"},
                                    "depth": {"type": "INTEGER"},
                                    "mode": {"type": "STRING", "enum": ["none"]},
                                    "normalization": {"type": "STRING", "enum": ["none"]},
                                    "db_ratio": {"type": "STRING", "enum": ["none"]},
                                    "conj_exp": {"type": "BOOLEAN"},
                                    "init_pattern": {"type": "STRING", "enum": ["$x"]},
                                },
                                "required": [
                                    "min_support",
                                    "depth",
                                    "mode",
                                    "normalization",
                                    "db_ratio",
                                    "conj_exp",
                                    "init_pattern",
                                ],
                            },
                        },
                    },
                    "required": ["configurations"],
                },
            },
        }).encode()
    else:
        endpoint = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
        body = json.dumps({"model": model,
                           "temperature": 0, "response_format": {"type": "json_object"},
                           "messages": [{"role": "system", "content": "You are a cautious experiment planner."},
                                        {"role": "user", "content": json.dumps(prompt)}]}).encode()
    request = urllib.request.Request(
        endpoint,
        data=body, headers={"Content-Type": "application/json"})
    if provider_kind == "gemini":
        request.add_header("x-goog-api-key", key)
    else:
        request.add_header("Authorization", "Bearer " + key)
    finish_reason: str | None = None
    try:
        retryable_statuses = {408, 429, 500, 502, 503, 504}
        max_retries = max(0, int(os.environ.get("LLM_RETRIES", "2")))
        for attempt in range(max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as exc:
                if exc.code not in retryable_statuses or attempt == max_retries:
                    raise
                time.sleep(2 ** attempt)
        if provider_kind == "gemini":
            content = payload["candidates"][0]["content"]["parts"][0]["text"]
            finish_reason = payload["candidates"][0].get("finishReason")
            usage = payload.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount")
            completion_tokens = usage.get("candidatesTokenCount")
        else:
            content = payload["choices"][0]["message"]["content"]
            usage = payload.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
        items = json.loads(content).get("configurations", [])
        configs = [Config(**item) for item in items[:limit]]
        if not configs:
            raise ValueError("provider returned no configurations")
        for config in configs:
            errors = validate_config(config, profile)
            if errors:
                raise ValueError(f"provider returned invalid configuration: {'; '.join(errors)}")
        provider_name = "gemini" if provider_kind == "gemini" else "openai-compatible"
        return configs, {"provider": provider_name, "model": model,
                         "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                         "finish_reason": finish_reason, "real_llm": True}
    except Exception as exc:
        error = str(exc)
        if isinstance(exc, urllib.error.HTTPError):
            details = exc.read().decode("utf-8", errors="replace")
            if details:
                error = f"{error}: {details}"
        safe_error = error.replace(key, "[redacted]")
        if require_live:
            raise RuntimeError(
                f"live {provider_kind} request failed: {safe_error}"
            ) from exc
        return deterministic_candidates(profile, limit), {
            "provider": "fallback-after-llm-error",
            "model": model,
            "endpoint": endpoint,
            "error": safe_error,
            "finish_reason": finish_reason,
            "fallback_count": 1,
            "real_llm": False,
        }
