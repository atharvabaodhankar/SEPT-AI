from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    # 🎮 GAMIFICATION
    points = db.Column(db.Integer, default=0)
    level = db.Column(db.String(50), default="Beginner")
    streak = db.Column(db.Integer, default=0)
    last_active = db.Column(db.Date)
    preferred_language = db.Column(db.String(20), nullable=True)
    is_first_login = db.Column(db.Boolean, default=True)

    # ✅ CASCADE RELATIONSHIPS
    quiz_results = db.relationship("QuizResult", cascade="all, delete-orphan", backref="user")
    progress_records = db.relationship("Progress", cascade="all, delete-orphan", backref="user")
    submissions = db.relationship("Submission", cascade="all, delete-orphan", backref="student")
    quiz_attempts = db.relationship("QuizAttempt", cascade="all, delete-orphan", backref="user")
    notifications = db.relationship("Notification", cascade="all, delete-orphan", backref="user")
    attendance_records = db.relationship("Attendance", cascade="all, delete-orphan", backref="user")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(120), unique=True, nullable=False)

class Quiz(db.Model):
    __tablename__ = "quiz"
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(120), nullable=False)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)

class QuizResult(db.Model):
    __tablename__ = "quiz_result"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    course = db.Column(db.String(120), nullable=True)
    score = db.Column(db.Float, default=0.0)
    attempts = db.Column(db.Integer, default=0)

class Progress(db.Model):
    __tablename__ = "progress"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    progress_percent = db.Column(db.Float, default=0.0)

class StudyMaterial(db.Model):
    __tablename__ = "study_material"
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String(120), index=True, nullable=False)
    level = db.Column(db.String(50), nullable=True)    # Beginner / Medium / Advanced
    title = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(500), nullable=False)
    material_type = db.Column(db.String(50), nullable=False, default="video")  
    # allowed values: video, notes, pdf, article, website

class CodingChallenge(db.Model):
    __tablename__ = 'coding_challenges'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    input_format = db.Column(db.Text, nullable=True)
    output_format = db.Column(db.Text, nullable=True)
    sample_input = db.Column(db.Text, nullable=True)
    sample_output = db.Column(db.Text, nullable=True)
    expected_output = db.Column(db.Text, nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(50), nullable=True)

class Submission(db.Model):
    __tablename__ = "submission"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("coding_challenges.id"), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), nullable=False)
    output = db.Column(db.Text)
    score = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class SimpleTeamChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class SimpleDiscussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text)
    username = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seen = db.Column(db.Boolean, default=False)

class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Present/Absent/Late/Leave
    note = db.Column(db.String(255))

class LeaderboardCache(db.Model):
    __tablename__ = "leaderboard_cache"
    id = db.Column(db.Integer, primary_key=True)
    payload_json = db.Column(db.Text)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

class RecommendedResource(db.Model):
    __tablename__ = 'recommended_resources'
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    link = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # video, notes, article

class Practical(db.Model):
    __tablename__ = "practicals"

    id = db.Column(db.Integer, primary_key=True)
    practical_no = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(50), nullable=False)  # no default
    title = db.Column(db.String(255), nullable=False)
    co = db.Column(db.String(50))
    llo = db.Column(db.Text)
    task = db.Column(db.Text)


class PracticalSubmission(db.Model):
    __tablename__ = 'practical_submissions'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    practical_id = db.Column(db.Integer, db.ForeignKey("practicals.id", ondelete="CASCADE"), nullable=False)
    code = db.Column(db.Text)
    output = db.Column(db.Text)
    marks = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='Submitted')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
