# THIS SCRIPT WAS WRITTEN BY AI. I AM TRASH AT PYTHON, THATS WHY.

import os
import git
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
REPO_PATH = "."  # Current directory (or put full path to your web project)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BRANCH_NAME = "main" # Change to 'master' or your dev branch if needed

def generate_commit_message(diff_text):
    """Uses Groq to generate a concise commit message based on code changes."""
    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
    You are an expert developer. Read the following git diff and write a
    concise, conventional commit message (e.g., 'feat: add user login', 'fix: resolve css bug').
    Do not use markdown formatting or quotes. Just the raw message.

    GIT DIFF:
    {diff_text[:4000]} # Truncate to avoid token limits if diff is huge
    """

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant", # Fast and cheap model good for this task
    )

    return chat_completion.choices[0].message.content.strip()

def maintain_project():
    try:
        # Initialize Git Repo
        repo = git.Repo(REPO_PATH)

        # Check for dirty index (uncommitted changes) or untracked files
        if not repo.is_dirty(untracked_files=True):
            print("✅ No changes detected. Project is clean.")
            return

        print("Changes detected. Staging files...")
        repo.git.add(all=True)

        # Get the diff of staged files to send to Groq
        # 'HEAD' compares staged changes to the last commit
        diff = repo.git.diff("HEAD", cached=True)

        if not diff:
            print("⚠ No substantial changes in diff (perhaps only whitespace).")
            return

        print("🧠 Analyzing changes with Groq...")
        commit_message = generate_commit_message(diff)
        print(f"📝 Generated Commit Message: {commit_message}")

        # Commit
        repo.index.commit(commit_message)
        print("🔒 Changes committed.")

        # Push
        origin = repo.remote(name='origin')
        print(f"🚀 Pushing to {BRANCH_NAME}...")
        origin.push(BRANCH_NAME)
        print("✨ Project successfully maintained and synced!")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    maintain_project()
