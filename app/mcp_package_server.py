from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import logging
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("mcp_package_server")

app = FastAPI()

@app.post("/")
async def handle_mcp_request(request: Request):
    body = await request.json()
    #print(f"📥 Received: {body}")
    logger.debug("Received request body: %s", json.dumps(body, indent=2))
    # optional manual validation
    if "method" not in body:
        logger.error("Missing required key: 'method'")
    if "params" not in body:
        logger.warning("No 'params' found in request body")

    method = body.get("method")
    req_id = body.get("id", 1)

    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "sampling": {
                        "createMessage": {}
                    },
                    "resources": {},
                    "tools": {}
                },
                "serverInfo": {
                    "name": "FastAPI MCP",
                    "version": "1.0.0"
                }
            }
        })

    elif method == "notifications/initialized":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "result/ok",
            "param": None
        })

    elif method in ["resources/list", "tools/list", "prompts/list"]:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "result/ok",
            "param": {
                "items": []
            }
        })



    elif method == "getServerCapabilities":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "result/ok",
            "result": {
                "name": "Local Claude Server",
                "version": "1.0.0",
                "capabilities": ["completion", "sampling"]
            }
        })

    elif method == "sampling/createMessage":
        messages = body["params"]["messages"]
        user_msg = next((m for m in messages if m["role"] == "user"), None)
        user_text = user_msg["content"]["text"] if user_msg else ""

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "result/ok",
            "result": {
                "completion": f"Simulated Claude Response: {user_text} → Paris"
            }
        })

    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Unsupported method: {method}"
            }
        })

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
