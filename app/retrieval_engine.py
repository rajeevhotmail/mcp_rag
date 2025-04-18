import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from logging_config import get_logger

logger = get_logger("retrieval_engine")

class BaseRetriever:
    def __init__(self, embedded_chunks: list):
        """
        embedded_chunks: List of tuples (chunk_text: str, embedding_vector: np.array)
        """
        self.embedded_chunks = embedded_chunks

    def retrieve(self, query: str, top_k: int = 5):
        raise NotImplementedError("Subclasses must implement retrieve()")


class CosineRetriever(BaseRetriever):
    def __init__(self, embedded_chunks, embed_model):
        super().__init__(embedded_chunks)
        self.embed_model = embed_model  # A sentence-transformer or compatible model

    def retrieve(self, query: str, top_k: int = 5):
        logger.info(f"Retrieving top {top_k} chunks for query: {query}")

        query_vector = self.embed_model.encode([query])
        chunk_vectors = np.array([vec for _, vec in self.embedded_chunks])
        scores = cosine_similarity(query_vector, chunk_vectors)[0]

        top_indices = np.argsort(scores)[::-1][:top_k]
        top_chunks = [(self.embedded_chunks[i][0], float(scores[i])) for i in top_indices]

        logger.info(f"Retrieved {len(top_chunks)} chunks with highest cosine similarity.")
        for i, (chunk, score) in enumerate(top_chunks, 1):
            preview = "\n".join(chunk.strip().splitlines()[:3])  # First 3 lines
            logger.info(f"🔹 Match #{i} | Score: {score:.4f}\n{preview}\n")
        return top_chunks
