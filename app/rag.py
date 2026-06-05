import json
import os
import re
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
VECTORS = DATA / "store.npz"
META = DATA / "store.json"

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "6"))
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))

CODE_INTENT = re.compile(
    r"\b(code|implementation|implement|function|method|snippet|class|def|algorithm|line)\b|\.\w{2,4}\b",
    re.I,
)

_embedder = None


def embedder():
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name=EMBED_MODEL)
    return _embedder


QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def embed(texts, is_query=False):
    if is_query:
        texts = [QUERY_PREFIX + t for t in texts]
    vecs = np.array(list(embedder().embed(list(texts))), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


class Store:
    def __init__(self, vectors, meta):
        self.vectors = vectors
        self.meta = meta

    @classmethod
    def load(cls):
        if not VECTORS.exists():
            raise FileNotFoundError("Vector store missing — run scripts/ingest.py first.")
        vectors = np.load(VECTORS)["vectors"]
        meta = json.loads(META.read_text(encoding="utf-8"))
        return cls(vectors, meta)

    @classmethod
    def build(cls, chunks):
        vectors = embed([c["text"] for c in chunks])
        DATA.mkdir(exist_ok=True)
        np.savez_compressed(VECTORS, vectors=vectors)
        META.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
        return cls(vectors, chunks)

    def search(self, query, top_k=TOP_K, tiers=None):
        q = embed([query], is_query=True)[0]
        scores = self.vectors @ q
        order = np.argsort(scores)[::-1]
        out = []
        for i in order:
            chunk = self.meta[i]
            if tiers and chunk["tier"] not in tiers:
                continue
            out.append({**chunk, "score": float(scores[i])})
            if len(out) == top_k:
                break
        return out


def tiers_for_query(query):
    return {1, 2, 3} if CODE_INTENT.search(query) else {1, 2}


class Retriever:
    def __init__(self):
        self.store = Store.load()

    def retrieve(self, query, top_k=TOP_K):
        tiers = tiers_for_query(query)
        results = self.store.search(query, top_k=top_k, tiers=tiers)
        top = results[0]["score"] if results else 0.0
        return {"results": results, "top_score": top, "confident": top >= THRESHOLD}
