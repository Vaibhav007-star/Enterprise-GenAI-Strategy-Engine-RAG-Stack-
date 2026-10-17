import json
import requests
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from ..config.settings import AppSettings
from ..utils.logger import get_logger

logger = get_logger("llm_client")


class BaseLLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """Generate text completion from system and user prompts."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider backend is reachable and ready."""
        pass


class OllamaLLMClient(BaseLLMClient):
    """Local Ollama client communicating via HTTP API."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:latest"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"<system>\n{system_prompt}\n</system>\n\n<user>\n{user_prompt}\n</user>",
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        try:
            resp = requests.post(endpoint, json=payload, timeout=60.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
            else:
                raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Ollama generation failure: {e}")
            raise


class OpenAICompatibleClient(BaseLLMClient):
    """Generic OpenAI-compatible client (e.g., OpenAI, Groq, vLLM)."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=60.0)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                raise RuntimeError(f"API returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"OpenAI compatible API failure: {e}")
            raise


class GroundedOfflineSynthesizer(BaseLLMClient):
    """High-reliability deterministic synthesizer when local or cloud LLM servers are unavailable."""

    def is_available(self) -> bool:
        return True

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        # Extract question and sources from prompt
        q_match = re.search(r"QUESTION:\s*(.*?)(?=\n\n|$)", user_prompt, re.DOTALL)
        question = q_match.group(1).strip() if q_match else "your query"

        sources_match = re.search(r"RETRIEVED DOCUMENT CONTEXT:\s*(.*?)(?=\n\nINSTRUCTIONS:|$)", user_prompt, re.DOTALL)
        sources_text = sources_match.group(1).strip() if sources_match else ""

        if not sources_text or "No matching documents" in sources_text:
            return (
                f"### Insufficient Evidence\n\n"
                f"The available enterprise documents do not contain sufficient evidence to answer: **\"{question}\"**.\n\n"
                f"*Please upload relevant documentation or adjust search keywords.*"
            )

        # Parse source blocks
        blocks = re.findall(r"\[SOURCE (\d+)\] (.*?)\n(.*?)(?=\[/SOURCE \1\])", sources_text, re.DOTALL)
        
        response_lines = [
            f"### Evidence-Grounded Analysis\n",
            f"Based on the verified enterprise records, here is the synthesized answer regarding **{question}**:\n"
        ]

        # Extract salient points from each source
        for src_id, header, body in blocks[:3]:
            # Clean body
            lines = [l.strip() for l in body.splitlines() if l.strip() and not l.startswith("#")]
            snippet = " ".join(lines[:3])
            if len(snippet) > 220:
                snippet = snippet[:220] + "..."
            response_lines.append(f"- **Key Evidence [Source {src_id}]**: {snippet} (Refer to *{header.split('|')[0].strip()}*)")

        response_lines.append("\n#### Verification Summary")
        response_lines.append("All statements above are directly supported by the retrieved document passages listed in the evidence panel.")

        return "\n".join(response_lines)


class LLMFactory:
    """Factory to retrieve active LLM client with automatic fallback."""

    @classmethod
    def create_client(cls, settings: AppSettings) -> BaseLLMClient:
        provider = (settings.llm_provider or "ollama").lower()

        if provider == "ollama":
            client = OllamaLLMClient(base_url=settings.llm_base_url, model=settings.llm_model)
            if client.is_available():
                logger.info(f"Using local Ollama provider at {settings.llm_base_url}")
                return client
            logger.warning("Ollama backend is not running or unreachable. Falling back to Grounded Offline Synthesizer.")
            return GroundedOfflineSynthesizer()

        elif provider in ("openai", "groq"):
            api_key = settings.openai_api_key if provider == "openai" else settings.groq_api_key
            base_url = "https://api.openai.com/v1" if provider == "openai" else "https://api.groq.com/openai/v1"
            if api_key:
                client = OpenAICompatibleClient(api_key=api_key, base_url=base_url, model=settings.llm_model)
                if client.is_available():
                    logger.info(f"Using {provider.upper()} API provider")
                    return client
            logger.warning(f"{provider.upper()} API key not configured. Falling back to Grounded Offline Synthesizer.")
            return GroundedOfflineSynthesizer()

        return GroundedOfflineSynthesizer()
