import os
from sentence_transformers import SentenceTransformer
from logging_config import get_logger

logger = get_logger("embedding_engine")

SUPPORTED_EXTENSIONS = {".py", ".md", ".txt", ".java", ".js", ".ts", ".json"}

class EmbeddingEngine:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def collect_files(self, repo_path):
        logger.info(f"Scanning files in {repo_path}")
        all_files = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    all_files.append(full_path)
        logger.info(f"Found {len(all_files)} supported files.")
        return all_files

    def chunk_file(self, file_path, max_lines=20):
        logger.info(f"Chunking file: {file_path}")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        chunks = []
        for i in range(0, len(lines), max_lines):
            chunk = "".join(lines[i:i + max_lines])
            if chunk.strip():
                chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from {file_path}")
        logger.debug(f"Chunk size stats (lines): {[len(chunk.splitlines()) for chunk in chunks]}")
        return chunks


    def embed_chunks(self, chunks):
        logger.info(f"Embedding {len(chunks)} chunks...")
        embeddings = self.model.encode(chunks, show_progress_bar=True)
        return list(zip(chunks, embeddings))
