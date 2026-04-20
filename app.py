from __future__ import annotations

import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE = "file:mentorlink_runtime?mode=memory&cache=shared"
ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "txt",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "zip",
}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
DEFAULT_MENTORS = [
    {
        "name": "Aarav Mehta",
        "email": "aarav.mehta@mentorlink.com",
        "password": "mentor123",
        "role": "mentor",
        "headline": "Backend mentor for Python and Flask",
        "bio": "Software engineer with experience in Python web applications and backend systems.",
        "skills": "Python, Flask, Web Development, Backend Development",
        "interests": "",
        "goals": "",
        "experience": "6 years building production web systems and mentoring developers.",
        "membership_type": "free",
        "price": 0,
        "membership_description": "Free mentorship access after request approval.",
    },
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@mentorlink.com",
        "password": "mentor123",
        "role": "mentor",
        "headline": "Data science and ML career mentor",
        "bio": "Data science mentor helping students build strong ML foundations and career paths.",
        "skills": "Data Science, Machine Learning, Python, Career Guidance",
        "interests": "",
        "goals": "",
        "experience": "7 years in analytics, ML projects, and student mentoring.",
        "membership_type": "premium",
        "price": 499,
        "membership_description": "Premium mentorship with structured guidance and deeper review sessions.",
    },
    {
        "name": "Rohan Deshmukh",
        "email": "rohan.deshmukh@mentorlink.com",
        "password": "mentor123",
        "role": "mentor",
        "headline": "Frontend and UI/UX mentor",
        "bio": "Frontend and design mentor focused on user-friendly web experiences.",
        "skills": "UI/UX Design, Frontend Development, HTML, CSS, JavaScript",
        "interests": "",
        "goals": "",
        "experience": "5 years building polished frontend products and design systems.",
        "membership_type": "free",
        "price": 0,
        "membership_description": "Free mentorship access after request approval.",
    },
    {
        "name": "Sneha Patil",
        "email": "sneha.patil@mentorlink.com",
        "password": "mentor123",
        "role": "mentor",
        "headline": "Career mentor for resumes and interviews",
        "bio": "Career mentor helping mentees with interview confidence, resumes, and growth planning.",
        "skills": "Resume Building, Interview Preparation, Career Mentoring, Communication Skills",
        "interests": "",
        "goals": "",
        "experience": "8 years helping students prepare for interviews and professional growth.",
        "membership_type": "premium",
        "price": 299,
        "membership_description": "Premium mentorship focused on hands-on preparation and personalized feedback.",
    },
]

app = Flask(__name__)
DB_KEEPER: sqlite3.Connection | None = None
@app.route("/test")
def test():
    return "<h1>Flask is working</h1><p>This is a test page.</p>"

app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, uri=True)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error: Exception | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    global DB_KEEPER
    UPLOAD_DIR.mkdir(exist_ok=True)
    if DB_KEEPER is None:
        DB_KEEPER = sqlite3.connect(DATABASE, uri=True)
        DB_KEEPER.row_factory = sqlite3.Row
    db = DB_KEEPER
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('mentor', 'mentee')),
            headline TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            skills TEXT DEFAULT '',
            interests TEXT DEFAULT '',
            goals TEXT DEFAULT '',
            experience TEXT DEFAULT '',
            membership_type TEXT DEFAULT 'free',
            price INTEGER DEFAULT 0,
            membership_description TEXT DEFAULT '',
            profile_image_path TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            attachment_name TEXT DEFAULT '',
            attachment_path TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        );

        CREATE TABLE IF NOT EXISTS mentor_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentee_id INTEGER NOT NULL,
            mentor_id INTEGER NOT NULL,
            request_message TEXT NOT NULL,
            topic TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'declined')),
            created_at TEXT NOT NULL,
            FOREIGN KEY (mentee_id) REFERENCES users (id),
            FOREIGN KEY (mentor_id) REFERENCES users (id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentee_id INTEGER NOT NULL,
            mentor_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            payment_status TEXT NOT NULL CHECK(payment_status IN ('pending', 'paid')),
            paid_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (mentee_id) REFERENCES users (id),
            FOREIGN KEY (mentor_id) REFERENCES users (id)
        );
        """
    )
    existing_user_columns = {
        row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()
    }
    if "membership_type" not in existing_user_columns:
        db.execute("ALTER TABLE users ADD COLUMN membership_type TEXT DEFAULT 'free'")
    if "price" not in existing_user_columns:
        db.execute("ALTER TABLE users ADD COLUMN price INTEGER DEFAULT 0")
    if "membership_description" not in existing_user_columns:
        db.execute("ALTER TABLE users ADD COLUMN membership_description TEXT DEFAULT ''")
    if "profile_image_path" not in existing_user_columns:
        db.execute("ALTER TABLE users ADD COLUMN profile_image_path TEXT DEFAULT ''")
    existing_columns = {
        row[1] for row in db.execute("PRAGMA table_info(messages)").fetchall()
    }
    if "attachment_name" not in existing_columns:
        db.execute("ALTER TABLE messages ADD COLUMN attachment_name TEXT DEFAULT ''")
    if "attachment_path" not in existing_columns:
        db.execute("ALTER TABLE messages ADD COLUMN attachment_path TEXT DEFAULT ''")
    db.commit()
    seed_default_mentors(db)
    db.commit()
    if db is not DB_KEEPER:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def role_required(role: str):
    def decorator(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                return redirect(url_for("login"))
            if g.user["role"] != role:
                flash("You do not have access to that page.", "error")
                return redirect(url_for("dashboard"))
            return view(**kwargs)

        return wrapped_view

    return decorator


@app.before_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def normalize_tags(raw_value: str) -> set[str]:
    return {
        item.strip().lower()
        for item in raw_value.replace("\n", ",").split(",")
        if item.strip()
    }


def mentor_match_score(mentee: sqlite3.Row, mentor: sqlite3.Row) -> tuple[int, list[str]]:
    mentee_tags = normalize_tags(mentee["interests"]) | normalize_tags(mentee["goals"])
    mentor_tags = normalize_tags(mentor["skills"]) | normalize_tags(mentor["headline"])
    overlap = sorted(mentee_tags & mentor_tags)
    score = len(overlap)
    if mentee["goals"] and mentor["experience"]:
        score += 1
    return score, overlap


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage) -> tuple[str, str] | None:
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    if not filename or not allowed_file(filename):
        return None
    stored_name = f"{uuid4().hex}_{filename}"
    destination = UPLOAD_DIR / stored_name
    file_storage.save(destination)
    return filename, stored_name


def save_profile_image(file_storage) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    if not filename or "." not in filename:
        return None
    extension = filename.rsplit(".", 1)[1].lower()
    if extension not in IMAGE_EXTENSIONS:
        return None
    stored_name = f"profile_{uuid4().hex}_{filename}"
    destination = UPLOAD_DIR / stored_name
    file_storage.save(destination)
    return stored_name


def seed_default_mentors(db: sqlite3.Connection) -> None:
    for mentor in DEFAULT_MENTORS:
        existing_user = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (mentor["email"],),
        ).fetchone()
        if existing_user is not None:
            db.execute(
                """
                UPDATE users
                SET membership_type = ?, price = ?, membership_description = ?
                WHERE email = ?
                """,
                (
                    mentor["membership_type"],
                    mentor["price"],
                    mentor["membership_description"],
                    mentor["email"],
                ),
            )
            continue

        db.execute(
            """
            INSERT INTO users
                (name, email, password_hash, role, headline, bio, skills, interests, goals, experience,
                 membership_type, price, membership_description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mentor["name"],
                mentor["email"],
                generate_password_hash(mentor["password"]),
                mentor["role"],
                mentor["headline"],
                mentor["bio"],
                mentor["skills"],
                mentor["interests"],
                mentor["goals"],
                mentor["experience"],
                mentor["membership_type"],
                mentor["price"],
                mentor["membership_description"],
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )


def conversation_partners(user_id: int) -> list[sqlite3.Row]:
    db = get_db()
    return db.execute(
        """
        SELECT DISTINCT u.*
        FROM users u
        JOIN messages m
            ON (m.sender_id = u.id AND m.receiver_id = ?)
            OR (m.receiver_id = u.id AND m.sender_id = ?)
        ORDER BY u.name
        """,
        (user_id, user_id),
    ).fetchall()


def get_latest_request(mentee_id: int, mentor_id: int):
    return get_db().execute(
        """
        SELECT *
        FROM mentor_requests
        WHERE mentee_id = ? AND mentor_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (mentee_id, mentor_id),
    ).fetchone()


def get_paid_record(mentee_id: int, mentor_id: int):
    return get_db().execute(
        """
        SELECT *
        FROM payments
        WHERE mentee_id = ? AND mentor_id = ? AND payment_status = 'paid'
        ORDER BY id DESC
        LIMIT 1
        """,
        (mentee_id, mentor_id),
    ).fetchone()


def mentor_access_state(mentee_id: int, mentor: sqlite3.Row) -> dict:
    latest_request = get_latest_request(mentee_id, mentor["id"])
    paid_record = get_paid_record(mentee_id, mentor["id"])
    is_premium = mentor["membership_type"] == "premium"
    can_chat = False
    needs_payment = False
    status = "not_requested"
    label = "No Request"

    if latest_request is not None:
        status = latest_request["status"]
        label = latest_request["status"].title()
        if latest_request["status"] == "accepted":
            if is_premium:
                if paid_record is not None:
                    can_chat = True
                    status = "paid"
                    label = "Paid"
                else:
                    needs_payment = True
                    status = "payment_required"
                    label = "Payment Required"
            else:
                can_chat = True
                label = "Accepted"

    return {
        "request": latest_request,
        "payment": paid_record,
        "can_chat": can_chat,
        "needs_payment": needs_payment,
        "is_premium": is_premium,
        "status": status,
        "label": label,
    }


def pair_access_state(user: sqlite3.Row, partner: sqlite3.Row) -> dict:
    if user["role"] == "mentee":
        mentee = user
        mentor = partner
    else:
        mentee = partner
        mentor = user
    state = mentor_access_state(mentee["id"], mentor)
    state["mentee_id"] = mentee["id"]
    state["mentor_id"] = mentor["id"]
    state["mentor"] = mentor
    state["mentee"] = mentee
    return state


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = request.form
        name = form.get("name", "").strip()
        email = form.get("email", "").strip().lower()
        password = form.get("password", "")
        role = form.get("role", "")
        headline = form.get("headline", "").strip()
        bio = form.get("bio", "").strip()
        skills = form.get("skills", "").strip()
        interests = form.get("interests", "").strip()
        goals = form.get("goals", "").strip()
        experience = form.get("experience", "").strip()
        membership_type = form.get("membership_type", "free").strip().lower()
        membership_description = form.get("membership_description", "").strip()
        price_raw = form.get("price", "0").strip()
        profile_image_path = ""
        uploaded_image = request.files.get("profile_image")

        if uploaded_image and uploaded_image.filename:
            profile_image_path = save_profile_image(uploaded_image) or ""
            if not profile_image_path:
                flash("Profile image must be png, jpg, jpeg, gif, or webp.", "error")
                return render_template("register.html")

        if role == "mentor":
            if membership_type not in {"free", "premium"}:
                membership_type = "free"
            try:
                price = max(0, int(price_raw or "0"))
            except ValueError:
                flash("Price must be a valid number.", "error")
                return render_template("register.html")
            if membership_type == "free":
                price = 0
        else:
            membership_type = "free"
            price = 0
            membership_description = ""

        if not name or not email or not password or role not in {"mentor", "mentee"}:
            flash("Name, email, password, and role are required.", "error")
            return render_template("register.html")

        db = get_db()
        try:
            db.execute(
                """
                INSERT INTO users
                    (name, email, password_hash, role, headline, bio, skills, interests, goals, experience,
                     membership_type, price, membership_description, profile_image_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password),
                    role,
                    headline,
                    bio,
                    skills,
                    interests,
                    goals,
                    experience,
                    membership_type,
                    price,
                    membership_description,
                    profile_image_path,
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
            return render_template("register.html")

        flash("Account created. You can log in now.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    if g.user["role"] == "mentee":
        return redirect(url_for("mentee_dashboard"))
    return redirect(url_for("mentor_dashboard"))


@app.route("/dashboard/mentee")
@login_required
@role_required("mentee")
def mentee_dashboard():
    db = get_db()
    mentors = db.execute("SELECT * FROM users WHERE role = 'mentor' ORDER BY name").fetchall()
    ranked_mentors = []
    for mentor in mentors:
        score, overlap = mentor_match_score(g.user, mentor)
        ranked_mentors.append(
            {
                "mentor": mentor,
                "score": score,
                "overlap": overlap,
                "access": mentor_access_state(g.user["id"], mentor),
            }
        )

    ranked_mentors.sort(key=lambda item: (-item["score"], item["mentor"]["name"].lower()))
    conversations = conversation_partners(g.user["id"])
    sent_requests = db.execute(
        """
        SELECT r.*, u.name AS mentor_name
        FROM mentor_requests r
        JOIN users u ON u.id = r.mentor_id
        WHERE r.mentee_id = ?
        ORDER BY r.id DESC
        """,
        (g.user["id"],),
    ).fetchall()
    return render_template(
        "dashboard_mentee.html",
        recommendations=ranked_mentors,
        conversations=conversations,
        sent_requests=sent_requests,
    )


@app.route("/dashboard/mentor")
@login_required
@role_required("mentor")
def mentor_dashboard():
    db = get_db()
    mentees = db.execute(
        """
        SELECT DISTINCT u.*
        FROM users u
        JOIN messages m
            ON (m.sender_id = u.id AND m.receiver_id = ?)
            OR (m.receiver_id = u.id AND m.sender_id = ?)
        WHERE u.role = 'mentee'
        ORDER BY u.name
        """,
        (g.user["id"], g.user["id"]),
    ).fetchall()
    total_messages = db.execute(
        "SELECT COUNT(*) AS count FROM messages WHERE sender_id = ? OR receiver_id = ?",
        (g.user["id"], g.user["id"]),
    ).fetchone()["count"]
    pending_requests = db.execute(
        """
        SELECT r.*, u.name AS mentee_name, u.email AS mentee_email, u.goals AS mentee_goals
        FROM mentor_requests r
        JOIN users u ON u.id = r.mentee_id
        WHERE r.mentor_id = ? AND r.status = 'pending'
        ORDER BY r.id DESC
        """,
        (g.user["id"],),
    ).fetchall()
    accepted_requests = db.execute(
        """
        SELECT r.*, u.name AS mentee_name, u.email AS mentee_email, p.payment_status, p.paid_at
        FROM mentor_requests r
        JOIN users u ON u.id = r.mentee_id
        LEFT JOIN payments p
            ON p.mentee_id = r.mentee_id AND p.mentor_id = r.mentor_id AND p.payment_status = 'paid'
        WHERE r.mentor_id = ? AND r.status = 'accepted'
        ORDER BY r.id DESC
        """,
        (g.user["id"],),
    ).fetchall()
    declined_requests = db.execute(
        """
        SELECT r.*, u.name AS mentee_name, u.email AS mentee_email
        FROM mentor_requests r
        JOIN users u ON u.id = r.mentee_id
        WHERE r.mentor_id = ? AND r.status = 'declined'
        ORDER BY r.id DESC
        """,
        (g.user["id"],),
    ).fetchall()
    return render_template(
        "dashboard_mentor.html",
        mentees=mentees,
        total_messages=total_messages,
        pending_requests=pending_requests,
        accepted_requests=accepted_requests,
        declined_requests=declined_requests,
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        form = request.form
        membership_type = g.user["membership_type"]
        membership_description = g.user["membership_description"]
        price = g.user["price"]
        profile_image_path = g.user["profile_image_path"]

        if g.user["role"] == "mentor":
            membership_type = form.get("membership_type", "free").strip().lower()
            membership_description = form.get("membership_description", "").strip()
            price_raw = form.get("price", "0").strip()
            if membership_type not in {"free", "premium"}:
                membership_type = "free"
            try:
                price = max(0, int(price_raw or "0"))
            except ValueError:
                flash("Price must be a valid number.", "error")
                return redirect(url_for("profile"))
            if membership_type == "free":
                price = 0
        uploaded_image = request.files.get("profile_image")
        if uploaded_image and uploaded_image.filename:
            new_image = save_profile_image(uploaded_image)
            if not new_image:
                flash("Profile image must be png, jpg, jpeg, gif, or webp.", "error")
                return redirect(url_for("profile"))
            profile_image_path = new_image

        get_db().execute(
            """
            UPDATE users
            SET name = ?, headline = ?, bio = ?, skills = ?, interests = ?, goals = ?, experience = ?,
                membership_type = ?, price = ?, membership_description = ?, profile_image_path = ?
            WHERE id = ?
            """,
            (
                form.get("name", "").strip(),
                form.get("headline", "").strip(),
                form.get("bio", "").strip(),
                form.get("skills", "").strip(),
                form.get("interests", "").strip(),
                form.get("goals", "").strip(),
                form.get("experience", "").strip(),
                membership_type,
                price,
                membership_description,
                profile_image_path,
                g.user["id"],
            ),
        )
        get_db().commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html")


@app.route("/requests/<int:mentor_id>/send", methods=["POST"])
@login_required
@role_required("mentee")
def send_request(mentor_id: int):
    db = get_db()
    mentor = db.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'mentor'",
        (mentor_id,),
    ).fetchone()
    if mentor is None:
        flash("Mentor not found.", "error")
        return redirect(url_for("mentee_dashboard"))

    topic = request.form.get("topic", "").strip()
    request_message = request.form.get("request_message", "").strip()
    latest_request = get_latest_request(g.user["id"], mentor_id)
    if latest_request is not None and latest_request["status"] in {"pending", "accepted"}:
        flash("You already have an active mentorship request for this mentor.", "error")
        return redirect(url_for("mentee_dashboard"))
    if not topic or not request_message:
        flash("Topic and request message are required.", "error")
        return redirect(url_for("mentee_dashboard"))

    db.execute(
        """
        INSERT INTO mentor_requests (mentee_id, mentor_id, request_message, topic, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
        """,
        (
            g.user["id"],
            mentor_id,
            request_message,
            topic,
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    flash("Mentorship request sent.", "success")
    return redirect(url_for("mentee_dashboard"))


@app.route("/requests/<int:request_id>/accept", methods=["POST"])
@login_required
@role_required("mentor")
def accept_request(request_id: int):
    db = get_db()
    mentor_request = db.execute(
        "SELECT * FROM mentor_requests WHERE id = ? AND mentor_id = ?",
        (request_id, g.user["id"]),
    ).fetchone()
    if mentor_request is None:
        flash("Request not found.", "error")
        return redirect(url_for("mentor_dashboard"))

    db.execute(
        "UPDATE mentor_requests SET status = 'accepted' WHERE id = ?",
        (request_id,),
    )
    db.commit()
    flash("Request accepted.", "success")
    return redirect(url_for("mentor_dashboard"))


@app.route("/requests/<int:request_id>/decline", methods=["POST"])
@login_required
@role_required("mentor")
def decline_request(request_id: int):
    db = get_db()
    mentor_request = db.execute(
        "SELECT * FROM mentor_requests WHERE id = ? AND mentor_id = ?",
        (request_id, g.user["id"]),
    ).fetchone()
    if mentor_request is None:
        flash("Request not found.", "error")
        return redirect(url_for("mentor_dashboard"))

    db.execute(
        "UPDATE mentor_requests SET status = 'declined' WHERE id = ?",
        (request_id,),
    )
    db.commit()
    flash("Request declined.", "success")
    return redirect(url_for("mentor_dashboard"))


@app.route("/payment/<int:mentor_id>", methods=["GET", "POST"])
@login_required
@role_required("mentee")
def payment(mentor_id: int):
    db = get_db()
    mentor = db.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'mentor'",
        (mentor_id,),
    ).fetchone()
    if mentor is None:
        flash("Mentor not found.", "error")
        return redirect(url_for("mentee_dashboard"))

    access = mentor_access_state(g.user["id"], mentor)
    if not access["request"] or access["request"]["status"] != "accepted":
        flash("You need mentor approval before payment.", "error")
        return redirect(url_for("mentee_dashboard"))
    if mentor["membership_type"] != "premium":
        flash("This mentor does not require payment.", "error")
        return redirect(url_for("chat", partner_id=mentor_id))
    if access["payment"]:
        flash("Payment already completed. Chat is unlocked.", "success")
        return redirect(url_for("chat", partner_id=mentor_id))

    if request.method == "POST":
        cardholder_name = request.form.get("cardholder_name", "").strip()
        card_number = request.form.get("card_number", "").strip()
        expiry = request.form.get("expiry", "").strip()
        cvv = request.form.get("cvv", "").strip()
        upi_id = request.form.get("upi_id", "").strip()
        if not cardholder_name and not upi_id:
            flash("Enter cardholder name or UPI ID to continue.", "error")
            return render_template("payment.html", mentor=mentor)
        if not upi_id and (not card_number or not expiry or not cvv):
            flash("Complete the mock payment form.", "error")
            return render_template("payment.html", mentor=mentor)

        db.execute(
            """
            INSERT INTO payments (mentee_id, mentor_id, amount, payment_status, paid_at, created_at)
            VALUES (?, ?, ?, 'paid', ?, ?)
            """,
            (
                g.user["id"],
                mentor_id,
                mentor["price"],
                datetime.utcnow().isoformat(timespec="seconds"),
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        db.commit()
        flash("Mock payment successful. Chat unlocked.", "success")
        return redirect(url_for("chat", partner_id=mentor_id))

    return render_template("payment.html", mentor=mentor)


@app.route("/chat/<int:partner_id>", methods=["GET", "POST"])
@login_required
def chat(partner_id: int):
    db = get_db()
    partner = db.execute("SELECT * FROM users WHERE id = ?", (partner_id,)).fetchone()
    if partner is None or partner["id"] == g.user["id"]:
        flash("Conversation not available.", "error")
        return redirect(url_for("dashboard"))
    if partner["role"] == g.user["role"]:
        flash("Chats are only available between mentors and mentees.", "error")
        return redirect(url_for("dashboard"))
    access = pair_access_state(g.user, partner)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        attachment = request.files.get("attachment")
        saved_attachment = None
        if attachment and attachment.filename:
            saved_attachment = save_uploaded_file(attachment)
            if saved_attachment is None:
                flash("Unsupported file type. Allowed: pdf, doc, docx, txt, images, zip.", "error")
                return redirect(url_for("chat", partner_id=partner_id))
        if not access["can_chat"]:
            flash("Chat is locked until the mentorship request flow is completed.", "error")
            return redirect(url_for("chat", partner_id=partner_id))
        if body or saved_attachment:
            db.execute(
                """
                INSERT INTO messages (sender_id, receiver_id, body, attachment_name, attachment_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    g.user["id"],
                    partner["id"],
                    body,
                    saved_attachment[0] if saved_attachment else "",
                    saved_attachment[1] if saved_attachment else "",
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
            db.commit()
            return redirect(url_for("chat", partner_id=partner_id))
        flash("Add a message or attach a file before sending.", "error")

    messages = db.execute(
        """
        SELECT *
        FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at
        """,
        (g.user["id"], partner["id"], partner["id"], g.user["id"]),
    ).fetchall()
    return render_template("chat.html", partner=partner, messages=messages, access=access)


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename: str):
    message = get_db().execute(
        """
        SELECT *
        FROM messages
        WHERE attachment_path = ?
          AND (sender_id = ? OR receiver_id = ?)
        LIMIT 1
        """,
        (filename, g.user["id"], g.user["id"]),
    ).fetchone()
    if message is None:
        flash("File not available.", "error")
        return redirect(url_for("dashboard"))
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


@app.route("/media/profile/<path:filename>")
def profile_media(filename: str):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)


@app.errorhandler(404)
def not_found(_error):
    routes = sorted(
        rule.rule for rule in app.url_map.iter_rules() if not rule.rule.startswith("/static/")
    )
    return (
        "<h1>Page not found</h1>"
        "<p>You reached the Flask app, but this URL does not exist.</p>"
        "<p>Try one of these:</p>"
        "<ul>"
        + "".join(f"<li><a href='{route}'>{route}</a></li>" for route in routes)
        + "</ul>",
        404,
    )


init_db()


if __name__ == "__main__":
    print("Available routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        print(f"  {rule.rule}")
    app.run(host="127.0.0.1", port=5055, debug=False, use_reloader=False)
