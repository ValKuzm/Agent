import csv
import os
import re

def normalize(s):
    """Базовая нормализация: strip + lower."""
    return str(s).strip().lower()


def smart_normalize(s):
    """
    Умная нормализация для сравнения ответов:
    - убирает LaTeX-обёртки ($...$, \(...\))
    - убирает единицы измерения (км, минут, кошек, и т.д.)
    - заменяет запятую на точку в числах
    - убирает лишнюю пунктуацию
    - пытается извлечь число, если оно есть
    """
    text = str(s).strip().lower()

    # Убираем LaTeX-обёртки
    text = re.sub(r'\$([^$]*)\$', r'\1', text)
    text = re.sub(r'\\\(([^)]*)\\\)', r'\1', text)
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    # Убираем LaTeX-функции, оставляя результат если есть "= число"
    # \sqrt{144} = 12 → 12
    text = re.sub(r'\\?sqrt\{[^}]*\}\s*=\s*', '', text)
    text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'(\1/\2)', text)

    # Убираем LaTeX-переменные типа "x = "
    text = re.sub(r'[a-zа-яё]\s*=\s*', '', text)

    # Словесные числительные → цифры (порядковые, для "на восьмой день" и т.п.)
    ordinals = {
        'первый': '1', 'второй': '2', 'третий': '3', 'четвёртый': '4',
        'пятый': '5', 'шестой': '6', 'седьмой': '7', 'восьмой': '8',
        'девятый': '9', 'десятый': '10',
    }
    for word, digit in ordinals.items():
        text = re.sub(r'\b' + word + r'\b', digit, text)

    # Убираем единицы измерения и поясняющие слова
    units = [
        r'кошек', r'кошки', r'конфеты?', r'конфет',
        r'км', r'метр\w*', r'секунд\w*', r'минут\w*',
        r'рубл\w*', r'лет', r'годами', r'года', r'год',
    ]
    for u in units:
        text = re.sub(r'\b' + u + r'\b\.?', '', text)

    # Схлопываем множественные пробелы
    text = re.sub(r' {2,}', ' ', text)

    # Запятая → точка (для десятичных)
    text = re.sub(r'(\d),(\d)', r'\1.\2', text)

    # Убираем пунктуацию в конце
    text = re.sub(r'[.,;:!?\s]+$', '', text)
    text = text.strip()

    # Убираем пробелы вокруг математических операторов
    text = re.sub(r'\s*([+\-*/=])\s*', r'\1', text)

    # Пробуем извлечь число
    num_match = re.match(r'^-?\d+\.?\d*$', text)
    if num_match:
        return text

    # Если текст — математическое выражение (содержит +,-,*,/,=),
    # не пытаемся извлекать отдельные числа
    is_math_expr = bool(re.search(r'[+*/=]', text))

    if not is_math_expr:
        numbers = re.findall(r'-?\d+\.?\d*', text)
        # Единственное число в тексте → извлекаем
        if len(numbers) == 1:
            return numbers[0]
        # Несколько чисел: извлекаем последнее, только если
        # между числами нет значимых слов (союзов, предлогов и т.п.)
        # "100 машин за 5 минут" → "5" (ок)
        # "2 и 1" → оставляем как есть (составной ответ)
        if numbers and len(numbers) > 1:
            # Проверяем, есть ли между числами короткие слова-связки
            between = re.sub(r'-?\d+\.?\d*', '', text).strip()
            connectors = {'и', 'или', 'либо', 'а', 'но'}
            words_between = set(between.split())
            if not words_between & connectors:
                if re.search(r'-?\d+\.?\d*\s*$', text):
                    return numbers[-1]

    return text


def answers_match(expected, given):
    """
    Сравнивает ответы с умной нормализацией.
    Поддерживает несколько правильных ответов через | в expected.
    """
    ans_norm = smart_normalize(given)
    # Лёгкая нормализация для подстрочного поиска (без извлечения чисел)
    ans_light = str(given).strip().lower()

    # Поддержка нескольких правильных ответов: "ответ1|ответ2"
    for exp_variant in expected.split('|'):
        exp = smart_normalize(exp_variant.strip())

        if not exp:
            continue

        # Прямое совпадение
        if exp == ans_norm:
            return True

        # Числовое сравнение
        try:
            if float(exp) == float(ans_norm):
                return True
        except ValueError:
            pass

        # Проверяем, является ли эталон числом
        is_numeric = False
        try:
            float(exp)
            is_numeric = True
        except ValueError:
            pass

        # Подстрочный поиск ТОЛЬКО для текстовых эталонов.
        # Ищем по лёгкой нормализации, чтобы не терять контекст.
        if not is_numeric and len(exp) <= 10:
            if re.search(r'\b' + re.escape(exp) + r'\b', ans_light):
                return True

        # Для текстовых эталонов длиннее 3 символов
        # проверяем вхождение подстроки с границами слов
        if not is_numeric and len(exp) > 3:
            if re.search(r'\b' + re.escape(exp) + r'\b', ans_norm):
                return True
            # Для мат. выражений типа "888+88" ищем точное вхождение
            if re.search(r'[+\-*/=]', exp) and exp in ans_norm:
                return True

    return False

def extract_final_answer(text):
    """
    Извлекает содержимое после [Final Answer].
    Если блока нет — возвращает весь текст.
    """
    if not text:
        return ""

    match = re.search(
        r"\[Final Answer\](.*)",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if match:
        return normalize(match.group(1).strip())

    return normalize(text)

# ---------------------------------------------------
# BASELINE
# ---------------------------------------------------

def calc_baseline_stats(filename):
    acc = 0
    n = 0
    tokens = []

    if not os.path.isfile(filename):
        return 0.0, 0, 0.0

    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            exp = normalize(row.get('expected_answer', ''))
            ans = extract_final_answer(row.get('answer', ''))

            if exp:
                n += 1

                if ans and answers_match(exp, ans):
                    acc += 1

            try:
                tokens.append(int(row.get('tokens_used', 0)))
            except:
                pass

    avg_tok = sum(tokens) / len(tokens) if tokens else 0.0

    return acc / n if n > 0 else 0.0, n, avg_tok

# ---------------------------------------------------
# SELF-REFLECTION
# ---------------------------------------------------

def calc_selfref_stats(filename):
    acc = 0
    n = 0

    tokens = []

    initial_errors = 0
    corrected = 0

    if not os.path.isfile(filename):
        return 0.0, 0, 0.0, 0.0, 0

    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:

            exp = normalize(row.get('expected_answer', ''))

            init_ans = row.get('initial_answer', '')
            final_ans = row.get('final_answer', init_ans)

            init_final = extract_final_answer(init_ans)
            final_final = extract_final_answer(final_ans)

            if exp:

                n += 1

                if final_final and answers_match(exp, final_final):
                    acc += 1

                # считаем исправления
                if not answers_match(exp, init_final):

                    initial_errors += 1

                    if final_final and answers_match(exp, final_final):
                        corrected += 1

            try:
                tokens.append(int(row.get('tokens_used', 0)))
            except:
                pass

    ecr = corrected / initial_errors if initial_errors > 0 else 0.0

    avg_tok = sum(tokens) / len(tokens) if tokens else 0.0

    return (
        acc / n if n > 0 else 0.0,
        n,
        avg_tok,
        ecr,
        initial_errors
    )

# ---------------------------------------------------
# META-CORRECTION
# ---------------------------------------------------

def calc_meta_stats(filename):

    acc = 0
    n = 0

    tokens = []

    initial_errors = 0
    corrected = 0
    localized = 0
    false_positives = 0
    regressions = 0
    total_flagged = 0

    if not os.path.isfile(filename):
        return 0.0, 0, 0.0, 0.0, 0, 0.0

    with open(filename, 'r', encoding='utf-8') as f:

        reader = csv.DictReader(f)

        for row in reader:

            exp = normalize(row.get('expected_answer', ''))

            corr_full = row.get(
                'corrected_final',
                row.get('corrected_answer', '')
            )

            init_full = row.get(
                'initial_final',
                row.get('initial_answer', '')
            )

            corr_final = extract_final_answer(corr_full)
            init_final = extract_final_answer(init_full)

            if exp:

                n += 1

                if corr_final and answers_match(exp, corr_final):
                    acc += 1

            # correction rate
            if exp:

                if not answers_match(exp, init_final):

                    initial_errors += 1

                    if answers_match(exp, corr_final):
                        corrected += 1

            # localization: считаем только случаи, когда модель
            # нашла ошибку И initial действительно был неправильным
            err_text = row.get('errors', '')

            error_flagged = bool(
                re.search(r"\[Error Found\]\s*YES", err_text, re.IGNORECASE)
            )

            if error_flagged:
                total_flagged += 1
                if not answers_match(exp, init_final):
                    localized += 1
                else:
                    false_positives += 1

            # регрессия: initial правильный → corrected неправильный
            init_was_correct = answers_match(exp, init_final)
            corr_is_correct = corr_final and answers_match(exp, corr_final)
            if init_was_correct and not corr_is_correct:
                regressions += 1

            try:
                tokens.append(int(row.get('tokens_used', 0)))
            except:
                pass

    ecr = corrected / initial_errors if initial_errors > 0 else 0.0

    loc_rate = (
        localized / initial_errors
        if initial_errors > 0 else 0.0
    )

    avg_tok = sum(tokens) / len(tokens) if tokens else 0.0

    fp_rate = (
        false_positives / total_flagged
        if total_flagged > 0 else 0.0
    )

    return (
        acc / n if n > 0 else 0.0,
        n,
        avg_tok,
        ecr,
        localized,
        loc_rate,
        false_positives,
        fp_rate,
        regressions
    )

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

if __name__ == "__main__":

    bl_acc, bl_n, bl_tok = calc_baseline_stats(
        "data/baseline_results.csv"
    )

    sr_acc, sr_n, sr_tok, sr_ecr, sr_err = calc_selfref_stats(
        "data/selfref_results.csv"
    )

    (meta_acc, meta_n, meta_tok, meta_ecr,
     meta_loc, meta_loc_rate,
     meta_fp, meta_fp_rate, meta_regr) = calc_meta_stats(
        "data/results.csv"
    )

    print("=" * 60)
    print("ЭКСПЕРИМЕНТАЛЬНЫЕ МЕТРИКИ")
    print("=" * 60)

    # BASELINE

    print(f"\nBaseline – задач: {bl_n}")
    print(f"  Accuracy: {bl_acc:.3f} ({bl_acc*100:.1f}%)")
    print(f"  Avg tokens: {bl_tok:.1f}")

    # SELFREF

    print(f"\nSelf-reflection (с коррекцией) – задач: {sr_n}")
    print(f"  Accuracy (final): {sr_acc:.3f} ({sr_acc*100:.1f}%)")
    print(f"  Error Correction Rate: {sr_ecr:.3f} ({sr_ecr*100:.1f}%)")
    print(f"  Avg tokens: {sr_tok:.1f}")

    # META

    print(f"\nMeta-correction – задач: {meta_n}")
    print(f"  Accuracy (corrected): {meta_acc:.3f} ({meta_acc*100:.1f}%)")
    print(f"  Error Correction Rate: {meta_ecr:.3f} ({meta_ecr*100:.1f}%)")
    print(f"  Localization Success: {meta_loc_rate:.3f} ({meta_loc_rate*100:.1f}%)")
    print(f"  False Positives: {meta_fp} ({meta_fp_rate*100:.1f}%)")
    print(f"  Regressions: {meta_regr}")
    print(f"  Avg tokens: {meta_tok:.1f}")
    print(f"  Avg iterations: 1.0")
