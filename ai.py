import json
import re
import time
import requests
from config import OPENROUTER_API_KEY

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-sonnet-4"
FALLBACK_MODEL = "anthropic/claude-haiku-4"


def _headers():
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://righthorizons.com",
        "X-Title": "Right Horizons Reporting",
    }


def _post(payload: dict, timeout: int = 120, _retries: int = 2) -> str:
    last_err = None
    for attempt in range(_retries + 1):
        try:
            resp = requests.post(OPENROUTER_URL, headers=_headers(), json=payload, timeout=timeout)
            if not resp.ok:
                body = resp.text[:500]
                if resp.status_code in (400, 404) and ("model" in body.lower() or "response_format" in body.lower()):
                    payload.pop("response_format", None)
                    payload["model"] = FALLBACK_MODEL
                    resp = requests.post(OPENROUTER_URL, headers=_headers(), json=payload, timeout=timeout)
                    if not resp.ok:
                        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text[:500]}")
                elif resp.status_code in (429, 500, 502, 503, 529) and attempt < _retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise RuntimeError(f"OpenRouter error {resp.status_code}: {body}")
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError):
                raise RuntimeError(f"Unexpected response: {json.dumps(data)[:500]}")
        except (requests.ConnectionError, requests.Timeout) as e:
            last_err = e
            if attempt < _retries:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"OpenRouter connection failed after {_retries + 1} attempts: {e}")
    raise RuntimeError(f"OpenRouter failed: {last_err}")


def chat(system: str, user: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    return _post(payload)


def _strip_fences(text: str) -> str:
    text = text.strip()
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        return m.group(1).strip()
    return text


def _slice_to_json_bounds(text: str) -> str:
    starts = [i for i in (text.find('['), text.find('{')) if i >= 0]
    if not starts:
        return text
    s = min(starts)
    e = max(text.rfind(']'), text.rfind('}'))
    if e > s:
        return text[s:e + 1]
    return text[s:]


def _basic_repair(text: str) -> str:
    text = re.sub(r',\s*([}\]])', r'\1', text)
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    open_sq, close_sq = text.count('['), text.count(']')
    open_cu, close_cu = text.count('{'), text.count('}')
    while open_cu > close_cu:
        text = text.rstrip().rstrip(',') + '}'
        close_cu += 1
    while open_sq > close_sq:
        text = text.rstrip().rstrip(',') + ']'
        close_sq += 1
    return text


def _ai_repair_json(broken: str, max_tokens: int) -> str:
    sys = (
        "You are a JSON repair tool. The user will give you broken JSON. "
        "Return ONLY the corrected, syntactically valid JSON. No commentary, "
        "no markdown, no code fences. Preserve all original content; only "
        "fix syntax (escape unescaped quotes inside strings, close brackets, "
        "remove trailing commas, fix smart quotes)."
    )
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": broken[:50000]},
        ],
    }
    return _post(payload)


def _parse_json(text: str, max_tokens: int = 6000):
    text = _strip_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    sliced = _slice_to_json_bounds(text)
    try:
        return json.loads(sliced)
    except json.JSONDecodeError:
        pass
    repaired = _basic_repair(sliced)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    try:
        fixed = _ai_repair_json(text, max_tokens)
        fixed = _strip_fences(fixed)
        return json.loads(fixed)
    except (json.JSONDecodeError, RuntimeError):
        pass
    try:
        return json.loads(_basic_repair(_slice_to_json_bounds(fixed)))
    except Exception:
        raise RuntimeError("Unable to parse AI JSON response after all repair attempts")


def chat_json(system: str, user: str, max_tokens: int = 4000, temperature: float = 0.7):
    sys_full = system + (
        "\n\nIMPORTANT: Respond with ONLY a valid JSON object of the form "
        '{"items": [...]} where items is the array described above. '
        'Escape all double quotes inside string values as \\". '
        "Use straight quotes only, no curly/smart quotes. "
        "No markdown, no code fences, no commentary."
    )
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": sys_full},
            {"role": "user", "content": user},
        ],
    }
    raw = _post(payload)
    return _parse_json(raw, max_tokens=max_tokens)


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
    sys_full = system + (
        "\n\nIMPORTANT: Respond with ONLY a valid JSON object. "
        'Escape all double quotes inside string values as \\". '
        "No markdown, no commentary."
    )
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": sys_full},
            {"role": "user", "content": [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]},
        ],
    }
    raw = _post(payload)
    return _parse_json(raw, max_tokens=max_tokens)
