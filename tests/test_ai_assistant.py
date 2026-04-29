"""
tests/test_ai_assistant.py - Reliability tests for the AI assistant layer.
Run with: python3 -m pytest
"""

import pytest
from unittest.mock import patch, MagicMock
from pawpal_system import Task, Pet, Owner
from ai_assistant import (
    build_context,
    check_guardrails,
    extract_confidence,
    ask_assistant,
)


# ── build_context ─────────────────────────────────────────────────────────────

def test_build_context_no_owner():
    assert "No owner profile" in build_context(None)

def test_build_context_no_pets():
    owner = Owner(name="Jordan", available_minutes=120)
    ctx = build_context(owner)
    assert "Jordan" in ctx
    assert "No pets" in ctx

def test_build_context_includes_pet_and_task():
    owner = Owner(name="Jordan", available_minutes=60)
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task(title="Walk", duration_minutes=20, time="08:00", priority="high"))
    owner.add_pet(pet)
    ctx = build_context(owner)
    assert "Mochi" in ctx
    assert "Walk" in ctx
    assert "08:00" in ctx

def test_build_context_completed_task_marked():
    owner = Owner(name="Jordan", available_minutes=60)
    pet = Pet(name="Luna", species="cat")
    t = Task(title="Feed", duration_minutes=5, time="07:00")
    t.completed = True
    pet.add_task(t)
    owner.add_pet(pet)
    ctx = build_context(owner)
    assert "done" in ctx


# ── check_guardrails ──────────────────────────────────────────────────────────

def test_guardrail_empty_input():
    assert check_guardrails("") is not None
    assert check_guardrails("   ") is not None

def test_guardrail_medical_keyword():
    result = check_guardrails("What medication dosage should I give my dog?")
    assert result is not None
    assert "vet" in result.lower()

def test_guardrail_blocked_keyword_diagnose():
    result = check_guardrails("Can you diagnose my cat's illness?")
    assert result is not None

def test_guardrail_safe_question():
    assert check_guardrails("What tasks are scheduled for Mochi today?") is None

def test_guardrail_too_long():
    long_input = "a" * 1001
    result = check_guardrails(long_input)
    assert result is not None
    assert "long" in result.lower()


# ── extract_confidence ────────────────────────────────────────────────────────

def test_extract_confidence_valid():
    text = "Here is my answer. [Confidence: 0.85]"
    assert extract_confidence(text) == pytest.approx(0.85)

def test_extract_confidence_missing():
    text = "Here is my answer with no score."
    assert extract_confidence(text) == 0.5

def test_extract_confidence_zero():
    text = "I'm not sure. [Confidence: 0.0]"
    assert extract_confidence(text) == pytest.approx(0.0)


# ── ask_assistant (mocked API) ────────────────────────────────────────────────

def make_owner():
    owner = Owner(name="Jordan", available_minutes=120)
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task(title="Walk", duration_minutes=20, time="08:00"))
    owner.add_pet(pet)
    return owner

def test_ask_assistant_blocked_query():
    result = ask_assistant("Please diagnose my dog", make_owner(), [])
    assert result["blocked"] is True
    assert result["confidence"] == 0.0

def test_ask_assistant_empty_query():
    result = ask_assistant("", make_owner(), [])
    assert result["blocked"] is True

@patch("ai_assistant.anthropic.Anthropic")
def test_ask_assistant_success(mock_anthropic_class):
    """Successful API call returns a response with confidence parsed."""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Mochi has a walk at 08:00. [Confidence: 0.9]")]
    mock_message.usage.input_tokens = 100
    mock_message.usage.output_tokens = 50
    mock_client.messages.create.return_value = mock_message

    result = ask_assistant("What does Mochi have today?", make_owner(), [])

    assert result["blocked"] is False
    assert result["error"] is None
    assert "Mochi" in result["response"]
    assert result["confidence"] == pytest.approx(0.9)

@patch("ai_assistant.anthropic.Anthropic")
def test_ask_assistant_api_failure(mock_anthropic_class):
    """API errors are caught and returned gracefully."""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("Connection timeout")

    result = ask_assistant("What tasks are due?", make_owner(), [])

    assert result["error"] is not None
    assert result["blocked"] is False
    assert "try again" in result["response"].lower()