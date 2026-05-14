import sys
import os
import re
import csv
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api_client import ask_yandexgpt_with_usage

# ------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ------------------------------------------------------------

def load_prompt(fname):
    path = os.path.join("prompts", fname)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def extract_final_answer(text):
    """
    Извлекает итоговый ответ из текста модели.
    Приоритет:
    1. Текст после маркера [Final Answer] (игнорируя регистр).
    2. Если маркера нет – последнее число (целое или дробное) в тексте.
    3. Иначе – весь текст (обрезанный).
    """
    # 1. Ищем [Final Answer]
    m = re.search(r"\[Final Answer\]\s*(.*?)(?=\n\[|$)", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 2. Последнее число (для числовых ответов)
    nums = re.findall(r'-?\d+\.?\d*', text)
    if nums:
        return nums[-1]
    # 3. Иначе – весь текст (для нечисловых логических ответов)
    return text.strip()

def compare_answers(answer, expected):
    """
    Сравнивает ответ с ожидаемым (игнорируя регистр, лишние пробелы, единицы измерения).
    """
    if expected is None:
        return None
    a = str(answer).strip().lower()
    e = str(expected).strip().lower()
    # Удаляем распространённые единицы измерения
    for unit in ["км", "руб", "рублей", "сек", "минут", "кошек", "конфет"]:
        a = a.replace(unit, "").strip()
        e = e.replace(unit, "").strip()
    return a == e

def run_verification(task, answer, expected_answer=None):
    """
    Вызывает модуль верификации (verify_prompt) и возвращает (result, reason, suggested_fix)
    result: "ПРАВИЛЬНО" / "НЕПРАВИЛЬНО"
    """
    sys_verify = load_prompt("verify_prompt.txt")
    verify_prompt = f"""
Задача:
{task}

Предлагаемый ответ:
{answer}

Ожидаемый правильный ответ (если известен):
{expected_answer if expected_answer else "Не указан"}

Проверь, соответствует ли ответ условию задачи.
"""
    response, _ = ask_yandexgpt_with_usage(
        verify_prompt,
        system_text=sys_verify,
        temperature=0.1,
        max_tokens=200
    )
    time.sleep(0.5)
    # Извлекаем результат
    m = re.search(r"\[Verification Result\]\s*(ПРАВИЛЬНО|НЕПРАВИЛЬНО)", response, re.IGNORECASE)
    result = m.group(1).upper() if m else "НЕПРАВИЛЬНО"
    # Извлекаем причину
    reason_m = re.search(r"\[Reason\](.*?)(?=\n\[|$)", response, re.DOTALL | re.IGNORECASE)
    reason = reason_m.group(1).strip() if reason_m else ""
    # Извлекаем предложение по исправлению
    fix_m = re.search(r"\[Suggested Fix\](.*?)(?=\n\[|$)", response, re.DOTALL | re.IGNORECASE)
    suggested_fix = fix_m.group(1).strip() if fix_m else ""
    return result, reason, suggested_fix

# ------------------------------------------------------------
# BASELINE (без изменений)
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# SELF-REFLECTION (улучшенная версия с верификацией)
# ------------------------------------------------------------

def run_selfreflection(task, expected_answer=None, max_iterations=7):
    result = {
        "task": task,
        "expected_answer": expected_answer,
        "initial_answer": "",
        "errors": "",
        "final_answer": "",
        "tokens_used": 0,
        "iterations": 0,
        "method": "selfref"
    }

    # ---------- INITIAL ----------
    sys_initial = load_prompt("initial_prompt.txt")
    answer, usage = ask_yandexgpt_with_usage(
        task,
        system_text=sys_initial,
        temperature=0.3,
        max_tokens=300
    )
    time.sleep(0.5)
    result["initial_answer"] = answer
    result["tokens_used"] += usage.get("totalTokens", 0)
    
    # ---------- ЦИКЛ КОРРЕКЦИИ ----------
    current_answer = answer
    history = []  # храним предыдущие ошибки и исправления

    for it in range(max_iterations):
        result["iterations"] = it + 1

        # ---- CRITIQUE ----
        sys_critique = load_prompt("critique_prompt.txt")
        critique_prompt = f"""
Задача:
{task}

Ответ модели:
{current_answer}

История предыдущих попыток (если есть):
{chr(10).join(history) if history else "Нет"}

Найди ошибки в ответе.
"""
        errors_text, usage = ask_yandexgpt_with_usage(
            critique_prompt,
            system_text=sys_critique,
            temperature=0.2,
            max_tokens=200
        )
        time.sleep(0.5)
        result["tokens_used"] += usage.get("totalTokens", 0)

        # Если critique не нашёл ошибок – выходим
        if not re.search(r"\[Error Found\]\s*ДА", errors_text, re.IGNORECASE):
            # Но всё равно проверим через верификатор (на случай, если critique пропустил)
            verif_result, verif_reason, _ = run_verification(task, current_answer, expected_answer)
            if verif_result == "ПРАВИЛЬНО":
                result["final_answer"] = current_answer
                result["errors"] = errors_text
                return result
            else:
                # Critique сказал "нет ошибок", но верификация показывает обратное
                # Добавляем принудительную ошибку в историю и продолжаем
                history.append(f"Попытка {it+1}: Верификация не прошла: {verif_reason}")
                continue

        # ---- CORRECTION ----
        sys_correction = load_prompt("correction_prompt.txt")
        correction_prompt = f"""
Задача:
{task}

Исходный ответ:
{current_answer}

Найденные ошибки:
{errors_text}

История предыдущих неудачных исправлений (если есть):
{chr(10).join(history) if history else "Нет"}

Исправь ответ. После исправления ОБЯЗАТЕЛЬНО выполни верификацию.
"""
        corrected, usage = ask_yandexgpt_with_usage(
            correction_prompt,
            system_text=sys_correction,
            temperature=0.2,
            max_tokens=300
        )
        time.sleep(0.5)
        result["tokens_used"] += usage.get("totalTokens", 0)

        # Извлекаем исправленный ответ (пытаемся найти [Final Answer] внутри corrected)
        corrected_answer = extract_final_answer(corrected)
        
        # ---- ВЕРИФИКАЦИЯ ИСПРАВЛЕНИЯ ----
        verif_result, verif_reason, suggested_fix = run_verification(task, corrected_answer, expected_answer)
        
        if verif_result == "ПРАВИЛЬНО":
            result["final_answer"] = corrected_answer
            result["errors"] = errors_text
            return result
        else:
            # Исправление не прошло – сохраняем в историю и пробуем ещё
            history.append(f"Попытка {it+1}: {errors_text[:100]} ... Верификация не пройдена: {verif_reason}")
            current_answer = corrected_answer  # обновляем для следующей итерации
            # Если это была последняя итерация – возвращаем последнее исправление (хоть и неверное)
            if it == max_iterations - 1:
                result["final_answer"] = corrected_answer
                result["errors"] = errors_text

    return result

# ------------------------------------------------------------
# META-CORRECTION (улучшенная версия)
# ------------------------------------------------------------

def run_meta_correction(task, expected_answer=None, max_iterations=7):
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
        "iterations": 0,
        "method": "meta"
    }

    # ---------- INITIAL ----------
    sys_init = load_prompt("initial_prompt.txt")
    answer, usage = ask_yandexgpt_with_usage(
        task,
        system_text=sys_init,
        temperature=0.3,
        max_tokens=500
    )
    time.sleep(0.5)
    result["initial_answer"] = answer
    result["initial_final"] = extract_final_answer(answer)
    result["tokens_used"] += usage.get("totalTokens", 0)

    current_answer = answer
    history = []  # храним (ошибка, исправление, причина неудачи)

    # ---------- ЦИКЛ КОРРЕКЦИИ ----------
    for it in range(max_iterations):
        result["iterations"] = it + 1

        # ---- CRITIQUE ----
        sys_crit = load_prompt("critique_prompt.txt")
        crit_prompt = f"""
Задача:
{task}

Ответ:
{current_answer}

История предыдущих попыток:
{chr(10).join(history) if history else "Нет"}

Проверь наличие ошибок.
"""
        errors_text, usage = ask_yandexgpt_with_usage(
            crit_prompt,
            system_text=sys_crit,
            temperature=0.2,
            max_tokens=200
        )
        time.sleep(0.5)
        result["tokens_used"] += usage.get("totalTokens", 0)
        result["errors"] = errors_text

        # Если critique не нашёл ошибок – проверяем верификатором
        if not re.search(r"\[Error Found\]\s*ДА", errors_text, re.IGNORECASE):
            verif_res, verif_reason, _ = run_verification(task, current_answer, expected_answer)
            if verif_res == "ПРАВИЛЬНО":
                result["corrected_answer"] = current_answer
                result["corrected_final"] = extract_final_answer(current_answer)
                # Формируем протокол (даже при отсутствии ошибок)
                result["protocol"] = "Ошибок не обнаружено, верификация пройдена."
                return result
            else:
                # Critique ошибся, добавим принудительную ошибку в историю
                history.append(f"Итерация {it+1}: critique не нашёл ошибок, но верификация не пройдена: {verif_reason}")
                continue

        # ---- CORRECTION ----
        sys_corr = load_prompt("correction_prompt.txt")
        corr_prompt = f"""
Задача:
{task}

Исходный ответ:
{current_answer}

Найденные ошибки:
{errors_text}

История предыдущих неудачных исправлений:
{chr(10).join(history) if history else "Нет"}

Исправь ответ. После исправления обязательно выполни верификацию.
"""
        corrected, usage = ask_yandexgpt_with_usage(
            corr_prompt,
            system_text=sys_corr,
            temperature=0.2,
            max_tokens=300
        )
        time.sleep(0.5)
        result["tokens_used"] += usage.get("totalTokens", 0)

        corrected_answer_full = corrected
        corrected_final = extract_final_answer(corrected)

        # ---- ВЕРИФИКАЦИЯ ----
        verif_res, verif_reason, suggested_fix = run_verification(task, corrected_final, expected_answer)

        if verif_res == "ПРАВИЛЬНО":
            result["corrected_answer"] = corrected_answer_full
            result["corrected_final"] = corrected_final
            # Формируем протокол
            sys_prot = load_prompt("protocol_prompt.txt")
            prot_prompt = f"""
Задача:
{task}

Исходный ответ:
{current_answer}

Диагностика:
{errors_text}

Исправленный ответ:
{corrected_answer_full}

Верификация пройдена успешно.
"""
            protocol, usage = ask_yandexgpt_with_usage(
                prot_prompt,
                system_text=sys_prot,
                temperature=0.1,
                max_tokens=150
            )
            time.sleep(0.5)
            result["protocol"] = protocol
            result["tokens_used"] += usage.get("totalTokens", 0)
            return result
        else:
            # Исправление неверное – сохраняем в историю и продолжаем
            history.append(f"Итерация {it+1}: ошибка – {errors_text[:100]}; исправление не прошло верификацию: {verif_reason}")
            current_answer = corrected_answer_full
            # Если последняя итерация – возвращаем последнее исправление (с пометкой)
            if it == max_iterations - 1:
                result["corrected_answer"] = corrected_answer_full
                result["corrected_final"] = corrected_final
                result["protocol"] = f"Не удалось исправить за {max_iterations} итераций. Последняя ошибка верификации: {verif_reason}"

    return result

# ------------------------------------------------------------
# ОБЁРТКИ ДЛЯ ЕДИНОГО ВЫЗОВА (совместимость с оригиналом)
# ------------------------------------------------------------

def run_task(task, expected_answer=None):
    """Обёртка для meta-correction (сохранение имени функции)"""
    return run_meta_correction(task, expected_answer, max_iterations=7)

def save_result(result, filename="data/results.csv"):
    """Без изменений – совместимость с исходным форматом CSV"""
    if result.get("method") == "baseline":
        fnames = ["task", "expected_answer", "answer", "tokens_used", "iterations", "method"]
    elif result.get("method") == "selfref":
        fnames = ["task", "expected_answer", "initial_answer", "errors", "final_answer", "tokens_used", "iterations", "method"]
    else:
        fnames = ["task", "expected_answer", "initial_answer", "initial_final", "errors", "corrected_answer", "corrected_final", "protocol", "tokens_used", "iterations", "method"]

    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fnames, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)
