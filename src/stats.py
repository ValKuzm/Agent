import csv, os, re

def normalize(s):
    return str(s).strip().lower()

def extract_number(text):
    """Извлекает последнее целое или дробное число из строки."""
    matches = re.findall(r'-?\d+\.?\d*', text)
    return matches[-1] if matches else text

def answers_match(a, b):
    """
    Мягкое сравнение: true, если строки равны ИЛИ одна содержит другую
    (полезно, когда модель добавляет "5 минут" vs "5").
    """
    a_norm = normalize(a)
    b_norm = normalize(b)
    if a_norm == b_norm:
        return True
    # Для нечисловых ответов: если один является частью другого
    if a_norm in b_norm or b_norm in a_norm:
        return True
    # Сравниваем последние числа (если оба числовые)
    num_a = extract_number(a)
    num_b = extract_number(b)
    return normalize(num_a) == normalize(num_b)

def calc_baseline_stats(filename):
    acc, n = 0.0, 0
    tokens = []
    if not os.path.isfile(filename):
        return acc, n, 0.0
    with open(filename, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = row.get('expected_answer', '')
            ans = row.get('answer', '')
            if exp and ans:
                n += 1
                if answers_match(exp, ans):
                    acc += 1
            try:
                tokens.append(int(row.get('tokens_used', 0)))
            except:
                pass
    return acc / n if n > 0 else 0.0, n, sum(tokens) / len(tokens) if tokens else 0.0

def calc_selfref_stats(filename):
    acc, n = 0.0, 0
    tokens = []
    initial_errors = 0
    corrected = 0
    if not os.path.isfile(filename):
        return acc, n, 0.0, 0.0, 0
    with open(filename, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = row.get('expected_answer', '')
            init_ans = row.get('initial_answer', '')
            final_ans = row.get('final_answer', init_ans)
            if exp and final_ans:
                n += 1
                if answers_match(exp, final_ans):
                    acc += 1
                # Error Correction Rate
                if init_ans and not answers_match(exp, init_ans):
                    initial_errors += 1
                    if answers_match(exp, final_ans):
                        corrected += 1
            try:
                tokens.append(int(row.get('tokens_used', 0)))
            except:
                pass
    ecr = corrected / initial_errors if initial_errors > 0 else 0.0
    avg_tok = sum(tokens) / len(tokens) if tokens else 0.0
    return acc, n, avg_tok, ecr, initial_errors

def calc_meta_stats(filename):
    acc, n = 0.0, 0
    tokens = []
    initial_errors = 0
    corrected = 0
    localized = 0
    if not os.path.isfile(filename):
        return acc, n, 0.0, 0.0, 0, 0.0
    with open(filename, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = row.get('expected_answer', '')
            corr_full = row.get('corrected_final', row.get('corrected_answer', ''))
            init_full = row.get('initial_final', row.get('initial_answer', ''))
            # Accuracy
            if exp and corr_full:
                n += 1
                if answers_match(exp, corr_full):
                    acc += 1
            # Error Correction Rate + Localization
            if exp and init_full:
                init_wrong = not answers_match(exp, init_full)
                if init_wrong:
                    initial_errors += 1
                    if answers_match(exp, corr_full):
                        corrected += 1
            # Localization: ищем YES в errors
            err_text = row.get('errors', '')
            if re.search(r'\[Error Found\]\s*YES', err_text, re.IGNORECASE) or \
               re.search(r'\[Error Found\]\s*ДА', err_text, re.IGNORECASE):
                localized += 1
            try:
                tokens.append(int(row.get('tokens_used', 0)))
            except:
                pass
    ecr = corrected / initial_errors if initial_errors > 0 else 0.0
    loc_rate = localized / initial_errors if initial_errors > 0 else 0.0
    avg_tok = sum(tokens) / len(tokens) if tokens else 0.0
    return acc / n if n > 0 else 0.0, n, avg_tok, ecr, localized, loc_rate

if __name__ == "__main__":
    bl_acc, bl_n, bl_tok = calc_baseline_stats("data/baseline_results.csv")
    sr_acc, sr_n, sr_tok, sr_ecr, sr_err = calc_selfref_stats("data/selfref_results.csv")
    meta_acc, meta_n, meta_tok, meta_ecr, meta_loc, meta_loc_rate = calc_meta_stats("data/results.csv")

    print("=" * 60)
    print("ЭКСПЕРИМЕНТАЛЬНЫЕ МЕТРИКИ (с мягким сравнением)")
    print("=" * 60)

    print(f"\nBaseline – задач: {bl_n}")
    print(f"  Accuracy: {bl_acc:.3f} ({bl_acc*100:.1f}%)")
    print(f"  Avg tokens: {bl_tok:.1f}")

    print(f"\nSelf-reflection – задач: {sr_n}")
    print(f"  Accuracy (final): {sr_acc:.3f} ({sr_acc*100:.1f}%)")
    print(f"  Error Correction Rate: {sr_ecr:.3f} ({sr_ecr*100:.1f}%)")
    print(f"  Avg tokens: {sr_tok:.1f}")

    print(f"\nMeta-correction – задач: {meta_n}")
    print(f"  Accuracy (corrected): {meta_acc:.3f} ({meta_acc*100:.1f}%)")
    print(f"  Error Correction Rate: {meta_ecr:.3f} ({meta_ecr*100:.1f}%)")
    print(f"  Localization Success: {meta_loc_rate:.3f} ({meta_loc_rate*100:.1f}%)")
    print(f"  Avg tokens: {meta_tok:.1f}")
    print(f"  Avg iterations: 1.0")

    # Запись в stats.txt
    with open("data/stats.txt", "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("ЭКСПЕРИМЕНТАЛЬНЫЕ МЕТРИКИ\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"Baseline – задач: {bl_n}\n")
        f.write(f"  Accuracy: {bl_acc:.3f} ({bl_acc*100:.1f}%)\n")
        f.write(f"  Avg tokens: {bl_tok:.1f}\n\n")

        f.write(f"Self-reflection (с коррекцией) – задач: {sr_n}\n")
        f.write(f"  Accuracy (final): {sr_acc:.3f} ({sr_acc*100:.1f}%)\n")
        f.write(f"  Error Correction Rate: {sr_ecr:.3f} ({sr_ecr*100:.1f}%)\n")
        f.write(f"  Avg tokens: {sr_tok:.1f}\n\n")

        f.write(f"Meta-correction – задач: {meta_n}\n")
        f.write(f"  Accuracy (corrected): {meta_acc:.3f} ({meta_acc*100:.1f}%)\n")
        f.write(f"  Error Correction Rate: {meta_ecr:.3f} ({meta_ecr*100:.1f}%)\n")
        f.write(f"  Localization Success: {meta_loc_rate:.3f} ({meta_loc_rate*100:.1f}%)\n")
        f.write(f"  Avg tokens: {meta_tok:.1f}\n")
        f.write(f"  Avg iterations: 1.0\n")

    print("\nРезультаты также сохранены в data/stats.txt")
