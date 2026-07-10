import io, json, csv, os, requests, urllib.parse
from pydoc_data.topics import topics
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, make_response, render_template, request, redirect, send_file, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_login import login_required, current_user, LoginManager
from flask_socketio import SocketIO, emit
from reportlab.pdfgen import canvas
from sqlalchemy import desc, func
from models import (
    Attendance, Feedback, Notification, Practical, PracticalSubmission, SimpleDiscussion, SimpleTeamChat,
    db, User, Quiz, QuizResult, StudyMaterial, CodingChallenge,
    Submission, RecommendedResource
)
from openai import OpenAI

# ----------------------------
# CONFIG
# ----------------------------
load_dotenv()
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Require SECRET_KEY to be set — never fall back to a known string
_secret = os.getenv("SECRET_KEY")
if not _secret:
    raise RuntimeError("SECRET_KEY environment variable must be set")
app.secret_key = _secret

# Require DATABASE_URL to be set — never fall back to a hardcoded password
_db_url = os.getenv("DATABASE_URL")
if not _db_url:
    raise RuntimeError("DATABASE_URL environment variable must be set")
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Secure session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

db.init_app(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))


# ----------------------------
# ONE-TIME DB SETUP (for free-tier hosts with no shell access)
# Visit: https://your-app.onrender.com/setup?key=YOUR_ADMIN_SECRET_KEY
# Safe to call multiple times — skips anything that already exists.
# ----------------------------
@app.route('/setup')
def one_time_setup():
    key = request.args.get('key', '')
    if key != os.getenv("ADMIN_SECRET_KEY"):
        return "Unauthorized. Pass ?key=YOUR_ADMIN_SECRET_KEY", 403

    with app.app_context():
        db.create_all()

        added = {"quiz": 0, "challenges": 0, "practicals": 0}

        quiz_questions = [
            dict(subject="Python", question="What is the output of print(2 ** 3)?",
                 option_a="5", option_b="6", option_c="8", option_d="9", correct_option="C"),
            dict(subject="Python", question="Which keyword is used to define a function in Python?",
                 option_a="func", option_b="def", option_c="function", option_d="lambda", correct_option="B"),
            dict(subject="Python", question="Which data type is immutable in Python?",
                 option_a="list", option_b="dict", option_c="set", option_d="tuple", correct_option="D"),
            dict(subject="Python", question="What does len() return for a string?",
                 option_a="Number of characters", option_b="Memory size", option_c="ASCII value", option_d="None",
                 correct_option="A"),
            dict(subject="Python", question="Which symbol is used for comments in Python?",
                 option_a="//", option_b="#", option_c="/*", option_d="--", correct_option="B"),
            dict(subject="Java", question="Which method is the entry point of a Java program?",
                 option_a="start()", option_b="run()", option_c="main()", option_d="init()", correct_option="C"),
            dict(subject="Java", question="Java is platform independent because of?",
                 option_a="Compiler", option_b="JVM", option_c="IDE", option_d="JDK", correct_option="B"),
            dict(subject="Java", question="Which keyword creates an object in Java?",
                 option_a="new", option_b="create", option_c="make", option_d="object", correct_option="A"),
            dict(subject="Java", question="Default value of a boolean in Java is?",
                 option_a="0", option_b="null", option_c="false", option_d="true", correct_option="C"),
            dict(subject="Java", question="Which of these is not a Java primitive type?",
                 option_a="int", option_b="float", option_c="String", option_d="char", correct_option="C"),
            dict(subject="C", question="Which header file is required for printf()?",
                 option_a="stdlib.h", option_b="stdio.h", option_c="string.h", option_d="conio.h", correct_option="B"),
            dict(subject="C", question="What is the size of an int on most systems (bytes)?",
                 option_a="2", option_b="4", option_c="8", option_d="1", correct_option="B"),
            dict(subject="C", question="Which operator is used to access a value at an address in a pointer?",
                 option_a="&", option_b="*", option_c="%", option_d="#", correct_option="B"),
            dict(subject="C", question="Which loop checks the condition after executing the body?",
                 option_a="for", option_b="while", option_c="do-while", option_d="if", correct_option="C"),
            dict(subject="C", question="Which function allocates memory dynamically in C?",
                 option_a="malloc()", option_b="alloc()", option_c="new()", option_d="calloc_mem()", correct_option="A"),
            dict(subject="C++", question="Which keyword defines a class in C++?",
                 option_a="class", option_b="struct", option_c="object", option_d="define", correct_option="A"),
            dict(subject="C++", question="Which operator is used for dynamic memory allocation in C++?",
                 option_a="malloc", option_b="new", option_c="alloc", option_d="create", correct_option="B"),
            dict(subject="C++", question="Which of these supports OOP feature 'Inheritance'?",
                 option_a="C", option_b="C++", option_c="Assembly", option_d="Machine Code", correct_option="B"),
            dict(subject="C++", question="Which symbol is used for scope resolution in C++?",
                 option_a="::", option_b="->", option_c=".", option_d=":", correct_option="A"),
            dict(subject="C++", question="Which of the following is a C++ STL container?",
                 option_a="vector", option_b="array_list", option_c="hashmap", option_d="stackframe",
                 correct_option="A"),
        ]

        coding_challenges = [
            dict(title="Sum of Two Numbers", difficulty="Easy", subject="Python", language="Python",
                 description="Read two integers and print their sum.",
                 input_format="Two integers a and b, space separated.",
                 output_format="Single integer: a + b.",
                 sample_input="3 4", sample_output="7", expected_output="7"),
            dict(title="Check Even or Odd", difficulty="Easy", subject="Python", language="Python",
                 description="Read an integer and print 'Even' or 'Odd'.",
                 input_format="One integer n.", output_format="'Even' or 'Odd'.",
                 sample_input="10", sample_output="Even", expected_output="Even"),
            dict(title="Reverse a String", difficulty="Medium", subject="Python", language="Python",
                 description="Read a string and print it reversed.",
                 input_format="A single line string.", output_format="Reversed string.",
                 sample_input="hello", sample_output="olleh", expected_output="olleh"),
            dict(title="Factorial", difficulty="Medium", subject="Java", language="Java",
                 description="Read an integer n and print n! (factorial).",
                 input_format="One integer n.", output_format="Factorial of n.",
                 sample_input="5", sample_output="120", expected_output="120"),
            dict(title="Fibonacci Series", difficulty="Hard", subject="C", language="C",
                 description="Print first n terms of the Fibonacci series.",
                 input_format="One integer n.", output_format="n Fibonacci numbers space separated.",
                 sample_input="5", sample_output="0 1 1 2 3", expected_output="0 1 1 2 3"),
        ]

        practicals = [
            dict(practical_no=1, subject="Python", title="Introduction to Python & Variables",
                 co="CO1", llo="Understand variables and data types", task="Write a program to swap two variables."),
            dict(practical_no=2, subject="Python", title="Control Flow Statements",
                 co="CO1", llo="Apply if-else and loops", task="Write a program to check if a number is prime."),
            dict(practical_no=1, subject="Java", title="Java Basics & OOP",
                 co="CO1", llo="Understand classes and objects", task="Write a Java program to create a Student class."),
            dict(practical_no=1, subject="C", title="C Fundamentals",
                 co="CO1", llo="Understand pointers and arrays",
                 task="Write a C program to find the largest element in an array."),
        ]

        for q in quiz_questions:
            if not Quiz.query.filter_by(subject=q["subject"], question=q["question"]).first():
                db.session.add(Quiz(**q))
                added["quiz"] += 1

        for c in coding_challenges:
            if not CodingChallenge.query.filter_by(title=c["title"]).first():
                db.session.add(CodingChallenge(**c))
                added["challenges"] += 1

        for p in practicals:
            if not Practical.query.filter_by(subject=p["subject"], practical_no=p["practical_no"]).first():
                db.session.add(Practical(**p))
                added["practicals"] += 1

        db.session.commit()

    return (f"✅ Setup complete! Tables created/verified. "
            f"Added {added['quiz']} quiz questions, {added['challenges']} coding challenges, "
            f"{added['practicals']} practicals. You can now register/login normally.")

# ----------------------------
# LANGUAGE CONFIG
# ----------------------------
LANG_CONFIG = {
    "python": {
        "lang": "python",
        "file": "main.py"
    },
    "java": {
        "lang": "java",
        "file": "Main.java"
    },
    "c": {
        "lang": "c",
        "file": "main.c"
    },
    "c++": {
        "lang": "cpp",
        "file": "main.cpp"
    }
}

# ----------------------------
# HELPERS
# ----------------------------
def normalize_output(s: str) -> str:
    """Normalize code output for comparison: strip whitespace, unify line endings."""
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.strip().split()) for line in s.split("\n")]
    return "\n".join(lines).strip()


def analyze_weak_areas(student_id):
    subjects=[q.subject for q in Quiz.query.distinct(Quiz.subject)]
    quiz_results=QuizResult.query.filter_by(user_id=student_id).all()
    progress, weak={}, []
    for sub in subjects:
        scores=[q.score for q in quiz_results if q.subject==sub]
        avg=round(sum(scores)/len(scores),2) if scores else 0
        progress[sub]=avg
        if avg<60: weak.append(sub)
    return {"progress":progress,"weak":weak}

def ai_generate_fix_list(topic, student_errors):
    try:
        prompt = f"Give 3 improvement steps for {topic}"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("AI ERROR:", e)
        return fallback_ai_fix(topic)

def normalize_output(s: str) -> str:
    """Normalize code output for comparison: strip whitespace, unify line endings."""
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.strip().split()) for line in s.split("\n")]
    return "\n".join(lines).strip()

def ai_generate_practice_tasks(topic, material):
    try:
        prompt = f"Give 3 simple practice tasks for {topic}."
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.split("\n")
    except Exception as e:
        print("AI ERROR (practice):", e)
        return ["🤖 ⚠️ AI is busy or error occurred."]

def ai_generate_extra_questions(topic, material):
    try:
        prompt = f"Generate 3 simple MCQs for {topic}."
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("AI ERROR (questions):", e)
        return "🤖 ⚠️ AI is busy or error occurred."


def ai_generate_fix_list(topic, student_errors):
    try:
        prompt = f"Give 3 improvement steps for {topic}"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("AI ERROR:", e)
        return "🤖 ⚠️ AI is busy or error occurred."

def offline_chatbot_reply(message):
    msg = message.lower().strip()

    # ---------------- GREETINGS ----------------
    if any(word in msg for word in ["hi", "hello", "hey", "good morning", "good evening"]):
        return "Hello 😊 I'm your learning assistant. How can I help you today?"

    # ---------------- HELP ----------------
    if "help" in msg or "support" in msg:
        return (
            "I can help you with:\n"
            "• Quizzes & unlocking topics\n"
            "• Programming languages (C, Java, Python)\n"
            "• Study tips & practice guidance\n"
            "Just ask 😊"
        )

    # ---------------- QUIZ ----------------
    if "quiz" in msg:
        if "retake" in msg:
            return "You can retake a quiz if your score is below 60%."
        return (
            "Quizzes test your understanding.\n"
            "✔ Score ≥ 60% → Next topic unlocks\n"
            "❌ Score < 60% → Retake quiz"
        )

    # ---------------- UNLOCK SYSTEM ----------------
    if "unlock" in msg or "locked" in msg:
        return (
            "Topics unlock one by one.\n"
            "Complete the current quiz with at least 60% to unlock the next topic."
        )

    # ---------------- PROGRESS ----------------
    if "progress" in msg or "score" in msg:
        return "Your progress is calculated using quiz scores and completed activities."

    # ---------------- STUDY MATERIAL ----------------
    if "study" in msg or "notes" in msg or "material" in msg:
        return (
            "Study materials include:\n"
            "📘 Notes\n"
            "📘 Practice problems\n"
            "🌐 Online references\n"
            "Check them from your dashboard."
        )

    # ---------------- PROGRAMMING LANGUAGES ----------------
    if "c language" in msg or "c programming" in msg or msg == "c":
        return (
            "C Language Topics:\n"
            "• Variables & Data Types\n"
            "• Loops & Conditions\n"
            "• Arrays & Strings\n"
            "• Pointers & Functions"
        )

    if "java" in msg:
        return (
            "Java Topics:\n"
            "• OOP Concepts\n"
            "• Inheritance & Polymorphism\n"
            "• Exception Handling\n"
            "• Collections & JDBC"
        )

    if "python" in msg:
        return (
            "Python Basics:\n"
            "• Variables & Data Types\n"
            "• Lists, Tuples, Dictionaries\n"
            "• Functions & Modules\n"
            "• File Handling"
        )

    # ---------------- PRACTICE & EXAMS ----------------
    if "practice" in msg:
        return "Practice daily. Consistency is the key to programming success 💻"

    if "exam" in msg or "test" in msg:
        return (
            "Exam Tips:\n"
            "✔ Revise basics\n"
            "✔ Solve practice problems\n"
            "✔ Attempt quizzes regularly\n"
            "✔ Manage time properly"
        )

    # ---------------- MOTIVATION ----------------
    if any(word in msg for word in ["tired", "stress", "demotivated", "motivation"]):
        return (
            "Don't give up 💪\n"
            "Every expert was once a beginner. Keep learning!"
        )

    # ---------------- DEFAULT ----------------
    return (
        "🤔 I didn't fully understand that.\n"
        "You can ask me about quizzes, unlocking topics, C, Java, Python, or study tips."
    )




def smart_resources(topic, score):
    if score < 50:
        return [
            ("YouTube Basics", f"https://www.youtube.com/results?search_query={topic}+basics"),
            ("W3Schools", f"https://www.w3schools.com/")
        ]
    elif score < 70:
        return [
            ("GeeksForGeeks", f"https://www.geeksforgeeks.org/{topic.lower()}"),
            ("Practice Problems", "https://practice.geeksforgeeks.org")
        ]
    else:
        return [
            ("Official Docs", f"https://docs.oracle.com/javase/8/docs/")
        ]
    
def fallback_ai_fix(topic):
    suggestions = suggestion_links(topic)
    html = "<ul>"
    for s, link in suggestions:
        html += f'<li>{s} - <a href="{link}" target="_blank">Study here</a></li>'
    html += "</ul>"
    return html
def ai_generate_fix_list(topic, student_errors):
    try:
        prompt = f"Give 3 improvement steps for {topic}"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("AI ERROR:", e)
        return fallback_ai_fix(topic)

def suggestion_links(topic):
    """Return a list of (suggestion, link) tuples for a given topic."""
    links = {
        "C": [
            ("Revise loops and conditions", "https://www.geeksforgeeks.org/c-loop-control/"),
            ("Practice arrays and pointers", "https://www.tutorialspoint.com/cprogramming/c_arrays.htm"),
            ("Solve beginner C programs", "https://www.codechef.com/problems/easy")
        ],
        "Java": [
            ("Revise OOP concepts", "https://docs.oracle.com/javase/tutorial/java/concepts/"),
            ("Practice inheritance examples", "https://www.geeksforgeeks.org/inheritance-in-java/"),
            ("Write small Java programs", "https://www.hackerrank.com/domains/java")
        ],
        "Python": [
            ("Practice lists and dictionaries", "https://docs.python.org/3/tutorial/datastructures.html"),
            ("Revise functions", "https://www.w3schools.com/python/python_functions.asp"),
            ("Solve Python basics problems", "https://www.hackerrank.com/domains/python")
        ]
    }

    # Return fallback if topic not found
    return links.get(topic, [("Revise basics", "https://www.google.com")])

def insert_c_practicals():
    practicals = [

        Practical(1, "Install and study the C programming environment",
                  "CO1", "LLO 2.1, LLO 2.2",
                  "Install GCC compiler and study C programming environment."),

        Practical(2, "Constants and Variables",
                  "CO1", "LLO 2.1, LLO 2.2",
                  "Implement C programs using constants and variables."),

        Practical(3, "Arithmetic Operators",
                  "CO1", "LLO 3.1",
                  "Implement C programs using arithmetic operators."),

        Practical(4, "Type Casting",
                  "CO1", "LLO 4.1",
                  "Implement C programs using implicit and explicit data type conversion."),

        Practical(5, "Formatted Input and Output",
                  "CO1", "LLO 5.1",
                  "Write well-commented C programs using formatted input/output statements."),

        Practical(6, "Relational and Conditional Operators",
                  "CO1", "LLO 6.1, LLO 6.2",
                  "Implement minimum two C programs using relational and conditional operators."),

        Practical(7, "Logical Operators",
                  "CO1, CO2", "LLO 7.1",
                  "Implement minimum two C programs using logical operators."),

        Practical(8, "Bitwise Operators",
                  "CO1, CO2", "LLO 8.1",
                  "Implement minimum two C programs using bitwise operators."),

        Practical(9, "Simple If and If-Else",
                  "CO2", "LLO 9.1, LLO 9.2",
                  "Implement C programs using simple if and if-else statements."),

        Practical(10, "Nested If and Else-If Ladder",
                   "CO2", "LLO 10.1",
                   "Write C program to print grades of students based on percentage."),

        Practical(11, "Switch Statement",
                   "CO2", "LLO 11.1",
                   "Develop C programs using switch statement."),

        Practical(12, "Calendar Months using Switch",
                   "CO2", "LLO 12.1",
                   "Print English calendar month name using switch statement."),

        Practical(13, "While and Do-While Loop",
                   "CO2", "LLO 13.1",
                   "Implement minimum two C programs using while and do-while loops."),

        Practical(14, "For Loop",
                   "CO2", "LLO 14.1, LLO 14.2",
                   "Write C program using for loop (e.g., print 1 to 100)."),

        Practical(15, "Pattern Printing using Loops",
                   "CO1, CO2", "LLO 15.1, LLO 15.2",
                   "Print various patterns using loops."),

        Practical(16, "One Dimensional Array",
                   "CO2", "LLO 16.1, LLO 16.2",
                   "Implement C programs using one-dimensional array."),

        Practical(17, "Two Dimensional Array",
                   "CO2, CO3", "LLO 17.1, LLO 17.2",
                   "Implement C programs using two-dimensional array."),

        Practical(18, "String Operations without Library",
                   "CO3", "LLO 18.1, LLO 18.2",
                   "Perform string operations without using standard string functions."),

        Practical(19, "Structure",
                   "CO3", "LLO 19.1",
                   "Implement structure in C (e.g., complex number operations)."),

        Practical(20, "Array of Structure",
                   "CO3", "LLO 20.1",
                   "Implement array of structure (employee information)."),

        Practical(21, "Built-in Library Functions",
                   "CO3", "LLO 21.1",
                   "Develop C programs using built-in mathematical and string functions."),

        Practical(22, "User Defined Functions",
                   "CO4", "LLO 22.1",
                   "Write C programs to demonstrate user-defined functions."),

        Practical(23, "Recursive Functions",
                   "CO4", "LLO 23.1",
                   "Implement recursive functions in C."),

        Practical(24, "Pointers Basics",
                   "CO4", "LLO 24.1, LLO 24.2",
                   "Write C program to access and display address of variables using pointers."),

        Practical(25, "Pointer Arithmetic",
                   "CO5", "LLO 25.1",
                   "Implement C programs to perform arithmetic operations using pointers.")
    ]

    db.session.add_all(practicals)
    db.session.commit()
    print("✅ All 25 C Practicals Inserted Successfully")
def insert_cpp_practicals():
    practicals = [
        Practical(1, "Install and setup C++ environment",
                  "CO1", "LLO 1.1",
                  "Install IDE/compiler and write a Hello World program.",
                  subject="C++"),
        Practical(2, "Variables and Constants in C++",
                  "CO1", "LLO 1.2",
                  "Implement programs using variables and constants.",
                  subject="C++"),
        Practical(3, "Arithmetic Operators in C++",
                  "CO1", "LLO 2.1",
                  "Implement programs using arithmetic operators.",
                  subject="C++"),
        Practical(4, "Type Casting",
                  "CO1", "LLO 2.2",
                  "Implement programs using implicit and explicit type conversion.",
                  subject="C++"),
        Practical(5, "Input and Output using cin/cout",
                  "CO1", "LLO 3.1",
                  "Write programs using formatted input/output with cin and cout.",
                  subject="C++"),
        Practical(6, "Relational and Logical Operators",
                  "CO2", "LLO 3.2",
                  "Implement programs using relational and logical operators.",
                  subject="C++"),
        Practical(7, "If and If-Else Statements",
                  "CO2", "LLO 4.1",
                  "Write programs using simple if and if-else statements.",
                  subject="C++"),
        Practical(8, "Nested If and Else-If Ladder",
                  "CO2", "LLO 4.2",
                  "Write programs using nested if and else-if ladder.",
                  subject="C++"),
        Practical(9, "Switch Statement",
                  "CO2", "LLO 5.1",
                  "Write programs using switch statement.",
                  subject="C++"),
        Practical(10, "While and Do-While Loops",
                   "CO2", "LLO 5.2",
                   "Implement programs using while and do-while loops.",
                   subject="C++"),
        Practical(11, "For Loop",
                   "CO2", "LLO 6.1",
                   "Write programs using for loops (e.g., print 1 to 100).",
                   subject="C++"),
        Practical(12, "Pattern Printing using Loops",
                   "CO2", "LLO 6.2",
                   "Print different patterns using loops.",
                   subject="C++"),
        Practical(13, "One-Dimensional Array",
                   "CO3", "LLO 7.1",
                   "Implement programs using one-dimensional arrays.",
                   subject="C++"),
        Practical(14, "Two-Dimensional Array",
                   "CO3", "LLO 7.2",
                   "Implement programs using two-dimensional arrays.",
                   subject="C++"),
        Practical(15, "String Operations",
                   "CO3", "LLO 8.1",
                   "Perform basic string operations using C++ strings.",
                   subject="C++"),
        Practical(16, "Functions",
                   "CO3", "LLO 8.2",
                   "Write programs demonstrating user-defined functions.",
                   subject="C++"),
        Practical(17, "Recursive Functions",
                   "CO4", "LLO 9.1",
                   "Implement recursive functions in C++.",
                   subject="C++"),
        Practical(18, "Structures in C++",
                   "CO4", "LLO 9.2",
                   "Define structures and access members in programs.",
                   subject="C++"),
        Practical(19, "Array of Structures",
                   "CO4", "LLO 10.1",
                   "Implement array of structures in programs.",
                   subject="C++"),
        Practical(20, "Pointers Basics",
                   "CO5", "LLO 10.2",
                   "Write programs to demonstrate pointer usage.",
                   subject="C++"),
        Practical(21, "Pointer Arithmetic",
                   "CO5", "LLO 11.1",
                   "Implement programs using pointer arithmetic.",
                   subject="C++"),
        Practical(22, "Dynamic Memory Allocation",
                   "CO5", "LLO 11.2",
                   "Use new/delete to allocate and free memory dynamically.",
                   subject="C++"),
        Practical(23, "Classes and Objects",
                   "CO5", "LLO 12.1",
                   "Implement basic classes and objects in C++.",
                   subject="C++"),
        Practical(24, "Constructor and Destructor",
                   "CO5", "LLO 12.2",
                   "Implement constructors and destructors in classes.",
                   subject="C++"),
        Practical(25, "Inheritance Basics",
                   "CO6", "LLO 13.1",
                   "Demonstrate single and multilevel inheritance in C++.",
                   subject="C++")
    ]

    db.session.add_all(practicals)
    db.session.commit()
    print("✅ All 25 C++ Practicals Inserted Successfully")
def insert_java_practicals():
    practicals = [
        Practical(1, "Install and setup Java environment",
                  "CO1", "LLO 1.1",
                  "Install JDK and set up IDE, write Hello World program.",
                  subject="Java"),
        Practical(2, "Variables and Data Types in Java",
                  "CO1", "LLO 1.2",
                  "Write programs using different data types and variables.",
                  subject="Java"),
        Practical(3, "Arithmetic Operators in Java",
                  "CO1", "LLO 2.1",
                  "Implement programs using arithmetic operators.",
                  subject="Java"),
        Practical(4, "Type Casting",
                  "CO1", "LLO 2.2",
                  "Implement programs using implicit and explicit type conversion.",
                  subject="Java"),
        Practical(5, "Input and Output using Scanner",
                  "CO1", "LLO 3.1",
                  "Write programs using Scanner for input and System.out for output.",
                  subject="Java"),
        Practical(6, "Relational and Logical Operators",
                  "CO2", "LLO 3.2",
                  "Implement programs using relational and logical operators.",
                  subject="Java"),
        Practical(7, "If and If-Else Statements",
                  "CO2", "LLO 4.1",
                  "Write programs using simple if and if-else statements.",
                  subject="Java"),
        Practical(8, "Nested If and Else-If Ladder",
                  "CO2", "LLO 4.2",
                  "Write programs using nested if and else-if ladder.",
                  subject="Java"),
        Practical(9, "Switch Statement",
                  "CO2", "LLO 5.1",
                  "Write programs using switch statement.",
                  subject="Java"),
        Practical(10, "While and Do-While Loops",
                   "CO2", "LLO 5.2",
                   "Implement programs using while and do-while loops.",
                   subject="Java"),
        Practical(11, "For Loop",
                   "CO2", "LLO 6.1",
                   "Write programs using for loops.",
                   subject="Java"),
        Practical(12, "Pattern Printing using Loops",
                   "CO2", "LLO 6.2",
                   "Print different patterns using loops.",
                   subject="Java"),
        Practical(13, "One-Dimensional Array",
                   "CO3", "LLO 7.1",
                   "Implement programs using one-dimensional arrays.",
                   subject="Java"),
        Practical(14, "Two-Dimensional Array",
                   "CO3", "LLO 7.2",
                   "Implement programs using two-dimensional arrays.",
                   subject="Java"),
        Practical(15, "String Operations",
                   "CO3", "LLO 8.1",
                   "Perform basic string operations using Java String class.",
                   subject="Java"),
        Practical(16, "Methods in Java",
                   "CO3", "LLO 8.2",
                   "Write programs demonstrating methods and function calls.",
                   subject="Java"),
        Practical(17, "Recursive Methods",
                   "CO4", "LLO 9.1",
                   "Implement recursive methods in Java.",
                   subject="Java"),
        Practical(18, "Classes and Objects",
                   "CO4", "LLO 9.2",
                   "Create classes and objects with member variables and methods.",
                   subject="Java"),
        Practical(19, "Constructors and Destructors",
                   "CO4", "LLO 10.1",
                   "Use constructors and finalize method in Java classes.",
                   subject="Java"),
        Practical(20, "Inheritance Basics",
                   "CO5", "LLO 10.2",
                   "Demonstrate single and multilevel inheritance.",
                   subject="Java"),
        Practical(21, "Polymorphism",
                   "CO5", "LLO 11.1",
                   "Implement method overloading and overriding.",
                   subject="Java"),
        Practical(22, "Interfaces in Java",
                   "CO5", "LLO 11.2",
                   "Create interfaces and implement them in classes.",
                   subject="Java"),
        Practical(23, "Packages and Import",
                   "CO5", "LLO 12.1",
                   "Organize classes into packages and use import statements.",
                   subject="Java"),
        Practical(24, "Exception Handling",
                   "CO5", "LLO 12.2",
                   "Handle exceptions using try-catch-finally blocks.",
                   subject="Java"),
        Practical(25, "File Handling in Java",
                   "CO6", "LLO 13.1",
                   "Read and write files using FileReader and FileWriter.",
                   subject="Java")
    ]
    
    db.session.add_all(practicals)
    db.session.commit()
    print("✅ All 25 Java Practicals Inserted Successfully")
def insert_python_practicals():
    practicals = [
        Practical(1, "Install Python and setup environment",
                  "CO1", "LLO 1.1",
                  "Install Python, set up IDE, write Hello World program.",
                  subject="Python"),
        Practical(2, "Variables and Data Types",
                  "CO1", "LLO 1.2",
                  "Write programs using different data types and variables.",
                  subject="Python"),
        Practical(3, "Arithmetic Operators",
                  "CO1", "LLO 2.1",
                  "Implement programs using arithmetic operators.",
                  subject="Python"),
        Practical(4, "Type Casting",
                  "CO1", "LLO 2.2",
                  "Convert data types using implicit and explicit methods.",
                  subject="Python"),
        Practical(5, "Input and Output using input() and print()",
                  "CO1", "LLO 3.1",
                  "Take input from user and display output.",
                  subject="Python"),
        Practical(6, "Relational and Logical Operators",
                  "CO2", "LLO 3.2",
                  "Implement programs using relational and logical operators.",
                  subject="Python"),
        Practical(7, "If and If-Else Statements",
                  "CO2", "LLO 4.1",
                  "Write programs using if and if-else statements.",
                  subject="Python"),
        Practical(8, "Nested If and Elif",
                  "CO2", "LLO 4.2",
                  "Write programs using nested if and elif statements.",
                  subject="Python"),
        Practical(9, "Loops: while, for",
                  "CO2", "LLO 5.1",
                  "Implement programs using while and for loops.",
                  subject="Python"),
        Practical(10, "Pattern Printing",
                   "CO2", "LLO 5.2",
                   "Print different patterns using loops.",
                   subject="Python"),
        Practical(11, "One-Dimensional Lists",
                   "CO3", "LLO 6.1",
                   "Implement programs using Python lists.",
                   subject="Python"),
        Practical(12, "Two-Dimensional Lists",
                   "CO3", "LLO 6.2",
                   "Implement programs using nested lists.",
                   subject="Python"),
        Practical(13, "Tuples and Sets",
                   "CO3", "LLO 7.1",
                   "Perform operations using tuples and sets.",
                   subject="Python"),
        Practical(14, "Dictionaries",
                   "CO3", "LLO 7.2",
                   "Create and manipulate dictionaries in Python.",
                   subject="Python"),
        Practical(15, "Strings",
                   "CO3", "LLO 8.1",
                   "Perform string operations and slicing.",
                   subject="Python"),
        Practical(16, "Functions",
                   "CO4", "LLO 8.2",
                   "Define and call user-defined functions.",
                   subject="Python"),
        Practical(17, "Recursive Functions",
                   "CO4", "LLO 9.1",
                   "Implement recursion in Python.",
                   subject="Python"),
        Practical(18, "Modules and Packages",
                   "CO4", "LLO 9.2",
                   "Import and use modules and packages.",
                   subject="Python"),
        Practical(19, "Classes and Objects",
                   "CO5", "LLO 10.1",
                   "Create classes and objects in Python.",
                   subject="Python"),
        Practical(20, "Constructor and Destructor",
                   "CO5", "LLO 10.2",
                   "Use __init__ and __del__ methods in classes.",
                   subject="Python"),
        Practical(21, "Inheritance",
                   "CO5", "LLO 11.1",
                   "Demonstrate single and multiple inheritance.",
                   subject="Python"),
        Practical(22, "Polymorphism",
                   "CO5", "LLO 11.2",
                   "Implement method overloading and overriding.",
                   subject="Python"),
        Practical(23, "Exception Handling",
                   "CO5", "LLO 12.1",
                   "Handle exceptions using try-except-finally.",
                   subject="Python"),
        Practical(24, "File Handling",
                   "CO5", "LLO 12.2",
                   "Read and write files using open(), read(), write().",
                   subject="Python"),
        Practical(25, "Basic Python Projects",
                   "CO6", "LLO 13.1",
                   "Implement small projects like calculator, student info manager.",
                   subject="Python")
    ]
    
    db.session.add_all(practicals)
    db.session.commit()
    print("✅ All 25 Python Practicals Inserted Successfully")



# ----------------------------
# GAMIFICATION HELPERS
# ----------------------------

def calculate_level(points):
    if points >= 1000:
        return "Master"
    elif points >= 500:
        return "Advanced"
    elif points >= 200:
        return "Intermediate"
    else:
        return "Beginner"


def update_gamification(user, earned_points):
    today = date.today()

    user.points += earned_points
    user.level = calculate_level(user.points)

    if user.last_active == today:
        pass
    elif user.last_active == today - timedelta(days=1):
        user.streak += 1
    else:
        user.streak = 1

    user.last_active = today
    db.session.commit()


# ----------------------------
# ROUTES
# ----------------------------



#------------------------
# HOME
#------------------------
@app.route('/')
def home():
    if 'user_id' in session:
        role=session.get('role')
        if role=='student': return redirect(url_for('student_dashboard'))
        if role=='teacher': return redirect(url_for('teacher_dashboard'))
        if role=='admin': return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

#-------------------------------
# REGISTER
#--------------------------------

@app.route('/register', methods=['GET','POST'])
def register():
    error=None
    if request.method=='POST':
        username=request.form['username'].strip()
        password=request.form['password']
        role = request.form.get('role')
        if User.query.filter_by(username=username).first(): error="Username exists"; return render_template('register.html',error=error)
        if role=="admin":
            admin_secret=request.form.get("admin_secret","").strip()
            expected_secret=os.getenv("ADMIN_SECRET_KEY","").strip()
            if not expected_secret or admin_secret!=expected_secret: error="Invalid Admin Key"; return render_template('register.html',error=error)
        if role=="teacher":
            teacher_secret=request.form.get("teacher_secret","").strip()
            expected_teacher_secret=os.getenv("TEACHER_SECRET_KEY","").strip()
            if not expected_teacher_secret or teacher_secret!=expected_teacher_secret:
                error="Invalid Teacher Key"
                return render_template('register.html',error=error)
        hashed=generate_password_hash(password)
        user=User(username=username,password=hashed,role=role)
        db.session.add(user); db.session.commit()
        flash("Registration successful! Please login."); return redirect(url_for('login'))
    return render_template('register.html', error=error)
#------------------------
# LOGIN
#------------------------

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # ✅ Fix 1: Check empty fields
        if not username or not password:
            flash("Please fill all fields", "error")
            return redirect(url_for('login'))

        username = username.strip()

        # ✅ Fix 2: Find user correctly
        user = User.query.filter_by(username=username).first()

        # ✅ Fix 3: Validate user + password
        if not user or not check_password_hash(user.password, password):
            flash("Invalid username or password", "error")
            return redirect(url_for('login'))

        # ✅ Fix 4: Set session
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role

        flash("Logged in successfully!", "success")

        # ✅ Fix 5: Role-based redirect
        if user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif user.role == 'admin':
            return redirect(url_for('admin_dashboard'))

    return render_template('login.html')

#----------------------------
# ADMIN DASHBOARD
#----------------------------
@app.route('/admin_dashboard', methods=['GET','POST'])
def admin_dashboard():
    if "user_id" not in session or session.get("role")!="admin": flash("Unauthorized"); return redirect(url_for('login'))
    users=User.query.all(); return render_template("admin_dashboard.html", users=users)

@app.route('/add_user', methods=['POST'])
def add_user():
    if "user_id" not in session or session.get("role")!="admin": flash("Unauthorized"); return redirect(url_for('login'))
    username=request.form["username"].strip(); password=request.form["password"]; role=request.form["role"]
    if User.query.filter_by(username=username).first(): flash("Username exists")
    else: db.session.add(User(username=username,password=generate_password_hash(password),role=role)); db.session.commit(); flash("User added")
    return redirect(url_for("admin_dashboard"))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):

    if "user_id" not in session or session.get("role") != "admin":
        flash("Unauthorized")
        return redirect(url_for('login'))

    if user_id == session["user_id"]:
        flash("Cannot delete own account")
        return redirect(url_for("admin_dashboard"))

    user = User.query.get_or_404(user_id)

    try:
        # ✅ Step 1: delete feedback
        Feedback.query.filter_by(student_id=user_id).delete()

        # ✅ Step 2: delete user
        db.session.delete(user)
        db.session.commit()

        flash(f"User {user.username} deleted")

    except Exception as e:
        db.session.rollback()
        flash("Error deleting user")

    return redirect(url_for("admin_dashboard"))
# ----------------------------
# STUDENT DASHBOARD (FULL WORKING)
# ----------------------------

@app.route('/student_dashboard', methods=['GET', 'POST'])
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    student_id = session['user_id']
    student = db.session.get(User, student_id)

    # ---------------- GAMIFICATION ----------------
    today = date.today()
    if student.last_active == today:
        pass
    elif student.last_active == today - timedelta(days=1):
        student.streak += 1
    else:
        student.streak = 1
    student.last_active = today

    # Auto Level System
    if student.points >= 500:
        student.level = "Master"
    elif student.points >= 300:
        student.level = "Advanced"
    elif student.points >= 150:
        student.level = "Intermediate"
    else:
        student.level = "Beginner"

    db.session.commit()

    # ---------------- QUIZ PROGRESS ----------------
    topics = [q.subject for q in Quiz.query.distinct(Quiz.subject)]
    quiz_results = QuizResult.query.filter_by(user_id=student_id).all()

    quiz_progress = {}
    weak_topics = []

    for topic in topics:
        scores = [r.score for r in quiz_results if r.subject == topic]
        avg = int(sum(scores)/len(scores)) if scores else 0
        quiz_progress[topic] = avg
        if avg < 60:
            weak_topics.append(topic)

    quiz_avg_progress = int(sum(quiz_progress.values()) / len(quiz_progress)) if quiz_progress else 0

    # ---------------- SEQUENTIAL QUIZ UNLOCK ----------------
    quiz_completed = {topic: (score > 0) for topic, score in quiz_progress.items()}
    quiz_unlocked = {}
    previous_completed = True

    for topic in topics:
        if quiz_completed[topic]:
            quiz_unlocked[topic] = True
        else:
            quiz_unlocked[topic] = previous_completed
        previous_completed = quiz_completed[topic]

    # ---------------- REMEDIAL MATERIALS ----------------
    remedial_materials = {t: StudyMaterial.query.filter_by(course=t).all() for t in weak_topics}

    # ---------------- CODING CHALLENGES ----------------
    student_subs = Submission.query.filter_by(student_id=student_id).all()
    solved_challenges = {s.challenge_id for s in student_subs if s.score and s.score >= 60}

    languages = ["C", "C++", "Python", "Java"]
    selected_language = request.form.get("language") if request.method == "POST" else None

    query = CodingChallenge.query
    if selected_language:
        query = query.filter(func.lower(CodingChallenge.language) == selected_language.lower())

    challenges_by_diff = {
        "easy": query.filter_by(difficulty="Easy").order_by(CodingChallenge.id.asc()).all(),
        "medium": query.filter_by(difficulty="Medium").order_by(CodingChallenge.id.asc()).all(),
        "hard": query.filter_by(difficulty="Hard").order_by(CodingChallenge.id.asc()).all()
    }

    test_progress = {}
    unlocked_challenges = {}
    force_easy_only = any(score < 50 for score in quiz_progress.values())

    # Easy challenges
    easy_done = True
    for i, ch in enumerate(challenges_by_diff["easy"]):
        subs = [s for s in student_subs if s.challenge_id == ch.id]
        scores = [s.score for s in subs if s.score is not None]
        test_progress[ch.id] = int(sum(scores)/len(scores)) if scores else 0
        unlocked_challenges[ch.id] = i == 0 or challenges_by_diff["easy"][i-1].id in solved_challenges
        if ch.id not in solved_challenges:
            easy_done = False

    # Medium challenges
    medium_done = True
    if not force_easy_only and easy_done:
        for i, ch in enumerate(challenges_by_diff["medium"]):
            subs = [s for s in student_subs if s.challenge_id == ch.id]
            scores = [s.score for s in subs if s.score is not None]
            test_progress[ch.id] = int(sum(scores)/len(scores)) if scores else 0
            unlocked_challenges[ch.id] = i == 0 or challenges_by_diff["medium"][i-1].id in solved_challenges
            if ch.id not in solved_challenges:
                medium_done = False
    else:
        for ch in challenges_by_diff["medium"]:
            test_progress[ch.id] = 0
            unlocked_challenges[ch.id] = False
        medium_done = False

    # Hard challenges
    if not force_easy_only and medium_done:
        for i, ch in enumerate(challenges_by_diff["hard"]):
            subs = [s for s in student_subs if s.challenge_id == ch.id]
            scores = [s.score for s in subs if s.score is not None]
            test_progress[ch.id] = int(sum(scores)/len(scores)) if scores else 0
            unlocked_challenges[ch.id] = i == 0 or challenges_by_diff["hard"][i-1].id in solved_challenges
    else:
        for ch in challenges_by_diff["hard"]:
            test_progress[ch.id] = 0
            unlocked_challenges[ch.id] = False

    # Test average
    test_avg_progress = int(sum(test_progress.values()) / len(test_progress)) if test_progress else 0

    # Determine visible challenges
    if force_easy_only:
        visible_challenges = challenges_by_diff["easy"]
    elif not easy_done:
        visible_challenges = challenges_by_diff["easy"]
    elif not medium_done:
        visible_challenges = challenges_by_diff["easy"] + challenges_by_diff["medium"]
    else:
        visible_challenges = challenges_by_diff["easy"] + challenges_by_diff["medium"] + challenges_by_diff["hard"]

    # Access coding console only if quiz_avg >=60
    can_access_console = quiz_avg_progress >= 50

    # ---------------- TODAY TASKS ----------------
    today_tasks = []
    for topic, score in quiz_progress.items():
        if score < 70 and quiz_unlocked.get(topic):
            today_tasks.append(f"📝 Take quiz on {topic}")
            break
    for ch in visible_challenges:
        if test_progress.get(ch.id, 0) < 60:
            today_tasks.append(f"💻 Solve {ch.title}")
            break
    if weak_topics:
        today_tasks.append(f"📘 Revise {weak_topics[0]} basics")

    # ---------------- PRACTICALS ----------------
    practicals_by_subject = {}
    for lang in languages:
        practicals_by_subject[lang] = Practical.query.filter_by(subject=lang).order_by(Practical.practical_no).all()

    # ---------------- EXTERNAL RESOURCES ----------------
    external_resources = {
        "Java": [
            ("Java Basics – Oracle Docs", "https://docs.oracle.com/javase/tutorial/"),
            ("Java Full Course – YouTube", "https://www.youtube.com/watch?v=eIrMbAQSU34")
        ],
        "Python": [
            ("Python Docs", "https://docs.python.org/3/tutorial/"),
            ("Python Course – YouTube", "https://www.youtube.com/watch?v=_uQrJ0TkZlc")
        ]
    }

 # ---------------- AI-Powered Remedial Suggestions ----------------
    # external_resources = {"Python": [...], "Java": [...] }  # your mapping
    ai_remedial_suggestions = {}
    for topic in weak_topics:
        suggestions = []
        # External resources
        if topic in external_resources:
            suggestions.extend(external_resources[topic])
        # Easy coding challenges as mini-exercises
        easy_challenges = CodingChallenge.query.filter_by(subject=topic, difficulty="Easy").all()
        for ch in easy_challenges:
            suggestions.append(("Mini Challenge: " + ch.title, url_for('solve_challenge', challenge_id=ch.id)))
        ai_remedial_suggestions[topic] = suggestions

    # ---------------- REAL-TIME NOTIFICATIONS ----------------
    notifications = Notification.query.filter_by(user_id=student_id, seen=False).order_by(Notification.created_at.desc()).all()
    
    return render_template(
        'student_dashboard.html',
        student=student,
        points=student.points,
        level=student.level,
        streak=student.streak,
        practicals_by_subject=practicals_by_subject,
        external_resources=external_resources,
        topics=topics,
        today_tasks=today_tasks,
        quiz_progress=quiz_progress,
        quiz_avg_progress=quiz_avg_progress,
        quiz_unlocked=quiz_unlocked,
        weak_topics=weak_topics,
        remedial_materials=remedial_materials,
        test_challenges=visible_challenges,
        test_progress=test_progress,
        unlocked_challenges=unlocked_challenges,
        test_avg_progress=test_avg_progress,
        languages=languages,
        selected_language=selected_language,
        ai_remedial_suggestions=ai_remedial_suggestions,
        notifications=notifications,
        can_access_console=can_access_console
    )


def broadcast_notification(title, body, user_ids=None):
    """Create a Notification for the given user_ids, or for all students if user_ids is None."""
    try:
        if user_ids is None:
            user_ids = [u.id for u in User.query.filter_by(role='student').all()]
        for uid in user_ids:
            db.session.add(Notification(user_id=uid, title=title, body=body))
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route('/get_notifications')
def get_notifications():
    if 'user_id' not in session:
        return jsonify([])

    student_id = session['user_id']
    notifs = Notification.query.filter_by(user_id=student_id, seen=False).order_by(Notification.created_at.desc()).all()
    return jsonify([{"title": n.title, "body": n.body, "created_at": n.created_at} for n in notifs])

#----------------------------
# CHATBOT ROUTE
#----------------------------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "Please type something."})

    # 🔹 Try OpenAI first
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful student assistant."},
                {"role": "user", "content": user_message}
            ]
        )

        ai_reply = response.choices[0].message.content
        return jsonify({"reply": ai_reply})

    # 🔹 If OpenAI fails → Offline bot
    except Exception as e:
        print("OPENAI FAILED → USING OFFLINE BOT:", e)

        fallback_reply = offline_chatbot_reply(user_message)
        return jsonify({"reply": fallback_reply})


#----------------------------
# CHATBOT PAGE
#----------------------------
@app.route("/chatbot_page")
def chatbot_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("chatbot.html")

#----------------------------
# STUDENT PRACTICALS VIEW
# ----------------------------   
@app.route('/student_practicals')
def student_practicals():
    subject = request.args.get("subject", "C")

    practicals = Practical.query.filter_by(subject=subject)\
        .order_by(Practical.practical_no).all()

    student = User.query.get(session.get("user_id"))

    return render_template(
        'practicals.html',
        practicals=practicals,
        subject=subject,
        student=student
    )

#----------------------------
# PRACTICALS ROUTES
#----------------------------
@app.route("/solve_practical/<int:pid>", methods=["GET", "POST"])
def solve_practical(pid):
    # ✅ Check login
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Please login first!")
        return redirect(url_for('login'))

    practical = Practical.query.get_or_404(pid)

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        output = request.form.get("output", "").strip()

        submission = PracticalSubmission(
            student_id=session["user_id"],
            practical_id=pid,
            code=code,
            output=output,
            status="Submitted"
        )
        db.session.add(submission)
        db.session.commit()

        flash("✅ Practical submitted successfully!")
        return redirect(url_for("student_dashboard"))

    return render_template("solve_practical.html", practical=practical)



#from models import User  # make sure this is imported
#----------------------------
# TEACHER VIEW PRACTICALS
#----------------------------

@app.route("/teacher_practicals")
def teacher_practicals():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access!")
        return redirect(url_for('login'))

    submissions = PracticalSubmission.query.order_by(PracticalSubmission.id.desc()).all()

    for sub in submissions:
        # 👤 Student name
        student = User.query.get(sub.student_id)
        sub.student_name = student.username if student else "Unknown"

        # 📘 Practical name
        practical = Practical.query.get(sub.practical_id)
        sub.practical_title = practical.title if practical else "Unknown Practical"

    return render_template("teacher_practicals.html", submissions=submissions)

#----------------------------
# MARK PRACTICAL
#----------------------------
@app.route("/mark_practical/<int:sid>", methods=["POST"])
def mark_practical(sid):

    if session.get("role") != "teacher":
        return redirect(url_for("login"))

    submission = PracticalSubmission.query.get_or_404(sid)

    submission.marks = int(request.form["marks"])
    submission.status = "Checked"

    db.session.commit()
    flash("✅ Marks updated successfully!")

    return redirect(url_for("teacher_practicals"))

#----------------------------
# MY PRACTICALS
#----------------------------
@app.route("/my_practicals")
def my_practicals():
    subs = PracticalSubmission.query.filter_by(
        student_id=session["user_id"]
    ).all()
    for s in subs:
        practical = Practical.query.get(s.practical_id)
        s.practical_title = practical.title if practical else "Unknown Practical"
        s.practical_subject = practical.subject if practical else ""
        s.practical_no = practical.practical_no if practical else None
    return render_template("my_practicals.html", subs=subs)

#----------------------------
# START PRACTICAL
#----------------------------
@app.route('/start_practical/<int:practical_id>', methods=['GET', 'POST'])
def start_practical(practical_id):
    # ✅ Check if student is logged in
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Please login first!")
        return redirect(url_for('login'))

    # Fetch practical
    practical = Practical.query.get_or_404(practical_id)

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        output = request.form.get('output', '').strip()

        # Save practical submission
        submission = PracticalSubmission(
            student_id=session['user_id'],
            practical_id=practical_id,
            code=code,
            output=output,
            status="Submitted"
        )
        db.session.add(submission)
        db.session.commit()

        flash("✅ Practical submitted successfully!")
        return redirect(url_for('student_dashboard'))

    return render_template(
        'start_practical.html',
        practical=practical
    )


#----------------------------
# SUBMIT PRACTICAL (FIXED)
#----------------------------
@app.route('/submit_practical/<int:practical_id>', methods=['POST'])
def submit_practical(practical_id):
    # Use session check instead of Flask-Login decorator
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Please login first!")
        return redirect(url_for('login'))

    student_id = session['user_id']
    code = request.form.get('code', '').strip()
    output = request.form.get('output', '').strip()

    # Auto marks logic
    marks = 0
    if code: marks = 3
    if output: marks = 5

    # Check if submission exists
    existing = PracticalSubmission.query.filter_by(
        student_id=student_id,
        practical_id=practical_id
    ).first()

    if existing:
        existing.code = code
        existing.output = output
        existing.marks = marks
        existing.status = 'Submitted'
        # Optional: add timestamp
        existing.submitted_at = datetime.utcnow()
    else:
        submission = PracticalSubmission(
            student_id=student_id,
            practical_id=practical_id,
            code=code,
            output=output,
            marks=marks,
            status='Submitted',
            submitted_at=datetime.utcnow()
        )
        db.session.add(submission)

    db.session.commit()
    flash('✅ Practical submitted successfully!')
    return redirect(url_for('student_dashboard'))



# ----------------------------
# TEACHER DASHBOARD
# ----------------------------
@app.route("/teacher_dashboard")
def teacher_dashboard():
    
    search_query = request.args.get("search", "").strip().lower()
    subjects = ["Java", "C++", "Python", "C"]

    students = User.query.filter_by(role="student").all()
    student_progress = []
    subject_progress = {}

    for student in students:
        # ---------------- QUIZ PROGRESS ----------------
        quiz_results = QuizResult.query.filter_by(user_id=student.id).all()
        quiz_progress = {}
        for subject in subjects:
            scores = [r.score for r in quiz_results if (r.subject or "").lower() == subject.lower()]
            quiz_progress[subject] = round(sum(scores)/len(scores),2) if scores else 0

        # ---------------- CODING AVERAGE ----------------
        coding_results = Submission.query.filter_by(student_id=student.id).all()
        coding_scores = [c.score for c in coding_results if c.score is not None]
        coding_avg = round(sum(coding_scores)/len(coding_scores),2) if coding_scores else 0

        # ---------------- LAST ACTIVITY ----------------
        last_quiz_time = None
        last_submission = max([s.timestamp for s in coding_results], default=None)
        chats = SimpleTeamChat.query.filter_by(username=student.username).all()
        last_chat = max([c.timestamp for c in chats], default=None)
        discussions = SimpleDiscussion.query.filter_by(username=student.username).all()
        last_discussion = max([d.timestamp for d in discussions], default=None)
        activity_candidates = [x for x in [last_quiz_time, last_submission, last_chat, last_discussion] if isinstance(x, datetime)]
        last_activity = max(activity_candidates) if activity_candidates else None

        # ---------------- PARTICIPATION ----------------
        participation = len(chats) + len(discussions)

        # ---------------- FILTER BY SEARCH ----------------
        if search_query and search_query not in student.username.lower() and search_query not in str(student.id):
            continue

        # ---------------- OVERALL STUDENT PROGRESS ----------------
        total_quiz_progress = sum(quiz_progress.values())
        overall_student_progress = round(total_quiz_progress / len(subjects),2) if subjects else 0

        student_progress.append({
            "id": student.id,
            "username": student.username,
            "quiz_progress": quiz_progress,
            "coding_avg": coding_avg,
            "last_activity": last_activity,
            "participation": participation,
            "overall_student_progress": overall_student_progress
        })

        subject_progress[student.id] = {
            "username": student.username,
            "subjects": quiz_progress
        }

        

   # ---------------- PRACTICAL SUBMISSIONS ----------------

  
        practical_submissions = []
        # get all submissions ordered latest first
        all_subs = PracticalSubmission.query.order_by(
            PracticalSubmission.student_id,
            PracticalSubmission.practical_id,
            desc(PracticalSubmission.submitted_at)
        ).all()

        seen = set()  # to avoid duplicates

        for sub in all_subs:
            key = (sub.student_id, sub.practical_id)

            # skip older duplicate submissions
            if key in seen:
                continue

            seen.add(key)

            student = User.query.get(sub.student_id)
            practical = Practical.query.get(sub.practical_id)

            practical_submissions.append({
                "submission_id": sub.id,
                "student_name": student.username if student else "N/A",
                "practical_title": practical.title if practical else "N/A",
                "marks": sub.marks,
                "status": sub.status,
                # convert UTC → IST for display
                "submitted_at": sub.submitted_at + timedelta(hours=5, minutes=30)
            })







    # ---------------- OVERALL CLASS PROGRESS ----------------
    overall_progress = round(
        sum([s["overall_student_progress"] + s["coding_avg"] for s in student_progress]) / (len(student_progress)*2),2
    ) if student_progress else 0

    # ---------------- TOP 3 STUDENTS ----------------
    top_students = sorted(student_progress, key=lambda s: s["coding_avg"], reverse=True)[:3]

    return render_template(
        "teacher_dashboard.html",
        student_progress=student_progress,
        top_students=top_students,
        subjects=subjects,
        overall_progress=overall_progress,
        subject_progress=subject_progress,
        practical_submissions=practical_submissions
    )

@app.route('/send_poll', methods=['POST'])
def send_poll():
    question = request.form.get('question')
    options = request.form.get('options')
    
    # Here, save the poll to database or send notifications
    # Example: save_poll_to_db(question, options)
    
    flash('Poll sent successfully!', 'success')
    return redirect(url_for('teacher_dashboard'))

#----------------------------
# DELETE PRACTICAL SUBMISSION
#----------------------------
@app.route('/delete_practical/<int:submission_id>', methods=['POST'])
def delete_practical(submission_id):
    submission = PracticalSubmission.query.get_or_404(submission_id)
    
    try:
        db.session.delete(submission)
        db.session.commit()
        flash('Practical submission deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting submission: ' + str(e), 'danger')
    
    return redirect(url_for('teacher_dashboard'))



# ----------------------------
# DELETE OWN ACCOUNT
# ----------------------------
@app.route('/delete_own_account', methods=['POST'])
@login_required
def delete_own_account():
    try:
        db.session.delete(current_user)
        db.session.commit()
        flash("Your account has been deleted.", "success")
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash("Error deleting account: " + str(e), "danger")
        return redirect(url_for('student_dashboard'))


# ----------------------------
# QUIZ HANDLING
# ----------------------------
@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Only teachers can generate quizzes.")
        return redirect(url_for('teacher_dashboard'))

    study_text = request.form.get('material', '').strip()
    subject = request.form.get('subject', '').strip()

    if not study_text or not subject:
        flash("Please provide both subject and study material.")
        return redirect(url_for('teacher_dashboard'))

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a quiz generator. Create 3 MCQs."},
                {"role": "user", "content": f"Generate 3 multiple-choice questions (A,B,C,D) with correct answers "
                                            f"from this study text:\n\n{study_text}\n\n"
                                            "Format JSON like this:\n"
                                            "[{'question':'...','options':['A','B','C','D'],'correct':'A'}]"}
            ],
            max_tokens=500
        )
        quiz_json = response.choices[0].message.content.strip()
        questions = json.loads(quiz_json.replace("'", '"'))
        for q in questions:
            new_quiz = Quiz(
                subject=subject,
                question=q["question"],
                option_a=q["options"][0],
                option_b=q["options"][1],
                option_c=q["options"][2],
                option_d=q["options"][3],
                correct_option=q["correct"]
            )
            db.session.add(new_quiz)
        db.session.commit()
        broadcast_notification("📝 New Quiz Available", f"A new quiz on \"{subject}\" has been added. Go take it!")
        flash("✅ AI-generated quiz successfully created!")
    except Exception as e:
        flash(f"❌ Error generating quiz: {e}")

    return redirect(url_for('teacher_dashboard'))


# ----------------------------
# UPLOAD QUIZ CSV
# ----------------------------
@app.route('/upload_quiz_csv', methods=['GET', 'POST'])
def upload_quiz_csv():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Only teachers can upload quizzes.")
        return redirect(url_for('teacher_dashboard'))
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file:
            flash("No file selected!")
            return redirect(url_for('upload_quiz_csv'))
        try:
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                new_quiz = Quiz(
                    subject=row['subject'].strip(),
                    question=row['question'].strip(),
                    option_a=row['option_a'].strip(),
                    option_b=row['option_b'].strip(),
                    option_c=row['option_c'].strip(),
                    option_d=row['option_d'].strip(),
                    correct_option=row['correct_option'].strip()
                )
                db.session.add(new_quiz)
            db.session.commit()
            broadcast_notification("📝 New Quiz Available", "New quiz questions have been uploaded. Check them out!")
            flash("✅ CSV quizzes uploaded successfully!")
        except Exception as e:
            flash(f"❌ Error uploading CSV: {e}")
        return redirect(url_for('teacher_dashboard'))
    return render_template('upload_quiz.html')


# ----------------------------
# ADD CODING CHALLENGE (manual, by teacher)
# ----------------------------
@app.route('/add_challenge', methods=['GET', 'POST'])
def add_challenge():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Only teachers can add coding challenges.")
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        try:
            new_challenge = CodingChallenge(
                title=request.form.get('title', '').strip(),
                subject=request.form.get('subject', '').strip(),
                language=request.form.get('language', '').strip(),
                difficulty=request.form.get('difficulty', '').strip(),
                description=request.form.get('description', '').strip(),
                input_format=request.form.get('input_format', '').strip(),
                output_format=request.form.get('output_format', '').strip(),
                sample_input=request.form.get('sample_input', '').strip(),
                sample_output=request.form.get('sample_output', '').strip(),
                expected_output=request.form.get('expected_output', '').strip(),
            )
            db.session.add(new_challenge)
            db.session.commit()
            broadcast_notification("💻 New Coding Challenge", f"A new challenge \"{new_challenge.title}\" has been posted.")
            flash("✅ Coding challenge added successfully!")
            return redirect(url_for('teacher_dashboard'))
        except Exception as e:
            flash(f"❌ Error adding challenge: {e}")

    return render_template('add_challenge.html')


# ----------------------------
# ADD STUDY MATERIAL (video / notes / pdf / article, by teacher)
# ----------------------------
@app.route('/add_material', methods=['GET', 'POST'])
def add_material():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Only teachers can add study material.")
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        try:
            new_material = StudyMaterial(
                course=request.form.get('course', '').strip(),
                level=request.form.get('level', '').strip(),
                title=request.form.get('title', '').strip(),
                link=request.form.get('link', '').strip(),
                material_type=request.form.get('material_type', 'video').strip(),
            )
            db.session.add(new_material)
            db.session.commit()
            broadcast_notification("📚 New Study Material", f"New material \"{new_material.title}\" was added for {new_material.course}.")
            flash("✅ Study material added successfully!")
            return redirect(url_for('teacher_dashboard'))
        except Exception as e:
            flash(f"❌ Error adding study material: {e}")

    return render_template('add_material.html')


# ----------------------------
# TAKE QUIZ
# ----------------------------
@app.route('/take_quiz/<topic>', methods=['GET', 'POST'])
def take_quiz(topic):
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Please login as a student to take quizzes.")
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    quizzes = Quiz.query.filter_by(subject=topic).all()
    total_questions = len(quizzes)
    QUIZ_DURATION_MINUTES = 5

    if request.method == 'POST':
        correct_count = sum(1 for quiz in quizzes if request.form.get(str(quiz.id)) == quiz.correct_option)
        percentage_score = int((correct_count / total_questions) * 100) if total_questions else 0
        result = QuizResult.query.filter_by(user_id=user.id, subject=topic).first()
        if result:
            result.score = percentage_score
        else:
            result = QuizResult(user_id=user.id, subject=topic, score=percentage_score)
            db.session.add(result)
        db.session.commit()
        # 🎮 Gamification: quiz reward
        update_gamification(user, earned_points=percentage_score)
        # -------- POINTS FOR QUIZ --------
        if percentage_score >= 80:
            user.points += 30
        elif percentage_score >= 60:
            user.points += 20
        else:
            user.points += 5

        db.session.commit()

        flash(f"✅ Quiz submitted! You scored {percentage_score}%")
        return redirect(url_for('student_dashboard'))

    return render_template('take_quiz.html',
                           questions=quizzes,
                           topic=topic,
                           quiz_duration=QUIZ_DURATION_MINUTES * 60)


# ----------------------------
# CODING CONSOLE and executor
# ----------------------------
@app.route('/coding_console/<topic>', methods=['GET', 'POST'])
def coding_console(topic):
    # Ensure user is logged in and is a student
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    output = None

    if request.method == "POST":
        language = request.form.get('language')
        code = request.form.get('code')
        if language and code:
            output = run_code_executor(language, code)

    return render_template("coding_console.html", topic=topic, output=output)



import subprocess
import tempfile
import os

import requests

def run_code_executor(language, code):
    try:
        lang_map = {
            "python": ("python3", "3"),
            "c": ("c", "5"),
            "cpp": ("cpp17", "0"),
            "java": ("java", "0")
        }

        if language not in lang_map:
            return "Error: Language not supported."

        jdoodle_lang, version = lang_map[language]

        response = requests.post(
            "https://api.jdoodle.com/v1/execute",
            json={
                "clientId": os.getenv("JDOODLE_CLIENT_ID"),
                "clientSecret": os.getenv("JDOODLE_CLIENT_SECRET"),
                "script": code,
                "language": jdoodle_lang,
                "versionIndex": version
            }
        )

        data = response.json()

        return data.get("output", "No output")

    except Exception as e:
        return f"Error: {str(e)}"

# ----------------------------
# SOLVE CHALLENGE
# ----------------------------
@app.route("/solve/<int:challenge_id>", methods=["GET", "POST"])
def solve_challenge(challenge_id):
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Please login as a student to solve challenges.")
        return redirect(url_for('login'))

    challenge = CodingChallenge.query.get_or_404(challenge_id)
    output, score, code = "", None, ""

    if request.method == "POST":
        code = request.form.get("code", "")
        language = request.form.get("language", "python").lower()
        action = request.form.get("action", "run")
        stdin_data = request.form.get("custom_input", "") if action == "run" else (challenge.sample_input or "")

        config = LANG_CONFIG.get(language)
        if not config:
            flash("❌ Unsupported language")
            return redirect(url_for('student_dashboard'))

        import subprocess
        import tempfile
        import os

        try:
            if language == "python":
                with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w") as temp:
                    temp.write(code)
                    temp_path = temp.name

                result = subprocess.run(
                    ["python", temp_path],
                    input=stdin_data,
                    text=True,
                    capture_output=True,
                    timeout=5
                )

                output = result.stdout.strip() if result.stdout else result.stderr.strip()

                os.remove(temp_path)

            else:
                output = "⚠️ Currently only Python execution is supported locally."

        except Exception as e:
            output = f"⚠️ Error executing code: {e}"

        if action == "submit":
            score = 100 if normalize_output(output) == normalize_output(challenge.sample_output) else 0
            submission = Submission(
                student_id=session['user_id'],
                challenge_id=challenge_id,
                code=code,
                language=language,
                output=output,
                score=score
            )
            db.session.add(submission)
            db.session.commit()

            student = db.session.get(User, session['user_id'])
            update_gamification(student, earned_points=score)
            flash(f"✅ Submission saved! Score: {score}%")

    return render_template(
        "solve_challenges.html",
        challenge=challenge,
        output=output,
        score=score,
        code=code,
        custom_input=request.form.get("custom_input", "")
    )




# ----------------------------
# DELETE SUBMISSION
# ----------------------------
@app.route("/delete_submission/<int:submission_id>", methods=["POST"])
def delete_submission(submission_id):
    if "user_id" not in session or session.get("role") != 'student':
        flash("Unauthorized access!")
        return redirect(url_for("login"))
    submission = Submission.query.get_or_404(submission_id)
    if submission.student_id != session["user_id"]:
        flash("You cannot delete this submission.")
        return redirect(url_for("student_dashboard"))
    db.session.delete(submission)
    db.session.commit()
    flash("Submission deleted successfully.")
    return redirect(url_for("student_dashboard"))


#-------------------------
# Online Class
#-------------------------
@app.route('/online_class')
def online_class():
    return render_template('online_class.html')


#--------------------------
# Team Chat
#--------------------------
@app.route('/team_chat', methods=['GET', 'POST'])
def team_chat():
    if 'username' not in session:
        flash("Please log in first!")
        return redirect(url_for('login'))

    if request.method == "POST":
        message_text = request.form.get('message', '').strip()
        if message_text:
            msg = SimpleTeamChat(
                username=session['username'],
                message=message_text,
                timestamp=datetime.utcnow()
            )
            db.session.add(msg)
            db.session.commit()

    return render_template("team_chat.html", current_user=session['username'])

#----------------------------
# Send message via POST
#----------------------------
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return "Not logged in", 403

    message_text = request.form.get('message', '').strip()
    if message_text:
        msg = SimpleTeamChat(
            username=session['username'],
            message=message_text,
            timestamp=datetime.utcnow()
        )
        db.session.add(msg)
        db.session.commit()

    return ('', 204)

#----------------------------
# Fetch messages as JSON
#----------------------------
@app.route('/fetch_messages', methods=['GET'])
def fetch_messages():
    chat = SimpleTeamChat.query.order_by(SimpleTeamChat.timestamp.asc()).all()
    messages = [{
        'username': c.username,
        'message': c.message,
        'timestamp': c.timestamp.strftime("%H:%M")  # hour:minute
    } for c in chat]
    return jsonify(messages)


# ----------------------------
# DISCUSSION
# ----------------------------
@app.route('/discussion', methods=['GET','POST'])
def discussion():
    if request.method == "POST":
        q = SimpleDiscussion(
            username=session.get('username', 'Guest'),
            question=request.form['question']
        )
        db.session.add(q)
        db.session.commit()

    discussions = SimpleDiscussion.query.order_by(SimpleDiscussion.id.desc()).all()
    return render_template("discussion.html", discussions=discussions)


# SocketIO handlers
@socketio.on('send_message')
def handle_send_message(data):
    username = session.get('username', 'Guest')
    message_text = data.get('message', '').strip()
    if message_text:
        msg = SimpleTeamChat(username=username, message=message_text, timestamp=datetime.utcnow())
        db.session.add(msg)
        db.session.commit()
        # Broadcast message to all clients
        emit('receive_message', {
            'username': username,
            'message': message_text,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }, broadcast=True)

@socketio.on('connect')
def handle_connect():
    chat = SimpleTeamChat.query.order_by(SimpleTeamChat.timestamp.asc()).limit(50).all()
    messages = [{
        'username': c.username,
        'message': c.message,
        'timestamp': c.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for c in chat]
    emit('load_messages', messages)


# ----------------------------
# STUDENT PROFILE & HELPERS
# ----------------------------
@app.route("/student/<int:student_id>")
def student_profile(student_id):
    student = User.query.get_or_404(student_id)
    quiz_results = QuizResult.query.filter_by(user_id=student_id).all()
    coding_results = Submission.query.filter_by(student_id=student_id).all()

    # AI Weak Area Analysis
    analysis = analyze_weak_areas(student_id)

    feedbacks = Feedback.query.filter_by(student_id=student_id).all()

    return render_template(
        "student_profile.html",
        student=student,
        quiz_results=quiz_results,
        coding_results=coding_results,
        analysis=analysis,
        feedbacks=feedbacks
    )


@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access!")
        return redirect(url_for('login'))

    teacher_id = session['user_id']
    student_id = request.form.get('student_id')
    message = request.form.get('message')

    feedback = Feedback(
        teacher_id=teacher_id,
        student_id=student_id,
        message=message
    )

    db.session.add(feedback)
    db.session.commit()

    flash("✅ Feedback sent successfully!")
    return redirect(url_for('teacher_dashboard'))


@app.route("/mark_attendance/<int:student_id>", methods=["POST"])
def attendance_mark(student_id):
    today = date.today()

    existing = Attendance.query.filter_by(user_id=student_id, date=today).first()
    if existing:
        flash("Attendance already marked for today!", "warning")
        return redirect(url_for("teacher_dashboard") + "#tabAttendance")

    status = request.form.get("status", "Present")

    attendance = Attendance(
        user_id=student_id,
        date=today,
        status=status,
        note=None
    )
    db.session.add(attendance)
    db.session.commit()

    flash("Attendance marked successfully!", "success")
    return redirect(url_for("teacher_dashboard") + "#tabAttendance")


# ----------------------------
# LEADERBOARD, NOTIFICATIONS, EXPORT
# ----------------------------
@app.route("/leaderboard")
def leaderboard():
    data = []

    students = User.query.filter_by(role="student").all()
    for s in students:
        quiz = QuizResult.query.filter_by(user_id=s.id).all()
        coding = Submission.query.filter_by(student_id=s.id).all()

        quiz_avg = sum([q.score for q in quiz])/len(quiz) if quiz else 0
        coding_avg = sum([c.score for c in coding])/len(coding) if coding else 0

        score = (quiz_avg + coding_avg)/2

        data.append({
            "name": s.username,
            "quiz": quiz_avg,
            "coding": coding_avg,
            "score": score
        })

    data = sorted(data, key=lambda x: x["score"], reverse=True)

    return render_template("leaderboard.html", data=data)


@app.route("/notifications")
def view_notifications():
    if 'user_id' not in session:
        flash("Please login to view notifications.")
        return redirect(url_for('login'))

    uid = session["user_id"]
    notes = Notification.query.filter_by(user_id=uid).order_by(Notification.created_at.desc()).all()

    unseen_ids = [n.id for n in notes if not n.seen]
    if unseen_ids:
        Notification.query.filter(Notification.id.in_(unseen_ids)).update(
            {Notification.seen: True}, synchronize_session=False
        )
        db.session.commit()

    back_endpoint = 'teacher_dashboard' if session.get('role') == 'teacher' else 'student_dashboard'
    return render_template("notifications.html", notes=notes, back_endpoint=back_endpoint)


@app.route('/send_notification', methods=['GET', 'POST'])
def send_notification():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Only teachers can send notifications.")
        return redirect(url_for('teacher_dashboard'))

    students = User.query.filter_by(role='student').order_by(User.username).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        selected_ids = request.form.getlist('student_ids')
        send_to_all = request.form.get('send_to_all') == 'on'

        if not title:
            flash("❌ Please provide a notification title.")
            return render_template('send_notification.html', students=students)

        try:
            if send_to_all or not selected_ids:
                broadcast_notification(title, body, user_ids=None)
            else:
                broadcast_notification(title, body, user_ids=[int(i) for i in selected_ids])
            flash("✅ Notification sent successfully!")
            return redirect(url_for('teacher_dashboard'))
        except Exception as e:
            flash(f"❌ Error sending notification: {e}")

    return render_template('send_notification.html', students=students)


@app.route("/export_csv")
def export_csv():
    students = User.query.filter_by(role="student").all()

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["Name","Quiz Avg","Coding Avg","Overall"])

    for s in students:
        quiz = QuizResult.query.filter_by(user_id=s.id).all()
        coding = Submission.query.filter_by(student_id=s.id).all()

        quiz_avg = sum([q.score for q in quiz])/len(quiz) if quiz else 0
        coding_avg = sum([c.score for c in coding])/len(coding) if coding else 0
        overall = (quiz_avg + coding_avg)/2

        writer.writerow([s.username, quiz_avg, coding_avg, overall])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=students.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# ----------------------------
# STUDENT REPORT (PDF)
# ----------------------------
@app.route("/student_report/<int:student_id>")
def student_report(student_id):
    student = User.query.get_or_404(student_id)
    analysis = analyze_weak_areas(student_id)

    pdf_buffer = io.BytesIO()
    p = canvas.Canvas(pdf_buffer)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Student Report")

    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Name: {student.username}")

    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 750, "Weak Areas:")

    y = 720
    # analysis["progress"] holds subject->score
    for subject, score in analysis["progress"].items():
        p.setFont("Helvetica", 12)
        p.drawString(120, y, f"{subject}: {score}%")
        y -= 20

    p.showPage()
    p.save()

    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        download_name="student_report.pdf",
        as_attachment=True
    )

@app.route("/teacher/attendance")
def teacher_attendance():

    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))

    attendance_records = Attendance.query.order_by(
        Attendance.date.desc()
    ).all()

    attendance_list = []

    for a in attendance_records:
        student = User.query.get(a.user_id)

        attendance_list.append({
            "student_name": student.username if student else "N/A",
            "status": a.status,
            "date": a.date,
            "note": a.note
        })

    return render_template(
        "attendance_records.html",
        attendance_list=attendance_list
    )


@app.route("/teacher/attendance/download")
def download_attendance_csv():

    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))

    import csv
    from io import StringIO
    from flask import Response

    attendance = Attendance.query.order_by(
        Attendance.date.desc()
    ).all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Student Name", "Date", "Status", "Note"])

    for a in attendance:
        student = User.query.get(a.user_id)
        writer.writerow([
            student.username if student else "N/A",
            a.date.strftime('%d-%m-%Y'),
            a.status,
            a.note or ""
        ])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance.csv"}
    )

# ----------------------------
# LOGOUT
# ----------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


# ----------------------------
# ERROR HANDLERS (fixes #10)
# ----------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500
