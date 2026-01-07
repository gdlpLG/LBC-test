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

def generate_batch_summaries(ads: List[Dict[str, Any]]) -> List[Dict[str, str]]:
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
    Pour chaque annonce dans la liste JSON ci-dessous, génère un résumé très concis (2 phrases max).
    Extrais : 
    1. Les points forts (état, options).
    2. Les points faibles ou alertes (travaux, défauts).
    3. Les caractéristiques clés.

    Réponds UNIQUEMENT sous forme de liste JSON d'objets contenant "id" et "summary".
    Format : [{{"id": "...", "summary": "..."}}, ...]

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
    """
    Calcule les statistiques du marché basées sur les annonces stockées.
    """
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
