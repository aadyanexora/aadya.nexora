import faiss
import numpy as np
import os
import pickle
from typing import List, Tuple, Union, Dict
from app.core.config import settings


class FaissVectorStore:
    def __init__(self, dim: int = None):
        self.dim = dim or settings.EMBEDDING_DIM
        self.index_path = os.path.join(settings.FAISS_DIR, "index.faiss")
        self.map_path = os.path.join(settings.FAISS_DIR, "mapping.pkl")
        self._load()

    def _load(self):
        # if existing index present, validate dimension and recreate if mismatch
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                # verify dim
                if self.index.ntotal > 0:
                    idx_dim = self.index.d
                else:
                    # for empty IndexFlatL2, d attribute exists
                    idx_dim = self.index.d
                if idx_dim != self.dim:
                    # recreate index with correct dim
                    self.index = faiss.IndexFlatL2(self.dim)
            except Exception:
                # on any error, recreate fresh index
                self.index = faiss.IndexFlatL2(self.dim)
        else:
            self.index = faiss.IndexFlatL2(self.dim)

        if os.path.exists(self.map_path):
            with open(self.map_path, "rb") as f:
                self.mapping = pickle.load(f)
        else:
            # mapping maps index -> (document_id, chunk_index)
            self.mapping: Dict[int, Tuple[int, int]] = {}

    def add(self, vectors: List[List[float]], meta: List[Tuple[int, int]]):
        """`meta` is a list of (document_id, chunk_index) corresponding to each vector."""
        arr = np.array(vectors).astype("float32")
        start = self.index.ntotal
        self.index.add(arr)
        for i, m in enumerate(meta):
            self.mapping[start + i] = m
        self._persist()

    def search(self, vector: List[float], top_k: int = 3) -> List[Tuple[int, int, float]]:
        if self.index.ntotal == 0:
            return []
        xq = np.array([vector]).astype("float32")
        D, I = self.index.search(xq, top_k)
        results: List[Tuple[int, int, float]] = []
        for score, idx in zip(D[0], I[0]):
            if idx == -1:
                continue
            meta = self.mapping.get(int(idx))
            if not meta:
                continue
            doc_id, chunk_idx = meta
            results.append((doc_id, chunk_idx, float(score)))
        return results

    def _persist(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.map_path, "wb") as f:
            pickle.dump(self.mapping, f)
