import os
import requests
import openai
from dotenv import load_dotenv
from logging_config import get_logger

logger = get_logger("llm_client")
load_dotenv()

# Load settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "TOGETHER").upper()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Shared content
DEFAULT_MODEL = {
    "TOGETHER": "mistralai/Mistral-7B-Instruct-v0.1",
    "OPENAI": "gpt-3.5-turbo"
}

def query_llm(prompt: str, max_tokens: int = 800) -> str:
    provider = LLM_PROVIDER
    logger.info(f"Routing prompt to: {provider}")

    if provider == "OPENAI":
        return query_openai(prompt, DEFAULT_MODEL["OPENAI"], max_tokens)
    elif provider == "TOGETHER":
        return query_together(prompt, DEFAULT_MODEL["TOGETHER"], max_tokens)
    else:
        logger.error(f"Unsupported LLM_PROVIDER: {provider}")
        return "[Error] Unsupported provider."

def query_openai(prompt: str, model: str, max_tokens: int) -> str:
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a technical documentation assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        logger.info("OpenAI responded.")
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "[Error] OpenAI could not generate a response."

def query_together(prompt: str, model: str, max_tokens: int) -> str:
    try:
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a technical documentation assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info("Together.ai responded.")
        return result["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"Together.ai request failed: {e}")
        return "[Error] Together.ai could not generate a response."
