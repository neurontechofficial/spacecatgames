import os
import git
import time
import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
REPO_PATH = "."
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_ID = "llama-3.1-8b-instant"
INTERVAL = 60  # 1 Hour
FILES_TO_WATCH = ["index.html", "games.html", "style.css"]
LOG_FILE = "maintainer.log"

client = Groq(api_key=GROQ_API_KEY)

def log_action(message):
    """Writes a timestamped message to the log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    print(log_entry.strip())

def get_context():
    context = ""
    for file in FILES_TO_WATCH:
        if os.path.exists(file):
            with open(file, "r") as f:
                context += f"\n### FILE: {file} ###\n{f.read()[:2000]}"
    return context

def brainstorm_and_execute():
    context = get_context()
    log_action("🧠 Brainstorming next improvement...")

    try:
        # STEP 1: BRAINSTORM
        plan_res = client.chat.completions.create(
            messages=[{"role": "system", "content": "Suggest one small, valid web UI improvement."},
                      {"role": "user", "content": f"Context: {context}"}],
            model=MODEL_ID
        )
        task = plan_res.choices[0].message.content.strip()
        log_action(f"💡 AI DECISION: {task}")

        # STEP 2: EXECUTE
        exec_res = client.chat.completions.create(
            messages=[{"role": "system", "content": "Output ONLY code. Format: ### FILE: filename ###"},
                      {"role": "user", "content": f"Task: {task}\nContext: {context}"}],
            model=MODEL_ID
        )
        response = exec_res.choices[0].message.content

        # STEP 3: APPLY
        parts = response.split("### FILE: ")
        updated_files = []
        for part in parts[1:]:
            lines = part.split("\n")
            filename = lines[0].strip(" #")
            if filename in FILES_TO_WATCH:
                content = "\n".join(lines[1:])
                with open(filename, "w") as f:
                    f.write(content.strip())
                updated_files.append(filename)

        return task, updated_files
    except Exception as e:
        log_action(f"❌ API Error: {e}")
        return None, []

def sync_to_github(task):
    try:
        repo = git.Repo(REPO_PATH)
        repo.git.add(A=True)

        if not repo.is_dirty():
            log_action("ℹ️ No functional changes were made by the AI.")
            return

        # --- NEW CLEANING LOGIC ---
        # Strip AI "chatter" like "One potential improvement is..."
        clean_msg = task.replace("One potential web UI improvement for these HTML files is to ", "")
        clean_msg = clean_msg.replace("One potential web UI improvement is to ", "")
        clean_msg = clean_msg.replace("I suggest adding ", "Add ")

        # Ensure it's a single line and limited to 72 characters
        clean_msg = clean_msg.split('\n')[0][:72].strip()

        commit_msg = f"auto: {clean_msg}"
        # --------------------------

        repo.index.commit(commit_msg)

        origin = repo.remote(name='origin')
        origin.push("main")
        log_action(f"🚀 SUCCESS: Pushed '{commit_msg}' to GitHub.")
    except Exception as e:
        log_action(f"⚠️ Git Error: {e}")

if __name__ == "__main__":
    log_action("🤖 AI Maintainer Session Started.")
    while True:
        # Pull latest changes first to prevent conflicts
        try:
            repo = git.Repo(REPO_PATH)
            repo.remote().pull()
        except:
            pass

        task, files = brainstorm_and_execute()
        if files:
            sync_to_github(task)

        log_action(f"💤 Sleeping for {INTERVAL/60} minutes...")
        time.sleep(INTERVAL)
