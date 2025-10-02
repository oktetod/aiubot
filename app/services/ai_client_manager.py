"""
# app/services/ai_client_manager.py
# New modular AIClientManager that uses model_registry for capability-aware model selection

import asyncio
import logging
from typing import List, Dict, Optional

from app.services.model_registry import choose_model, get_model_capability, DEFAULT_MODEL_SEQUENCE
from app.core.config import settings

# Import vendor clients lazily to avoid import issues during tests if not configured
try:
    from cerebras.cloud.sdk import Cerebras
except Exception:
    Cerebras = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

logger = logging.getLogger(__name__)

class AIClientManager:
    """Manages AI clients with failover and model capability awareness"""

    def __init__(self):
        self.cerebras_client = None
        self.nvidia_client = None
        self.active_clients = {}
        self.init_clients()

    def init_clients(self):
        """Initialize AI clients and register available families"""
        # Initialize Cerebras client
        try:
            if getattr(settings, 'CEREBRAS_API_KEY', None) and Cerebras:
                self.cerebras_client = Cerebras(api_key=settings.CEREBRAS_API_KEY)
                self.active_clients['cerebras'] = self.cerebras_client
                logger.info("✅ Cerebras client initialized")
            else:
                logger.warning("⚠️ CEREBRAS_API_KEY not configured or Cerebras SDK not installed")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Cerebras client: {e}")

        # Initialize NVIDIA/OpenAI client
        try:
            if getattr(settings, 'NVIDIA_API_KEY', None) and OpenAI:
                self.nvidia_client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=settings.NVIDIA_API_KEY
                )
                self.active_clients['nvidia'] = self.nvidia_client
                logger.info("✅ NVIDIA client initialized")
            else:
                logger.warning("⚠️ NVIDIA_API_KEY not configured or OpenAI SDK not installed")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NVIDIA client: {e}")

        if not self.active_clients:
            logger.error("❌ No AI clients available! Check API keys.")
            # Do not raise here to keep process startable; callers should handle missing clients.

    async def _call_with_client(self, client, method_name: str, *args, **kwargs) -> Optional[Dict]:
        """Run blocking client call in threadpool and return standardized response dict."""
        try:
            func = getattr(client, method_name)
            response = await asyncio.to_thread(func, *args, **kwargs)
            # Normalize response where possible; callers expect keys: content, model, usage
            return {
                "content": getattr(response.choices[0].message, "content", response.choices[0].message.content),
                "model": getattr(response, "model", kwargs.get("model", "")),
                "usage": getattr(response, "usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
            }
        except Exception as e:
            logger.error(f"Error calling client {client}: {e}")
            return None

    async def call_model(self, messages: List[Dict], model_id: str, max_tokens: int = 4096, temperature: float = 0.7, stream: bool = False) -> Optional[Dict]:
        """Call a specific model by id, selecting the correct client behind it."""
        cap = get_model_capability(model_id)
        fam = cap.get("family", "")
        # Select client by family
        if fam == "cerebras" and self.cerebras_client:
            try:
                # cerebras client uses chat.completions.create API in current repo
                return await self._call_with_client(self.cerebras_client.chat.completions, 'create', messages=messages, model=model_id, max_tokens=max_tokens, temperature=temperature, stream=False)
            except Exception as e:
                logger.error(f"Error calling cerebras model {model_id}: {e}")
                return None

        if fam in ("nvidia", "openai") and self.nvidia_client:
            try:
                return await self._call_with_client(self.nvidia_client.chat.completions, 'create', messages=messages, model=model_id, max_tokens=max_tokens, temperature=temperature, stream=False)
            except Exception as e:
                logger.error(f"Error calling nvidia/openai model {model_id}: {e}")
                return None

        # If no matching client available, return None
        logger.warning(f"No client available for model family {fam}")
        return None

    async def call_best_available(self, messages: List[Dict], model_hint: str = "", max_tokens: int = 4096, temperature: float = 0.7, stream: bool = False) -> Optional[Dict]:
        """Choose the best available model according to the registry and try with failover.
        model_hint can be a family hint ('cerebras') or specific model id."""
        # If hint is a family name (e.g., 'cerebras'), try to choose a model from that family
        preferred_family = ""
        hints = []
        if model_hint:
            if model_hint.lower() in ("cerebras", "nvidia", "openai"):
                preferred_family = model_hint.lower()
            else:
                hints.append(model_hint)

        # Choose a candidate model id
        candidate = choose_model(preferred_family=preferred_family, hints=hints)

        tried = set()
        # Try candidate list in order of DEFAULT_MODEL_SEQUENCE, but prefer candidate first
        ordered = [candidate] + [m for m in DEFAULT_MODEL_SEQUENCE if m != candidate]

        for model_id in ordered:
            if model_id in tried:
                continue
            tried.add(model_id)

            cap = get_model_capability(model_id)
            model_max_tokens = min(max_tokens, cap.get("max_tokens", max_tokens))
            temp = temperature if temperature is not None else cap.get("recommended_temperature", 0.7)

            logger.info(f"Attempting model {model_id} (max_tokens={model_max_tokens})")
            result = await self.call_model(messages, model_id, max_tokens=model_max_tokens, temperature=temp, stream=stream)
            if result:
                return result

        logger.error("❌ All AI clients/models failed in call_best_available")
        return None

    async def call_models_sequential(self, messages: List[Dict], model_ids: List[str],
                                     max_tokens: int = 4096, temperature: float = 0.7, stream: bool = False) -> List[Dict]:
        """Call given model_ids in order, return list of responses (dict per model).
        Each response is normalized (content, model, usage) or {'error': ...} on failure."""
        results = []
        for model_id in model_ids:
            cap = get_model_capability(model_id)
            per_max = min(max_tokens, cap.get("max_tokens", max_tokens))
            try:
                resp = await self.call_model(messages, model_id, max_tokens=per_max, temperature=temperature, stream=stream)
                if resp:
                    results.append({"model": model_id, "response": resp})
                    # append assistant content for subsequent calls
                    assistant_content = resp.get("content", "")
                    if assistant_content:
                        messages.append({"role": "assistant", "content": assistant_content})
                else:
                    results.append({"model": model_id, "response": None, "error": "no_response"})
            except Exception as e:
                results.append({"model": model_id, "response": None, "error": str(e)})
        return results
"""