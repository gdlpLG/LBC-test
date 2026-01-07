# Guide d'Utilisation - LBC Finder

Bienvenue dans la documentation utilisateur de **LBC Finder**. Cet outil vous permet de ne rater aucune bonne affaire sur Leboncoin en automatisant vos recherches.

## 🚀 Démarrage Rapide

1. Installez les dépendances : `pip install -r requirements.txt`
2. Lancez le programme : `python main.py`
3. Choisissez une option dans le menu.

## 📋 Fonctionnalités du Menu

### 1. Recherche Rapide
Effectuez une recherche instantanée sans mise en veille. Utile pour vérifier si des objets sont actuellement disponibles.

### 2. Lancer une Veille (NLP)
C'est la fonction la plus puissante. Vous tapez ce que vous cherchez comme si vous parliez à un ami.
*   **Exemple** : *"Je cherche une Porsche 911 sur Paris budget max 80000€"*
*   Le programme va extraire :
    *   **Quoi** : Porsche 911
    *   **Où** : Paris
    *   **Prix** : Max 80 000€
*   La veille tourne en arrière-plan avec des pauses aléatoires pour rester discret vis-à-vis du site.

### 3. Analyser (Top 10)
Analyse les annonces sauvegardées pour un mot-clé donné et compare le prix par rapport à votre "prix idéal" pour trouver les meilleures opportunités.

### 4. Générer résumés IA
Analyse les nouvelles annonces trouvées lors des veilles. L'IA parcourt les descriptions pour vous extraire :
*   Les points forts.
*   Les points faibles (défauts signalés).
*   Les équipements clés.

### 5. Consulter les annonces
Affiche l'historique de toutes les annonces trouvées par vos veilles, avec leurs résumés si vous les avez générés.

## 💡 Astuces pour la Recherche Naturelle (NLP)

Pour que l'outil comprenne bien votre demande, essayez d'utiliser des mots-clés clairs :
- **Lieu** : Utilisez "à", "sur" ou "vers" (ex: "à Lyon", "sur Nantes").
- **Prix** : Utilisez "entre X et Y euros", "moins de X euros", "maximum X€".
- **K suffixe** : Le programme comprend que "15k" signifie 15 000€.

## 🛠️ Maintenance

Les annonces sont stockées dans le fichier `leboncoin_ads.db`. Vous pouvez l'ouvrir avec n'importe quel lecteur SQLite pour exporter vos données.
