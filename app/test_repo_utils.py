from repo_utils import get_repo_path
from embedding_engine import EmbeddingEngine
from retrieval_engine import CosineRetriever
from mcp_context import build_mcp_context, render_prompt, validate_context
from questions import QUESTION_TEMPLATES
from llm_client import query_llm
from pdf_generator import generate_pdf_from_llm_response
import os

# Configuration
repo_name = "kleur"
role = "programmer"
local_path = "/mnt/data/test_kleur"  # or set repo_url = "https://github.com/..."

# STEP 1: Get repo
path = get_repo_path(local_path=local_path)

# STEP 2: Chunk and embed
engine = EmbeddingEngine()
files = engine.collect_files(path)
all_chunks = []
for file_path in files:
    all_chunks.extend(engine.chunk_file(file_path))
print(f"\n🧩 Total chunks created: {len(all_chunks)}")
chunk_embeddings = engine.embed_chunks(all_chunks)

# STEP 3: Retrieve for all questions
retriever = CosineRetriever(chunk_embeddings, engine.model)
questions = QUESTION_TEMPLATES[role]
retrieved_chunks_set = set()

for q in questions:
    top_chunks = retriever.retrieve(q, top_k=5)
    for chunk, _ in top_chunks:
        retrieved_chunks_set.add(chunk)

retrieved_chunks = list(retrieved_chunks_set)
print(f"\n📦 Retrieved {len(retrieved_chunks)} unique chunks for MCP context.")

# STEP 4: Build prompt
context = build_mcp_context(repo_name, role, retrieved_chunks)
validate_context(context)
prompt = render_prompt(context)

# STEP 5: Query LLM
response = query_llm(prompt)
print("\n🧠 LLM Response (full):\n", response)

# STEP 6: Generate PDF
pdf_path = generate_pdf_from_llm_response(repo_name, role, response)
print(f"\n📄 PDF report saved to: {pdf_path}")
