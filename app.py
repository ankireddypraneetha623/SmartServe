from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "smartserve_secret"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect("smartserve.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Create demo login
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if not user:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", "admin123")
        )

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return redirect("/login")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND password = ?
            """,
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["username"] = username
            return redirect("/dashboard")

        return "Invalid username or password"

    return render_template("login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect("/login")

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    conn = get_db()

    query = "SELECT * FROM requests WHERE 1=1"
    params = []

    # Search
    if search:

        query += """
            AND (
                employee LIKE ?
                OR category LIKE ?
                OR description LIKE ?
            )
        """

        search_value = "%" + search + "%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    # Status filter
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id DESC"

    service_requests = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        requests=service_requests,
        search=search,
        status=status
    )


# ---------------- RAISE REQUEST ----------------

@app.route("/request", methods=["GET", "POST"])
def service_request():

    if "username" not in session:
        return redirect("/login")

    # Show request form
    if request.method == "GET":
        return render_template("request.html")

    # Receive submitted request
    employee = request.form.get("employee", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority", "").strip()

    # Basic validation
    if not employee or not category or not description or not priority:
        return "Please fill all required fields."

    conn = get_db()

    conn.execute(
        """
        INSERT INTO requests
        (employee, category, description, priority, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            employee,
            category,
            description,
            priority,
            "Pending"
        )
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# ---------------- UPDATE STATUS ----------------

@app.route("/update/<int:id>", methods=["POST"])
def update_status(id):

    if "username" not in session:
        return redirect("/login")

    status = request.form.get("status", "").strip()

    allowed_status = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_status:
        return "Invalid status"

    conn = get_db()

    conn.execute(
        """
        UPDATE requests
        SET status = ?
        WHERE id = ?
        """,
        (status, id)
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    create_database()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )