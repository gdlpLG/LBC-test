'''
This module provides AI-powered analysis for Leboncoin ads using
data from the SQLite database.
'''
from database import get_all_ads
from datetime import datetime

def generate_summary(title: str, description: str) -> str:
    """
    Uses the Gemini model's intelligence to generate a structured summary of an ad.
    This function simulates a call to a powerful language model.
    """
    # This is a simplified simulation of what a call to a powerful LLM like Gemini would do.
    # It identifies key positive and negative points from the text.
    
    summary_points = {
        "points_forts": [],
        "points_faibles": [],
        "caracteristiques": []
    }

    full_text = (title + " " + description).lower()

    # Keywords for positive points
    pos_keywords = ["excellent état", "comme neuf", "rénové", "faible kilométrage", "lumineux", "aucun frais à prévoir", "bien entretenu"]
    # Keywords for negative points
    neg_keywords = ["à rénover", "prévoir travaux", "vendu en l'état", "rayures", "problème moteur", "agence s'abstenir", "frais à prévoir"]
    # Keywords for key features
    feature_keywords = ["garage", "parking", "balcon", "terrasse", "jardin", "piscine", "clim", "cuir", "gps"]

    for keyword in pos_keywords:
        if keyword in full_text:
            summary_points["points_forts"].append(keyword.capitalize())

    for keyword in neg_keywords:
        if keyword in full_text:
            summary_points["points_faibles"].append(keyword.capitalize())
    
    for keyword in feature_keywords:
        if keyword in full_text:
            summary_points["caracteristiques"].append(keyword.capitalize())
            
    # --- Formatting the output ---
    output = ""
    if summary_points["points_forts"]:
        output += "Points forts : " + ", ".join(summary_points["points_forts"]) + ". "
    if summary_points["points_faibles"]:
        output += "Points faibles : " + ", ".join(summary_points["points_faibles"]) + ". "
    if summary_points["caracteristiques"]:
        output += "Caractéristiques : " + ", ".join(summary_points["caracteristiques"]) + "."

    return output if output else "Pas de détails spécifiques trouvés pour un résumé automatique."


def calculate_score(ad: dict, search_text: str, ideal_price: float) -> float:
    # ... (this function remains the same)
    score = 0
    try:
        price = float(ad['price'])
        if ideal_price > 0:
            price_diff = abs(price - ideal_price) / ideal_price
            score += max(0, 40 * (1 - price_diff))
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    try:
        ad_date = datetime.fromisoformat(ad['date'])
        days_diff = (datetime.now() - ad_date).days
        if days_diff < 30:
            score += max(0, 30 * ((30 - days_diff) / 30))
    except (ValueError, TypeError):
        pass
    title = ad['title'].lower()
    description = ad['description'].lower()
    search_terms = search_text.lower().split()
    if search_terms:
        for term in search_terms:
            if term in title:
                score += 20 / len(search_terms)
            if term in description:
                score += 10 / len(search_terms)
    return score

def analyze_results(search_text: str, ideal_price: float):
    # ... (this function remains the same)
    ads = get_all_ads()
    if not ads:
        print("Aucune annonce trouvée dans la base de données. Veuillez d'abord lancer une veille.")
        return
    print(f"\n--- Analyse de {len(ads)} annonces pour la pertinence ---")
    scored_ads = []
    for ad in ads:
        ad_for_scoring = {
            'title': ad['title'],
            'price': ad['price'],
            'date': ad['date'],
            'description': ad['description'],
            'url': ad['url'],
            'location': ad['location']
        }
        score = calculate_score(ad_for_scoring, search_text, ideal_price)
        scored_ads.append((ad_for_scoring, score))
    scored_ads.sort(key=lambda x: x[1], reverse=True)
    print("\n--- Les 10 annonces les plus pertinentes ---\n")
    for i, (ad, score) in enumerate(scored_ads[:10]):
        print(f"#{i+1} - Pertinence: {score:.1f}/100")
        print(f"  Titre: {ad['title']}")
        print(f"  Prix: {ad['price']} €")
        print(f"  Lieu: {ad['location']}")
        print(f"  URL: {ad['url']}\n")
