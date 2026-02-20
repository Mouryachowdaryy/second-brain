"""
tools.py
All data-layer functions. Every function reads/writes memory.json.
"""

import json
from datetime import date, datetime, timedelta

MEMORY_FILE = "memory.json"


# ---------------------------------------------------------------------------
# Core I/O
# ---------------------------------------------------------------------------

def load_memory() -> dict:
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def save_memory(mem: dict) -> None:
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)


def _get_goal(mem: dict, goal_id: int) -> dict | None:
    for g in mem["goals"]:
        if g["id"] == goal_id:
            return g
    return None


# ---------------------------------------------------------------------------
# Priority engine
# ---------------------------------------------------------------------------

def calculate_priority(goal: dict) -> tuple[str, int]:
    """Return (priority_label, days_left)."""
    try:
        deadline = datetime.strptime(goal["deadline"], "%Y-%m-%d").date()
        days_left = (deadline - date.today()).days
        pending = sum(1 for t in goal["tasks"] if t["status"] == "pending")

        if days_left < 0:
            return "OVERDUE", days_left
        elif days_left < 7:
            return "CRITICAL", days_left
        elif days_left < 15:
            return "HIGH", days_left
        elif days_left < 30 or pending > 3:
            return "MEDIUM", days_left
        else:
            return "LOW", days_left
    except Exception:
        return "MEDIUM", 999


def recalc_goal(goal: dict) -> dict:
    """Recalculate progress and priority in-place, return goal."""
    tasks = goal.get("tasks", [])
    if tasks:
        done = sum(1 for t in tasks if t["status"] == "completed")
        goal["progress"] = round((done / len(tasks)) * 100)
    else:
        goal["progress"] = 0

    priority, _ = calculate_priority(goal)
    goal["priority"] = priority
    return goal


# ---------------------------------------------------------------------------
# Goal CRUD
# ---------------------------------------------------------------------------

def get_all_goals() -> list:
    mem = load_memory()
    for g in mem["goals"]:
        recalc_goal(g)
    save_memory(mem)
    return mem["goals"]


def add_goal(title: str, deadline: str) -> dict:
    mem = load_memory()
    new_id = max((g["id"] for g in mem["goals"]), default=0) + 1
    goal = {
        "id": new_id,
        "title": title.strip(),
        "deadline": deadline,
        "priority": "MEDIUM",
        "status": "active",
        "tasks": [],
        "progress": 0
    }
    recalc_goal(goal)
    mem["goals"].append(goal)
    save_memory(mem)
    return goal


def edit_goal(goal_id: int, title: str | None = None, deadline: str | None = None) -> dict | None:
    mem = load_memory()
    goal = _get_goal(mem, goal_id)
    if not goal:
        return None
    if title:
        goal["title"] = title.strip()
    if deadline:
        goal["deadline"] = deadline
    recalc_goal(goal)
    save_memory(mem)
    return goal


def delete_goal(goal_id: int) -> bool:
    mem = load_memory()
    before = len(mem["goals"])
    mem["goals"] = [g for g in mem["goals"] if g["id"] != goal_id]
    save_memory(mem)
    return len(mem["goals"]) < before


def mark_goal_complete(goal_id: int) -> dict | None:
    mem = load_memory()
    goal = _get_goal(mem, goal_id)
    if not goal:
        return None
    goal["status"] = "completed"
    # mark all tasks done
    for t in goal["tasks"]:
        t["status"] = "completed"
    recalc_goal(goal)
    save_memory(mem)
    return goal


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------

def get_tasks(goal_id: int) -> list:
    mem = load_memory()
    goal = _get_goal(mem, goal_id)
    return goal["tasks"] if goal else []


def add_task(goal_id: int, task_text: str) -> dict | None:
    mem = load_memory()
    goal = _get_goal(mem, goal_id)
    if not goal:
        return None
    new_task_id = max((t["id"] for t in goal["tasks"]), default=0) + 1
    task = {"id": new_task_id, "task": task_text.strip(), "status": "pending"}
    goal["tasks"].append(task)
    recalc_goal(goal)
    save_memory(mem)
    return task


def edit_task(goal_id: int, task_id: int, text: str) -> dict | None:
    mem = load_memory()
    goal = _get_goal(mem, goal_id)
    if not goal:
        return None
    for t in goal["tasks"]:
        if t["id"] == task_id:
            t["task"] = text.strip()
            save_memory(mem)
            return t
    return None


def toggle_task(goal_id: int, task_id: int) -> dict | None:
    mem = load_memory()
    goal = _get_goal(mem, goal_id)
    if not goal:
        return None
    for t in goal["tasks"]:
        if t["id"] == task_id:
            t["status"] = "completed" if t["status"] == "pending" else "pending"
            recalc_goal(goal)
            save_memory(mem)
            return t
    return None


def delete_task(goal_id: int, task_id: int) -> bool:
    mem = load_memory()
    goal = _get_goal(mem, goal_id)
    if not goal:
        return False
    before = len(goal["tasks"])
    goal["tasks"] = [t for t in goal["tasks"] if t["id"] != task_id]
    recalc_goal(goal)
    save_memory(mem)
    return len(goal["tasks"]) < before


# ---------------------------------------------------------------------------
# Study log & streak
# ---------------------------------------------------------------------------

def log_study_hours(hours: float) -> dict:
    mem = load_memory()
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    dates_logged = {log["date"] for log in mem["study_logs"]}

    for log in mem["study_logs"]:
        if log["date"] == today:
            log["hours"] += hours
            save_memory(mem)
            return {"date": today, "total_today": log["hours"], "streak": mem["streak"]}

    if yesterday in dates_logged:
        mem["streak"] += 1
    else:
        mem["streak"] = 1

    mem["study_logs"].append({"date": today, "hours": hours})
    save_memory(mem)
    return {"date": today, "hours": hours, "streak": mem["streak"]}


def update_mood(mood: str) -> dict:
    mem = load_memory()
    mem["mood"] = mood.lower().strip()
    save_memory(mem)
    return {"mood": mem["mood"]}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def get_analytics() -> dict:
    mem = load_memory()
    today = date.today()
    week_ago = today - timedelta(days=7)

    week_hours = sum(
        l["hours"] for l in mem["study_logs"]
        if datetime.strptime(l["date"], "%Y-%m-%d").date() >= week_ago
    )
    total_hours = sum(l["hours"] for l in mem["study_logs"])

    goals_data = []
    most_urgent = None
    min_days = float("inf")

    for g in mem["goals"]:
        recalc_goal(g)
        priority, days_left = calculate_priority(g)
        done = sum(1 for t in g["tasks"] if t["status"] == "completed")
        total = len(g["tasks"])
        goals_data.append({
            "id": g["id"],
            "title": g["title"],
            "deadline": g["deadline"],
            "priority": priority,
            "days_left": days_left,
            "progress": g["progress"],
            "status": g["status"],
            "tasks_done": done,
            "total_tasks": total,
        })
        if days_left < min_days and g["status"] == "active":
            min_days = days_left
            most_urgent = g["title"]

    save_memory(mem)

    # Weekly logs for chart
    log_chart = []
    for i in range(6, -1, -1):
        d = str(today - timedelta(days=i))
        hrs = next((l["hours"] for l in mem["study_logs"] if l["date"] == d), 0)
        log_chart.append({"date": d, "hours": hrs})

    return {
        "name": mem["name"],
        "mood": mem["mood"],
        "streak": mem["streak"],
        "week_hours": week_hours,
        "total_hours": total_hours,
        "goals": goals_data,
        "most_urgent": most_urgent,
        "log_chart": log_chart,
        "active_count": sum(1 for g in mem["goals"] if g["status"] == "active"),
        "completed_count": sum(1 for g in mem["goals"] if g["status"] == "completed"),
    }


# ---------------------------------------------------------------------------
# Agent context helpers
# ---------------------------------------------------------------------------

def get_agent_context() -> dict:
    """Return rich context for the LLM prompt."""
    mem = load_memory()
    goals_summary = []
    for g in mem["goals"]:
        recalc_goal(g)
        _, days = calculate_priority(g)
        pending = [t["task"] for t in g["tasks"] if t["status"] == "pending"]
        goals_summary.append({
            "title": g["title"],
            "priority": g["priority"],
            "days_left": days,
            "progress": g["progress"],
            "pending_tasks": pending,
            "status": g["status"],
        })
    save_memory(mem)

    recent_logs = mem["study_logs"][-7:]
    return {
        "name": mem["name"],
        "mood": mem["mood"],
        "streak": mem["streak"],
        "goals": goals_summary,
        "recent_logs": recent_logs,
    }
