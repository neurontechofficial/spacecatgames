import os
import git
import time
import datetime
from groq import Groq
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
REPO_PATH = "."
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_ID = "llama-3.3-70b-versatile" # The "Smarter" Model
INTERVAL = 3600
FILES_TO_WATCH = ["index.html", "games.html", "style.css"]
LOG_FILE = "maintainer.log"

client = Groq(api_key=GROQ_API_KEY)

def log_action(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def is_html_valid(html_content):
    """Checks if the HTML has essential tags and isn't totally broken."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Check for basic structural integrity
    has_html = bool(soup.find('html'))
    has_body = bool(soup.find('body'))
    # BeautifulSoup automatically 'fixes' broken HTML.
    # If the fixed version is wildly different in length, it was probably broken.
    return has_html and has_body

def brainstorm_and_execute():
    # Read files for context
    context = ""
    for file in FILES_TO_WATCH:
        if os.path.exists(file):
            with open(file, "r") as f:
                context += f"\n### FILE: {file} ###\n{f.read()[:3000]}"

    log_action("🧠 Llama 3.3 70B is analyzing the project...")

    try:
        # STEP 1: BRAINSTORM
        plan = client.chat.completions.create(
            messages=[{"role": "system", "content": "You are a senior web architect. Suggest ONE small, safe UI improvement."},
                      {"role": "user", "content": context}],
            model=MODEL_ID, temperature=0.2
        )
        task = plan.choices[0].message.content.strip()
        log_action(f"💡 TASK: {task}")

        # STEP 2: EXECUTE
        exec_res = client.chat.completions.create(
            messages=[{"role": "system", "content": "Output ONLY the full updated code. Format: ### FILE: filename ###"},
                      {"role": "user", "content": f"Task: {task}\nContext: {context}"}],
            model=MODEL_ID, temperature=0.1
        )
        response = exec_res.choices[0].message.content

        # STEP 3: VALIDATE & APPLY
        parts = response.split("### FILE: ")
        changes_made = []

        for part in parts[1:]:
            lines = part.split("\n")
            filename = lines[0].strip(" #")
            content = "\n".join(lines[1:]).strip()

            if filename in FILES_TO_WATCH:
                # VALIDATION STEP
                if filename.endswith(".html"):
                    if not is_html_valid(content):
                        log_action(f"🛡️ REJECTED: {filename} failed HTML validation (missing tags).")
                        continue

                with open(filename, "w") as f:
                    f.write(content)
                changes_made.append(filename)

        return task, changes_made

    except Exception as e:
        log_action(f"❌ Error: {e}")
        return None, []

def sync_to_github(task):
    try:
        repo = git.Repo(REPO_PATH)
        repo.git.add(A=True)

        if not repo.is_dirty():
            return

        # Clean up the commit message
        clean_msg = task.split('\n')[0][:70].replace("One potential improvement is ", "")
        repo.index.commit(f"auto(70b): {clean_msg}")

        # PUSHING TO A SAFE BRANCH INSTEAD OF MAIN
        origin = repo.remote(name='origin')
        origin.push("main") # Change to "ai-dev" if you want to be extra safe
        log_action(f"🚀 SUCCESS: Pushed change to GitHub.")
    except Exception as e:
        log_action(f"⚠️ Git Error: {e}")

if __name__ == "__main__":
    log_action("🦾 Heavy-Duty AI Maintainer Started.")
    while True:
        task, files = brainstorm_and_execute()
        if files:
            sync_to_github(task)

        log_action(f"⏳ Next check in {INTERVAL/60} minutes.")
        time.sleep(INTERVAL)
