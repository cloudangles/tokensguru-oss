"""Provider adapter registry.

Usage:
    from providers import get_adapter, REGISTRY
    adapter = get_adapter("openai")
    url = adapter.endpoint_url("/v1/chat/completions")
    headers = {**adapter.auth_headers(api_key), **adapter.extra_headers()}

8 providers in this OSS edition: openai, anthropic, groq, deepseek, google
(Gemini), ollama, openrouter, together. Azure/Vertex/Bedrock are not
included -- they require multi-tenant credential-vault/cloud-IAM machinery
(STS role assumption, ADC token minting) that doesn't fit a single-tenant
self-host; see docs/OSS_FEATURE_MATRIX.md.
"""
from __future__ import annotations

from providers.base import ProviderAdapter
from providers.openai_adapter import OpenAIAdapter
from providers.anthropic_adapter import AnthropicAdapter
from providers.deepseek_adapter import DeepSeekAdapter
from providers.groq_adapter import GroqAdapter
from providers.gemini_adapter import GeminiAdapter
from providers.openrouter_adapter import OpenRouterAdapter
from providers.together_adapter import TogetherAdapter
from providers.ollama_adapter import OllamaAdapter, is_ollama_model

_ollama = OllamaAdapter()

REGISTRY: dict[str, ProviderAdapter] = {
    "openai": OpenAIAdapter(),
    "anthropic": AnthropicAdapter(),
    "deepseek": DeepSeekAdapter(),
    "groq": GroqAdapter(),
    "google": GeminiAdapter(),
    "openrouter": OpenRouterAdapter(),
    "together": TogetherAdapter(),
    "ollama": _ollama,
    "self-hosted": _ollama,  # naming alias -> same adapter
}

_PROVIDER_ALIASES: dict[str, str] = {
    "gemini": "google",
    "self-hosted": "ollama",
}

_MODEL_PREFIX_MAP = [
    (("gpt-", "o1", "o3", "o4", "text-embedding-", "dall-e", "whisper-", "tts-"), "openai"),
    (("claude-",), "anthropic"),
    (("deepseek-",), "deepseek"),
    (("llama-", "mixtral-", "gemma"), "groq"),
    (("gemini-",), "google"),
]


def normalize_provider(provider: str) -> str:
    p = (provider or "").lower().strip()
    return _PROVIDER_ALIASES.get(p, p)


def get_adapter(provider: str) -> ProviderAdapter:
    """Return the adapter for the given provider name.

    Falls back to the OpenAI adapter for unknown providers (most third-party
    hosts are OpenAI-compatible).
    """
    p = normalize_provider(provider)
    return REGISTRY.get(p, REGISTRY["openai"])


def detect_provider(model: str) -> str:
    """Infer provider name from a model name/prefix."""
    m = (model or "").lower().strip()
    if m.startswith("openrouter/"):
        return "openrouter"
    if m.startswith("together/"):
        return "together"
    if m.startswith("ollama/") or m.startswith("self-hosted/"):
        return "ollama"
    for prefixes, provider in _MODEL_PREFIX_MAP:
        if any(m.startswith(p) for p in prefixes):
            return provider
    return "openai"


__all__ = [
    "ProviderAdapter", "OpenAIAdapter", "AnthropicAdapter", "DeepSeekAdapter",
    "GroqAdapter", "GeminiAdapter", "OpenRouterAdapter", "TogetherAdapter",
    "OllamaAdapter", "REGISTRY", "get_adapter", "detect_provider",
    "normalize_provider", "is_ollama_model",
]
