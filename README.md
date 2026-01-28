🦎 Critter Tracker
A sleek, dark-themed management system for reptile enthusiasts.

Critter Tracker is a full-stack web application designed to help keepers track their reptiles, feeding schedules, and tasks.

✨ Features
User Authentication: Secure Login and Registration system with duplicate username protection.

Reptile Dashboard: A centralized view of your collection using a clean "Card" based layout.

Automated Task Tracking: Keep track of feedings and maintenance with a database-driven backend.

Custom Dark Mode UI: A bespoke CSS framework focusing on readability, spacing, and a "premium" feel.

Responsive Design: Optimized for different screen sizes using CSS Flexbox and min/max width methodologies.

🛠️ Tech Stack
Backend: Python (Flask)

Database: SQLite with SQLAlchemy ORM

Frontend: HTML5, CSS3 (Custom Flexbox Grid)

Version Control: Git

🚀 Getting Started
Prerequisites
Python 3.x

Pip (Python package manager)

Installation
Clone the repository:

Bash
git clone https://github.com/yourusername/reptile-tasks.git
cd reptile-tasks
Set up a virtual environment:

Bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
Install dependencies:

Bash
pip install flask flask_sqlalchemy flask_login werkzeug
Run the application:

Bash
python app.py
View in Browser: Navigate to http://127.0.0.1:5000

🎨 UI/UX Philosophy
This project avoids heavy CSS frameworks like Bootstrap in favor of custom, lightweight CSS. This allows for:

Precise control over "pixel-perfect" spacing.

A unique brand identity (Teal/Navy/Slate).

Fast load times and clean code hierarchy.
