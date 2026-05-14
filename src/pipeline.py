import sys
import os
import re
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api_client import ask_yandexgpt_with_usage


def load_prompt(fname):
    path = os.path.join("prompts", fname)

    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def extract_final_answer(text):
    # 1. Ищем [Final Answer] (с любым регистром)
    m = re.search(r"\[Final Answer\]\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 2. Ищем последнее число, если маркера нет (запасной вариант)
    nums = re.findall(r'-?\d+\.?\d+', text)
    if nums:
        return nums[-1]
    # 3. Если совсем ничего нет, возвращаем весь текст (для нечисловых ответов)
    return text.strip()

# =========================================================
# BASELINE
# =========================================================

def run_baseline(task, expected_answer=None):

    system_baseline = load_prompt("baseline_prompt.txt")

    answer, usage = ask_yandexgpt_with_usage(
        task,
        system_text=system_baseline,
        temperature=0.3,
        max_tokens=300
    )

    return {
        "task": task,
        "expected_answer": expected_answer,
        "answer": answer,
        "tokens_used": usage.get("totalTokens", 0),
        "iterations": 1,
        "method": "baseline"
    }


# =========================================================
# SELF-REFLECTION
# =========================================================

def run_selfreflection(task, expected_answer=None):
    result = {
        "task": task,
        "expected_answer": expected_answer,
        "initial_answer": "",
        "errors": "",
        "final_answer": "",
        "tokens_used": 0,
        "iterations": 1,
        "method": "selfref"
    }

    # ---------------- INITIAL ----------------
    system_initial = load_prompt("initial_prompt.txt")
    answer, usage1 = ask_yandexgpt_with_usage(
        task,
        system_text=system_initial,
        temperature=0.3,
        max_tokens=300
    )
    result["initial_answer"] = answer
    result["tokens_used"] += usage1.get("totalTokens", 0)

    # ---------------- CRITIQUE ----------------
    system_critique = load_prompt("critique_prompt.txt")
    critique_prompt = f"""
Задача:
{task}

Ответ модели:
{answer}
"""
    errors, usage2 = ask_yandexgpt_with_usage(
        critique_prompt,
        system_text=system_critique,
        temperature=0.2,
        max_tokens=200
    )
    result["errors"] = errors
    result["tokens_used"] += usage2.get("totalTokens", 0)

    # ---------------- SELF-CORRECTION (только при YES) ----------------
    if re.search(r'\[Error Found\]\s*YES', errors, re.IGNORECASE):
        system_correction = load_prompt("correction_prompt.txt")
        correction_prompt = f"""
Задача:
{task}

Исходный ответ:
{answer}

Найденные ошибки:
{errors}

Исправь ответ.
"""
        corrected, usage3 = ask_yandexgpt_with_usage(
            correction_prompt,
            system_text=system_correction,
            temperature=0.2,
            max_tokens=300
        )
        final_answer = corrected
        result["tokens_used"] += usage3.get("totalTokens", 0)
    else:
        final_answer = answer

    # Сохраняем полный текст, а stats.py сам извлечёт число через extract_number
    result["final_answer"] = final_answer

    return result

# =========================================================
# META-CORRECTION
# =========================================================

def run_task(task, expected_answer=None):
    result = {
        "task": task,
        "expected_answer": expected_answer,
        "initial_answer": "",
        "initial_final": "",
        "errors": "",
        "corrected_answer": "",
        "corrected_final": "",
        "protocol": "",
        "tokens_used": 0,
        "iterations": 1,
        "method": "meta"
    }

    # ---------------- INITIAL ----------------
    sys_init = load_prompt("initial_prompt.txt")
    answer, usage = ask_yandexgpt_with_usage(
        task,
        system_text=sys_init,
        temperature=0.3,
        max_tokens=300
    )
    result["initial_answer"] = answer
    result["initial_final"] = extract_final_answer(answer)
    result["tokens_used"] += usage.get("totalTokens", 0)

    # ---------------- CRITIQUE ----------------
    sys_crit = load_prompt("critique_prompt.txt")
    crit_prompt = f"""
Задача:
{task}

Ответ:
{answer}
"""
    errors, usage = ask_yandexgpt_with_usage(
        crit_prompt,
        system_text=sys_crit,
        temperature=0.2,
        max_tokens=200
    )
    result["errors"] = errors
    result["tokens_used"] += usage.get("totalTokens", 0)

    # ---------------- CORRECTION (только при YES) ----------------
    if re.search(r'\[Error Found\]\s*YES', errors, re.IGNORECASE):
        sys_corr = load_prompt("correction_prompt.txt")
        corr_prompt = f"""
Задача:
{task}

Исходный ответ:
{answer}

Найденные ошибки:
{errors}
"""
        corrected, usage = ask_yandexgpt_with_usage(
            corr_prompt,
            system_text=sys_corr,
            temperature=0.2,
            max_tokens=300
        )
        result["tokens_used"] += usage.get("totalTokens", 0)
    else:
        # Ошибок нет (или формат не соблюдён) – оставляем исходный ответ
        corrected = answer

    result["corrected_answer"] = corrected
    result["corrected_final"] = extract_final_answer(corrected)

    # ---------------- PROTOCOL ----------------
    sys_prot = load_prompt("protocol_prompt.txt")
    prot_prompt = f"""
Задача:
{task}

Исходный ответ:
{answer}

Диагностика:
{errors}

Исправленный ответ:
{corrected}
"""
    protocol, usage = ask_yandexgpt_with_usage(
        prot_prompt,
        system_text=sys_prot,
        temperature=0.1,
        max_tokens=150
    )
    result["protocol"] = protocol
    result["tokens_used"] += usage.get("totalTokens", 0)

    return result


# =========================================================
# SAVE RESULTS
# =========================================================

def save_result(result, filename="data/results.csv"):

    if result.get("method") == "baseline":

        fnames = [
            "task",
            "expected_answer",
            "answer",
            "tokens_used",
            "iterations",
            "method"
        ]

    elif result.get("method") == "selfref":

        fnames = [
            "task",
            "expected_answer",
            "initial_answer",
            "errors",
            "final_answer",
            "tokens_used",
            "iterations",
            "method"
        ]

    else:

        fnames = [
            "task",
            "expected_answer",
            "initial_answer",
            "initial_final",
            "errors",
            "corrected_answer",
            "corrected_final",
            "protocol",
            "tokens_used",
            "iterations",
            "method"
        ]

    file_exists = os.path.isfile(filename)

    with open(filename, "a", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fnames,
            extrasaction='ignore'
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(result)
