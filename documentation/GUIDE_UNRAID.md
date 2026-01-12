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

C'est la méthode la plus simple pour construire et lancer l'application avec toutes ses dépendances.

1.  Ouvrez le **Terminal** de votre Unraid (icône `>_` en haut à droite de l'interface Web).
2.  Naviguez dans le dossier de l'application :
    ```bash
    cd /mnt/user/appdata/lbc-finder
    ```
3.  Lancez l'application :
    ```bash
    docker compose up -d --build
    ```
    *(Cette commande va construire l'image Docker locale, ce qui peut prendre 1 à 2 minutes la première fois).*

4.  Vérifiez que tout tourne :
    ```bash
    docker logs -f lbc-finder
    ```
    Vous devriez voir : `Running on http://0.0.0.0:5000`. (Faites `Ctrl+C` pour quitter les logs).

---

## 🌐 Étape 4 : Accès à l'application

Ouvrez votre navigateur web et allez à l'adresse :
`http://IP_DE_VOTRE_UNRAID:5000`

(Exemple : `http://192.168.1.50:5000`)

---

## 🔄 Mises à jour futures

Si vous modifiez le code ou téléchargez une nouvelle version :
1.  Remplacez les fichiers dans le dossier sur le serveur.
2.  Relancez la commande de build :
    ```bash
    cd /mnt/user/appdata/lbc-finder
    docker compose up -d --build
    ```

## 🛠️ Dépannage
*   **Permissions** : Si vous avez des erreurs de base de données ("Read-only file system"), lancez cette commande dans le terminal Unraid sur le dossier data :
    ```bash
    chmod -R 777 /mnt/user/appdata/lbc-finder/data
    ```
