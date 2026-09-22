"""
WEBUI-SERVICE — Interface utilisateur
========================================
Sert les pages HTML. Ne se connecte JAMAIS directement à la base de
données : toutes les données passent par des appels REST vers
auth-service et catalogue-service. Le jeton reçu à la connexion est
gardé dans la session Flask (cookie navigateur) et renvoyé à chaque
appel vers catalogue-service.

Ports : 5003 (exposé publiquement, seul point d'entrée du navigateur)
"""

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-a-changer")

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:5001")
CATALOGUE_SERVICE_URL = os.environ.get("CATALOGUE_SERVICE_URL", "http://catalogue-service:5002")
CA_CERT_PATH = os.environ.get("CA_CERT_PATH")  # défini uniquement en version chiffrée (TLS)
VERIFY = CA_CERT_PATH if CA_CERT_PATH else True


def auth_headers():
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


@app.route("/")
def index():
    try:
        resp = requests.get(f"{CATALOGUE_SERVICE_URL}/books", timeout=3, verify=VERIFY)
        books = resp.json()
    except requests.RequestException:
        flash("Le service catalogue est indisponible pour le moment.")
        books = []
    return render_template("index.html", books=books)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        payload = {
            "username": request.form["username"].strip(),
            "password": request.form["password"],
            "email": request.form.get("email", "").strip(),
        }
        resp = requests.post(f"{AUTH_SERVICE_URL}/register", json=payload, timeout=3, verify=VERIFY)
        if resp.status_code == 201:
            flash("Compte créé avec succès, vous pouvez vous connecter.")
            return redirect(url_for("login"))
        flash(resp.json().get("error", "Erreur lors de la création du compte."))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        payload = {
            "username": request.form["username"].strip(),
            "password": request.form["password"],
        }
        resp = requests.post(f"{AUTH_SERVICE_URL}/login", json=payload, timeout=3, verify=VERIFY)
        if resp.status_code == 200:
            data = resp.json()
            session["token"] = data["token"]
            session["username"] = data["username"]
            flash(f"Bienvenue, {data['username']} !")
            return redirect(url_for("index"))
        flash(resp.json().get("error", "Identifiants incorrects."))
    return render_template("login.html")


@app.route("/logout")
def logout():
    token = session.get("token")
    if token:
        try:
            requests.post(f"{AUTH_SERVICE_URL}/logout", json={"token": token}, timeout=3, verify=VERIFY)
        except requests.RequestException:
            pass
    session.clear()
    flash("Vous avez été déconnecté.")
    return redirect(url_for("index"))


@app.route("/borrow/<int:book_id>", methods=["POST"])
def borrow(book_id):
    if "token" not in session:
        flash("Connectez-vous pour emprunter un livre.")
        return redirect(url_for("login"))

    resp = requests.post(f"{CATALOGUE_SERVICE_URL}/borrow/{book_id}", headers=auth_headers(), timeout=3, verify=VERIFY)
    flash(resp.json().get("status") or resp.json().get("error"))
    return redirect(url_for("index"))


@app.route("/mes-emprunts")
def my_loans():
    if "token" not in session:
        flash("Connectez-vous pour voir vos emprunts.")
        return redirect(url_for("login"))

    resp = requests.get(f"{CATALOGUE_SERVICE_URL}/loans", headers=auth_headers(), timeout=3, verify=VERIFY)
    if resp.status_code != 200:
        flash("Impossible de récupérer vos emprunts.")
        return redirect(url_for("index"))
    return render_template("mes_emprunts.html", loans=resp.json())


@app.route("/return/<int:loan_id>", methods=["POST"])
def return_book(loan_id):
    if "token" not in session:
        return redirect(url_for("login"))

    resp = requests.post(f"{CATALOGUE_SERVICE_URL}/return/{loan_id}", headers=auth_headers(), timeout=3, verify=VERIFY)
    flash(resp.json().get("status") or resp.json().get("error"))
    return redirect(url_for("my_loans"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
