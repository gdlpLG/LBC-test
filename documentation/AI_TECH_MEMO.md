# Documentation Technique (Mémo Agent AI)

Ce document sert de rappel sur la structure et la logique interne du programme `lbc-finder` pour les futures sessions de développement.

## Architecture des Dossiers

- `/model` : Contient les dataclasses `Search` et `Parameters`. C'est le contrat d'interface pour définir une recherche.
- `/searcher` : Le moteur d'exécution. Utilise du threading (`searcher.py`) pour gérer plusieurs recherches. `id.py` gère la déduplication via un Set en mémoire (et vérification DB).
- `/documentation` : Ce dossier.

## Flux de Données

1. **Entrée Utilisateur** : Via `main.py`.
   - Si NLP : `nlp.py` parse la chaîne -> convertit en `Parameters`.
   - Si Classique : Paramètres directs.
2. **Exécution** : `Searcher` instancie des threads. Chaque thread boucle avec un `delay`.
3. **Capture** : Le `lbc.Client` récupère les annonces.
4. **Filtrage** : `searcher/id.py` vérifie si l'ID est nouveau.
5. **Callback** : Si nouveau, `config.handle(ad, name)` est appelé.
6. **Persistence** : `database.add_ad` stocke l'ID, titre, prix, url, description et initialise `ai_summary` à `NULL`.
7. **Enrichissement (Post-process)** : L'utilisateur lance manuellement "Générer résumés IA" dans le menu, ce qui appelle `analyzer.generate_batch_summaries` puis met à jour la DB.

## Base de Données (SQLite)

**Fichier** : `leboncoin_ads.db`
**Table** : `searches`
- `name` (PK), `query_text`, `city`, `radius`, `lat`, `lng`, `zip_code`, `locations` (JSON array), `price_min`, `price_max`, `category`, `last_run`, `is_active`, `ai_context`, `refresh_mode`, `refresh_interval`, `platforms`, `last_viewed`.

**Table** : `ads`
- `id` (PK), `search_name`, `title`, `price` (REAL), `location`, `date`, `url` (UNIQUE), `description`, `ai_summary`, `ai_score`, `ai_tips`, `image_url`, `is_pro`, `lat`, `lng`, `category`, `source`.

## Points Critiques & Regex NLP

- Les regex dans `nlp.py` sont sensibles à la langue française.
- `price_max` cherche des patterns comme "moins de X", "budget max X", "jusqu'à X".
- `location` cherche "à X", "sur X", "vers X" suivi d'une Majuscule.

## Simulation IA
Le module `analyzer.py` contient actuellement une simulation. Pour passer en production :
- Remplacer le contenu de `generate_batch_summaries` par un appel `google-generativeai`.
- Conserver le formatage JSON en sortie pour la mise à jour par lot.
