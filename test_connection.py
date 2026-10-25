"""
Step 1: Confirm your Nebius Token Factory API key works and Nemotron responds.

Run this FIRST, before touching the extraction logic. If this script prints
a sensible answer, your key + billing + model access are all working.

Usage:
    1. Copy .env.example to .env and paste your real key into it.
    2. pip install -r requirements.txt
    3. python test_connection.py
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env file into environment variables

api_key = os.environ.get("NEBIUS_API_KEY")
if not api_key:
    raise SystemExit(
        "NEBIUS_API_KEY not found. Did you create a .env file from .env.example "
        "and paste your real key into it?"
    )

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=api_key,
)

# Start with a cheap/fast model to confirm access before using bigger ones.
MODEL_NAME = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"

print(f"Calling {MODEL_NAME} on Nebius Token Factory...\n")

response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[
        {"role": "system", "content": "You are a helpful, concise assistant."},
        {"role": "user", "content": "In one sentence, what is a mechanical seal used for in industrial pumps?"},
    ],
)

message = response.choices[0].message

# Nemotron models sometimes return the real answer in `reasoning_content`
# instead of `content` when reasoning mode is on. Handle both cases.
content = getattr(message, "content", None)
reasoning_content = getattr(message, "reasoning_content", None)

if content:
    print("SUCCESS. Model responded in `content`:\n")
    print(content)
elif reasoning_content:
    print("SUCCESS, but note: model responded in `reasoning_content`, not `content`.")
    print("You'll need to read this field in your extraction script too:\n")
    print(reasoning_content)
else:
    print("Call succeeded but no text found in either field. Full raw response:")
    print(response)
