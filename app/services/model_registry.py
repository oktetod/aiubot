"""# app/services/model_registry.py
# Registry of model capabilities and helper utilities
# Only include user-specified models and the NVIDIA RAG model.

from typing import Dict, Any, List

MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    # Cerebras model
    "cerebras/llama-4-maverick-17b-128e-instruct": {
        "family": "cerebras",
        "max_tokens": 131072,
        "streaming": True,
        "recommended_temperature": 0.7,
    },

    # GPT-OSS model (assumed available via generic API / Cerebras if integrated)
    "gpt-oss-120b": {
        "family": "oss",
        "max_tokens": 65536,
        "streaming": False,
        "recommended_temperature": 0.7,
    },

    # Qwen family
    "qwen-3-235b-a22b-thinking-2507": {
        "family": "qwen",
        "max_tokens": 65536,
        "streaming": False,
        "recommended_temperature": 0.7,
    },
    "qwen-3-coder-480b": {
        "family": "qwen",
        "max_tokens": 65536,
        "streaming": False,
        "recommended_temperature": 0.7,
    },
    "qwen-3-235b-a22b-instruct-2507": {
        "family": "qwen",
        "max_tokens": 65536,
        "streaming": False,
        "recommended_temperature": 0.7,
    },

    # NVIDIA RAG model via OpenAI-compatible client
    "nvidia/llama-3.1-nemotron-ultra-253b-v1": {
        "family": "nvidia",
        "max_tokens": 65536,
        "streaming": True,
        "recommended_temperature": 0.6,
    }
}

# Use the order provided by the user for chaining
DEFAULT_MODEL_SEQUENCE: List[str] = [
    "cerebras/llama-4-maverick-17b-128e-instruct",
    "gpt-oss-120b",
    "qwen-3-235b-a22b-thinking-2507",
    "qwen-3-coder-480b",
    "qwen-3-235b-a22b-instruct-2507",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
]


def get_model_capability(model_id: str) -> Dict[str, Any]:
    return MODEL_CAPABILITIES.get(model_id, {
        "family": "unknown",
        "max_tokens": 4096,
        "streaming": False,
        "recommended_temperature": 0.7
    })


def choose_model(preferred_family: str = "", hints: List[str] = None) -> str:
    """
    Backwards-compatible picker; returns first in DEFAULT_MODEL_SEQUENCE or a hinted model.
    """
    hints = hints or []
    for h in hints:
        if h in MODEL_CAPABILITIES:
            return h
    # return first available in DEFAULT_MODEL_SEQUENCE
    for m in DEFAULT_MODEL_SEQUENCE:
        if m in MODEL_CAPABILITIES:
            return m
    return next(iter(MODEL_CAPABILITIES.keys()))
"""