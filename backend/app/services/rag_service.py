from app.rag.vector_store import FaissVectorStore
import time
import logging
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
        self.logger = logging.getLogger(__name__)

    def add_documents(self, texts: List[str], meta: List[Tuple[int, int]]):
        """`meta` is a list of tuples (document_id, chunk_index) corresponding to each text.

        Embeddings are generated via the OpenAIService and added to the FAISS store.
        This method logs how long the embedding step took and how many vectors were
        added.
        """
        start = time.time()
        embs = self.openai.get_embeddings(texts)
        self.vs.add(embs, meta)
        elapsed = time.time() - start
        self.logger.info(f"generated {len(texts)} embeddings in {elapsed:.2f}s")

    def search(
        self, query: str, top_k: int = 5
    ) -> List[dict]:
        """Return list of results with content, metadata and score.

        Each dict contains:
            - content (str)
            - document_id (int)
            - chunk_index (int)
            - score (float)
            - source (str|None)
            - filename (str|None)
            - page (int|None)
        """
        emb = self.openai.get_embeddings([query])[0]
        hits = self.vs.search(emb, top_k=top_k)
        results: List[dict] = []
        from app.db.session import SessionLocal

        db = SessionLocal()
        from sqlalchemy import text
        try:
            start = time.time()
            for doc_id, chunk_idx, score in hits:
                stmt = text(
                    "SELECT content, source, filename, page "
                    "FROM document_chunks "
                    "WHERE document_id = :d AND chunk_index = :ci"
                )
                row = db.execute(stmt, {"d": doc_id, "ci": chunk_idx}).fetchone()
                if row:
                    content, source, filename, page = row
                    results.append({
                        "content": content,
                        "document_id": doc_id,
                        "chunk_index": chunk_idx,
                        "score": score,
                        "source": source,
                        "filename": filename,
                        "page": page,
                    })
            elapsed = time.time() - start
            self.logger.info(f"retrieved {len(results)} chunks in {elapsed:.3f}s")
        finally:
            db.close()
        return results
