# 🐳 Guide d'Installation sur UNRAID (Méthode Recommandée)

Ce guide vous explique comment installer LBC Finder sur votre serveur Unraid en quelques minutes.

## 📋 Prérequis
*   Accès aux fichiers de votre serveur Unraid (via SMB/Partage réseau).
*   Accès au terminal de votre serveur Unraid (WebTerminal ou SSH).
*   Le plugin **Docker Compose** installé sur Unraid (Optionnel mais recommandé, sinon via ligne de commande).

---

## 🚀 Étape 1 : Transfert des fichiers

1.  Ouvrez le partage `appdata` de votre Unraid depuis votre ordinateur Windows.
2.  Créez un dossier nommé `lbc-finder`.
3.  **Copiez l'intégralité du contenu de ce dossier de projet** (tous les fichiers : `app.py`, `Dockerfile`, `docker-compose.yml`, le dossier `templates`, etc.) à l'intérieur de ce nouveau dossier `lbc-finder` sur le serveur.

   *Chemin typique sur le serveur :* `/mnt/user/appdata/lbc-finder`

---

## ⚙️ Étape 2 : Configuration

1.  Assurez-vous que le fichier `.env` est bien présent dans le dossier sur le serveur.
2.  Si besoin, éditez-le pour vérifier votre clé API Google :
    `GEMINI_API_KEY=votre_cle_ici`

---


## 🐳 Étape 3 : Lancement (Docker Compose)

Comme le port **5000** est souvent pris, j'ai configuré le port **5090** par défaut.

1.  Ouvrez le **Terminal** de votre Unraid.
2.  Naviguez dans le dossier :
    ```bash
    cd /mnt/user/appdata/lbc-finder
    ```
3.  (Optionnel) Si vous voulez changer le port **5090** :
    *   Éditez le fichier : `nano docker-compose.yml`
    *   Modifiez la ligne `- "5090:5000"` (ne touchez pas à la partie droite `:5000`).
    *   Sauvegardez (`Ctrl+X`, `Y`, `Entrée`).

4.  Lancez l'application :
    ```bash
    docker compose up -d --build
    ```

---

## 🔒 Étape 4 : Configuration Tailscale / Pangolin

Puisque vous utilisez **Tailscale** et **Pangolin** (Reverse Proxy) :

1.  **Dans Pangolin** :
    *   Créez un nouveau **Service** ou **Host**.
    *   **Nom** : `lbc-finder`.
    *   **Scheme** : `http`
    *   **Forward IP** : Mettez l'adresse IP locale de votre serveur Unraid (ex: `192.168.1.50`).
        *   *Note : Ne mettez pas 127.0.0.1 (localhost).*
    *   **Forward Port** : `5090` (ou celui choisi à l'étape 3).
    *   **Public URL** : Votre URL Tailscale (ex: `lbc.votre-tailnet.ts.net`).

2.  **Accès** :
    *   Accédez via votre URL Tailscale depuis n'importe quel appareil connecté à votre VPN.

---

## 🌐 Étape 5 : Vérification locale

Vérifiez que le conteneur tourne bien via l'IP locale :
`http://IP_UNRAID:5090`

---

## 🔄 Mises à jour futures

Si vous modifiez le code ou téléchargez une nouvelle version :
1.  Remplacez les fichiers dans le dossier sur le serveur.
2.  Relancez la commande de build :
    ```bash
    cd /mnt/user/appdata/lbc-finder
    docker compose up -d --build
    ```

## 🛠️ Dépannage (Important)

### ❌ Symptôme : "Aucune annonce" ou Erreur 500
Si vous voyez une **Erreur 500** dans la console (ex: `POST /api/searches 500`) ou aucune image :

1.  **Permissions du dossier** : C'est la cause n°1. Le conteneur ne peut pas écrire dans `leboncoin_ads.db` car il appartient à `root` ou à un autre user.
    ```bash
    # Commande magique à lancer dans le terminal Unraid :
    chmod -R 777 /mnt/user/appdata/lbc-finder
    ```
    *Note: Faites-le sur tout le dossier `lbc-finder` pour être sûr.*

2.  **Redémarrage** :
    ```bash
    cd /mnt/user/appdata/lbc-finder
    docker compose down
    docker compose up -d
    ```

