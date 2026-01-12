# Utiliser une image Python légère
FROM python:3.10-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier le fichier des dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . .

# Créer un dossier pour la base de données persistante
RUN mkdir -p /app/data

# Définir les variables d'environnement par défaut
ENV PORT=5000
ENV DB_PATH=/app/data/leboncoin_ads.db
ENV FLASK_DEBUG=False

# Exposer le port
EXPOSE 5000

# Lancer l'application
CMD ["python", "app.py"]
