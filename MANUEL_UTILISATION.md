# 📘 Manuel d'Utilisation - LBC Finder

Bienvenue dans le manuel d'utilisation de **LBC Finder**. Cet outil est conçu pour automatiser la surveillance du site Leboncoin, analyser les annonces grâce à l'intelligence artificielle (IA) et visualiser les résultats via un dashboard moderne.

---

## 📑 Sommaire
1. [Installation](#-installation)
2. [Configuration](#-configuration)
3. [Interface en Ligne de Commande (CLI)](#-interface-en-ligne-de-commande-cli)
4. [Dashboard Web](#-dashboard-web)
5. [Fonctionnalités Avancées](#-fonctionnalités-avancées)
7. [Déploiement (Docker / Unraid)](#-déploiement-docker--unraid)
8. [Maintenance et Base de Données](#-maintenance-et-base-de-données)

---

## 🚀 Installation

### Prérequis
*   **Python 3.9+** installé sur votre système.
*   Une connexion internet.

### Étapes
1.  **Cloner ou télécharger le projet** :
    ```bash
    git clone https://github.com/votre-repo/LBC-test.git
    cd LBC-test
    ```

2.  **Créer un environnement virtuel (recommandé)** :
    ```bash
    python -m venv .venv
    # Sur Windows :
    .venv\Scripts\activate
    # Sur Linux/Mac :
    source .venv/bin/activate
    ```

3.  **Installer les dépendances** :
    ```bash
    pip install -r requirements.txt
    ```

---

## ⚙️ Configuration

LBC Finder utilise l'IA de Google (Gemini) pour résumer les annonces.

1.  Copiez le fichier `.env.example` et renommez-le en `.env`.
2.  Obtenez une clé API gratuite sur [Google AI Studio](https://aistudio.google.com/).
3.  Collez votre clé dans le fichier `.env` :
    ```env
    GEMINI_API_KEY=votre_cle_api_ici
    ```

### 📢 Notifications Discord

Pour recevoir des alertes automatiques (pépites IA et baisses de prix) sur Discord :
1. Créez un **Webhook** sur votre serveur Discord (Paramètres du salon > Intégrations > Webhooks).
2. Dans le Dashboard Web de LBC Finder, allez dans **Paramètres de la veille** (via le Dashboard d'une veille).
3. Collez l'URL de votre Webhook dans le champ **Notification Discord**.
4. Testez la connexion avec le bouton "Tester".

---

## 💻 Interface en Ligne de Commande (CLI)

Le CLI est l'outil principal pour configurer vos veilles et gérer vos annonces.

### Lancement
```bash
python main.py
```

### Options du Menu
1.  **🔍 Recherche rapide** : Effectue une recherche instantanée sur un mot-clé et une ville. Les résultats s'affichent directement sans être sauvegardés en base.
2.  **📡 Lancer une veille active (NLP)** : Configure une surveillance automatique. Vous parlez en langage naturel (ex: *"Je cherche une PS5 à Bordeaux moins de 400€"*). Le programme vérifiera régulièrement les nouvelles annonces.
3.  **📊 Analyse Top 10** : Compare les annonces en base pour un mot-clé par rapport à votre "prix idéal" pour identifier les meilleures affaires.
4.  **🤖 Générer les résumés IA** : Envoie par lot les annonces sans résumé à l'IA pour analyse (points forts, points faibles).
5.  **📂 Consulter vos annonces** : Affiche l'historique complet des annonces trouvées lors de vos veilles.

---

## 📊 Dashboard Web

Pour une expérience visuelle et une gestion simplifiée, utilisez l'interface web.

### Lancement
```bash
python app.py
```
Ouvrez ensuite votre navigateur à l'adresse : `http://127.0.0.1:5000`

### Fonctionnalités
- **Vue d'ensemble** : Statistiques sur vos annonces (total, prix moyen).
- **Gestion des veilles** : Ajoutez ou supprimez des recherches actives directement depuis l'interface.
- **📍 Multi-Localisation** : Saisissez plusieurs zones géographiques (villes avec rayon, départements, régions) pour une même recherche. L'outil regroupera tous les résultats.
- **🔗 Ajout Manuel** : Cliquez sur le bouton "🔗 Ajouter un lien" pour coller une URL Leboncoin. L'application extraira automatiquement le titre, le prix, la photo et la localisation exacte.
- **🗑️ Modération & Archivage** : Masquez les annonces qui ne vous intéressent plus en cliquant sur l'icône poubelle (**🗑️**) sur chaque carte.
- **📦 Actions Groupées** : Sélectionnez plusieurs annonces via le cercle en haut à droite des photos pour faire apparaître la barre d'actions (Tout sélectionner, Masquer la sélection, Comparer).
- **Filtrage** : Filtrez vos annonces par prix, date ou mot-clé.
- **Analyse IA en un clic** : Lancez la génération de résumés via le bouton "🤖 Analyser".
- **Cartographie** (si activée) : Visualisez la localisation des annonces.


---

## ✨ Fonctionnalités Avancées

### Recherche en Langage Naturel (NLP)
Plus besoin de formulaires complexes. L'outil comprend :
- **Lieu** : `"à Paris"`, `"sur Lyon"`, `"autour de Bordeaux"` (avec rayon).
- **Prix** : `"moins de 500€"`, `"entre 10k et 15k"`, `"max 800 euros"`.
- **Exemple** : *"Je veux un vélo électrique vers Nantes budget max 1200€"*

### Analyse de Marché
L'outil calcule automatiquement :
- La moyenne des prix pour une recherche donnée.
- L'écart par rapport à votre prix cible.
- Un indicateur "Bonne Affaire" basé sur l'analyse statistique.

### Résumés IA (Google Gemini)
Chaque annonce peut être analysée pour extraire :
- **Points forts** (ex: Accessoires inclus, bon état).
- **Points faibles** (ex: Rayure sur l'écran, sans facture).
- **Résumé court** pour gagner du temps.

### 🤝 Aide à la Négociation
Sur chaque annonce, un bouton **"🤝 Négocier"** permet à l'IA de générer un message personnalisé pour le vendeur. L'IA analyse les points faibles détectés pour proposer un argumentaire de baisse de prix poli et efficace.

### 📊 Comparateur Expert
Sélectionnez au moins 2 annonces et cliquez sur **"📊 Comparer"** dans la barre flottante. L'IA produira un tableau comparatif détaillé (état, prix, accessoires, localisation) et vous conseillera sur le meilleur choix.

### 📈 Historique des Prix
Si une annonce change de prix au fil de vos scans, l'outil le détecte et affiche un badge **📉 BAISSE**. Cliquez sur **"📈 Historique"** pour voir l'évolution des tarifs.


---

## 🛠️ Maintenance et Base de Données

Les données sont stockées localement dans un fichier SQLite : `leboncoin_ads.db`.

- **Sauvegarde** : Copiez simplement le fichier `.db` ailleurs.
- **Reset** : Supprimez le fichier `.db` (il sera recréé au prochain lancement).
- **Export** : Utilisez un outil comme `DB Browser for SQLite` pour exporter vos annonces en CSV ou Excel.

---

## ⚠️ Avertissement

LBC Finder est un outil expérimental. Veillez à :
- Respecter les conditions d'utilisation de Leboncoin.
- Ne pas lancer des veilles avec des délais trop courts pour éviter les bannissements d'IP.
- Surveiller votre quota d'utilisation de l'API Gemini.
- Si vous recevez une erreur **429 (Quota Exceeded)** : l'outil réessaiera automatiquement avec un délai. Si l'erreur persiste, c'est que votre quota journalier gratuit est épuisé. Attendez le lendemain ou utilisez une autre clé API.

---

## ❓ FAQ / Dépannage

### L'analyse IA échoue avec une erreur 429
C'est une limite fixée par Google sur l'usage gratuit. 
- **Solution 1** : Attendre quelques minutes (l'outil gère désormais les attentes automatiques).
- **Solution 2** : Attendre le lendemain si le quota journalier est atteint.
- **Solution 3** : Vérifier que votre clé API est valide sur [Google AI Studio](https://aistudio.google.com/).

### Pourquoi certaines annonces n'ont pas de résumé ?
Si vous traitez un gros volume (40+ annonces), il est possible que le quota s'épuise en cours de route. L'outil sauvegardera les résumés déjà générés et vous pourrez relancer pour le reste plus tard.

---

## 🐳 Déploiement (Docker / Unraid)

LBC Finder est prêt pour être déployé sur un serveur via Docker, ce qui est idéal pour une utilisation sur **Unraid**, Synology ou un VPS.

### Utilisation de Docker Compose
1.  Assurez-vous d'avoir configuré votre fichier `.env` à la racine.
2.  Lancez la commande : `docker-compose up -d --build`.
3.  **Note Importante** : Si vous modifiez le code, utilisez toujours le flag `--build` pour que vos changements soient pris en compte à l'intérieur du container.
4.  L'application sera accessible sur `http://IP_DU_SERVEUR:5000`.

### Installation sur Unraid
Pour installer LBC Finder sur Unraid, suivez ces étapes :

1.  **Préparation** : Créez un dossier `lbc-finder` dans votre partage `appdata` (ex: `/mnt/user/appdata/lbc-finder`).
2.  **Configuration Docker** :
    *   Allez dans l'onglet **Docker** de votre interface Unraid.
    *   Cliquez sur **Add Container** (tout en bas).
    *   **Name** : `LBC-Finder`
    *   **Repository** : `python:3.10-slim` (ou construisez votre propre image si vous l'hébergez). 
    *   *Note : Il est recommandé de construire l'image localement ou d'utiliser le `docker-compose.yml` fourni via la console SSH.*
3.  **Variables & Chemins (Mappings)** :
    *   **Port** : Host Port `5000` -> Container Port `5000`.
    *   **Volume 1 (Données)** : Host Path `/mnt/user/appdata/lbc-finder/data` -> Container Path `/app/data`.
    *   **Variable ENV** : `GEMINI_API_KEY` = *Votre Clé API*.
    *   **Variable ENV** : `DB_PATH` = `/app/data/leboncoin_ads.db`.

### Persistance
La base de données est stockée dans le dossier mappé `/app/data`. Cela permet de conserver vos annonces et réglages même si vous mettez à jour ou redémarrez le container.

---
*Développé pour simplifier vos recherches sur leboncoin.*
