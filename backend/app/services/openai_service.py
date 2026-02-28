import os
from typing import List, Iterator
from app.core.config import settings

from sentence_transformers import SentenceTransformer
import httpx
import json


class OpenAIService:
    """Embedding/chat service using local SentenceTransformer and Groq API
    via raw HTTP (no OpenAI SDK).
    """

    def __init__(self):
        # local embedder
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.chat_model = "llama-3.1-8b-instant"
        # httpx client for Groq
        self.client = httpx.Client(
            base_url="https://api.groq.com/openai/v1",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            timeout=30.0,
        )

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embs = self.embedder.encode(texts)
        try:
            return embs.tolist()
        except Exception:
            # work around numpy types
            return [list(map(float, e)) for e in embs]

    def chat_with_context(self, message: str, contexts: List[str]) -> str:
        prompt = self._build_prompt(message, contexts)
        payload = {
            "model": self.chat_model,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        # safe traversal
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return ""

    def stream_chat_with_context(self, message: str, contexts: List[str]) -> Iterator[str]:
        prompt = self._build_prompt(message, contexts)
        payload = {
            "model": self.chat_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        with self.client.stream("POST", "/chat/completions", json=payload) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                # handle bytes or str
                if isinstance(line, bytes):
                    try:
                        text = line.decode("utf-8")
                    except Exception:
                        continue
                else:
                    text = line
                # Groq uses data: prefix similar to OpenAI
                if text.startswith("data: "):
                    try:
                        chunk = json.loads(text[len("data: "):])
                        delta = chunk.get("choices", [])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except Exception:
                        continue

    def _build_prompt(self, message: str, contexts: List[str]) -> str:
        context_block = "\n---\n".join(contexts) if contexts else ""
        return (
            "Use the following context to answer the question.\n"
            f"{context_block}\n\n"
            f"Question: {message}"
        )
