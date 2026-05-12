import sys, os, re, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.api_client import ask_yandexgpt_with_usage

def load_prompt(fname):
    path = os.path.join("prompts", fname)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def extract_final_answer(text):
    """Извлекает текст после [Final Answer] (игнорируя регистр)."""
    m = re.search(r"\[Final Answer\]\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()

# ------------------- BASELINE -------------------
def run_baseline(task, expected_answer=None):
    system_baseline = load_prompt("baseline_prompt.txt")
    answer, usage = ask_yandexgpt_with_usage(task, system_text=system_baseline,
                                             temperature=0.3, max_tokens=300)
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
    system_initial = load_prompt("initial_prompt.txt")
    answer, usage1 = ask_yandexgpt_with_usage(task, system_text=system_initial,
                                             temperature=0.3, max_tokens=300)
    system_critique = load_prompt("critique_prompt.txt")
    critique_prompt = f"Задача: {task}\nОтвет:\n{answer}"
    errors, usage2 = ask_yandexgpt_with_usage(critique_prompt,
                                              system_text=system_critique,
                                              temperature=0.2, max_tokens=200)
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

    sys_init = load_prompt("initial_prompt.txt")
    answer, usage = ask_yandexgpt_with_usage(task, system_text=sys_init,
                                             temperature=0.3, max_tokens=300)
    result["initial_answer"] = answer
    result["initial_final"] = extract_final_answer(answer)
    result["tokens_used"] += usage.get("totalTokens", 0)

    sys_crit = load_prompt("critique_prompt.txt")
    crit_prompt = f"Задача: {task}\nОтвет:\n{answer}"
    errors, usage = ask_yandexgpt_with_usage(crit_prompt, system_text=sys_crit,
                                             temperature=0.2, max_tokens=200)
    result["errors"] = errors
    result["tokens_used"] += usage.get("totalTokens", 0)

    if re.search(r"\[Error Found\]\s*NO", errors, re.IGNORECASE):
        corrected = answer
    else:
        sys_corr = load_prompt("correction_prompt.txt")
        corr_prompt = f"Задача: {task}\nИсходный ответ:\n{answer}\nНайденные ошибки:\n{errors}"
        corrected, usage = ask_yandexgpt_with_usage(corr_prompt,
                                                    system_text=sys_corr,
                                                    temperature=0.2,
                                                    max_tokens=300)
        result["tokens_used"] += usage.get("totalTokens", 0)
    result["corrected_answer"] = corrected
    result["corrected_final"] = extract_final_answer(corrected)

    sys_prot = load_prompt("protocol_prompt.txt")
    prot_prompt = f"""Задача: {task}
Исходный ответ: {answer}
Диагностика: {errors}
Исправленный ответ: {corrected}"""
    protocol, usage = ask_yandexgpt_with_usage(prot_prompt, system_text=sys_prot,
                                               temperature=0.1, max_tokens=150)
    result["protocol"] = protocol
    result["tokens_used"] += usage.get("totalTokens", 0)

    return result

# ------------------- СОХРАНЕНИЕ -------------------
def save_result(result, filename="data/results.csv"):
    if result.get("method") == "baseline":
        fnames = ["task","expected_answer","answer","tokens_used","iterations","method"]
    elif result.get("method") == "selfref":
        fnames = ["task","expected_answer","initial_answer","errors","tokens_used","iterations","method"]
    else:
        fnames = ["task","expected_answer","initial_answer","initial_final","errors",
                  "corrected_answer","corrected_final","protocol","tokens_used","iterations","method"]
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fnames, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)
