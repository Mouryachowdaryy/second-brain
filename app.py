"""
app.py
Flask server — all HTTP routes for the AI Second Brain application.
"""

from flask import Flask, request, jsonify, render_template
from agent import run_agent
from tools import (
    get_analytics, load_memory,
    add_goal, edit_goal, delete_goal, mark_goal_complete,
    add_task, edit_task, toggle_task, delete_task,
    get_all_goals, get_tasks,
    log_study_hours, update_mood,
)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@app.route("/api/analytics")
def api_analytics():
    return jsonify(get_analytics())


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

@app.route("/api/goals", methods=["GET"])
def api_goals_list():
    return jsonify(get_all_goals())


@app.route("/api/goals", methods=["POST"])
def api_goals_add():
    data = request.get_json()
    title    = (data.get("title") or "").strip()
    deadline = (data.get("deadline") or "").strip()
    if not title or not deadline:
        return jsonify({"error": "title and deadline are required"}), 400
    goal = add_goal(title, deadline)
    return jsonify(goal), 201


@app.route("/api/goals/<int:goal_id>", methods=["PUT"])
def api_goals_edit(goal_id):
    data     = request.get_json()
    title    = data.get("title")
    deadline = data.get("deadline")
    goal = edit_goal(goal_id, title=title, deadline=deadline)
    if goal is None:
        return jsonify({"error": "Goal not found"}), 404
    return jsonify(goal)


@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
def api_goals_delete(goal_id):
    ok = delete_goal(goal_id)
    if not ok:
        return jsonify({"error": "Goal not found"}), 404
    return jsonify({"deleted": goal_id})


@app.route("/api/goals/<int:goal_id>/complete", methods=["POST"])
def api_goals_complete(goal_id):
    goal = mark_goal_complete(goal_id)
    if goal is None:
        return jsonify({"error": "Goal not found"}), 404
    return jsonify(goal)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.route("/api/goals/<int:goal_id>/tasks", methods=["GET"])
def api_tasks_list(goal_id):
    return jsonify(get_tasks(goal_id))


@app.route("/api/goals/<int:goal_id>/tasks", methods=["POST"])
def api_tasks_add(goal_id):
    data = request.get_json()
    text = (data.get("task") or "").strip()
    if not text:
        return jsonify({"error": "task text required"}), 400
    task = add_task(goal_id, text)
    if task is None:
        return jsonify({"error": "Goal not found"}), 404
    return jsonify(task), 201


@app.route("/api/goals/<int:goal_id>/tasks/<int:task_id>", methods=["PUT"])
def api_tasks_edit(goal_id, task_id):
    data = request.get_json()
    text = (data.get("task") or "").strip()
    task = edit_task(goal_id, task_id, text)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/api/goals/<int:goal_id>/tasks/<int:task_id>/toggle", methods=["POST"])
def api_tasks_toggle(goal_id, task_id):
    task = toggle_task(goal_id, task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/api/goals/<int:goal_id>/tasks/<int:task_id>", methods=["DELETE"])
def api_tasks_delete(goal_id, task_id):
    ok = delete_task(goal_id, task_id)
    if not ok:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"deleted": task_id})


# ---------------------------------------------------------------------------
# Study log & mood
# ---------------------------------------------------------------------------

@app.route("/api/log-hours", methods=["POST"])
def api_log_hours():
    data  = request.get_json()
    hours = float(data.get("hours", 1))
    return jsonify(log_study_hours(hours))


@app.route("/api/mood", methods=["POST"])
def api_mood():
    data = request.get_json()
    mood = (data.get("mood") or "neutral").strip()
    return jsonify(update_mood(mood))


# ---------------------------------------------------------------------------
# AI Chat
# ---------------------------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data  = request.get_json()
    msg   = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"error": "message required"}), 400
    result = run_agent(msg)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Raw memory (debug)
# ---------------------------------------------------------------------------

@app.route("/api/memory")
def api_memory():
    return jsonify(load_memory())


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=8000)
