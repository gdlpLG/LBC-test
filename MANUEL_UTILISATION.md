# 📘 Manuel d'Utilisation - LBC Finder

Bienvenue dans le manuel d'utilisation de **LBC Finder**. Cet outil est conçu pour automatiser la surveillance du site Leboncoin, analyser les annonces grâce à l'intelligence artificielle (IA) et visualiser les résultats via un dashboard moderne.

---

## 📑 Sommaire
1. [Installation](#-installation)
2. [Configuration](#-configuration)
3. [Interface en Ligne de Commande (CLI)](#-interface-en-ligne-de-commande-cli)
4. [Dashboard Web](#-dashboard-web)
5. [Fonctionnalités Avancées](#-fonctionnalités-avancées)
6. [Maintenance et Base de Données](#-maintenance-et-base-de-données)

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
- **Filtrage** : Filtrez vos annonces par prix, date ou mot-clé.
- **Analyse IA en un clic** : Lancez la génération de résumés via le bouton dédié.
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

---
*Développé pour simplifier vos recherches sur leboncoin.*
