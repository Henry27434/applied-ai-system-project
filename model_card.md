# Model Card: PawPal+ AI Assistant

## What model is being used

PawPal+ uses Claude (claude-haiku-4-5-20251001) by Anthropic, accessed through the Anthropic API.

---

## What it is for

It helps pet owners get personalized answers about their pets and daily care schedule. It is not meant to replace a veterinarian or give medical advice.

---

## How the AI feature works

Every time a user asks a question, the system first pulls their current pet and task data and includes it in the prompt before calling Claude. This is called RAG (Retrieval-Augmented Generation). Instead of giving generic pet care advice, the AI answers based on the user's actual pets and schedule.

---

## Guardrails

The system blocks questions about medication dosages, diagnoses, prescriptions, and surgery. When a blocked question is detected, the user gets a message telling them to see a vet instead. Inputs over 1000 characters are also rejected. Every query and its result is saved to a log file called pawpal_ai.log.

---

## Confidence scoring

Every response includes a confidence score from 0.0 to 1.0 that the model appends itself. The UI shows it color coded: green means high confidence, orange means medium, red means low. It is a self-reported score, not externally verified, so it should be treated as a rough signal rather than a guarantee.

---

## Limitations

The model does not know about rare species or very recent veterinary research. Confidence scores can be misleading since the model sometimes rates itself highly on questions it cannot fully answer. The guardrail uses keyword matching, so a cleverly rephrased medical question might slip through. The system also has no memory between sessions, so users start fresh each time.

---

## Potential misuse

Someone could try rephrasing medical questions to avoid the keyword guardrail. A more robust system would use a classifier instead of keyword matching. The log file also stores all queries locally, so in a shared environment it would need to be secured.

---

## Testing results

15 automated tests cover the AI layer: context building, guardrail blocking, confidence score parsing, successful API responses, and graceful handling of API failures. All 15 pass. In manual testing, confidence scores averaged around 0.90 for specific schedule questions and dropped to around 0.65 for vague questions. The guardrail correctly blocked every medical query tested.

---

## AI collaboration reflection

The most useful part of working with AI on this project was using it to think through edge cases, like what happens when a user has no pets yet or when the API goes down. It also saved time explaining unfamiliar APIs like how to structure multi-turn message history.

The most important lesson was that AI suggestions always need review. I accepted a suggestion early on to serialize the Owner object to JSON on every Streamlit rerun, which was unnecessary and would have caused bugs. The AI also confidently gave a model name that turned out to be wrong and returned a 404 error. These moments reinforced that the engineer needs to stay in the decision-making role.

This project shows that I can design a modular system, identify where AI adds value versus where it adds risk, build in guardrails and logging for responsible use, and verify behavior through automated tests.