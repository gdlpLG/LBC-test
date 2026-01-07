# LBC Finder V5 🚀
[![GitHub license](https://img.shields.io/github/license/etienne-hd/lbc?style=for-the-badge)](https://github.com/etienne-hd/lbc/blob/master/LICENSE)

**Restez informé en temps réel des nouvelles annonces Leboncoin avec Analyse IA et Recherche Naturelle.**

LBC Finder automatise la surveillance du site Leboncoin. Contrairement aux alertes classiques, il permet de filtrer intelligemment les résultats et de générer des résumés automatiques via IA pour gagner du temps.

## ✨ Caractéristiques principales

*   **🔍 Recherche en Langage Naturel (NLP)** : Plus besoin de remplir des formulaires complexes. Tapez simplement : *"Je cherche un vélo électrique à Bordeaux moins de 1000€"*.
*   **🤖 Analyse IA & Résumés** : L'IA parcourt les descriptions pour vous (points forts, points faibles, caractéristiques clés).
*   **📂 Base de Données SQLite** : Toutes les annonces trouvées sont sauvegardées localement pour historique et analyse.
*   **🕵️ Mode Discret** : Délais aléatoires et gestion des agents utilisateurs pour éviter les blocages.
*   **📈 Analyse de Prix** : Comparez les offres par rapport à votre prix idéal.

## 🛠️ Installation

1.  **Prérequis** : Python 3.9+
2.  **Clonage et installation** :
    ```bash
    git clone https://github.com/etienne-hd/lbc-finder.git
    cd lbc-finder
    pip install -r requirements.txt
    ```

### Dashboard Web 📊
Pour une expérience visuelle premium, lancez le dashboard :
```bash
python app.py
```
Puis ouvrez `http://127.0.0.1:5000` dans votre navigateur.

Lancez simplement le menu principal :
```bash
python main.py
```

### Menu Interactif :
1.  **Recherche rapide** : Pour un check instantané.
2.  **Lancer une veille** : Active la surveillance continue (NLP).
3.  **Analyser (Top 10)** : Trie les meilleures offres en base.
4.  **Générer résumés IA** : Envoie les nouvelles annonces à l'analyseur IA.
5.  **Consulter les annonces** : Parcourez votre historique sauvegardé.

## 📖 Documentation

Consultez le manuel complet pour apprendre à utiliser toutes les fonctionnalités :
- [**Manuel d'Utilisation** (Complet)](MANUEL_UTILISATION.md) 📘

D'autres documents techniques sont disponibles dans `/documentation` :
- [Guide Utilisateur (Ancien)](documentation/GUIDE_UTILISATEUR.md)
- [Mémo Technique (Architecture)](documentation/AI_TECH_MEMO.md)

## ⚖️ Avertissement

*lbc-finder n'est pas affilié à, approuvé par, ou associé de quelque manière que ce soit à Leboncoin. L'utilisation de cet outil se fait à vos propres risques, conformément aux conditions d'utilisation du site cible.*

---
*Développé avec ❤️ pour simplifier vos recherches.*