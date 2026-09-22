"""
AUTH-SERVICE — Microservice d'authentification
================================================
Responsabilité unique : gérer les comptes utilisateurs et les jetons de
session. Les autres services (catalogue-service, webui-service) lui
délèguent toute vérification d'identité via des appels REST.

Ports : 5001 (interne au réseau Docker)
"""

import os
import uuid
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "db")
DB_NAME = os.environ.get("DB_NAME", "bibliotheque")
DB_USER = os.environ.get("DB_USER", "biblio_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "biblio_pass")


def get_db():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "auth-service"})


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()

    if not username or not password:
        return jsonify({"error": "username et password requis"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Ce nom d'utilisateur existe déjà."}), 409

    password_hash = generate_password_hash(password)
    cur.execute(
        "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s) RETURNING id",
        (username, password_hash, email),
    )
    user_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": user_id, "username": username}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        cur.close()
        conn.close()
        return jsonify({"error": "Identifiants incorrects."}), 401

    token = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO tokens (token, user_id) VALUES (%s, %s)",
        (token, user["id"]),
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"token": token, "user_id": user["id"], "username": user["username"]})


@app.route("/verify", methods=["GET"])
def verify():
    """Appelé par les autres services pour valider un jeton et récupérer l'utilisateur associé."""
    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "token manquant"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.id AS user_id, u.username
        FROM tokens t JOIN users u ON t.user_id = u.id
        WHERE t.token = %s
        """,
        (token,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"valid": False}), 401

    return jsonify({"valid": True, "user_id": row["user_id"], "username": row["username"]})


@app.route("/logout", methods=["POST"])
def logout():
    data = request.get_json(force=True)
    token = data.get("token", "")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tokens WHERE token = %s", (token,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "déconnecté"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
