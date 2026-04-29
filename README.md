# PawPal+ Applied AI System

PawPal+ is a pet care planning assistant that helps busy pet owners manage daily care tasks for their pets. It uses a RAG-powered AI chat assistant that reads your actual pet and task data before answering questions, so responses are personalized to your specific situation.

---

## Original Project

This project extends PawPal+ from AI110 Module 2. The original app let users add pets and care tasks, generate a priority-aware daily schedule, detect task conflicts, and automate recurring tasks. It was built with Python OOP and a Streamlit UI.

---

## What's New in This Version

The main addition is an AI Assistant tab powered by Claude. When you ask it a question, it first retrieves your current pet and task data and includes it as context before calling the AI. This means it can answer things like "what should I prioritize today?" or "does Mochi have any high priority tasks?" with answers specific to your pets, not generic advice.

Other additions include confidence scoring on every AI response, guardrails that block medical or veterinary advice requests, a log file that records all queries and errors, and 15 new automated tests for the AI layer.

---

## How to Run It

First, make sure you have Python 3.9 or higher installed. Then run these commands:

git clone https://github.com/Henry27434/applied-ai-system-project.git
cd applied-ai-system-project
pip3 install -r requirements.txt

Create a file called .env in the project folder and add your Anthropic API key:
ANTHROPIC_API_KEY=your_key_here

Then start the app:
streamlit run app.py

To run the tests:
python3 -m pytest

---

## Sample Interactions

User: What does Mochi have scheduled today?
AI: Mochi has 3 tasks today. A morning walk at 07:30 (20 min, high priority), flea medication at 08:00 (5 min, high priority), and a fetch session at 16:00 (15 min, low priority). Total time is 40 minutes. [Confidence: 0.95]

User: I only have 30 minutes, what should I prioritize?
AI: With 30 minutes I would focus on the morning walk (20 min) and breakfast feeding (5 min) since both are high priority daily tasks. The enrichment session is low priority and can be skipped today. [Confidence: 0.88]

User: What medication dosage should I give my dog?
AI: I am not able to give medical or veterinary advice. Please consult a licensed vet for that question.

---

## How It Works

When a user submits a question in the AI tab, the system first checks guardrails to block harmful or off-topic requests. If the question passes, it builds a context string from the owner's current pet and task data. That context plus the user's question are sent together to Claude. The response is displayed in the UI along with a confidence score. Everything is logged to pawpal_ai.log.

---

## Design Decisions

The main reason for using RAG is that a generic pet care chatbot would give generic answers. By injecting the owner's real data into every prompt, the AI can give specific, useful responses. Confidence scoring is included because pet care decisions matter and users should know how certain the AI is. The guardrails exist because veterinary medical advice requires a licensed professional and the app should never try to replace that.

One tradeoff in the scheduler is that conflict detection only checks for exact time matches, not overlapping durations. This keeps the logic simple and avoids false positives, but it does miss cases where tasks overlap without sharing the exact same start time.

---

## Testing

Running python3 -m pytest runs all 33 tests. The first 18 cover the core scheduling logic from Module 2, including task completion, recurrence, sorting, filtering, and conflict detection. The 15 new tests cover the AI layer, including context building, guardrail triggering, confidence score parsing, successful API responses, and graceful handling of API failures.

All 33 tests pass. Confidence scores from the AI average around 0.85 to 0.95 for schedule-related questions and drop below 0.7 for vague or ambiguous queries.

---

## Reflection and Ethics

The main limitation is that the AI's knowledge of pet care is only as good as its training data. For unusual species or rare conditions, answers may be incomplete or wrong. Confidence scores are self-reported by the model, not externally validated, so a high score does not guarantee a correct answer.

One thing that surprised me during testing is that the model sometimes reported high confidence for questions it clearly could not answer well, like predicting how a pet would behave. This showed that confidence scores reflect the model's self-assessment, not ground truth, and users should treat them as a rough guide rather than a guarantee.

On AI collaboration, one helpful suggestion was how to structure multi-turn conversation history for the Anthropic API, which worked correctly on the first try. One flawed suggestion was to serialize the Owner object to JSON on every Streamlit rerun to persist it, which was unnecessary since Streamlit's session state already stores Python objects directly. That suggestion was rejected in favor of the simpler approach.