import os
import logging
import json
import requests

HF_TOKEN = os.getenv("HF_API_TOKEN")
# pick a model from Hugging Face Hub, e.g. a code‑friendly one like starcoder or LLaMA‑based
HF_MODEL = "bigcode/starcoder"  # adapt if you want another

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

def ask_hf(prompt):
    if not HF_TOKEN:
        logging.warning("No HF_API_TOKEN set; skipping call.")
        return ""

    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

    payload = {
        "inputs": prompt,
        "options": {
            "use_cache": False,
            "wait_for_model": True
        }
    }

    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=90)
        response.raise_for_status()
        out = response.json()

        # HF Inference API returns a list of possible completions in JSON
        # If you get a direct string, adapt accordingly
        if isinstance(out, list) and 'generated_text' in out[0]:
            return out[0]["generated_text"]
        elif isinstance(out, dict) and "error" in out:
            logging.warning("HF model error: %s", out["error"])
            return ""
        else:
            # sometimes JSON is different, try raw text
            return str(out)

    except requests.exceptions.RequestException as e:
        logging.error("Hugging Face API call failed: %s", e)
        return ""
