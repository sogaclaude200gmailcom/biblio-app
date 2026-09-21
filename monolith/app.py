"""
Bibliothèque en ligne — VERSION MONOLITHIQUE ("avant migration")
==================================================================
Toute l'application (interface, authentification, catalogue, emprunts)
tourne dans un seul processus Python, sans conteneurisation.
C'est le scénario "application directe sur VM" de votre cahier de charges.

Lancement direct (sans Docker) :
    pip install -r requirements.txt
    export DB_HOST=localhost DB_NAME=bibliotheque DB_USER=biblio_user DB_PASSWORD=biblio_pass
    python app.py
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-a-changer")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "bibliotheque")
DB_USER = os.environ.get("DB_USER", "biblio_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "biblio_pass")


def get_db():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


@app.route("/")
def index():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM books ORDER BY title")
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html", books=books)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        email = request.form.get("email", "").strip()

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            flash("Ce nom d'utilisateur existe déjà.")
            cur.close()
            conn.close()
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)",
            (username, password_hash, email),
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Compte créé avec succès, vous pouvez vous connecter.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Bienvenue, {username} !")
            return redirect(url_for("index"))

        flash("Nom d'utilisateur ou mot de passe incorrect.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Vous avez été déconnecté.")
    return redirect(url_for("index"))


@app.route("/borrow/<int:book_id>", methods=["POST"])
def borrow(book_id):
    if "user_id" not in session:
        flash("Connectez-vous pour emprunter un livre.")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT available_copies FROM books WHERE id = %s", (book_id,))
    book = cur.fetchone()

    if book and book["available_copies"] > 0:
        cur.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE id = %s",
            (book_id,),
        )
        cur.execute(
            "INSERT INTO loans (user_id, book_id) VALUES (%s, %s)",
            (session["user_id"], book_id),
        )
        conn.commit()
        flash("Livre emprunté avec succès.")
    else:
        flash("Plus d'exemplaires disponibles pour ce livre.")

    cur.close()
    conn.close()
    return redirect(url_for("index"))


@app.route("/mes-emprunts")
def my_loans():
    if "user_id" not in session:
        flash("Connectez-vous pour voir vos emprunts.")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT l.id, b.title, b.author, l.loan_date, l.status
        FROM loans l
        JOIN books b ON l.book_id = b.id
        WHERE l.user_id = %s
        ORDER BY l.loan_date DESC
        """,
        (session["user_id"],),
    )
    loans = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("mes_emprunts.html", loans=loans)


@app.route("/return/<int:loan_id>", methods=["POST"])
def return_book(loan_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT book_id FROM loans WHERE id = %s AND user_id = %s AND status = 'en_cours'",
        (loan_id, session["user_id"]),
    )
    loan = cur.fetchone()

    if loan:
        cur.execute(
            "UPDATE loans SET status = 'rendu', return_date = CURRENT_TIMESTAMP WHERE id = %s",
            (loan_id,),
        )
        cur.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE id = %s",
            (loan["book_id"],),
        )
        conn.commit()
        flash("Livre rendu, merci !")

    cur.close()
    conn.close()
    return redirect(url_for("my_loans"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
