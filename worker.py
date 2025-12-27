import os
import git
import time
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
REPO_PATH = "."
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BRANCH_NAME = "main"
INTERVAL = 5

def generate_commit_message(diff_text):
    client = Groq(api_key=GROQ_API_KEY)
    prompt = f"Write a concise, professional git commit message for these changes:\n\n{diff_text[:4000]}"

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
    )
    return chat_completion.choices[0].message.content.strip()

def maintain_project():
    try:
        repo = git.Repo(REPO_PATH)

        # Check for dirty state
        if not repo.is_dirty(untracked_files=True):
            print(f"[{time.strftime('%H:%M:%S')}] ✅ No changes. Sleeping...")
            return

        # Stage and protect .env
        repo.git.add(A=True)
        staged_files = [item.a_path for item in repo.index.diff("HEAD")]
        if ".env" in staged_files:
            print("❌ ERROR: .env detected! Untracking it now...")
            repo.git.rm("--cached", ".env")
            return

        # Commit
        diff = repo.git.diff("HEAD", cached=True)
        msg = generate_commit_message(diff)
        repo.index.commit(msg)
        print(f"📝 Committed: {msg}")

        # Push
        print("🚀 Pushing...")
        origin = repo.remote(name='origin')
        origin.push(BRANCH_NAME)
        print("✨ Sync complete.")

    except Exception as e:
        print(f"❌ Loop Error: {e}")

if __name__ == "__main__":
    print(f"🤖 AI Maintainer started. Monitoring every {INTERVAL/60} minutes.")
    print("Press Ctrl+C to stop.")

    while True:
        maintain_project()
        time.sleep(INTERVAL)
