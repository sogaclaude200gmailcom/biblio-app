# Bibliothèque en ligne — Application de test pour le mémoire

Application développée pour servir de cas d'étude représentatif dans le cadre
du mémoire sur la migration vers les microservices conteneurisés (DRSI,
Université de Lomé).

## Structure actuelle

```
biblio-app/
├── db/
│   └── schema.sql          # Schéma partagé (users, books, loans) + données d'exemple
├── monolith/                # VERSION "AVANT MIGRATION"
│   ├── app.py                # Toute l'application en un seul processus Flask
│   ├── requirements.txt
│   ├── templates/             # Pages HTML (Jinja2)
│   └── static/style.css
└── README.md
```

La version microservices ("après migration") sera ajoutée dans un second temps,
en reprenant exactement la même logique métier, éclatée en 3 services distincts
(authentification, catalogue/emprunts, interface web).

## Tester rapidement (avec Docker, juste pour la base de données)

Le plus simple pour tester sur votre VM : gardez PostgreSQL en conteneur (ce n'est
qu'une base de données, ce n'est pas "l'application" au sens de votre étude),
et lancez l'application elle-même directement avec Python — ce qui correspond
exactement à votre scénario "application directe sur VM".

```bash
# 1. Lancer uniquement la base de données
docker run --name biblio-db -e POSTGRES_USER=biblio_user \
  -e POSTGRES_PASSWORD=biblio_pass -e POSTGRES_DB=bibliotheque \
  -p 5432:5432 -d postgres:16

# 2. Charger le schéma (attendre ~5 secondes que Postgres démarre)
sleep 5
PGPASSWORD=biblio_pass psql -h localhost -U biblio_user -d bibliotheque -f db/schema.sql

# 3. Installer les dépendances et lancer l'application (SANS Docker, en direct)
cd monolith
pip install -r requirements.txt
export DB_HOST=localhost DB_NAME=bibliotheque DB_USER=biblio_user DB_PASSWORD=biblio_pass
python3 app.py
```

Puis ouvrez `http://<IP_DE_LA_VM>:5000/` dans votre navigateur.

## Compte de test

Créez votre propre compte via "Créer un compte", ou utilisez celui testé
pendant le développement :
- Utilisateur : `testuser`
- Mot de passe : `motdepasse123`

## Parcours fonctionnel (déjà vérifié)

1. Page d'accueil → affiche le catalogue de 5 livres.
2. Créer un compte → connexion.
3. Emprunter un livre → le compteur d'exemplaires disponibles diminue en base.
4. "Mes emprunts" → affiche le livre emprunté avec le statut "En cours".
5. "Rendre" → le livre redevient disponible.

## Prochaine étape

Découper cette même logique en 3 microservices (auth-service, catalogue-service,
webui-service), chacun dans son propre conteneur Docker, communiquant via API
REST — c'est la version "après migration" à comparer avec celle-ci.
