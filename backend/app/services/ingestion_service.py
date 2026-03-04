from typing import List, Tuple, Optional
from app.services.openai_service import OpenAIService
from app.services.rag_service import RAGService
from app.db.session import SessionLocal
from sqlalchemy import text
import time

# optional PDF extraction library; will be imported lazily in helper
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


# simple whitespace-based chunker; approximates token count
# chunk size and overlap can be adjusted via settings if desired

def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> List[str]:
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
        """Legacy wrapper keeping same signature as before."""
        docs = []
        for idx, t in enumerate(texts):
            docs.append({
                "text": t,
                "source": names[idx] if names and idx < len(names) else None,
                "filename": names[idx] if names and idx < len(names) else None,
                "page": None,
            })
        return self.ingest_documents(docs)

    def ingest_documents(self, docs: List[dict]):
        """Process a list of documents with metadata.

        Each entry in ``docs`` should be a dict containing at least:
            - text: the raw string to ingest
        Optional keys are ``source`` (identifier), ``filename`` and ``page``.
        """
        self.logger.info("starting ingestion", extra={})
        db = SessionLocal()
        try:
            chunk_texts: List[str] = []
            chunk_meta: List[Tuple[int, int]] = []  # (doc_id, chunk_index)
            for doc in docs:
                text_content = doc.get("text", "")
                source = doc.get("source")
                filename = doc.get("filename")
                page = doc.get("page")
                # insert document record; store original full text and source
                res = db.execute(
                    text("INSERT INTO documents (content, name) VALUES (:c, :n) RETURNING id"),
                    {"c": text_content, "n": source},
                )
                doc_id = res.fetchone()[0]
                self.logger.info(f"persisted document {doc_id}", extra={"source": source, "filename": filename, "page": page})
                # chunk the text
                chunks = chunk_text(text_content)
                for ci, chunk in enumerate(chunks):
                    db.execute(
                        text(
                            "INSERT INTO document_chunks "
                            "(document_id, chunk_index, content, source, filename, page) "
                            "VALUES (:d, :ci, :c, :s, :f, :p)"
                        ),
                        {"d": doc_id, "ci": ci, "c": chunk, "s": source, "f": filename, "p": page},
                    )
                    chunk_texts.append(chunk)
                    chunk_meta.append((doc_id, ci))
            db.commit()
            # now embed chunks in vector store; measure time
            if chunk_texts:
                self.logger.info(f"embedding {len(chunk_texts)} chunks")
                start = time.time()
                self.rag.add_documents(chunk_texts, chunk_meta)
                elapsed = time.time() - start
                self.logger.info(f"embeddings generated in {elapsed:.2f}s")
        finally:
            db.close()
            self.logger.info("finished ingestion")
