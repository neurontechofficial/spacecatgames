import subprocess
import os
import time
import logging
from pathlib import Path

# =====================
# Configuration
# =====================

MODEL = "tinyllama"          # keep small for Steam Deck
SLEEP_SECONDS = 2
MAX_LINES = 300              # increased context
EXTS = {".js", ".ts", ".jsx", ".tsx", ".html", ".css"}
BRANCH = "main"

# Either:
#  - comma-separated literal list: "js,css,."
#  - or env var name containing such a list
WORKER_DIRS_SPEC = "js,css,."

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# =====================
# Helpers
# =====================

def run(cmd):
    try:
        return subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return ""

def clean_repo():
    return run("git status --porcelain") == ""

def is_skippable(file):
    return (
        file.endswith(".min.js")
        or file.endswith(".min.css")
        or "/libs/" in file
        or "/vendor/" in file
        or "/dist/" in file
        or "/build/" in file
    )

def get_allowed_dirs(files):
    spec = WORKER_DIRS_SPEC

    if "," not in spec:
        spec = os.environ.get(spec, "")

    if spec:
        allowed = [d.strip() for d in spec.split(",") if d.strip()]
        return allowed[:3]

    tops = []
    for f in files:
        if "/" in f:
            top = f.split("/", 1)[0]
            if top not in tops:
                tops.append(top)
                if len(tops) >= 3:
                    break
    return tops

def get_files():
    files = run("git ls-files").splitlines()
    allowed = set(get_allowed_dirs(files))
    logging.info(
        "Allowed top-level dirs: %s",
        ",".join(allowed) if allowed else "(none)",
    )

    out = []
    for f in files:
        if Path(f).suffix not in EXTS:
            continue
        if is_skippable(f):
            continue
        top = f.split("/", 1)[0] if "/" in f else "."
        if top in allowed:
            out.append(f)
    return out

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
        logging.warning("ollama not found")
        return ""

    try:
        out, _ = p.communicate(prompt, timeout=120)
        return out or ""
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

# =====================
# Main loop
# =====================

print("🤖 AI maintainer running")

while True:
    print("\n=== Cycle start ===")

    if not clean_repo():
        print("Repo dirty, skipping.")
        time.sleep(SLEEP_SECONDS)
        continue

    print("Fetching origin...")
    run("git fetch origin")

    print("Checking out branch...")
    run(f"git checkout -B {BRANCH} origin/{BRANCH}")

    for file in get_files():
        try:
            lines = Path(file).read_text(errors="ignore").splitlines()
            text = "\n".join(lines[:MAX_LINES])
        except Exception:
            continue

        prompt = f"""
You are a senior developer performing automated maintenance.

Task:
- Fix bugs, edge cases, and obvious correctness issues
- Small refactors for clarity are allowed
- Do add new features
- Do improve the user experience
- Do NOT change public APIs
- Do NOT reformat unrelated code

Rules:
- Output ONLY a unified git diff
- If no real issues exist, output nothing
- Keep changes minimal

File: {file}

{text}
"""

        print(f"Processing {file}")
        patch = ask_ollama(prompt)

        if not patch.strip():
            continue

        if "diff --git" not in patch:
            print("Non-diff response (ignored):")
            print(patch[:200])
            continue

        apply_patch(patch)

    if run("git diff --stat"):
        print("Committing changes...")
        run('git commit -am "chore: automated code improvements"')
        print("Pushing changes...")
        run(f"git push -u origin {BRANCH}")
        print("Changes committed and pushed.")
    else:
        print("No changes.")

    time.sleep(SLEEP_SECONDS)
