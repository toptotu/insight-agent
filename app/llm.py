import os
from dataclasses import dataclass
from typing import Any, Dict

import requests


@dataclass
class LLMResponse:
    text: str
    model: str
    raw: Dict[str, Any]
    is_mock: bool = False


class BaseLLMClient:
    is_mock: bool = False

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> LLMResponse:
        raise NotImplementedError


class AliyunLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, api_base: str, model: str) -> None:
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        }
        response = requests.post(self.api_base, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        output = data.get("output", {})
        text = output.get("text")
        if not text and isinstance(output.get("choices"), list):
            text = output["choices"][0].get("message", {}).get("content")
        if not text:
            text = str(output)[:2000]
        return LLMResponse(text=text, model=self.model, raw=data, is_mock=False)


class MockLLMClient(BaseLLMClient):
    is_mock: bool = True

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> LLMResponse:
        fallback = "Mock response: no API key configured. Set ALI_API_KEY to enable LLM."
        return LLMResponse(text=fallback, model="mock", raw={"prompt_preview": prompt[:2000]}, is_mock=True)


def create_llm_client() -> BaseLLMClient:
    api_key = os.getenv("ALI_API_KEY", "").strip()
    api_base = os.getenv(
        "ALI_API_BASE",
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
    ).strip()
    model = os.getenv("ALI_MODEL", "qwen-plus").strip()
    if api_key:
        return AliyunLLMClient(api_key=api_key, api_base=api_base, model=model)
    return MockLLMClient()
