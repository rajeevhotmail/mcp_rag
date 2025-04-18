from repo_utils import get_repo_path
from embedding_engine import EmbeddingEngine

if __name__ == "__main__":
    # Step 1: Clone a real small repo
    url = "https://github.com/lukeed/kleur"

    try:

       # Use local repo (this will skip cloning)
       path = get_repo_path(local_path="/mnt/data/test_kleur")
       print(f"\n✅ Repo read from local path: {path}")
    except Exception as e:
       print(f"\n❌ Failed to fetch repo: {e}")
       exit(-1)
    try:
        # Step 2: Embed the contents
        engine = EmbeddingEngine()
        files = engine.collect_files(path)

        all_chunks = []
        for file_path in files:
            all_chunks.extend(engine.chunk_file(file_path))

        print(f"\n🧩 Total chunks created: {len(all_chunks)}")

        chunk_embeddings = engine.embed_chunks([text for text in all_chunks])
        print(f"\n✅ Embedding complete. Total embedded chunks: {len(chunk_embeddings)}")
        from retrieval_engine import CosineRetriever
        retriever = CosineRetriever(chunk_embeddings, engine.model)
        top_chunks = retriever.retrieve("What programming language is used?")

    except Exception as e:
        print(f"\n❌ Error during repo fetch or embedding: {e}")
