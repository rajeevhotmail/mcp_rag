// mcp_bridge.js
// A minimal MCP-compliant stdin/stdout proxy that forwards JSON-RPC messages to a local FastAPI server
const readline = require("readline");
const axios = require("axios");
const fs = require("fs");

const TARGET_URL = process.env.TARGET_URL || "http://127.0.0.1:8000";

// File logger function
function logToFile(message) {
  const timestamp = new Date().toISOString();
  fs.appendFileSync("mcp_bridge.log", `[${timestamp}] ${message}\n`);
}

// Initialize reader from stdin
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

logToFile("🚀 MCP Bridge started. Forwarding requests to: " + TARGET_URL);

rl.on("line", async (line) => {
  let request;
  try {
    request = JSON.parse(line);
  } catch (err) {
    logToFile("❌ Invalid JSON input: " + line);
    return;
  }

  try {
    const response = await axios.post(TARGET_URL, request);
    const responseData = response.data;

    // Handle responses (skip request revalidation)
    if (!responseData.method) {
      logToFile("ZZZ Work: Skipping revalidation. Sending back raw result to client.");
      process.stdout.write(JSON.stringify(responseData) + "\n");
    } else {
      logToFile("⚠️ Unexpected method field in response: " + responseData.method);
      process.stdout.write(JSON.stringify(responseData) + "\n");
    }

  } catch (err) {
    const errorResponse = {
      jsonrpc: "2.0",
      id: request.id || null,
      error: {
        code: -32000,
        message: err.message
      }
    };
    process.stdout.write(JSON.stringify(errorResponse) + "\n");
    logToFile("❌ Error forwarding request: " + err.message);
  }
});
