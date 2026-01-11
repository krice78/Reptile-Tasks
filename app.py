# from flask import Flask, request, jsonify
# import json
# import os

# app = Flask(__name__)
# DATA_FILE = 'tasks.json'

# # Load tasks from the file
# def load_tasks():
#     if not os.path.exists(DATA_FILE):
#         return []
#     try:
#         with open(DATA_FILE, 'r') as file:
#             return json.load(file)
#     except json.JSONDecodeError:
#         return []

# # Save tasks to the file
# def save_tasks(tasks):
#     with open(DATA_FILE, 'w') as file:
#         json.dump(tasks, file, indent=2)
        
# @app.route('/')
# def home():
#     return 'Welcome to the To-Do API!'

# @app.route('/tasks', methods=['GET'])
# def get_tasks():
#     return jsonify(load_tasks())

# @app.route('/tasks/<int:task_id>', methods=['GET'])
# def get_task(task_id):
#     tasks = load_tasks()
#     task = next((t for t in tasks if t['id'] == task_id), None)
#     return jsonify(task or {'error': 'Task not found'}), 200 if task else 404

# @app.route('/tasks', methods=['POST'])
# def create_task():
#     tasks = load_tasks()
#     data = request.get_json(silent=True) or {}
#     new_task = {
#         'id': int(time.time() * 1000),
#         'title': data.get('title', 'Untitled Task'),
#         'completed': False
#     }
#     tasks.append(new_task)
#     save_tasks(tasks)
#     return jsonify(new_task), 201

# @app.route('/tasks/<int:task_id>', methods=['PUT'])
# def update_task(task_id):
#     tasks = load_tasks()
#     task = next((t for t in tasks if t['id'] == task_id), None)
#     if not task:
#         return jsonify({'error': 'Task not found'}), 404
#     data = request.get_json(silent=True) or {}
#     task['title'] = data.get('title', task['title'])
#     task['completed'] = data.get('completed', task['completed'])
#     save_tasks(tasks)
#     return jsonify(task)

# @app.route('/tasks/<int:task_id>', methods=['DELETE'])
# def delete_task(task_id):
#     tasks = load_tasks()
#     new_tasks = [t for t in tasks if t['id'] != task_id]
    
#     if len(new_tasks) == len(tasks):
#         return jsonify({'error': 'Task not found'}), 404
    
#     save_tasks(tasks)
#     return '', 204

# if __name__ == '__main__':
#     app.run(debug=True)

from flask import Flask, request, jsonify
import json
import os
import time

app = Flask(__name__)

TASKS_FILE = "tasks.json"
REPTILES_FILE = "reptiles.json"


# ---------- Generic JSON helpers ----------
def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def new_id():
    return int(time.time() * 1000)


# ---------- Home ----------
@app.get("/")
def home():
    return "Welcome! Try /tasks or /reptiles"


# ---------- Tasks (your existing API, slightly safer) ----------
@app.get("/tasks")
def get_tasks():
    return jsonify(load_json(TASKS_FILE))


@app.get("/tasks/<int:task_id>")
def get_task(task_id):
    tasks = load_json(TASKS_FILE)
    task = next((t for t in tasks if t["id"] == task_id), None)
    return jsonify(task or {"error": "Task not found"}), (200 if task else 404)


@app.post("/tasks")
def create_task():
    tasks = load_json(TASKS_FILE)
    data = request.get_json(silent=True) or {}

    new_task = {
        "id": new_id(),
        "title": data.get("title", "Untitled Task"),
        "completed": False
    }

    tasks.append(new_task)
    save_json(TASKS_FILE, tasks)
    return jsonify(new_task), 201


@app.put("/tasks/<int:task_id>")
def update_task(task_id):
    tasks = load_json(TASKS_FILE)
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True) or {}
    task["title"] = data.get("title", task["title"])
    task["completed"] = data.get("completed", task["completed"])

    save_json(TASKS_FILE, tasks)
    return jsonify(task)


@app.delete("/tasks/<int:task_id>")
def delete_task(task_id):
    tasks = load_json(TASKS_FILE)
    new_tasks = [t for t in tasks if t["id"] != task_id]

    if len(tasks) == len(new_tasks):
        return jsonify({"error": "Task not found"}), 404

    save_json(TASKS_FILE, new_tasks)
    return "", 204


# ---------- Reptiles ----------
def validate_reptile_payload(data, partial=False):
    """
    partial=False: required for create
    partial=True: allow partial updates
    """
    required = ["name", "species"]
    if not partial:
        missing = [k for k in required if not data.get(k)]
        if missing:
            return False, f"Missing required field(s): {', '.join(missing)}"
    return True, ""


@app.get("/reptiles")
def get_reptiles():
    return jsonify(load_json(REPTILES_FILE))


@app.get("/reptiles/<int:reptile_id>")
def get_reptile(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)
    return jsonify(reptile or {"error": "Reptile not found"}), (200 if reptile else 404)


@app.post("/reptiles")
def create_reptile():
    reptiles = load_json(REPTILES_FILE)
    data = request.get_json(silent=True) or {}

    ok, msg = validate_reptile_payload(data, partial=False)
    if not ok:
        return jsonify({"error": msg}), 400

    reptile = {
        "id": new_id(),
        "name": data.get("name"),
        "species": data.get("species"),
        "appearance": data.get("appearance", ""),
        "diet": data.get("diet", ""),
        "weight_grams": data.get("weight_grams", None),
        "feeding_schedule": data.get("feeding_schedule", {
            "frequency": "",
            "time_of_day": "",
            "notes": ""
        }),
        "last_fed": data.get("last_fed", "")  # e.g. "2026-01-10"
    }

    reptiles.append(reptile)
    save_json(REPTILES_FILE, reptiles)
    return jsonify(reptile), 201


@app.put("/reptiles/<int:reptile_id>")
def update_reptile(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)
    if not reptile:
        return jsonify({"error": "Reptile not found"}), 404

    data = request.get_json(silent=True) or {}
    ok, msg = validate_reptile_payload(data, partial=True)
    if not ok:
        return jsonify({"error": msg}), 400

    # Update only provided fields
    for key in ["name", "species", "appearance", "diet", "weight_grams", "last_fed"]:
        if key in data:
            reptile[key] = data[key]

    if "feeding_schedule" in data and isinstance(data["feeding_schedule"], dict):
        reptile.setdefault("feeding_schedule", {})
        reptile["feeding_schedule"].update(data["feeding_schedule"])

    save_json(REPTILES_FILE, reptiles)
    return jsonify(reptile), 200


@app.delete("/reptiles/<int:reptile_id>")
def delete_reptile(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    new_reptiles = [r for r in reptiles if r["id"] != reptile_id]

    if len(reptiles) == len(new_reptiles):
        return jsonify({"error": "Reptile not found"}), 404

    save_json(REPTILES_FILE, new_reptiles)
    return "", 204


if __name__ == "__main__":
    app.run(debug=True)
