"""
# Orchestrator to run all models in sequence (AI chaining) and insert DeepWebSearch results.
# Place this file at app/services/ai_chain_orchestrator.py

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.model_registry import DEFAULT_MODEL_SEQUENCE, get_model_capability
from app.services.ai_client_manager import AIClientManager
from app.services.code_validator import CodeCompletenessValidator
# Import deep search class if available
try:
    from app.services.cerebras_chain import DeepWebSearch
except Exception:
    DeepWebSearch = None

logger = logging.getLogger(__name__)

class AIChainOrchestrator:
    """
    Runs models sequentially (chaining). Flow:
    1) Build base messages (system + user + project context)
    2) Optionally run deep web search and inject top results into messages
    3) For each model in DEFAULT_MODEL_SEQUENCE:
       - call model with current messages
       - append assistant response to messages so next model sees it
       - record metadata
    4) Post-process final content and run validator
    """

    def __init__(self, ai_client: AIClientManager, deep_search: Optional[DeepWebSearch] = None):
        self.ai_client = ai_client
        self.deep_search = deep_search or (DeepWebSearch() if DeepWebSearch else None)
        # allow override of sequence if needed
        self.model_sequence = list(DEFAULT_MODEL_SEQUENCE)

    async def run_chain(self, base_messages: List[Dict[str, str]], 
                        project_context: str = "", filename_hint: str = "code.py",
                        use_deep_search: bool = True, max_tokens_per_model: int = 4096,
                        temperature: float = 0.7, stream: bool = False) -> Dict[str, Any]:
        start_time = datetime.utcnow()
        messages = list(base_messages)  # copy
        if project_context:
            messages.insert(0, {"role": "system", "content": f"PROJECT CONTEXT:\n{project_context}"})

        metadata = {
            "runs": [],
            "final_content": "",
            "validator": None,
            "processing_time": None,
        }

        # 1) Deep web search injection
        if use_deep_search and self.deep_search:
            try:
                # Perform a short deep search using the user's last user message as query
                user_query = ""
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        user_query = msg.get("content", "")
                        break
                if user_query:
                    search_results = await self.deep_search.deep_search(user_query, depth=1)
                    # Attach top 3 results to messages as system info
                    top = search_results[:3]
                    if top:
                        search_text = "\n\n".join([f"[{i+1}] {r.title}\n{r.url}\nSnippet: {r.snippet}" for i,r in enumerate(top)])
                        messages.insert(0, {"role": "system", "content": f"EXTERNAL SOURCES (top {len(top)}):\n{search_text}"})
                        metadata["runs"].append({"step": "deep_search", "sources": [ {"title": r.title, "url": r.url} for r in top ]})
            except Exception as e:
                logger.warning(f"Deep search failed or not available: {e}")

        # 2) Sequential model calls
        for model_id in self.model_sequence:
            # call each model in order; if model not available, ai_client will log and return None
            cap = get_model_capability(model_id)
            per_model_max_tokens = min(max_tokens_per_model, cap.get("max_tokens", max_tokens_per_model))
            try:
                logger.info(f"[orchestrator] Calling model {model_id}")
                resp = await self.ai_client.call_model(messages, model_id, max_tokens=per_model_max_tokens, temperature=temperature, stream=stream)
                if not resp or not resp.get("content"):
                    metadata["runs"].append({"model": model_id, "status": "failed", "note": "no response"})
                    continue

                content = resp["content"]
                # simple post-processing: strip common truncation markers
                content_clean = self._post_process_content(content)

                # append assistant reply so next model sees it
                messages.append({"role": "assistant", "content": content_clean})

                # record run metadata
                run_meta = {
                    "model": model_id,
                    "status": "ok",
                    "usage": resp.get("usage", {}),
                    "model_raw": resp.get("model", model_id)
                }
                metadata["runs"].append(run_meta)
            except Exception as e:
                logger.exception(f"Error calling model {model_id}: {e}")
                metadata["runs"].append({"model": model_id, "status": "error", "error": str(e)})
                # continue to next model

        # Final content is last assistant message if available
        final_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                final_content = msg.get("content", "")
                break

        metadata["final_content"] = final_content

        # 3) Validation
        try:
            validation = CodeCompletenessValidator.validate_completeness(final_content, filename_hint)
            metadata["validator"] = validation
        except Exception as e:
            metadata["validator"] = {"is_complete": False, "completeness_score": 0.0, "issues": [f"validator_error: {e}"], "warnings": []}

        metadata["processing_time"] = (datetime.utcnow() - start_time).total_seconds()
        return metadata

    def _post_process_content(self, content: str) -> str:
        # remove common markers and trim
        cleaned = content.replace("```", "")
        # strip truncation markers
        for m in ["# ... rest of code", "...", "[truncated]", "[TRUNCATED]", "# ... (rest omitted)"]:
            cleaned = cleaned.replace(m, "")
        return cleaned.strip()
"""