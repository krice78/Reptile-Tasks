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

# Authentication Logic Setup
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPTILES_FILE = os.path.join(BASE_DIR, "reptiles.json")

# Jason Helpers (load/save)
def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def new_id():
    return int(time.time() * 1000)

# Logic Helpers
FREQ_TO_DAYS = {
    "daily": 1,
    "every_other_day": 2,
    "every_3_days": 3,
    "weekly": 7,
    "biweekly": 14,
    "monthly": 30,  
}

def calc_next_feed_date(last_fed_str, frequency):
    if not last_fed_str or not frequency:
        return ""
    try:
        last = datetime.strptime(last_fed_str, "%Y-%m-%d").date()
        days = FREQ_TO_DAYS.get(frequency.strip().lower())
        if not days: return ""
        return (last + timedelta(days=days)).strftime("%Y-%m-%d")
    except ValueError:
        return ""

def feed_status(next_date_str):
    if not next_date_str: return "unknown"
    try:
        d = datetime.strptime(next_date_str, "%Y-%m-%d").date()
        today = date.today()
        if d < today: return "overdue"
        elif (d - today).days <= 2: return "soon"
        return "good"
    except ValueError:
        return "unknown"
    
def compute_feed_status(last_fed_str, freq_str):
    # Parses dates and determines if feeding is due based on FREQ_TO_DAYS
    last_fed = None
    if last_fed_str:
        try:
            last_fed = datetime.strptime(last_fed_str, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    interval = FREQ_TO_DAYS.get(freq_str.strip().lower())

    if not last_fed or not interval:
        return "unknown", "Unknown"

    due_date = last_fed + timedelta(days=interval)
    today = date.today()
    days_until = (due_date - today).days

    if days_until < 0:
        return "overdue", f"Overdue ({abs(days_until)}d)"
    if days_until <= 1:
        return "due", "Due soon"
    return "ok", f"OK ({days_until}d)"



# Routes Login/Registration
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            login_user(user)
            return redirect(url_for("my_reptiles"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        hashed = generate_password_hash(request.form["password"])
        new_user = User(username=request.form["username"].lower(), password_hash=hashed)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("my_reptiles"))
    return render_template("register.html")

@app.route("/dashboard")
@login_required
def dashboard():
    # Load reptiles exactly as in other routes 
    all_reps = load_json(REPTILES_FILE)
    user_reps = [r for r in all_reps if r.get("user_id") == current_user.id]
    
    notifications = []
    for r in user_reps:
        #  Use existing compute_feed_status helper 
        freq = r.get("feeding_schedule", {}).get("frequency", "")
        last_fed = r.get("last_fed", "")
        status_key, status_label = compute_feed_status(last_fed, freq)
        
        # Only grab the ones that need attention 
        if status_key in ['due', 'overdue']:
            notifications.append({
                "name": r.get("name"),
                "status": status_label,
                "id": r.get("id"),
                "is_overdue": (status_key == 'overdue')
            })
            
    return render_template("dashboard.html", 
                           notifications=notifications, 
                           reptile_count=len(user_reps))

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))

# Routes for Reptiles
@app.get("/my_reptiles")
@login_required
def my_reptiles():
    # Only show reptiles belonging to current user
    all_reps = load_json(REPTILES_FILE)
    user_reps = [r for r in all_reps if r.get("user_id") == current_user.id]
    return render_template("my_reptiles.html", reptiles=user_reps)

@app.post("/my_reptiles")
@login_required
def my_reptiles_post():
    all_reps = load_json(REPTILES_FILE)
    
    last_fed = request.form.get("last_fed", "").strip()
    freq = request.form.get("feed_frequency", "").strip()

    new_rep = {
        "id": new_id(),
        "user_id": current_user.id,
        "name": request.form.get("name"),
        "species": request.form.get("species"),
        "image_url": request.form.get("image_url", ""),
        "appearance": request.form.get("appearance", ""),
        "diet": request.form.get("diet", ""),
        "weight_grams": request.form.get("weight_grams"),
        "last_fed": last_fed,
        "feeding_schedule": {
            "frequency": freq,
            "time_of_day": request.form.get("feed_time", ""),
            "notes": request.form.get("feed_notes", ""),
            "next_feed_date": calc_next_feed_date(last_fed, freq)
        },
        "feeding_log": []
    }
    all_reps.append(new_rep)
    save_json(REPTILES_FILE, all_reps)
    return redirect(url_for("reptile_view", reptile_id=new_rep["id"]))

@app.post("/reptiles/<int:reptile_id>/edit")
@login_required
def edit_reptile_post(reptile_id):
    # Load ALL to prevent data loss for other users
    all_reps = load_json(REPTILES_FILE)
    
    # Find the specific reptile belonging to this user
    reptile = next((r for r in all_reps if r["id"] == reptile_id and r["user_id"] == current_user.id), None)
    
    if not reptile:
        return "Reptile not found", 404

# Update Basic Info 
    reptile["name"] = request.form.get("name", "").strip()
    reptile["species"] = request.form.get("species", "").strip()
    reptile["image_url"] = request.form.get("image_url", "").strip()
    reptile["appearance"] = request.form.get("appearance", "").strip()
    reptile["diet"] = request.form.get("diet", "").strip()
    reptile["last_fed"] = request.form.get("last_fed", "").strip()
    
    # Update Weight (with safety check) 
    weight_raw = request.form.get("weight_grams", "").strip()
    try:
        reptile["weight_grams"] = float(weight_raw) if weight_raw else 0.0
    except ValueError:
        pass 

    # Update Feeding Schedule & Recalculate Next Date 
    freq = request.form.get("feed_frequency", "").strip()
    reptile["feeding_schedule"] = {
        "frequency": freq,
        "time_of_day": request.form.get("feed_time", "").strip(),
        "notes": request.form.get("feed_notes", "").strip(),
        "next_feed_date": calc_next_feed_date(reptile["last_fed"], freq)
    }

    save_json(REPTILES_FILE, all_reps)
    return redirect(url_for("reptile_view", reptile_id=reptile_id))

@app.get("/reptiles/<int:reptile_id>/feedings/<int:feeding_id>/edit")
@login_required
def edit_feeding_form(reptile_id, feeding_id):
    all_reps = load_json(REPTILES_FILE)
    reptile = next((r for r in all_reps if r["id"] == reptile_id and r["user_id"] == current_user.id), None)
    
    if not reptile:
        return "Reptile not found", 404

    # Find the specific feeding entry in the log
    feeding = next((f for f in reptile.get("feeding_log", []) if f["id"] == feeding_id), None)
    
    if not feeding:
        return "Feeding record not found", 404
        
    return render_template("edit_feeding.html", reptile=reptile, feeding=feeding)

@app.post("/reptiles/<int:reptile_id>/feedings/<int:feeding_id>/edit")
@login_required
def edit_feeding_post(reptile_id, feeding_id):
    all_reps = load_json(REPTILES_FILE)
    reptile = next((r for r in all_reps if r["id"] == reptile_id and r["user_id"] == current_user.id), None)
    
    if reptile:
        # Find and update the specific feeding in the log
        log = reptile.get("feeding_log", [])
        feeding = next((f for f in log if f["id"] == feeding_id), None)
        
        if feeding:
            feeding["date"] = request.form.get("date")
            feeding["food"] = request.form.get("food")
            feeding["amount"] = request.form.get("amount")
            feeding["notes"] = request.form.get("notes")

            # Recalculate the overall 'last_fed' based on the newest date in the log
            if log:
                # This finds the most recent date string in the list
                latest_entry = max(log, key=lambda x: x['date'])
                reptile["last_fed"] = latest_entry["date"]
                
                # Update the schedule so the Dashboard knows when the next one is due
                freq = reptile["feeding_schedule"].get("frequency", "")
                reptile["feeding_schedule"]["next_feed_date"] = calc_next_feed_date(reptile["last_fed"], freq)

        save_json(REPTILES_FILE, all_reps)
        
    return redirect(url_for("reptile_view", reptile_id=reptile_id))

@app.get("/reptiles/<int:reptile_id>")
@login_required
def reptile_view(reptile_id):
    all_reps = load_json(REPTILES_FILE)
    # Security: Ensure it exists AND belongs to the user
    reptile = next((r for r in all_reps if r["id"] == reptile_id and r["user_id"] == current_user.id), None)
    
    if not reptile: return "Reptile not found", 404

    # Update status for the template
    next_f = reptile.get("feeding_schedule", {}).get("next_feed_date", "")
    reptile["feed_status"] = feed_status(next_f)
    
    return render_template("reptile_view.html", reptile=reptile, today_date=date.today().isoformat())

@app.post("/reptiles/<int:reptile_id>/feedings")
@login_required
def add_feeding(reptile_id):
    all_reps = load_json(REPTILES_FILE)
    reptile = next((r for r in all_reps if r["id"] == reptile_id and r["user_id"] == current_user.id), None)
    
    if reptile:
        feed_date = request.form.get("date")
        new_entry = {
            "id": new_id(),
            "date": feed_date,
            "food": request.form.get("food"),
            "amount": request.form.get("amount"),
            "notes": request.form.get("notes")
        }
        reptile.setdefault("feeding_log", []).append(new_entry)
        
        # Sync last_fed and re-calc next date
        reptile["last_fed"] = feed_date
        freq = reptile["feeding_schedule"].get("frequency", "")
        reptile["feeding_schedule"]["next_feed_date"] = calc_next_feed_date(feed_date, freq)
        
        save_json(REPTILES_FILE, all_reps)
        
    return redirect(url_for("reptile_view", reptile_id=reptile_id))

@app.post("/reptiles/<int:reptile_id>/delete")
@login_required
def delete_reptile_ui(reptile_id):
    all_reps = load_json(REPTILES_FILE)
    # Keep only reptiles that aren't the one being deleted (and verify ownership)
    filtered_reps = [r for r in all_reps if not (r["id"] == reptile_id and r["user_id"] == current_user.id)]
    save_json(REPTILES_FILE, filtered_reps)
    return redirect(url_for("my_reptiles"))

@app.post("/reptiles/<int:reptile_id>/feedings/<int:feeding_id>/delete")
@login_required
def delete_feeding(reptile_id, feeding_id):
    all_reps = load_json(REPTILES_FILE)
    # Find the reptile belonging to the current user
    reptile = next((r for r in all_reps if r["id"] == reptile_id and r["user_id"] == current_user.id), None)
    
    if reptile:
        # Filter the feeding_log to remove the entry with the matching feeding_id
        old_log = reptile.get("feeding_log", [])
        reptile["feeding_log"] = [entry for entry in old_log if entry.get("id") != feeding_id]
        
        # Save the updated list back to the JSON file
        save_json(REPTILES_FILE, all_reps)
        
    return redirect(url_for("reptile_view", reptile_id=reptile_id))

@app.route("/")
def landing():
    return render_template("landing.html")

@app.get("/reptiles/<int:reptile_id>/edit")
@login_required
def edit_reptile_form(reptile_id):
    all_reps = load_json(REPTILES_FILE)
    # Find the reptile and ensure it belongs to the current user
    reptile = next((r for r in all_reps if r["id"] == reptile_id and r["user_id"] == current_user.id), None)
    
    if not reptile:
        return "Reptile not found", 404
        
    return render_template("reptile_edit.html", reptile=reptile)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)