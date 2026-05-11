# Meta-Correction and Iteration

Исследовательский прототип системы метакоррекции для больших языковых моделей.  
Проект реализует технику **«Мета-коррекция и итерация»**, сравнивая три метода:
- **Baseline** (простой prompting),
- **Self‑reflection** (ответ + критика без исправления),
- **Meta‑correction** (полный цикл: генерация → критика → исправление → протокол антиошибок).

## Структура проекта

```
project/
├── data/
│   ├── tasks.csv                    # Датасет задач (id, task, expected_answer)
│   ├── baseline_results.csv         # Результаты базового метода
│   ├── selfref_results.csv          # Результаты self‑reflection
│   └── results.csv                  # Результаты meta‑correction
├── prompts/
│   ├── initial_prompt.txt           # Промпт генерации ответа
│   ├── critique_prompt.txt          # Промпт поиска ошибок
│   ├── correction_prompt.txt        # Промпт исправления ошибок
│   ├── protocol_prompt.txt          # Промпт формирования протокола
│   └── baseline_prompt.txt          # Промпт для baseline (только решение)
├── src/
│   ├── api_client.py                # Клиент для YandexGPT API
│   ├── pipeline.py                  # Реализация всех трёх методов
│   ├── main.py                      # Запуск эксперимента
│   └── metrics.py                   # Подсчёт метрик
├── experiments/                     # Дополнительные сводные таблицы
├── paper/                           # Научная статья
├── requirements.txt                 # Зависимости Python
└── README.md
```

## Требования

- Python 3.10 или выше
- Доступ к API YandexGPT (Yandex Cloud)
- Git (для клонирования репозитория)

## Быстрый старт

1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/ValKuzm/Agent.git
   cd Agent
   ```

2. **Создайте виртуальное окружение и установите зависимости**
   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Linux / macOS
   # или venv\Scripts\activate (Windows)
   pip install -r requirements.txt
   ```

3. **Настройте доступ к YandexGPT**
   - Получите API‑ключ сервисного аккаунта с ролью `ai.languageModels.user` (или `ai.editor`).
   - Узнайте идентификатор каталога (Folder ID).
   - Создайте файл `set_env.sh` (или установите переменные окружения вручную):
     ```bash
     export YC_API_KEY="AQVN..."
     export YC_FOLDER_ID="b1g..."
     ```
   - Выполните `source set_env.sh` или задайте переменные в вашей системе.

4. **Подготовьте датасет**
   - Отредактируйте `data/tasks.csv`, добавив свои задачи в формате:
     ```
     id,task,expected_answer
     1,17×24,408
     2,0.1+0.2,0.3
     ```

5. **Запустите эксперимент**
   ```bash
   python src/main.py
   ```
   Результаты будут сохранены в `data/baseline_results.csv`, `data/selfref_results.csv` и `data/results.csv`.

6. **Посчитайте метрики**
   ```bash
   python src/metrics.py
   ```
   Вывод покажет accuracy для baseline и meta‑correction, а также другие метрики.

## Метрики

- **Accuracy** – доля правильных итоговых ответов.
- **Error Correction Rate** – доля изначально ошибочных ответов, исправленных meta‑correction.
- **Token Usage** – суммарное количество токенов, потраченных на задачу.
- **Iteration Count** – количество итераций коррекции (в текущей версии 1).

## Воспроизводимость

Все команды и структура зафиксированы. Для повторения эксперимента достаточно клонировать репозиторий, установить зависимости и задать переменные окружения. Пайплайн полностью детерминирован: при одинаковых промптах и одинаковых задачах результаты будут воспроизводимы.

## Участники

- **Участник 1** – Теория и архитектура, промпты.
- **Участник 2** – Метрики и эксперименты.
- **Участник 3** – Программная реализация и воспроизводимость.
- **Участник 4** – Координация и оформление.

## Лицензия

Проект учебный, лицензия MIT.
