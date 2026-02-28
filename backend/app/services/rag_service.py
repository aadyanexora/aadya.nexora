from app.rag.vector_store import FaissVectorStore
from app.services.openai_service import OpenAIService
from typing import List, Tuple
from app.db.session import SessionLocal
from app.db.base import Base
from sqlalchemy import create_engine
from app.core.config import settings
from sqlalchemy.orm import sessionmaker
from app import models


class RAGService:
    def __init__(self):
        self.vs = FaissVectorStore()
        self.openai = OpenAIService()

    def add_documents(self, texts: List[str], meta: List[Tuple[int, int]]):
        """`meta` is a list of tuples (document_id, chunk_index) corresponding to each text."""
        embs = self.openai.get_embeddings(texts)
        self.vs.add(embs, meta)

    def search(
        self, query: str, top_k: int = 5
    ) -> List[Tuple[str, int, int, float]]:
        """Return list of (chunk_content, document_id, chunk_index, score)"""
        emb = self.openai.get_embeddings([query])[0]
        hits = self.vs.search(emb, top_k=top_k)
        results: List[Tuple[str, int, int, float]] = []
        from app.db.session import SessionLocal

        db = SessionLocal()
        from sqlalchemy import text
        try:
            for doc_id, chunk_idx, score in hits:
                # fetch the corresponding chunk
                stmt = text(
                    "SELECT content FROM document_chunks WHERE document_id = :d AND chunk_index = :ci"
                )
                row = db.execute(stmt, {"d": doc_id, "ci": chunk_idx}).fetchone()
                if row:
                    results.append((row[0], doc_id, chunk_idx, score))
        finally:
            db.close()
        return results
