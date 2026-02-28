from app.rag.vector_store import FaissVectorStore
from app.services.openai_service import OpenAIService
from typing import List
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

    def add_documents(self, texts: List[str], doc_ids: List[int]):
        embs = self.openai.get_embeddings(texts)
        self.vs.add(embs, doc_ids)

    def search(self, query: str, top_k: int = 3) -> List[str]:
        emb = self.openai.get_embeddings([query])[0]
        hits = self.vs.search(emb, top_k=top_k)
        docs = []
        # fetch document contents from DB by ids
        from app.db.session import SessionLocal

        db = SessionLocal()
        from sqlalchemy import text
        try:
            for doc_id, score in hits:
                stmt = text("SELECT content FROM documents WHERE id = :id")
                doc = db.execute(stmt, {"id": doc_id}).fetchone()
                if doc:
                    docs.append(doc[0])
        finally:
            db.close()
        return docs
