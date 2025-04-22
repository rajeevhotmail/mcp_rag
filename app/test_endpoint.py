import requests
import json

"""
payload = {
    "jsonrpc": "2.0",
    "method": "queryContext",
    "params": {
        "question": "What does the kleur library do?",
        "repo": "/mnt/data/test_kleur"
    },
    "id": 1
}
"""
payload = {
    "jsonrpc": "2.0",
    "method": "listBranches",
    "params": {},
    "id": 1
}

response = requests.post("http://34.192.154.118:8000/mcp",
                         headers={"Content-Type": "application/json"},
                         data=json.dumps(payload))

print("✅ Status:", response.status_code)
print("📄 Response:", response.json())
