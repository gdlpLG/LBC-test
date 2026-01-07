'''
This module provides AI-powered analysis for Leboncoin ads using Google Gemini.
'''
import os
import json
import google.generativeai as genai
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
else:
    model = None

def generate_batch_summaries(ads: List[Dict[str, Any]], user_context: str = None) -> List[Dict[str, Any]]:
    """
    Generates summaries for a list of ads using Gemini.
    """
    if not model:
        print("[Erreur IA] GEMINI_API_KEY non trouvée. Veuillez configurer votre fichier .env")
        return []

    print(f"\nAppel à Gemini pour résumer {len(ads)} annonce(s)...")

    # Construct the JSON prompt
    ads_data = [{"id": ad['id'], "titre": ad['title'], "description": ad['description'][:1000]} for ad in ads]
    
    prompt = f"""
    Tu es un assistant expert en analyse d'annonces Leboncoin.
    CONTEXTE SPÉCIFIQUE DE RECHERCHE : {user_context or "Analyse générale de qualité/prix."}

    Pour chaque annonce dans la liste JSON ci-dessous, génère un résumé très concis (2 phrases max).
    Extrais : 
    1. Les points forts (état, options).
    2. Les points faibles ou alertes (travaux, défauts).
    3. Les caractéristiques clés.

    Réponds UNIQUEMENT sous forme de liste JSON d'objets contenant "id", "summary", "score" et "tips".
    - "id": l'identifiant de l'annonce
    - "summary": un résumé concis (points forts/faibles)
    - "score": une note de 1 à 10 sur la qualité de l'affaire et la clarté de l'annonce
    - "tips": un conseil court pour négocier ou une question à poser au vendeur

    Format : [{{"id": "...", "summary": "...", "score": 8.5, "tips": "..."}}, ...]

    Annonces :
    {json.dumps(ads_data, ensure_ascii=False)}
    """

    try:
        response = model.generate_content(prompt)
        # Clean response text in case LLM adds markdown backticks
        text_response = response.text.replace('```json', '').replace('```', '').strip()
        summaries = json.loads(text_response)
        print(f"✅ {len(summaries)} résumés générés avec succès.")
        return summaries
    except Exception as e:
        print(f"❌ Erreur lors de l'appel Gemini : {e}")
        return []

def calculate_score(ad: Dict[str, Any], search_text: str, ideal_price: float) -> float:
    """
    Calcule un score de pertinence (0-10) basé sur le prix et le titre.
    """
    score = 5.0 # Base score
    
    # 1. Analyse du prix
    try:
        price = float(ad.get('price', 0))
        if price > 0:
            diff = abs(price - ideal_price) / ideal_price
            if price <= ideal_price:
                score += (1 - diff) * 4 # Bonus si moins cher
            else:
                score -= diff * 5 # Malus si plus cher
    except: pass

    # 2. Analyse du titre
    if search_text.lower() in ad.get('title', '').lower():
        score += 2
    
    return max(0, min(10, round(score, 1)))

def analyze_results(search_text: str, ideal_price: float):
    """
    Analyse les annonces en base et affiche le Top 10 des meilleures affaires.
    """
    from database import get_all_ads
    ads = get_all_ads()
    
    scored_ads = []
    for ad in ads:
        if search_text.lower() in ad['title'].lower() or search_text.lower() in ad['description'].lower():
            ad['score'] = calculate_score(ad, search_text, ideal_price)
            scored_ads.append(ad)
    
    scored_ads.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n--- Top 10 des annonces pour '{search_text}' (Prix idéal: {ideal_price}€) ---")
    if not scored_ads:
        print("Aucune annonce correspondante trouvée.")
        return

    for i, ad in enumerate(scored_ads[:10]):
        print(f"#{i+1} [Score: {ad['score']}/10] {ad['title']} - {ad['price']}€")
        print(f"   URL: {ad['url']}")
        print(f"   Résumé IA: {ad.get('ai_summary') or 'Non disponible'}")
        print("-" * 50)

def get_market_stats(query_text: str) -> Dict[str, Any]:
    # ... existing code ...
    from database import get_all_ads
    ads = get_all_ads()
    
    # Filtrage par mot-clé (simple pour le moment)
    prices = [float(ad['price']) for ad in ads 
              if ad['price'] and (query_text.lower() in ad['title'].lower() or query_text.lower() in ad['description'].lower())]
    
    if not prices:
        return {"count": 0, "avg": 0, "median": 0, "min": 0, "max": 0}
    
    prices.sort()
    count = len(prices)
    avg = sum(prices) / count
    median = prices[count // 2] if count % 2 != 0 else (prices[count // 2 - 1] + prices[count // 2]) / 2
    
    return {
        "count": count,
        "avg": round(avg, 2),
        "median": round(median, 2),
        "min": min(prices),
        "max": max(prices)
    }

def compare_and_recommend(ads: List[Dict[str, Any]]) -> str:
    """
    Asks Gemini to compare a list of ads and recommend the best one(s).
    """
    if not model: return "IA non configurée."
    
    # Prepare compact data to save tokens
    comparison_data = []
    for ad in ads:
        comparison_data.append({
            "titre": ad['title'],
            "prix": ad['price'],
            "description": ad.get('description', ''), # We use the full description here as context is large
            "score_precedent": ad.get('ai_score', 'N/A')
        })

    prompt = f"""
    En tant qu'expert en achat d'occasion et personal shopper, analyse en profondeur ces {len(ads)} annonces.
    Puisque j'ai un large contexte de tokens, examine chaque détail des descriptions pour déceler les vices cachés ou les opportunités exceptionnelles.

    Critères d'analyse :
    1. État réel perçu à travers la description.
    2. Cohérence du prix par rapport à l'état.
    3. Fiabilité du vendeur (pro vs particulier, clarté du texte).
    4. Équipements ou accessoires inclus qui justifient le prix.

    Structure de la réponse :
    - 🏆 LE MEILLEUR CHOIX : Nom de l'objet + Pourquoi c'est le gagnant indiscutable.
    - 🥈 L'ALTERNATIVE : Pour quel profil d'acheteur elle serait intéressante.
    - 🚩 ALERTES : Points de vigilance spécifiques sur les autres annonces.
    - 💬 STRATÉGIE : Comment aborder le vendeur du gagnant.

    Données :
    {json.dumps(comparison_data, ensure_ascii=False)}

    Réponds en Markdown avec un ton expert et assuré.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erreur lors de la comparaison : {e}"

def build_ai_instructions(user_goal: str) -> str:
    """
    Acts as a consultant to help the user build a complex 'Gem' (AI Instruction).
    """
    if not model: return "IA non configurée."

    prompt = f"""
    Tu es un expert en 'Prompt Engineering' et en achat d'occasion.
    L'utilisateur veut créer une veille Leboncoin avec l'objectif suivant : "{user_goal}"
    
    Ta mission est de rédiger une "Instruction de Personal Shopper" ultra-détaillée que le programme utilisera pour analyser chaque annonce à sa place.
    
    L'instruction doit inclure :
    1. Un rôle précis (ex: "Tu es un mécanicien expert en voitures anciennes").
    2. Une liste de points de contrôle techniques basés sur l'objectif.
    3. Les "Red Flags" (alertes) spécifiques à cet objet.
    4. Comment évaluer le prix par rapport à l'état.

    Réponds UNIQUEMENT par le texte de l'instruction prête à l'emploi. 
    Soit professionnel, technique et exigeant. Ne commence pas par "Voici l'instruction", donne directement le contenu.
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```markdown', '').replace('```', '').strip()
        return text
    except Exception as e:
        return f"Erreur lors de la construction : {e}"
