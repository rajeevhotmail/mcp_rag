from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import logging
import os
import json
from retrieval_engine import CosineRetriever
from embedding_engine import EmbeddingEngine
from pathlib import Path
from dotenv import load_dotenv






# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

app = FastAPI()

load_dotenv()
llm_provider = os.getenv("LLM_PROVIDER", "CLAUDE").upper()
claude_api_key = os.getenv("ANTHROPIC_API_KEY")
# Configuration
repo_name = "kleur"  # this can be made dynamic later via params
role = "programmer"
local_path = "/mnt/data/test_kleur"

# STEP 1: Load repo path (assume local for now)
path = Path(local_path)

# STEP 2: Chunk and embed
engine = EmbeddingEngine()
files = engine.collect_files(path)
all_chunks = []
for file_path in files:
    all_chunks.extend(engine.chunk_file(file_path))
print(f"\n🧩 Total chunks created: {len(all_chunks)}")
chunk_embeddings = engine.embed_chunks(all_chunks)

# STEP 3: Initialize retriever globally
retriever = CosineRetriever(chunk_embeddings, engine.model)

# Dummy Claude LLM call simulation (you can plug in real Claude API here)
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT

# Initialize Claude client
anthropic = Anthropic(api_key=claude_api_key)
def call_llm_api(question: str, context: str) -> str:
    logger.info(f"(Mock) Responding to question: {question}")
    return f"(🧪 This is a mock answer for: '{question}')\n\n📄 Context preview:\n{context[:200]}..."


"""
def call_llm_api(question: str, context: str) -> str:
    logger.info(f"Calling {llm_provider} with question: {question} and context length: {len(context)}")

    if llm_provider == "CLAUDE":
        prompt = f"{HUMAN_PROMPT} Here is some context:\n{context}\n\nNow answer this question:\n{question}{AI_PROMPT}"

        response = anthropic.completions.create(
            model="claude-2.1",
            max_tokens_to_sample=512,
            prompt=prompt,
            temperature=0.3,
            stop_sequences=[HUMAN_PROMPT]
        )
        return response.completion.strip()

    elif llm_provider == "OPENAI":
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        messages = [
            {"role": "system", "content": "Use the context to answer questions."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.3
        )
        return response.choices[0].message["content"].strip()

    elif llm_provider == "TOGETHER":
        import requests
        headers = {
            "Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}",
            "Content-Type": "application/json"
        }
        json_payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.1",
            "prompt": f"Context:\n{context}\n\nQuestion: {question}",
            "temperature": 0.3,
            "max_tokens": 512
        }
        resp = requests.post("https://api.together.xyz/v1/completions", headers=headers, json=json_payload)
        return resp.json()["choices"][0]["text"].strip()

    else:
        raise ValueError(f"Unknown LLM provider: {llm_provider}")
"""
# Dummy context retrieval simulation (plug in your real RAG pipeline here)
def retrieve_context(question: str, repo_path: str) -> str:
    top_chunks = retriever.retrieve(query=question, top_k=5)
    combined_context = "\n\n".join(chunk for chunk, _ in top_chunks)
    return combined_context

@app.post("/mcp")
async def handle_mcp_rpc(request: Request):
    try:
        body = await request.json()
        logger.info(f"Received MCP JSON-RPC request: {body}")

        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        if method == "initialize":
            logger.info("✔️ Sending 'initialize' response to Claude")
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "result": {
                    "toolName": "RAG MCP Server",
                    "toolVersion": "0.1.0",
                    "capabilities": {}
                },
                "id": request_id
            })


        elif method == "queryContext":
            question = params.get("question", "")
            repo = params.get("repo", "")

            context = retrieve_context(question, repo)
            answer = call_llm_api(question, context)

            return JSONResponse(content={
                "jsonrpc": "2.0",
                "result": answer,
                "id": request_id
            })

        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found."},
                "id": request_id
            })

    except Exception as e:
        logger.exception("Error processing request")
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": None
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("mcp_jsonrpc_server:app", host="0.0.0.0", port=port, reload=True)
