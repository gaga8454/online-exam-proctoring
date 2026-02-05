from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import os

app = Flask(__name__)
app.secret_key = "exam_proctoring_secret"

# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    return pymysql.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT username, role, status FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "teacher":
                return redirect(url_for("teacher_dashboard"))

            if user["status"] == "approved":
                return redirect(url_for("dashboard"))
            elif user["status"] == "pending":
                return "Your registration is under review."
            else:
                return "Your registration was rejected."

        return "Invalid login"

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (username, password, role, status) VALUES (%s, %s, 'student', 'pending')",
            (username, password)
        )

        conn.commit()
        cur.close()
        conn.close()

        return "Registered successfully. Wait for approval."

    return render_template("register.html")

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" in session and session.get("role") == "student":
        return render_template("dashboard.html")
    return redirect(url_for("login"))

# ---------------- EXAM ----------------
@app.route("/exam")
def exam():
    if "user" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    username = session["user"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT result, reexam_status
        FROM responses
        WHERE username=%s
        ORDER BY id DESC
        LIMIT 1
    """, (username,))
    last_attempt = cur.fetchone()

    cur.close()
    conn.close()

    # Allowed:
    # 1. First attempt
    # 2. Failed and re-exam approved
    if not last_attempt or (
        last_attempt["result"] == "Fail"
        and last_attempt["reexam_status"] == "approved"
    ):
        return render_template("exam.html")

    return "You are not allowed to take the exam at this time."

# ---------------- SUBMIT EXAM ----------------
@app.route("/submit", methods=["POST"])
def submit():
    if "user" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    username = session["user"]

    answer_q1 = request.form.get("q1")
    answer_q2 = request.form.get("q2")
    answer_q3 = request.form.get("q3")
    answer_q4 = request.form.get("q4")
    answer_q5 = request.form.get("q5")

    cheating_count = request.form.get("cheatCount")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO responses
        (username, answer_q1, answer_q2, answer_q3, answer_q4, answer_q5,
         cheating_count, result, reexam_request, reexam_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending', 'No', 'none')
    """, (
        username,
        answer_q1,
        answer_q2,
        answer_q3,
        answer_q4,
        answer_q5,
        cheating_count
    ))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("student_result"))

# ---------------- STUDENT RESULT ----------------
@app.route("/result")
def student_result():
    if "user" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    username = session["user"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT answer_q1, answer_q2, answer_q3, answer_q4, answer_q5,
            cheating_count, result, reexam_request, reexam_status
        FROM responses
        WHERE username=%s
        ORDER BY id DESC
        LIMIT 1
    """, (username,))
    data = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("result.html", data=data)

# ---------------- APPLY FOR RE-EXAM ----------------
@app.route("/apply_reexam")
def apply_reexam():
    if "user" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    username = session["user"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE responses
        SET reexam_request='Yes', reexam_status='pending'
        WHERE username=%s
        ORDER BY id DESC
        LIMIT 1
    """, (username,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("student_result"))

# ---------------- TEACHER DASHBOARD ----------------
@app.route("/teacher")
def teacher_dashboard():
    if "user" not in session or session.get("role") != "teacher":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT username FROM users WHERE role='student' AND status='pending'")
    pending_students = cur.fetchall()

    cur.execute("""
        SELECT username, answer_q1, answer_q2, answer_q3, answer_q4, answer_q5,
            cheating_count, result
        FROM responses
        ORDER BY id DESC
    """)
    responses = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "teacher.html",
        pending_students=pending_students,
        responses=responses
    )

# ---------------- APPROVE / REJECT STUDENT ----------------
@app.route("/approve/<username>")
def approve_student(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE username=%s", (username,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("teacher_dashboard"))

@app.route("/reject/<username>")
def reject_student(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='rejected' WHERE username=%s", (username,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("teacher_dashboard"))

# ---------------- PASS / FAIL ----------------
@app.route("/pass/<username>")
def pass_student(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE responses SET result='Pass'
        WHERE username=%s
        ORDER BY id DESC
        LIMIT 1
    """, (username,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("teacher_dashboard"))

@app.route("/fail/<username>")
def fail_student(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE responses SET result='Fail'
        WHERE username=%s
        ORDER BY id DESC
        LIMIT 1
    """, (username,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("teacher_dashboard"))

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()