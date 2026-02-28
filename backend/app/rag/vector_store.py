import faiss
import numpy as np
import os
import pickle
from typing import List, Tuple
from app.core.config import settings


class FaissVectorStore:
    def __init__(self, dim: int = None):
        self.dim = dim or settings.EMBEDDING_DIM
        self.index_path = os.path.join(settings.FAISS_DIR, "index.faiss")
        self.map_path = os.path.join(settings.FAISS_DIR, "mapping.pkl")
        self._load()

    def _load(self):
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            self.index = faiss.IndexFlatL2(self.dim)

        if os.path.exists(self.map_path):
            with open(self.map_path, "rb") as f:
                self.mapping = pickle.load(f)
        else:
            self.mapping = {}

    def add(self, vectors: List[List[float]], doc_ids: List[int]):
        arr = np.array(vectors).astype("float32")
        start = self.index.ntotal
        self.index.add(arr)
        for i, doc_id in enumerate(doc_ids):
            self.mapping[start + i] = doc_id
        self._persist()

    def search(self, vector: List[float], top_k: int = 3) -> List[Tuple[int, float]]:
        if self.index.ntotal == 0:
            return []
        xq = np.array([vector]).astype("float32")
        D, I = self.index.search(xq, top_k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx == -1:
                continue
            doc_id = self.mapping.get(int(idx))
            results.append((doc_id, float(score)))
        return results

    def _persist(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.map_path, "wb") as f:
            pickle.dump(self.mapping, f)
