import os
import requests

API_KEY = os.getenv("YC_API_KEY")
FOLDER_ID = os.getenv("YC_FOLDER_ID")

def ask_yandexgpt(prompt, system_text="", temperature=0.3, max_tokens=500):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }
    # Собираем сообщения, исключая пустые
    messages = []
    if system_text and system_text.strip():
        messages.append({"role": "system", "text": system_text.strip()})
    if prompt and prompt.strip():
        messages.append({"role": "user", "text": prompt.strip()})
    if not messages:
        raise ValueError("Both system_text and prompt are empty")

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
        raise Exception("API did not return 'result'. Check the printed response.")
    return data["result"]["alternatives"][0]["message"]["text"]
