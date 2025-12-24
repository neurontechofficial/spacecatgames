#!/usr/bin/env python3
import os
import subprocess
import logging
import time
from pathlib import Path
import requests

# --- Configuration ---
MODEL = "bigcode/starcoder"  # Hugging Face model for code generation
HF_TOKEN = os.getenv("HF_API_TOKEN")
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
    except subprocess.CalledProcessError as e:
        logging.warning("Command failed: %s", cmd)
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

def ask_hf(prompt):
    """Call Hugging Face Inference API"""
    if not HF_TOKEN:
        logging.warning("HF_API_TOKEN not set; skipping API call")
        return ""

    url = f"https://api-inference.huggingface.co/models/{MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    payload = {"inputs": prompt, "options": {"use_cache": False, "wait_for_model": True}}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        out = resp.json()
        # HF returns list of dicts with "generated_text"
        if isinstance(out, list) and "generated_text" in out[0]:
            return out[0]["generated_text"]
        elif isinstance(out, dict) and "error" in out:
            logging.warning("HF model error: %s", out["error"])
            return ""
        else:
            return str(out)
    except requests.exceptions.RequestException as e:
        logging.warning("Hugging Face API call failed: %s", e)
        return ""

def apply_patch(patch):
    """Apply git patch from string"""
    if not patch.strip():
        return
    try:
        p = subprocess.Popen(["git", "apply"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        _, err = p.communicate(patch, timeout=15)
        if p.returncode != 0:
            logging.warning("Patch failed: %s", err.strip())
    except Exception as e:
        logging.exception("Failed to apply patch: %s", e)

# --- Main Loop ---
logging.info("AI worker starting with Hugging Face model '%s'", MODEL)

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
Do add new features.
Do NOT change public APIs.
Output ONLY a unified git diff.
If no changes are needed, output NOTHING.

File: {file}
{text}
"""
        patch = ask_hf(prompt)
        if "diff --git" not in patch:
            logging.info("No valid diff returned for %s", file)
            continue
        apply_patch(patch)

    # Commit and push changes if any
    if run("git diff --stat").strip():
        logging.info("Committing changes...")
        run('git commit -am "chore: automated code improvements"')
        logging.info("Pushing to origin/%s", BRANCH)
        run(f"git push -u origin {BRANCH}")
    else:
        logging.info("No changes made this cycle")

    logging.info("Cycle complete, sleeping %s seconds\n", SLEEP_SECONDS)
    time.sleep(SLEEP_SECONDS)
