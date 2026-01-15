from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import time
from datetime import date, datetime, timedelta


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///reptiles.db"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
REPTILES_FILE = os.path.join(BASE_DIR, "reptiles.json")

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Animal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    species = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Feeding frequency to days mapping
FREQ_TO_DAYS = {
    "daily": 1,
    "every_other_day": 2,
    "every_3_days": 3,
    "weekly": 7,
    "biweekly": 14,
    "monthly": 30,  
}

def feed_status(next_date_str):
    try:
        d = datetime.strptime(next_date_str, "%Y-%m-%d").date()
    except:
        return "good"

    today = date.today()
    if d < today:
        return "overdue"
    elif (d - today).days <= 2:
        return "soon"
    else:
        return "good"


def parse_yyyy_mm_dd(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None

def calc_next_feed_date(last_fed_str: str, frequency: str) -> str:
    last = parse_yyyy_mm_dd(last_fed_str)
    days = FREQ_TO_DAYS.get((frequency or "").strip())
    if not last or not days:
        return ""
    return (last + timedelta(days=days)).strftime("%Y-%m-%d")


#  JSON helpers
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



# tasks
@app.get("/tasks")
def get_tasks():
    return jsonify(load_json(TASKS_FILE))


@app.get("/tasks/<int:task_id>")
def get_task(task_id):
    tasks = load_json(TASKS_FILE)
    task = next((t for t in tasks if t["id"] == task_id), None)
    return jsonify(task or {"error": "Task not found"}), (200 if task else 404)


@app.post("/tasks")
@login_required
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
@login_required
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
@login_required
def delete_task(task_id):
    tasks = load_json(TASKS_FILE)
    new_tasks = [t for t in tasks if t["id"] != task_id]

    if len(tasks) == len(new_tasks):
        return jsonify({"error": "Task not found"}), 404

    save_json(TASKS_FILE, new_tasks)
    return "", 204


# reptiles, could expand to all pets/insects 
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
@login_required
def get_reptiles():
    return jsonify(load_json(REPTILES_FILE))


@app.get("/api/reptiles/<int:reptile_id>")
@login_required
def get_reptile(reptile_id):

    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)
    return jsonify(reptile or {"error": "Reptile not found"}), (200 if reptile else 404)


@app.post("/reptiles")
@login_required
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
        "last_fed": data.get("last_fed", "")  #"2026-01-10"
    }

    reptiles.append(reptile)
    save_json(REPTILES_FILE, reptiles)
    return jsonify(reptile), 201


@app.put("/reptiles/<int:reptile_id>")
@login_required
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
@login_required
def delete_reptile(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    new_reptiles = [r for r in reptiles if r["id"] != reptile_id]

    if len(reptiles) == len(new_reptiles):
        return jsonify({"error": "Reptile not found"}), 404

    save_json(REPTILES_FILE, new_reptiles)
    return "", 204

#helpers for notifications

def parse_date_yyyy_mm_dd(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def frequency_to_interval_days(freq: str):
    """
    Convert a human frequency string into an interval in days.
    You can expand this mapping anytime.
    """
    f = (freq or "").strip().lower().replace("_", " ")


    # common phrases
    if "daily" in f or "every day" in f:
        return 1
    if "twice weekly" in f or "2x weekly" in f or "two times" in f:
        return 3  # ~every 3-4 days
    if "every other day" in f:
        return 2
    if "weekly" in f:
        return 7
    if "biweekly" in f or "every 2 week" in f or "every two week" in f:
        return 14
    if "monthly" in f:
        return 30

    # handle a number like "3 days" / "every 5 days"
    # very lightweight parsing
    for token in f.split():
        if token.isdigit():
            n = int(token)
            if "day" in f:
                return n
            if "week" in f:
                return n * 7

    return None  # unknown




def compute_feed_status(last_fed_str: str, freq_str: str):
    """
    Returns: (status_key, label_text)
    status_key: 'ok', 'due', 'overdue', 'unknown'
    """
    last_fed = parse_date_yyyy_mm_dd(last_fed_str)
    interval = frequency_to_interval_days(freq_str)

    if not last_fed or not interval:
        return "unknown", "Unknown"

    due_date = last_fed + timedelta(days=interval)
    today = date.today()
    days_until = (due_date - today).days

    if days_until < 0:
        return "overdue", f"Overdue ({abs(days_until)}d)"
    if days_until == 0:
        return "due", "Due today"
    if days_until <= 1:
        return "due", "Due soon"
    return "ok", f"OK ({days_until}d)"

#login and log out routes

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            return "Username already exists"

        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("index"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            return render_template("login.html", error="Invalid username or password")


        login_user(user)
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/")
@login_required
def index():
    animals = Animal.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", animals=animals)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_animal():
    if request.method == "POST":
        animal = Animal(
            name=request.form["name"],
            species=request.form["species"],
            description=request.form["description"],
            user_id=current_user.id
        )
        db.session.add(animal)
        db.session.commit()
        return redirect(url_for("index"))

    return render_template("add.html")


@app.route("/animal/<int:animal_id>")
@login_required
def animal_detail(animal_id):
    animal = Animal.query.filter_by(id=animal_id, user_id=current_user.id).first_or_404()
    return render_template("detail.html", animal=animal)



@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# routes to reptile form

@app.get("/reptiles-form")
@login_required
def reptiles_form():
    reptiles = load_json(REPTILES_FILE)

    for r in reptiles:
        freq = ""
        if isinstance(r.get("feeding_schedule"), dict):
            freq = r["feeding_schedule"].get("frequency", "")

        status_key, status_label = compute_feed_status(r.get("last_fed", ""), freq)
        r["feed_status_key"] = status_key
        r["feed_status_label"] = status_label
        

    return render_template("reptiles_form.html", reptiles=reptiles)

#delete reptile route for ui
@app.post("/reptiles/<int:reptile_id>/delete")
@login_required
def delete_reptile_ui(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    new_reptiles = [r for r in reptiles if r.get("id") != reptile_id]

    # If not found, just go back to list
    if len(new_reptiles) == len(reptiles):
        return redirect(url_for("reptiles_form"))

    save_json(REPTILES_FILE, new_reptiles)
    return redirect(url_for("reptiles_form"))


# POST route to handle reptile form submission
@app.post("/reptiles-form")
@login_required
def reptiles_form_post():
    reptiles = load_json(REPTILES_FILE)
    


    name = request.form.get("name", "").strip()
    species = request.form.get("species", "").strip()

    if not name or not species:
        return redirect(url_for("reptiles_form"))

    weight_raw = request.form.get("weight_grams", "").strip()
    try:
        weight_grams = float(weight_raw) if weight_raw else None
    except ValueError:
        weight_grams = None

    last_fed = request.form.get("last_fed", "").strip()
    freq = request.form.get("feed_frequency", "").strip()

    reptile = {
        "id": new_id(),
        "user_id": current_user.id,
        "name": name,
        "species": species,
        "image_url": request.form.get("image_url", "").strip(),
        "appearance": request.form.get("appearance", "").strip(),
        "diet": request.form.get("diet", "").strip(),
        "weight_grams": weight_grams,
        "feeding_schedule": {
            "frequency": freq,
            "time_of_day": request.form.get("feed_time", "").strip(),
            "notes": request.form.get("feed_notes", "").strip(),
            "next_feed_date": calc_next_feed_date(last_fed, freq),  # ✅ add this
        },
        "last_fed": last_fed,
    }

    reptiles.append(reptile)
    save_json(REPTILES_FILE, reptiles)

    return redirect(url_for("reptile_view", reptile_id=reptile["id"]))


# reptile detail view route
@app.get("/reptiles/<int:reptile_id>")
@login_required
def reptile_view(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)

    if not reptile:
        return "Reptile not found", 404

    # ensure feeding_schedule exists
    reptile.setdefault("feeding_schedule", {})

    # compute next_feed_date if missing/blank (helps older reptiles)
    if not reptile["feeding_schedule"].get("next_feed_date"):
        last_fed = reptile.get("last_fed", "")
        freq = reptile["feeding_schedule"].get("frequency", "")
        reptile["feeding_schedule"]["next_feed_date"] = calc_next_feed_date(last_fed, freq)
        save_json(REPTILES_FILE, reptiles)  # keeps it saved

    # 🔹 calculate feed status
    reptile["feed_status"] = feed_status(
        reptile["feeding_schedule"].get("next_feed_date", "")
    )

    return render_template("reptile_view.html", reptile=reptile)


@app.get("/reptiles-ui")
def reptiles_ui():
    return render_template("reptiles.html")

#home page redirect to reptiles ui
# @app.get("/")
# def home():
#     return redirect(url_for("reptiles_ui"))



# adding 2 routes to app.py

@app.get("/reptiles/<int:reptile_id>/edit")
@login_required
def edit_reptile_form(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)
    if not reptile:
        return "Reptile not found", 404
    return render_template("reptile_edit.html", reptile=reptile)


@app.post("/reptiles/<int:reptile_id>/edit")
@login_required
def edit_reptile_post(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)
    if not reptile:
        return "Reptile not found", 404

    # Pull fields from reptile form
    reptile["name"] = request.form.get("name", reptile.get("name", "")).strip()
    reptile["species"] = request.form.get("species", reptile.get("species", "")).strip()
    reptile["appearance"] = request.form.get("appearance", reptile.get("appearance", "")).strip()
    reptile["diet"] = request.form.get("diet", reptile.get("diet", "")).strip()
    reptile["image_url"] = request.form.get("image_url", reptile.get("image_url", "")).strip()
    reptile["last_fed"] = request.form.get("last_fed", reptile.get("last_fed", "")).strip()

    weight_raw = request.form.get("weight_grams", "").strip()
    try:
        reptile["weight_grams"] = float(weight_raw) if weight_raw else None
    except ValueError:
        pass  # keep old weight if invalid input

    # Feeding schedule (ensure dict exists) + update fields FIRST
    reptile.setdefault("feeding_schedule", {})
    reptile["feeding_schedule"]["frequency"] = request.form.get("feed_frequency", "").strip()
    reptile["feeding_schedule"]["time_of_day"] = request.form.get("feed_time", "").strip()
    reptile["feeding_schedule"]["notes"] = request.form.get("feed_notes", "").strip()

    #  calculate next feed date using the UPDATED frequency + last_fed
    reptile["feeding_schedule"]["next_feed_date"] = calc_next_feed_date(
        reptile.get("last_fed", ""),
        reptile["feeding_schedule"].get("frequency", "")
    )

    save_json(REPTILES_FILE, reptiles)
    return redirect(url_for("reptile_view", reptile_id=reptile_id))


# food log POST route to save feeding entry
@app.post("/reptiles/<int:reptile_id>/feedings")
@login_required
def add_feeding(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)
    if not reptile:
        return "Reptile not found", 404

    feed_date = request.form.get("date", "").strip()
    food = request.form.get("food", "").strip()
    amount = request.form.get("amount", "").strip()
    notes = request.form.get("notes", "").strip()

    # Basic validation (date + food required)
    if not feed_date or not food:
        return redirect(url_for("reptile_view", reptile_id=reptile_id))

    reptile.setdefault("feeding_log", [])
    reptile["feeding_log"].append({
        "id": new_id(),
        "date": feed_date,
        "food": food,
        "amount": amount,
        "notes": notes
    })

    # keep last_fed in sync automatically
    reptile["last_fed"] = feed_date

    save_json(REPTILES_FILE, reptiles)
    return redirect(url_for("reptile_view", reptile_id=reptile_id))

#debug reptile view
@app.get("/debug/reptile-view/<int:reptile_id>")
@login_required
def debug_reptile_view(reptile_id):
    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)
    if not reptile:
        return "Reptile not found", 404

    html = render_template("reptile_view.html", reptile=reptile)
    # show first 2000 chars so i can confirm the feeding form exists in the HTML
    return "<pre>" + html.replace("<", "&lt;").replace(">", "&gt;")[:2000] + "</pre>"

#delete feeding entry

@app.post("/reptiles/<int:reptile_id>/feedings/<int:feeding_id>/delete")
@login_required
def delete_feeding(reptile_id, feeding_id):
    reptiles = load_json(REPTILES_FILE)
    reptile = next((r for r in reptiles if r["id"] == reptile_id), None)
    if not reptile:
        return "Reptile not found", 404

    reptile.setdefault("feeding_log", [])
    before = len(reptile["feeding_log"])
    reptile["feeding_log"] = [e for e in reptile["feeding_log"] if e.get("id") != feeding_id]

    # If nothing changed, entry wasn't found
    if len(reptile["feeding_log"]) == before:
        return redirect(url_for("reptile_view", reptile_id=reptile_id))

    # keep last_fed synced to the newest remaining entry
    if reptile["feeding_log"]:
        # find max date string 
        newest = max((e.get("date", "") for e in reptile["feeding_log"]), default="")
        reptile["last_fed"] = newest
    else:
        reptile["last_fed"] = ""

    save_json(REPTILES_FILE, reptiles)
    return redirect(url_for("reptile_view", reptile_id=reptile_id))


#run once then comment out
with app.app_context():
    db.create_all()


#last line only
if __name__ == "__main__":
    app.run(debug=True)
    
    


