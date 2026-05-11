import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
from src.api_client import ask_yandexgpt_with_usage

def load_prompt(filename):
    path = os.path.join("prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

# ------------------- BASELINE -------------------
def run_baseline(task, expected_answer=None):
    """
    Обычный prompting (один вызов модели, system_text пустой).
    Возвращает словарь с результатом.
    """
    answer, usage = ask_yandexgpt_with_usage(task, system_text="", temperature=0.3, max_tokens=300)
    return {
        "task": task,
        "expected_answer": expected_answer,
        "answer": answer,
        "tokens_used": usage.get("totalTokens", 0),
        "iterations": 1,
        "method": "baseline"
    }

# ------------------- SELF-REFLECTION -------------------
def run_selfreflection(task, expected_answer=None):
    """
    Ответ + критика (без исправления). Возвращает ответ, ошибки и токены.
    """
    system_initial = load_prompt("initial_prompt.txt")
    answer, usage1 = ask_yandexgpt_with_usage(task, system_text=system_initial,
                                             temperature=0.3, max_tokens=300)
    system_critique = load_prompt("critique_prompt.txt")
    critique_prompt = f"Задача: {task}\nОтвет:\n{answer}"
    errors, usage2 = ask_yandexgpt_with_usage(critique_prompt,
                                              system_text=system_critique,
                                              temperature=0.2,
                                              max_tokens=200)
    return {
        "task": task,
        "expected_answer": expected_answer,
        "initial_answer": answer,
        "errors": errors,
        "tokens_used": usage1.get("totalTokens", 0) + usage2.get("totalTokens", 0),
        "iterations": 1,
        "method": "selfref"
    }

# ------------------- META-CORRECTION -------------------
def run_task(task, expected_answer=None):
    """
    Полный цикл метакоррекции с условием пропуска коррекции,
    если ошибок не найдено. Температуры снижены для critique и protocol.
    """
    result = {
        "task": task,
        "expected_answer": expected_answer,
        "initial_answer": "",
        "errors": "",
        "corrected_answer": "",
        "protocol": "",
        "tokens_used": 0,
        "iterations": 1,
        "method": "meta"
    }

    # 1. Генерация ответа
    system_initial = load_prompt("initial_prompt.txt")
    answer, usage = ask_yandexgpt_with_usage(task, system_text=system_initial,
                                             temperature=0.3, max_tokens=300)
    result["initial_answer"] = answer
    result["tokens_used"] += usage.get("totalTokens", 0)

    # 2. Критика (температура снижена до 0.2)
    system_critique = load_prompt("critique_prompt.txt")
    critique_prompt = f"Задача: {task}\nОтвет:\n{answer}"
    errors, usage = ask_yandexgpt_with_usage(critique_prompt, system_text=system_critique,
                                             temperature=0.2, max_tokens=200)
    result["errors"] = errors
    result["tokens_used"] += usage.get("totalTokens", 0)

    # 3. Исправление (только если найдены ошибки)
    NO_ERROR_MARKERS = ["ошибок нет", "no errors", "no_errors_found", "ответ верный"]
    if any(marker in errors.lower() for marker in NO_ERROR_MARKERS):
        corrected = answer
    else:
        system_correction = load_prompt("correction_prompt.txt")
        correction_prompt = f"Задача: {task}\nИсходный ответ:\n{answer}\nНайденные ошибки:\n{errors}"
        corrected, usage = ask_yandexgpt_with_usage(correction_prompt,
                                                    system_text=system_correction,
                                                    temperature=0.2,
                                                    max_tokens=300)
        result["tokens_used"] += usage.get("totalTokens", 0)
    result["corrected_answer"] = corrected

    # 4. Протокол (температура снижена до 0.1, промпт расширен)
    system_protocol = load_prompt("protocol_prompt.txt")
    protocol_prompt = f"""
Задача: {task}
Исходный ответ: {answer}
Диагностика: {errors}
Исправленный ответ: {corrected}
"""
    protocol, usage = ask_yandexgpt_with_usage(protocol_prompt, system_text=system_protocol,
                                               temperature=0.1, max_tokens=150)
    result["protocol"] = protocol
    result["tokens_used"] += usage.get("totalTokens", 0)

    return result

# ------------------- СОХРАНЕНИЕ (общая функция) -------------------
def save_result(result, filename="data/results.csv"):
    """Записывает результат в CSV. Поля зависят от метода."""
    # Определяем заголовки в зависимости от метода
    if result.get("method") == "baseline":
        fieldnames = ["task", "expected_answer", "answer", "tokens_used", "iterations", "method"]
    elif result.get("method") == "selfref":
        fieldnames = ["task", "expected_answer", "initial_answer", "errors", "tokens_used", "iterations", "method"]
    else:  # meta
        fieldnames = ["task", "expected_answer", "initial_answer", "errors",
                      "corrected_answer", "protocol", "tokens_used", "iterations", "method"]

    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)
