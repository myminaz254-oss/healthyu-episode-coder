import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import anthropic


@dataclass
class CacheEntry:
    messages: List[Dict[str, Any]]
    response: str
    model: str


class CacheMissError(Exception):
    def __init__(self, case_id: str, call_n: int):
        self.case_id = case_id
        self.call_n = call_n
        super().__init__(f"Cache miss for {case_id} call {call_n}")


class LLMClient:
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", cache_dir: str = "cache/responses", replay: bool = True):
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.replay = replay
        self.calls_made = 0
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not replay and api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None

    def _cache_key(self, messages: List[Dict[str, Any]]) -> str:
        content = json.dumps(messages, sort_keys=True) + self.model
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _cache_path(self, case_id: str, call_n: int, key: str) -> Path:
        return self.cache_dir / f"{case_id}_call{call_n}_{key}.json"

    def _load_cache(self, case_id: str, call_n: int, key: str) -> Optional[str]:
        path = self._cache_path(case_id, call_n, key)
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
            return data.get("response")
        return None

    def _save_cache(self, case_id: str, call_n: int, key: str, messages: List[Dict[str, Any]], response: str):
        path = self._cache_path(case_id, call_n, key)
        data = {
            "case_id": case_id,
            "call_n": call_n,
            "model": self.model,
            "messages": messages,
            "response": response
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def call(self, case_id: str, call_n: int, messages: List[Dict[str, Any]], system_prompt: str) -> str:
        self.calls_made += 1
        key = self._cache_key(messages)
        cached = self._load_cache(case_id, call_n, key)
        
        if cached is not None:
            return cached
        
        if self.replay:
            raise CacheMissError(case_id, call_n)
        
        if self.client is None:
            raise RuntimeError("LLM client not initialized (no API key) and not in replay mode")
        
        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=messages,
            max_tokens=4000,
            temperature=0
        )
        
        response_text = response.content[0].text
        self._save_cache(case_id, call_n, key, messages, response_text)
        return response_text


def create_llm_client(replay: bool = True) -> LLMClient:
    return LLMClient(replay=replay)