#!/usr/bin/env python3
import os
import subprocess
import logging
import time
from pathlib import Path
import requests

# --- Configuration ---
MODEL = "gemini-2.0-flash-exp"  # Gemini 2.0 Flash model
GEMINI_KEY = os.getenv("GEMINI_API_KEY")  # must be set
SLEEP_SECONDS = 5
EXTS = {".js", ".ts", ".jsx", ".tsx", ".html", ".css"}
BRANCH = "main"
WORKER_DIRS = ["js", "css", "."]  # top-level directories or root

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# --- Helper Functions ---
def run(cmd):
    """Run shell command, return stdout or empty string on error"""
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return ""


def clean_repo():
    """Check if repo has uncommitted changes"""
    return run("git status --porcelain").strip() == ""


def get_files():
    """Get list of files matching extensions in allowed dirs"""
    files = run("git ls-files").splitlines()
    allowed = set(WORKER_DIRS)
    result = []
    for f in files:
        suffix = Path(f).suffix
        top = f.split("/", 1)[0] if "/" in f else "."
        if suffix in EXTS and top in allowed:
            result.append(f)
    logging.info("Files to process: %s", result if result else "(none)")
    return result


def ask_gemini(prompt):
    """Call Gemini API"""
    if not GEMINI_KEY:
        logging.warning("GEMINI_API_KEY not set; skipping API call.")
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    headers = {"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "candidateCount": 1,
            "maxOutputTokens": 1024,
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        out = resp.json()
        # Gemini returns text in out['candidates'][0]['content']['parts'][0]['text']
        if "candidates" in out and len(out["candidates"]) > 0:
            candidate = out["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                return candidate["content"]["parts"][0]["text"]
        
        logging.warning("No valid output from Gemini: %s", out)
        return ""
    except requests.exceptions.RequestException as e:
        logging.warning("Gemini API call failed: %s", e)
        return ""


def safe_diff(file):
    """Return a minimal valid patch so git apply always works"""
    return f"""diff --git a/{file} b/{file}
index 0000000..0000000 100644
--- a/{file}
+++ b/{file}
+// no-op dummy line
"""


def apply_patch(patch):
    """Apply git patch from string"""
    if not patch.strip():
        return
    try:
        p = subprocess.Popen(["git", "apply"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        _, err = p.communicate(patch, timeout=15)
        if p.returncode != 0:
            logging.warning("Patch failed, applying safe no-op")
            safe = safe_diff(file)
            subprocess.run(["git", "apply"], input=safe, text=True)
    except Exception as e:
        logging.exception("Failed to apply patch: %s", e)


# --- Main Loop ---
logging.info("AI worker starting with Gemini model '%s'", MODEL)

while True:
    logging.info("=== Cycle start ===")

    if not clean_repo():
        logging.info("Repo dirty, skipping this cycle")
        time.sleep(SLEEP_SECONDS)
        continue

    logging.info("Fetching origin...")
    run("git fetch origin")
    logging.info("Checking out branch %s", BRANCH)
    run(f"git checkout -B {BRANCH} origin/{BRANCH}")

    files = get_files()
    if not files:
        logging.info("No files to process")
        time.sleep(SLEEP_SECONDS)
        continue

    for file in files:
        logging.info("Processing %s", file)
        try:
            text = "\n".join(Path(file).read_text().splitlines()[:200])
        except Exception as e:
            logging.warning("Could not read file %s: %s", file, e)
            continue

        prompt = f"""
You are a senior developer.
Fix bugs and improve code quality.
Add new features if appropriate.
Do NOT change public APIs.
Output ONLY a unified git diff, suitable for git apply.
Always produce a diff, even if it's a no-op.

File: {file}
{text}
"""
        patch = ask_gemini(prompt)
        if not patch.strip() or "diff --git" not in patch:
            logging.info("No valid model diff for %s, using safe diff", file)
            patch = safe_diff(file)

        apply_patch(patch)

    # Commit and push changes if any
    if run("git diff --stat").strip():
        logging.info("Committing changes...")
        run('git commit -am "chore: automated code improvements"')
        logging.info("Pushing to origin/%s", BRANCH)
        run(f"git push -u origin {BRANCH}")
    else:
        logging.info("No changes this cycle")

    logging.info("Cycle complete, sleeping %s seconds\n", SLEEP_SECONDS)
    time.sleep(SLEEP_SECONDS)

