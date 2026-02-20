"""
agent.py
Intent detection, tool routing, LLM prompt construction.
Using Groq API (api.groq.com) — key starts with gsk_
"""
from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
import requests
from datetime import date, datetime
from tools import (
    get_agent_context, calculate_priority, load_memory,
    log_study_hours, update_mood, add_goal, add_task,
    get_all_goals, mark_goal_complete
)


# ---------------------------------------------------------------------------
# LLM call — Groq API
# ---------------------------------------------------------------------------

def call_llm(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()

    print(f"[DEBUG] GROQ_API_KEY loaded: {'YES - ' + api_key[:10] + '...' if api_key else 'NO - EMPTY'}")

    if not api_key:
        print("[DEBUG] No API key found — using mock response.")
        return _mock_response(prompt)

    # Groq model options in order of preference
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    for model in models:
        try:
            print(f"[DEBUG] Trying model: {model}")

            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 900,
                    "temperature": 0.7
                },
                timeout=30
            )

            print(f"[DEBUG] Status: {resp.status_code}")
            print(f"[DEBUG] Body: {resp.text[:400]}")

            data = resp.json()

            if resp.status_code == 401:
                return (
                    "PLAN: Authentication failed.\n"
                    "REASON: Groq rejected the API key (401 Unauthorized).\n"
                    "ACTION: Check your .env file.\n"
                    "FINAL ANSWER: Invalid API key. Make sure your .env has: GROQ_API_KEY=gsk_xxxx"
                )

            if resp.status_code == 429:
                return (
                    "PLAN: Rate limit reached.\n"
                    "REASON: Too many requests sent to Groq API.\n"
                    "ACTION: Wait and retry.\n"
                    "FINAL ANSWER: Rate limit hit. Wait 30 seconds and try again."
                )

            if resp.status_code == 404 or (isinstance(data, dict) and "model" in str(data.get("error", ""))):
                print(f"[DEBUG] Model '{model}' not found — trying next.")
                continue

            if "error" in data:
                err = data["error"] if isinstance(data["error"], str) else data["error"].get("message", str(data["error"]))
                print(f"[DEBUG] API error: {err}")
                # If it's a model error, try next model
                if "model" in err.lower():
                    continue
                return (
                    f"PLAN: Groq API returned an error.\n"
                    f"REASON: {err}\n"
                    f"ACTION: Check your API key at console.groq.com.\n"
                    f"FINAL ANSWER: Groq error — {err}"
                )

            if "choices" not in data:
                print(f"[DEBUG] No choices in response: {data}")
                continue

            return data["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout:
            print("[DEBUG] Request timed out.")
            return (
                "PLAN: Request timed out.\n"
                "REASON: Groq API did not respond within 30 seconds.\n"
                "ACTION: Check internet connection and try again.\n"
                "FINAL ANSWER: Connection timed out. Please try again."
            )

        except requests.exceptions.ConnectionError as e:
            print(f"[DEBUG] Connection error: {e}")
            return (
                "PLAN: Cannot connect to Groq API.\n"
                f"REASON: {e}\n"
                "ACTION: Check your internet connection.\n"
                "FINAL ANSWER: Cannot reach api.groq.com — check your internet connection."
            )

        except Exception as e:
            print(f"[DEBUG] Unexpected error on model {model}: {e}")
            continue

    print("[DEBUG] All models failed — using mock response.")
    return _mock_response(prompt)


# ---------------------------------------------------------------------------
# Mock responses (fallback when API unavailable)
# ---------------------------------------------------------------------------

def _mock_response(prompt: str) -> str:
    p = prompt.lower()
    if "quiz" in p:
        return (
            "PLAN: Generate a targeted knowledge quiz based on goal topics.\n"
            "REASON: Active recall is the highest-leverage study method.\n"
            "ACTION: Produce five multiple-choice questions.\n"
            "FINAL ANSWER:\n\n"
            "Knowledge Check\n\n"
            "1. What is the time complexity of quicksort (average case)?\n"
            "   A) O(n)   B) O(n log n)   C) O(n squared)   D) O(log n)\n\n"
            "2. What does the bias-variance tradeoff describe?\n"
            "   A) Speed vs accuracy   B) Model complexity vs generalization   C) Data size vs epochs   D) None\n\n"
            "3. What does gradient descent minimize?\n"
            "   A) Accuracy   B) Loss function   C) Weights   D) Learning rate\n\n"
            "4. Which data structure does BFS use?\n"
            "   A) Stack   B) Heap   C) Queue   D) Tree\n\n"
            "5. What is regularization?\n"
            "   A) Normalizing data   B) Penalizing complexity to reduce overfitting   C) Increasing epochs   D) Feature scaling\n\n"
            "Answers: 1-B, 2-B, 3-B, 4-C, 5-B"
        )
    elif "week" in p or "plan" in p:
        return (
            "PLAN: Build a structured 7-day study schedule.\n"
            "REASON: Even distribution prevents cramming.\n"
            "ACTION: Assign tasks to each day.\n"
            "FINAL ANSWER:\n\n"
            "7-Day Study Plan\n\n"
            "Monday    — Core theory review, 2 hours\n"
            "Tuesday   — Problem set A, 2 hours\n"
            "Wednesday — Video lecture + notes, 1.5 hours\n"
            "Thursday  — Problem set B, 2 hours\n"
            "Friday    — Mock test, 1 hour\n"
            "Saturday  — Weak area revision, 2 hours\n"
            "Sunday    — Light review + next week prep, 1 hour\n\n"
            "Total: 11.5 hours. Consistency compounds."
        )
    elif "reflect" in p:
        return (
            "PLAN: Summarize week and extract insights.\n"
            "REASON: Reflection closes the feedback loop.\n"
            "ACTION: Evaluate logs and suggest corrections.\n"
            "FINAL ANSWER:\n\n"
            "Weekly Reflection\n\n"
            "Consistent effort this week. Streak is holding.\n\n"
            "What worked: Showing up daily.\n"
            "What to improve: Front-load hard tasks earlier in the week.\n"
            "Next priority: Tackle the highest-priority pending tasks first."
        )
    elif "focus" in p or "suggest" in p or "should i" in p:
        return (
            "PLAN: Compare goals by deadline and pending work.\n"
            "REASON: Every session must target the highest-leverage work.\n"
            "ACTION: Recommend the best starting point.\n"
            "FINAL ANSWER:\n\n"
            "Focus Recommendation\n\n"
            "Prioritize your most time-sensitive goal first.\n\n"
            "Start with a single focused 50-minute session on one pending task.\n"
            "Log hours afterward to protect your streak."
        )
    elif "tired" in p or "rest" in p:
        return (
            "PLAN: Reduce workload to match energy level.\n"
            "REASON: Fatigue produces low-quality work.\n"
            "ACTION: Suggest lighter tasks.\n"
            "FINAL ANSWER:\n\n"
            "Low-Energy Plan\n\n"
            "Keep it light today. Review existing notes or watch a short lecture.\n"
            "Even 30 minutes of intentional review protects your streak.\n"
            "Rest is part of the process."
        )
    else:
        return (
            "PLAN: Process query using full goal context.\n"
            "REASON: Context-aware responses produce better outcomes.\n"
            "ACTION: Deliver a targeted recommendation.\n"
            "FINAL ANSWER:\n\n"
            "Focus on your most urgent pending task first.\n"
            "Work in 50-minute blocks with deliberate breaks.\n"
            "Log study hours after each session to maintain your streak.\n\n"
            "Precision and consistency beat intensity."
        )


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

def detect_intent(text: str) -> str:
    t = text.lower()
    if re.search(r"add.*(goal|target)|new goal", t):              return "add_goal"
    if re.search(r"add.*(task|todo)", t):                         return "add_task"
    if re.search(r"mark.*done|complete.*task|finish.*task", t):   return "mark_task"
    if re.search(r"\d+\s*(hour|hr)|studied|log.*hour", t):        return "log_hours"
    if re.search(r"feel|mood|i am|i'm", t):                       return "update_mood"
    if re.search(r"quiz|test me|practice question", t):           return "quiz"
    if re.search(r"plan.*week|week.*plan", t):                    return "plan_week"
    if re.search(r"study.*plan|plan.*study", t):                  return "study_plan"
    if re.search(r"reflect|weekly review", t):                    return "reflect"
    if re.search(r"focus|what should|suggest|priority|which goal", t): return "suggest"
    return "chat"


def _parse_hours(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hour|hr|h)", text, re.I)
    return float(m.group(1)) if m else 1.0


def _parse_mood(text: str) -> str:
    for mood in ["tired", "motivated", "stressed", "happy", "focused",
                 "anxious", "energetic", "excited", "bored", "sad"]:
        if mood in text.lower():
            return mood
    return "neutral"


def _find_goal_id(text: str, mem: dict) -> int:
    t = text.lower()
    for g in mem["goals"]:
        for word in g["title"].lower().split():
            if len(word) > 3 and word in t:
                return g["id"]
    best, min_d = None, float("inf")
    for g in mem["goals"]:
        if g["status"] == "active":
            _, days = calculate_priority(g)
            if days < min_d:
                min_d, best = days, g["id"]
    return best or (mem["goals"][0]["id"] if mem["goals"] else 1)


def _parse_task_text(text: str) -> str:
    m = re.search(r"(?:task|todo)[:\s]+(.+)", text, re.I)
    if m:
        return m.group(1).strip()
    cleaned = re.sub(r"add\s+(a\s+)?task(\s+to\s+\w+(\s+\w+)?\s+goal)?:?\s*", "", text, flags=re.I)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Build master LLM prompt
# ---------------------------------------------------------------------------

def _build_prompt(user_input: str, tool_context: dict, ctx: dict) -> str:
    goals_lines = ""
    for g in ctx["goals"]:
        goals_lines += (
            f"\n  [{g['priority']}] {g['title']} | "
            f"{g['days_left']}d left | {g['progress']}% done | "
            f"Pending: {g['pending_tasks']}"
        )

    logs_line = ", ".join(f"{l['date']}: {l['hours']}h" for l in ctx["recent_logs"][-5:])
    ctx_json = f"\nTool result: {json.dumps(tool_context)}" if tool_context else ""

    return f"""You are an AI Productivity Agent embedded in a professional second-brain application.

User: {ctx['name']}
Mood: {ctx['mood']}
Study streak: {ctx['streak']} days

Active Goals:{goals_lines}

Recent study logs: {logs_line}
{ctx_json}

User message: {user_input}

Instructions:
- Think step by step.
- Consider all goals and compare priorities.
- Adapt tone to mood ({ctx['mood']}): if tired, suggest lighter work; if motivated, push harder tasks.
- Be direct and professional. No emojis. No filler phrases.
- Always reference the streak positively.

Respond in this exact format, no deviations:

PLAN:
REASON:
ACTION:
FINAL ANSWER:
"""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_agent(user_input: str) -> dict:
    mem = load_memory()
    intent = detect_intent(user_input)
    tool_result = {}

    if intent == "log_hours":
        hours = _parse_hours(user_input)
        tool_result = log_study_hours(hours)

    elif intent == "update_mood":
        mood = _parse_mood(user_input)
        tool_result = update_mood(mood)

    elif intent == "add_goal":
        tool_result = {"note": "Use the Goals panel to add goals with full details."}

    elif intent == "add_task":
        goal_id = _find_goal_id(user_input, mem)
        task_text = _parse_task_text(user_input)
        if task_text:
            tool_result = add_task(goal_id, task_text) or {}

    ctx = get_agent_context()
    prompt = _build_prompt(user_input, tool_result, ctx)
    response = call_llm(prompt)

    return {
        "response": response,
        "intent": intent,
        "tool_result": tool_result,
    }