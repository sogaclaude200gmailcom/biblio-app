#!/bin/bash
# Génère une autorité de certification (CA) auto-signée et un certificat
# serveur pour Traefik, utilisés pour chiffrer les communications entre
# microservices (auth-service, catalogue-service, webui-service).
set -e
cd "$(dirname "$0")"

echo "1) Génération de l'autorité de certification (CA)..."
openssl genrsa -out ca.key 4096 2>/dev/null
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -subj "/C=TG/O=Memoire-DRSI/CN=Biblio-App-CA" \
  -out ca.crt

echo "2) Génération du certificat serveur (Traefik), valable pour tous les services internes..."
cat > server.ext <<EOF
subjectAltName = DNS:traefik,DNS:webui-service,DNS:auth-service,DNS:catalogue-service,DNS:localhost,IP:127.0.0.1
EOF

openssl genrsa -out server.key 2048 2>/dev/null
openssl req -new -key server.key \
  -subj "/C=TG/O=Memoire-DRSI/CN=traefik" \
  -out server.csr

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 -extfile server.ext 2>/dev/null

rm -f server.csr server.ext
echo "Terminé."
echo " - ca.crt          : à distribuer aux services pour qu'ils vérifient le certificat Traefik"
echo " - server.crt/.key : utilisés par Traefik pour chiffrer le trafic"
