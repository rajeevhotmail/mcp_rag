#!/usr/bin/env python3
import sys
import json
import requests
import traceback
import datetime
import os

# Create a log directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

# Create a log file with timestamp
log_file = os.path.join(log_dir, f"mcp_proxy_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

def log_message(message):
    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        f.write(f"[{timestamp}] {message}\n")

# Log the start of the script
log_message("Proxy script started")

try:
    # Read from stdin
    input_data = sys.stdin.read()
    log_message(f"Received input data: {repr(input_data)}")

    # Parse the input as JSON
    try:
        request_data = json.loads(input_data)
        log_message(f"Parsed request data: {json.dumps(request_data, indent=2)}")

        # Special handling for initialize method
        if request_data.get("method") == "initialize":
            log_message("Handling initialize method")
            # Respond directly to initialize without forwarding
            response_data = {
                "jsonrpc": "2.0",
                "result": {
                    "serverInfo": {
                        "name": "rag-proxy",
                        "version": "0.1.0"
                    },
                    "capabilities": {}
                },
                "id": request_data.get("id")
            }
            response_str = json.dumps(response_data)
            log_message(f"Sending response: {response_str}")
            sys.stdout.write(response_str)
        else:
            log_message(f"Forwarding request to remote server: {request_data.get('method')}")
            # Forward other requests to your remote server
            response = requests.post(
                "http://34.192.154.118:8000/mcp",
                headers={"Content-Type": "application/json"},
                json=request_data,
                timeout=30
            )

            log_message(f"Received response from remote server: {response.status_code}")
            log_message(f"Response content: {response.text}")

            # Write the response to stdout
            sys.stdout.write(response.text)

    except json.JSONDecodeError as e:
        log_message(f"JSON decode error: {str(e)}")
        log_message("Trying to parse line by line...")

        # Try to parse line by line
        for i, line in enumerate(input_data.splitlines()):
            if line.strip():  # Skip empty lines
                log_message(f"Processing line {i+1}: {line}")
                try:
                    line_data = json.loads(line)
                    log_message(f"Successfully parsed line {i+1}")
                    # Process this line...
                except Exception as e:
                    log_message(f"Error parsing line {i+1}: {str(e)}")

        # Return an error response
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": f"Parse error: {str(e)}"
            },
            "id": None
        }
        response_str = json.dumps(error_response)
        log_message(f"Sending error response: {response_str}")
        sys.stdout.write(response_str)

except Exception as e:
    log_message(f"Fatal error: {str(e)}")
    log_message(traceback.format_exc())

    # Write a fallback error response to stdout
    error_response = {
        "jsonrpc": "2.0",
        "error": {
            "code": -32603,
            "message": f"Internal error: {str(e)}"
        },
        "id": None
    }
    response_str = json.dumps(error_response)
    log_message(f"Sending fatal error response: {response_str}")
    sys.stdout.write(response_str)

log_message("Proxy script finished")
