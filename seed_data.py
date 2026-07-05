"""
Seed script — run this ONCE after init_db.py to fill the database
with sample Quiz questions, Coding Challenges, and Practicals.

Why this is needed:
  init_db.py only creates empty tables. Nothing in app.py ever inserts
  rows into Quiz / CodingChallenge / Practical, so the student dashboard's
  "Topics & Quiz", "Challenges", and "Practicals" sections have nothing
  to loop over and show up blank.

Usage:
  python seed_data.py
"""
from app import app
from models import db, Quiz, CodingChallenge, Practical

SUBJECTS = ["Python", "Java", "C", "C++"]

quiz_questions = [
    # Python
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

    # Java
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

    # C
    dict(subject="C", question="Which header file is required for printf()?",
         option_a="stdlib.h", option_b="stdio.h", option_c="string.h", option_d="conio.h", correct_option="B"),
    dict(subject="C", question="What is the size of an int on most systems (bytes)?",
         option_a="2", option_b="4", option_c="8", option_d="1", correct_option="B"),
    dict(subject="C", question="Which operator is used to access a value at an address in a pointer?",
         option_a="&", option_b="*", option_c="%", option_d="#",
         correct_option="B"),
    dict(subject="C", question="Which loop checks the condition after executing the body?",
         option_a="for", option_b="while", option_c="do-while", option_d="if", correct_option="C"),
    dict(subject="C", question="Which function allocates memory dynamically in C?",
         option_a="malloc()", option_b="alloc()", option_c="new()", option_d="calloc_mem()", correct_option="A"),

    # C++
    dict(subject="C++", question="Which keyword defines a class in C++?",
         option_a="class", option_b="struct", option_c="object", option_d="define", correct_option="A"),
    dict(subject="C++", question="Which operator is used for dynamic memory allocation in C++?",
         option_a="malloc", option_b="new", option_c="alloc", option_d="create",
         correct_option="B"),
    dict(subject="C++", question="Which of these supports OOP feature 'Inheritance'?",
         option_a="C", option_b="C++", option_c="Assembly", option_d="Machine Code", correct_option="B"),
    dict(subject="C++", question="Which symbol is used for scope resolution in C++?",
         option_a="::", option_b="->", option_c=".", option_d=":",
         correct_option="A"),
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
         co="CO1", llo="Understand pointers and arrays", task="Write a C program to find the largest element in an array."),
]

with app.app_context():
    added = {"quiz": 0, "challenges": 0, "practicals": 0}

    for q in quiz_questions:
        exists = Quiz.query.filter_by(subject=q["subject"], question=q["question"]).first()
        if not exists:
            db.session.add(Quiz(**q))
            added["quiz"] += 1

    for c in coding_challenges:
        exists = CodingChallenge.query.filter_by(title=c["title"]).first()
        if not exists:
            db.session.add(CodingChallenge(**c))
            added["challenges"] += 1

    for p in practicals:
        exists = Practical.query.filter_by(subject=p["subject"], practical_no=p["practical_no"]).first()
        if not exists:
            db.session.add(Practical(**p))
            added["practicals"] += 1

    db.session.commit()
    print(f"Seed complete: {added['quiz']} quiz questions, "
          f"{added['challenges']} coding challenges, "
          f"{added['practicals']} practicals added.")
