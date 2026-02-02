"""
LLM client abstraction using LangChain: OpenAI, Gemini, and placeholder for local models.
Supports configurable model/temperature, streaming/non-streaming, retry and rate limiting.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any

from app.config import get_settings


class LLMClient(ABC):
    """Abstract LLM client for chat completions."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Non-streaming completion; returns full response text."""
        pass

    @abstractmethod
    async def complete_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream completion chunks."""
        pass


def _make_messages(system_prompt: str, user_prompt: str) -> list[Any]:
    """Build LangChain message list from system + user prompts."""
    from langchain_core.messages import SystemMessage, HumanMessage
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=user_prompt))
    return messages


class LangChainChatClient(LLMClient):
    """LangChain-based client wrapping any LangChain chat model (OpenAI, Gemini, etc.)."""

    def __init__(
        self,
        model: Any,
        temperature: float = 0.2,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        min_interval: float = 0.5,
    ) -> None:
        self._model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._last_request_time: float = 0
        self._min_interval = min_interval

    def _wait_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> str:
        self._wait_rate_limit()
        messages = _make_messages(system_prompt, user_prompt)
        for attempt in range(self.max_retries):
            try:
                if hasattr(self._model, "ainvoke"):
                    result = await self._model.ainvoke(messages)
                else:
                    result = await __import__("asyncio").to_thread(self._model.invoke, messages)
                if hasattr(result, "content"):
                    text = result.content
                    if isinstance(text, list):
                        text = "".join(getattr(t, "text", str(t)) for t in text)
                    return (text or "").strip()
                return str(result).strip()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return f"[LLM error: {e}]"
                await __import__("asyncio").sleep(self.retry_delay * (attempt + 1))
        return ""

    async def complete_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        self._wait_rate_limit()
        messages = _make_messages(system_prompt, user_prompt)
        try:
            if hasattr(self._model, "astream"):
                async for chunk in self._model.astream(messages):
                    text = getattr(chunk, "content", None) or str(chunk)
                    if isinstance(text, list):
                        text = "".join(getattr(t, "text", str(t)) for t in text)
                    if text:
                        yield text
            else:
                for chunk in await __import__("asyncio").to_thread(
                    lambda: list(self._model.stream(messages))
                ):
                    text = getattr(chunk, "content", None) or str(chunk)
                    if isinstance(text, list):
                        text = "".join(getattr(t, "text", str(t)) for t in text)
                    if text:
                        yield text
        except Exception as e:
            yield f"[LLM error: {e}]"


def _build_langchain_model_openai(settings: Any) -> Any:
    """Build LangChain ChatOpenAI from settings."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        max_tokens=4096,
    )


def _build_langchain_model_gemini(settings: Any) -> Any:
    """Build LangChain ChatGoogleGenerativeAI from settings."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        google_api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        temperature=settings.gemini_temperature,
        max_output_tokens=4096,
    )


def get_llm_client() -> LLMClient:
    """Return the configured LLM client (LangChain-backed OpenAI, Gemini, or local placeholder)."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "openai":
        if not settings.openai_api_key:
            return _NoOpClient("[OPENAI_API_KEY not set]")
        try:
            model = _build_langchain_model_openai(settings)
            return LangChainChatClient(model=model, temperature=settings.openai_temperature)
        except Exception as e:
            return _NoOpClient(f"[OpenAI init error: {e}]")
    if provider == "gemini":
        if not settings.gemini_api_key:
            return _NoOpClient("[GEMINI_API_KEY not set]")
        try:
            model = _build_langchain_model_gemini(settings)
            return LangChainChatClient(model=model, temperature=settings.gemini_temperature)
        except Exception as e:
            return _NoOpClient(f"[Gemini init error: {e}]")
    return LocalModelClient(
        model=getattr(settings, "anthropic_model", "local") or "local",
        temperature=settings.openai_temperature,
    )


class _NoOpClient(LLMClient):
    """Fallback client when provider is configured but key/init fails."""

    def __init__(self, error_message: str) -> None:
        self._error = error_message

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> str:
        return self._error

    async def complete_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        yield self._error


class LocalModelClient(LLMClient):
    """Placeholder for a local model (Ollama, vLLM, etc.)."""

    def __init__(self, model: str = "local", temperature: float = 0.2) -> None:
        self.model = model
        self.temperature = temperature

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> str:
        return "[Local model not implemented; set LLM_PROVIDER=openai or gemini]"

    async def complete_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        yield "[Local model not implemented]"
