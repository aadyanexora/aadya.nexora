import os
from typing import List, Iterator
from app.core.config import settings

from sentence_transformers import SentenceTransformer
from openai import OpenAI


class OpenAIService:
    """Hybrid provider service: local SentenceTransformers for embeddings
    and Groq (OpenAI-compatible) for chat/streaming.
    """

    def __init__(self):
        # local embedder
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        # groq client (OpenAI-compatible SDK)
        self.groq_client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        # models
        self.chat_model = "llama-3.1-8b-instant"

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embs = self.embedder.encode(texts)
        try:
            # numpy array -> list
            return embs.tolist()
        except Exception:
            return [list(map(float, e)) for e in embs]

    def chat_with_context(self, message: str, contexts: List[str]) -> str:
        prompt = self._build_prompt(message, contexts)
        response = self.groq_client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": prompt}],
        )
        # safe access
        return getattr(response.choices[0].message, "content", "")

    def stream_chat_with_context(self, message: str, contexts: List[str]) -> Iterator[str]:
        prompt = self._build_prompt(message, contexts)
        stream = self.groq_client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                if delta is None:
                    continue
                content = getattr(delta, "content", None)
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
