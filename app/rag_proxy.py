#!/usr/bin/env python3
import sys
import json
import traceback
import requests
import os

RAG_SERVER_URL = "http://34.192.154.118:8000/mcp"  # ✅ Your real RAG server

def process_message(line):
    try:
        request = json.loads(line)
        method = request.get("method")
        request_id = request.get("id")

        if method == "initialize":
            sys.stderr.write("✅ Declared capabilities: ['complete'] with structured block\n")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "serverInfo": {
                        "name": "rag-proxy",
                        "version": "0.1.0"
                    },
                    "capabilities": {
                        "completion": {
                            "methods": ["complete"],
                            "supportsTools": False,
                            "supportsStream": False
                        }
                    }
                }
            }

        elif method == "complete":
            sys.stderr.write("📥 Handling 'complete' method\n")

            # Forward to real RAG server
            sys.stderr.write(f"🌐 Forwarding to RAG server: {RAG_SERVER_URL}\n")
            response = requests.post(
                RAG_SERVER_URL,
                headers={"Content-Type": "application/json"},
                json=request,
                timeout=30
            )

            sys.stderr.write("✅ RAG server responded\n")
            return json.loads(response.text)

        else:
            sys.stderr.write(f"⚠️ Unknown method: {method}\n")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not implemented"
                }
            }

    except Exception as e:
        sys.stderr.write(f"🔥 Error: {e}\n")
        sys.stderr.write(traceback.format_exc())
        return {
            "jsonrpc": "2.0",
            "id": request_id if 'request_id' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {e}"
            }
        }

# 🟢 Persistent stdin loop
try:
    sys.stderr.write(f"🟢 ENV VARS: {os.environ}\n")
    sys.stderr.write("✅ Proxy loop running and waiting for input...\n")

    while True:
        line = sys.stdin.readline()
        if not line:
            break  # EOF from Claude

        if line.strip():
            sys.stderr.write(f"🔁 Received: {repr(line)}\n")
            response = process_message(line)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
except Exception as e:
    sys.stderr.write(f"🔥 Fatal error in proxy loop: {e}\n")
    sys.stderr.write(traceback.format_exc())
