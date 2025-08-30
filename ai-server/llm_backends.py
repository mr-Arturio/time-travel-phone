import os, requests

ENDPOINT = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:8001/v1")
MODEL    = os.environ.get("LLM_MODEL",  os.environ.get("VLLM_MODEL", "gpt-oss-20B"))
TIMEOUT  = float(os.environ.get("LLM_TIMEOUT", "20"))

def _get(url: str, timeout: float = TIMEOUT) -> requests.Response:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r

def health() -> bool:
    """Return True if the vLLM server responds to /v1/models."""
    try:
        _get(f"{ENDPOINT}/models")
        return True
    except Exception:
        return False

def chat(system: str, user: str, temperature: float = 0.7, max_tokens: int = 256) -> str:
    """OpenAI-compatible /v1/chat/completions call to vLLM."""
    url = f"{ENDPOINT}/chat/completions"
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        "temperature": float(os.environ.get("LLM_TEMPERATURE", temperature)),
        "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", max_tokens)),
    }
    r = requests.post(url, json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()
