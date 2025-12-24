import subprocess
import json
import os
import time
import logging
from pathlib import Path

MODEL = "tinyllama"
SLEEP_SECONDS = 1
MAX_LINES = 100
EXTS = {".js", ".ts", ".jsx", ".tsx", ".html", ".css"}

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return ""

def clean_repo():
    return run("git status --porcelain").strip() == ""

def get_files():
    files = run("git ls-files").splitlines()
    return [f for f in files if Path(f).suffix in EXTS]

def ask_ollama(prompt):
    try:
        p = subprocess.Popen(
            ["ollama", "run", MODEL],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        logging.warning("'ollama' binary not found; skipping AI patches.")
        return ""

    try:
        out, _ = p.communicate(prompt, timeout=90)
        return out
    except subprocess.TimeoutExpired:
        p.kill()
        logging.warning("Ollama timed out")
        return ""

def apply_patch(patch):
    try:
        p = subprocess.Popen(
            ["git", "apply"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        p.communicate(patch, timeout=10)
    except Exception:
        logging.exception("Failed to apply patch")

print("AI maintainer (Python, memory-safe) running")

while True:
    print("\n=== Cycle start ===")

    if not clean_repo():
        print("Repo dirty, skipping.")
        time.sleep(SLEEP_SECONDS)
        continue
    print("Fetching origin...")
    run("git fetch origin")
    print("checking out...")
    run("git checkout -B main origin/main")

    for file in get_files():
        try:
            text = "\n".join(Path(file).read_text().splitlines()[:MAX_LINES])
        except Exception:
            continue

        prompt = f"""
You are a senior developer.

Fix bugs and improve code quality.
Do NOT add features.
Do NOT change APIs.
Do NOT reformat unrelated code.
Output ONLY a unified git diff.

File: {file}

{text}
"""

        print(f"Processing {file}")
        try:
            patch = ask_ollama(prompt)
        except Exception:
            print("Ollama timeout, skipping file.")
            continue

        if "diff --git" not in patch:
            continue

        try:
            apply_patch(patch)
        except Exception:
            continue

    if run("git diff --stat").strip():
        run('git commit -am "chore: automated code improvements"')
        run("git push -u origin ai-maintenance")
        print("Changes committed and pushed.")
    else:
        print("No changes.")

    time.sleep(SLEEP_SECONDS)
