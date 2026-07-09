# SEPT AI — Smart Education Progress Tracker

SEPT AI is an all-in-one, AI-powered learning platform that brings students, teachers, and admins together on a single system — combining quizzes, coding practicals, attendance, performance tracking, discussions, and an AI assistant, all in one place.

🔗 **Live Demo:** [https://sept-ai.onrender.com/](https://sept-ai.onrender.com/)

📂 **Repository:** [github.com/Pranaykhendkar45/SEPT-AI](https://github.com/Pranaykhendkar45/SEPT-AI)

---

## ✨ Features

**Student**
- Personalized dashboard with study suggestions
- Topic-wise quizzes and coding practicals
- Coding challenges with a built-in in-browser coding console
- Real-time team chat and class discussions
- Leaderboard to track rank against classmates
- AI Assistant for instant doubt-solving

**Teacher**
- Class overview — total students, class average, practical submissions
- View detailed student profiles and download performance reports
- Review and grade submitted practicals
- Mark and track attendance
- Bulk upload quiz questions via CSV
- Add new coding challenges and study material videos
- Send notifications to students

**Admin**
- Full control over the platform
- Add, update, or delete users, content, and resources
- Manage student and teacher accounts and roles

---

## 🧰 Tech Stack

Backend: Python, Flask
Database: PostgreSQL, SQLAlchemy
Real-time Communication: Flask-SocketIO
AI Assistant: OpenAI API
Authentication: Flask-Login, Werkzeug (password hashing)
Frontend: HTML, CSS, JavaScript
PDF Reports: ReportLab
Deployment: Render (Gunicorn)

---

## 📁 Project Structure

SEPT AI/

├── app.py                # Main Flask application (routes, logic)

├── models.py              # SQLAlchemy database models

├── init_db.py              # Database initialization script

├── seed_data.py             # Script to populate sample data

├── requirements.txt          # Python dependencies

├── Procfile               # Render/Gunicorn start command

├── templates/              # HTML templates (Jinja2)

└── static/                # CSS, JS, theme files

---

## ⚙️ Getting Started (Local Setup)

1. Clone the repository
   git clone https://github.com/Pranaykhendkar45/SEPT-AI.git
   cd SEPT-AI

2. Create a virtual environment & install dependencies
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt

3. Add your environment variables in a .env file (see requirements.txt / app.py for the variables needed)

4. Initialize the database
   python init_db.py
   python seed_data.py

5. Run the app
   python app.py
   Visit http://localhost:5000 in your browser

---

## 🚀 Deployment

The live version is deployed on Render, using Gunicorn as the production server. Environment variables are configured directly in the Render dashboard.

---

## 👥 Authors

Built by Pranay and Pranita.

---

## 📄 License

This project is for educational purposes.
