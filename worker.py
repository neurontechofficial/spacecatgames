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
INTERVAL = 300  # Set to 5 minutes (300s) to avoid spamming
MODEL_ID = "llama-3.1-8b-instant"

def generate_commit_message(diff_text):
    client = Groq(api_key=GROQ_API_KEY)

    # Using a System Message is the best way to keep the AI concise
    system_prompt = "You are a git automation tool. Respond ONLY with a single-line conventional commit message. No markdown, no quotes, no explanations."
    user_prompt = f"Generate a commit message for this diff:\n\n{diff_text[:4000]}"

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=MODEL_ID,
        temperature=0.2, # Lower temperature makes it more focused/less creative
    )
    return chat_completion.choices[0].message.content.strip()

def maintain_project():
    try:
        repo = git.Repo(REPO_PATH)

        if not repo.is_dirty(untracked_files=True):
            print(f"[{time.strftime('%H:%M:%S')}] ✅ No changes. Sleeping...")
            return

        # Stage everything
        repo.git.add(A=True)

        # Safety: Check for .env again
        staged_files = [item.a_path for item in repo.index.diff("HEAD")]
        if ".env" in staged_files:
            print("🛡️ Safety: .env detected. Removing from staging...")
            repo.git.rm("--cached", ".env")
            repo.index.commit("chore: ignore sensitive files")
            return

        # Commit and Push
        diff = repo.git.diff("HEAD", cached=True)
        if diff:
            print("🧠 Analyzing changes with Llama 3.1...")
            msg = generate_commit_message(diff)

            # Clean up the message just in case it still uses markdown or quotes
            msg = msg.replace('`', '').replace('"', '').split('\n')[0]

            repo.index.commit(msg)
            print(f"📝 Committed: {msg}")

            print("🚀 Pushing to GitHub...")
            origin = repo.remote(name='origin')
            origin.push(BRANCH_NAME)
            print("✨ Sync complete.")

    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    print(f"🤖 AI Maintainer active. Model: {MODEL_ID}")
    while True:
        maintain_project()
        time.sleep(INTERVAL)
