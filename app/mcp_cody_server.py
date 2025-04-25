from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn
import logging
import os
import json
import asyncio
from retrieval_engine import CosineRetriever
from embedding_engine import EmbeddingEngine
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

app = FastAPI()
load_dotenv()

# Configuration
claude_api_key = os.getenv("ANTHROPIC_API_KEY")
local_path = "/mnt/data/test_kleur"

# Initialize embedding engine and retriever
engine = EmbeddingEngine()
path = Path(local_path)
files = engine.collect_files(path)
all_chunks = []
for file_path in files:
    all_chunks.extend(engine.chunk_file(file_path))
logger.info(f"Total chunks created: {len(all_chunks)}")
chunk_embeddings = engine.embed_chunks(all_chunks)
retriever = CosineRetriever(chunk_embeddings, engine.model)

# Initialize Claude client
anthropic = Anthropic(api_key=claude_api_key)

def retrieve_context(question: str) -> str:
    top_chunks = retriever.retrieve(query=question, top_k=5)
    combined_context = "\n\n".join(chunk for chunk, _ in top_chunks)
    return combined_context

async def generate_response(message_content: str) -> str:
    # Retrieve context based on the user's question
    context = retrieve_context(message_content)

    # Format prompt with context
    prompt = f"""You are a helpful AI assistant with access to a code repository.
    
Context from the repository:
{context}

Based on this context, please answer the following question:
{message_content}"""

    # Call Claude API (you can replace this with your actual Claude API call)
    try:
        response = anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    except Exception as e:
        logger.exception("Error calling Claude API")
        return f"Error generating response: {str(e)}"

@app.post("/mcp")
async def handle_mcp(request: Request):
    try:
        body = await request.json()
        logger.info(f"Received MCP request: {body}")

        # Handle different MCP message types
        message_type = body.get("type")

        if message_type == "message":
            message = body.get("message", {})
            role = message.get("role")
            content = message.get("content", "")

            if role == "user":
                # Generate response to user message
                response_text = await generate_response(content)

                return JSONResponse(content={
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    }
                })
            else:
                return JSONResponse(content={
                    "type": "error",
                    "error": {
                        "message": f"Unsupported role: {role}"
                    }
                }, status_code=400)

        elif message_type == "ping":
            # Respond to ping
            return JSONResponse(content={
                "type": "pong"
            })

        else:
            return JSONResponse(content={
                "type": "error",
                "error": {
                    "message": f"Unsupported message type: {message_type}"
                }
            }, status_code=400)

    except Exception as e:
        logger.exception("Error processing request")
        return JSONResponse(content={
            "type": "error",
            "error": {
                "message": str(e)
            }
        }, status_code=500)

# WebSocket endpoint for streaming responses
@app.websocket("/mcp/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)

            message_type = request.get("type")
            if message_type == "message":
                message = request.get("message", {})
                role = message.get("role")
                content = message.get("content", "")

                if role == "user":
                    # Send start event
                    await websocket.send_json({
                        "type": "message_start",
                        "message": {
                            "role": "assistant"
                        }
                    })

                    # Generate response
                    response_text = await generate_response(content)

                    # Send content delta
                    await websocket.send_json({
                        "type": "content_block_delta",
                        "delta": {
                            "type": "text",
                            "text": response_text
                        }
                    })

                    # Send end event
                    await websocket.send_json({
                        "type": "message_delta",
                        "delta": {
                            "stop_reason": "end_turn"
                        }
                    })

            elif message_type == "ping":
                await websocket.send_json({
                    "type": "pong"
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception("Error in WebSocket connection")
        await websocket.send_json({
            "type": "error",
            "error": {
                "message": str(e)
            }
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("mcp_cody_server:app", host="0.0.0.0", port=port, reload=True)
