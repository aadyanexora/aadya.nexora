import os
import openai
from typing import List, Iterator
from app.core.config import settings


openai.api_key = settings.OPENAI_API_KEY


class OpenAIService:
    def __init__(self):
        self.model = "gpt-4o-mini" if True else "gpt-4"

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        resp = openai.Embeddings.create(input=texts, model="text-embedding-3-small")
        return [r["embedding"] for r in resp["data"]]

    def chat_with_context(self, message: str, contexts: List[str]) -> str:
        prompt = self._build_prompt(message, contexts)
        resp = openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
        return resp["choices"][0]["message"]["content"]

    def stream_chat_with_context(self, message: str, contexts: List[str]) -> Iterator[str]:
        prompt = self._build_prompt(message, contexts)
        resp_iter = openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], stream=True)
        buffer = ""
        for part in resp_iter:
            delta = part.get("choices", [])[0].get("delta", {}).get("content")
            if delta:
                buffer += delta
                yield delta

    def _build_prompt(self, message: str, contexts: List[str]) -> str:
        context_block = "\n---\n".join(contexts) if contexts else ""
        return f"Use the following context to answer the question.\n{context_block}\n\nQuestion: {message}"
