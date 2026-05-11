import csv
import sys
import os

def calc_accuracy(filename, answer_field):
    """Считает долю правильных ответов, сравнивая expected_answer и answer_field."""
    correct = 0
    total = 0
    if not os.path.isfile(filename):
        print(f"Файл {filename} не найден.")
        return 0.0, 0
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            expected = row.get("expected_answer", "").strip().lower()
            given = row.get(answer_field, "").strip().lower()
            if expected and given:
                total += 1
                if expected == given:
                    correct += 1
    return correct / total if total > 0 else 0.0, total

def calc_error_correction_rate(filename):
    """
    Для meta‑correction: считает долю случаев,
    когда initial_answer НЕ совпадает с expected, а corrected_answer — совпадает.
    """
    errors_found = 0
    corrected = 0
    total_tasks = 0
    if not os.path.isfile(filename):
        print(f"Файл {filename} не найден.")
        return 0.0
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_tasks += 1
            expected = row.get("expected_answer", "").strip().lower()
            initial = row.get("initial_answer", "").strip().lower()
            fixed = row.get("corrected_answer", "").strip().lower()
            if not expected:
                continue
            if initial != expected:
                errors_found += 1
                if fixed == expected:
                    corrected += 1
    return corrected / errors_found if errors_found > 0 else 0.0

def calc_avg_tokens(filename):
    """Среднее количество токенов на задачу."""
    total_tokens = 0
    count = 0
    if not os.path.isfile(filename):
        print(f"Файл {filename} не найден.")
        return 0.0
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                tokens = int(row.get("tokens_used", 0))
                total_tokens += tokens
                count += 1
            except (ValueError, TypeError):
                pass
    return total_tokens / count if count > 0 else 0.0

if __name__ == "__main__":
    print("=" * 60)
    print("МЕТРИКИ ЭКСПЕРИМЕНТА")
    print("=" * 60)

    # Baseline
    bl_acc, bl_total = calc_accuracy("data/baseline_results.csv", "answer")
    bl_tokens = calc_avg_tokens("data/baseline_results.csv")
    print(f"\nBaseline (обычный prompting):")
    print(f"  Всего задач: {bl_total}")
    print(f"  Accuracy: {bl_acc:.2%}")
    print(f"  Среднее токенов: {bl_tokens:.1f}")

    # Self‑reflection
    sr_acc, sr_total = calc_accuracy("data/selfref_results.csv", "initial_answer")
    sr_tokens = calc_avg_tokens("data/selfref_results.csv")
    print(f"\nSelf‑reflection (ответ + критика):")
    print(f"  Всего задач: {sr_total}")
    print(f"  Accuracy: {sr_acc:.2%}")
    print(f"  Среднее токенов: {sr_tokens:.1f}")

    # Meta‑correction
    meta_acc, meta_total = calc_accuracy("data/results.csv", "corrected_answer")
    meta_tokens = calc_avg_tokens("data/results.csv")
    ecr = calc_error_correction_rate("data/results.csv")
    print(f"\nMeta‑correction (полный цикл):")
    print(f"  Всего задач: {meta_total}")
    print(f"  Accuracy (corrected): {meta_acc:.2%}")
    print(f"  Error Correction Rate: {ecr:.2%}")
    print(f"  Среднее токенов: {meta_tokens:.1f}")

    # Вывод ярких примеров ошибок
    print("\n" + "=" * 60)
    print("ПРИМЕРЫ НАЙДЕННЫХ ОШИБОК (из results.csv):")
    if os.path.isfile("data/results.csv"):
        with open("data/results.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("errors", "").strip() and "ошибок нет" not in row["errors"].lower():
                    print(f"\nЗадача: {row['task']}")
                    print(f"  Ожидался: {row['expected_answer']}")
                    print(f"  Исходный: {row['initial_answer'][:100]}...")
                    print(f"  Исправлен: {row['corrected_answer'][:100]}...")
                    print(f"  Протокол: {row['protocol'][:100]}...")
    print("\nГотово.")
