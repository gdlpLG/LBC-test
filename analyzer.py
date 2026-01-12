'''
This module provides AI-powered analysis for Leboncoin ads using Google Gemini.
'''
import os
import json
import time
import os
import json
import time
from google import genai
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Rate Limiter for Free Tier (15 RPM)
class RateLimiter:
    def __init__(self, requests_per_minute=15):
        self.rpm_limit = requests_per_minute
        self.timestamps = []
        self.daily_count = 0 
        self.last_reset = time.time()
    
    def wait_if_needed(self):
        now = time.time()
        
        # Reset daily count if 24h passed (rough approximation)
        if now - self.last_reset > 86400:
            self.daily_count = 0
            self.last_reset = now
            
        # Filter timestamps older than 60s
        self.timestamps = [t for t in self.timestamps if now - t < 60]
        
        # Check RPM
        if len(self.timestamps) >= self.rpm_limit:
            wait_time = 60 - (now - self.timestamps[0]) + 1
            if wait_time > 0:
                msg = f"⏳ Limite RPM ({self.rpm_limit}) atteinte. Pause de {int(wait_time)}s..."
                print(msg)
                set_ai_status(message=msg)
                time.sleep(wait_time)
                
        # Record this request
        self.timestamps.append(time.time())
        self.daily_count += 1

_rate_limiter = RateLimiter(requests_per_minute=15)

# Global state for the client
_current_api_key = None
_client = None
_selected_model_name = None 
_status = {"status": "idle", "progress": 0, "total": 0, "message": "En attente"}
import threading
_ai_lock = threading.Lock()


_stop_requested = False

def get_ai_status():
    return _status

def stop_analysis():
    global _stop_requested
    _stop_requested = True
    set_ai_status(status="idle", message="🛑 Analyse arrêtée par l'utilisateur.")

def set_ai_status(status=None, progress=None, total=None, message=None):
    global _status, _stop_requested
    if status is not None: 
        _status['status'] = status
        # If starting new analysis, reset stop flag
        if status == 'loading':
            _stop_requested = False
            
    if progress is not None: _status['progress'] = progress
    if total is not None: _status['total'] = total
    if message is not None: _status['message'] = message


def _discover_best_model(client):
    """
    Dynamically lists available models and picks the best one for the user.
    Preferences: gemini-2.5-flash-lite > gemini-2.5-flash > gemini-2.0-flash-lite > gemini-2.0-flash > gemini-1.5-flash
    """
    global _selected_model_name
    print("🔎 Recherche du meilleur modèle Gemini disponible...")
    
    preferred_order = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite", 
        "gemini-2.0-flash", 
        "gemini-1.5-flash"
    ]
    
    try:
        # Listing models (New SDK)
        available_models = [m.name for m in client.models.list()]
        # Filter for models supporting generateContent (usually implied by being in .models.list() but good to be safe)
        # Note: In new SDK, client.models.list() returns items with .name (e.g. "models/gemini-1.5-flash")
        
        # Clean names (remove "models/" prefix if present)
        clean_names = [m.replace("models/", "") for m in available_models]
        
        print(f"📋 Modèles disponibles : {', '.join(clean_names)}")
        
        # Find best match
        for pref in preferred_order:
            if pref in clean_names:
                _selected_model_name = pref
                print(f"✅ Modèle sélectionné : {_selected_model_name}")
                set_ai_status(message=f"✅ Modèle activé : {_selected_model_name}")
                return
        
        # Fallback if no exact match found
        # Try to find any "flash" model
        for name in clean_names:
            if "flash" in name and "gemini" in name:
                _selected_model_name = name
                print(f"⚠️ Fallback Modèle : {_selected_model_name}")
                set_ai_status(message=f"⚠️ Modèle activé (fallback) : {_selected_model_name}")
                return
                
        # Last resort
        _selected_model_name = "gemini-2.0-flash-lite"
        print(f"⚠️ Aucune correspondance, utilisation par défaut : {_selected_model_name}")
        
    except Exception as e:
        print(f"❌ Erreur découverte modèles : {e}")
        # Default safety
        _selected_model_name = "gemini-2.0-flash-lite" 


def get_client(api_key=None):
    """Returns the configured Gemini client (New SDK)."""
    global _current_api_key, _client
    
    # Priority: passed key > DB global setting > Env
    if not api_key:
        from database import get_setting
        api_key = get_setting('google_api_key') or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return None
        
    if api_key != _current_api_key or _client is None:
        try:
            # New SDK initialization
            _client = genai.Client(api_key=api_key)
            _current_api_key = api_key
            print(f"🤖 Client IA reconfiguré (google-genai)")
            
            # Trigger dynamic discovery
            _discover_best_model(_client)
            
        except Exception as e:
            msg = f"❌ Erreur configuration Client: {e}"
            print(msg)
            set_ai_status(message=msg)
            return None
            
    return _client

def safe_generate_content(prompt: str, api_key: str = None, max_retries: int = 3) -> Any:
    """
    Calls Gemini API with locking using the new google-genai SDK.
    """
    with _ai_lock:
        client = get_client(api_key)
        if not client:
            set_ai_status(message="❌ Client IA non configuré ou clé API invalide.")
            return None
        
        # Determine model
        model_name = _selected_model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

        for i in range(max_retries):
            try:
                # Rate Limit Check
                _rate_limiter.wait_if_needed()
                
                # New SDK Syntax: client.models.generate_content
                return client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
            except Exception as e:
                # Handle Quota / 429 errors generic string check (robust for new SDK)
                err_str = str(e).lower()
                if "429" in err_str or "resource exhausted" in err_str or "quota" in err_str:
                    wait_time = (i + 1) * 20
                    set_ai_status(message=f"⏳ Quota Gemini (SDK v2). Pause {wait_time}s... ({i+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    msg = f"❌ Erreur critique Gemini: {str(e)}"
                    print(msg)
                    with open("debug_ai_errors.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()} - {msg}\n")
                    set_ai_status(message=msg)
                    break
        
        set_ai_status(message="❌ Échec après plusieurs tentatives (Quota ou Service HS).")
    return None


def detect_scam(ad: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
    """
    Uses AI to detect potential scams based on price, title and description.
    """
    prompt = f"""
    En tant qu'expert en cybersécurité et en fraudes sur les sites de petites annonces (type Leboncoin), analyse cette annonce pour détecter un risque d'arnaque.
    
    Titre : {ad.get('title')}
    Prix : {ad.get('price')}€
    Description : {ad.get('description')}

    Réponds UNIQUEMENT en JSON avec les clés :
    "risk_score" (entier 0-100),
    "risk_level" ("faible", "modéré", "élevé", "critique"),
    "reasons" (liste de chaînes expliquant pourquoi).
    """

    try:
        response = safe_generate_content(prompt, api_key=api_key)
        if not response or not response.text: 
            return {"risk_score": 0, "risk_level": "indisponible", "reasons": ["IA indisponible"]}
            
        text = response.text.strip()
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        return {"risk_score": 0, "risk_level": "erreur", "reasons": ["Format JSON invalide"]}
    except Exception as e:
        return {"risk_score": 0, "risk_level": "erreur", "reasons": [str(e)]}



def generate_batch_summaries(ads: List[Dict[str, Any]], user_context: str = None, api_key: str = None) -> List[Dict[str, Any]]:
    """Generates summaries for a list of ads using Gemini."""
    all_summaries = []
    chunk_size = 10
    
    total_ads = len(ads)
    set_ai_status(status="loading", progress=0, total=total_ads, message=f"🚀 Démarrage analyse de {total_ads} annonces...")
    
    for i in range(0, total_ads, chunk_size):
        if _stop_requested:
            print("Analyze stopped by user")
            break

        chunk = ads[i:i+chunk_size]
        current_batch_num = (i // chunk_size) + 1
        total_batches = (total_ads + chunk_size - 1) // chunk_size
        
        # Log detail
        msg = f"📦 Lot {current_batch_num}/{total_batches} ({len(chunk)} annonces). Context: {(user_context[:30] + '...') if user_context else 'Standard'}"
        set_ai_status(progress=i, total=total_ads, message=msg)
        
        ads_data = [{"id": ad['id'], "titre": ad['title'], "description": ad['description'][:1000]} for ad in chunk]
        
        prompt = f"""
        Objectif : {user_context or "Analyse générale."}
        Pour chaque annonce JSON, génère un résumé (2 sentences), un score (1-10) et un conseil.
        Réponds UNIQUEMENT en JSON : [{{"id": "...", "ai_summary": "...", "ai_score": 8, "ai_tips": "..."}}, ...]
        Données : {json.dumps(ads_data, ensure_ascii=False)}
        """

        try:
            response = safe_generate_content(prompt, api_key=api_key)
            if response and response.text:
                text = response.text.strip()
                # Remove markdown code blocks if present
                if text.startswith("```"):
                    text = text.replace("```json", "").replace("```", "")
                
                s, e = text.find('['), text.rfind(']')
                if s != -1 and e != -1:
                    new_sums = json.loads(text[s:e+1])
                    all_summaries.extend(new_sums)
                    set_ai_status(message=f"✅ Lot {current_batch_num} validé : {len(new_sums)} analyses reçues.")
                else:
                    set_ai_status(message=f"⚠️ Lot {current_batch_num}: Réponse IA non conforme (JSON vide/invalide).")
            else:
                 set_ai_status(message=f"⚠️ Lot {current_batch_num}: Pas de réponse de l'IA (ou vide).")

            time.sleep(1) # Little pause to be nice
        except Exception as e:
            err_msg = f"❌ Erreur technique sur le lot {current_batch_num}: {str(e)}"
            print(err_msg)
            set_ai_status(message=err_msg)

    set_ai_status(status="idle", message=f"🎉 Terminé ! {len(all_summaries)}/{total_ads} annonces analysées avec succès.")
    return all_summaries


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
    Computes statistical data for a given search query based on saved ads.
    """
    from database import get_all_ads
    ads = get_all_ads()
    
    # Filtrage par mot-clé (simple)
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

def get_ai_market_analysis(query_text: str, ads: List[Dict[str, Any]]) -> str:
    """
    Asks Gemini to analyze the market trends based on a list of ads.
    """
    client = get_client()
    if not client: return "IA non disponible."
    
    # Prepare data (limit to titles and prices to save tokens if many ads)
    market_data = [{"t": a['title'], "p": a['price']} for a in ads[:100]]
    
    prompt = f"""
    Analyse le marché pour la recherche : "{query_text}"
    Voici les données des 100 dernières annonces (Titre et Prix) :
    {json.dumps(market_data, ensure_ascii=False)}

    Rédige un rapport de marché concis (environ 250 mots) en Markdown incluant :
    1. L'état général du marché (pénurie, abondance, stabilité).
    2. La fourchette de prix "Bonne affaire" vs " Trop cher".
    3. Les tendances observées (versions plus recherchées, accessoires récurrents).
    4. Un conseil stratégique pour un acheteur aujourd'hui.
    """

    try:
        response = safe_generate_content(prompt)
        return response.text if response else "Analyse indisponible."
    except Exception as e:
        return f"Erreur d'analyse : {e}"



def generate_comparison(ads: List[Dict[str, Any]], api_key: str = None) -> str:
    """Asks Gemini to compare a list of ads and recommend the best one."""
    data = [{"t": a['title'], "p": a['price'], "d": a.get('description', '')[:500]} for a in ads]
    prompt = f"Compare ces annonces et dis laquelle est la meilleure affaire. Réponds en Markdown.\n{json.dumps(data)}"
    res = safe_generate_content(prompt, api_key=api_key)
    return res.text if res else "Comparaison indisponible."


def get_chat_response(query: str, ad_data: Dict[str, Any], history: List[Dict[str, str]] = None, api_key: str = None) -> str:
    """Chat with the AI about an ad or general search."""
    ctx = f"Annonce: {ad_data['title']} ({ad_data['price']}€)\n{ad_data.get('description', '')[:1000]}" if ad_data else "Pas d'annonce spécifique."
    prompt = f"Tu es un expert Leboncoin. Voici le contexte:\n{ctx}\n\nQuestion: {query}"
    res = safe_generate_content(prompt, api_key=api_key)
    return res.text if res else "Erreur de réponse."


def refine_search_query(goal: str, api_key: str = None) -> str:
    """Refines a search query into technical instructions."""
    prompt = f"Rédige une instruction de veille Leboncoin experte pour : {goal}"
    res = safe_generate_content(prompt, api_key=api_key)
    return res.text.strip() if res else "Erreur."


def generate_negotiation_draft(ad: Dict[str, Any], api_key: str = None) -> str:
    """Generates a negotiation message."""
    prompt = f"Rédige un message de négociation poli pour : {ad['title']} à {ad['price']}€."
    res = safe_generate_content(prompt, api_key=api_key)
    return res.text if res else "Erreur."


