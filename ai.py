import json
import requests
from config import OPENROUTER_API_KEY

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-sonnet-4-6"
FALLBACK_MODEL = "anthropic/claude-3.5-sonnet"


def _headers():
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://righthorizons.com",
        "X-Title": "Right Horizons Reporting",
    }


def _post(payload: dict, timeout: int = 90) -> str:
    resp = requests.post(OPENROUTER_URL, headers=_headers(), json=payload, timeout=timeout)
    if not resp.ok:
        if resp.status_code == 404 or "model" in resp.text.lower():
            payload["model"] = FALLBACK_MODEL
            resp = requests.post(OPENROUTER_URL, headers=_headers(), json=payload, timeout=timeout)
            if not resp.ok:
                raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text[:500]}")
        else:
            raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected response: {json.dumps(data)[:500]}")


def chat(system: str, user: str, max_tokens: int = 2000) -> str:
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    return _post(payload)


def _repair_json(text: str) -> str:
    import re
    text = re.sub(r',\s*([}\]])', r'\1', text)
    if text.count('[') > text.count(']'):
        text = text.rstrip().rstrip(',') + ']'
    if text.count('{') > text.count('}'):
        text = text.rstrip().rstrip(',') + '}'
    text = re.sub(r'(?<!\\)\n', ' ', text)
    return text


def _extract_json(text: str):
    text = text.strip()
    if "```" in text:
        import re
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if m:
            text = m.group(1).strip()
    for attempt in range(3):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if attempt == 0:
                start = text.find("[")
                startobj = text.find("{")
                candidates = [c for c in (start, startobj) if c >= 0]
                if candidates:
                    s = min(candidates)
                    end = max(text.rfind("]"), text.rfind("}"))
                    if end > s:
                        text = text[s:end + 1]
                        continue
            if attempt <= 1:
                text = _repair_json(text)
                continue
            raise


def chat_json(system: str, user: str, max_tokens: int = 3000):
    sys_full = system + (
        "\n\nIMPORTANT: Respond with ONLY a valid JSON object of the form "
        '{"items": [...]} where items is the array described above. '
        "Escape all double quotes inside string values as \\\". "
        "Use straight quotes only, no curly/smart quotes. No markdown, no commentary."
    )
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": sys_full},
            {"role": "user", "content": user},
        ],
    }
    raw = _post(payload)
    return _extract_json(raw)


def chat_vision(system: str, user: str, image_data_url: str, max_tokens: int = 2000) -> str:
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]},
        ],
    }
    return _post(payload)


def chat_vision_json(system: str, user: str, image_data_url: str, max_tokens: int = 2000):
    sys_full = system + "\n\nIMPORTANT: Respond with ONLY valid JSON. No markdown, no commentary."
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": sys_full},
            {"role": "user", "content": [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]},
        ],
    }
    raw = _post(payload)
    return _extract_json(raw)
