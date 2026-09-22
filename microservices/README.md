# Bibliothèque en ligne — Version microservices ("après migration")

Même logique métier que le monolithe, éclatée en 3 services indépendants :

```
microservices/
├── auth-service/         # Port 5001 — comptes utilisateurs, jetons de session
├── catalogue-service/    # Port 5002 — livres, emprunts, retours
├── webui-service/        # Port 5003 — interface web, seul point exposé
└── docker-compose.yml    # Orchestre les 3 services + PostgreSQL
```

## Qui parle à qui

- Le navigateur ne parle qu'à **webui-service**.
- **webui-service** appelle **auth-service** (login/register) et **catalogue-service**
  (livres/emprunts) via des requêtes HTTP/JSON.
- **catalogue-service** appelle **auth-service** pour vérifier le jeton avant
  chaque emprunt/retour — c'est cette communication inter-services qui devra
  être chiffrée (TLS/mTLS via Traefik) à l'étape suivante du protocole.
- Seuls **auth-service** et **catalogue-service** parlent à la base de données ;
  **webui-service** ne s'y connecte jamais directement.

## Déploiement sur la VM (avec Docker déjà installé)

```bash
cd biblio-app/microservices
docker compose up -d --build
```

Ça construit et lance automatiquement les 4 conteneurs (db, auth-service,
catalogue-service, webui-service). Vérifiez que tout tourne :

```bash
docker compose ps
```

L'application est accessible sur le port **8000** (et non 5000/5003) :
```
http://<IP_DE_LA_VM>:8000/
```

## Pour tout arrêter / nettoyer

```bash
docker compose down -v
```

(le `-v` supprime aussi les données de la base, pratique pour repartir propre
entre deux séries de tests).

## Vérifié avant livraison

Le parcours complet a été testé service par service (inscription → connexion
→ affichage du catalogue → emprunt → vérification du jeton entre catalogue-service
et auth-service → historique des emprunts → mise à jour réelle en base de
données). Tout fonctionne correctement.

## Prochaine étape

Ajouter Traefik en reverse proxy devant les 3 services avec des certificats
TLS/mTLS générés via OpenSSL, pour chiffrer les communications inter-services
et mesurer le coût CPU de ce chiffrement (objectif 3.2 du cahier de charges).

---

## Chiffrement TLS des communications inter-services (Traefik)

```
microservices/
├── certs/
│   ├── generate-certs.sh   # génère la CA + le certificat serveur
│   ├── ca.crt              # autorité de certification (déjà générée)
│   └── server.crt/.key     # certificat utilisé par Traefik
├── traefik/dynamic/config.yml   # routes chiffrées vers chaque service
└── docker-compose.tls.yml       # à ajouter au déploiement pour activer le TLS
```

**Comment ça marche** : Traefik s'intercale devant chaque service interne
(`auth-service`, `catalogue-service`, `webui-service`) et termine le TLS.
`catalogue-service` et `webui-service` appellent alors leurs collègues en
HTTPS à travers Traefik plutôt qu'en HTTP direct — c'est ce détour qui
chiffre le trafic entre microservices.

### Déployer SANS chiffrement (baseline)
```bash
docker compose up -d --build
```

### Déployer AVEC chiffrement (à comparer)
```bash
docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build
```

Accès à l'interface web chiffrée : `https://<IP_DE_LA_VM>:8443/`
(certificat auto-signé : votre navigateur affichera un avertissement, c'est
normal — cliquez sur "Avancé" puis "Continuer", ou importez `certs/ca.crt`
comme autorité de confiance si vous préférez éviter l'avertissement).

Si `docker compose` (sans tiret) ne fonctionne pas sur votre VM, essayez
`docker-compose` (avec tiret) — installez-le si besoin avec
`apt install docker-compose -y`, la syntaxe des commandes reste identique.

### Régénérer les certificats si besoin
```bash
cd certs && ./generate-certs.sh
```

### Mesurer le coût CPU du chiffrement (objectif 3.2)

Le principe : lancer la même série d'actions (emprunts, consultations) sur
les deux déploiements (avec/sans `docker-compose.tls.yml`), et comparer avec
les outils déjà prévus en section 6.2 :

- **Sysbench / `docker stats`** : consommation CPU des conteneurs `catalogue-service`
  et `webui-service` pendant une charge identique, avec puis sans TLS.
- **iPerf3** ou de simples requêtes `curl -w "%{time_total}\n"` répétées :
  comparer la latence moyenne des appels inter-services dans les deux cas.
- **Prometheus/Grafana** : si déjà branché, comparer les graphes de charge
  CPU des deux déploiements sur une fenêtre de temps équivalente.

La différence observée entre les deux séries de mesures constitue directement
le résultat attendu pour cet objectif.

