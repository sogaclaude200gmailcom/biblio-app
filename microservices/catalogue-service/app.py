"""
CATALOGUE-SERVICE — Microservice métier
=========================================
Responsabilité : gérer le catalogue de livres et les emprunts/retours.
Ne fait JAMAIS confiance à un identifiant utilisateur transmis tel quel :
il vérifie systématiquement le jeton auprès de auth-service avant toute
action liée à un utilisateur. C'est cette communication inter-services
qui sera chiffrée (TLS/mTLS) dans l'étape suivante du protocole.

Ports : 5002 (interne au réseau Docker)
"""

import os
import requests
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "db")
DB_NAME = os.environ.get("DB_NAME", "bibliotheque")
DB_USER = os.environ.get("DB_USER", "biblio_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "biblio_pass")
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:5001")
CA_CERT_PATH = os.environ.get("CA_CERT_PATH")  # défini uniquement en version chiffrée (TLS)
VERIFY = CA_CERT_PATH if CA_CERT_PATH else True


def get_db():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def verify_token(token):
    """Appel inter-services vers auth-service : c'est CETTE communication
    qui devra être chiffrée pour répondre à l'objectif sécurité du mémoire."""
    if not token:
        return None
    try:
        resp = requests.get(f"{AUTH_SERVICE_URL}/verify", params={"token": token}, timeout=3, verify=VERIFY)
        if resp.status_code == 200 and resp.json().get("valid"):
            return resp.json()
    except requests.RequestException:
        return None
    return None


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "catalogue-service"})


@app.route("/books", methods=["GET"])
def list_books():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM books ORDER BY title")
    books = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(books)


@app.route("/borrow/<int:book_id>", methods=["POST"])
def borrow(book_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Authentification requise."}), 401

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT available_copies FROM books WHERE id = %s", (book_id,))
    book = cur.fetchone()

    if not book or book["available_copies"] <= 0:
        cur.close()
        conn.close()
        return jsonify({"error": "Plus d'exemplaires disponibles."}), 409

    cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = %s", (book_id,))
    cur.execute(
        "INSERT INTO loans (user_id, book_id) VALUES (%s, %s)",
        (user["user_id"], book_id),
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "Livre emprunté avec succès."})


@app.route("/return/<int:loan_id>", methods=["POST"])
def return_book(loan_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Authentification requise."}), 401

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT book_id FROM loans WHERE id = %s AND user_id = %s AND status = 'en_cours'",
        (loan_id, user["user_id"]),
    )
    loan = cur.fetchone()

    if not loan:
        cur.close()
        conn.close()
        return jsonify({"error": "Emprunt introuvable."}), 404

    cur.execute("UPDATE loans SET status = 'rendu', return_date = CURRENT_TIMESTAMP WHERE id = %s", (loan_id,))
    cur.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = %s", (loan["book_id"],))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "Livre rendu, merci."})


@app.route("/loans", methods=["GET"])
def my_loans():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return jsonify({"error": "Authentification requise."}), 401

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT l.id, b.title, b.author,
               TO_CHAR(l.loan_date, 'DD/MM/YYYY') AS loan_date, l.status
        FROM loans l JOIN books b ON l.book_id = b.id
        WHERE l.user_id = %s ORDER BY l.loan_date DESC
        """,
        (user["user_id"],),
    )
    loans = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(loans)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
