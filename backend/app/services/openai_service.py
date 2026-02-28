import os
from typing import List, Iterator
from openai import OpenAI
from app.core.config import settings


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.chat_model = "gpt-4o-mini"
        self.embedding_model = "text-embedding-3-small"

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return [item.embedding for item in response.data]

    def chat_with_context(self, message: str, contexts: List[str]) -> str:
        prompt = self._build_prompt(message, contexts)

        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    def stream_chat_with_context(self, message: str, contexts: List[str]) -> Iterator[str]:
        prompt = self._build_prompt(message, contexts)

        stream = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _build_prompt(self, message: str, contexts: List[str]) -> str:
        context_block = "\n---\n".join(contexts) if contexts else ""
        return (
            "Use the following context to answer the question.\n"
            f"{context_block}\n\n"
            f"Question: {message}"
        )