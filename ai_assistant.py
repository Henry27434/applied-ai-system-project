"""
ai_assistant.py - RAG-powered pet care assistant for PawPal+
Uses the owner's actual pet/task data as context before answering.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import anthropic

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="pawpal_ai.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ── Guardrail: topics the assistant will not answer ───────────────────────────
BLOCKED_KEYWORDS = [
    "medication dosage", "prescription", "diagnose", "surgery",
    "vaccine schedule", "euthanize", "breed fighting",
]

SYSTEM_PROMPT = """You are PawPal+, a friendly and knowledgeable pet care assistant.
You help pet owners manage daily care tasks for their pets.

You will be given the owner's current pet and task data as context.
Always use that context to give specific, personalized answers.
If the question is not related to pet care or the owner's schedule, politely decline.
Keep answers concise and practical.
At the end of every response, add a confidence score like: [Confidence: 0.0-1.0]"""


def build_context(owner) -> str:
    """Convert the owner's current pet/task data into a readable context string."""
    if owner is None:
        return "No owner profile found."

    lines = [f"Owner: {owner.name}, daily time budget: {owner.available_minutes} minutes."]
    if not owner.pets:
        lines.append("No pets registered yet.")
    else:
        for pet in owner.pets:
            lines.append(f"\nPet: {pet.name} ({pet.species}, {pet.age_years} yrs)")
            if not pet.tasks:
                lines.append("  No tasks.")
            else:
                for task in pet.tasks:
                    status = "done" if task.completed else "pending"
                    lines.append(
                        f"  - [{status}] {task.time} {task.title} "
                        f"({task.duration_minutes} min, {task.priority} priority, {task.frequency})"
                    )
    return "\n".join(lines)


def check_guardrails(user_input: str) -> Optional[str]:
    """
    Return a refusal message if the query trips a guardrail, else None.
    Blocks medical/harmful topics and empty inputs.
    """
    if not user_input.strip():
        return "Please enter a question."

    lower = user_input.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in lower:
            return (
                "I'm not able to give medical or veterinary advice. "
                "Please consult a licensed vet for that question."
            )

    if len(user_input) > 1000:
        return "Your message is too long. Please keep questions under 1000 characters."

    return None


def extract_confidence(response_text: str) -> float:
    """Parse the confidence score the model appended to its response."""
    try:
        if "[Confidence:" in response_text:
            score_str = response_text.split("[Confidence:")[-1].strip().rstrip("]").strip()
            return float(score_str)
    except (ValueError, IndexError):
        pass
    return 0.5


def ask_assistant(user_input: str, owner, chat_history: list) -> dict:
    """
    Main entry point. Runs guardrails → builds RAG context → calls Claude → logs result.

    Returns a dict with:
      - response (str): the assistant's reply
      - confidence (float): extracted confidence score
      - blocked (bool): whether a guardrail was triggered
      - error (str | None): error message if the API call failed
    """
    # 1. Guardrails
    refusal = check_guardrails(user_input)
    if refusal:
        logging.warning(f"BLOCKED | query='{user_input[:80]}' | reason='{refusal}'")
        return {"response": refusal, "confidence": 0.0, "blocked": True, "error": None}

    # 2. Build RAG context from live pet/task data
    context = build_context(owner)

    # 3. Build message history for multi-turn conversation
    messages = []
    for turn in chat_history:
        messages.append({"role": "user",      "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})

    # Add the current user message with context injected
    messages.append({
        "role": "user",
        "content": (
            f"[Current pet/task data]\n{context}\n\n"
            f"[User question]\n{user_input}"
        ),
    })

    # 4. Call the Anthropic API
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        response_text = message.content[0].text
        confidence = extract_confidence(response_text)

        logging.info(
            f"OK | query='{user_input[:80]}' | confidence={confidence} | "
            f"tokens={message.usage.input_tokens}+{message.usage.output_tokens}"
        )

        return {
            "response": response_text,
            "confidence": confidence,
            "blocked": False,
            "error": None,
        }

    except Exception as e:
        error_msg = f"API error: {str(e)}"
        logging.error(f"ERROR | query='{user_input[:80]}' | error='{error_msg}'")
        return {
            "response": "Sorry, I couldn't reach the AI service. Please try again.",
            "confidence": 0.0,
            "blocked": False,
            "error": error_msg,
        }