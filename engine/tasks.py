# tasks.py (converted for Application API)

from storage import database as db

# 🔍 Show user their active tasks
def get_user_tasks(user_id):
    tasks = db.get_tasks(user_id)
    if not tasks:
        return "📭 You have no active tasks."
    
    return "🧾 Your Tasks:\n" + "\n".join(
        f"• {t.get('description', '[No description]')}" for t in tasks
    )

# ✅ Submit a task by code
def submit_task(user_id, code):
    tasks = db.get_tasks(user_id)
    for task in tasks:
        if task.get('code') == code:
            db.complete_task(user_id, task)
            return "✅ Task completed successfully!"
    return "❌ Invalid or expired task code."

# ⚠️ Abandon current task
def abandon_task(user_id):
    success = db.abandon_current_task(user_id)
    return "⚠️ Task abandoned." if success else "❌ You have no task to abandon."

# 🧾 Assign a task to a user with a reward
def assign_task(user_id, description, code):
    tasks = db.get_tasks(user_id) or []

    reward_map = {
        "say_stars": "truth_crystal",
        "guard_3rounds": "shadow_ring",
        "no_vote2": "goat_scroll"
    }

    reward_item = reward_map.get(code, "relic")
    new_task = {
        "description": description,
        "code": code,
        "reward": reward_item
    }

    tasks.append(new_task)
    db.set_tasks(user_id, tasks)  # ✅ Save the updated task list
