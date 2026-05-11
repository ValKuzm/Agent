import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
from src.pipeline import run_task, save_result

def main():
    tasks = []
    with open("data/tasks.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append((row["id"], row["task"], row.get("expected_answer", "")))

    if not tasks:
        print("No tasks in data/tasks.csv. Please add tasks.")
        return

    for task_id, task_text, expected in tasks:
        print(f"Processing task {task_id}: {task_text}")
        result = run_task(task_text, expected)
        out_row = {
            "task": result["task"],
            "expected_answer": result["expected_answer"],
            "initial_answer": result["initial_answer"],
            "errors": result["errors"],
            "corrected_answer": result["corrected_answer"],
            "protocol": result["protocol"],
            "tokens_used": result["tokens_used"],
            "iterations": result["iterations"]
        }
        save_result(out_row)
        # Выводим ключевые результаты в консоль
        print(f"  Expected : {result['expected_answer']}")
        print(f"  Initial  : {result['initial_answer']}")
        print(f"  Errors   : {result['errors']}")
        print(f"  Corrected: {result['corrected_answer']}")
        print(f"  Protocol : {result['protocol']}")
        print(f"  Tokens used: {result['tokens_used']}")

    print("All tasks processed. Results in data/results.csv")

if __name__ == "__main__":
    main()
