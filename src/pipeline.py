import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
from src.api_client import ask_yandexgpt_with_usage

def load_prompt(filename):
    path = os.path.join("prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def run_task(task, expected_answer=None):
    result = {
        "task": task,
        "expected_answer": expected_answer,
        "initial_answer": "",
        "errors": "",
        "corrected_answer": "",
        "protocol": "",
        "tokens_used": 0,
        "iterations": 1
    }

    # Шаг 1
    system_initial = load_prompt("initial_prompt.txt")
    answer, usage = ask_yandexgpt_with_usage(task, system_text=system_initial,
                                             temperature=0.3, max_tokens=300)
    result["initial_answer"] = answer
    result["tokens_used"] += usage.get("totalTokens", 0)

    # Шаг 2
    system_critique = load_prompt("critique_prompt.txt")
    critique_prompt = f"Задача: {task}\nОтвет:\n{answer}"
    errors, usage = ask_yandexgpt_with_usage(critique_prompt, system_text=system_critique,
                                             temperature=0.3, max_tokens=200)
    result["errors"] = errors
    result["tokens_used"] += usage.get("totalTokens", 0)

    # Шаг 3
    system_correction = load_prompt("correction_prompt.txt")
    correction_prompt = f"Задача: {task}\nИсходный ответ:\n{answer}\nНайденные ошибки:\n{errors}"
    corrected, usage = ask_yandexgpt_with_usage(correction_prompt, system_text=system_correction,
                                                temperature=0.3, max_tokens=300)
    result["corrected_answer"] = corrected
    result["tokens_used"] += usage.get("totalTokens", 0)

    # Шаг 4
    system_protocol = load_prompt("protocol_prompt.txt")
    protocol_prompt = f"Задача: {task}\nОшибки: {errors}"
    protocol, usage = ask_yandexgpt_with_usage(protocol_prompt, system_text=system_protocol,
                                               temperature=0.3, max_tokens=150)
    result["protocol"] = protocol
    result["tokens_used"] += usage.get("totalTokens", 0)

    return result

def save_result(result, filename="data/results.csv"):
    fieldnames = ["task", "expected_answer", "initial_answer", "errors",
                  "corrected_answer", "protocol", "tokens_used", "iterations"]
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)
