import subprocess
from fastapi import FastAPI, Request
import uvicorn
import json
import threading

app = FastAPI()

# Start the Git MCP server (stdio-based)
try:
    mcp_proc = subprocess.Popen(
        ["node", "../servers/dist/github/index.js", "--repository", "https://github.com/sindresorhus/kleur"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
except Exception as e:
    print("❌ Could not start subprocess:", e)
    raise

print("✅ MCP subprocess started")

# Background thread to read and print stderr (so we don’t miss crash messages)
def log_stderr():
    for line in mcp_proc.stderr:
        print("🐞 [stderr]:", line.strip())

threading.Thread(target=log_stderr, daemon=True).start()

# Send MCP initialize message
init_message = json.dumps({
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "wrapper-client",
            "version": "0.1.0"
        }
    },
    "id": 0
})
try:
    print("📤 Sending initialize...")
    mcp_proc.stdin.write(init_message + "\n")
    mcp_proc.stdin.flush()
    response_line = mcp_proc.stdout.readline()
    print("📥 Received init response:", response_line.strip())
except Exception as e:
    print("❌ Error during initialize:", e)

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    payload = await request.body()
    print("📥 Incoming request:", payload.decode())

    try:
        mcp_proc.stdin.write(payload.decode() + "\n")
        mcp_proc.stdin.flush()
    except Exception as e:
        print("❌ Failed writing to MCP subprocess:", e)
        return {"error": str(e)}

    try:
        response_line = mcp_proc.stdout.readline()
        print("📤 Raw MCP response:", response_line.strip())
        return json.loads(response_line.strip())
    except Exception as e:
        print("❌ Failed parsing MCP output:", e)
        return {"error": "Invalid MCP output", "raw": response_line.strip()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
