from typing import List
from app.services.openai_service import OpenAIService
from app.services.rag_service import RAGService
from app.db.session import SessionLocal
from sqlalchemy import text

class IngestionService:
    def __init__(self):
        self.openai = OpenAIService()
        self.rag = RAGService()

    def ingest_texts(self, texts: List[str]):
        # Persist documents in a simple table and add vectors
        db = SessionLocal()
        try:
            doc_ids = []
            for t in texts:
                res = db.execute(text("INSERT INTO documents (content) VALUES (:c) RETURNING id"), {"c": t})
                doc_id = res.fetchone()[0]
                doc_ids.append(doc_id)
            db.commit()
            self.rag.add_documents(texts, doc_ids)
        finally:
            db.close()
