# AI Second Brain — Professional Productivity Agent

A full-featured AI productivity application with five sections:
Dashboard, Goals Manager, Task Manager, Analytics, and AI Agent Chat.

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set Grok API key (optional — smart mock mode works without it)
export GROK_API_KEY=your_key_here      # Linux / Mac
set GROK_API_KEY=your_key_here         # Windows

# 3. Run
python app.py

# 4. Open browser
http://localhost:5000
```

---

## Application Sections

| Section     | What you can do |
|-------------|----------------|
| Dashboard   | View stats, goal progress, study chart, log hours, set mood |
| Goals       | Add, edit, delete, mark complete — full goal management |
| Tasks       | Select goal, add/edit/delete/toggle tasks per goal |
| Analytics   | 7-day study bar chart, per-goal progress breakdown |
| Agent Chat  | AI-powered conversation — plans, quizzes, reflections |

---

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET    | /api/analytics | Full analytics payload |
| GET    | /api/goals | All goals |
| POST   | /api/goals | Add goal `{title, deadline}` |
| PUT    | /api/goals/:id | Edit goal `{title?, deadline?}` |
| DELETE | /api/goals/:id | Delete goal |
| POST   | /api/goals/:id/complete | Mark goal complete |
| GET    | /api/goals/:id/tasks | Tasks for a goal |
| POST   | /api/goals/:id/tasks | Add task `{task}` |
| PUT    | /api/goals/:id/tasks/:tid | Edit task `{task}` |
| POST   | /api/goals/:id/tasks/:tid/toggle | Toggle task status |
| DELETE | /api/goals/:id/tasks/:tid | Delete task |
| POST   | /api/log-hours | Log hours `{hours}` |
| POST   | /api/mood | Set mood `{mood}` |
| POST   | /api/chat | AI chat `{message}` |

---

## Priority Logic

| Condition | Priority |
|-----------|----------|
| Deadline overdue | OVERDUE |
| Less than 7 days | CRITICAL |
| Less than 15 days | HIGH |
| Less than 30 days or many tasks | MEDIUM |
| Otherwise | LOW |

---

## Notes

- All data persists in `memory.json` — no database required.
- Works fully without an API key using built-in smart mock responses.
- To use real AI: set `GROK_API_KEY` to your Grok API key from [console.x.ai](https://console.x.ai).
- Swap to OpenAI by changing the endpoint URL in `agent.py → call_llm()`.
