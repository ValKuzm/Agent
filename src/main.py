import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
from src.pipeline import run_task, run_baseline, run_selfreflection, save_result

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
        print(f"\nProcessing task {task_id}: {task_text}")

        # Baseline
        print("  [baseline]")
        bl = run_baseline(task_text, expected)
        save_result(bl, "data/baseline_results.csv")
        print(f"    Answer: {bl['answer'][:80]}...")

        # Self-reflection
        print("  [selfref]")
        sr = run_selfreflection(task_text, expected)
        save_result(sr, "data/selfref_results.csv")
        print(f"    Initial: {sr['initial_answer'][:80]}...")
        print(f"    Errors: {sr['errors'][:80]}...")

        # Meta-correction
        print("  [meta]")
        meta = run_task(task_text, expected)
        save_result(meta, "data/results.csv")
        print(f"    Initial: {meta['initial_answer'][:80]}...")
        print(f"    Errors: {meta['errors'][:80]}...")
        print(f"    Corrected: {meta['corrected_answer'][:80]}...")
        print(f"    Tokens: {meta['tokens_used']}")

    print("\nAll methods completed. Results saved to data/")

if __name__ == "__main__":
    main()
