import os
import requests
import base64
from mcp.server.fastmcp import FastMCP

# GitHub API credentials
GH_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GH_TOKEN:
    print("Warning: No GITHUB_TOKEN set. You may hit GitHub API rate limits.")


# Utility: GitHub API request helper
def github_api(url, params=None):
    headers = {"Authorization": f"token {GH_TOKEN}"} if GH_TOKEN else {}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        raise Exception(f"GitHub API error: {resp.status_code}")
    return resp.json()

mcp = FastMCP("GitHub Repo MCP")

# 1. Resource: Read a file from a repository (by path)
@mcp.resource("repo://{owner}/{repo}/file/{filepath}")
def get_file_content(owner: str, repo: str, filepath: str) -> str:
    """Retrieve the content of a file from the given GitHub repo (default branch)."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}"
    try:
        data = github_api(api_url)
    except Exception as e:
        return f"(Error fetching file: {e})"

    if "content" in data:
        content_bytes = base64.b64decode(data["content"])
        # Limit content to some size to avoid massive files
        content = content_bytes.decode('utf-8', errors='ignore')
        if len(content) > 10000:
            content = content[:10000] + "\n...(truncated)"
        return f"File: {filepath}\n---\n{content}"
    else:
        return "(File content not available or not a file)"

# 2. Tool: Search repository for a keyword
@mcp.tool()
def search_repo(owner: str, repo: str, query: str) -> str:
    """Search for a keyword in the specified GitHub repository's code."""
    # Using GitHub code search API
    search_q = f"{query} repo:{owner}/{repo}"
    params = {"q": search_q}
    try:
        results = github_api("https://api.github.com/search/code", params=params)
    except Exception as e:
        return f"(Search error: {e})"

    items = results.get("items", [])
    if not items:
        return f"No code found for '{query}' in {owner}/{repo}."

    # List top 3 results
    response_lines = [f"Search results for '{query}' in {owner}/{repo}:"]
    for item in items[:3]:
        file_path = item.get("path")
        if file_path:
            response_lines.append(f"- {file_path}")
    if len(items) > 3:
        response_lines.append(f"...and {len(items)-3} more results")
    return "\n".join(response_lines)

if __name__ == "__main__":
    mcp.run(transport='stdio')
