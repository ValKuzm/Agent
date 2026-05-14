import csv, os, re

def normalize(s):
    return str(s).strip().lower()

def extract_number(text):
    matches = re.findall(r'-?\d+\.?\d*', text)
    return matches[-1] if matches else text

def answers_match(a, b):
    """Мягкое сравнение: true, если строки равны или одна содержит другую."""
    a_norm = normalize(a)
    b_norm = normalize(b)
    if a_norm == b_norm:
        return True
    if a_norm in b_norm or b_norm in a_norm:
        return True
    num_a = extract_number(a)
    num_b = extract_number(b)
    return normalize(num_a) == normalize(num_b)

def calc_baseline_stats(filename):
    acc, n = 0.0, 0
    tokens = []
    iters = []
    if not os.path.isfile(filename):
        return acc, n, 0.0, 1.0
    with open(filename, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = row.get('expected_answer', '').strip()
            ans = row.get('answer', '').strip()
            if not exp or not ans:
                continue
            n += 1
            if answers_match(exp, ans):
                acc += 1
            try:
                tokens.append(int(row.get('tokens_used', 0)))
                iters.append(int(row.get('iterations', 1)))
            except:
                pass
    avg_tok = sum(tokens) / len(tokens) if tokens else 0.0
    avg_iter = sum(iters) / len(iters) if iters else 1.0
    return acc / n if n > 0 else 0.0, n, avg_tok, avg_iter

def calc_selfref_stats(filename):
    acc, n = 0.0, 0
    tokens = []
    iters = []
    initial_errors = 0
    corrected = 0
    if not os.path.isfile(filename):
        return acc, n, 0.0, 0.0, 0, 1.0
    with open(filename, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = row.get('expected_answer', '').strip()
            init_ans = row.get('initial_answer', '').strip()
            final_ans = row.get('final_answer', '').strip()
            if not final_ans:
                final_ans = init_ans
            if not exp or not final_ans:
                continue
            n += 1
            if answers_match(exp, final_ans):
                acc += 1
            if init_ans and not answers_match(exp, init_ans):
                initial_errors += 1
                if answers_match(exp, final_ans):
                    corrected += 1
            try:
                tokens.append(int(row.get('tokens_used', 0)))
                iters.append(int(row.get('iterations', 1)))
            except:
                pass
    ecr = corrected / initial_errors if initial_errors > 0 else 0.0
    avg_tok = sum(tokens) / len(tokens) if tokens else 0.0
    avg_iter = sum(iters) / len(iters) if iters else 1.0
    return acc, n, avg_tok, ecr, initial_errors, avg_iter

def calc_meta_stats(filename):
    acc, n = 0.0, 0
    tokens = []
    iters = []
    initial_errors = 0
    corrected = 0
    localized = 0
    if not os.path.isfile(filename):
        return acc, n, 0.0, 0.0, 0, 0.0, 1.0
    with open(filename, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = row.get('expected_answer', '').strip()
            corr_full = row.get('corrected_final', '').strip()
            if not corr_full:
                corr_full = row.get('corrected_answer', '').strip()
            init_full = row.get('initial_final', '').strip()
            if not init_full:
                init_full = row.get('initial_answer', '').strip()
            if not exp or not corr_full:
                continue
            n += 1
            if answers_match(exp, corr_full):
                acc += 1
            if init_full and not answers_match(exp, init_full):
                initial_errors += 1
                if answers_match(exp, corr_full):
                    corrected += 1
            err_text = row.get('errors', '')
            if re.search(r'\[Error Found\]\s*(YES|ДА)', err_text, re.IGNORECASE):
                localized += 1
            try:
                tokens.append(int(row.get('tokens_used', 0)))
                iters.append(int(row.get('iterations', 1)))
            except:
                pass
    ecr = corrected / initial_errors if initial_errors > 0 else 0.0
    loc_rate = localized / initial_errors if initial_errors > 0 else 0.0
    avg_tok = sum(tokens) / len(tokens) if tokens else 0.0
    avg_iter = sum(iters) / len(iters) if iters else 1.0
    return acc / n if n > 0 else 0.0, n, avg_tok, ecr, localized, loc_rate, avg_iter

if __name__ == "__main__":
    bl_acc, bl_n, bl_tok, bl_iter = calc_baseline_stats("data/baseline_results.csv")
    sr_acc, sr_n, sr_tok, sr_ecr, sr_err, sr_iter = calc_selfref_stats("data/selfref_results.csv")
    meta_acc, meta_n, meta_tok, meta_ecr, meta_loc, meta_loc_rate, meta_iter = calc_meta_stats("data/results.csv")

    print("=" * 60)
    print("ЭКСПЕРИМЕНТАЛЬНЫЕ МЕТРИКИ (с реальными итерациями)")
    print("=" * 60)

    print(f"\nBaseline – задач: {bl_n}")
    print(f"  Accuracy: {bl_acc:.3f} ({bl_acc*100:.1f}%)")
    print(f"  Avg tokens: {bl_tok:.1f}")
    print(f"  Avg iterations: {bl_iter:.1f}")

    print(f"\nSelf-reflection – задач: {sr_n}")
    print(f"  Accuracy (final): {sr_acc:.3f} ({sr_acc*100:.1f}%)")
    print(f"  Error Correction Rate: {sr_ecr:.3f} ({sr_ecr*100:.1f}%)")
    print(f"  Avg tokens: {sr_tok:.1f}")
    print(f"  Avg iterations: {sr_iter:.1f}")

    print(f"\nMeta-correction – задач: {meta_n}")
    print(f"  Accuracy (corrected): {meta_acc:.3f} ({meta_acc*100:.1f}%)")
    print(f"  Error Correction Rate: {meta_ecr:.3f} ({meta_ecr*100:.1f}%)")
    print(f"  Localization Success: {meta_loc_rate:.3f} ({meta_loc_rate*100:.1f}%)")
    print(f"  Avg tokens: {meta_tok:.1f}")
    print(f"  Avg iterations: {meta_iter:.1f}")

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
