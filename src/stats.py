import csv, os, re

def normalize(s):
    return str(s).strip().lower()

def extract_number(text):
    matches = re.findall(r'-?\d+\.?\d*', text)
    return matches[-1] if matches else text

def calc_baseline_stats(filename):
    acc, n = 0.0, 0
    tokens = []
    if not os.path.isfile(filename):
        return acc, n, 0.0
    with open(filename, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = normalize(row.get('expected_answer', ''))
            ans = normalize(extract_number(row.get('answer', '')))
            if exp and ans:
                n += 1
                if exp == ans:
                    acc += 1
            try:
                tokens.append(int(row['tokens_used']))
            except:
                pass
    return acc / n if n > 0 else 0.0, n, sum(tokens)/len(tokens) if tokens else 0.0

def calc_selfref_stats(filename):
    acc, n = 0.0, 0
    tokens = []
    initial_errors = 0
    corrected = 0
    if not os.path.isfile(filename):
        return acc, n, 0.0, 0.0, 0
    with open(filename, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            exp = normalize(row.get('expected_answer', ''))
            init_ans = row.get('initial_answer', '')
            final_ans = row.get('final_answer', init_ans)
            init_num = normalize(extract_number(init_ans))
            final_num = normalize(extract_number(final_ans))
            if exp and final_num:
                n += 1
                if exp == final_num:
                    acc += 1
                if init_num and init_num != exp:
                    initial_errors += 1
                    if final_num == exp:
                        corrected += 1
            try:
                tokens.append(int(row['tokens_used']))
            except:
                pass
    ecr = corrected / initial_errors if initial_errors > 0 else 0.0
    avg_tok = sum(tokens)/len(tokens) if tokens else 0.0
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
            exp = normalize(row.get('expected_answer', ''))
            corr_full = row.get('corrected_final', row.get('corrected_answer', ''))
            corr_num = normalize(extract_number(corr_full))
            init_full = row.get('initial_final', row.get('initial_answer', ''))
            init_num = normalize(extract_number(init_full))
            if exp and corr_num:
                n += 1
                if exp == corr_num:
                    acc += 1
            if exp and init_num:
                if init_num != exp:
                    initial_errors += 1
                    if corr_num == exp:
                        corrected += 1
            err_text = row.get('errors', '')
            if re.search(r'\[Error Found\]\s*YES', err_text, re.IGNORECASE):
                localized += 1
            try:
                tokens.append(int(row['tokens_used']))
            except:
                pass
    ecr = corrected / initial_errors if initial_errors > 0 else 0.0
    loc_rate = localized / initial_errors if initial_errors > 0 else 0.0
    avg_tok = sum(tokens)/len(tokens) if tokens else 0.0
    return acc / n if n > 0 else 0.0, n, avg_tok, ecr, localized, loc_rate

if __name__ == "__main__":
    bl_acc, bl_n, bl_tok = calc_baseline_stats("data/baseline_results.csv")
    sr_acc, sr_n, sr_tok, sr_ecr, sr_err = calc_selfref_stats("data/selfref_results.csv")
    meta_acc, meta_n, meta_tok, meta_ecr, meta_loc, meta_loc_rate = calc_meta_stats("data/results.csv")

    print("=" * 60)
    print("ЭКСПЕРИМЕНТАЛЬНЫЕ МЕТРИКИ")
    print("=" * 60)

    print(f"\nBaseline – задач: {bl_n}")
    print(f"  Accuracy: {bl_acc:.3f} ({bl_acc*100:.1f}%)")
    print(f"  Avg tokens: {bl_tok:.1f}")

    print(f"\nSelf-reflection (с коррекцией) – задач: {sr_n}")
    print(f"  Accuracy (final): {sr_acc:.3f} ({sr_acc*100:.1f}%)")
    print(f"  Error Correction Rate: {sr_ecr:.3f} ({sr_ecr*100:.1f}%)")
    print(f"  Avg tokens: {sr_tok:.1f}")

    print(f"\nMeta-correction – задач: {meta_n}")
    print(f"  Accuracy (corrected): {meta_acc:.3f} ({meta_acc*100:.1f}%)")
    print(f"  Error Correction Rate: {meta_ecr:.3f} ({meta_ecr*100:.1f}%)")
    print(f"  Localization Success: {meta_loc_rate:.3f} ({meta_loc_rate*100:.1f}%)")
    print(f"  Avg tokens: {meta_tok:.1f}")
    print(f"  Avg iterations: 1.0")
