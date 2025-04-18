from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from mcp_context import build_mcp_context, render_prompt
from repo_utils import get_repo_path



# Initialize FastAPI
app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_rag_api")

context = build_mcp_context(repo_name, role, chunks)
validate_context(context)
prompt = render_prompt(context)

# Input model for /analyze endpoint
class AnalyzeRequest(BaseModel):
    repo_url: str
    role: str
    model: Optional[str] = "together"  # Options: "together", "chatgpt", etc.

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        logger.info(f"Received analysis request: repo={request.repo_url}, role={request.role}, model={request.model}")

        # === MCP FLOW START ===
        # Placeholder: clone and process repo
        # repo_path = clone_repo(request.repo_url)
        # chunks = chunk_and_embed(repo_path, request.model)
        # context = build_mcp_context(chunks, request.repo_url, request.role)
        # narrative = query_llm(context, request.model)
        # pdf_path = generate_pdf(narrative, repo_name, role)

        # Placeholder response
        return {"status": "success", "message": f"Analysis for {request.repo_url} as {request.role} started."}

    except Exception as e:
        logger.error(f"Error in /analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))

