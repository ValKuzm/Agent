import os
import requests

API_KEY = os.getenv("YC_API_KEY")
FOLDER_ID = os.getenv("YC_FOLDER_ID")

def _call_api(messages, temperature=0.3, max_tokens=500):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": str(max_tokens)
        },
        "messages": messages
    }
    resp = requests.post(url, json=body, headers=headers)
    data = resp.json()
    if 'result' not in data:
        import json
        print("Server response:", json.dumps(data, indent=2, ensure_ascii=False))
        raise Exception("API did not return 'result'")
    raw_usage = data["result"]["usage"]
    # Приводим числовые поля к int (пропуская вложенные словари, например completionTokensDetails)
    usage = {}
    for k, v in raw_usage.items():
        if isinstance(v, dict):
            usage[k] = v   # оставляем как есть (например, completionTokensDetails)
        else:
            try:
                usage[k] = int(v)
            except (ValueError, TypeError):
                usage[k] = v   # если не получилось, оставляем исходное значение
    text = data["result"]["alternatives"][0]["message"]["text"]
    return text, usage

def ask_yandexgpt(prompt, system_text="", temperature=0.3, max_tokens=500):
    messages = []
    if system_text and system_text.strip():
        messages.append({"role": "system", "text": system_text.strip()})
    if prompt and prompt.strip():
        messages.append({"role": "user", "text": prompt.strip()})
    if not messages:
        raise ValueError("Both system_text and prompt are empty")
    text, _ = _call_api(messages, temperature, max_tokens)
    return text

def ask_yandexgpt_with_usage(prompt, system_text="", temperature=0.3, max_tokens=500):
    messages = []
    if system_text and system_text.strip():
        messages.append({"role": "system", "text": system_text.strip()})
    if prompt and prompt.strip():
        messages.append({"role": "user", "text": prompt.strip()})
    if not messages:
        raise ValueError("Both system_text and prompt are empty")
    return _call_api(messages, temperature, max_tokens)
