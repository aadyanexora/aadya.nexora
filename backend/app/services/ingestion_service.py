from typing import List, Tuple, Optional
from app.services.openai_service import OpenAIService
from app.services.rag_service import RAGService
from app.db.session import SessionLocal
from sqlalchemy import text


# simple whitespace-based chunker; approximates token count
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    tokens = text.split()
    if not tokens:
        return []
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk = " ".join(tokens[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


import logging

class IngestionService:
    def __init__(self):
        self.openai = OpenAIService()
        self.rag = RAGService()
        self.logger = logging.getLogger(__name__)

    def ingest_texts(self, texts: List[str], names: Optional[List[str]] = None):
        """Persist incoming texts (and optional names) into documents & chunks then embed.

        `names` corresponds to each text and may be a filename or other source identifier.
        """
        self.logger.info("starting ingestion", extra={})
        db = SessionLocal()
        try:
            chunk_texts: List[str] = []
            chunk_meta: List[Tuple[int, int]] = []  # (doc_id, chunk_index)
            for idx, t in enumerate(texts):
                name = names[idx] if names and idx < len(names) else None
                # insert document record
                res = db.execute(
                    text("INSERT INTO documents (content, name) VALUES (:c, :n) RETURNING id"),
                    {"c": t, "n": name},
                )
                doc_id = res.fetchone()[0]
                self.logger.info(f"persisted document {doc_id}", extra={"name": name})
                # create chunks
                chunks = chunk_text(t)
                for ci, chunk in enumerate(chunks):
                    db.execute(
                        text(
                            "INSERT INTO document_chunks (document_id, chunk_index, content) VALUES (:d, :ci, :c)"
                        ),
                        {"d": doc_id, "ci": ci, "c": chunk},
                    )
                    chunk_texts.append(chunk)
                    chunk_meta.append((doc_id, ci))
            db.commit()
            # now embed chunks in vector store
            if chunk_texts:
                self.logger.info(f"adding {len(chunk_texts)} vectors to index")
                self.rag.add_documents(chunk_texts, chunk_meta)
        finally:
            db.close()
            self.logger.info("finished ingestion")
